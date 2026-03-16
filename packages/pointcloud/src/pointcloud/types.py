"""Shared types for the pointcloud package."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol

import numpy as np


class TraceLength(IntEnum):
    """Allowed FFT/trace lengths for current detector data."""

    TB256 = 256
    TB512 = 512


@dataclass(frozen=True)
class PadMapEntry:
    """Resolved AT-TPC pad information."""

    pad_id: int
    x: float
    y: float
    scale: float
    time_offset: float
    is_beam_pad: bool


class PadMapProvider(Protocol):
    """Lookup interface for pad geometry/time/scale data."""

    def get_by_hardware(self, hardware_row: np.ndarray) -> PadMapEntry | None: ...

    def get_by_pad_id(self, pad_id: int) -> PadMapEntry | None: ...


@dataclass(frozen=True)
class SiliconMapEntry:
    """Resolved silicon channel information."""

    layer: int
    side: int
    strip: int


class SiliconMapProvider(Protocol):
    """Lookup interface for silicon channel mapping."""

    def get_by_hardware(self, hardware_row: np.ndarray) -> SiliconMapEntry | None: ...


class PointCorrection(Protocol):
    """Optional TPC point correction hook."""

    def correct_point(self, point_row: np.ndarray) -> np.ndarray: ...
