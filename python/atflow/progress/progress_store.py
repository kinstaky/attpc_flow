"""
Centralized progress store for ATTPC Flow.
Handles progress data storage and WebSocket broadcasting.
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from pydantic import BaseModel
from typing import Literal

class TaskProgress(BaseModel):
    task_id: str
    task_name: Optional[str] = None
    run: Optional[str] = None
    percentage: int
    timestamp: Optional[float] = None
    status: Literal["running", "failed", "completed", "discarded", "cached"]

class ExecutionStatus(BaseModel):
    execution_id: str
    workflow_id: str
    status: Literal["waiting", "running", "completed", "failed"]
    run_mode: Optional[str] = None  # "ui", "workflow", "node"
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    completed_tasks: int = 0
    total_tasks: int = 0

class TaskInfo(BaseModel):
    name: str
    run: str

class ProgressStore:
    """Thread-safe progress store with WebSocket broadcasting capability."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # store execution status
        self.executions: Dict[str, ExecutionStatus] = {}  # {execution_id: ExecutionStatus}
        # store task status
        self.tasks: Dict[str, Dict[str, TaskProgress]] = {}  # {execution_id: {task_id: TaskProgress}}
        # store task name
        self.task_info: Dict[str, Dict[str, TaskInfo]] = {}  # {execution_id: {task_id: TaskInfo}}
        self.websocket_callbacks: List[Callable] = []  # [callbacks]
        self._data_lock = threading.Lock()

    def register_websocket_callback(self, callback: Callable):
        """Register a WebSocket callback for progress updates."""
        with self._data_lock:
            self.websocket_callbacks.append(callback)

    def unregister_websocket_callback(self, callback: Callable):
        """Unregister a WebSocket callback."""
        with self._data_lock:
            try:
                self.websocket_callbacks.remove(callback)
            except ValueError:
                pass  # Callback already removed

    def start_task(self, execution_id: str, task_id: str):
        """Start a task and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.executions:
                return
            if execution_id not in self.tasks:
                self.tasks[execution_id] = {}

            # Check if task already exists
            if task_id in self.tasks[execution_id]:
                return

            # Create new task progress with 0% and running status
            task_info = self.task_info.get(execution_id, {}).get(task_id, {})

            progress = TaskProgress(
                task_id=task_id,
                task_name=task_info.name,
                run=task_info.run,
                percentage=0,
                timestamp=time.time(),
                status="running"
            )
            self.tasks[execution_id][task_id] = progress

            # Notify WebSocket subscribers
            self._notify_subscribers({
                "type": "task",
                "timestamp": progress.timestamp,
                "execution_id": execution_id,
                "tasks": {k: v.model_dump() for k, v in self.tasks[execution_id].items()}
            })

            logging.debug(f"Started task: {execution_id}:{task_id}")

    def update_task_progress(self, execution_id: str, task_id: str, percentage: int):
        """Update progress for a running task and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.tasks:
                self.tasks[execution_id] = {}
                logging.info(f"Initialized progress tracking for execution {execution_id}")

            task_info = self.task_info.get(execution_id, {}).get(task_id, {})

            # Check if task exists and handle progress logic
            if task_id not in self.tasks[execution_id]:
                progress = TaskProgress(
                    task_id=task_id,
                    task_name=task_info.name,
                    run=task_info.run,
                    percentage=0,
                    timestamp=time.time(),
                    status="running"
                )
                self.tasks[execution_id][task_id] = progress

            # Clamp percentage to valid range
            percentage = max(0, min(percentage, 100))

            progress = self.tasks[execution_id][task_id]
            if progress.status != "running" or percentage < progress.percentage:
                return  # Don't update future progress

            # Update task progress
            progress = TaskProgress(
                task_id=task_id,
                task_name=task_info.name,
                run=task_info.run,
                percentage=percentage,
                timestamp=time.time(),
                status="running"
            )

            self.tasks[execution_id][task_id] = progress

            # Notify WebSocket subscribers
            self._notify_subscribers({
                "type": "task",
                "timestamp": progress.timestamp,
                "execution_id": execution_id,
                "tasks": {k: v.model_dump() for k, v in self.tasks[execution_id].items()}
            })

            logging.debug(f"Updated task progress: {execution_id}:{task_id} -> {percentage}%")

    def finish_task(self, execution_id: str, task_id: str, failed=False):
        """Finish a task and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.tasks:
                self.tasks[execution_id] = {}
                logging.info(f"Initialized progress tracking for execution {execution_id}")

            # Create or update task progress with 100% and completed status
            task_info = self.task_info.get(execution_id, {}).get(task_id, {})
            if (
                task_id in self.tasks[execution_id]
                and self.tasks[execution_id][task_id].status == "failed"
            ):
                return
            progress = TaskProgress(
                task_id=task_id,
                task_name=task_info.name,
                run=task_info.run,
                percentage=100,
                timestamp=time.time(),
                status="failed" if failed else "completed"
            )

            self.tasks[execution_id][task_id] = progress

            # Notify WebSocket subscribers
            self._notify_subscribers({
                "type": "task",
                "timestamp": progress.timestamp,
                "execution_id": execution_id,
                "tasks": {k: v.model_dump() for k, v in self.tasks[execution_id].items()}
            })

            logging.debug(f"Finished task: {execution_id}:{task_id}")

    def discard_task(self, execution_id: str, task_id: str):
        """Mark a task as discarded and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.tasks:
                self.tasks[execution_id] = {}
                logging.info(f"Initialized progress tracking for execution {execution_id}")

            # Create or update task progress with discarded status
            task_info = self.task_info.get(execution_id, {}).get(task_id, {})
            progress = TaskProgress(
                task_id=task_id,
                task_name=getattr(task_info, 'name', None),
                run=getattr(task_info, 'run', None),
                percentage=0,
                timestamp=time.time(),
                status="discarded"
            )

            self.tasks[execution_id][task_id] = progress

            # Update execution completed_tasks count
            if execution_id in self.executions:
                self.executions[execution_id].completed_tasks += 1

            # Notify WebSocket subscribers
            self._notify_subscribers({
                "type": "task",
                "timestamp": progress.timestamp,
                "execution_id": execution_id,
                "tasks": {k: v.model_dump() for k, v in self.tasks[execution_id].items()}
            })

            logging.debug(f"Discarded task: {execution_id}:{task_id}")

    def cached_task(self, execution_id: str, task_id: str):
        """Mark a task as cached (skipped due to cache hit) and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.tasks:
                self.tasks[execution_id] = {}
                logging.info(f"Initialized progress tracking for execution {execution_id}")

            # Create or update task progress with cached status
            task_info = self.task_info.get(execution_id, {}).get(task_id, {})
            progress = TaskProgress(
                task_id=task_id,
                task_name=getattr(task_info, 'name', None),
                run=getattr(task_info, 'run', None),
                percentage=100,
                timestamp=time.time(),
                status="cached"
            )

            self.tasks[execution_id][task_id] = progress

            # Update execution completed_tasks count
            if execution_id in self.executions:
                self.executions[execution_id].completed_tasks += 1

            # Notify WebSocket subscribers
            self._notify_subscribers({
                "type": "task",
                "timestamp": progress.timestamp,
                "execution_id": execution_id,
                "tasks": {k: v.model_dump() for k, v in self.tasks[execution_id].items()}
            })

            logging.debug(f"Cached task: {execution_id}:{task_id}")

    def register_tasks_information(self, execution_id: str, tasks: Dict[str, Dict[str, str]]):
        with self._data_lock:
            self.task_info[execution_id] = {
                task_id: TaskInfo(**task_info) for task_id, task_info in tasks.items()
            }

    def start_execution(self, execution_id: str, total_tasks: int):
        """Start an execution and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.executions:
                return

            # Store execution metadata with 0 completed tasks
            status = self.executions[execution_id]
            status.total_tasks = total_tasks
            status.started_at = time.time()
            status.status = "running"

            # Notify subscribers about execution start
            self._notify_subscribers({
                "type": "execution",
                "timestamp": time.time(),
                "executions": [v.model_dump() for v in self.executions.values()]
            })

            logging.info(f"Started execution {execution_id} with {total_tasks} tasks")

    def update_execution_progress(self, execution_id: str, completed_tasks: int, total_tasks: int):
        """Update execution progress and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.executions:
                return

            # Clamp values to valid range
            completed_tasks = max(0, min(completed_tasks, total_tasks))

            # Store execution metadata
            status = self.executions[execution_id]
            status.completed_tasks = completed_tasks
            status.total_tasks = total_tasks

            # Notify subscribers about execution progress
            self._notify_subscribers({
                "type": "execution",
                "timestamp": time.time(),
                "executions": [v.model_dump() for v in self.executions.values()]
            })

            logging.debug(f"Updated execution progress: {execution_id} -> {completed_tasks}/{total_tasks}")

    def finish_execution(self, execution_id: str, total_tasks: int) -> ExecutionStatus:
        """Finish an execution and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.executions:
                return

            # Update execution metadata
            status = self.executions[execution_id]
            status.completed_tasks = total_tasks
            status.total_tasks = total_tasks
            status.completed_at = time.time()
            status.status = "completed" if total_tasks > 0 else "failed"

            # Notify subscribers about execution completion
            self._notify_subscribers({
                "type": "execution_complete",
                "execution_id": execution_id,
                "timestamp": time.time(),
                "executions": [v.model_dump() for v in self.executions.values()]
            })

            logging.info(f"Finished execution {execution_id} with {total_tasks} tasks")

            return status

    def _notify_subscribers(self, message: dict):
        """Notify all WebSocket subscribers for an execution.

        Note: This method is called while _data_lock is held, so it must NOT
        call unregister_websocket_callback (which also acquires _data_lock),
        as _data_lock is non-reentrant and would deadlock.
        """
        dead_callbacks = []
        for callback in self.websocket_callbacks:
            try:
                callback(message)
            except Exception as e:
                logging.error(f"Failed to notify subscriber: {e}")
                dead_callbacks.append(callback)

        # Remove failed callbacks inline (already holding _data_lock)
        for callback in dead_callbacks:
            try:
                self.websocket_callbacks.remove(callback)
            except ValueError:
                pass

    def create_execution(self, workflow) -> ExecutionStatus:
        with self._data_lock:
            import uuid
            execution_id = str(uuid.uuid4())
            status = ExecutionStatus(
                execution_id=execution_id,
                workflow_id=workflow.name,
                status="waiting",
            )
            self.executions[execution_id] = status

            return status

    def get_executions(self) -> Dict[str, ExecutionStatus]:
        with self._data_lock:
            return self.executions.copy()

    def get_progress(self, execution_id: str) -> Dict[str, TaskProgress]:
        """Get current progress for an execution."""
        with self._data_lock:
            print("tasks keys:", list(self.tasks.keys()))
            print("tasks info:", list(self.task_info.keys()))
            return self.tasks.get(execution_id, {}).copy()

    def cleanup_execution(self, execution_id: str):
        """Clean up data for a completed execution."""
        with self._data_lock:
            if execution_id in self.executions:
                del self.executions[execution_id]
            if execution_id in self.tasks:
                del self.tasks[execution_id]
            if execution_id in self.websocket_callbacks:
                del self.websocket_callbacks[execution_id]


# Global singleton instance
progress_store = ProgressStore()