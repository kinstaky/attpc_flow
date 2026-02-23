"""
Meta record module for execution logging.
Handles creation of execution meta directories, workflow copies, and metadata DB files.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .progress_store import TaskProgress, ExecutionStatus


class ExecutionMetaManager:
    """Manages meta records for workflow executions using SQLite databases."""

    _lock = threading.Lock()
    _connections: Dict[str, sqlite3.Connection] = {}

    @staticmethod
    def _get_meta_dir(workspace: str, execution_id: str) -> Path:
        """Get the meta directory path for an execution."""
        return Path(workspace) / "meta" / "executions" / execution_id

    @staticmethod
    def _get_executions_db_path(workspace: str) -> Path:
        """Get the path to the executions database."""
        db_path = Path(workspace) / "meta" / "executions" / "executions.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    @staticmethod
    def _get_tasks_db_path(workspace: str, execution_id: str) -> Path:
        """Get the path to the tasks database for an execution."""
        meta_dir = ExecutionMetaManager._get_meta_dir(workspace, execution_id)
        meta_dir.mkdir(parents=True, exist_ok=True)
        return meta_dir / "tasks.db"

    @classmethod
    def _init_executions_db(cls, workspace: str):
        """Initialize the executions database schema."""
        db_path = cls._get_executions_db_path(workspace)
        with cls._lock:
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS executions (
                        execution_id TEXT PRIMARY KEY,
                        workflow_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        run_mode TEXT NOT NULL,
                        started_at REAL,
                        completed_at REAL,
                        total_tasks INTEGER DEFAULT 0,
                        completed_tasks INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    @classmethod
    def _init_tasks_db(cls, workspace: str, execution_id: str):
        """Initialize the tasks database schema."""
        db_path = cls._get_tasks_db_path(workspace, execution_id)
        with cls._lock:
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        task_name TEXT,
                        run TEXT,
                        percentage INTEGER DEFAULT 0,
                        status TEXT NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    @classmethod
    def create_execution_meta(
        cls,
        workspace: str,
        execution_id: str,
        workflow: Any,  # Workflow model or node name
        run_mode: Optional[str] = None,
    ) -> Path:
        """
        Create execution meta directory and optionally save workflow.json.
        Initialize executions.db and tasks.db.
        Called when execution is created.
        """

        # Determine workflow_id
        if run_mode == "node":
            workflow_id = "node"
        else:
            workflow_id = workflow.name

        # Create directories
        meta_dir = cls._get_meta_dir(workspace, execution_id)
        meta_dir.mkdir(parents=True, exist_ok=True)

        # Save workflow.json only if workflow is provided
        if run_mode != "node":
            workflow_file = meta_dir / "workflow.json"
            with open(workflow_file, "w") as f:
                json.dump(workflow.model_dump(), f, indent=2)

        # Initialize databases
        cls._init_executions_db(workspace)
        cls._init_tasks_db(workspace, execution_id)

        # Insert execution record
        db_path = cls._get_executions_db_path(workspace)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""
                INSERT INTO executions (
                    execution_id, workflow_id, status, run_mode,
                    started_at, completed_at, total_tasks, completed_tasks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                workflow_id,
                "waiting",
                run_mode,
                None,
                None,
                0,
                0
            ))
            conn.commit()
        finally:
            conn.close()

        return meta_dir

    @classmethod
    def write_meta(
        cls,
        workspace: str,
        execution_status: ExecutionStatus,
        tasks_progress: Optional[Dict[str, TaskProgress]]
    ) -> Path:
        """
        Update execution metadata in executions.db and write tasks to tasks.db.
        Called after execution finishes.
        """
        # Update executions.db
        db_path = cls._get_executions_db_path(workspace)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""
                UPDATE executions SET
                    status = ?,
                    started_at = ?,
                    completed_at = ?,
                    total_tasks = ?,
                    completed_tasks = ?
                WHERE execution_id = ?
            """, (
                execution_status.status,
                execution_status.started_at,
                execution_status.completed_at,
                execution_status.total_tasks,
                execution_status.completed_tasks,
                execution_status.execution_id
            ))
            conn.commit()
        finally:
            conn.close()

        # Write tasks to tasks.db
        if tasks_progress:
            cls._write_tasks(workspace, execution_status.execution_id, tasks_progress)

        return db_path

    @classmethod
    def _write_tasks(
        cls,
        workspace: str,
        execution_id: str,
        tasks_progress: Dict[str, TaskProgress]
    ):
        """Write task progress to tasks.db."""
        db_path = cls._get_tasks_db_path(workspace, execution_id)
        conn = sqlite3.connect(str(db_path))
        try:
            for task_id, task in tasks_progress.items():
                conn.execute("""
                    INSERT OR REPLACE INTO tasks (
                        task_id, task_name, run, percentage, status
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    task_id,
                    task.task_name,
                    task.run,
                    task.percentage,
                    task.status
                ))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def update_meta_status(
        cls,
        workspace: str,
        execution_id: str,
        status: str,
        completed_at: Optional[float] = None,
        completed_tasks: Optional[int] = None,
    ) -> Path:
        """
        Update execution status in executions.db.
        Returns path to executions.db file.
        """
        db_path = cls._get_executions_db_path(workspace)
        conn = sqlite3.connect(str(db_path))
        try:
            if completed_at is not None and completed_tasks is not None:
                conn.execute("""
                    UPDATE executions SET
                        status = ?,
                        completed_at = ?,
                        completed_tasks = ?
                    WHERE execution_id = ?
                """, (status, completed_at, completed_tasks, execution_id))
            elif completed_at is not None:
                conn.execute("""
                    UPDATE executions SET status = ?, completed_at = ?
                    WHERE execution_id = ?
                """, (status, completed_at, execution_id))
            elif completed_tasks is not None:
                conn.execute("""
                    UPDATE executions SET status = ?, completed_tasks = ?
                    WHERE execution_id = ?
                """, (status, completed_tasks, execution_id))
            else:
                conn.execute("""
                    UPDATE executions SET status = ? WHERE execution_id = ?
                """, (status, execution_id))
            conn.commit()
        finally:
            conn.close()

        return db_path

    @classmethod
    def record_task_progress(
        cls,
        workspace: str,
        execution_id: str,
        task_id: str,
        task_name: Optional[str],
        run: Optional[str],
        percentage: int,
        timestamp: float,
        status: str,
    ):
        """Record or update task progress in tasks.db."""
        db_path = cls._get_tasks_db_path(workspace, execution_id)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO tasks (
                    task_id, task_name, run, percentage, timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, task_name, run, percentage, timestamp, status))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def get_executions(
        cls,
        workspace: str,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated execution history from executions.db.
        Returns (executions_list, total_count).
        """
        db_path = cls._get_executions_db_path(workspace)
        if not db_path.exists():
            return [], 0

        conn = sqlite3.connect(str(db_path))
        try:
            conn.row_factory = sqlite3.Row

            # Get total count
            cursor = conn.execute("SELECT COUNT(*) FROM executions")
            total = cursor.fetchone()[0]

            # Get paginated results
            offset = (page - 1) * page_size
            cursor = conn.execute(
                """
                SELECT * FROM executions
                ORDER BY completed_at DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset)
            )

            executions = []
            for row in cursor.fetchall():
                execution = dict(row)
                # Load tasks from tasks.db
                tasks_db_path = cls._get_tasks_db_path(workspace, execution["execution_id"])
                if tasks_db_path.exists():
                    tasks = cls._get_tasks_for_execution(tasks_db_path)
                    execution["tasks"] = tasks
                else:
                    execution["tasks"] = {}
                executions.append(execution)

            return executions, total
        finally:
            conn.close()

    @classmethod
    def _get_tasks_for_execution(cls, tasks_db_path: Path) -> Dict[str, Any]:
        """Get all tasks for an execution from tasks.db."""
        conn = sqlite3.connect(str(tasks_db_path))
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks ORDER BY task_id")
            tasks = {}
            for row in cursor.fetchall():
                print("row:", row)
                task = dict(row)
                print("task:", task)
                tasks[task["task_id"]] = task
            return tasks
        finally:
            conn.close()

    @classmethod
    def get_execution(cls, workspace: str, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get a single execution with its tasks."""
        db_path = cls._get_executions_db_path(workspace)
        if not db_path.exists():
            return None

        conn = sqlite3.connect(str(db_path))
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM executions WHERE execution_id = ?",
                (execution_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            execution = dict(row)
            # Load tasks from tasks.db
            tasks_db_path = cls._get_tasks_db_path(workspace, execution_id)
            if tasks_db_path.exists():
                execution["tasks"] = cls._get_tasks_for_execution(tasks_db_path)
            else:
                execution["tasks"] = {}
            return execution
        finally:
            conn.close()
