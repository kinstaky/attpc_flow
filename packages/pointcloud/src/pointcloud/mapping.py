"""Map-provider implementations for pointcloud hit builders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

import numpy as np

from .types import PadMapEntry, PadMapProvider, SiliconMapEntry, SiliconMapProvider

DEFAULT_TOKEN = "<default>"


@dataclass
class _CsvPadData:
    x: float = 0.0
    y: float = 0.0
    time_offset: float = 0.0
    scale: float = 1.0
    is_beam_pad: bool = False


class _IdentityPadMapProvider(PadMapProvider):
    """Fallback provider when no real pad map resource is available.

    The default mapping uses hardware columns to generate stable placeholders so
    point building can still run before experiment-specific maps are wired in.
    """

    def get_by_hardware(self, hardware_row: np.ndarray) -> PadMapEntry | None:
        if hardware_row.shape[0] < 5:
            return None
        cobo, asad, aget, channel, pad_id = (int(value) for value in hardware_row[:5])
        x = float(channel + aget * 100)
        y = float(asad + cobo * 10)
        return PadMapEntry(
            pad_id=pad_id,
            x=x,
            y=y,
            scale=1.0,
            time_offset=0.0,
            is_beam_pad=False,
        )

    def get_by_pad_id(self, pad_id: int) -> PadMapEntry | None:
        return PadMapEntry(
            pad_id=int(pad_id),
            x=float(pad_id),
            y=0.0,
            scale=1.0,
            time_offset=0.0,
            is_beam_pad=False,
        )


class _CsvPadMapProvider(PadMapProvider):
    def __init__(self, geometry_path: Path, time_path: Path, scale_path: Path) -> None:
        self._map: dict[int, _CsvPadData] = {}
        self._load_geometry(geometry_path)
        self._load_time(time_path)
        self._load_scale(scale_path)

    def _load_geometry(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for pad_id, row in enumerate(reader):
                if len(row) < 2:
                    continue
                self._map.setdefault(pad_id, _CsvPadData())
                self._map[pad_id].x = float(row[0])
                self._map[pad_id].y = float(row[1])

    def _load_time(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for pad_id, row in enumerate(reader):
                if not row:
                    continue
                self._map.setdefault(pad_id, _CsvPadData())
                self._map[pad_id].time_offset = float(row[0])

    def _load_scale(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for pad_id, row in enumerate(reader):
                if not row:
                    continue
                self._map.setdefault(pad_id, _CsvPadData())
                self._map[pad_id].scale = float(row[0])

    def get_by_hardware(self, hardware_row: np.ndarray) -> PadMapEntry | None:
        if hardware_row.shape[0] < 5:
            return None
        return self.get_by_pad_id(int(hardware_row[4]))

    def get_by_pad_id(self, pad_id: int) -> PadMapEntry | None:
        data = self._map.get(int(pad_id))
        if data is None:
            return None
        return PadMapEntry(
            pad_id=int(pad_id),
            x=data.x,
            y=data.y,
            scale=data.scale,
            time_offset=data.time_offset,
            is_beam_pad=data.is_beam_pad,
        )


class _IdentitySiliconMapProvider(SiliconMapProvider):
    """Fallback silicon mapping before a detector-specific map is provided."""

    def get_by_hardware(self, hardware_row: np.ndarray) -> SiliconMapEntry | None:
        if hardware_row.shape[0] < 5:
            return None
        _, asad, _, channel, _ = (int(value) for value in hardware_row[:5])
        side = max(0, min(asad, 3))
        layer = 0 if side < 2 else 1
        return SiliconMapEntry(layer=layer, side=side, strip=channel)


class _CsvSiliconMapProvider(SiliconMapProvider):
    def __init__(self, map_path: Path) -> None:
        self._map: dict[tuple[int, int, int], SiliconMapEntry] = {}
        with map_path.open("r", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                if len(row) < 6:
                    continue
                asad = int(row[1])
                aget = int(row[2])
                channel = int(row[3])
                detector_name = row[4].strip()
                side = 0
                if detector_name == "si_upstream_back":
                    side = 1
                elif detector_name == "si_downstream_front":
                    side = 2
                elif detector_name == "si_downstream_back":
                    side = 3
                layer = 0 if side < 2 else 1
                strip = int(row[5])
                self._map[(asad, aget, channel)] = SiliconMapEntry(layer=layer, side=side, strip=strip)

    def get_by_hardware(self, hardware_row: np.ndarray) -> SiliconMapEntry | None:
        if hardware_row.shape[0] < 5:
            return None
        _, asad, aget, channel, _ = (int(value) for value in hardware_row[:5])
        return self._map.get((asad, aget, channel))


def _resolve_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def create_pad_map_provider(
    *,
    geometry_path: str | Path = DEFAULT_TOKEN,
    time_path: str | Path = DEFAULT_TOKEN,
    scale_path: str | Path = DEFAULT_TOKEN,
) -> PadMapProvider:
    """Create a pad-map provider.

    When any path is `"<default>"`, a lightweight identity provider is used.
    This keeps the package usable even when experiment map resources are not
    bundled in the repo yet.
    """
    if geometry_path == DEFAULT_TOKEN or time_path == DEFAULT_TOKEN or scale_path == DEFAULT_TOKEN:
        return _IdentityPadMapProvider()
    return _CsvPadMapProvider(_resolve_path(geometry_path), _resolve_path(time_path), _resolve_path(scale_path))



def create_silicon_map_provider(
    *,
    map_path: str | Path = DEFAULT_TOKEN,
) -> SiliconMapProvider:
    """Create a silicon-map provider."""
    if map_path == DEFAULT_TOKEN:
        return _IdentitySiliconMapProvider()
    return _CsvSiliconMapProvider(_resolve_path(map_path))
