"""Hit-building functions for phase-1 detector outputs."""

from __future__ import annotations

import numpy as np

from .calibration import TpcDriftCalibrationConfig
from .types import PadMapProvider, SiliconMapProvider, PointCorrection


TPC_HIT_WIDTH = 8
SILICON_HIT_WIDTH = 6
GAGG_HIT_WIDTH = 8
IC_HIT_WIDTH = 4



def _empty(width: int) -> np.ndarray:
    return np.empty((0, width), dtype=np.float64)



def _validate_matrix(name: str, value: np.ndarray, width: int) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a 2D matrix")
    if array.shape[1] != width:
        raise ValueError(f"{name} must have {width} columns, got {array.shape[1]}")
    return array



def _highest_peak_rows(peaks: np.ndarray) -> np.ndarray:
    if peaks.size == 0:
        return peaks
    order = np.argsort(peaks[:, 0], kind="stable")
    sorted_peaks = peaks[order]
    selected: list[np.ndarray] = []
    start = 0
    while start < len(sorted_peaks):
        trace_index = int(sorted_peaks[start, 0])
        end = start + 1
        while end < len(sorted_peaks) and int(sorted_peaks[end, 0]) == trace_index:
            end += 1
        group = sorted_peaks[start:end]
        selected.append(group[np.argmax(group[:, 1])])
        start = end
    return np.vstack(selected)



def build_tpc_hits(
    hardware: np.ndarray,
    peaks: np.ndarray,
    *,
    pad_map: PadMapProvider,
    drift_calibration: TpcDriftCalibrationConfig,
    correction: PointCorrection | None = None,
    beam_region_radius: float = 25.0,
) -> np.ndarray:
    """Join ATTPC hardware and peak data into TPC hits."""
    hardware_array = _validate_matrix("hardware", hardware, 5)
    peak_array = _validate_matrix("peaks", peaks, 4)
    if hardware_array.shape[0] == 0 or peak_array.shape[0] == 0:
        return _empty(TPC_HIT_WIDTH)

    hits: list[np.ndarray] = []
    denom = drift_calibration.window_time_bucket - drift_calibration.micromegas_time_bucket
    if denom == 0.0:
        raise ValueError("Invalid drift calibration: zero time-bucket span")

    for peak_row in peak_array:
        trace_index = int(peak_row[0])
        if trace_index < 0 or trace_index >= hardware_array.shape[0]:
            continue
        pad = pad_map.get_by_hardware(hardware_array[trace_index])
        if pad is None or pad.is_beam_pad:
            continue
        corrected_time_bucket = float(peak_row[3]) + pad.time_offset
        z = ((corrected_time_bucket - drift_calibration.micromegas_time_bucket) / denom) * drift_calibration.detector_length
        hit = np.array(
            [
                pad.x,
                pad.y,
                z,
                float(peak_row[1]),
                float(peak_row[2]),
                float(pad.pad_id),
                corrected_time_bucket,
                pad.scale,
            ],
            dtype=np.float64,
        )
        if np.hypot(hit[0], hit[1]) <= beam_region_radius:
            continue
        if correction is not None:
            hit = np.asarray(correction.correct_point(hit), dtype=np.float64)
        if np.any(np.isnan(hit)):
            continue
        hits.append(hit)

    if not hits:
        return _empty(TPC_HIT_WIDTH)
    result = np.vstack(hits)
    return result[np.argsort(result[:, 2], kind="stable")]



def build_silicon_hits(
    hardware: np.ndarray,
    peaks: np.ndarray,
    *,
    silicon_map: SiliconMapProvider,
) -> np.ndarray:
    """Convert silicon hardware and peaks into silicon hit rows."""
    hardware_array = _validate_matrix("hardware", hardware, 5)
    peak_array = _validate_matrix("peaks", peaks, 4)
    peak_array = _highest_peak_rows(peak_array)
    if hardware_array.shape[0] == 0 or peak_array.shape[0] == 0:
        return _empty(SILICON_HIT_WIDTH)

    hits: list[list[float]] = []
    for peak_row in peak_array:
        trace_index = int(peak_row[0])
        if trace_index < 0 or trace_index >= hardware_array.shape[0]:
            continue
        mapping = silicon_map.get_by_hardware(hardware_array[trace_index])
        if mapping is None:
            continue
        hits.append(
            [
                float(mapping.layer),
                float(mapping.side),
                float(mapping.strip),
                float(peak_row[1]),
                float(peak_row[2]),
                float(peak_row[3]),
            ]
        )
    if not hits:
        return _empty(SILICON_HIT_WIDTH)
    return np.asarray(hits, dtype=np.float64)



