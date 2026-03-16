from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "packages" / "pointcloud" / "src"))

from pointcloud import adapt_attpc, adapt_gagg, adapt_silicon  # noqa: E402


def test_adapt_attpc_splits_hardware_and_traces() -> None:
    event = np.arange(2 * 517, dtype=np.int16).reshape(2, 517)
    hardware, traces = adapt_attpc(event)
    assert hardware.shape == (2, 5)
    assert traces.shape == (2, 512)
    np.testing.assert_array_equal(hardware, event[:, :5])
    np.testing.assert_array_equal(traces, event[:, 5:])


def test_adapt_silicon_flips_front_sides() -> None:
    base = np.ones((1, 517), dtype=np.int16)
    matrices = (base.copy(), base.copy() * 2, base.copy() * 3, base.copy() * 4)
    hardware, traces = adapt_silicon(matrices)
    assert hardware.shape == (4, 5)
    assert traces.shape == (4, 512)
    assert np.all(traces[0] == -1)
    assert np.all(traces[1] == 2)
    assert np.all(traces[2] == -3)
    assert np.all(traces[3] == 4)


def test_adapt_gagg_drops_sis3316_index_column() -> None:
    sis330x = tuple(np.full((1, 256), idx, dtype=np.int16) for idx in range(1, 4))
    sis3316 = np.arange(257, dtype=np.int16).reshape(1, 257)
    sis330x_traces, sis3316_traces = adapt_gagg(sis330x, sis3316)
    assert sis330x_traces.shape == (3, 256)
    assert sis3316_traces.shape == (1, 256)
    np.testing.assert_array_equal(sis3316_traces[0], sis3316[0, 1:])
