"""Documented seed patterns for three-dimensional cellular automata."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray

from three_dimensional_ca import BOUNDARY_MODES, BOUNDARY_WRAP, VolumeShape


@dataclass(frozen=True)
class Pattern3D:
    """A finite set of live offsets tied to a compatible 3D rule."""

    key: str
    name: str
    rule_key: str
    offsets: tuple[tuple[int, int, int], ...]
    description: str
    source_url: str
    boundary: str = "fixed"

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.name.strip() or not self.rule_key.strip():
            raise ValueError("3D pattern identity fields cannot be empty.")
        if not self.offsets or len(set(self.offsets)) != len(self.offsets):
            raise ValueError("3D pattern offsets must be non-empty and unique.")
        if any(len(offset) != 3 for offset in self.offsets):
            raise ValueError("Every 3D pattern offset must contain z, y, and x.")
        if self.boundary not in BOUNDARY_MODES:
            raise ValueError(f"Unknown 3D pattern boundary: {self.boundary!r}.")

    def centered_cells(self, shape: VolumeShape) -> NDArray[np.uint8]:
        """Return this pattern centered inside a binary volume."""
        cells = np.zeros(shape, dtype=np.uint8)
        center = np.asarray(tuple(length // 2 for length in shape), dtype=np.int64)
        for offset in self.offsets:
            position = center + np.asarray(offset, dtype=np.int64)
            if np.any(position < 0) or np.any(position >= np.asarray(shape)):
                raise ValueError(f"Pattern '{self.name}' does not fit in volume {shape}.")
            cells[tuple(int(value) for value in position)] = 1
        return cells


# Published as the common/evident 3D glider for Life 5766. The source lists
# coordinates as (i, j, k); the isotropic Moore neighborhood permits mapping
# them directly to the engine's canonical (z, y, x) axes.
BAYS_5766_GLIDER = Pattern3D(
    key="bays_5766_glider",
    name="Bays 5766 Glider",
    rule_key="bays_5766",
    offsets=(
        (0, 0, 0),
        (0, 0, 1),
        (0, 0, -1),
        (0, -1, 1),
        (0, -2, 0),
        (1, 0, 0),
        (1, 0, 1),
        (1, 0, -1),
        (1, -1, 1),
        (1, -2, 0),
    ),
    description=(
        "Carter Bays' common Life 5766 glider: ten voxels, period four, "
        "translating diagonally by one cell per period."
    ),
    source_url="https://www.ibiblio.org/e-notes/Life/Gliders.htm",
    boundary=BOUNDARY_WRAP,
)


PATTERNS_3D = MappingProxyType({BAYS_5766_GLIDER.key: BAYS_5766_GLIDER})
