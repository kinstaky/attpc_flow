"""Public API for the pointcloud package."""

from .adapters import adapt_attpc, adapt_gagg, adapt_silicon
from .calibration import TpcDriftCalibrationConfig, create_tpc_drift_calibration_config
from .filtering import fft_filter_traces
from .hits import build_gagg_hits, build_ion_chamber_hits, build_silicon_hits, build_tpc_hits
from .mapping import create_pad_map_provider, create_silicon_map_provider
from .peaks import find_trace_peaks
from .types import PadMapEntry, PadMapProvider, PointCorrection, SiliconMapEntry, SiliconMapProvider, TraceLength

try:
    from .point_cloud_node import (
        AttpcAdapterNode,
        FftFilterNode,
        GaggAdapterNode,
        GaggHitsNode,
        IonChamberHitsNode,
        PeakFinderNode,
        SiliconAdapterNode,
        SiliconHitsNode,
        TpcHitsNode,
    )
except ModuleNotFoundError:  # pragma: no cover - function-level API can stand alone
    pass

__all__ = [
    "adapt_attpc",
    "adapt_silicon",
    "adapt_gagg",
    "fft_filter_traces",
    "find_trace_peaks",
    "build_tpc_hits",
    "build_silicon_hits",
    "build_gagg_hits",
    "build_ion_chamber_hits",
    "create_pad_map_provider",
    "create_silicon_map_provider",
    "TraceLength",
    "PadMapEntry",
    "PadMapProvider",
    "SiliconMapEntry",
    "SiliconMapProvider",
    "PointCorrection",
    "TpcDriftCalibrationConfig",
    "create_tpc_drift_calibration_config",
]

try:
    __all__.extend(
        [
            "AttpcAdapterNode",
            "SiliconAdapterNode",
            "GaggAdapterNode",
            "FftFilterNode",
            "PeakFinderNode",
            "TpcHitsNode",
            "SiliconHitsNode",
            "GaggHitsNode",
            "IonChamberHitsNode",
        ]
    )
except NameError:  # pragma: no cover - node imports unavailable
    pass
