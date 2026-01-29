"""
Task processing and execution logic for ATTPC Flow.
Handles individual task execution and workflow orchestration.
"""

import concurrent.futures
import threading
from enum import IntEnum
import logging

from .node_registry import NodeRegistry, NodeInfo

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
	return NodeRegistry.dispatch(
		name=task["name"],
		execution_id=task["execution_id"],
		task_id=task["id"],
		environment=task["environment"],
		inputs=task["inputs"],
		properties=task["properties"]
	)

class Processor:
	def __init__(self, threads, environment, tasks):
		self.threads = threads
		self.environment = environment
		self._init_tasks(tasks)
		self.futures_to_task = {}

	def process(self):
		# No collector needed here - handled by manager
		with concurrent.futures.ProcessPoolExecutor(max_workers=self.threads) as executor:
			# submit initial ready tasks
			self._submit_ready_tasks(executor)
			while self.futures_to_task:
				# wait until any task is completed
				done, _ = concurrent.futures.wait(
					self.futures_to_task.keys(),
					return_when=concurrent.futures.FIRST_COMPLETED,
				)
				for future in done:
					# get task from future
					task = self.futures_to_task.pop(future)
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
					# submit new tasks
					self._reduce_waiting(task["id"])
					self._submit_ready_tasks(executor)
		for task in self.tasks:
			if task["status"] == TaskStatus.COMPLETED:
				logger.info(f"Task {task["id"]} completed with result: {task["outputs"]}")
			elif task["status"] == TaskStatus.FAILED:
				logger.info(f"Task {task["id"]} failed.")

	def _init_tasks(self, pre_tasks):
		offset = 0
		self.tasks = []
		for run in self.environment["run_list"]:
			for ptask in pre_tasks:
				task = {
					"execution_id": self.environment["execution_id"],
					"id": ptask.id + offset,
					"name": ptask.name,
					"environment": {
						"run": run,
						"workspace_dir": self.environment["workspace"],
						**self.environment
					},
					"ports": [],
					"inputs": {},
					"properties": {},
					"waiting": [],
					"status": TaskStatus.WAITING
				}
				for port in ptask.inputs:
					if port.link_task == -1:
						task["inputs"][port.name] = port.value
					else:
						task["ports"].append({
							"port": "inputs",
							"name": port.name,
							"link_task": port.link_task + offset,
							"link_port": port.link_port,
							"value": None
						})
				for port in ptask.properties:
					if port.link_task == -1:
						task["properties"][port.name] = port.value
					else:
						task["ports"].append({
							"port": "properties",
							"name": port.name,
							"link_task": port.link_task + offset,
							"link_port": port.link_port,
							"value": None
						})
				for id in ptask.waiting:
					task["waiting"].append(id + offset)
				if len(task["waiting"]) == 0:
					task["status"] = TaskStatus.READY
				self.tasks.append(task)
			offset += len(pre_tasks)

	def _submit_ready_tasks(self, executor):
		for task in self.tasks:
			if task["status"] != TaskStatus.READY:
				continue
			task["status"] = TaskStatus.QUEUED
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
	def run(cls, threads, environment, tasks):
		processor = cls(threads, environment, tasks)
		processor.process()