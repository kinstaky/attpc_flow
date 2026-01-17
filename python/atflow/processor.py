from .node_registry import NodeRegistry

import concurrent.futures
from enum import Enum
import logging
import threading

import zmq
from tqdm import tqdm


class TaskStatus(Enum):
	WAITING = 0
	READY = 1
	RUNNING = 2
	COMPLETED = 3
	FAILED = 4

def run_node(name, task_id, environment, inputs, properties):
	return NodeRegistry.dispatch(name, task_id, environment, inputs, properties)

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
	def __init__(self, max_workers=2, environment={}):
		self.max_workers = max_workers
		self.environment = environment

	def process(self, tasks):
		# submit zmq collector in a separate thread
		collector_thread = threading.Thread(target=zmq_collector, args=(self.max_workers,), daemon=True)
		collector_thread.start()
		# submit node tasks
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
					except Exception as e:
						# failed
						task["status"] = TaskStatus.FAILED
						logging.error(f"Task {task['id']} failed: {e}")
					# submit new tasks
					self.__reduce_waiting(tasks, task["id"])
					self.__submit_ready_tasks(tasks, executor, futures_to_task)
		send_terminal_message()
		for task in tasks:
			if task["status"] == TaskStatus.COMPLETED:
				print(f"Task {task['id']} completed with result: {task['result']}")
			elif task["status"] == TaskStatus.FAILED:
				print(f"Task {task['id']} failed.")

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
				run_node, task["name"], task["id"],
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