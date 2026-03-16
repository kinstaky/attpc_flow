"""Workflow node wrappers for HDF5 storage.

These nodes are thin adapters over the class-based storage API in
``attpc_storage.hdf5``. They keep the current ``Node`` interface usable today
while staying close to the planned processor design where storage nodes are
stream boundaries.
"""

from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel, ConfigDict

from atflow.node import Node
from atflow.node_manager import auto_register_node

from .hdf5 import Hdf5Reader, Hdf5Writer, MetaTuple


class Hdf5ReaderParameters(BaseModel):
    """Validated execution parameters for ``Hdf5ReaderNode``."""

    model_config = ConfigDict(extra="ignore")

    workspace: str
    run: int
    path: str
    dataset: str


class Hdf5WriterParameters(BaseModel):
    """Validated execution parameters for ``Hdf5WriterNode``."""

    model_config = ConfigDict(extra="ignore")

    workspace: str
    run: int
    path: str
    dataset: str


class Hdf5CheckpointParameters(BaseModel):
    """Validated execution parameters for ``Hdf5CheckpointNode``."""

    model_config = ConfigDict(extra="ignore")

    workspace: str
    run: int
    path: str
    dataset: str


@auto_register_node
class Hdf5ReaderNode(Node):
    """Workflow wrapper around :class:`attpc_storage.hdf5.Hdf5Reader`."""
    _name: str = "hdf5_reader"
    _version: str = "0.1.0"
    _description = "Read from HDF5 file dataset as event"
    _category = "storage"
    _type = "reader"
    _inputs = {}
    _outputs = {"event": "matrix"}
    _properties = {"path": "str", "dataset": "str"}
    _parameters = Hdf5ReaderParameters

    def __init__(self, workspace: str, run: int, path: str, dataset: str) -> None:
        super().__init__()
        self._reader = Hdf5Reader(
            workspace=workspace,
            run=run,
            path=path,
            dataset=dataset,
        )
        self.event_meta: MetaTuple | None = None

    def __del__(self) -> None:
        """Close the reader if the node instance is released."""
        if self._reader is not None:
            self._reader.close()

    def get_range(self) -> tuple[int, int]:
        return self._reader.get_range()

    def event_id(self) -> int:
        return self._reader.event_id()

    def execute(self) -> list[Any]:
        """Get next event."""
        self.event_meta, event = self._reader.read()
        return [event]


@auto_register_node
class Hdf5WriterNode(Node):
    """Workflow wrapper around :class:`attpc_storage.hdf5.Hdf5Writer`."""

    _name: str = "hdf5_writer"
    _version: str = "0.1.0"
    _description = "Write one event matrix at a time into an HDF5 dataset"
    _category = "storage"
    _type = "writer"
    _inputs = {"event": "matrix"}
    _outputs = {}
    _properties = {"path": "str", "dataset": "str"}
    _parameters = Hdf5WriterParameters

    def __init__(
            self,
            workspace: str,
            run: int,
            path: str,
            dataset: str,
        ) -> None:
        super().__init__()
        self._writer = Hdf5Writer(
            workspace=workspace,
            run=run,
            path=path,
            dataset=dataset,
        )

    def __del__(self) -> None:
        """Close the writer if the node instance is released."""
        if self._writer is not None:
            self._writer.close()

    def execute(self, **kwargs: Any) -> list[Any]:
        """Write event."""
        self._writer.write(kwargs["meta"], kwargs["event"])
        return []


@auto_register_node
class Hdf5CheckpointNode(Node):
    """Checkpoint sugar node lowered by the processor into reader/writer nodes."""

    _name: str = "hdf5_checkpoint"
    _version: str = "0.1.0"
    _description = "Write then read back one event matrix through HDF5"
    _category = "storage"
    _type = "checkpoint"
    _inputs = {"event": "matrix"}
    _outputs = {"event": "matrix"}
    _properties = {"path": "str", "dataset": "str"}
    _parameters = Hdf5CheckpointParameters

    def execute(self, **kwargs: Any) -> list[Any]:
        """Return the reader and writer node names used for checkpoint lowering."""
        return ["hdf5_writer", "hdf5_reader"]
