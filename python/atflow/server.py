#!/usr/bin/env python3
"""
FastAPI server for ATTPC Flow workflow management.
Provides RESTful API for node registry and workflow operations.
"""

import asyncio
import logging
import json
import os
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
from multiprocessing import Queue

from atflow.node_manager import NodeManager
from atflow.nodes import *  # Import all nodes to register them
from atflow.progress.progress_store import (
    TaskProgress,
    progress_store,
    ExecutionStatus,
)
from .progress.execution_meta import ExecutionMetaManager
from .run_tag_db import RunTagDB
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

class ExecutionWithTasks(ExecutionStatus):
	tasks: Dict[str, TaskProgress]

class ExecutionHistoryResponse(BaseModel):
	executions: List[ExecutionWithTasks]
	total: int
	page: int
	page_size: int
	total_pages: int

# Storage
WORKFLOWS_DIR = Path("workflows")
WORKFLOWS_DIR.mkdir(exist_ok=True)

# Recent workflows storage (plain text, one workflow per line)
RECENT_WORKFLOWS_FILE = Path("workflows/.recent")
MAX_RECENT_WORKFLOWS = 5

# Opened workflows storage (plain text, one workflow per line)
OPENED_WORKFLOWS_FILE = Path("workflows/.opened")

def load_workflow_list(file_path: Path) -> List[str]:
	"""Load a list of workflow names from a plain text file (one per line)."""
	if not file_path.exists():
		return []
	try:
		with open(file_path, 'r') as f:
			# Filter out empty lines
			return [line.strip() for line in f if line.strip()]
	except IOError:
		return []

def save_workflow_list(file_path: Path, workflows: List[str]):
	"""Save a list of workflow names to a plain text file (one per line)."""
	try:
		file_path.parent.mkdir(parents=True, exist_ok=True)
		with open(file_path, 'w') as f:
			for workflow in workflows:
				f.write(f"{workflow}\n")
	except IOError as e:
		logging.error(f"Failed to save workflow list to {file_path}: {e}")

def load_recent_workflows() -> List[str]:
	"""Load the list of recently opened workflows from disk."""
	return load_workflow_list(RECENT_WORKFLOWS_FILE)

def save_recent_workflows(workflows: List[str]):
	"""Save the list of recently opened workflows to disk."""
	save_workflow_list(RECENT_WORKFLOWS_FILE, workflows[:MAX_RECENT_WORKFLOWS])

def load_opened_workflows() -> List[str]:
	"""Load the list of currently opened workflows from disk."""
	return load_workflow_list(OPENED_WORKFLOWS_FILE)

def save_opened_workflows(workflows: List[str]):
	"""Save the list of currently opened workflows to disk."""
	save_workflow_list(OPENED_WORKFLOWS_FILE, workflows)


# WebSocket manager for progress broadcasting
class WebSocketManager:
	def __init__(self):
		self.active_connections: List[WebSocket] = []
		self._callbacks: Dict[WebSocket, object] = {}
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

		progress_store.register_websocket_callback(progress_callback)
		self._callbacks[websocket] = progress_callback

	def disconnect(self, websocket: WebSocket):
		try:
			self.active_connections.remove(websocket)
		except ValueError:
			pass  # Connection already removed

		# Unregister callback from progress store
		callback = self._callbacks.pop(websocket, None)
		if callback:
			progress_store.unregister_websocket_callback(callback)

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
	"""Organize registered nodes by their category."""
	categories = {}
	manager = NodeManager()

	for name in manager.list_nodes():
		node = manager.get_node(name)
		if node:
			category = node.category
			if category not in categories:
				categories[category] = []

			# Add just the node name
			categories[category].append(name)

	return categories

run_tag_db = RunTagDB()

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
		manager = NodeManager()
		node = manager.get_node(node_name)
		if not node:
			raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")

		return NodeResponse(
			name=node_name,
			category=node.category,
			inputs=node.inputs,
			outputs=node.outputs,
			properties=node.properties,
			parameters=get_node_schema(node.parameters_model),
		)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get node: {str(e)}")