def _map_gagg(channel: int) -> tuple[int, int, int, float]:
    if channel < 2 or channel == 21 or channel >= 40:
        return (-1, -1, -1, -1.0)
    if channel < 8:
        return (1, channel + 6, 3300, 6.25)
    if channel < 15:
        return (1, channel - 8, 3301, 6.25)
    if channel == 15:
        return (0, 21, 3301, 6.25)
    if channel < 24:
        return (0, channel, 3301, 6.25)
    return (0, channel - 24, 3316, 7.8125)



def _build_gagg_rows(peaks: np.ndarray, channel_offset: int, over_range_mask: int | None) -> list[list[float]]:
    selected = _highest_peak_rows(peaks)
    rows: list[list[float]] = []
    for peak_row in selected:
        channel = channel_offset + int(peak_row[0])
        layer, index, series, sampling_rate = _map_gagg(channel)
        if layer < 0:
            continue
        over_range = 0
        if over_range_mask is not None and channel < 24:
            over_range = (int(over_range_mask) >> channel) & 0x1
        rows.append(
            [
                float(layer),
                float(index),
                float(peak_row[1]),
                float(peak_row[2]),
                float(peak_row[3]),
                float(series),
                float(sampling_rate),
                float(over_range),
            ]
        )
    return rows



def build_gagg_hits(
    sis330x_peaks: np.ndarray,
    sis3316_peaks: np.ndarray,
    *,
    over_range_mask: int | None = None,
) -> np.ndarray:
    """Convert GAGG peak matrices into hit rows."""
    sis330x_array = _validate_matrix("sis330x_peaks", sis330x_peaks, 4)
    sis3316_array = _validate_matrix("sis3316_peaks", sis3316_peaks, 4)
    rows = _build_gagg_rows(sis330x_array, 0, over_range_mask)
    rows.extend(_build_gagg_rows(sis3316_array, 24, None))
    if not rows:
        return _empty(GAGG_HIT_WIDTH)
    return np.asarray(rows, dtype=np.float64)



def build_ion_chamber_hits(
    peaks: np.ndarray,
    *,
    ic_delay_time_bucket: float = 1100.0,
    ic_multiplicity: int = 1,
) -> np.ndarray:
    """Convert ion-chamber peaks into a dedicated hit matrix."""
    peak_array = _validate_matrix("peaks", peaks, 4)
    if peak_array.shape[0] == 0:
        return _empty(IC_HIT_WIDTH)

    order = np.argsort(peak_array[:, 3], kind="stable")
    sorted_peaks = peak_array[order]
    multiplicity = int(np.sum(sorted_peaks[:, 3] > ic_delay_time_bucket))
    trigger_index = None
    if 0 < multiplicity <= ic_multiplicity:
        trigger_candidates = np.flatnonzero(sorted_peaks[:, 3] > ic_delay_time_bucket)
        if trigger_candidates.size > 0:
            trigger_index = int(trigger_candidates[0])

    if trigger_index is not None:
        rows = [sorted_peaks[trigger_index]]
        rows.extend(sorted_peaks[idx] for idx in range(len(sorted_peaks)) if idx != trigger_index)
    else:
        rows = list(sorted_peaks)

    result = np.zeros((len(rows), IC_HIT_WIDTH), dtype=np.float64)
    for idx, peak_row in enumerate(rows):
        result[idx, 0] = float(peak_row[1])
        result[idx, 1] = float(peak_row[2])
        result[idx, 2] = float(peak_row[3])
        result[idx, 3] = float(multiplicity)
    return result
