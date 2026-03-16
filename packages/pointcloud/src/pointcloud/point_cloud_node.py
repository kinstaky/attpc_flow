"""Workflow node wrappers for pointcloud phase-1 algorithms."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from atflow.node import Node
from atflow.node_manager import auto_register_node

from .adapters import adapt_attpc, adapt_gagg, adapt_silicon
from .calibration import create_tpc_drift_calibration_config
from .filtering import fft_filter_traces
from .hits import build_gagg_hits, build_ion_chamber_hits, build_silicon_hits, build_tpc_hits
from .mapping import create_pad_map_provider, create_silicon_map_provider
from .peaks import find_trace_peaks
from .types import TraceLength

class AttpcAdapterParameters(BaseModel):
    pass


class SiliconAdapterParameters(BaseModel):
    pass


class GaggAdapterParameters(BaseModel):
    pass


class FftFilterParameters(BaseModel):
    trace_length: TraceLength = TraceLength.TB512
    baseline_window_scale: float = 20.0


class PeakFinderParameters(BaseModel):
    peak_separation: float = 50.0
    peak_prominence: float = 20.0
    peak_max_width: float = 50.0
    peak_threshold: float = 40.0
    rel_height: float = 0.95


class TpcHitsParameters(BaseModel):
    pad_geometry_path: str = "<default>"
    pad_time_path: str = "<default>"
    pad_scale_path: str = "<default>"
    micromegas_time_bucket: float = 10.0
    window_time_bucket: float = 560.0
    detector_length: float = 1000.0
    beam_region_radius: float = 25.0


class SiliconHitsParameters(BaseModel):
    silicon_map_path: str = "<default>"

class GaggHitsParameters(BaseModel):
    pass


class IonChamberHitsParameters(BaseModel):
    ic_delay_time_bucket: float = 1100.0
    ic_multiplicity: int = 1


@auto_register_node
class AttpcAdapterNode(Node):
    _name = "attpc_adapter"
    _version = "0.1.0"
    _description = "Split ATTPC raw event matrices into hardware and trace matrices"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"event": "matrix"}
    _outputs = {"hardware": "matrix", "traces": "matrix"}
    _properties = {}
    _parameters = AttpcAdapterParameters

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.validated_parameters = kwargs

    def execute(self, **kwargs: Any) -> list[Any]:
        params = {
            **self.validated_parameters,
            **kwargs,
        }
        hardware, traces = adapt_attpc(**params)
        return [hardware, traces]


@auto_register_node
class SiliconAdapterNode(Node):
    _name = "silicon_adapter"
    _version = "0.1.0"
    _description = "Merge the four silicon raw matrices into one hardware/trace pair"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"silicon_raw": "matrix[]"}
    _outputs = {"hardware": "matrix", "traces": "matrix"}
    _properties = {}
    _parameters = SiliconAdapterParameters

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.validated_parameters = kwargs

    def execute(self, **kwargs: Any) -> list[Any]:
        params = {
            **self.validated_parameters,
            **kwargs,
        }
        hardware, traces = adapt_silicon(**params)
        return [hardware, traces]


@auto_register_node
class GaggAdapterNode(Node):
    _name = "gagg_adapter"
    _version = "0.1.0"
    _description = "Prepare GAGG SIS330x and SIS3316 traces for filtering"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"sis330x_raw": "matrix[]", "sis3316_raw": "matrix"}
    _outputs = {"sis330x_traces": "matrix", "sis3316_traces": "matrix"}
    _properties = {}
    _parameters = GaggAdapterParameters

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.validated_parameters = kwargs

    def execute(self, **kwargs: Any) -> list[Any]:
        params = {
            **self.validated_parameters,
            **kwargs,
        }
        sis330x_traces, sis3316_traces = adapt_gagg(**params)
        return [sis330x_traces, sis3316_traces]


@auto_register_node
class FftFilterNode(Node):
    _name = "fft_filter"
    _version = "0.1.0"
    _description = "Apply FFT baseline removal to detector traces"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"traces": "matrix"}
    _outputs = {"traces": "matrix"}
    _properties = {"trace_length": "int", "baseline_window_scale": "float"}
    _parameters = FftFilterParameters

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.validated_parameters = kwargs

    def execute(self, **kwargs: Any) -> list[Any]:
        params = {
            **self.validated_parameters,
            **kwargs,
        }
        return [fft_filter_traces(**params)]


@auto_register_node
class PeakFinderNode(Node):
    _name = "peak_finder"
    _version = "0.1.0"
    _description = "Find peaks in filtered detector traces"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"traces": "matrix"}
    _outputs = {"peaks": "matrix"}
    _properties = {
        "peak_separation": "float",
        "peak_prominence": "float",
        "peak_max_width": "float",
        "peak_threshold": "float",
        "rel_height": "float",
    }
    _parameters = PeakFinderParameters

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.validated_parameters = kwargs

    def execute(self, **kwargs: Any) -> list[Any]:
        params = {
            **self.validated_parameters,
            **kwargs,
        }
        return [find_trace_peaks(**params)]


@auto_register_node
class TpcHitsNode(Node):
    _name = "tpc_hits"
    _version = "0.1.0"
    _description = "Build ATTPC hit matrices from hardware and peak data"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"hardware": "matrix", "peaks": "matrix"}
    _outputs = {"event": "matrix"}
    _properties = {
        "pad_geometry_path": "str",
        "pad_time_path": "str",
        "pad_scale_path": "str",
        "micromegas_time_bucket": "float",
        "window_time_bucket": "float",
        "detector_length": "float",
        "beam_region_radius": "float",
    }
    _parameters = TpcHitsParameters

    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.validated_parameters = kwargs

    def execute(self, **kwargs: Any) -> list[Any]:
        params = {
            **self.validated_parameters,
            **kwargs,
        }
        pad_map = create_pad_map_provider(
            geometry_path=params["pad_geometry_path"],
            time_path=params["pad_time_path"],
            scale_path=params["pad_scale_path"],
        )
        drift_calibration = create_tpc_drift_calibration_config(
            micromegas_time_bucket=params["micromegas_time_bucket"],
            window_time_bucket=params["window_time_bucket"],
            detector_length=params["detector_length"],
        )
        hits = build_tpc_hits(
            kwargs["hardware"],
            kwargs["peaks"],
            pad_map=pad_map,
            drift_calibration=drift_calibration,
            beam_region_radius=params["beam_region_radius"],
        )
        return [hits]


@auto_register_node
class SiliconHitsNode(Node):
    _name = "silicon_hits"
    _version = "0.1.0"
    _description = "Build silicon hit matrices from hardware and peak data"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"hardware": "matrix", "peaks": "matrix"}
    _outputs = {"event": "matrix"}
    _properties = {"silicon_map_path": "str"}
    _parameters = SiliconHitsParameters

    def execute(self, **kwargs: Any) -> list[Any]:
        properties = self._validated_properties(kwargs)
        silicon_map = create_silicon_map_provider(map_path=properties["silicon_map_path"])
        return [build_silicon_hits(kwargs["hardware"], kwargs["peaks"], silicon_map=silicon_map)]


@auto_register_node
class GaggHitsNode(Node):
    _name = "gagg_hits"
    _version = "0.1.0"
    _description = "Build GAGG hit matrices from peak data"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"sis330x_peaks": "matrix", "sis3316_peaks": "matrix"}
    _outputs = {"event": "matrix"}
    _properties = {}
    _parameters = BaseModel

    def execute(self, **kwargs: Any) -> list[Any]:
        over_range_mask = kwargs.get("over_range_mask")
        if over_range_mask is not None:
            over_range_mask = int(over_range_mask)
        return [
            build_gagg_hits(
                kwargs["sis330x_peaks"],
                kwargs["sis3316_peaks"],
                over_range_mask=over_range_mask,
            )
        ]


@auto_register_node
class IonChamberHitsNode(Node):
    _name = "ion_chamber_hits"
    _version = "0.1.0"
    _description = "Build ion-chamber hit matrices from peak data"
    _category = "pointcloud"
    _type = "event"
    _inputs = {"peaks": "matrix"}
    _outputs = {"event": "matrix"}
    _properties = {"ic_delay_time_bucket": "float", "ic_multiplicity": "int"}
    _parameters = IonChamberHitsParameters

    def execute(self, **kwargs: Any) -> list[Any]:
        properties = self._validated_properties(kwargs)
        return [build_ion_chamber_hits(kwargs["peaks"], **properties)]
