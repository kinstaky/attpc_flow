import concurrent.futures
import importlib
import logging
import multiprocessing
from dataclasses import asdict, is_dataclass
from typing import Any

from .node_manager import NodeManager
from .progress.progress_store import ProgressStore
from .tasks import (
	Task,
	BatchTask,
	EventTask,
	Dependency,
	EventTaskUnit,
	TaskStatus,
)
from .workflow import Workflow

logger = logging.getLogger(__name__)
_mp_context = multiprocessing.get_context("spawn")

def _run_task(task: Task) -> list[Any]:
	return task.run()

def _init_worker() -> None:
	"""Initialize worker process for spawn context."""
	importlib.import_module("atflow.nodes")
	manager = NodeManager()
	manager.discover_nodes()

class Processor:
	def __init__(self, execution_id: str, workflow: Workflow):
		self.threads = workflow.workers
		self.environment = {
			"execution_id": execution_id,
			"workspace": workflow.workspace,
			"run_list": workflow.run.runs,
		}

		self.manager = NodeManager()
		self.manager.discover_nodes()

		self.resolved_workflow = {}
		self.task_templates = {}
		self.tasks: list[Task] = []
		self.futures_to_task: dict[concurrent.futures.Future[list[object]], Task] = {}
		self._init_tasks(workflow)
		self.progress_store = ProgressStore()
		self.progress_store.register_tasks_information(
			execution_id,
			{
				str(task.id): {
					"name": task.name,
					"run": str(task.environment["run"]),
				}
				for task in self.tasks
			}
		)

	def process(self) -> None:
		execution_id = self.environment["execution_id"]
		self.progress_store.start_execution(execution_id, len(self.tasks))

		with concurrent.futures.ProcessPoolExecutor(
			max_workers=self.threads,
			mp_context=_mp_context,
			initializer=_init_worker,
		) as executor:
			# submit initial ready tasks
			self._submit_ready_tasks(executor)
			while self.futures_to_task:
				for future in concurrent.futures.as_completed(self.futures_to_task):
					task = self.futures_to_task.pop(future, None)
					if task is None:
						continue
					try:
						result = future.result()
						task.status = TaskStatus.COMPLETED
						task.outputs = result
						logger.info("Task %s (%s) completed", task.id, task.name)
					except Exception as error:
						task.status = TaskStatus.FAILED
						logger.error("Task %s (%s) failed: %s", task.id, task.name, error)
						self.progress_store.finish_task(execution_id, str(task.id), failed=True)

					completed_tasks = sum(
						1
						for current in self.tasks
						if current.status in (
							TaskStatus.DISCARDED,
							TaskStatus.FAILED,
							TaskStatus.COMPLETED,
						)
					)
					self.progress_store.update_execution_progress(
						execution_id,
						completed_tasks,
						len(self.tasks),
					)
					self._reduce_waiting(task.id)
					self._submit_ready_tasks(executor)
					break

			self.progress_store.finish_execution(execution_id, len(self.tasks))

	def _init_tasks(self, workflow: Workflow) -> None:
		self._resolve_workflow(workflow)
		self._nodes_to_tasks(self.resolved_workflow)
		self._compile_tasks(self.task_templates)

	def _parse_property_value(self, prop: dict[str, Any]) -> Any:
		"""Parse property value base on its type."""
		result = None
		value = prop.get("value")
		if value in ("", None):
			return None
		try:
			match prop["type"]:
				case "int" | "integer":
					result = int(prop["value"])
				case "float":
					result = float(prop["value"])
				case "bool":
					if isinstance(prop["value"], bool):
						result = prop["value"]
					else:
						result = str(prop["value"]).lower() in {"1", "true", "yes", "on"}
				case _:
					result = prop["value"]
		except Exception:
			result = None
		return result

	def _resolve_workflow(self, workflow: Workflow) -> None:
		resolved = {
			"workflow_name": workflow.name,
			"workspace": workflow.workspace,
			"threads": workflow.workers,
			"run_list": workflow.run.runs,
			"nodes": []
		}
		# resolve nodes
		for node in workflow.nodes:
			node_class = self.manager.get_node(node.name)
			if node_class is None:
				raise ValueError(f"Workflow node '{node.name}' is not registered")
			resolved["nodes"].append({
				"id": node.id,
				"name": node.name,
				"type": node_class.type(),
				"inputs": [
					{
						"name": port["name"],
						"link_node": -1,
					} for port in node.inputs
				],
				"properties": [
					{
						"name": prop["name"],
						"link_node": -1,
						"value": self._parse_property_value(prop),
					} for prop in node.properties
				],
				"waiting": [],
			})
		# get map
		node_map = {node["id"]: index for index, node in enumerate(resolved["nodes"])}

		for link in workflow.links:
			# check link rules:
			# 1. instant node ---> instant node only
			# 2. batch node -x-> event node
			# 3. event node -x-> batch node
			# 4. property ---> instant node only
			source_node = resolved["nodes"][node_map[link.source]]
			source_type = source_node["type"]
			target_node = resolved["nodes"][node_map[link.target]]
			target_type = target_node["type"]
			if (
				(target_type == "instant" and source_type != "instant")
				or (target_type == "event" and source_type == "batch")
				or (target_type == "batch" and source_type == "event")
			):
				raise ValueError(
					f"Link from {source_type} node '{source_node['name']}' to {target_type} node '{target_node['name']}' is not allowed"
				)
			if link.targetHandle.startswith("property") and source_type != "instant":
				raise ValueError(
					f"Link from {source_type} node '{source_node['name']}' to property is not allowed"
				)

			target_index = int(link.targetHandle.split("-")[1])
			target_port = (
				target_node["inputs"][target_index]
				if link.targetHandle.startswith("input")
				else target_node["properties"][target_index]
			)
			target_port["link_node"] = link.source
			target_port["link_port"] = int(link.sourceHandle.split("-")[1])
			target_node["waiting"].append(link.source)

		self.resolved_workflow = resolved

	def _nodes_to_tasks(self, workflow: dict[str, Any]) -> None:
		converted = []
		instant_values = {}
		self.task_templates = []
		open_templates = []

		def _resolve_property(node: dict[str, Any]):
			result = {}
			for prop in node["properties"]:
				if prop["link_node"] != -1:
					if prop["link_node"] not in instant_values:
						raise ValueError(
							f"Node {node['id']} depends on {prop['link_node']}, but not exist in instant_values"
						)
					prop["value"] = instant_values[prop["link_node"]][prop["link_port"]]
				result[prop["name"]] = prop["value"]
			return result

		def _create_open_template(
				node: dict[str, Any],
				properties: dict[str, Any],
			):
			open_templates.append({
				"id": node["id"],
				"name": node["alias"] if "alias" in node else "phase",
				"type": "event",
				"units": [{
					"name": node["name"],
					"parameters": {**properties} if properties else None,
					"dependencies": {},
				}],
				"waiting": node["waiting"].copy(),
				"contains": [node["id"]],
				"id_map": {node["id"]: 0},
				"open": True,
			})

		def _append_unit(
			node: dict[str, Any],
			properties: dict[str, Any],
			name: str,
			close: bool = False
		):
			found = False
			for template in open_templates:
				if not template["open"]:
					continue
				if not set(node["waiting"]).issubset(template["contains"]):
					continue
				found = True
				template["units"].append({
					"name": name,
					"parameters": {**properties},
					"dependencies": {
						port["name"]: (
							template["id_map"][port["link_node"]],
							port["link_port"]
						)
						for port in node["inputs"]
					},
				})
				template["contains"].append(node["id"])
				template["id_map"][node["id"]] = len(template["units"]) - 1
				template["open"] = not close
				if close:
					self.task_templates.append(template)

			if not found:
				raise ValueError(
					f"Node {node['id']} can't find reader."
				)


		change = True
		while change:
			change = False
			for node in workflow["nodes"]:
				if (
					node["id"] in converted
					or not set(node["waiting"]).issubset(converted)
				): continue
				change = True
				properties = _resolve_property(node)

				if node["type"] == "instant":
					manager = NodeManager()
					instant_values[node["id"]] = (
						manager.instant_execute_node(node["name"], properties)
					)

				elif node["type"] == "batch":
					task = {
						"id": node["id"],
						"name": node["name"],
						"type": "batch",
						"parameters": {**properties},
						"dependencies": {
							port["name"]: (
								port["link_node"],
								port["link_port"]
							)
							for port in node["inputs"]
						},
						"waiting": node["waiting"],
					}
					self.task_templates.append(task)

				elif node["type"] == "reader":
					_create_open_template(node, properties)

				elif node["type"] == "checkpoint":
					writer_name, reader_name = manager.instant_execute_node(node["name"])
					_append_unit(node, properties, writer_name, True)
					_create_open_template(node, properties)
					open_templates[-1]["units"][0]["name"] = reader_name
					open_templates[-1]["waiting"] = [node["id"]]

				elif node["type"] == "writer":
					_append_unit(node, properties, node["name"], True)

				elif node["type"] == "event":
					_append_unit(node, properties, node["name"])

				else:
					raise ValueError(f"Unknown node type: {node['type']}")
				converted.append(node["id"])

	def _task_environment(self, run: int):
		return {
			**self.environment,
			"run": run,
		}

	def _compile_tasks(self, templates):
		task_id = 0
		node_map = {}
		for run in self.environment["run_list"]:
			for template in templates:
				if template["type"] == "batch":
					task = BatchTask(
						execution_id=self.environment["execution_id"],
						id=task_id,
						name=template["name"],
						environment=self._task_environment(run),
						outputs=[],
						parameters=template["parameters"],
						dependencies=[
							Dependency(
								parameter_name=name,
								task=node_map[dep[0]],
								index=dep[1],
							)
							for name, dep in template["dependencies"].items()
						],
						waiting=template["waiting"],
						status=TaskStatus.WAITING if len(template["waiting"]) else TaskStatus.READY,
					)
					self.tasks.append(task)
					node_map[template["id"]] = task_id
					task_id += 1
				elif template["type"] == "event":
					task = EventTask(
						execution_id=self.environment["execution_id"],
						id=task_id,
						name=template["name"],
						environment=self._task_environment(run),
						outputs=[],
						units=[
							EventTaskUnit(
								id=idx,
								name=unit["name"],
								parameters=unit["parameters"],
								dependencies=unit["dependencies"],
							)
							for idx, unit in enumerate(template["units"])
						],
						waiting=template["waiting"],
						status=TaskStatus.WAITING if len(template["waiting"]) else TaskStatus.READY,
					)
					self.tasks.append(task)
					node_map[template["id"]] = task_id
					task_id += 1

	def _submit_ready_tasks(self, executor: concurrent.futures.ProcessPoolExecutor) -> None:
		"""Submit ready tasks to executor."""
		for task in self.tasks:
			if task.status != TaskStatus.READY:
				continue
			task.status = TaskStatus.QUEUED
			future = executor.submit(_run_task, task)
			self.futures_to_task[future] = task

	def _reduce_waiting(self, completed_task_id: int) -> None:
		"""Remove finished tasks from waiting list. Check if tasks become ready."""
		for task in self.tasks:
			if task.status != TaskStatus.WAITING:
				continue
			if completed_task_id not in task.waiting:
				continue
			task.waiting.remove(completed_task_id)
			# Completing one task may fill linked inputs/properties for downstream
			# tasks before they become ready.
			self._resolve_parameters(completed_task_id, task)
			if not task.waiting and task.status == TaskStatus.WAITING:
				task.status = TaskStatus.READY

	def _resolve_links(self, completed_task_id: int, task: Task) -> None:
		"""Resolve links and assign value to proerties."""
		outputs = self.tasks[completed_task_id].outputs
		discard = False
		if outputs is None:
			discard = True
		else:
			for dep in task.dependencies:
				if dep.task != completed_task_id:
					continue
				if outputs[dep.index] is None:
					discard = True
					break
				task.parameters[dep.parameter_name] = outputs[dep.index]
		if discard:
			task.status = TaskStatus.DISCARDED
			self.progress_store.discard_task(
				execution_id=self.environment["execution_id"],
				task_id=str(task.id),
			)
			self._chain_discard(task.id)

	def _chain_discard(self, discarded_task_id: int) -> None:
		for task in self.tasks:
			if task.status != TaskStatus.WAITING:
				continue
			if discarded_task_id not in task.waiting:
				continue
			task.status = TaskStatus.DISCARDED
			self.progress_store.discard_task(
				execution_id=self.environment["execution_id"],
				task_id=str(task.id),
			)
			self._chain_discard(task.id)

	def _serialize_initialization_value(self, value: Any) -> Any:
		if isinstance(value, TaskStatus):
			return value.name.lower()
		if is_dataclass(value):
			return {
				key: self._serialize_initialization_value(item)
				for key, item in asdict(value).items()
			}
		if isinstance(value, dict):
			return {
				str(key): self._serialize_initialization_value(item)
				for key, item in value.items()
			}
		if isinstance(value, list):
			return [self._serialize_initialization_value(item) for item in value]
		if isinstance(value, tuple):
			return [self._serialize_initialization_value(item) for item in value]
		return value

	def get_initialization_snapshot(self) -> dict[str, Any]:
		"""Return snapshot of the workflow state."""
		return {
			"environment": self._serialize_initialization_value(self.environment),
			"resolved_workflow": self._serialize_initialization_value(self.resolved_workflow),
			"task_templates": self._serialize_initialization_value(self.task_templates),
			"tasks": self._serialize_initialization_value(self.tasks),
		}

	@classmethod
	def run(cls, execution_id: str, workflow: Workflow) -> None:
		processor = cls(execution_id, workflow)
		processor.process()