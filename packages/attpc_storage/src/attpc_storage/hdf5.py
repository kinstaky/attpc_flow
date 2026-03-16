"""HDF5 storage primitives for ATTPC Flow.

This module implements the class-based storage API planned for phase-1:

- ``Hdf5Reader`` owns one input file handle and iterates event-by-event
- ``Hdf5Writer`` owns one output file handle and writes event-by-event

The reader and writer operate on generic matrix datasets. They resolve
``<workspace>`` and ``<run>`` in file paths once, then resolve ``<id>`` in
dataset paths for each event.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import h5py
import numpy as np

MetaTuple: TypeAlias = tuple[int, int, int]
"""Runtime event metadata as ``(event_id, orig_run, orig_event)``."""


def _split_hdf5_path(path: str) -> list[str]:
    """Split an HDF5 object path into components."""
    stripped = path.strip("/")
    return stripped.split("/") if stripped else []


def _join_hdf5_path(parts: list[str]) -> str:
    """Join HDF5 path components into an absolute object path."""
    return "/" + "/".join(parts) if parts else "/"


def _resolve_path(*, workspace: str, run: int, path: str) -> Path:
    """Resolve storage path placeholders into a concrete filesystem path."""
    resolved = path.replace("<workspace>", workspace).replace("<run>", str(run))
    resolved_path = Path(resolved)
    if "<workspace>" not in path and not resolved_path.is_absolute():
        resolved_path = Path(workspace) / resolved_path
    return resolved_path


def _resolve_dataset(*, dataset: str, event_id: int) -> str:
    """Resolve the runtime ``<id>`` placeholder in a dataset template."""
    return dataset.replace("<id>", str(event_id))


def _event_segment_pattern(dataset: str) -> tuple[int, str, str] | None:
    """Return the path segment that contains the event-id placeholder."""
    parts = _split_hdf5_path(dataset)
    for index, part in enumerate(parts):
        if "<id>" in part:
            prefix, suffix = part.split("<id>", 1)
            return index, prefix, suffix
    return None


def _event_container_path(dataset: str) -> str:
    """Return the group path that contains the per-event objects."""
    pattern = _event_segment_pattern(dataset)
    parts = _split_hdf5_path(dataset)
    if pattern is None:
        return _join_hdf5_path(parts[:-1])
    event_index, _, _ = pattern
    return _join_hdf5_path(parts[:event_index])


def _iter_ancestor_paths(path: str) -> list[str]:
    """Yield a path and its ancestors, from nearest to root."""
    parts = _split_hdf5_path(path)
    ancestors = [_join_hdf5_path(parts[:index]) for index in range(len(parts), -1, -1)]
    # `_join_hdf5_path([])` is `/`; keep a single root entry.
    deduped: list[str] = []
    for candidate in ancestors:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _open_group(handle: h5py.File, path: str) -> h5py.File | h5py.Group | None:
    """Open an existing HDF5 group-like object if it exists."""
    if path == "/":
        return handle
    return handle[path] if path in handle else None


def _read_range_from_attrs(handle: h5py.File, dataset: str) -> tuple[int, int] | None:
    """Read ``min_event`` and ``max_event`` from the nearest ancestor attrs."""
    for group_path in _iter_ancestor_paths(_event_container_path(dataset)):
        group = _open_group(handle, group_path)
        if group is None:
            continue
        attrs = group.attrs
        if "min_event" in attrs and "max_event" in attrs:
            return int(attrs["min_event"]), int(attrs["max_event"])
    return None


def _read_bad_events(handle: h5py.File, dataset: str) -> set[int]:
    """Read the nearest ``bad_events`` attribute and normalize it to a set."""
    for group_path in _iter_ancestor_paths(_event_container_path(dataset)):
        group = _open_group(handle, group_path)
        if group is None:
            continue
        attrs = group.attrs
        if "bad_events" in attrs:
            return {int(event_id) for event_id in np.asarray(attrs["bad_events"]).tolist()}
    return set()


def _infer_range_from_children(handle: h5py.File, dataset: str) -> tuple[int, int]:
    """Infer the event-id range by scanning children under the event container."""
    pattern = _event_segment_pattern(dataset)
    if pattern is None:
        raise KeyError(f"Dataset template has no <id> placeholder: {dataset}")

    event_index, prefix, suffix = pattern
    parts = _split_hdf5_path(dataset)
    container_path = _join_hdf5_path(parts[:event_index])
    group = _open_group(handle, container_path)
    if group is None:
        raise KeyError(f"Event container group not found: {container_path}")

    event_ids: list[int] = []
    for name in group.keys():
        if prefix and not name.startswith(prefix):
            continue
        if suffix and not name.endswith(suffix):
            continue
        start = len(prefix)
        end = len(name) - len(suffix) if suffix else len(name)
        number = name[start:end]
        if number.isdigit():
            event_ids.append(int(number))

    if not event_ids:
        raise KeyError(f"Unable to infer event-id range from group: {container_path}")

    return min(event_ids), max(event_ids)


def _get_dataset_parent(handle: h5py.File, dataset_path: str) -> tuple[h5py.Group | h5py.File, str]:
    """Return the parent group and leaf dataset name for a concrete dataset path."""
    parts = _split_hdf5_path(dataset_path)
    if not parts:
        raise ValueError("Dataset path must not be root")

    group: h5py.Group | h5py.File = handle
    for part in parts[:-1]:
        group = group.require_group(part)
    return group, parts[-1]


def _update_event_range(handle: h5py.File, dataset_template: str, event_id: int) -> None:
    """Update ``min_event`` and ``max_event`` on the event container group."""
    group = _open_group(handle, _event_container_path(dataset_template))
    if group is None:
        return

    if "min_event" in group.attrs:
        group.attrs["min_event"] = min(int(group.attrs["min_event"]), event_id)
    else:
        group.attrs["min_event"] = event_id

    if "max_event" in group.attrs:
        group.attrs["max_event"] = max(int(group.attrs["max_event"]), event_id)
    else:
        group.attrs["max_event"] = event_id


class Hdf5Reader:
    """Read event matrices from one HDF5 file.

    The reader keeps one HDF5 file open, tracks the current iteration window,
    skips bad events declared in the file metadata, can read a specific event
    by event id, and returns the pair ``(meta, event)`` until the iteration is
    exhausted.
    """

    def __init__(
        self,
        *,
        workspace: str,
        run: int,
        path: str,
        dataset: str,
    ) -> None:
        """Open the input file and initialize iteration state."""
        self.workspace = workspace
        self.run = run
        self.path_template = path
        self.dataset_template = dataset
        self.path = _resolve_path(workspace=workspace, run=run, path=path)
        self._handle = h5py.File(self.path, "r")

        available_range = _read_range_from_attrs(self._handle, self.dataset_template)
        if available_range is None:
            available_range = _infer_range_from_children(self._handle, self.dataset_template)

        self._available_start, self._available_stop = available_range
        self._bad_events = _read_bad_events(self._handle, self.dataset_template)
        self._range_start, self._range_stop = available_range
        self._next_event_id = self._range_start

    def __del__(self) -> None:
        """Defensively close the file if the object is garbage-collected."""
        self.close()

    def event_id(self) -> int:
        """Return the current event id."""
        return self._next_event_id

    def reset(self) -> None:
        """Reset the next event id to the current range start."""
        self._next_event_id = self._range_start

    def get_range(self) -> tuple[int, int]:
        """Return the currently active inclusive event-id range."""
        return self._range_start, self._range_stop

    def set_range(self, start_event: int, stop_event: int) -> None:
        """Restrict iteration to an inclusive event-id subrange."""
        if start_event > stop_event:
            raise ValueError("start_event must be <= stop_event")
        if start_event < self._available_start or stop_event > self._available_stop:
            raise ValueError(
                f"Requested range [{start_event}, {stop_event}] is outside "
                f"available range [{self._available_start}, {self._available_stop}]"
            )
        self._range_start = start_event
        self._range_stop = stop_event
        self.reset_iteration()

    def read_event(self, event_id: int) -> tuple[MetaTuple, np.ndarray]:
        """Read one specific event by event id.

        This bypasses the reader's iteration cursor and does not modify the
        current iteration state. The method still rejects event ids outside the
        file's available range and event ids listed in ``bad_events``.
        """
        if self._handle is None:
            raise RuntimeError("HDF5 reader is closed")
        if event_id < self._available_start or event_id > self._available_stop:
            raise ValueError(
                f"Requested event_id {event_id} is outside available range "
                f"[{self._available_start}, {self._available_stop}]"
            )
        if event_id in self._bad_events:
            raise ValueError(f"Requested event_id {event_id} is marked as bad")

        dataset_path = _resolve_dataset(dataset=self.dataset_template, event_id=event_id)
        dataset = self._handle[dataset_path]
        event = np.asarray(dataset[()])

        orig_run = int(dataset.attrs.get("orig_run", self.run))
        orig_event = int(dataset.attrs.get("orig_event", event_id))
        meta = (event_id, orig_run, orig_event)
        return meta, event

    def read(self) -> tuple[MetaTuple, np.ndarray] | None:
        """Read the next good event or return ``None`` when iteration is over."""
        if self._handle is None:
            return None

        # The file range stays dense, but iteration should not return events that
        # the upstream merger already marked as bad.
        while self._next_event_id <= self._range_stop and self._next_event_id in self._bad_events:
            self._next_event_id += 1

        if self._next_event_id > self._range_stop:
            return None

        event_id = self._next_event_id
        self._next_event_id += 1

        return self.read_event(event_id)

    def close(self) -> None:
        """Close the underlying HDF5 file."""
        if getattr(self, "_handle", None) is not None:
            self._handle.close()
            self._handle = None


class Hdf5Writer:
    """Write event matrices to one HDF5 file.

    The writer keeps one HDF5 file open, resolves each event dataset path on
    demand, and records provenance attributes on every written dataset.
    """

    def __init__(
        self,
        *,
        workspace: str,
        run: int,
        path: str,
        dataset: str,
    ) -> None:
        """Open or create the output file and keep it ready for event writes."""
        self.workspace = workspace
        self.run = run
        self.path_template = path
        self.dataset_template = dataset
        self.path = _resolve_path(workspace=workspace, run=run, path=path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = h5py.File(self.path, "a")

    def __del__(self) -> None:
        """Defensively close the file if the object is garbage-collected."""
        self.close()

    def write(self, meta: MetaTuple, event: np.ndarray) -> None:
        """Write one event matrix and its provenance attributes."""
        if self._handle is None:
            raise RuntimeError("HDF5 writer is closed")

        event_id, orig_run, orig_event = meta
        dataset_path = _resolve_dataset(dataset=self.dataset_template, event_id=event_id)
        parent, name = _get_dataset_parent(self._handle, dataset_path)
        if name in parent:
            del parent[name]

        array = np.asarray(event)
        dataset = parent.create_dataset(name, data=array)
        dataset.attrs["orig_run"] = int(orig_run)
        dataset.attrs["orig_event"] = int(orig_event)
        _update_event_range(self._handle, self.dataset_template, int(event_id))
        self._handle.flush()

    def close(self) -> None:
        """Close the underlying HDF5 file."""
        if getattr(self, "_handle", None) is not None:
            self._handle.close()
            self._handle = None
