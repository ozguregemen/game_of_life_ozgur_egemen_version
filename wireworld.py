"""Wireworld four-state cellular automaton."""

from __future__ import annotations

import random
from typing import Sequence, TypeAlias

EMPTY = 0
ELECTRON_HEAD = 1
ELECTRON_TAIL = 2
CONDUCTOR = 3

STATE_NAMES = {
    EMPTY: "Empty",
    ELECTRON_HEAD: "Electron Head",
    ELECTRON_TAIL: "Electron Tail",
    CONDUCTOR: "Conductor",
}
VALID_STATES = frozenset(STATE_NAMES)

WireworldGrid: TypeAlias = list[list[int]]


def make_wireworld_grid(rows: int, cols: int) -> WireworldGrid:
    """Create an empty Wireworld grid."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid dimensions must be positive.")
    return [[EMPTY for _ in range(cols)] for _ in range(rows)]


def randomize_wireworld_grid(
    rows: int,
    cols: int,
    *,
    conductor_density: float = 0.20,
    signal_fraction: float = 0.08,
    rng: random.Random | None = None,
) -> WireworldGrid:
    """Create a random board with conductors and a few signal cells."""
    if not 0.0 <= conductor_density <= 1.0:
        raise ValueError("conductor_density must be between 0 and 1.")
    if not 0.0 <= signal_fraction <= 1.0:
        raise ValueError("signal_fraction must be between 0 and 1.")

    rng = rng or random.Random()
    grid = make_wireworld_grid(rows, cols)
    for row in range(rows):
        for col in range(cols):
            if rng.random() >= conductor_density:
                continue
            signal_roll = rng.random()
            if signal_roll < signal_fraction / 2:
                grid[row][col] = ELECTRON_HEAD
            elif signal_roll < signal_fraction:
                grid[row][col] = ELECTRON_TAIL
            else:
                grid[row][col] = CONDUCTOR
    return grid


def apply_wireworld_rules(grid: Sequence[Sequence[int]]) -> WireworldGrid:
    """Advance Wireworld by one finite, synchronous generation.

    Empty cells remain empty. Electron heads become tails, tails become
    conductors, and conductors become heads when exactly one or two of their
    eight neighbors are electron heads.
    """
    if not grid or not grid[0]:
        return []
    rows, cols = len(grid), len(grid[0])
    if any(len(row) != cols for row in grid):
        raise ValueError("Wireworld grid must be rectangular.")
    if any(cell not in VALID_STATES for row in grid for cell in row):
        raise ValueError("Wireworld grid contains an invalid cell state.")

    next_grid = make_wireworld_grid(rows, cols)
    for row in range(rows):
        for col in range(cols):
            current = grid[row][col]
            if current == EMPTY:
                continue
            if current == ELECTRON_HEAD:
                next_grid[row][col] = ELECTRON_TAIL
                continue
            if current == ELECTRON_TAIL:
                next_grid[row][col] = CONDUCTOR
                continue

            head_neighbors = 0
            for row_offset in (-1, 0, 1):
                for col_offset in (-1, 0, 1):
                    if row_offset == 0 and col_offset == 0:
                        continue
                    neighbor_row = row + row_offset
                    neighbor_col = col + col_offset
                    if (
                        0 <= neighbor_row < rows
                        and 0 <= neighbor_col < cols
                        and grid[neighbor_row][neighbor_col] == ELECTRON_HEAD
                    ):
                        head_neighbors += 1
            next_grid[row][col] = (
                ELECTRON_HEAD if head_neighbors in (1, 2) else CONDUCTOR
            )

    return next_grid


def wireworld_stats(grid: Sequence[Sequence[int]]) -> dict[str, float | int]:
    """Return state counts and occupied-cell density."""
    counts = {
        state: sum(cell == state for row in grid for cell in row)
        for state in VALID_STATES
    }
    total = sum(len(row) for row in grid)
    occupied = total - counts[EMPTY]
    return {
        "empty": counts[EMPTY],
        "heads": counts[ELECTRON_HEAD],
        "tails": counts[ELECTRON_TAIL],
        "conductors": counts[CONDUCTOR],
        "occupied": occupied,
        "density": 100.0 * occupied / total if total else 0.0,
    }
