from .node_registry import NodeRegistry

import concurrent.futures
from enum import Enum
import logging
import threading
import copy

import zmq
from tqdm import tqdm

class PreTaskStatus(Enum):
	WAITING = 0
	READY = 1
	SUBMITTED = 2
	EXPLODED = 3

class TaskStatus(Enum):
	QUEUED = 0
	RUNNING = 1
	COMPLETED = 2
	FAILED = 3

class PortStatus(Enum):
	ORIGIN = 0
	UPDATED = 1
	SOLVED = 2

def run_node(task):
	task["status"] = TaskStatus.RUNNING
	return NodeRegistry.dispatch(
		name=task["name"],
		id=task["id"],
		environment=task["environment"],
		inputs=task["inputs"],
		properties=task["properties"]
	)

def zmq_collector(max_workers):
	"""This function collects progress from zmq socket and displays with tqdm progress bars."""
	ctx = zmq.Context()
	subscriber = ctx.socket(zmq.PULL)
	subscriber.bind("ipc://@attpc_flow_zmq")

	# Dictionary to track progress bars for each task: {task_id: (pbar, position)}
	progress_bars = {}
	# Available positions pool (0 to max_workers-1)
	available_positions = list(range(max_workers))
	# Lock for thread-safe position management
	position_lock = threading.Lock()

	while True:
		try:
			msg = subscriber.recv().decode("utf-8").split(",")
			if msg[0] == "-1":
				# logging.debug(f"Received terminal message: {msg}")
				break
			task_id = msg[0]
			percentage = float(msg[1])

			# Create progress bar for new tasks
			if task_id not in progress_bars:
				with position_lock:
					if not available_positions:
						# No available positions, skip creating bar (shouldn't happen with proper max_workers)
						logging.warning(f"No available position for task {task_id}")
						continue
					position = available_positions.pop(0)
				progress_bars[task_id] = (
					tqdm(
						total=100,
						desc=f"Task {task_id}",
						position=position,
						leave=False,
						unit="%",
						bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
					),
					position
				)

			# Update progress bar to the new percentage value
			pbar, _ = progress_bars[task_id]
			current_value = pbar.n
			increment = max(0, min(percentage - current_value, 100 - current_value))
			if increment > 0:
				pbar.update(increment)

			# Close progress bar if task is complete
			if percentage >= 100:
				pbar, position = progress_bars[task_id]
				pbar.close()
				del progress_bars[task_id]
				# Return position to available pool
				with position_lock:
					available_positions.append(position)
					available_positions.sort()  # Keep sorted for consistent ordering

			# logging.debug(f"Received message: Task {task_id} in progress {percentage}%.")
		except zmq.ZMQError as e:
			logging.error(f"ZMQ error: {e}")

	# Close all progress bars
	for pbar, _ in progress_bars.values():
		pbar.close()

def send_terminal_message():
	"""This function sends terminal message to zmq socket."""
	ctx = zmq.Context()
	publisher = ctx.socket(zmq.PUSH)
	publisher.connect("ipc://@attpc_flow_zmq")
	publisher.send(b"-1")
	logging.debug(f"Sent terminal message: {b'-1'}")


