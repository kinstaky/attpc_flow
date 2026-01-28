from .node_registry import NodeRegistry

import concurrent.futures
from enum import Enum
import logging
import threading
import copy

import zmq
from tqdm import tqdm


class TaskStatus(Enum):
	DISCARDED = -2
	FAILED = -1
	COMPLETED = 0
	WAITING = 1
	READY = 2
	QUEUED = 3
	RUNNING = 4

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
		self._init_tasks()
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
					self._reduce_waiting(task["id"])
					self._submit_ready_tasks(executor)
		send_terminal_message()
		for task in self.tasks:
			if task["status"] == TaskStatus.COMPLETED:
				print(f"Task {task["id"]} completed with result: {task["output"]}")
			elif task["status"] == TaskStatus.FAILED:
				print(f"Task {task["id"]} failed.")

	def _init_tasks(self):
		offset = 0
		for run in self.environment["run_list"]:
			for task in self.tasks:
				copy_task = task.copy()
				copy_task["id"] += offset
				copy_task["environment"] = self.environment
				copy_task["environment"]["run"] = run
				copy_task["ports"] = []
				copy_task["inputs"] = {}
				copy_task["properties"] = {}
				for port in copy_task["inputs"]:
					port["port"] = "inputs"
					if port["link_task"] != -1:
						port["link_task"] += offset
					else:
						port["inputs"][port["name"]] = port["value"]
					copy_task["ports"].append(port)
				for port in copy_task["properties"]:
					port["port"] = "properties"
					if port["link_task"] != -1:
						port["link_task"] += offset
					else:
						port["inputs"][port["name"]] = port["value"]
					copy_task["ports"].append(port)
				copy_task["waiting"] = []
				for id in task["waiting"]:
					copy_task["waiting"].append(id + offset)
				if len(copy_task["waiting"]) == 0:
					copy_task["status"] = TaskStatus.READY
				else:
					copy_task["status"] = TaskStatus.WAITING
				self.tasks.append(copy_task)
			offset += len(self.tasks)

	def _submit_ready_tasks(self, executor):
		for task in self.tasks:
			if task["status"] != TaskStatus.READY:
				continue
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
				port[port["port"]][port["name"]] = outputs[port["link_port"]]

	def _chain_discard(self, task_id):
		for task in self.tasks:
			if task["status"] == TaskStatus.WAITING and task_id in task["waiting"]:
				task["status"] = TaskStatus.DISCARDED
				self._chain_discard(task["id"])

	@classmethod
	def run(cls, threads, environment, tasks):
		cls(threads, environment, tasks).process()