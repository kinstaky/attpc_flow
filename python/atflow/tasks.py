"""Task structures and task runners for ATTPC Flow.

These runners operate on already-lowered tasks. In particular, `EventTask`
expects that:

- event-node execution order is precomputed,
- literal and external-task values are already attached to each node,
- only per-event linked values remain to be provided through slot routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from abc import ABC, abstractmethod
from typing import Any
import zmq

from .node_manager import NodeManager
from .progress.progress_store import progress_store


class TaskStatus(IntEnum):
    DISCARDED = -2
    FAILED = -1
    COMPLETED = 0
    WAITING = 1
    READY = 2
    QUEUED = 3
    RUNNING = 4
    CACHED = 5


@dataclass
class Dependency:
    """One unresolved dependency value that must be filled from another task's output."""
    parameter_name: str
    task: int
    index: int

@dataclass
class Task(ABC):
    """A task for execution."""
    execution_id: str
    id: int
    environment: dict[str, Any]
    name: str
    outputs: list[Any]
    waiting: list[int]
    status: TaskStatus

    @abstractmethod
    def run(self) -> list[Any]:
        ...

@dataclass
class BatchTask:
    """A one-shot task for normal run-scoped node execution."""
    parameteres: dict[str, Any]
    dependencies: list[Dependency]

    def run(self) -> list[Any]:
        manager = NodeManager
        return manager.execute_node(
            name=self.name,
            execution_id=self.execution_id,
            taskk_id=self.id,
            environment=self.environment,
            parameters=self.parameters,
        )

@dataclass
class EventTaskUnit:
    """One compiled event node inside an `EventTask`."""
    id: int
    name: str
    parameters: dict[str, object]
    dependencies: dict[str, (int, int)]  # [input_name: (unit_id, output_index)]


@dataclass
class EventTask(Task):
    """One compiled stream->event...->stream region."""
    units: list[EventTaskUnit]

    def run(self) -> list[Any]:
        manager = NodeManager()
        # Stream nodes and event nodes are instantiated once per task execution so
        # the event loop can reuse them across all events in the run.
        nodes = []
        for unit in self.units:
            param = {
                **self.environment,
                **unit.parameters,
            }
            node_class = manager.get_node(unit.name)
            param = node_class.parameters_model()(**param).model_dump()
            nodes.append(manager.create_node(unit.name, **param))

        # cnt = 0
        try:
            ctx = zmq.Context()
            socket = ctx.socket(zmq.PUSH)
            socket.connect("ipc://@attpc_flow_zmq")
            socket.send_string(f"task,start,{self.execution_id},{self.id}")
            last_percentage = 0
            event_range = nodes[0].get_range()
            total = event_range[1] - event_range[0]
            cnt = 0
            print(f"Event range: {event_range}, total events: {total}")

            while True:
                # if cnt >= 10:
                    # break
                # cnt += 1

                outputs = [None] * len(nodes)

                # reader
                reader = nodes[0]
                outputs[0] = reader.execute()
                # read last event
                if outputs[0] is None:
                    break
                # print(f"  --- Loop {cnt} step 0 node {nodes[0].name()} ---")
                # print(outputs[0])

                for idx in range(1, len(nodes)-1):
                    inputs = {
                        name: outputs[dep[0]][dep[1]]
                        for name, dep in self.units[idx].dependencies.items()
                    }
                    outputs[idx] = nodes[idx].execute(**inputs)
                    # print(f"  --- Loop {cnt} step {idx} {nodes[idx].name()} ---")
                    # print(outputs[idx])

                # writer
                writer = nodes[-1]
                payload = {
                    name: outputs[dep[0]][dep[1]]
                    for name, dep in self.units[-1].dependencies.items()
                }
                payload["meta"] = reader.event_meta
                writer.execute(**payload)
                # print(f"--- Loop {cnt} finished ---")

                cnt += 1
                percentage = int(100 * cnt / total)
                if percentage > last_percentage:
                    socket.send_string(f"task,progress,{self.execution_id},{self.id},{percentage}")
                    last_percentage = percentage
        finally:
            socket.send_string(f"task,finish,{self.execution_id},{self.id}")
            del nodes

        return []