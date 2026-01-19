#!/usr/bin/env python3
"""
Test suite for ATTPC Flow server endpoints.
Run with: uv run pytest python/tests/test_server.py -v
"""

import pytest
import sys
import os

# Add parent directory to path to import server module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi.testclient import TestClient
import server
import json

@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(server.app)

@pytest.fixture
def sample_workflow():
    """Sample workflow data for testing."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow for unit testing",
        "nodes": [
            {
                "id": "node1",
                "type": "const_int",
                "position": {"x": 100, "y": 100},
                "properties": {"value": [1, 2, 3]}
            },
            {
                "id": "node2",
                "type": "check_graw_event_id",
                "position": {"x": 300, "y": 100},
                "properties": {"graw_dir": "/test/data"}
            }
        ],
        "connections": [
            {
                "source_node": "node1",
                "source_output": "ARRAY[INT]",
                "target_node": "node2",
                "target_input": "INT"
            }
        ]
    }

class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns correct status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "nodes_registered" in data
        assert "workflows_saved" in data

class TestNodes:
    """Test node endpoints."""

    def test_get_nodes(self, client):
        """Test get all nodes returns organized list of names."""
        response = client.get("/nodes")
        assert response.status_code == 200

        data = response.json()
        assert "basic" in data
        assert "merger" in data

        # Check const_int is in basic category
        basic_nodes = data["basic"]
        assert "const_int" in basic_nodes

        # Check check_graw_event_id is in merger category
        merger_nodes = data["merger"]
        assert "check_graw_event_id" in merger_nodes

        # Verify these are strings, not objects
        assert all(isinstance(node, str) for node in basic_nodes)
        assert all(isinstance(node, str) for node in merger_nodes)

    def test_get_specific_node(self, client):
        """Test get specific node returns full details."""
        response = client.get("/nodes/const_int")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "const_int"
        assert data["category"] == "basic"
        assert "inputs" in data
        assert "outputs" in data
        assert "properties" in data
        assert "parameters" in data

    def test_get_nonexistent_node(self, client):
        """Test get nonexistent node returns 404."""
        response = client.get("/nodes/nonexistent")
        assert response.status_code == 404

class TestWorkflows:
    """Test workflow management endpoints."""

    def test_list_workflows_empty(self, client):
        """Test listing workflows when none exist."""
        # Clean up any existing workflows
        response = client.get("/workflows")
        for workflow_name in response.json():
            client.delete(f"/workflows/{workflow_name}")

        # Now test empty list
        response = client.get("/workflows")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_workflow(self, client, sample_workflow):
        """Test creating a new workflow."""
        response = client.post("/workflows", json=sample_workflow)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == sample_workflow["name"]
        assert data["id"] == "test_workflow"  # Auto-generated from name
        assert len(data["nodes"]) == 2
        assert len(data["connections"]) == 1

    def test_get_workflow(self, client, sample_workflow):
        """Test getting a specific workflow."""
        # Create workflow first
        create_response = client.post("/workflows", json=sample_workflow)
        workflow_id = create_response.json()["id"]

        # Get workflow
        response = client.get(f"/workflows/{workflow_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == workflow_id
        assert data["name"] == sample_workflow["name"]

    def test_get_nonexistent_workflow(self, client):
        """Test getting nonexistent workflow returns 404."""
        response = client.get("/workflows/nonexistent")
        assert response.status_code == 404

    def test_delete_workflow(self, client, sample_workflow):
        """Test deleting a workflow."""
        # Create workflow first
        create_response = client.post("/workflows", json=sample_workflow)
        workflow_id = create_response.json()["id"]

        # Delete workflow
        response = client.delete(f"/workflows/{workflow_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f"/workflows/{workflow_id}")
        assert get_response.status_code == 404

class TestExecution:
    """Test workflow execution endpoints."""

    def test_execute_workflow(self, client, sample_workflow):
        """Test executing a workflow."""
        # Create workflow first
        create_response = client.post("/workflows", json=sample_workflow)
        workflow_id = create_response.json()["id"]

        # Execute workflow (no body needed since execution is optional)
        response = client.post(f"/workflows/{workflow_id}/execute")
        assert response.status_code == 200

        data = response.json()
        assert "execution_id" in data
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "completed"  # Demo mode
        assert "started_at" in data
        assert "completed_at" in data

    def test_execute_nonexistent_workflow(self, client):
        """Test executing nonexistent workflow returns 404."""
        response = client.post("/workflows/nonexistent/execute")
        assert response.status_code == 404

    def test_get_execution_status(self, client, sample_workflow):
        """Test getting execution status."""
        # Create and execute workflow
        create_response = client.post("/workflows", json=sample_workflow)
        workflow_id = create_response.json()["id"]

        exec_response = client.post(f"/workflows/{workflow_id}/execute")
        execution_id = exec_response.json()["execution_id"]

        # Get execution status
        response = client.get(f"/executions/{execution_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["execution_id"] == execution_id
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "completed"

    def test_list_executions(self, client, sample_workflow):
        """Test listing all executions."""
        # Create and execute workflow
        create_response = client.post("/workflows", json=sample_workflow)
        workflow_id = create_response.json()["id"]

        client.post(f"/workflows/{workflow_id}/execute")

        # List executions
        response = client.get("/executions")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1
        assert all("execution_id" in exec for exec in data)

    def test_get_workflow_executions(self, client, sample_workflow):
        """Test that workflow-specific status endpoint was removed and clean up test workflow."""
        # This endpoint should no longer exist
        create_response = client.post("/workflows", json=sample_workflow)
        workflow_id = create_response.json()["id"]
        
        # The endpoint should return 404
        response = client.get(f"/workflows/{workflow_id}/status")
        assert response.status_code == 404
        
        # Clean up: delete the test workflow
        delete_response = client.delete(f"/workflows/{workflow_id}")
        assert delete_response.status_code == 200
        
        # Verify it was deleted
        get_response = client.get(f"/workflows/{workflow_id}")
        assert get_response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
