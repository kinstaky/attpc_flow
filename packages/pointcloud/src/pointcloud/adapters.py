"""Raw-matrix adapter functions for phase-1 detector data."""

from __future__ import annotations

import numpy as np

AGET_WIDTH = 517
AGET_TRACE_OFFSET = 5
AGET_TRACE_WIDTH = 512
SIS330X_WIDTH = 256
SIS3316_WIDTH = 257


def _ensure_matrix(name: str, matrix: np.ndarray, width: int) -> np.ndarray:
    array = np.asarray(matrix)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a 2D matrix")
    if array.shape[1] != width:
        raise ValueError(f"{name} must have {width} columns, got {array.shape[1]}")
    return array


def adapt_attpc(event: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split an ATTPC raw event matrix into hardware and trace matrices."""
    array = _ensure_matrix("event", event, AGET_WIDTH)
    return array[:, :AGET_TRACE_OFFSET].copy(), array[:, AGET_TRACE_OFFSET:].copy()



def adapt_silicon(
    silicon_raw: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Merge the four silicon raw matrices into one hardware/trace pair."""
    if len(silicon_raw) != 4:
        raise ValueError("silicon_raw must contain four matrices")
    matrices = [_ensure_matrix(f"silicon_raw[{idx}]", matrix, AGET_WIDTH) for idx, matrix in enumerate(silicon_raw)]
    hardware_parts = [matrix[:, :AGET_TRACE_OFFSET] for matrix in matrices]
    trace_parts = [matrix[:, AGET_TRACE_OFFSET:].copy() for matrix in matrices]
    # Front sides are inverted to match the Spyral v2 treatment.
    trace_parts[0] *= -1
    trace_parts[2] *= -1
    hardware = np.vstack(hardware_parts) if hardware_parts else np.empty((0, AGET_TRACE_OFFSET), dtype=np.float64)
    traces = np.vstack(trace_parts) if trace_parts else np.empty((0, AGET_TRACE_WIDTH), dtype=np.float64)
    return hardware, traces



def adapt_gagg(
    sis330x_raw: tuple[np.ndarray, np.ndarray, np.ndarray],
    sis3316_raw: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Prepare SIS330x and SIS3316 GAGG traces for filtering."""
    if len(sis330x_raw) != 3:
        raise ValueError("sis330x_raw must contain three matrices")
    sis330x_parts = [
        _ensure_matrix(f"sis330x_raw[{idx}]", matrix, SIS330X_WIDTH) for idx, matrix in enumerate(sis330x_raw)
    ]
    sis3316_matrix = _ensure_matrix("sis3316_raw", sis3316_raw, SIS3316_WIDTH)
    sis330x_traces = np.vstack(sis330x_parts) if sis330x_parts else np.empty((0, SIS330X_WIDTH), dtype=np.float64)
    return sis330x_traces, sis3316_matrix[:, 1:].copy()
