"""
Task processing and execution logic for ATTPC Flow.
Handles individual task execution and workflow orchestration.
"""

import concurrent.futures
import multiprocessing
from enum import IntEnum
from typing import Dict, Any
import logging
import json

from .node_manager import NodeManager
from .workflow import Workflow
from .progress.progress_store import ProgressStore

# Use 'spawn' context to avoid fork + polars/rayon thread pool deadlock.
# When polars is used in the parent process (e.g. via RunTagDB API calls),
# its rayon thread pool is initialized. fork() inherits the dead thread pool
# state, causing child processes to deadlock when they use polars.
_mp_context = multiprocessing.get_context('spawn')

def _init_worker():
	"""Initialize worker process for spawn context.
	With 'spawn', child processes start fresh and need to re-register nodes."""
	# Import node modules to trigger @auto_register_node decorators
	import importlib
	importlib.import_module('atflow.nodes')
	manager = NodeManager()
	manager.discover_nodes()

# Set up logger
logger = logging.getLogger(__name__)

class TaskStatus(IntEnum):
	DISCARDED = -2
	FAILED = -1
	COMPLETED = 0
	WAITING = 1
	READY = 2
	QUEUED = 3
	RUNNING = 4

def run_node(task):
	task["status"] = TaskStatus.RUNNING
	manager = NodeManager()
	return manager.execute_node(
		name=task["name"],
		execution_id=task["execution_id"],
		task_id=task["id"],
		environment=task["environment"],
		inputs=task["inputs"],
		properties=task["properties"]
	)

