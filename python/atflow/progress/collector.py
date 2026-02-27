"""
ZMQ collectors for ATTPC Flow progress reporting.
Separated from processor to enable independent process management.
"""

import zmq
import logging
from tqdm import tqdm
from .progress_store import progress_store

def zmq_collector_tqdm():
    """Original tqdm-based progress collector for terminal display."""
    ctx = zmq.Context()
    subscriber = ctx.socket(zmq.PULL)
    subscriber.bind("ipc://@attpc_flow_zmq")

    # Dictionary to track progress bars for each task: {task_id: pbar}
    progress_bars = {}
    # Next available position

    while True:
        try:
            msg = subscriber.recv().decode("utf-8").split(",")
            if msg[0] == "termination":
                logging.debug("Received system termination message.")
                break

            if msg[0] != "task":
                continue

            command = msg[1]
            execution_id = msg[2]
            task_id = msg[3]

            if command == "start":
                # Handle start message - create new progress bar
                if task_id not in progress_bars:
                    progress_bars[task_id] = tqdm(
                        total=100,
                        desc=f"Task {task_id}",
                        unit="%",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                    )
                    logging.info(f"Started progress bar for task {task_id}.")

            elif command == "finish":
                # Handle finish message
                if task_id in progress_bars:
                    progress_bars[task_id].update(max(0, 100-progress_bars[task_id].n))
                    logging.info(f"Finished progress bar for task {task_id}.")
                progress_store.finish_task(execution_id, task_id)

            else:
                # Handle progress message (legacy format or percentage)
                try:
                    percentage = int(msg[4])

                    # Create progress bar if it doesn't exist (for legacy compatibility)
                    if task_id not in progress_bars:
                        progress_bars[task_id] = tqdm(
                            total=100,
                            desc=f"Task {task_id}",
                            unit="%",
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                        )

                    # Update progress bar
                    current_value = progress_bars[task_id].n
                    increment = max(0, min(percentage - current_value, 100 - current_value))
                    if increment > 0:
                        progress_bars[task_id].update(increment)

                    logging.debug(f"Updated progress bar for task {task_id} to {percentage}%")

                except ValueError:
                    logging.warning(f"Received unknown message type: {command}")

        except zmq.ZMQError as e:
            logging.error(f"ZMQ error in tqdm collector: {e}")

    # # Close all progress bars
    # for pbar in progress_bars.values():
    #     pbar.close()

def zmq_collector_store():
    """Progress store collector for web UI display."""
    ctx = zmq.Context()
    subscriber = ctx.socket(zmq.PULL)
    subscriber.bind("ipc://@attpc_flow_zmq")

    logging.info("Store zmq collector started, listening for progress messages")

    while True:
        try:
            msg = subscriber.recv().decode("utf-8").split(",")
            if msg[0] == "termination" :
                logging.info(f"Received terminal message: {msg[0]}")
                break

            if msg[0] == "task":
                command = msg[1]
                execution_id = msg[2]
                task_id = msg[3]

                if command == "start":
                    # Handle start message
                    logging.debug(f"Received start: Execution {execution_id}, Task {task_id}")
                    # Could initialize task progress to 0 here if needed
                    progress_store.start_task(execution_id=execution_id, task_id=task_id)

                elif command == "finish":
                    # Handle finish message
                    logging.debug(f"Received finish: Execution {execution_id}, Task {task_id}")
                    # Set progress to 100% on finish
                    progress_store.finish_task(execution_id=execution_id, task_id=task_id)

                elif command == "failed":
                    # Handle failed message
                    logging.error(f"Received failed: Execution {execution_id}, Task {task_id}")
                    # Set progress to 100% on finish
                    progress_store.finish_task(
                        execution_id=execution_id,
                        task_id=task_id,
                        failed=True
                    )

                elif command == "discard":
                    # Handle discard message
                    logging.debug(f"Received discard: Execution {execution_id}, Task {task_id}")
                    # Set task discarded
                    progress_store.discard_task(execution_id=execution_id, task_id=task_id)

                elif command == "cached":
                    # Handle cacahed message
                    logging.debug(f"Received cached: Execution {execution_id}, Task {task_id}")
                    # Set task discarded
                    progress_store.cached_task(execution_id=execution_id, task_id=task_id)

                else:
                    # Handle progress message
                    try:
                        percentage = int(msg[4])
                        # logging.debug(f"Received progress: Execution {execution_id}, Task {task_id}, {percentage}%")
                        progress_store.update_task_progress(
                            execution_id=execution_id,
                            task_id=task_id,
                            percentage=percentage
                        )
                    except ValueError:
                        logging.warning(f"Received unknown message type: {command}")
            elif msg[0] == "execution":
                command = msg[1]
                execution_id = msg[2]

                if command == "start":
                    total_tasks = int(msg[3])
                    # Handle start message
                    logging.debug(f"Received start: Execution {execution_id}, {total_tasks} tasks")
                    # Could initialize task progress to 0 here if needed
                    progress_store.start_execution(execution_id=execution_id, total_tasks=total_tasks)
                elif command == "finish":
                    total_tasks = int(msg[3])
                    # Handle finish message
                    logging.debug(f"Received finish: Execution {execution_id}")
                    # Set progress to 100% on finish
                    progress_store.finish_execution(execution_id=execution_id, total_tasks=total_tasks)
                else:
                    completed_tasks = int(msg[3])
                    total_tasks = int(msg[4])
                    # Handle progress message
                    # logging.debug(f"Received progress: Execution {execution_id}, {completed_tasks}/{total_tasks} tasks")
                    progress_store.update_execution_progress(
                        execution_id=execution_id,
                        completed_tasks=completed_tasks,
                        total_tasks=total_tasks
                    )

        except zmq.ZMQError as e:
            logging.error(f"ZMQ error in store collector: {e}")

    logging.info("Store zmq collector shutting down")
