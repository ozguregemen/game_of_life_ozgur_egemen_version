"""Metadata for the application's top-level simulation dimensions."""

from __future__ import annotations

from dataclasses import dataclass

Color = tuple[int, int, int]


@dataclass(frozen=True)
class DimensionDefinition:
    """User-facing metadata for one workspace dimension."""

    key: str
    name: str
    summary: str
    accent: Color
    available: bool
    status_hint: str


DIMENSION_DEFINITIONS = (
    DimensionDefinition(
        key="1d",
        name="1D · General CA Lab",
        summary=(
            "Explore Elementary, totalistic, multi-state, extended-radius, "
            "higher-order, and reversible rules."
        ),
        accent=(70, 205, 255),
        available=True,
        status_hint="Choose a rule family, seed it, or compare two rules side by side.",
    ),
    DimensionDefinition(
        key="2d",
        name="2D · Cellular Automata",
        summary=(
            "Use the existing Life-like, Immigration, Brain, Ant, Wireworld, "
            "and Cyclic modes."
        ),
        accent=(90, 225, 115),
        available=True,
        status_hint="Choose among the established two-dimensional simulations.",
    ),
    DimensionDefinition(
        key="3d",
        name="3D · Spatial Automata",
        summary=(
            "A future volume workspace for three-dimensional neighborhoods, "
            "slices, and camera controls."
        ),
        accent=(190, 120, 255),
        available=False,
        status_hint="The 3D workspace is planned but not implemented yet.",
    ),
)

DIMENSION_BY_KEY = {
    definition.key: definition for definition in DIMENSION_DEFINITIONS
}
DIMENSION_KEYS = tuple(DIMENSION_BY_KEY)


def get_dimension_definition(key: str) -> DimensionDefinition:
    """Return one registered dimension or raise for an unknown key."""
    try:
        return DIMENSION_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f"Unknown simulation dimension: {key}") from exc
