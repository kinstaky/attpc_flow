"""
ZMQ collectors for ATTPC Flow progress reporting.
Separated from processor to enable independent process management.
"""

import zmq
import threading
import logging
from tqdm import tqdm
from .progress_store import progress_store

def zmq_collector_tqdm(max_workers):
    """Original tqdm-based progress collector for terminal display."""
    ctx = zmq.Context()
    subscriber = ctx.socket(zmq.PULL)
    subscriber.bind("ipc://@attpc_flow_zmq")

    # Dictionary to track progress bars for each task: {task_id: (pbar, position)}
    progress_bars = {}
    # Available positions pool (0 to max_workers-1)
    available_positions = list(range(max_workers))
    # Lock for thread-safe position management
    position_lock = threading.Lock()

    while True:
        try:
            msg = subscriber.recv().decode("utf-8").split(",")
            if msg[0] == "-1":
                logging.debug("Received terminal message: -1")
                break
            task_id = msg[1]
            percentage = float(msg[2])

            # Create progress bar for new tasks
            if task_id not in progress_bars:
                with position_lock:
                    if not available_positions:
                        logging.warning(f"No available position for task {task_id}")
                        continue
                    position = available_positions.pop(0)
                progress_bars[task_id] = (
                    tqdm(
                        total=100,
                        desc=f"Task {task_id}",
                        position=position,
                        leave=False,
                        unit="%",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                    ),
                    position
                )

            # Update progress bar
            pbar, _ = progress_bars[task_id]
            current_value = pbar.n
            increment = max(0, min(percentage - current_value, 100 - current_value))
            if increment > 0:
                pbar.update(increment)

            # Close progress bar if task is complete
            if percentage >= 100:
                pbar, position = progress_bars[task_id]
                pbar.close()
                del progress_bars[task_id]
                with position_lock:
                    available_positions.append(position)
                    available_positions.sort()

        except zmq.ZMQError as e:
            logging.error(f"ZMQ error: {e}")

    # Close all progress bars
    for pbar, _ in progress_bars.values():
        pbar.close()

def zmq_collector_store():
    """Progress store collector for web UI display."""
    ctx = zmq.Context()
    subscriber = ctx.socket(zmq.PULL)
    subscriber.bind("ipc://@attpc_flow_zmq")

    while True:
        try:
            msg = subscriber.recv().decode("utf-8").split(",")
            if msg[0] == "-1":
                logging.debug(f"Received terminal message: {msg[0]}")
                break
            if len(msg) != 3:
                continue

            execution_id = msg[0]
            task_id = msg[1]
            percentage = float(msg[2])

            progress_store.update_progress(execution_id, task_id, percentage)
            # logging.debug(f"Updated progress: Execution {execution_id}, task {task_id}, progress {percentage}%")

        except zmq.ZMQError as e:
            logging.error(f"ZMQ error in store collector: {e}")

    logging.info("Store zmq collector shutting down")
