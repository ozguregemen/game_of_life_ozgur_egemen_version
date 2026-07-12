"""Brian's Brain three-state cellular automaton."""

from __future__ import annotations

import random
from typing import Sequence, TypeAlias

OFF = 0
FIRING = 1
DYING = 2
BrainGrid: TypeAlias = list[list[int]]


def make_brain_grid(rows: int, cols: int) -> BrainGrid:
    """Create an empty Brian's Brain grid."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid dimensions must be positive.")
    return [[OFF for _ in range(cols)] for _ in range(rows)]


def randomize_brain_grid(
    rows: int,
    cols: int,
    *,
    density: float = 0.18,
    rng: random.Random | None = None,
) -> BrainGrid:
    """Create a random mix of firing and dying cells."""
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be between 0 and 1.")
    rng = rng or random.Random()
    grid = make_brain_grid(rows, cols)
    for row in range(rows):
        for col in range(cols):
            if rng.random() < density:
                grid[row][col] = FIRING if rng.random() < 0.65 else DYING
    return grid


def apply_brain_rules(grid: Sequence[Sequence[int]]) -> BrainGrid:
    """Advance Brian's Brain by one finite, synchronous generation.

    An off cell fires when exactly two neighbors are firing. Firing cells
    become dying, and dying cells become off. Dying neighbors do not count.
    """
    if not grid or not grid[0]:
        return []
    rows, cols = len(grid), len(grid[0])
    if any(len(row) != cols for row in grid):
        raise ValueError("Brian's Brain grid must be rectangular.")

    next_grid = make_brain_grid(rows, cols)
    for row in range(rows):
        for col in range(cols):
            current = grid[row][col]
            if current == FIRING:
                next_grid[row][col] = DYING
                continue
            if current == DYING:
                next_grid[row][col] = OFF
                continue

            firing_neighbors = 0
            for row_offset in (-1, 0, 1):
                for col_offset in (-1, 0, 1):
                    if row_offset == 0 and col_offset == 0:
                        continue
                    neighbor_row = row + row_offset
                    neighbor_col = col + col_offset
                    if (
                        0 <= neighbor_row < rows
                        and 0 <= neighbor_col < cols
                        and grid[neighbor_row][neighbor_col] == FIRING
                    ):
                        firing_neighbors += 1
            if firing_neighbors == 2:
                next_grid[row][col] = FIRING

    return next_grid


def brain_stats(grid: Sequence[Sequence[int]]) -> dict[str, float | int]:
    """Return firing, dying, active, and density statistics."""
    firing = sum(cell == FIRING for row in grid for cell in row)
    dying = sum(cell == DYING for row in grid for cell in row)
    active = firing + dying
    total = sum(len(row) for row in grid)
    return {
        "firing": firing,
        "dying": dying,
        "active": active,
        "off": total - active,
        "density": 100.0 * active / total if total else 0.0,
    }
