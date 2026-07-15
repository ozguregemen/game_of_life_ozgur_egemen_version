"""Life-like transition rules for the UI-independent 3D volume model."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray

from three_dimensional_ca import (
    MOORE_NEIGHBORHOOD,
    VON_NEUMANN_NEIGHBORHOOD,
    Neighborhood3D,
    Volume3D,
)


@dataclass(frozen=True)
class LifeLikeRule3D:
    """A binary birth/survival rule tied to a 3D neighborhood."""

    key: str
    name: str
    birth: tuple[int, ...]
    survival: tuple[int, ...]
    neighborhood: Neighborhood3D
    description: str

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.name.strip():
            raise ValueError("3D rule key and name cannot be empty.")
        maximum = self.neighborhood.size
        for label, values in (("birth", self.birth), ("survival", self.survival)):
            normalized = tuple(sorted(set(values)))
            if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
                raise TypeError(f"3D {label} counts must be integers.")
            if any(not 0 <= value <= maximum for value in normalized):
                raise ValueError(
                    f"3D {label} counts must be between 0 and {maximum}."
                )
            object.__setattr__(self, label, normalized)

    @property
    def notation(self) -> str:
        """Return conventional B/S notation."""
        births = "".join(str(value) for value in self.birth)
        survival = "".join(str(value) for value in self.survival)
        return f"B{births}/S{survival}"


BAYS_5766 = LifeLikeRule3D(
    key="bays_5766",
    name="Bays 5766",
    birth=(6,),
    survival=(5, 6, 7),
    neighborhood=MOORE_NEIGHBORHOOD,
    description="Carter Bays' bounded-growth 3D Life rule on 26 neighbors.",
)

BAYS_4555 = LifeLikeRule3D(
    key="bays_4555",
    name="Bays 4555",
    birth=(5,),
    survival=(4, 5),
    neighborhood=MOORE_NEIGHBORHOOD,
    description="An alternate Carter Bays 3D Life rule on 26 neighbors.",
)

FACE_LIFE = LifeLikeRule3D(
    key="face_life",
    name="Face Life",
    birth=(3,),
    survival=(2, 3),
    neighborhood=VON_NEUMANN_NEIGHBORHOOD,
    description="An exploratory B3/S23 rule using the six face neighbors.",
)

RULES_3D = MappingProxyType(
    {
        rule.key: rule
        for rule in (
            BAYS_5766,
            BAYS_4555,
            FACE_LIFE,
        )
    }
)
RULE_KEYS_3D = tuple(RULES_3D)
DEFAULT_RULE_3D = BAYS_5766


def step_life_like_3d(
    volume: Volume3D,
    rule: LifeLikeRule3D,
) -> NDArray[np.uint8]:
    """Return the next binary volume without mutating ``volume``."""
    if not isinstance(volume, Volume3D):
        raise TypeError("volume must be a Volume3D instance.")
    if not isinstance(rule, LifeLikeRule3D):
        raise TypeError("rule must be a LifeLikeRule3D instance.")
    if volume.state_count != 2:
        raise ValueError("Life-like 3D rules require a binary volume.")

    counts = volume.neighbor_counts(
        active_states=(1,),
        neighborhood=rule.neighborhood,
    )
    alive = volume.cells == 1
    born = np.isin(counts, rule.birth)
    survives = np.isin(counts, rule.survival)
    return np.where(alive, survives, born).astype(np.uint8, copy=False)
