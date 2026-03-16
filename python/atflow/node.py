"""Abstract base class for ATTPC Flow nodes."""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel


class Node(ABC):
    """Abstract base class for all nodes in the ATTPC Flow framework."""

    _name: str = "node"
    _version: str = "1.0.0"
    _description: str = ""
    _category: str = "unknown"
    _type: str = "unknown"
    _inputs: dict[str, str] = {}
    _outputs: dict[str, str] = {}
    _properties: dict[str, str] = {}
    _parameters: Type[BaseModel] | None = None

    @classmethod
    def name(cls) -> str:
        """Return the node name."""
        return cls._name

    @classmethod
    def version(cls) -> str:
        """Return the node version."""
        return cls._version

    @classmethod
    def description(cls) -> str:
        """Return the node description."""
        return cls._description

    @classmethod
    def category(cls) -> str:
        """Return the node category."""
        return cls._category

    @classmethod
    def type(cls) -> str:
        """Return the node type."""
        return cls._type

    @classmethod
    def inputs(cls) -> dict[str, str]:
        """Return input schema as {name: type}."""
        return cls._inputs

    @classmethod
    def outputs(cls) -> dict[str, str]:
        """Return output schema as {name: type}."""
        return cls._outputs

    @classmethod
    def properties(cls) -> dict[str, str]:
        """Return configurable properties as {name: type}."""
        return cls._properties

    @classmethod
    def parameters_model(cls) -> Type[BaseModel] | None:
        """Return Pydantic model for parameter validation."""
        return cls._parameters

    @abstractmethod
    def execute(self, **kwargs: Any) -> list[Any]:
        """Execute the node logic.

        Args:
            **kwargs: Combined execution parameters including:
                - execution_id: str
                - task_id: int
                - environment: dict
                - inputs: dict
                - properties: dict

        Returns:
            List of output values.
        """
        ...

    def write_meta(
        self,
        workspace: str,
        execution_id: str,
        task_id: int,
        run: str,
    ) -> None:
        """Write metadata to sqlite3 database after node execution.

        Writes to ${workspace}/meta/${node_name}.db

        Args:
            workspace: Workspace directory path
            execution_id: Execution identifier
            task_id: Task identifier
            meta_data: Dictionary of metadata to store
        """
        meta_dir = Path(workspace) / "meta" / "nodes"
        meta_dir.mkdir(parents=True, exist_ok=True)

        db_path = meta_dir / f"{self.name}.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")

        # Create table for this execution
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS meta (
                run TEXT PRIMARY KEY NOT NULL,
                execution_id TEXT NOT NULL,
                task_id INTEGER NOT NULL,
                version TEXT NOT NULL
            )
        """)

        # insert metadata
        conn.execute("""
            INSERT OR REPLACE INTO meta (
                run, execution_id, task_id, version
            ) VALUES (?, ?, ?, ?)
        """,
            (run, execution_id, task_id, self.version())
        )
        conn.commit()
        conn.close()

    def validate_parameters(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate parameters using Pydantic model if available.

        Args:
            params: Dictionary of parameters to validate

        Returns:
            Validated parameters as dictionary

        Raises:
            ValueError: If parameter validation fails
        """
        if self.parameters_model():
            try:
                return self.parameters_model(**params).model_dump()
            except Exception as e:
                raise ValueError(f"Parameters validation failed for {self.name}: {e}")
        return params
