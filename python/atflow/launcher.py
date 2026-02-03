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
import json
import sys
import uuid
from datetime import datetime

from .processor import Processor
from .progress.collector import zmq_collector_tqdm, zmq_collector_store
from .nodes import *
from .workflow import Workflow

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
	"""Start worker thread only."""
	logger.info("Starting ATTPC Flow worker")
	workflow_queue = mp.Queue()
	worker_thread = threading.Thread(target=_workflow_worker, args=(workflow_queue,))
	worker_thread.start()

def start_full_system(host="0.0.0.0", port=8000, reload=False):
	"""Start complete ATTPC Flow system (server + worker + collector)."""

	# Local state for cleanup
	threads = {}
	workflow_queue = None

	def _shutdown_all():
		"""Cleanup function."""
		# Send poison pill to worker
		if workflow_queue:
			try:
				workflow_queue.put((None, None))
			except:
				pass

		# logger.debug("Shutting down worker")
		# # Wait for worker thread
		# if "worker" in threads:
		# 	worker = threads["worker"]
		# 	if worker.is_alive():
		# 		worker.join(timeout=2)

		logger.debug("Shutting down threads")
		# Don't wait for daemon threads - they'll be killed automatically
		for _name, thread in threads.items():
			if thread.is_alive() and not thread.daemon:
				try:
					thread.join(timeout=1)
				except:
					pass

	def _workflow_worker(queue: mp.Queue):
		"""Worker thread."""
		# Use the global handler configured by basicConfig
		worker_logger = logging.getLogger(__name__)
		worker_logger.info("Worker started")
		try:
			while True:
				try:
					execution_id, workflow = queue.get(timeout=1)  # Add timeout
					if workflow is None:
						break

					worker_logger.info(f"Processing execution {execution_id}")

					# Run workflow
					Processor.run(
						execution_id=execution_id,
						workflow=workflow,
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
		# Initialize server with auto-created queue
		from .progress.progress_store import get_workflow_queue
		workflow_queue = get_workflow_queue()

		collector_thread = threading.Thread(target=zmq_collector_store)
		collector_thread.start()
		threads["collector"] = collector_thread

		# Start worker thread with existing queue
		worker_thread = threading.Thread(target=_workflow_worker, args=(workflow_queue,))
		worker_thread.start()
		threads["worker"] = worker_thread

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

	# Get project root directory
	project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
	frontend_dir = os.path.join(project_root, "frontend")

	try:
		# Start frontend with Vite first, capturing output
		logger.info("Starting Vite frontend with hot reload...")
		frontend_cmd = ["pnpm", "dev", "--host"]
		frontend_proc = subprocess.Popen(
			frontend_cmd,
			cwd=frontend_dir,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			universal_newlines=True,
			bufsize=1
		)

		# Start backend directly in main process for visible logs
		logger.info("Starting FastAPI backend with hot reload...")

		# Store original print function
		original_print = print

		# Add prefix to backend logs
		import builtins
		def prefixed_print(*args, **kwargs):
			original_print("[BACKEND] ", end='')
			original_print(*args, **kwargs)

		# Temporarily replace print for backend logs
		builtins.print = prefixed_print

		# Function to read and prefix frontend logs
		def read_frontend_output():
			for line in iter(frontend_proc.stdout.readline, ''):
				if line:
					# Use original print to avoid backend prefix
					original_print(f"[FRONTEND] {line}", end='')

		# Start thread to read frontend output
		import threading
		frontend_thread = threading.Thread(target=read_frontend_output)
		frontend_thread.start()

		try:
			# Run backend in main process so logs are visible
			start_full_system(host=host, port=port, reload=False)
		finally:
			# Restore original print
			builtins.print = original_print

		# Wait for processes
		try:
			# Backend runs in main process, so just wait for frontend
			frontend_proc.wait()
		except KeyboardInterrupt:
			logger.info("Received interrupt signal, shutting down development servers...")
			frontend_proc.terminate()
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

def process_workflow(workflow_file):
	"""Process workflow from file with terminal progress bar."""
	# Read workflow first to get workflow ID
	try:
		with open(workflow_file, 'r') as f:
			workflow_data = json.load(f)
		workflow_id = workflow_data.get("name", "workflow").replace(" ", "_")
	except Exception as e:
		print(f"Error: Failed to load workflow file: {e}")
		sys.exit(1)

	# Generate timestamp and execution ID
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	execution_id = str(uuid.uuid4())

	# Create logs directory if it doesn't exist
	logs_dir = "logs"
	os.makedirs(logs_dir, exist_ok=True)

	# Format log file name as logs/{workflow_id}-{timestamp}-{execution_id}.txt
	log_file = f"{logs_dir}/{workflow_id}-{timestamp}-{execution_id}.txt"

	# Configure logging to file
	file_handler = logging.FileHandler(log_file, mode='w')
	file_handler.setFormatter(AlignedFormatter())

	# Get the root logger and redirect all handlers to file
	root_logger = logging.getLogger()
	# Remove existing handlers
	for handler in root_logger.handlers[:]:
		root_logger.removeHandler(handler)
	# Add file handler
	root_logger.addHandler(file_handler)
	root_logger.setLevel(logging.DEBUG)

	logger.info(f"Loaded workflow from {workflow_file}")
	logger.info(f"Starting workflow execution {execution_id}")
	print(f"\nProcessing workflow: {workflow_file}")
	print(f"Execution ID: {execution_id}")
	print(f"Log file: {log_file}")
	print("-" * 50)

	try:
		# Start zmq collector for tqdm in a thread
		collector_thread = threading.Thread(target=zmq_collector_tqdm)
		collector_thread.start()
		logger.info("Started ZMQ collector for terminal progress bar")

		# Create workflow object
		workflow = Workflow.model_validate(workflow_data)

		# Use the Processor.run class method
		Processor.run(
			execution_id=execution_id,
			workflow=workflow,
		)

		# Send termination message to collector
		send_terminal_message()
		collector_thread.join(timeout=2)

		logger.info(f"Completed workflow execution {execution_id}")
		print("\n" + "-" * 50)
		print("Workflow completed successfully!")
		print(f"Check {log_file} for detailed logs.")

	except Exception as e:
		# Send termination message to collector
		send_terminal_message()
		collector_thread.join(timeout=2)
		logger.error(f"Workflow execution failed: {e}")
		print(f"\nError: Workflow execution failed: {e}")
		print(f"Check {log_file} for detailed logs.")


def main():
	"""Main entry point for command line interface."""
	parser = argparse.ArgumentParser(description="ATTPC Flow launcher")
	parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
	parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
	parser.add_argument("--dev", action="store_true", help="Start development servers with hot reload")
	parser.add_argument("--workflow", help="Read workflow from file and run it.")

	args = parser.parse_args()

	if args.workflow:
		process_workflow(args.workflow)
	elif args.dev:
		start_dev_servers(host=args.host, port=args.port)
	else:
		start_full_system(host=args.host, port=args.port)
