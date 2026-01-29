"""
Centralized progress store for ATTPC Flow.
Handles progress data storage and WebSocket broadcasting.
"""

import threading
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class TaskProgress:
    task_id: str
    percentage: float
    timestamp: float
    status: str = "running"

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
        self.data: Dict[str, Dict[str, TaskProgress]] = {}  # {execution_id: {task_id: TaskProgress}}
        self.websocket_callbacks: Dict[str, List[Callable]] = {}  # {execution_id: [callbacks]}
        self._data_lock = threading.Lock()

    def register_websocket_callback(self, execution_id: str, callback: Callable):
        """Register a WebSocket callback for progress updates."""
        with self._data_lock:
            if execution_id not in self.websocket_callbacks:
                self.websocket_callbacks[execution_id] = []
            self.websocket_callbacks[execution_id].append(callback)

    def unregister_websocket_callback(self, execution_id: str, callback: Callable):
        """Unregister a WebSocket callback."""
        with self._data_lock:
            if execution_id in self.websocket_callbacks:
                try:
                    self.websocket_callbacks[execution_id].remove(callback)
                except ValueError:
                    pass  # Callback already removed

    def update_progress(self, execution_id: str, task_id: str, percentage: float):
        """Update progress for a task and notify WebSocket subscribers."""
        with self._data_lock:
            # Initialize execution data if needed
            if execution_id not in self.data:
                self.data[execution_id] = {}

            # Update task progress
            status = "completed" if percentage >= 100 else "running"
            progress = TaskProgress(
                task_id=task_id,
                percentage=percentage,
                timestamp=time.time(),
                status=status
            )
            self.data[execution_id][task_id] = progress

            # Notify WebSocket subscribers
            if execution_id in self.websocket_callbacks:
                message = {
                    "type": "progress",
                    "data": {
                        "task_id": task_id,
                        "percentage": percentage,
                        "timestamp": progress.timestamp,
                        "status": status
                    }
                }

                # Remove dead callbacks
                dead_callbacks = []
                for callback in self.websocket_callbacks[execution_id]:
                    try:
                        callback(message)
                    except Exception as e:
                        logging.error(f"WebSocket callback failed: {e}")
                        dead_callbacks.append(callback)

                for callback in dead_callbacks:
                    self.websocket_callbacks[execution_id].remove(callback)

    def mark_execution_complete(self, execution_id: str):
        """Mark an execution as complete and notify subscribers."""
        with self._data_lock:
            if execution_id in self.websocket_callbacks:
                message = {
                    "type": "completion",
                    "timestamp": time.time()
                }

                dead_callbacks = []
                for callback in self.websocket_callbacks[execution_id]:
                    try:
                        callback(message)
                    except Exception as e:
                        logging.error(f"WebSocket callback failed: {e}")
                        dead_callbacks.append(callback)

                for callback in dead_callbacks:
                    self.websocket_callbacks[execution_id].remove(callback)

    def get_progress(self, execution_id: str) -> Dict[str, TaskProgress]:
        """Get current progress for an execution."""
        with self._data_lock:
            return self.data.get(execution_id, {}).copy()

    def cleanup_execution(self, execution_id: str):
        """Clean up data for a completed execution."""
        with self._data_lock:
            if execution_id in self.data:
                del self.data[execution_id]
            if execution_id in self.websocket_callbacks:
                del self.websocket_callbacks[execution_id]

# Global singleton instance
progress_store = ProgressStore()