class Processor:
	def __init__(self, threads, environment, tasks):
		self.threads = threads
		self.environment = environment
		self.pre_tasks = tasks
		self.tasks = []
		self.task_id = 0
		self.futures_to_task = {}

	def process(self):
		# submit zmq collector in a separate thread
		collector_thread = threading.Thread(target=zmq_collector, args=(self.threads,), daemon=True)
		collector_thread.start()

		self._init_pre_tasks()
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
						task["output"] = result
					except Exception as e:
						# failed
						task["status"] = TaskStatus.FAILED
						logging.error(f"Task {task["id"]} failed: {e}")
					# submit new tasks
					self.__reduce_waiting(task["id"])
					self.__submit_ready_tasks(executor)
		send_terminal_message()
		for task in self.tasks:
			if task["status"] == TaskStatus.COMPLETED:
				print(f"Task {task["id"]} completed with result: {task["output"]}")
			elif task["status"] == TaskStatus.FAILED:
				print(f"Task {task["id"]} failed.")

	def _init_pre_tasks(self):
		for ptask in self.pre_tasks:
			if len(ptask["waiting"]) > 0:
				ptask["status"] = PreTaskStatus.WAITING
			else:
				ptask["status"] = PreTaskStatus.READY
			ptask["waiting_task"] = []
			for port in ptask["inputs"] + ptask["properties"]:
				if port["link_node"] == -1:
					port["status"] = PortStatus.SOLVED
				else:
					port["status"] = PortStatus.ORIGIN


	def _submit_ready_tasks(self, executor):
		for ptask in self.pre_tasks:
			if ptask["status"] != PreTaskStatus.READY:
				continue
			task = {
				"id": self.task_id,
				"name": ptask["name"],
				"environment": self.environment,
				"inputs": ptask["inputs"],
				"properties": ptask["properties"],
				"status": TaskStatus.QUEUED,
			}
			self.task_id += 1
			self.tasks.append(task)
			future = executor.submit(run_node, task)
			self.futures_to_task[future] = task
			self._update_links(ptask["id"], task["id"])

	def _update_links(self, src_ptask_id, task_id):
		for ptask in self.pre_tasks:
			if ptask["status"] != PreTaskStatus.WAITING:
				continue
			if src_ptask_id not in ptask["waiting"]:
				continue
			for port in ptask["inputs"] + ptask["properties"]:
				if port["link_node"] != src_ptask_id:
					continue
				if port["status"] != PortStatus.ORIGIN:
					continue
				port["link_task"] = task_id
				ptask["waiting"].remove(src_ptask_id)
				ptask["waiting_task"].append(task_id)
				port["status"] = PortStatus.UPDATED

	def _reduce_waiting(self, task_id):
		for task in self.pre_tasks:
			if task["status"] != TaskStatus.WAITING:
				continue
			if task_id not in task["waiting_task"]:
				continue
			task["waiting_task"].remove(task_id)
			if not self._solve_links(task_id):
				continue
			if len(task["waiting"]) == 0 and len(task["waiting_task"]) == 0:
				task["status"] = TaskStatus.READY

	def _solve_links(self, task_id):
		outputs = self.tasks[task_id]["outputs"]
		for task in self.pre_tasks:
			if task["status"] != TaskStatus.WAITING:
				continue
			if task_id not in task["waiting_task"]:
				continue
			for idx, port in enumerate(task["inputs"] + task["properties"]):
				if port["status"] != PortStatus.UPDATED:
					continue
				if port["link_task"] != task_id:
					continue
				if idx < len(task["inputs"]):
					port_name = "inputs"
					port_idx = idx
				else:
					port_name = "properties"
					port_idx = idx - len(task["inputs"])
				if port["link_adapt"] == 1:
					self._explode_task(task["id"], port_name, port_idx, outputs[port["link_port"]])
					task["status"] = PreTaskStatus.EXPLODED
					return False
				elif port["link_adapt"] == 0:
					port["value"] = outputs[port["link_port"]]
					port["status"] = PortStatus.SOLVED
				else:
					port["value"] = [outputs[port["link_port"]]]
					port["status"] = PortStatus.SOLVED
		return True

	def _explode_task(self, task_id, port_name, port_idx, outputs):
		pre_task = self.pre_tasks[task_id]
		for output in outputs:
			new_task = pre_task.copy()
			new_task["id"] = len(self.pre_tasks)
			new_task[port_name][port_idx]["value"] = output
			new_task[port_name][port_idx]["status"] = PortStatus.SOLVED
			self.pre_tasks.append(new_task)
		for task in self.pre_tasks:
			if task["status"] != PreTaskStatus.WAITING:
				continue
			if task_id not in task["waiting"]:
				continue
			
			task["waiting"].remove(task["id"])
			self._explode_task(task["id"])


	@classmethod
	def run(cls, threads, environment, tasks):
		cls(threads, environment, tasks).process()