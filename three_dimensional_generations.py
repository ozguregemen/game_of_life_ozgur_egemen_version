"""Multi-state Generations rules for three-dimensional cellular automata."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray

from three_dimensional_ca import (
    MOORE_NEIGHBORHOOD,
    Neighborhood3D,
    Volume3D,
)


@dataclass(frozen=True)
class GenerationsRule3D:
    """A 3D Generations rule using state 1 as its only active state.

    State 0 is empty, state 1 is alive, and states 2 through ``state_count - 1``
    are refractory states. The notation follows Softology's
    ``survival/birth/states/neighborhood`` convention.
    """

    key: str
    name: str
    survival: tuple[int, ...]
    birth: tuple[int, ...]
    state_count: int
    neighborhood: Neighborhood3D
    description: str
    seed_density: float = 0.20

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.name.strip():
            raise ValueError("3D Generations rule key and name cannot be empty.")
        if not 2 <= self.state_count <= 256:
            raise ValueError("3D Generations state_count must be between 2 and 256.")
        maximum = self.neighborhood.size
        for label, values in (("survival", self.survival), ("birth", self.birth)):
            if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
                raise TypeError(f"3D Generations {label} counts must be integers.")
            normalized = tuple(sorted(set(values)))
            if any(not 0 <= value <= maximum for value in normalized):
                raise ValueError(
                    f"3D Generations {label} counts must be between 0 and {maximum}."
                )
            object.__setattr__(self, label, normalized)
        if not 0.01 <= float(self.seed_density) <= 0.99:
            raise ValueError("3D Generations seed_density must be between 0.01 and 0.99.")
        object.__setattr__(self, "seed_density", float(self.seed_density))

    @staticmethod
    def _counts(values: tuple[int, ...]) -> str:
        if not values:
            return ""
        groups: list[str] = []
        start = previous = values[0]
        for value in values[1:]:
            if value == previous + 1:
                previous = value
                continue
            groups.append(str(start) if start == previous else f"{start}-{previous}")
            start = previous = value
        groups.append(str(start) if start == previous else f"{start}-{previous}")
        return ",".join(groups)

    @property
    def notation(self) -> str:
        neighborhood = "M" if self.neighborhood.size == 26 else "N"
        return (
            f"{self._counts(self.survival)}/{self._counts(self.birth)}/"
            f"{self.state_count}/{neighborhood}"
        )


GENERATIONS_445 = GenerationsRule3D(
    key="generations_445",
    name="445",
    survival=(4,),
    birth=(4,),
    state_count=5,
    neighborhood=MOORE_NEIGHBORHOOD,
    description=(
        "Softology's featured 3D Generations rule: active voxels survive with "
        "four active neighbors; empty voxels are born with four, then deaths "
        "cool through three refractory states."
    ),
    seed_density=0.18,
)

GENERATIONS_3D_BRAIN = GenerationsRule3D(
    key="generations_3d_brain",
    name="3D Brain",
    survival=(),
    birth=(4,),
    state_count=2,
    neighborhood=MOORE_NEIGHBORHOOD,
    description="A birth-only 3D rule documented as /4/2/M.",
    seed_density=0.18,
)

GENERATIONS_CLOUDS_1 = GenerationsRule3D(
    key="generations_clouds_1",
    name="Clouds 1",
    survival=tuple(range(13, 27)),
    birth=(13, 14, 17, 18, 19),
    state_count=2,
    neighborhood=MOORE_NEIGHBORHOOD,
    description="A dense, cloud-forming 3D rule documented by Softology.",
    seed_density=0.52,
)

GENERATIONS_PYROCLASTIC = GenerationsRule3D(
    key="generations_pyroclastic",
    name="Pyroclastic",
    survival=(4, 5, 6, 7),
    birth=(6, 7, 8),
    state_count=10,
    neighborhood=MOORE_NEIGHBORHOOD,
    description="A ten-state rule with long refractory trails and turbulent growth.",
    seed_density=0.28,
)

GENERATIONS_RULES_3D = MappingProxyType(
    {
        rule.key: rule
        for rule in (
            GENERATIONS_445,
            GENERATIONS_3D_BRAIN,
            GENERATIONS_CLOUDS_1,
            GENERATIONS_PYROCLASTIC,
        )
    }
)
GENERATIONS_RULE_KEYS_3D = tuple(GENERATIONS_RULES_3D)
DEFAULT_GENERATIONS_RULE_3D = GENERATIONS_445


def step_generations_3d(
    volume: Volume3D,
    rule: GenerationsRule3D,
) -> NDArray[np.uint8]:
    """Return one corrected Generations step without mutating ``volume``.

    Only state 1 participates in survival and neighbor counts. Refractory
    states never survive or give birth; they advance deterministically toward
    state 0.
    """
    if not isinstance(volume, Volume3D):
        raise TypeError("volume must be a Volume3D instance.")
    if not isinstance(rule, GenerationsRule3D):
        raise TypeError("rule must be a GenerationsRule3D instance.")
    if volume.state_count != rule.state_count:
        raise ValueError(
            "3D Generations volume state_count must match the selected rule."
        )

    cells = volume.cells
    counts = volume.neighbor_counts(
        active_states=(1,),
        neighborhood=rule.neighborhood,
    )
    active = cells == 1
    empty = cells == 0
    survives = active & np.isin(counts, rule.survival)
    born = empty & np.isin(counts, rule.birth)
    following = np.zeros(volume.shape, dtype=np.uint8)

    if rule.state_count > 2:
        dying = active & ~survives
        following[dying] = 2
        refractory = cells >= 2
        cooling = refractory & (cells < rule.state_count - 1)
        following[cooling] = cells[cooling] + 1

    following[survives | born] = 1
    return following
