from .node_registry import NodeRegistry

import concurrent.futures
from enum import Enum

class TaskStatus(Enum):
	WAITING = 0
	READY = 1
	RUNNING = 2
	COMPLETED = 3
	FAILED = 4

def run_node(name, environment, inputs, properties):
	return NodeRegistry.dispatch(name, environment, inputs, properties)

class Processor:
	def __init__(self, max_workers=2, environment={}):
		self.max_workers = max_workers
		self.environment = environment

	def process(self, tasks):
		futures_to_task = {}
		for task in tasks:
			if task["waiting"] > 0:
				task["status"] = TaskStatus.WAITING
			else:
				task["status"] = TaskStatus.READY
		with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
			# submit initial ready tasks
			self.__submit_ready_tasks(tasks, executor, futures_to_task)
			while futures_to_task:
				# wait until any task is completed
				done, _ = concurrent.futures.wait(
					futures_to_task.keys(),
					return_when=concurrent.futures.FIRST_COMPLETED,
				)
				for future in done:
					# get task from future
					task = futures_to_task.pop(future)
					# check result
					try:
						# success
						result = future.result()
						task["status"] = TaskStatus.COMPLETED
						task["result"] = result
						print(f"Task {task['id']} completed with result: {result}")
					except Exception as e:
						# failed
						task["status"] = TaskStatus.FAILED
						print(f"Task {task['id']} failed: {e}")
					# submit new tasks
					self.__reduce_waiting(tasks, task["id"])
					self.__submit_ready_tasks(tasks, executor, futures_to_task)

	def __reduce_waiting(self, tasks, task_id):
		for task in tasks:
			if task["status"] != TaskStatus.WAITING:
				continue
			for value in task["inputs"].values():
				if value[0] == task_id:
					task["waiting"] -= 1
			if task["waiting"] <= 0:
				task["status"] = TaskStatus.READY

	def __submit_ready_tasks(self, tasks, executor, futures_to_task):
		for task in tasks:
			if task["status"] != TaskStatus.READY:
				continue
			solved_inputs = self.__resolve_inputs(task, tasks)
			future = executor.submit(
				run_node, task["name"],
				self.environment, solved_inputs, task["properties"]
			)
			task["status"] = TaskStatus.RUNNING
			futures_to_task[future] = task

	def __resolve_inputs(self, task, tasks):
		solved = {}
		for key, value in task["inputs"].items():
			depend_task = tasks[value[0]]
			output = depend_task["result"][value[1]]
			for idx in value[2:]:
				output = output[idx]
			solved[key] = output
		return solved