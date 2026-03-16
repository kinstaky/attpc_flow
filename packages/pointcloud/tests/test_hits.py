from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "packages" / "pointcloud" / "src"))

from pointcloud import (  # noqa: E402
    PadMapEntry,
    SiliconMapEntry,
    build_gagg_hits,
    build_ion_chamber_hits,
    build_silicon_hits,
    build_tpc_hits,
    create_tpc_drift_calibration_config,
)


class DummyPadMap:
    def get_by_hardware(self, hardware_row: np.ndarray) -> PadMapEntry | None:
        return PadMapEntry(pad_id=int(hardware_row[4]), x=100.0, y=0.0, scale=1.5, time_offset=2.0, is_beam_pad=False)

    def get_by_pad_id(self, pad_id: int) -> PadMapEntry | None:
        return PadMapEntry(pad_id=pad_id, x=100.0, y=0.0, scale=1.5, time_offset=2.0, is_beam_pad=False)


class DummySiliconMap:
    def get_by_hardware(self, hardware_row: np.ndarray) -> SiliconMapEntry | None:
        return SiliconMapEntry(layer=1, side=2, strip=int(hardware_row[3]))



def test_build_tpc_hits_joins_and_sorts() -> None:
    hardware = np.array([[0, 0, 0, 10, 99], [0, 0, 0, 20, 100]], dtype=np.float64)
    peaks = np.array([[1, 50, 80, 20], [0, 60, 90, 10]], dtype=np.float64)
    calibration = create_tpc_drift_calibration_config(
        micromegas_time_bucket=10.0,
        window_time_bucket=110.0,
        detector_length=1000.0,
    )
    hits = build_tpc_hits(hardware, peaks, pad_map=DummyPadMap(), drift_calibration=calibration, beam_region_radius=25.0)
    assert hits.shape == (2, 8)
    assert list(hits[:, 5].astype(int)) == [99, 100]
    assert np.all(np.diff(hits[:, 2]) >= 0)



def test_build_silicon_hits_keeps_max_peak_per_trace() -> None:
    hardware = np.array([[0, 0, 0, 11, 0]], dtype=np.float64)
    peaks = np.array([[0, 10, 20, 30], [0, 50, 60, 70]], dtype=np.float64)
    hits = build_silicon_hits(hardware, peaks, silicon_map=DummySiliconMap())
    assert hits.shape == (1, 6)
    assert hits[0, 3] == 50
    assert hits[0, 5] == 70



def test_build_gagg_hits_maps_channels_and_over_range() -> None:
    sis330x_peaks = np.array([[2, 10, 20, 30]], dtype=np.float64)
    sis3316_peaks = np.array([[0, 40, 50, 60]], dtype=np.float64)
    hits = build_gagg_hits(sis330x_peaks, sis3316_peaks, over_range_mask=1 << 2)
    assert hits.shape == (2, 8)
    assert hits[0, 7] == 1
    assert hits[1, 7] == 0



def test_build_ion_chamber_hits_promotes_first_trigger_peak() -> None:
    peaks = np.array([[0, 5, 10, 1000], [0, 6, 11, 1200], [0, 7, 12, 1300]], dtype=np.float64)
    hits = build_ion_chamber_hits(peaks, ic_delay_time_bucket=1100.0, ic_multiplicity=2)
    assert hits.shape == (3, 4)
    assert hits[0, 2] == 1200
    assert np.all(hits[:, 3] == 2)