@app.get("/nodes_dev/{node_name}", response_model=Dict[Any, Any])
async def get_dev_node(node_name: str):
	try:
		manager = NodeManager()
		node = manager.get_node(node_name)
		if not node:
			raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")

		return {
			"name": node_name,
			"category": node.category,
			"inputs": node.inputs,
			"outputs": node.outputs,
			"properties": node.properties,
			"parameters": node.parameters_model.model_json_schema() if node.parameters_model else None
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
	"""Get a specific workflow and update recent/opened lists."""
	try:
		file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
		if not file_path.exists():
			raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

		with open(file_path, 'r') as f:
			workflow_data = json.load(f)
			workflow = Workflow.model_validate(workflow_data)

		# Update recent workflows: move to front if exists, add to front if new
		recent = load_recent_workflows()
		if workflow_id in recent:
			recent.remove(workflow_id)
		recent.insert(0, workflow_id)
		save_recent_workflows(recent[:MAX_RECENT_WORKFLOWS])

		# Add to opened workflows if not already present
		opened = load_opened_workflows()
		if workflow_id not in opened:
			opened.append(workflow_id)
			save_opened_workflows(opened)

		return workflow
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")

@app.put("/workflows/{workflow_id}", response_model=Workflow)
async def update_workflow(workflow_id: str, workflow: Workflow):
    def _save():
        file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow '{workflow_id}' not found")
        with open(file_path, 'w') as f:
            json.dump(workflow.model_dump(by_alias=True), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        return workflow

    try:
        return await asyncio.to_thread(_save)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
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

@app.get("/recent_workflows", response_model=List[str])
async def list_recent_workflows():
	"""Get list of recently opened workflows (max 5)."""
	try:
		return load_recent_workflows()
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to load recent workflows: {str(e)}")

@app.get("/opened_workflows", response_model=List[str])
async def list_opened_workflows():
	"""Get list of currently opened workflows."""
	try:
		return load_opened_workflows()
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to load opened workflows: {str(e)}")

@app.post("/close_workflow/{workflow_name}")
async def close_workflow(workflow_name: str):
	"""Remove a workflow from the opened list."""
	try:
		opened = load_opened_workflows()
		if workflow_name in opened:
			opened.remove(workflow_name)
			save_opened_workflows(opened)
		return {"message": f"Closed '{workflow_name}'"}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to close workflow: {str(e)}")

# Global workflow queue for multiprocessing
workflow_queue: Optional[Queue] = None

def get_workflow_queue():
    """Get or create the workflow queue. Survives uvicorn reloads."""
    global workflow_queue
    if workflow_queue is None:
        workflow_queue = Queue()
    return workflow_queue

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

		try:
			queue = get_workflow_queue()
			if queue:
				queue.put((status.execution_id, workflow))
		except Exception as e:
			logging.warning(f"Failed to enqueue workflow: {e}")
			status = progress_store.finish_execution(status.execution_id, 0)

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

@app.get("/executions/history", response_model=ExecutionHistoryResponse)
async def list_execution_history(workspace: str, page: int = 1, page_size: int = 10):
	"""
	Get paginated execution history from database.

	Args:
		workspace: Workspace directory path
		page: Page number (1-indexed)
		page_size: Number of items per page
	"""
	try:
		executions, total = ExecutionMetaManager.get_executions(
			workspace=workspace,
			page=page,
			page_size=page_size
		)
		return {
			"executions": executions,
			"total": total,
			"page": page,
			"page_size": page_size,
			"total_pages": (total + page_size - 1) // page_size
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to list execution history: {str(e)}")

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


# Run Tags API
class RunFilterRequest(BaseModel):
	runs: Optional[List[int]] = None
	tags: Optional[List[str]] = None

@app.get("/runs", response_model=List[int])
async def list_runs(workspace: str):
	"""List all run numbers."""
	try:
		return run_tag_db.list_runs(Path(workspace))
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to list runs: {str(e)}")

@app.get("/runs/tags", response_model=Dict[str, List[str]])
async def list_tags(workspace: str):
	"""Get all tag groups with their unique values."""
	try:
		return run_tag_db.list_all_tags(Path(workspace))
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to list tag groups: {str(e)}")

@app.post("/runs/refresh", response_model=Dict[str, int|str])
async def refresh_run_database(workspace: str):
	"""Force refresh the run database from disk."""
	try:
		df = run_tag_db.refresh(Path(workspace))
		return {"message": "Database refreshed", "rows": len(df)}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to initialize run database: {str(e)}")

@app.get("/runs/info", response_model=List[Dict])
async def get_runs_info(workspace: str, runs: Optional[List[int]] = None):
	"""Get detailed info for runs. Pass comma-separated run numbers or omit for all."""
	try:
		return run_tag_db.get_runs_info(Path(workspace), runs)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get runs info: {str(e)}")

@app.get("/runs/{run_number}", response_model=Dict)
async def get_run_info(workspace: str, run_number: int):
	"""Get detailed info for a specific run."""
	try:
		info = run_tag_db.get_run_info(Path(workspace), run_number)
		if info is None:
			raise HTTPException(status_code=404, detail=f"Run {run_number} not found")
		return info
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get run info: {str(e)}")

# Health check
@app.get("/health")
async def health_check():
	"""Health check endpoint."""
	from .progress.progress_store import workflow_queue
	manager = NodeManager()
	return {
		"status": "healthy",
		"nodes_registered": len(manager.list_nodes()),
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
