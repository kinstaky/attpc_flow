import argparse
from datetime import datetime
import logging
import os
import sys
import uuid

from ..node_manager import NodeManager
from ..progress.execution_meta import ExecutionMetaManager
from ..progress.progress_store import ExecutionStatus, TaskProgress
from ..utils.launcher import setup_logging

def run_node(node_name, node_args, verbose=False, list_nodes=False):
	"""Run a single node with provided arguments."""

	# Handle list option
	if list_nodes:
		try:
			manager = NodeManager()
			manager.discover_nodes()
			# Exclude nodes except instant type and batch type
			node_names = [
				name for name in manager.list_nodes()
				if manager.get_node(name).type() in ["instant", "batch"]
			]

			nodes_by_category = {}
			for name in node_names:
				node = manager.get_node(name)
				category = node.category() if node else "uncategorized"
				nodes_by_category.setdefault(category, []).append(name)

			print("Available nodes by category:")
			for category in sorted(nodes_by_category):
				print(f"  {category}:")
				for name in sorted(nodes_by_category[category]):
					print(f"    - {name}")
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
		manager = NodeManager()
		manager.discover_nodes()
		node = manager.get_node(node_name)
		if not node:
			print(f"Error: Node '{node_name}' not found in registry")
			print("Use --list to see available nodes.")
			sys.exit(1)
		if node.type() != "instant" and node.type() != "batch":
			print(f"Error: Node '{node_name}' is not an instant or batch node.")
			print("Use --list to see available nodes.")
			sys.exit(1)
	except Exception as e:
		print(f"Error: Failed to get node '{node_name}': {e}")
		sys.exit(1)

	# Parse node-specific arguments using the node's parameter model
	try:
		if node.parameters_model():
			# Create a temporary parser for node parameters
			param_parser = argparse.ArgumentParser()
			for field_name, field_info in node.parameters_model().model_fields.items():
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
	try:
		workspace = params.get("workspace")
		if workspace is None:
			raise ValueError("workspace parameter is required.")
	except Exception as e:
		print(f"Error: workspace parameter is required: {e}")
		sys.exit(1)

	# create logger
	os.makedirs("logs", exist_ok=True)
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	log_file = f"logs/node-{node_name}-{timestamp}.log"
	setup_logging(
		level=logging.DEBUG if verbose else logging.INFO,
		log_file=log_file
	)
	logger = logging.getLogger(__name__)
	print(f"\nLog file: {log_file}")

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
			parameters=execution_params
		)
		execution_status = "completed"

		# Print results
		print(f"\nNode '{node_name}' executed successfully!")
		print(f"Parameters: {execution_params}")
		print(f"Result: {result}")

	except Exception as e:
		execution_status = "failed"
		print(f"Error: Failed to execute node '{node_name}': {e}")
		logger.error(f"Error: Failed to execute node '{node_name}': {e}")

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