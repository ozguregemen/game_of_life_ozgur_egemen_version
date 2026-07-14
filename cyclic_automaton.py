"""Cyclic cellular automaton with threshold-based color succession."""

from __future__ import annotations

import math
import random
from typing import Sequence, TypeAlias

DEFAULT_STATE_COUNT = 8
DEFAULT_THRESHOLD = 1
MIN_STATE_COUNT = 3
MOORE_NEIGHBOR_COUNT = 8

CyclicGrid: TypeAlias = list[list[int]]


def _validate_state_count(state_count: int) -> None:
    if not isinstance(state_count, int) or state_count < MIN_STATE_COUNT:
        raise ValueError(f"state_count must be at least {MIN_STATE_COUNT}.")


def _validate_threshold(threshold: int) -> None:
    if not isinstance(threshold, int) or not 1 <= threshold <= MOORE_NEIGHBOR_COUNT:
        raise ValueError(
            f"threshold must be between 1 and {MOORE_NEIGHBOR_COUNT}."
        )


def _grid_dimensions(grid: Sequence[Sequence[int]]) -> tuple[int, int]:
    if not grid or not grid[0]:
        return 0, 0
    rows, cols = len(grid), len(grid[0])
    if any(len(row) != cols for row in grid):
        raise ValueError("Cyclic automaton grid must be rectangular.")
    return rows, cols


def _validate_grid_states(
    grid: Sequence[Sequence[int]],
    state_count: int,
) -> None:
    if any(
        not isinstance(cell, int) or not 0 <= cell < state_count
        for row in grid
        for cell in row
    ):
        raise ValueError(
            f"Cyclic automaton cells must be integers from 0 to {state_count - 1}."
        )


def make_cyclic_grid(
    rows: int,
    cols: int,
    *,
    fill_state: int = 0,
    state_count: int = DEFAULT_STATE_COUNT,
) -> CyclicGrid:
    """Create a uniformly colored cyclic automaton grid."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid dimensions must be positive.")
    _validate_state_count(state_count)
    if not isinstance(fill_state, int) or not 0 <= fill_state < state_count:
        raise ValueError(f"fill_state must be between 0 and {state_count - 1}.")
    return [[fill_state for _ in range(cols)] for _ in range(rows)]


def randomize_cyclic_grid(
    rows: int,
    cols: int,
    *,
    state_count: int = DEFAULT_STATE_COUNT,
    rng: random.Random | None = None,
) -> CyclicGrid:
    """Create a grid whose colors are independently and uniformly random."""
    _validate_state_count(state_count)
    rng = rng or random.Random()
    grid = make_cyclic_grid(rows, cols, state_count=state_count)
    for row in range(rows):
        for col in range(cols):
            grid[row][col] = rng.randrange(state_count)
    return grid


def apply_cyclic_rules(
    grid: Sequence[Sequence[int]],
    *,
    state_count: int = DEFAULT_STATE_COUNT,
    threshold: int = DEFAULT_THRESHOLD,
) -> CyclicGrid:
    """Advance one finite, synchronous Moore-neighborhood generation.

    A cell in state ``s`` advances to ``(s + 1) % state_count`` when at
    least ``threshold`` of its eight surrounding neighbors already have that
    successor state. Otherwise it keeps its current state.
    """
    _validate_state_count(state_count)
    _validate_threshold(threshold)
    rows, cols = _grid_dimensions(grid)
    if not rows:
        return []
    _validate_grid_states(grid, state_count)

    next_grid = [list(row) for row in grid]
    for row in range(rows):
        for col in range(cols):
            successor = (grid[row][col] + 1) % state_count
            successor_neighbors = 0
            for row_offset in (-1, 0, 1):
                for col_offset in (-1, 0, 1):
                    if row_offset == 0 and col_offset == 0:
                        continue
                    neighbor_row = row + row_offset
                    neighbor_col = col + col_offset
                    if (
                        0 <= neighbor_row < rows
                        and 0 <= neighbor_col < cols
                        and grid[neighbor_row][neighbor_col] == successor
                    ):
                        successor_neighbors += 1
                        if successor_neighbors >= threshold:
                            next_grid[row][col] = successor
                            break
                if successor_neighbors >= threshold:
                    break
    return next_grid


def cyclic_stats(
    grid: Sequence[Sequence[int]],
    *,
    state_count: int = DEFAULT_STATE_COUNT,
) -> dict[str, float | int | list[int]]:
    """Return state counts, diversity, dominance, and normalized entropy."""
    _validate_state_count(state_count)
    rows, cols = _grid_dimensions(grid)
    if not rows:
        return {
            "counts": [0] * state_count,
            "diversity": 0,
            "dominant_state": 0,
            "dominant_share": 0.0,
            "entropy": 0.0,
        }
    _validate_grid_states(grid, state_count)

    counts = [0] * state_count
    for row in grid:
        for cell in row:
            counts[cell] += 1

    total = rows * cols
    dominant_state = max(range(state_count), key=counts.__getitem__)
    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in counts
        if count
    )
    normalized_entropy = entropy / math.log2(state_count) if entropy else 0.0
    return {
        "counts": counts,
        "diversity": sum(count > 0 for count in counts),
        "dominant_state": dominant_state,
        "dominant_share": 100.0 * counts[dominant_state] / total,
        "entropy": normalized_entropy,
    }
