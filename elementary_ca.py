"""Pure rule engine for one-dimensional elementary cellular automata."""

from __future__ import annotations

import random
from collections.abc import Iterable

ElementaryRow = tuple[int, ...]
Neighborhood = tuple[int, int, int]

MIN_RULE = 0
MAX_RULE = 255
DEFAULT_RULE = 30
DEFAULT_WIDTH = 121
BOUNDARY_FIXED = "fixed"
BOUNDARY_INFINITE = "infinite"
BOUNDARY_WRAP = "wrap"
BOUNDARY_MODES = (BOUNDARY_INFINITE, BOUNDARY_FIXED, BOUNDARY_WRAP)
RULE_PRESETS = (30, 54, 90, 110, 184)
NEIGHBORHOODS: tuple[Neighborhood, ...] = (
    (1, 1, 1),
    (1, 1, 0),
    (1, 0, 1),
    (1, 0, 0),
    (0, 1, 1),
    (0, 1, 0),
    (0, 0, 1),
    (0, 0, 0),
)


def validate_rule(rule: int) -> int:
    """Return a valid Wolfram rule number in the inclusive range 0–255."""
    if isinstance(rule, bool) or not isinstance(rule, int):
        raise TypeError("Rule number must be an integer.")
    if not MIN_RULE <= rule <= MAX_RULE:
        raise ValueError("Rule number must be between 0 and 255.")
    return rule


def normalize_row(values: Iterable[int]) -> ElementaryRow:
    """Validate and freeze a non-empty binary row."""
    row = tuple(values)
    if not row:
        raise ValueError("An elementary automaton row cannot be empty.")
    if any(isinstance(value, bool) or value not in (0, 1) for value in row):
        raise ValueError("Elementary automaton cells must be integers 0 or 1.")
    return row


def rule_bits(rule: int) -> tuple[int, ...]:
    """Return outputs ordered by neighborhoods 111, 110, ..., 000."""
    validate_rule(rule)
    return tuple((rule >> neighborhood_value) & 1 for neighborhood_value in range(7, -1, -1))


def neighborhood_output(rule: int, neighborhood: Neighborhood) -> int:
    """Return the next center value for one three-cell neighborhood."""
    validate_rule(rule)
    if len(neighborhood) != 3 or any(value not in (0, 1) for value in neighborhood):
        raise ValueError("A neighborhood must contain exactly three binary cells.")
    left, center, right = neighborhood
    bit_index = (left << 2) | (center << 1) | right
    return (rule >> bit_index) & 1


def next_background(rule: int, background: int) -> int:
    """Evolve a uniform infinite background by one generation."""
    if isinstance(background, bool) or background not in (0, 1):
        raise ValueError("Background state must be the integer 0 or 1.")
    return neighborhood_output(rule, (background, background, background))


def step_elementary(
    row: Iterable[int],
    rule: int,
    *,
    boundary: str = BOUNDARY_INFINITE,
    background: int = 0,
) -> ElementaryRow:
    """Advance one binary row using a radius-one Wolfram rule.

    ``infinite`` uses the supplied uniform background beyond both visible edges.
    The caller can evolve that value with :func:`next_background` between steps.
    ``fixed`` always uses zero and ``wrap`` joins the two visible edges.
    """
    current = normalize_row(row)
    validate_rule(rule)
    if boundary not in BOUNDARY_MODES:
        raise ValueError(f"Unknown boundary mode: {boundary}")
    if isinstance(background, bool) or background not in (0, 1):
        raise ValueError("Background state must be the integer 0 or 1.")

    width = len(current)
    next_row: list[int] = []
    for index, center in enumerate(current):
        if boundary == BOUNDARY_WRAP:
            left = current[(index - 1) % width]
            right = current[(index + 1) % width]
        else:
            outside = background if boundary == BOUNDARY_INFINITE else 0
            left = current[index - 1] if index > 0 else outside
            right = current[index + 1] if index + 1 < width else outside
        next_row.append(neighborhood_output(rule, (left, center, right)))
    return tuple(next_row)


def single_cell_seed(width: int = DEFAULT_WIDTH) -> ElementaryRow:
    """Create a centered single-cell seed for the classic space-time view."""
    if isinstance(width, bool) or not isinstance(width, int):
        raise TypeError("Seed width must be an integer.")
    if width < 1:
        raise ValueError("Seed width must be positive.")
    seed = [0] * width
    seed[width // 2] = 1
    return tuple(seed)


def random_seed(
    width: int = DEFAULT_WIDTH,
    *,
    density: float = 0.20,
    rng: random.Random | None = None,
) -> ElementaryRow:
    """Create a random binary seed using a caller-provided RNG when desired."""
    if isinstance(width, bool) or not isinstance(width, int):
        raise TypeError("Seed width must be an integer.")
    if width < 1:
        raise ValueError("Seed width must be positive.")
    if not 0.0 <= density <= 1.0:
        raise ValueError("Seed density must be between 0 and 1.")
    generator = rng if rng is not None else random
    return tuple(1 if generator.random() < density else 0 for _ in range(width))


def row_stats(row: Iterable[int]) -> dict[str, float | int]:
    """Return active-cell counts and density for a binary row."""
    current = normalize_row(row)
    active = sum(current)
    return {
        "active": active,
        "inactive": len(current) - active,
        "density": 100.0 * active / len(current),
    }
