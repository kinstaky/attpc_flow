#!/usr/bin/env python3
"""
FastAPI server for ATTPC Flow workflow management.
Provides RESTful API for node registry and workflow operations.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import os
from pathlib import Path

from atflow.node_registry import NodeRegistry
from atflow.nodes import *  # Import all nodes to register them

app = FastAPI(
    title="ATTPC Flow API",
    description="Workflow management API for AT-TPC analysis",
    version="0.1.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# Data models
class NodeResponse(BaseModel):
    name: str
    category: str
    inputs: List[str]
    outputs: List[str]
    properties: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None

class SimpleNodeResponse(BaseModel):
    name: str
    category: str

class WorkflowNode(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    properties: Dict[str, Any] = {}
    inputs: Dict[str, Any] = {}

class WorkflowConnection(BaseModel):
    source_node: str
    source_output: str
    target_node: str
    target_input: str

class Workflow(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    nodes: List[WorkflowNode]
    connections: List[WorkflowConnection] = []

class WorkflowExecution(BaseModel):
    workflow_id: str
    environment: Dict[str, Any] = {}

class ExecutionStatus(BaseModel):
    execution_id: str
    workflow_id: str
    status: str  # pending, running, completed, failed
    message: Optional[str] = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Optional[Dict[str, Any]] = None

# Storage
WORKFLOWS_DIR = Path("workflows")
WORKFLOWS_DIR.mkdir(exist_ok=True)

# In-memory execution tracking (for demo purposes)
executions: Dict[str, ExecutionStatus] = {}

# Helper functions
def get_node_schema(pydantic_class) -> Optional[Dict[str, Any]]:
    """Extract JSON schema from Pydantic model."""
    if pydantic_class is None:
        return None
    try:
        return pydantic_class.model_json_schema()
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
            properties=get_node_schema(info.properties),
            parameters=get_node_schema(info.parameters)
        )
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
        # Generate ID if not provided
        if not workflow.id:
            workflow.id = workflow.name.lower().replace(" ", "_")

        # Save to file
        file_path = WORKFLOWS_DIR / f"{workflow.id}.json"
        with open(file_path, 'w') as f:
            json.dump(workflow.model_dump(), f, indent=2)

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
            return Workflow(**workflow_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")

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

@app.post("/workflows/{workflow_id}/execute", response_model=ExecutionStatus)
async def execute_workflow(workflow_id: str, execution: Optional[WorkflowExecution] = None):
    """Execute a workflow."""
    try:
        # Load workflow
        file_path = WORKFLOWS_DIR / f"{workflow_id}.json"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        with open(file_path, 'r') as f:
            workflow_data = json.load(f)
            workflow = Workflow(**workflow_data)

        # Generate execution ID
        import uuid
        execution_id = str(uuid.uuid4())

        # Create execution status
        from datetime import datetime, timezone
        status = ExecutionStatus(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="pending",
            message="Workflow execution queued",
            started_at=datetime.now(timezone.utc).isoformat()
        )

        # Store execution status
        executions[execution_id] = status

        # TODO: Convert workflow to Processor format and execute
        # For now, simulate execution
        status.status = "completed"
        status.message = "Workflow completed successfully (demo mode)"
        status.completed_at = datetime.now(timezone.utc).isoformat()
        status.results = {"message": "Demo execution completed"}

        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")

@app.get("/executions/{execution_id}", response_model=ExecutionStatus)
async def get_execution_status(execution_id: str):
    """Get specific execution status."""
    try:
        if execution_id not in executions:
            raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")

        return executions[execution_id]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")

@app.get("/executions", response_model=List[ExecutionStatus])
async def list_executions():
    """List all executions."""
    try:
        return list(executions.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "nodes_registered": len(NodeRegistry._registry),
        "workflows_saved": len(list(WORKFLOWS_DIR.glob("*.json")))
    }

if __name__ == "__main__":
    import uvicorn

    print("Starting ATTPC Flow API server...")
    print(f"Registered nodes: {list(NodeRegistry._registry.keys())}")
    print(f"Workflows directory: {WORKFLOWS_DIR.absolute()}")
    print("API documentation available at: http://localhost:8000/docs")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
