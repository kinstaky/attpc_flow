#!/usr/bin/env python3
"""
FastAPI server for ATTPC Flow workflow management.
Provides RESTful API for node registry and workflow operations.
"""

import asyncio
import logging
import json
import uvicorn
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from pathlib import Path

from atflow.node_registry import NodeRegistry
from atflow.nodes import *  # Import all nodes to register them
from atflow.progress.progress_store import (
    progress_store,
    ExecutionStatus,
)
from .workflow import Workflow

app = FastAPI(
	title="ATTPC Flow API",
	description="Workflow management API for AT-TPC analysis",
	version="0.1.0"
)

# Enable CORS for frontend development
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # In production, specify actual origins
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Mount static files for frontend
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

def to_camel(string: str) -> str:
	return ''.join(word.capitalize() for word in string.split('_'))

def to_lower_camel(s: str) -> str:
	parts = s.split("_")
	return parts[0] + "".join(word.capitalize() for word in parts[1:])

# Data models
class SimpleNodeResponse(BaseModel):
	name: str
	category: str

class NodeResponse(BaseModel):
	name: str
	category: str
	inputs: Optional[Dict[str, str]] = None
	outputs: Optional[Dict[str, str]] = None
	properties: Optional[Dict[str, str]] = None
	parameters: Optional[Dict[str, str]] = None

# Storage
WORKFLOWS_DIR = Path("workflows")
WORKFLOWS_DIR.mkdir(exist_ok=True)

# WebSocket manager for progress broadcasting
class WebSocketManager:
	def __init__(self):
		self.active_connections: List[WebSocket] = []
		self.loop = None  # Will be set when server starts

	async def connect(self, websocket: WebSocket):
		await websocket.accept()
		self.active_connections.append(websocket)

		# Store the event loop for this connection
		if self.loop is None:
			self.loop = asyncio.get_running_loop()

		# Register callback with progress store
		def progress_callback(message: dict):
			# Send message to this specific websocket
			try:
				if self.loop and not self.loop.is_closed():
					# Use run_coroutine_threadsafe for thread-safe async execution
					asyncio.run_coroutine_threadsafe(websocket.send_json(message), self.loop)
			except Exception as e:
				logging.error(f"Failed to send WebSocket message: {e}")
				# Remove this connection from active connections
				self.disconnect(websocket)

		progress_store.register_websocket_callback(progress_callback)

	def disconnect(self, websocket: WebSocket):
		try:
			self.active_connections.remove(websocket)
		except ValueError:
			pass  # Connection already removed

		# Unregister callback from progress store
		# Note: We don't have the callback reference, so cleanup happens automatically
		# when callbacks fail in progress_callback function

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

# Helper functions
def translate_type(python_type: str) -> str:
	type_mapping = {
		"integer": "int",
		"string": "str",
		"float": "float",
		"boolean": "bool"
	}
	return type_mapping.get(python_type)

def get_node_schema(pydantic_class) -> Optional[Dict[str, Any]]:
	"""Extract JSON schema from Pydantic model."""
	if pydantic_class is None:
		return None
	try:
		schema = pydantic_class.model_json_schema()
		return {
			key: (
				translate_type(value["items"]["type"]) + "[]"
				if value["type"] == "array"
				else translate_type(value["type"])
			)
			for key, value in schema["properties"].items()
		}
	except Exception:
		return None

def organize_nodes_by_category() -> Dict[str, List[str]]:
	"""Organize registered nodes by their Python module directory."""
	categories = {}

	for name, entry in NodeRegistry._registry.items():
		# Determine category from node class module
		module_name = entry.node_class.__module__
		category = module_name.split('.')[-1]
		if category not in categories:
			categories[category] = []

		# Add just the node name
		categories[category].append(name)

	return categories

# API Endpoints
@app.get("/")
async def root():
	"""Serve the frontend index.html."""
	try:
		return FileResponse("frontend/dist/index.html")
	except FileNotFoundError:
		return {
			"message": "ATTPC Flow API",
			"version": "0.1.0",
			"docs": "/docs",
			"nodes": "/nodes",
			"workflows": "/workflows",
			"note": "Frontend not built. Run 'npm run build' in frontend directory."
		}

@app.get("/api")
async def api_info():
	"""API information endpoint."""
	return {
		"message": "ATTPC Flow API",
		"version": "0.1.0",
		"docs": "/docs",
		"nodes": "/nodes",
		"workflows": "/workflows"
	}

@app.get("/nodes", response_model=Dict[str, List[str]])
async def list_nodes():
	"""Get all available node names organized by category."""
	try:
		return organize_nodes_by_category()
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get nodes: {str(e)}")

@app.get("/nodes/{node_name}", response_model=NodeResponse)
async def get_node(node_name: str):
	"""Get specific node information."""
	try:
		entry = NodeRegistry._registry.get(node_name)
		if not entry:
			raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")

		info = entry.info
		module_name = entry.node_class.__module__
		category = module_name.split('.')[-1]

		return NodeResponse(
			name=node_name,
			category=category,
			inputs=info.inputs,
			outputs=info.outputs,
			properties=info.properties,
			parameters=get_node_schema(info.parameters),
		)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get node: {str(e)}")

