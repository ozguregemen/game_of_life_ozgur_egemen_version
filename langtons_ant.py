"""Langton's Ant two-color turmite simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Sequence, TypeAlias

WHITE = 0
BLACK = 1
NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3
DIRECTION_NAMES = ("North", "East", "South", "West")
_DIRECTION_OFFSETS = ((-1, 0), (0, 1), (1, 0), (0, -1))

AntGrid: TypeAlias = list[list[int]]


@dataclass(frozen=True)
class AntState:
    """Position, heading, and activity state of the ant."""

    row: int
    col: int
    direction: int = NORTH
    active: bool = True


@dataclass(frozen=True)
class AntStepReport:
    """Changes produced by one Langton step."""

    turned: str = ""
    painted_black: bool = False
    exited: bool = False


def make_ant_grid(rows: int, cols: int) -> AntGrid:
    """Create an all-white ant grid."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid dimensions must be positive.")
    return [[WHITE for _ in range(cols)] for _ in range(rows)]


def centered_ant(rows: int, cols: int, direction: int = NORTH) -> AntState:
    """Create an active ant in the center of a grid."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid dimensions must be positive.")
    if direction not in (NORTH, EAST, SOUTH, WEST):
        raise ValueError("Invalid ant direction.")
    return AntState(rows // 2, cols // 2, direction)


def randomize_ant_grid(
    rows: int,
    cols: int,
    *,
    density: float = 0.15,
    rng: random.Random | None = None,
) -> AntGrid:
    """Create a random black-and-white board."""
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be between 0 and 1.")
    rng = rng or random.Random()
    return [
        [BLACK if rng.random() < density else WHITE for _ in range(cols)]
        for _ in range(rows)
    ]


def rotate_ant_clockwise(ant: AntState) -> AntState:
    """Rotate an ant in place for interactive setup."""
    return replace(ant, direction=(ant.direction + 1) % 4, active=True)


def step_ant(
    grid: Sequence[Sequence[int]],
    ant: AntState,
) -> tuple[AntGrid, AntState, AntStepReport]:
    """Apply one standard Langton's Ant step on a finite board.

    White turns the ant right and becomes black. Black turns the ant left and
    becomes white. The ant then moves forward. Crossing the board boundary
    marks it inactive instead of wrapping.
    """
    if not grid or not grid[0]:
        return [], replace(ant, active=False), AntStepReport(exited=True)
    rows, cols = len(grid), len(grid[0])
    if any(len(row) != cols for row in grid):
        raise ValueError("Langton grid must be rectangular.")
    if not (0 <= ant.row < rows and 0 <= ant.col < cols):
        raise ValueError("Ant position must be inside the grid.")
    if ant.direction not in (NORTH, EAST, SOUTH, WEST):
        raise ValueError("Invalid ant direction.")
    if not ant.active:
        return [list(row) for row in grid], ant, AntStepReport()

    next_grid = [list(row) for row in grid]
    current_color = grid[ant.row][ant.col]
    if current_color == WHITE:
        direction = (ant.direction + 1) % 4
        next_grid[ant.row][ant.col] = BLACK
        turned = "right"
        painted_black = True
    elif current_color == BLACK:
        direction = (ant.direction - 1) % 4
        next_grid[ant.row][ant.col] = WHITE
        turned = "left"
        painted_black = False
    else:
        raise ValueError("Langton grid cells must be WHITE or BLACK.")

    row_offset, col_offset = _DIRECTION_OFFSETS[direction]
    target_row = ant.row + row_offset
    target_col = ant.col + col_offset
    if not (0 <= target_row < rows and 0 <= target_col < cols):
        return (
            next_grid,
            AntState(ant.row, ant.col, direction, active=False),
            AntStepReport(turned, painted_black, exited=True),
        )

    return (
        next_grid,
        AntState(target_row, target_col, direction),
        AntStepReport(turned, painted_black),
    )


def ant_stats(grid: Sequence[Sequence[int]]) -> dict[str, float | int]:
    """Return black/white cell counts and black density."""
    black = sum(cell == BLACK for row in grid for cell in row)
    total = sum(len(row) for row in grid)
    return {
        "black": black,
        "white": total - black,
        "black_density": 100.0 * black / total if total else 0.0,
    }
