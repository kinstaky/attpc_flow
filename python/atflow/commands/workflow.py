from datetime import datetime
import json
import logging
import os
import sys
import threading
import uuid

from ..progress.collector import zmq_collector_tqdm
from ..workflow import Workflow
from ..processor import Processor
from ..progress.progress_store import progress_store
from ..progress.execution_meta import ExecutionMetaManager
from ..utils.launcher import setup_logging, send_terminal_message


def process_workflow(workflow_file, *, verbose=False, dry_run=False):
	"""Process workflow from file with terminal progress bar."""
	# Read workflow first to get workflow ID
	try:
		with open(workflow_file, 'r') as f:
			workflow_data = json.load(f)
		workflow_id = workflow_data.get("name", "workflow").replace(" ", "_")
	except Exception as e:
		print(f"Failed to load workflow file {workflow_file}: {e}")
		sys.exit(1)

	# Create workflow object to get workspace
	workflow = Workflow.model_validate(workflow_data)
	workspace = workflow.workspace

	if dry_run:
		execution_id = str(uuid.uuid4())
		processor = Processor(execution_id=execution_id, workflow=workflow)
		print(f"\nDry run workflow: {workflow_file}")
		print(f"Execution ID: execution_id")
		print(f"Initialized tasks: {len(processor.tasks)}")
		if (verbose):
			print("\nProcessor initialization:")
			print(json.dumps(processor.get_initialization_snapshot(), indent=2))
		print("\nDry run completed. No task was executed.")
		return

	# create execution in progress store
	execution_id = progress_store.create_execution(workflow).execution_id

	# Setup logging
	# Create logs directory if it doesn't exist
	logs_dir = "logs"
	os.makedirs(logs_dir, exist_ok=True)
	# Generate timestamp
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	log_file = f"{logs_dir}/{workflow_id}-{timestamp}-{execution_id}.log"
	setup_logging(
		level=logging.DEBUG if verbose else logging.INFO,
		log_file=log_file
	)
	logger = logging.getLogger(__name__)


	# Create execution meta directory and save workflow.json
	try:
		ExecutionMetaManager.create_execution_meta(
			workspace=workspace,
			execution_id=execution_id,
			workflow=workflow,
			run_mode="workflow",
		)
		logger.info(f"Created execution meta directory: %s/meta/%s", workspace, execution_id)
	except Exception:
		logger.exception("Failed to create execution meta")


	logger.info(f"Loaded workflow from {workflow_file}")
	logger.info(f"Starting workflow execution {execution_id}")
	print(f"\nProcessing workflow: {workflow_file}")
	print(f"Execution ID: {execution_id}")
	print(f"Log file: {log_file}")
	print("-" * 50)

	try:
		processor = Processor(
			execution_id=execution_id,
			workflow=workflow,
		)
		logger.debug("Processor initialization:")
		logger.debug(json.dumps(processor.get_initialization_snapshot(), indent=2))

		# Start zmq collector for tqdm in a thread
		collector_thread = threading.Thread(target=zmq_collector_tqdm)
		collector_thread.start()
		logger.info("Started ZMQ collector for terminal progress bar")

		processor.process()

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
		if execution_status is None:
			raise ValueError(f"Execution {execution_id} not found in progress store")
		ExecutionMetaManager.write_meta(
			workspace=workspace,
			execution_status=execution_status,
			tasks_progress=tasks_progress,
		)
		logger.info(f"Wrote meta for execution {execution_id}")
	except Exception:
		logger.exception(f"Failed to write meta")