"""TPC drift calibration helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TpcDriftCalibrationConfig:
    """Parameters for direct time-bucket-to-z conversion."""

    micromegas_time_bucket: float
    window_time_bucket: float
    detector_length: float


def create_tpc_drift_calibration_config(
    *,
    micromegas_time_bucket: float,
    window_time_bucket: float,
    detector_length: float,
) -> TpcDriftCalibrationConfig:
    """Construct and validate the TPC drift calibration config."""
    if window_time_bucket == micromegas_time_bucket:
        raise ValueError("window_time_bucket must differ from micromegas_time_bucket")
    return TpcDriftCalibrationConfig(
        micromegas_time_bucket=float(micromegas_time_bucket),
        window_time_bucket=float(window_time_bucket),
        detector_length=float(detector_length),
    )
