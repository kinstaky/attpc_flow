"""FFT-based baseline filtering for trace matrices."""

from __future__ import annotations

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover - optional acceleration
    def njit(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

from .types import TraceLength


@njit(cache=True)
def _replace_baseline_outliers(bases: np.ndarray) -> np.ndarray:
    result = bases.copy()
    rows, cols = result.shape
    for row_idx in range(rows):
        row = result[row_idx]
        mean = 0.0
        for value in row:
            mean += value
        mean /= cols
        variance = 0.0
        for value in row:
            diff = value - mean
            variance += diff * diff
        sigma = np.sqrt(variance / cols)
        # First pass: compute replacement average from non-outlier buckets.
        keep_sum = 0.0
        keep_count = 0
        for value in row:
            if abs(value - mean) <= sigma * 1.5:
                keep_sum += value
                keep_count += 1
        replacement = mean if keep_count == 0 else keep_sum / keep_count
        for col_idx in range(cols):
            if abs(row[col_idx] - mean) > sigma * 1.5:
                row[col_idx] = replacement
    return result



def _coerce_trace_length(trace_length: TraceLength | int) -> TraceLength:
    if isinstance(trace_length, TraceLength):
        return trace_length
    return TraceLength(int(trace_length))



def fft_filter_traces(
    traces: np.ndarray,
    *,
    trace_length: TraceLength = TraceLength.TB512,
    baseline_window_scale: float = 20.0,
) -> np.ndarray:
    """Smooth trace edges and subtract FFT-estimated baseline."""
    length = _coerce_trace_length(trace_length)
    array = np.asarray(traces, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("traces must be a 2D matrix")
    if array.shape[1] != int(length):
        raise ValueError(f"traces must have width {int(length)}, got {array.shape[1]}")
    if array.shape[0] == 0:
        return array.copy()

    filtered = array.copy()
    filtered[:, 0] = filtered[:, 1]
    filtered[:, -1] = filtered[:, -2]
    bases = _replace_baseline_outliers(filtered)

    half_width = int(length) // 2
    window = np.arange(-float(half_width), float(half_width), 1.0)
    filt = np.fft.ifftshift(np.sinc(window / float(baseline_window_scale)))
    transformed = np.fft.fft2(bases, axes=(1,))
    baseline = np.real(np.fft.ifft2(transformed * filt, axes=(1,)))
    return filtered - baseline
