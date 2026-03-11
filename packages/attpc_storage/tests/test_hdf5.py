from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _load_modules(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("python").resolve()))
    monkeypatch.syspath_prepend(str((Path(__file__).resolve().parents[1] / "src").resolve()))
    package = importlib.import_module("attpc_storage")
    hdf5 = importlib.import_module("attpc_storage.hdf5")
    nodes = importlib.import_module("attpc_storage.attpc_storage_node")
    return package, hdf5, nodes


@pytest.mark.skipif(
    importlib.util.find_spec("h5py") is None or importlib.util.find_spec("numpy") is None,
    reason="h5py and numpy are required for attpc_storage tests",
)
def test_writer_then_reader_round_trip(monkeypatch, tmp_path):
    _, hdf5, _ = _load_modules(monkeypatch)
    np = importlib.import_module("numpy")
    h5py = importlib.import_module("h5py")

    writer = hdf5.Hdf5Writer(
        workspace=str(tmp_path),
        run=12,
        path="<workspace>/phase1/output_<run>.h5",
        dataset="/events/event_<id>/pads",
    )
    writer.write((3, 12, 3), np.arange(6).reshape(2, 3))
    writer.write((4, 9, 40), np.arange(4).reshape(2, 2))
    writer.close()

    output_path = tmp_path / "phase1" / "output_12.h5"
    with h5py.File(output_path, "r") as handle:
        assert int(handle["/events"].attrs["min_event"]) == 3
        assert int(handle["/events"].attrs["max_event"]) == 4
        assert int(handle["/events/event_4/pads"].attrs["orig_run"]) == 9
        assert int(handle["/events/event_4/pads"].attrs["orig_event"]) == 40

    reader = hdf5.Hdf5Reader(
        workspace=str(tmp_path),
        run=12,
        path="<workspace>/phase1/output_<run>.h5",
        dataset="/events/event_<id>/pads",
    )
    assert reader.get_range() == (3, 4)
    meta_1, event_1 = reader.read()
    meta_2, event_2 = reader.read()
    assert reader.read() is None
    assert meta_1 == (3, 12, 3)
    assert meta_2 == (4, 9, 40)
    assert event_1.shape == (2, 3)
    assert event_2.shape == (2, 2)


@pytest.mark.skipif(
    importlib.util.find_spec("h5py") is None or importlib.util.find_spec("numpy") is None,
    reason="h5py and numpy are required for attpc_storage tests",
)
def test_reader_falls_back_to_current_run_and_event(monkeypatch, tmp_path):
    _, hdf5, _ = _load_modules(monkeypatch)
    np = importlib.import_module("numpy")
    h5py = importlib.import_module("h5py")

    path = tmp_path / "hdf5" / "run_8.h5"
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        events = handle.require_group("events")
        events.attrs["min_event"] = 5
        events.attrs["max_event"] = 5
        group = handle.require_group("/events/event_5/get")
        group.create_dataset("pads", data=np.arange(4).reshape(2, 2))

    reader = hdf5.Hdf5Reader(
        workspace=str(tmp_path),
        run=8,
        path="<workspace>/hdf5/run_<run>.h5",
        dataset="/events/event_<id>/get/pads",
    )
    meta, event = reader.read()
    assert meta == (5, 8, 5)
    assert event.shape == (2, 2)
    reader.reset_iteration()
    meta_again, event_again = reader.read_event(5)
    assert meta_again == (5, 8, 5)
    assert event_again.shape == (2, 2)


@pytest.mark.skipif(
    importlib.util.find_spec("h5py") is None or importlib.util.find_spec("numpy") is None,
    reason="h5py and numpy are required for attpc_storage tests",
)
def test_reader_skips_bad_events(monkeypatch, tmp_path):
    _, hdf5, _ = _load_modules(monkeypatch)
    np = importlib.import_module("numpy")
    h5py = importlib.import_module("h5py")

    path = tmp_path / "hdf5" / "run_15.h5"
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        events = handle.require_group("events")
        events.attrs["min_event"] = 5
        events.attrs["max_event"] = 7
        events.attrs["bad_events"] = np.array([6], dtype=np.int64)
        for event_id in (5, 6, 7):
            group = handle.require_group(f"/events/event_{event_id}/get")
            group.create_dataset("pads", data=np.array([[event_id]], dtype=np.int64))

    reader = hdf5.Hdf5Reader(
        workspace=str(tmp_path),
        run=15,
        path="<workspace>/hdf5/run_<run>.h5",
        dataset="/events/event_<id>/get/pads",
    )
    first_meta, first_event = reader.read()
    second_meta, second_event = reader.read()

    assert first_meta == (5, 15, 5)
    assert first_event.tolist() == [[5]]
    assert second_meta == (7, 15, 7)
    assert second_event.tolist() == [[7]]
    with pytest.raises(ValueError, match="marked as bad"):
        reader.read_event(6)
    direct_meta, direct_event = reader.read_event(7)
    assert direct_meta == (7, 15, 7)
    assert direct_event.tolist() == [[7]]
    assert reader.read() is None


@pytest.mark.skipif(
    importlib.util.find_spec("h5py") is None or importlib.util.find_spec("numpy") is None,
    reason="h5py and numpy are required for attpc_storage tests",
)
def test_checkpoint_node_returns_written_event(monkeypatch, tmp_path):
    _, _, nodes = _load_modules(monkeypatch)
    np = importlib.import_module("numpy")

    node = nodes.Hdf5CheckpointNode()
    event = np.arange(9).reshape(3, 3)
    result = node.execute(
        execution_id="exec",
        task_id=1,
        workspace=str(tmp_path),
        run=21,
        path="<workspace>/checkpoint/run_<run>.h5",
        dataset="/events/event_<id>/stage",
        event=event,
        meta=(7, 21, 7),
    )
    assert result[0].shape == (3, 3)
    assert node.last_meta == (7, 21, 7)
