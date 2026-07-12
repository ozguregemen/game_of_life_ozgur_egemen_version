"""Two-species Immigration Game cellular automaton."""

from __future__ import annotations

import random
from typing import Sequence, TypeAlias

SPECIES_A = 1
SPECIES_B = -1
ImmigrationGrid: TypeAlias = list[list[int]]


def make_immigration_grid(rows: int, cols: int) -> ImmigrationGrid:
    """Create an empty two-species grid."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid dimensions must be positive.")
    return [[0 for _ in range(cols)] for _ in range(rows)]


def species_of(value: int) -> int:
    """Return the species sign of a live cell, or zero for a dead cell."""
    if value > 0:
        return SPECIES_A
    if value < 0:
        return SPECIES_B
    return 0


def cell_age(value: int) -> int:
    """Return the age encoded in a cell value."""
    return abs(value)


def randomize_immigration_grid(
    rows: int,
    cols: int,
    *,
    density: float = 0.20,
    rng: random.Random | None = None,
) -> ImmigrationGrid:
    """Create a random population split evenly between both species."""
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be between 0 and 1.")
    rng = rng or random.Random()
    grid = make_immigration_grid(rows, cols)
    for row in range(rows):
        for col in range(cols):
            if rng.random() < density:
                grid[row][col] = (
                    SPECIES_A if rng.random() < 0.5 else SPECIES_B
                )
    return grid


def apply_immigration_rules(
    grid: Sequence[Sequence[int]],
) -> ImmigrationGrid:
    """Advance the standard Immigration Game by one finite generation.

    Both species use Conway's B3/S23 rule. A surviving cell retains its
    species and increments its age. A newborn inherits the majority species
    among its exactly three live parents.
    """
    if not grid or not grid[0]:
        return []
    rows, cols = len(grid), len(grid[0])
    if any(len(row) != cols for row in grid):
        raise ValueError("Immigration grid must be rectangular.")

    next_grid = make_immigration_grid(rows, cols)
    for row in range(rows):
        for col in range(cols):
            live_neighbors = 0
            species_balance = 0
            for row_offset in (-1, 0, 1):
                for col_offset in (-1, 0, 1):
                    if row_offset == 0 and col_offset == 0:
                        continue
                    neighbor_row = row + row_offset
                    neighbor_col = col + col_offset
                    if not (
                        0 <= neighbor_row < rows
                        and 0 <= neighbor_col < cols
                    ):
                        continue
                    neighbor_species = species_of(
                        grid[neighbor_row][neighbor_col]
                    )
                    if neighbor_species:
                        live_neighbors += 1
                        species_balance += neighbor_species

            current = grid[row][col]
            if current and live_neighbors in (2, 3):
                next_grid[row][col] = species_of(current) * (cell_age(current) + 1)
            elif not current and live_neighbors == 3:
                next_grid[row][col] = (
                    SPECIES_A if species_balance > 0 else SPECIES_B
                )

    return next_grid


def immigration_stats(grid: Sequence[Sequence[int]]) -> dict[str, float | int]:
    """Return population, balance, age, and density statistics."""
    species_a = sum(cell > 0 for row in grid for cell in row)
    species_b = sum(cell < 0 for row in grid for cell in row)
    population = species_a + species_b
    total = sum(len(row) for row in grid)
    return {
        "population": population,
        "species_a": species_a,
        "species_b": species_b,
        "density": 100.0 * population / total if total else 0.0,
        "average_age": (
            sum(cell_age(cell) for row in grid for cell in row if cell)
            / population
            if population
            else 0.0
        ),
        "balance": (
            100.0 * species_a / population if population else 50.0
        ),
    }
