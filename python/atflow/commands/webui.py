import logging
import multiprocessing as mp
import threading

from ..progress.collector import zmq_collector_store
from ..processor import Processor
from ..progress.execution_meta import ExecutionMetaManager
from ..progress.progress_store import progress_store
from ..server import run_server, get_workflow_queue
from ..utils.launcher import setup_logging, send_terminal_message

def start_webui(host="0.0.0.0", port=8000, end_point="ipc://@attpc_flow_zmq", verbose=False):
	"""Start complete ATTPC Flow system (server + worker + collector)."""

	# setup logging
	setup_logging(
		level=logging.DEBUG if verbose else logging.INFO
	)
	logger = logging.getLogger(__name__)

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
		workflow_queue = get_workflow_queue()

		collector_thread = threading.Thread(target=zmq_collector_store)
		collector_thread.start()
		threads["collector"] = collector_thread

		# Start worker thread with existing queue
		worker_thread = threading.Thread(target=_workflow_worker, args=(workflow_queue,))
		worker_thread.start()
		threads["worker"] = worker_thread

		# Start server in main process
		run_server(host=host, port=port, reload=False)

	except Exception as e:
		logger.error(f"Unexpected error: {e}")

	send_terminal_message()
	logger.debug("Sent terminal message")
	_shutdown_all()
	logger.info("Full system stopped")