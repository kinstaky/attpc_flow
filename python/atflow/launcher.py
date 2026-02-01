"""
Simple launcher functions for ATTPC Flow.
Lightweight alternative to the manager class.
"""

import multiprocessing as mp
import threading
import logging
import zmq
import subprocess
import os
import argparse

from .processor import Processor
from .collector import zmq_collector_tqdm, zmq_collector_store
from .nodes import *

# Configure ONE global colorful handler for all processes
import colorlog

class AlignedFormatter(logging.Formatter):
    """Custom formatter that aligns all log levels perfectly with colors."""

    def __init__(self, log_colors=None):
        super().__init__()
        self.log_colors = log_colors or {}
        self.color_codes = {
            'DEBUG': '\033[36m',    # cyan
            'INFO': '\033[32m',     # green
            'WARNING': '\033[33m',  # yellow
            'ERROR': '\033[31m',    # red
            'CRITICAL': '\033[35m', # magenta
        }
        self.reset_code = '\033[0m'

    def format(self, record):
        level_name = record.levelname

        # Apply colors
        color = self.color_codes.get(level_name, '')
        reset = self.reset_code if color else ''

        # Normalize all levels to match uvicorn's format exactly
        if level_name == 'INFO':
            level_display = f"{color}INFO{reset}:     "
        elif level_name == 'DEBUG':
            level_display = f"{color}DEBUG{reset}:    "
        elif level_name == 'ERROR':
            level_display = f"{color}ERROR{reset}:    "
        elif level_name == 'WARNING':
            level_display = f"{color}WARNING{reset}:  "
        elif level_name == 'CRITICAL':
            level_display = f"{color}CRITICAL{reset}: "
        else:
            level_display = f"{color}{level_name}{reset}:"

        message = record.getMessage()
        return f"{level_display}{message}"

handler = logging.StreamHandler()
formatter = AlignedFormatter()
formatter.ALIGN = True
handler.setFormatter(formatter)

logging.basicConfig(
	level=logging.DEBUG,
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
	publisher.send_string("termination")
	logger.debug("Sent terminal message: termination")

def start_server(host="0.0.0.0", port=8000, reload=False):
	"""Start ATTPC Flow server only."""
	from .server import run_server
	logger.info(f"Starting ATTPC Flow server on http://{host}:{port}")
	run_server(host=host, port=port, reload=reload)

def start_worker():
	"""Start worker process only."""
	logger.info("Starting ATTPC Flow worker")
	workflow_queue = mp.Queue()
	_workflow_worker(workflow_queue)

def start_full_system(host="0.0.0.0", port=8000, reload=False):
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
		for _name, thread in threads.items():
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
		from .progress_store import init_workflow_queue
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
		run_server(host=host, port=port, reload=reload)

	except Exception as e:
		logger.error(f"Unexpected error: {e}")

	send_terminal_message()
	_shutdown_all()
	logger.info("Full system stopped")

def start_dev_servers(host="0.0.0.0", port=8000):
	"""Start both frontend and backend with hot reload for development."""
	logger.info("Starting ATTPC Flow development servers...")
	logger.info(f"Backend will be available at http://{host}:{port}")
	logger.info("Frontend will be available at http://localhost:3000")

	# Get project root directory
	project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
	frontend_dir = os.path.join(project_root, "frontend")

	try:
		# Start backend with uvicorn reload by calling start_server directly
		logger.info("Starting FastAPI backend with hot reload...")
		backend_proc = mp.Process(
			target=start_full_system,
			kwargs={"host": host, "port": port, "reload": True}
		)
		backend_proc.start()

		# Start frontend with Vite
		logger.info("Starting Vite frontend with hot reload...")
		frontend_cmd = ["pnpm", "dev", "--host"]
		frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir)

		# Wait for processes
		try:
			backend_proc.join()
			frontend_proc.wait()
		except KeyboardInterrupt:
			logger.info("Received interrupt signal, shutting down development servers...")
			backend_proc.terminate()
			frontend_proc.terminate()
			backend_proc.join()
			frontend_proc.wait()
			logger.info("Development servers stopped")

	except Exception as e:
		logger.error(f"Failed to start development servers: {e}")

# Convenience function for most common use case
def launch(host="0.0.0.0", port=8000, dev=False):
	"""Launch ATTPC Flow with web UI (most common usage)."""
	if dev:
		start_dev_servers(host=host, port=port)
	else:
		start_full_system(host=host, port=port)

def main():
	"""Main entry point for command line interface."""
	parser = argparse.ArgumentParser(description="ATTPC Flow launcher")
	parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
	parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
	parser.add_argument("--dev", action="store_true", help="Start development servers with hot reload")

	args = parser.parse_args()

	if args.dev:
		start_dev_servers(host=args.host, port=args.port)
	else:
		start_full_system(host=args.host, port=args.port)
