"""Abstract base class for ATTPC Flow nodes."""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Type

from pydantic import BaseModel


class Node(ABC):
    """Abstract base class for all nodes in the ATTPC Flow framework."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the node name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the node version."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the node description."""
        ...

    @property
    @abstractmethod
    def category(self) -> str:
        """Return the node category."""
        ...

    @property
    @abstractmethod
    def type(self) -> str:
        """Return the node type."""
        ...

    @property
    @abstractmethod
    def inputs(self) -> Dict[str, str]:
        """Return input schema as {name: type}."""
        ...

    @property
    @abstractmethod
    def outputs(self) -> Dict[str, str]:
        """Return output schema as {name: type}."""
        ...

    @property
    @abstractmethod
    def properties(self) -> Dict[str, str]:
        """Return configurable properties as {name: type}."""
        ...

    @property
    def parameters_model(self) -> Type[BaseModel] | None:
        """Return Pydantic model for parameter validation."""
        return None

    @abstractmethod
    def execute(self, **kwargs: Any) -> List[Any]:
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
            (run, execution_id, task_id, self.version)
        )
        conn.commit()
        conn.close()

    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters using Pydantic model if available.

        Args:
            params: Dictionary of parameters to validate

        Returns:
            Validated parameters as dictionary

        Raises:
            ValueError: If parameter validation fails
        """
        if self.parameters_model:
            try:
                return self.parameters_model(**params).model_dump()
            except Exception as e:
                raise ValueError(f"Parameters validation failed for {self.name}: {e}")
        return params
