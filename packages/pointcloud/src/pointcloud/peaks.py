"""Peak-finding utilities for filtered detector traces."""

from __future__ import annotations

import numpy as np

try:
    from scipy import signal
except ImportError:  # pragma: no cover - optional dependency
    signal = None


def _find_peaks_fallback(
    trace: np.ndarray,
    *,
    peak_separation: float,
    peak_prominence: float,
    peak_max_width: float,
    rel_height: float,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    peaks: list[int] = []
    left_ips: list[float] = []
    right_ips: list[float] = []
    min_distance = max(1, int(np.ceil(peak_separation)))
    max_width = max(1, int(np.ceil(peak_max_width)))
    threshold_factor = max(0.0, min(1.0, 1.0 - float(rel_height)))

    last_peak = -min_distance
    for idx in range(1, trace.shape[0] - 1):
        center = float(trace[idx])
        if center <= float(trace[idx - 1]) or center < float(trace[idx + 1]):
            continue
        local_base = max(float(trace[idx - 1]), float(trace[idx + 1]))
        if center - local_base < peak_prominence:
            continue
        if idx - last_peak < min_distance:
            if peaks and center > float(trace[peaks[-1]]):
                peaks.pop()
                left_ips.pop()
                right_ips.pop()
            else:
                continue

        half_height = local_base + (center - local_base) * threshold_factor
        left = idx
        while left > 0 and trace[left] > half_height and idx - left <= max_width:
            left -= 1
        right = idx
        while right < trace.shape[0] - 1 and trace[right] > half_height and right - idx <= max_width:
            right += 1
        if right - left > max_width:
            continue

        peaks.append(idx)
        left_ips.append(float(left))
        right_ips.append(float(right))
        last_peak = idx

    return np.asarray(peaks, dtype=np.int64), {
        "left_ips": np.asarray(left_ips, dtype=np.float64),
        "right_ips": np.asarray(right_ips, dtype=np.float64),
    }



def find_trace_peaks(
    traces: np.ndarray,
    *,
    peak_separation: float = 50.0,
    peak_prominence: float = 20.0,
    peak_max_width: float = 50.0,
    peak_threshold: float = 40.0,
    rel_height: float = 0.95,
) -> np.ndarray:
    """Find all significant peaks in a trace matrix.

    Returns one row per peak: [trace_index, amplitude, integral, time_bucket].
    """
    array = np.asarray(traces, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("traces must be a 2D matrix")

    rows: list[list[float]] = []
    for trace_index, trace in enumerate(array):
        if signal is None:
            peaks, props = _find_peaks_fallback(
                trace,
                peak_separation=peak_separation,
                peak_prominence=peak_prominence,
                peak_max_width=peak_max_width,
                rel_height=rel_height,
            )
        else:
            peaks, props = signal.find_peaks(
                trace,
                distance=peak_separation,
                prominence=peak_prominence,
                width=(1.0, peak_max_width),
                rel_height=rel_height,
            )
        for idx, peak_index in enumerate(peaks):
            amplitude = float(trace[peak_index])
            if amplitude <= peak_threshold:
                continue
            left = int(np.floor(props["left_ips"][idx]))
            right = int(np.ceil(props["right_ips"][idx]))
            integral = float(np.sum(np.abs(trace[left:right])))
            rows.append([float(trace_index), amplitude, integral, float(peak_index)])

    if not rows:
        return np.empty((0, 4), dtype=np.float64)
    return np.asarray(rows, dtype=np.float64)
