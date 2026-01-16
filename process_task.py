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

tasks = [
	{
		"name": "const_int",
		"id": 0,
		"inputs": {},
		"outputs": [[(1, "run"), (2, "run"), (3, "run")]],
		"properties": {
			"value": [1055, 1056, 1057],
		},
		"waiting": 0,
	},
	{
		"name": "check_graw_event_id",
		"id": 1,
		"inputs": {
			"run": (0, 0, 0)
		},
		"outputs": [],
		"properties": {
			"graw_dir": "/data/rcnp2025/graw",
		},
		"waiting": 1,
	},
	{
		"name": "check_graw_event_id",
		"id": 2,
		"inputs": {
			"run": (0, 0, 1)
		},
		"outputs": [],
		"properties": {
			"graw_dir": "/data/rcnp2025/graw",
		},
		"waiting": 1,
	},
	{
		"name": "check_graw_event_id",
		"id": 3,
		"inputs": {
			"run": (0, 0, 2)
		},
		"outputs": [],
		"properties": {
			"graw_dir": "/data/rcnp2025/graw",
		},
		"waiting": 1,
	},
]

workspace_dir = "/data/rcnp2025/attpc_flow"

if __name__ == "__main__":
	processor = Processor(
		environment={
			"workspace_dir": workspace_dir,
		},
		max_workers=2,
	)
	processor.process(tasks)
