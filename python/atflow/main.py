"""
Process manager for ATTPC Flow.
Manages server, collector, and worker processes/threads.
"""

import multiprocessing as mp
import threading
import signal
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .processor import Processor
from .collector import zmq_collector_tqdm, zmq_collector_store
from .progress_store import progress_store

logger = logging.getLogger(__name__)

class ATFlowManager:
    """Manages ATTPC Flow processes and threads."""

    def __init__(self):
        self.processes: Dict[str, mp.Process] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.workflow_queue: Optional[mp.Queue] = None
        self.running = False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)

    def start_server_only(self, host="0.0.0.0", port=8000):
        """Start only the FastAPI server."""
        from .server import run_server
        logger.info(f"Starting ATTPC Flow server on {host}:{port}")
        run_server(host=host, port=port)

    def start_worker_only(self):
        """Start only the worker process."""
        if not self.workflow_queue:
            raise RuntimeError("Workflow queue not initialized")

        logger.info("Starting ATTPC Flow worker")
        self._workflow_worker(self.workflow_queue)

    def start_collector_only(self, collector_type="tqdm", execution_id=None):
        """Start only the ZMQ collector."""
        logger.info(f"Starting ATTPC Flow collector ({collector_type})")

        if collector_type == "store" and execution_id:
            zmq_collector_store(4, execution_id)  # max_workers = 4
        else:
            zmq_collector_tqdm(4)  # max_workers = 4

    def start_full_system(self, host="0.0.0.0", port=8000, collector_type="tqdm"):
        """Start the complete system: server + collector + worker."""
        logger.info("Starting ATTPC Flow full system")

        self.running = True
        self.setup_signal_handlers()

        # Create workflow queue
        self.workflow_queue = mp.Queue()

        # Initialize server with queue
        from .server import init_workflow_queue
        init_workflow_queue(self.workflow_queue)

        # Start collector thread
        if collector_type == "store":
            # For web UI, collector will be started per execution
            collector_thread = None
        else:
            # For terminal, start tqdm collector
            collector_thread = threading.Thread(
                target=zmq_collector_tqdm,
                args=(4,),  # max_workers
                daemon=True
            )
            collector_thread.start()
            self.threads["collector"] = collector_thread

        # Start worker process
        worker_process = mp.Process(
            target=self._workflow_worker,
            args=(self.workflow_queue,)
        )
        worker_process.start()
        self.processes["worker"] = worker_process

        try:
            # Start server in main process
            from .server import run_server
            run_server(host=host, port=port)
        except KeyboardInterrupt:
            logger.info("Server interrupted")
        finally:
            self.shutdown()

    def start_development_mode(self, host="0.0.0.0", port=8000):
        """Start development mode with frontend."""
        logger.info("Starting ATTPC Flow development mode")

        # Start frontend in background
        frontend_path = Path(__file__).parent.parent.parent / "frontend"
        if frontend_path.exists():
            import subprocess
            frontend_thread = threading.Thread(
                target=lambda: subprocess.run(["npm", "run", "dev"], cwd=frontend_path),
                daemon=True
            )
            frontend_thread.start()
            self.threads["frontend"] = frontend_thread

        # Start full system
        self.start_full_system(host=host, port=port, collector_type="store")

    def _workflow_worker(self, queue: mp.Queue):
        """Worker process that consumes workflows from the queue."""
        logger.info("Worker started")

        try:
            while True:
                try:
                    workflow_data = queue.get()
                    if workflow_data is None:  # Poison pill
                        logger.info("Worker received shutdown signal")
                        break

                    execution_id = workflow_data.execution_id
                    logger.info(f"Worker processing execution {execution_id}")

                    # Update execution status
                    from .server import executions
                    from datetime import datetime, timezone

                    if execution_id in executions:
                        executions[execution_id].started_at = datetime.now(timezone.utc).isoformat()
                        executions[execution_id].status = "running"

                    # Run workflow with processor
                    Processor.run(
                        threads=workflow_data.threads,
                        environment={
                            "workspace": workflow_data.workspace,
                            "run_list": workflow_data.run_list,
                        },
                        tasks=workflow_data.tasks
                    )

                    # Update execution status
                    if execution_id in executions:
                        executions[execution_id].status = "completed"
                        executions[execution_id].completed_at = datetime.now(timezone.utc).isoformat()
                    logger.info(f"Worker completed execution {execution_id}")

                except Exception as e:
                    if 'execution_id' in locals() and execution_id in executions:
                        executions[execution_id].status = "failed"
                        executions[execution_id].completed_at = datetime.now(timezone.utc).isoformat()
                    logger.error(f"Worker failed: {e}")

        except Exception as e:
            logger.error(f"Worker process error: {e}")

    def shutdown(self):
        """Gracefully shutdown all processes and threads."""
        if not self.running:
            return

        logger.info("Shutting down ATTPC Flow...")
        self.running = False

        # Send poison pill to worker
        if self.workflow_queue:
            self.workflow_queue.put(None)

        # Wait for worker process
        if "worker" in self.processes:
            worker = self.processes["worker"]
            worker.join(timeout=5)
            if worker.is_alive():
                logger.warning("Worker did not shut down gracefully, terminating...")
                worker.terminate()

        # Wait for threads
        for name, thread in self.threads.items():
            if thread.is_alive():
                logger.info(f"Waiting for {name} thread...")
                thread.join(timeout=2)

        logger.info("ATTPC Flow shutdown complete")

# Global manager instance
manager = ATFlowManager()
