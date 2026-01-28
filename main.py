#!/usr/bin/env python3
"""
Main entry point for ATTPC Flow application.
Manages FastAPI server and workflow processing.
"""

import multiprocessing as mp
import signal
import sys
import logging
from multiprocessing import Queue
from pathlib import Path

# Add python directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "python"))

from atflow import Processor
import atflow.nodes
from server import app, executions, ExecutionStatus, init_workflow_queue
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global queue for workflow distribution
workflow_queue: Queue = None

def workflow_worker(queue: Queue):
	"""Worker process that consumes workflows from the queue and processes them using the existing Processor."""
	logger.info("Worker started")

	try:
		while True:
			try:
				workflow_data = queue.get()
				if workflow_data is None:  # Poison pill to stop worker
					logger.info("Worker received shutdown signal")
					break

				execution_id = workflow_data.execution_id
				logger.info(f"Worker processing execution {execution_id}")

				# Update status to running
				if execution_id in executions:
					executions[execution_id].started_at = datetime.now(timezone.utc+8).isoformat()
					executions[execution_id].status = "running"

				# TODO: implement translate workflow to tasks
				print(workflow_data.model_dump_json(indent=2))

				# # Convert workflow dict to tasks format for Processor
				# tasks, max_workers, environment = translate_workflow(workflow_dict)

				# # TODO: implement the workflow processing
				# print(f"Max workers: {max_workers}")
				# print(f"Environment: {environment}")
				# print(tasks)

				# # Use existing Processor class (it handles its own multiprocessing)
				# processor = Processor(
				# 	max_workers=max_workers,
				# 	environment=environment
				# )
				# processor.process(tasks)

				# Update status to completed
				if execution_id in executions:
					executions[execution_id].status = "completed"
					executions[execution_id].completed_at = datetime.now(timezone.utc+8).isoformat()
				logger.info(f"Worker completed execution {execution_id}")

			except Exception as e:
				# Update status to failed
				if 'execution_id' in locals() and execution_id in executions:
					executions[execution_id].status = "failed"
				logger.error(f"Worker failed to process workflow: {e}")

	except KeyboardInterrupt:
		logger.info("Worker interrupted")
	finally:
		logger.info("Worker shutting down")

# def translate_workflow(workflow: dict):
# 	"""Convert Workflow model to tasks format expected by Processor."""
# 	tasks = []

# 	for node in workflow["nodes"]:
# 		task = {
# 			"id": None,
# 			"node_id": node["id"],
# 			"name": node["name"],
# 			"inputs": {},
# 			"properties": 
# 		}



# def translate_workflow_to_tasks(workflow_dict: dict) -> list:
# 	"""Convert Workflow model to tasks format expected by Processor."""
# 	tasks = []

# 	# Convert nodes to tasks
# 	for node in workflow_dict['nodes']:
# 		task = {
# 			'id': node['id'],
# 			'name': node['name'],
# 			'inputs': {},  # Will be populated from links
# 			'properties': {prop['key']: prop['value'] for prop in node.get('properties', [])},
# 			'waiting': 0,
# 			'status': None
# 		}
# 		tasks.append(task)

# 	# Process links to set up inputs and waiting counts
# 	for link in workflow_dict['links']:
# 		target_task = next((t for t in tasks if t['id'] == link['target']), None)
# 		if target_task:
# 			target_task['inputs'][link['targetHandle']] = [link['source'], link['sourceHandle']]
# 			target_task['waiting'] += 1

# 	return tasks

def run_server():
	"""Run the FastAPI server."""
	import uvicorn

	logger.info("Starting FastAPI server...")
	logger.info("API documentation available at: http://localhost:8000/docs")

	uvicorn.run(
		app,
		host="0.0.0.0",
		port=8000,
		reload=False,  # Disable reload when running with workers
		log_level="info"
	)

def signal_handler(signum, frame):
	"""Handle shutdown signals."""
	logger.info("Received shutdown signal, cleaning up...")

	# Send poison pills to all workers
	if workflow_queue:
		num_workers = mp.cpu_count() or 2
		for _ in range(num_workers):
			workflow_queue.put(None)

	sys.exit(0)

def main():
	"""Main entry point that starts both server and workers."""
	global workflow_queue

	# Set up signal handlers
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	# Create workflow queue
	workflow_queue = mp.Queue()

	# Initialize the queue in server module
	init_workflow_queue(workflow_queue)

	worker = mp.Process(target=workflow_worker, args=(workflow_queue,))
	worker.start()

	try:
		# Start server in main process
		run_server()
	except KeyboardInterrupt:
		logger.info("Server interrupted")
	finally:
		# Clean up workers
		logger.info("Shutting down workers...")
		workflow_queue.put(None)  # Poison pill

		# Wait for workers to finish
		worker.join(timeout=5)
		if worker.is_alive():
			logger.warning("Worker process did not shut down gracefully, terminating...")
			worker.terminate()

		logger.info("Worker shut down")

if __name__ == "__main__":
	main()
