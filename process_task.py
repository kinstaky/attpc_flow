import sys
import json
import os
import logging

from atflow import Processor
import atflow.nodes

# config = {
# 	"version": 0.1,
# 	"workspace_dir": "/data/rcnp2025/attpc_flow",
# 	"last_node_id": 2,
# 	"last_link_id": 1,
# 	"nodes": [
# 		{
# 			"id": 0,
# 			"type": "set_run",
# 			"config": {
# 				"run": [1055, 1056, 1057],
# 			},
# 			"inputs": [],
# 			"outputs": [
# 				{
# 					"type": "ARRAY[INT]",
# 					"link": 0,
# 				}
# 			],
# 		},
# 		{
# 			"id": 1,
# 			"type": "check_graw",
# 			"config": {
# 				"graw_dir": "/data/rcnp2025/graw",
# 			},
# 			"inputs": [
# 				{
# 					"type": "INT",
# 					"link": 0,
# 				}
# 			],
# 			"outputs": []
# 		},
# 	],
# 	"links": [
# 		[0, 0, 0, 1, 0, "INT"]
# 	]
# }

logging.basicConfig(level=logging.DEBUG)

def main():
	# Validate Command Line Arguments
	if len(sys.argv) != 2:
		print("Usage: python script_name.py <config_file.json>")
		print("Example: python main.py my_config.json")
		sys.exit(1)

	config_path = sys.argv[1]

	# Check if file exists
	if not os.path.exists(config_path):
		print(f"Error: File '{config_path}' not found.")
		sys.exit(1)

	# Read and Parse JSON Config
	try:
		with open(config_path, "r") as f:
			config_data = json.load(f)
	except json.JSONDecodeError as e:
		print(f"Error: Failed to parse JSON. {e}")
		sys.exit(1)
	except Exception as e:
		print(f"An unexpected error occurred: {e}")
		sys.exit(1)

	# Extract parameters (with defaults or error checking)
	max_workers = config_data.get("threads", 1)
	environment = config_data.get("environment", {})
	tasks = config_data.get("tasks", [])

	if not tasks:
		print("Warning: No tasks found in configuration file.")
		return

	processor = Processor(
		environment=environment,
		max_workers=max_workers,
	)
	processor.process(tasks)

if __name__ == "__main__":
	main()