@app.get("/nodes_dev/{node_name}", response_model=Dict[Any, Any])
async def get_dev_node(node_name: str):
	try:
		entry = NodeRegistry._registry.get(node_name)
		if not entry:
			raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")

		info = entry.info
		module_name = entry.node_class.__module__
		category = module_name.split('.')[-1]

		return {
			"name": node_name,
			"category": category,
			"inputs": info.inputs,
			"outputs": info.outputs,
			"properties": info.properties,
			"parameters": info.parameters.model_json_schema()
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get node: {str(e)}")

@app.get("/workflows", response_model=List[str])
async def list_workflows():
	"""List all saved workflow names."""
	try:
		workflow_names = []
		for file_path in WORKFLOWS_DIR.glob("*.json"):
			workflow_names.append(file_path.stem)
		return workflow_names
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")

@app.post("/workflows", response_model=Workflow)
async def create_workflow(workflow: Workflow):
	"""Create or save a workflow."""
	try:
		# Save to file
		file_path = WORKFLOWS_DIR / f"{workflow.name}.json"
		with open(file_path, 'w') as f:
			json.dump(workflow.model_dump(by_alias=True), f, indent=2)

		return workflow
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")

@app.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
	"""Get a specific workflow."""
	try:
		file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
		if not file_path.exists():
			raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

		with open(file_path, 'r') as f:
			workflow_data = json.load(f)
			return Workflow.model_validate(workflow_data)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")

@app.put("/workflows/{workflow_id}", response_model=Workflow)
async def update_workflow(workflow_id: str, workflow: Workflow):
	"""Update an existing workflow."""
	try:
		# Check if workflow exists
		file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
		if not file_path.exists():
			raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

		# Save updated workflow
		with open(file_path, 'w') as f:
			json.dump(workflow.model_dump(by_alias=True), f, indent=2)

		return workflow
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to update workflow: {str(e)}")

@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
	"""Delete a workflow."""
	try:
		file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
		if not file_path.exists():
			raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

		file_path.unlink()
		return {"message": f"Workflow '{workflow_id}' deleted successfully"}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to delete workflow: {str(e)}")

@app.post("/executions/{workflow_id}", response_model=ExecutionStatus)
async def execute_workflow(workflow_id: str):
	"""Execute a workflow."""
	try:
		# Load workflow
		file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
		if not file_path.exists():
			raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

		with open(file_path, 'r') as f:
			workflow_data = json.load(f)
			workflow = Workflow.model_validate(workflow_data)

		# Execute workflow using progress store
		status = progress_store.create_execution(workflow)

		return status
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")

@app.websocket("/ws/progress")
async def progress_websocket(websocket: WebSocket):
	"""WebSocket endpoint for real-time progress updates."""
	await websocket_manager.connect(websocket)
	try:
		execution_status = progress_store.get_executions()
		import time
		await websocket.send_json({
			"type": "execution",
			"timestamp": time.time(),
			"executions": [v.model_dump() for v in execution_status.values()]
		})
		for status in execution_status.values():
			progress = progress_store.get_progress(status.execution_id)
			await websocket.send_json({
				"type": "task",
                "timestamp": time.time(),
                "execution_id": status.execution_id,
                "tasks": {k: v.model_dump() for k, v in progress.items()}
			})

		# Keep connection alive
		while True:
			await websocket.receive_text()
	except WebSocketDisconnect:
		websocket_manager.disconnect(websocket)
		logging.info(f"WebSocket disconnected for execution progress.")

@app.get("/executions", response_model=List[ExecutionStatus])
async def list_executions():
	"""List all executions."""
	try:
		executions = progress_store.get_executions()
		return list(executions.values())
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")

@app.get("/executions/{execution_id}", response_model=ExecutionStatus)
async def get_execution_status(execution_id: str):
	"""Get specific execution status."""
	try:
		executions = progress_store.get_executions()
		if execution_id not in executions:
			raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")

		return executions[execution_id]
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")


# Health check
@app.get("/health")
async def health_check():
	"""Health check endpoint."""
	from .progress.progress_store import workflow_queue
	return {
		"status": "healthy",
		"nodes_registered": len(NodeRegistry._registry),
		"workflows_saved": len(list(WORKFLOWS_DIR.glob("*.json"))),
		"worker_queue_available": workflow_queue is not None
	}

def run_server(host="0.0.0.0", port=8000, reload=False):
	"""Run the FastAPI server."""
	if reload:
		# Use import string for reload mode
		uvicorn.run("atflow.server:app", host=host, port=port, reload=reload)
	else:
		# Use direct app reference for non-reload mode
		uvicorn.run(app, host=host, port=port, reload=reload)

if __name__ == "__main__":
	run_server()
