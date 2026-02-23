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
from .progress.execution_meta import ExecutionMetaManager
from .progress.progress_store import ExecutionStatus, TaskProgress, progress_store
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

					workspace = workflow.workspace

					worker_logger.info(f"Processing execution {execution_id}")

					# Create execution meta directory and save workflow.json
					try:
						ExecutionMetaManager.create_execution_meta(
							workspace=workspace,
							execution_id=execution_id,
							workflow=workflow,
							run_mode="ui",
						)
						worker_logger.info(f"Created execution meta directory: {workspace}/meta/{execution_id}")
					except Exception as e:
						worker_logger.error(f"Failed to create execution meta: {e}")

					# Run workflow
					try:
						Processor.run(
							execution_id=execution_id,
							workflow=workflow,
						)
						worker_logger.info(f"Completed execution {execution_id}")
					except Exception as e:
						worker_logger.error(f"Execution {execution_id} failed: {e}")

					try:
						# Get execution status from progress_store
						executions = progress_store.get_executions()
						execution_status = executions.get(execution_id)
						# Get task info from progress store
						tasks_progress = progress_store.get_progress(execution_id)
						if execution_status is None:
							raise ValueError(f"Execution {execution_id} not found in progress store")
						ExecutionMetaManager.write_meta(
							workspace=workspace,
							execution_status=execution_status,
							tasks_progress=tasks_progress,
						)
						worker_logger.info(f"Wrote meta for execution {execution_id}")
					except Exception as e:
						worker_logger.error(f"Failed to write meta: {e}")

				except mp.queues.Empty:
					continue  # Timeout, check again

		except KeyboardInterrupt:
			worker_logger.info("Worker interrupted by KeyboardInterrupt")
		except Exception as e:
			worker_logger.error(f"Worker error: {e}")

		worker_logger.info("Worker stopped")

	try:
		# Initialize server with auto-created queue
		from .server import get_workflow_queue
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

	# Create workflow object to get workspace
	workflow = Workflow.model_validate(workflow_data)
	workspace = workflow.workspace
	# create execution in progress store
	execution_id = progress_store.create_execution(workflow).execution_id

	# Create execution meta directory and save workflow.json
	try:
		ExecutionMetaManager.create_execution_meta(
			workspace=workspace,
			execution_id=execution_id,
			workflow=workflow,
			run_mode="workflow",
		)
		logger.info(f"Created execution meta directory: {workspace}/meta/{execution_id}")
	except Exception as e:
		logger.error(f"Failed to create execution meta: {e}")

	# Create logs directory if it doesn't exist
	logs_dir = "logs"
	os.makedirs(logs_dir, exist_ok=True)

	# Generate timestamp
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	# Format log file name as logs/{workflow_id}-{timestamp}-{execution_id}.log
	log_file = f"{logs_dir}/{workflow_id}-{timestamp}-{execution_id}.log"

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
		execution_status = "failed"
		# Send termination message to collector
		send_terminal_message()
		collector_thread.join(timeout=2)
		logger.error(f"Workflow execution failed: {e}")
		print(f"\nError: Workflow execution failed: {e}")
		print(f"Check {log_file} for detailed logs.")

	# Write to db after execution finishes
	try:
		# Get execution status from progress_store (if available)
		executions = progress_store.get_executions()
		execution_status = executions.get(execution_id)
		tasks_progress = progress_store.get_progress(execution_id)
		print("tasks_progress:", tasks_progress)
		if execution_status is None:
			raise ValueError(f"Execution {execution_id} not found in progress store")
		ExecutionMetaManager.write_meta(
			workspace=workspace,
			execution_status=execution_status,
			tasks_progress=tasks_progress,
		)
		logger.info(f"Wrote meta for execution {execution_id}")
	except Exception as e:
		logger.error(f"Failed to write meta: {e}")