class Processor:
	def __init__(self, execution_id: str, workflow: Workflow):
		self.threads = workflow.workers
		self.environment = {
			"execution_id": execution_id,
			"workspace": workflow.workspace,
			"run_list": workflow.run.runs,
		}
		self._init_tasks(workflow)
		self.futures_to_task = {}
		# Progress store for direct updates
		self.progress_store = ProgressStore()
		self.progress_store.register_tasks_information(
			execution_id,
			{
				str(task["id"]) : {
					"name": task["name"],
					"run": task["environment"]["run_str"],
				} for task in self.tasks
			}
		)
	def process(self):
		execution_id = self.environment.get("execution_id")
		# Report execution start
		self.progress_store.start_execution(execution_id, len(self.tasks))

		with concurrent.futures.ProcessPoolExecutor(
			max_workers=self.threads,
			mp_context=_mp_context,
			initializer=_init_worker,
		) as executor:
			# submit initial ready tasks
			self._submit_ready_tasks(executor)
			while self.futures_to_task:
				# Use as_completed to iterate over futures as they complete
				for future in concurrent.futures.as_completed(self.futures_to_task):
					# get task from future
					task = self.futures_to_task.pop(future, None)
					if task is None:
						continue
					# check result
					try:
						# success
						result = future.result()
						task["status"] = TaskStatus.COMPLETED
						task["outputs"] = result

					except Exception as e:
						# failed
						task["status"] = TaskStatus.FAILED
						logger.error(f"Task {task['id']} failed: {e}")
						# Report task failed
						self.progress_store.finish_task(execution_id, str(task["id"]), failed=True)

					finally:
						completed_tasks = 0
						for jtask in self.tasks:
							if (
								jtask["status"] == TaskStatus.DISCARDED
								or jtask["status"] == TaskStatus.FAILED
								or jtask["status"] == TaskStatus.COMPLETED
							):
								completed_tasks += 1
						self.progress_store.update_execution_progress(
							execution_id,
							completed_tasks,
							len(self.tasks)
						)
						logger.debug(f"Execution {execution_id} progress: {completed_tasks}/{len(self.tasks)}")

					# submit new tasks
					self._reduce_waiting(task["id"])
					self._submit_ready_tasks(executor)

					# Break out of as_completed loop to re-evaluate futures_to_task
					break

		# Report execution finish
		self.progress_store.finish_execution(execution_id, len(self.tasks))

		for task in self.tasks:
			if task["status"] == TaskStatus.COMPLETED:
				logger.info(f"Task {task["id"]} completed with result: {task["outputs"]}")
			elif task["status"] == TaskStatus.FAILED:
				logger.info(f"Task {task["id"]} failed.")

	def _init_tasks(self, workflow: Workflow):
		# print(json.dumps(workflow.model_dump(), indent=2))
		adapted = self._adapt_workflow(workflow)
		print(json.dumps(adapted, indent=2))

		load_run_nodes = []
		single_mode_nodes = []
		multiple_mode_nodes = []
		for node in adapted["nodes"]:
			if node["name"] == "load_run":
				single_mode_nodes.append(node["id"])
				load_run_nodes.append(node["id"])
			elif node["name"] == "load_list_run":
				multiple_mode_nodes.append(node["id"])
		if len(multiple_mode_nodes) != 0:
			raise NotImplementedError("Multiple mode nodes are not supported yet.")
		change = True
		while change:
			change = False
			for node in adapted["nodes"]:
				if node["id"] in single_mode_nodes:
					continue
				for depend_node in node["waiting"]:
					if depend_node in single_mode_nodes:
						single_mode_nodes.append(node["id"])
						change = True

		# solve load run
		self.tasks = []
		task_id = 0
		task_id_map = {}
		for run in self.environment["run_list"]:
			for node in adapted["nodes"]:
				if node["name"] == "load_run":
					continue
				task = {
					"execution_id": self.environment["execution_id"],
					"id": task_id,
					"name": node["name"],
					"environment": {
						"run": run,
						"run_str": str(run),
						"workspace": self.environment["workspace"],
						**self.environment
					},
					"ports": [],
					"inputs": {},
					"properties": {},
					"waiting": [],
					"status": TaskStatus.WAITING
				}
				for port in node["inputs"]:
					if port["link_node"] == -1:
						task["inputs"][port["name"]] = port["value"]
					elif port["link_node"] in load_run_nodes:
						task["inputs"][port["name"]] = int(run)
					else:
						task["ports"].append({
							"port": "inputs",
							"name": port["name"],
							"link_task": (run, port["link_node"]),
							"link_port": port["link_port"],
						})
				for port in node["properties"]:
					if port["link_node"] == -1:
						task["properties"][port["name"]] = port["value"]
					elif port["link_node"] in load_run_nodes:
						task["properties"][port["name"]] = int(run)
					else:
						task["ports"].append({
							"port": "properties",
							"name": port["name"],
							"link_task": (run, port["link_node"]),
							"link_port": port["link_port"],
						})
				for id in node["waiting"]:
					if id not in load_run_nodes:
						task["waiting"].append((run, id))
				if len(task["waiting"]) == 0:
					task["status"] = TaskStatus.READY
				self.tasks.append(task)
				task_id_map[(run, node["id"])] = task_id
				task_id += 1
		# print(json.dumps(self.tasks, indent=2))
		for task in self.tasks:
			# solve link task id
			for port in task["ports"]:
				port["link_task"] = task_id_map[port["link_task"]]
			# solve waiting task id
			solve_waiting = []
			for w in task["waiting"]:
				solve_waiting.append(task_id_map[w])
			task["waiting"] = solve_waiting
		print(json.dumps(self.tasks, indent=2))

	def _parse_property_value(self, prop: Dict[str, Any]):
		"""Parse property value based on its type."""
		result = None
		if "type" in prop:
			try:
				match prop["type"]:
					case "integer":
						result = int(prop["value"])
					case "float":
						result = float(prop["value"])
					case "bool":
						result = bool(prop["value"])
					case "str":
						result = prop["value"]
			except:
				result = None
		return result

	def _adapt_workflow(self, workflow: Workflow):
		"""Adapt workflow to execution task."""
		adapted = {
			"workflow_name": workflow.name,
			"workspace": workflow.workspace,
			"threads": workflow.workers,
			"run_list": workflow.run.runs,
			"nodes": [
				{
					"id": node.id,
					"name": node.name,
					"inputs": [
						{
							"name": v["name"],
							"link_node": -1,
						} for v in node.inputs
					],
					"properties": [
						{
							"name": v["name"],
							"link_node": -1,
							"value": self._parse_property_value(v),
						} for v in node.properties
					],
					"waiting": [],
				} for node in workflow.nodes
			],
		}
		# get map
		node_map = {node["id"]: idx for idx, node in enumerate(adapted["nodes"])}
		# loop links
		for link in workflow.links:
			target_node = adapted["nodes"][node_map[link.target]]
			target_port_id = int(link.targetHandle.split("-")[1])
			target_port = (
				target_node["inputs"][target_port_id]
				if link.targetHandle.startswith("input-")
				else target_node["properties"][target_port_id]
			)
			target_port["link_node"] = link.source
			target_port["link_port"] = int(link.sourceHandle.split("-")[1])
			target_node["waiting"].append(link.source)
		return adapted

	def _submit_ready_tasks(self, executor):
		for task in self.tasks:
			if task["status"] != TaskStatus.READY:
				continue
			task["status"] = TaskStatus.QUEUED
			# self.progress_store.start_task(task["execution_id"], str(task["id"]))
			future = executor.submit(run_node, task)
			self.futures_to_task[future] = task

	def _reduce_waiting(self, task_id):
		for task in self.tasks:
			if task["status"] != TaskStatus.WAITING:
				continue
			if task_id not in task["waiting"]:
				continue
			task["waiting"].remove(task_id)
			self._solve_links(task_id, task)
			if len(task["waiting"]) == 0 and task["status"] == TaskStatus.WAITING:
				task["status"] = TaskStatus.READY

	def _solve_links(self, task_id, task):
		outputs = self.tasks[task_id]["outputs"]
		for port in task["ports"]:
			if port["link_task"] != task_id:
				continue
			if outputs[port["link_port"]] is None:
				task["status"] = TaskStatus.DISCARDED
				self._chain_discard(task["id"])
				break
			else:
				task[port["port"]][port["name"]] = outputs[port["link_port"]]

	def _chain_discard(self, task_id):
		for task in self.tasks:
			if task["status"] == TaskStatus.WAITING and task_id in task["waiting"]:
				task["status"] = TaskStatus.DISCARDED
				self._chain_discard(task["id"])

	@classmethod
	def run(cls, execution_id: str, workflow: Workflow):
		processor = cls(execution_id, workflow)
		processor.process()