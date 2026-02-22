"""Node manager for loading and managing ATTPC Flow nodes."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
import tomllib
import zipfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .node import Node

# Global manager instance for auto-registration
_global_manager: Optional['NodeManager'] = None
_manager_lock = threading.Lock()


def auto_register_node(cls: Type[Node]) -> Type[Node]:
    """Decorator to automatically register a node class when imported.

    This decorator creates an instance of the node class and registers it
    with the global NodeManager. If no manager exists yet, the node is
    stored for later registration.

    Uses double-checked locking pattern for thread-safe, lock-free fast path
    when manager is already initialized.

    Usage:
        @auto_register_node
        class MyNode(Node):
            @property
            def name(self) -> str:
                return "my_node"
            ...
    """
    node = cls()

    # First check without lock (fast path)
    if _global_manager is not None:
        _global_manager.register_node(node)
        return cls

    # Slow path with lock - double-check pattern
    with _manager_lock:
        # Double-check after acquiring lock
        if _global_manager is not None:
            _global_manager.register_node(node)
        else:
            if not hasattr(auto_register_node, '_pending_nodes'):
                auto_register_node._pending_nodes = []
            auto_register_node._pending_nodes.append(node)

    return cls


def set_global_manager(manager: 'NodeManager') -> None:
    """Set the global node manager for auto-registration.

    Args:
        manager: The NodeManager instance to use for auto-registration
    """
    global _global_manager
    with _manager_lock:
        _global_manager = manager

        # Register any pending nodes
        if hasattr(auto_register_node, '_pending_nodes'):
            for node in auto_register_node._pending_nodes:
                manager.register_node(node)
            auto_register_node._pending_nodes.clear()


class NodeManager:
    """Thread-safe singleton manager for loading and managing nodes."""

    _instance: Optional['NodeManager'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'NodeManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, '_initialized'):
            return

        self._nodes: Dict[str, Node] = {}
        self._external_node_path: Optional[Path] = None
        self._nodes_lock = threading.Lock()
        self._initialized = True

        # Set this instance as the global manager for auto-registration
        set_global_manager(self)

    def set_external_node_path(self, path: Path) -> None:
        """Set the directory path for external nodes.

        Args:
            path: Directory path containing external node packages
        """
        with self._nodes_lock:
            self._external_node_path = path

    def discover_nodes(self) -> None:
        """Discover and load all nodes from entry points and external directory."""
        self._load_entry_point_nodes()
        if self._external_node_path:
            self._load_external_nodes()

    def _load_entry_point_nodes(self) -> None:
        """Load nodes registered via entry points."""
        try:
            entry_points = importlib.metadata.entry_points()
            if hasattr(entry_points, 'select'):
                # Python 3.10+
                eps = entry_points.select(group='attpc_nodes')
            else:
                # Older Python
                eps = entry_points.get('attpc_nodes', [])

            for ep in eps:
                try:
                    node_class = ep.load()
                    node = node_class()
                    with self._nodes_lock:
                        self._nodes[node.name] = node
                except Exception as e:
                    print(f"Failed to load node {ep.name}: {e}")
        except Exception as e:
            print(f"Error loading entry point nodes: {e}")

    def _load_external_nodes(self) -> None:
        """Load nodes from external node directory.

        Process:
        1. Search for subdirectories in self._external_node_path
        2. Read node.toml for node name and entry point
        3. Check if built (dist/{package_name} exists), if not build and extract
        4. Import module and record node class
        """
        if not self._external_node_path or not self._external_node_path.exists():
            return

        for node_dir in self._external_node_path.iterdir():
            if not node_dir.is_dir():
                continue

            node_toml = node_dir / "node.toml"
            if not node_toml.exists():
                continue

            try:
                # Read node.toml
                with open(node_toml, "rb") as f:
                    config = tomllib.load(f)

                node_name = config.get("node", {}).get("name")
                entrypoint = config.get("entrypoint", {})
                package_name = entrypoint.get("package")
                class_name = entrypoint.get("class")

                if not all([node_name, package_name, class_name]):
                    print(f"Invalid node.toml in {node_dir.name}")
                    continue

                # Check if built
                dist_dir = node_dir / "dist"
                package_dist_dir = dist_dir / package_name

                if not package_dist_dir.exists():
                    # Build the node
                    print(f"Building node {node_name}...")
                    try:
                        _result = subprocess.run(
                            ["uv", "build", "--wheel"],
                            cwd=node_dir,
                            capture_output=True,
                            text=True,
                            check=True
                        )
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to build {node_name}: {e.stderr}")
                        continue
                    except FileNotFoundError:
                        print(f"uv not found, cannot build {node_name}")
                        continue

                    # Find and extract the wheel
                    wheels = list(dist_dir.glob("*.whl"))
                    if not wheels:
                        print(f"No wheel found for {node_name}")
                        continue

                    wheel = wheels[0]
                    extract_dir = dist_dir / package_name
                    extract_dir.mkdir(parents=True, exist_ok=True)

                    with zipfile.ZipFile(wheel, 'r') as zf:
                        zf.extractall(extract_dir)

                # Add dist/{package_name} to sys.path and import
                if str(package_dist_dir) not in sys.path:
                    sys.path.insert(0, str(package_dist_dir))

                try:
                    module = importlib.import_module(package_name)
                    node_class = getattr(module, class_name)
                    node = node_class()
                    with self._nodes_lock:
                        self._nodes[node.name] = node
                    print(f"Loaded external node: {node_name}")
                except Exception as e:
                    print(f"Failed to import {node_name}: {e}")

            except Exception as e:
                print(f"Failed to load external node from {node_dir}: {e}")

    def register_node(self, node: Node, force: bool = False) -> None:
        """Register a node instance.

        Args:
            node: The node instance to register
            force: If True, overwrite existing node with same name

        Raises:
            ValueError: If node is already registered and force=False
        """
        with self._nodes_lock:
            if node.name in self._nodes and not force:
                raise ValueError(f"Node '{node.name}' is already registered. Use force=True to overwrite.")
            self._nodes[node.name] = node

    def unregister_node(self, name: str) -> Optional[Node]:
        """Unregister a node by name.

        Args:
            name: The name of the node to unregister

        Returns:
            The unregistered node instance, or None if not found
        """
        with self._nodes_lock:
            return self._nodes.pop(name, None)

    def is_registered(self, name: str) -> bool:
        """Check if a node is registered.

        Args:
            name: The name of the node to check

        Returns:
            True if the node is registered, False otherwise
        """
        with self._nodes_lock:
            return name in self._nodes

    def get_node(self, name: str) -> Optional[Node]:
        """Get a node by name.

        Args:
            name: The name of the node to retrieve

        Returns:
            The node instance, or None if not found
        """
        with self._nodes_lock:
            return self._nodes.get(name)

    def list_nodes(self) -> List[str]:
        """List all registered node names.

        Returns:
            List of node names
        """
        with self._nodes_lock:
            return list(self._nodes.keys())

    def execute_node(
        self,
        name: str,
        execution_id: str,
        task_id: int,
        environment: Dict[str, Any],
        inputs: Dict[str, Any],
        properties: Dict[str, Any]
    ) -> List[Any]:
        """Execute a node by name with given parameters.

        Args:
            name: Name of the node to execute
            execution_id: Execution identifier
            task_id: Task identifier
            environment: Environment variables
            inputs: Input values
            properties: Property values

        Returns:
            List of output values from the node

        Raises:
            ValueError: If node is not registered
        """
        node = self.get_node(name)
        if not node:
            raise ValueError(f"Node '{name}' is not registered.")

        # Combine parameters
        params = {
            "execution_id": execution_id,
            "task_id": task_id,
            **environment,
            **inputs,
            **properties
        }

        # Validate parameters
        validated_params = node.validate_parameters(params)

        # Execute node
        result = node.execute(**validated_params)

        # Write metadata
        workspace = params.get("workspace")
        run = params.get("run")
        if workspace is not None and run is not None:
            node.write_meta(workspace, execution_id, task_id, run)

        return result

    def get_node_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get node information including schemas.

        Args:
            name: Name of the node

        Returns:
            Dictionary with node information, or None if not found
        """
        node = self.get_node(name)
        if not node:
            return None

        return {
            "name": node.name,
            "version": node.version,
            "description": node.description,
            "category": node.category,
            "inputs": node.inputs,
            "outputs": node.outputs,
            "properties": node.properties,
            "parameters_model": node.parameters_model
        }
