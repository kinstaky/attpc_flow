"""Workflow node wrappers for HDF5 storage.

These nodes are thin adapters over the class-based storage API in
``attpc_storage.hdf5``. They keep the current ``Node`` interface usable today
while staying close to the planned processor design where storage nodes are
stream boundaries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Type

from pydantic import BaseModel, ConfigDict

from atflow.node import Node
from atflow.node_manager import auto_register_node

from .hdf5 import Hdf5Reader, Hdf5Writer, MetaTuple


class _StorageNodeBase(Node):
    """Common helpers for storage nodes with runtime-bound HDF5 objects."""

    def __init__(self) -> None:
        self._storage_key: tuple[str, int, str, str] | None = None

    def _runtime_key(self, *, workspace: str, run: int, path: str, dataset: str) -> tuple[str, int, str, str]:
        """Build a key that identifies one concrete storage target."""
        return (workspace, run, path, dataset)


class Hdf5ReaderParameters(BaseModel):
    """Validated execution parameters for ``Hdf5ReaderNode``."""

    model_config = ConfigDict(extra="ignore")

    execution_id: str
    task_id: int
    workspace: str
    run: int
    path: str
    dataset: str
    start_event: int | None = None
    stop_event: int | None = None
    reset_iteration: bool = False


class Hdf5WriterParameters(BaseModel):
    """Validated execution parameters for ``Hdf5WriterNode``."""

    model_config = ConfigDict(extra="ignore")

    execution_id: str
    task_id: int
    workspace: str
    run: int
    path: str
    dataset: str
    event: Any
    meta: MetaTuple | None = None
    event_id: int | None = None
    orig_run: int | None = None
    orig_event: int | None = None


class Hdf5CheckpointParameters(Hdf5WriterParameters):
    """Checkpoint node shares the writer parameter contract."""

    pass


@auto_register_node
class Hdf5ReaderNode(_StorageNodeBase):
    """Workflow wrapper around :class:`attpc_storage.hdf5.Hdf5Reader`."""

    def __init__(self) -> None:
        super().__init__()
        self._reader: Hdf5Reader | None = None
        self.last_meta: MetaTuple | None = None

    def __del__(self) -> None:
        """Close the reader if the node instance is released."""
        if self._reader is not None:
            self._reader.close()

    @property
    def name(self) -> str:
        return "hdf5_reader"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Read one event matrix at a time from an HDF5 dataset family"

    @property
    def category(self) -> str:
        return "storage"

    @property
    def type(self) -> str:
        return "stream"

    @property
    def inputs(self) -> Dict[str, str]:
        return {}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"event": "matrix"}

    @property
    def properties(self) -> Dict[str, str]:
        return {"path": "str", "dataset": "str"}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return Hdf5ReaderParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        """Create or reuse a reader, then return the next event matrix."""
        key = self._runtime_key(
            workspace=kwargs["workspace"],
            run=kwargs["run"],
            path=kwargs["path"],
            dataset=kwargs["dataset"],
        )
        # The current NodeManager constructs nodes with no runtime arguments, so
        # the real HDF5 object has to be created lazily on first execute.
        if self._reader is None or self._storage_key != key:
            if self._reader is not None:
                self._reader.close()
            self._reader = Hdf5Reader(
                workspace=kwargs["workspace"],
                run=kwargs["run"],
                path=kwargs["path"],
                dataset=kwargs["dataset"],
            )
            self._storage_key = key

        if kwargs.get("start_event") is not None or kwargs.get("stop_event") is not None:
            current_start, current_stop = self._reader.get_range()
            self._reader.set_range(
                kwargs.get("start_event", current_start),
                kwargs.get("stop_event", current_stop),
            )
        elif kwargs.get("reset_iteration"):
            self._reader.reset()

        result = self._reader.read()
        if result is None:
            self.last_meta = None
            return [None]

        self.last_meta, event = result
        return [event]


@auto_register_node
class Hdf5WriterNode(_StorageNodeBase):
    """Workflow wrapper around :class:`attpc_storage.hdf5.Hdf5Writer`."""

    def __init__(self) -> None:
        super().__init__()
        self._writer: Hdf5Writer | None = None

    def __del__(self) -> None:
        """Close the writer if the node instance is released."""
        if self._writer is not None:
            self._writer.close()

    @property
    def name(self) -> str:
        return "hdf5_writer"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Write one event matrix at a time into an HDF5 dataset family"

    @property
    def category(self) -> str:
        return "storage"

    @property
    def type(self) -> str:
        return "stream"

    @property
    def inputs(self) -> Dict[str, str]:
        return {"event": "matrix"}

    @property
    def outputs(self) -> Dict[str, str]:
        return {}

    @property
    def properties(self) -> Dict[str, str]:
        return {"path": "str", "dataset": "str"}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return Hdf5WriterParameters

    def _resolve_meta(self, **kwargs: Any) -> MetaTuple:
        """Accept explicit meta or reconstruct it from runtime fields."""
        meta = kwargs.get("meta")
        if meta is not None:
            return tuple(int(value) for value in meta)  # type: ignore[return-value]

        event_id = kwargs.get("event_id")
        if event_id is None:
            raise ValueError("Hdf5WriterNode requires runtime meta or event_id")
        orig_run = kwargs["run"] if kwargs.get("orig_run") is None else kwargs["orig_run"]
        orig_event = event_id if kwargs.get("orig_event") is None else kwargs["orig_event"]
        return int(event_id), int(orig_run), int(orig_event)

    def execute(self, **kwargs: Any) -> List[Any]:
        """Create or reuse a writer, then store one event matrix."""
        key = self._runtime_key(
            workspace=kwargs["workspace"],
            run=kwargs["run"],
            path=kwargs["path"],
            dataset=kwargs["dataset"],
        )
        if self._writer is None or self._storage_key != key:
            if self._writer is not None:
                self._writer.close()
            self._writer = Hdf5Writer(
                workspace=kwargs["workspace"],
                run=kwargs["run"],
                path=kwargs["path"],
                dataset=kwargs["dataset"],
            )
            self._storage_key = key

        meta = self._resolve_meta(**kwargs)
        self._writer.write(meta, kwargs["event"])
        return []


@auto_register_node
class Hdf5CheckpointNode(_StorageNodeBase):
    """Write an event to HDF5 and immediately read it back.

    This is a convenience node for current workflows. In the longer-term
    processor design, checkpointing is expected to be lowered into distinct
    writer and reader boundaries.
    """

    def __init__(self) -> None:
        super().__init__()
        self._writer: Hdf5Writer | None = None
        self._reader: Hdf5Reader | None = None
        self.last_meta: MetaTuple | None = None

    def __del__(self) -> None:
        """Close any held reader and writer objects."""
        if self._writer is not None:
            self._writer.close()
        if self._reader is not None:
            self._reader.close()

    @property
    def name(self) -> str:
        return "hdf5_checkpoint"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Write then read back one event matrix through HDF5"

    @property
    def category(self) -> str:
        return "storage"

    @property
    def type(self) -> str:
        return "stream"

    @property
    def inputs(self) -> Dict[str, str]:
        return {"event": "matrix"}

    @property
    def outputs(self) -> Dict[str, str]:
        return {"event": "matrix"}

    @property
    def properties(self) -> Dict[str, str]:
        return {"path": "str", "dataset": "str"}

    @property
    def parameters_model(self) -> Type[BaseModel]:
        return Hdf5CheckpointParameters

    def execute(self, **kwargs: Any) -> List[Any]:
        """Persist an event through HDF5, then read back the same event id."""
        key = self._runtime_key(
            workspace=kwargs["workspace"],
            run=kwargs["run"],
            path=kwargs["path"],
            dataset=kwargs["dataset"],
        )
        if self._writer is None or self._storage_key != key:
            if self._writer is not None:
                self._writer.close()
            self._writer = Hdf5Writer(
                workspace=kwargs["workspace"],
                run=kwargs["run"],
                path=kwargs["path"],
                dataset=kwargs["dataset"],
            )
            self._storage_key = key

        meta = kwargs.get("meta")
        if meta is None:
            event_id = kwargs.get("event_id")
            if event_id is None:
                raise ValueError("Hdf5CheckpointNode requires runtime meta or event_id")
            meta = (
                int(event_id),
                int(kwargs["run"] if kwargs.get("orig_run") is None else kwargs["orig_run"]),
                int(event_id if kwargs.get("orig_event") is None else kwargs["orig_event"]),
            )

        self._writer.write(meta, kwargs["event"])
        if self._reader is not None:
            self._reader.close()
        # Re-open the reader after the write so the read side sees the newly
        # written dataset and refreshed event-range attrs.
        self._reader = Hdf5Reader(
            workspace=kwargs["workspace"],
            run=kwargs["run"],
            path=kwargs["path"],
            dataset=kwargs["dataset"],
        )
        self._reader.set_range(int(meta[0]), int(meta[0]))
        self._reader.reset()
        result = self._reader.read()
        if result is None:
            self.last_meta = None
            return [None]
        self.last_meta, event = result
        return [event]
