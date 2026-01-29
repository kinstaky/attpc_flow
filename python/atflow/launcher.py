"""
Simple launcher functions for ATTPC Flow.
Lightweight alternative to the manager class.
"""

import multiprocessing as mp
import signal
import sys
import threading
import logging
import zmq

from .processor import Processor
from .collector import zmq_collector_tqdm, zmq_collector_store

# Configure ONE global colorful handler for all processes
import colorlog
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
	'%(log_color)s%(levelname)s:%(reset)s     %(message)s',
	log_colors={
		'DEBUG': 'cyan',
		'INFO': 'green',
		'WARNING': 'yellow',
		'ERROR': 'red',
		'CRITICAL': 'magenta',
	}
))

logging.basicConfig(
	level=logging.INFO,
	handlers=[handler],
	force=True  # Override any existing config
)

# Get logger that will use the global colorful handler
logger = logging.getLogger(__name__)

def send_terminal_message():
	"""This function sends terminal message to zmq socket."""
	ctx = zmq.Context()
	publisher = ctx.socket(zmq.PUSH)
	publisher.connect("ipc://@attpc_flow_zmq")
	publisher.send(b"-1")
	logger.debug(f"Sent terminal message: {b'-1'}")

def start_server(host="0.0.0.0", port=8000):
	"""Start ATTPC Flow server only."""
	from .server import run_server
	logger.info(f"Starting ATTPC Flow server on http://{host}:{port}")
	run_server(host=host, port=port)

def start_worker():
	"""Start worker process only."""
	logger.info("Starting ATTPC Flow worker")
	workflow_queue = mp.Queue()
	_workflow_worker(workflow_queue)

def start_full_system(host="0.0.0.0", port=8000):
	"""Start complete ATTPC Flow system (server + worker + collector)."""

	logger.info(f"Starting ATTPC Flow full system on http://{host}:{port}")

	# Local state for cleanup
	processes = {}
	threads = {}
	workflow_queue = None

	def _shutdown_all():
		"""Cleanup function."""
		# Send poison pill to worker
		if workflow_queue:
			try:
				workflow_queue.put(None)
			except:
				pass

		logger.debug("Shutting down worker")
		# Wait for worker
		if "worker" in processes:
			worker = processes["worker"]
			if worker.is_alive():
				worker.join(timeout=2)
				if worker.is_alive():
					worker.terminate()

		logger.debug("Shutting down threads")
		# Don't wait for daemon threads - they'll be killed automatically
		for name, thread in threads.items():
			if thread.is_alive() and not thread.daemon:
				try:
					thread.join(timeout=1)
				except:
					pass

	def _workflow_worker(queue: mp.Queue):
		"""Worker process."""
		# Use the global handler configured by basicConfig
		worker_logger = logging.getLogger(__name__)
		worker_logger.info("Worker started")
		try:
			while True:
				try:
					workflow_data = queue.get(timeout=1)  # Add timeout
					if workflow_data is None:
						break

					execution_id = workflow_data.execution_id
					worker_logger.info(f"Processing execution {execution_id}")

					# Update execution status
					from .server import executions
					from datetime import datetime, timezone

					if execution_id in executions:
						executions[execution_id].started_at = datetime.now(timezone.utc).isoformat()
						executions[execution_id].status = "running"

					# Run workflow
					Processor.run(
						threads=workflow_data.threads,
						environment={
							"execution_id": execution_id,
							"workspace": workflow_data.workspace,
							"run_list": workflow_data.run_list,
						},
						tasks=workflow_data.tasks
					)

					# Update status
					if execution_id in executions:
						executions[execution_id].status = "completed"
						executions[execution_id].completed_at = datetime.now(timezone.utc).isoformat()
					worker_logger.info(f"Completed execution {execution_id}")

				except mp.queues.Empty:
					continue  # Timeout, check again

		except KeyboardInterrupt:
			worker_logger.info("Worker interrupted by KeyboardInterrupt")
		except Exception as e:
			worker_logger.error(f"Worker error: {e}")

		worker_logger.info("Worker stopped")

	try:
		# Create workflow queue
		workflow_queue = mp.Queue()

		# Initialize server
		from .server import init_workflow_queue
		init_workflow_queue(workflow_queue)

		collector_thread = threading.Thread(target=zmq_collector_store)
		collector_thread.start()
		threads["collector"] = collector_thread

		# Start worker process
		worker_process = mp.Process(target=_workflow_worker, args=(workflow_queue,))
		worker_process.start()
		processes["worker"] = worker_process

		# Start server in main process
		from .server import run_server
		run_server(host=host, port=port)

	except Exception as e:
		logger.error(f"Unexpected error: {e}")

	send_terminal_message()
	_shutdown_all()
	logger.info("Full system stopped")

# Convenience function for most common use case
def launch(host="0.0.0.0", port=8000):
	"""Launch ATTPC Flow with web UI (most common usage)."""
	start_full_system(host=host, port=port)