def run_node(node_name, node_args, list_nodes=False):
	"""Run a single node with provided arguments."""
	# Redirect logger output to a file instead of screen
	root_logger = logging.getLogger()
	original_handlers = root_logger.handlers.copy()

	# Create file handler for error logs
	log_file = f"logs/node_{node_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
	os.makedirs("logs", exist_ok=True)
	file_handler = logging.FileHandler(log_file, mode='w')
	file_handler.setFormatter(AlignedFormatter())

	# Clear existing handlers and add only file handler
	root_logger.handlers.clear()
	root_logger.addHandler(file_handler)
	root_logger.setLevel(logging.DEBUG)

	try:
		# Handle list option
		if list_nodes:
			try:
				from .node_manager import NodeManager
				manager = NodeManager()
				all_nodes = manager.list_nodes()
				# Exclude load_run and load_run_list
				excluded_nodes = {'load_run', 'load_run_list'}
				available_nodes = [node for node in all_nodes if node not in excluded_nodes]

				print("Available nodes:")
				for name in sorted(available_nodes):
					print(f"  - {name}")
			except Exception as e:
				print(f"Error: Failed to list nodes: {e}")
			return

		# Check if node_name is provided
		if not node_name:
			print("Error: No node name provided. Use --list to see available nodes.")
			print("Example: atflow node const_int --value 42")
			sys.exit(1)

		# Get node from registry
		try:
			from .node_manager import NodeManager
			manager = NodeManager()
			node = manager.get_node(node_name)
			if not node:
				print(f"Error: Node '{node_name}' not found in registry")
				print("Use --list to see available nodes.")
				sys.exit(1)
		except Exception as e:
			print(f"Error: Failed to get node '{node_name}': {e}")
			sys.exit(1)

		# Parse node-specific arguments using the node's parameter model
		try:
			if node.parameters_model:
				# Create a temporary parser for node parameters
				param_parser = argparse.ArgumentParser()
				for field_name, field_info in node.parameters_model.model_fields.items():
					if field_name == "task_id":
						continue
					elif field_name == "execution_id":
						param_parser.add_argument("--execution_id", required=False, help="Execution ID")
					else:
						param_parser.add_argument(f"--{field_name}", required=field_info.default is None,
										   help=f"Parameter {field_name}")

				param_args = param_parser.parse_args(node_args)
				params = param_args.__dict__
			else:
				params = {}

		except Exception as e:
			print(f"Error parsing node parameters: {e}")
			sys.exit(1)

		# Execute the node
		workspace = params.get("workspace")
		if workspace is None:
			raise ValueError("workspace parameter is required.")

		try:
			started_at = datetime.now().timestamp()

			# Extract parameter values (excluding None values)
			execution_params = {}
			for key, value in params.items():
				if value is not None:
					execution_params[key] = value

			if "execution_id" not in execution_params:
				execution_params["execution_id"] = str(uuid.uuid4())

			execution_id = execution_params["execution_id"]

			print(f"\nLog file: {log_file}")

			# Create execution meta directory (no workflow.json for single node)
			try:
				ExecutionMetaManager.create_execution_meta(
					workspace=workspace,
					execution_id=execution_id,
					workflow="node",  # No workflow for single node execution
					run_mode="node",
				)
				logger.info(f"Created execution meta directory: {workspace}/meta/{execution_id}")
			except Exception as e:
				logger.error(f"Failed to create execution meta: {e}")

			# Execute node
			result = manager.execute_node(
				name=node_name,
				execution_id=execution_id,
				task_id=-1,
				environment={},
				inputs={},
				properties=execution_params
			)
			execution_status = "completed"

			# Print results
			print(f"\nNode '{node_name}' executed successfully!")
			print(f"Parameters: {execution_params}")
			print(f"Result: {result}")

		except Exception as e:
			execution_status = "failed"
			print(f"Error: Failed to execute node '{node_name}': {e}")

		# Write meta after execution finishes
		completed_at = datetime.now().timestamp()
		try:
			# create new ExecutionStatus
			execution_status_obj = ExecutionStatus(
				execution_id=execution_id,
				workflow_id=node_name,
				status=execution_status,
				run_mode="node",
				started_at=started_at,
				completed_at=completed_at,
				total_tasks=0,
				completed_tasks=0,
			)
			tasks_progress = {
				"-1": TaskProgress(
					task_id="-1",
					task_name=node_name,
					run=execution_params.get("run", None),
					percentage=100,
					status=execution_status,
				)
			}
			ExecutionMetaManager.write_meta(
				workspace=workspace,
				execution_status=execution_status_obj,
				tasks_progress=tasks_progress,
			)
		except Exception as e:
			logger.error(f"Failed to write meta: {e}")

	finally:
		# Close file handler and restore original logger handlers
		file_handler.close()
		root_logger.handlers = original_handlers


def main():
	"""Main entry point for command line interface."""
	parser = argparse.ArgumentParser(description="ATTPC Flow launcher")
	parser.add_argument("--dev", action="store_true", help="Start development servers with hot reload")
	parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
	parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

	subparsers = parser.add_subparsers(dest='command', help='Available commands')

	# Workflow command
	workflow_parser = subparsers.add_parser('workflow', help='Run a workflow from file')
	workflow_parser.add_argument("workflow_file", help="Path to workflow file")

	# Node command
	node_parser = subparsers.add_parser('node', help='Run a single node')
	node_parser.add_argument("name", nargs='?', help="Name of the node to run")
	node_parser.add_argument('--list', '-l', action='store_true', help='List available nodes')
	node_parser.add_argument('node_args', nargs=argparse.REMAINDER,
						   help='Arguments to pass to the node (e.g., --value 42)')

	args = parser.parse_args()

	if args.command == 'workflow':
		process_workflow(args.workflow_file)
	elif args.command == 'node':
		run_node(args.name, args.node_args, args.list)
	elif args.dev:
		start_dev_servers(host=args.host, port=args.port)
	else:
		# Default behavior - start full system
		start_full_system(host=args.host, port=args.port)
