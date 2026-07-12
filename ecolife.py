"""Energy-and-resource based artificial-life simulation core."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class EcoConfig:
    """Tunable environmental and organism parameters for EcoLife."""

    food_capacity: float = 10.0
    food_regeneration: float = 0.18
    food_consumption: float = 2.0
    initial_energy: float = 6.0
    maximum_energy: float = 20.0
    metabolism_cost: float = 0.55
    reproduction_cost: float = 4.0
    default_reproduction_threshold: float = 11.0
    minimum_reproduction_threshold: float = 7.0
    maximum_reproduction_threshold: float = 16.0
    mutation_amount: float = 0.45
    maximum_age: int = 120

    def __post_init__(self) -> None:
        positive_values = (
            self.food_capacity,
            self.food_consumption,
            self.initial_energy,
            self.maximum_energy,
            self.metabolism_cost,
            self.reproduction_cost,
            self.default_reproduction_threshold,
            self.maximum_age,
        )
        if any(value <= 0 for value in positive_values):
            raise ValueError("EcoLife capacities and costs must be positive.")
        if self.food_regeneration < 0 or self.mutation_amount < 0:
            raise ValueError("Regeneration and mutation cannot be negative.")
        if self.minimum_reproduction_threshold > self.maximum_reproduction_threshold:
            raise ValueError("Reproduction threshold bounds are invalid.")
        if not (
            self.minimum_reproduction_threshold
            <= self.default_reproduction_threshold
            <= self.maximum_reproduction_threshold
        ):
            raise ValueError("Default reproduction threshold is outside its bounds.")
        if self.initial_energy > self.maximum_energy:
            raise ValueError("Initial energy cannot exceed maximum energy.")
        if self.reproduction_cost > self.maximum_energy:
            raise ValueError("Reproduction cost cannot exceed maximum energy.")


@dataclass
class EcoCell:
    """One organism with an energy budget and a heritable trait."""

    energy: float
    reproduction_threshold: float
    age: int = 0
    generation: int = 0


@dataclass(frozen=True)
class EcoStepReport:
    """Population changes produced by one simulation step."""

    births: int = 0
    deaths: int = 0
    consumed_food: float = 0.0


EcoGrid: TypeAlias = list[list[EcoCell | None]]
FoodGrid: TypeAlias = list[list[float]]


def make_eco_grid(rows: int, cols: int) -> EcoGrid:
    """Create an empty organism grid."""
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid dimensions must be positive.")
    return [[None for _ in range(cols)] for _ in range(rows)]


def make_food_grid(
    rows: int,
    cols: int,
    config: EcoConfig,
    fill_ratio: float = 0.65,
) -> FoodGrid:
    """Create a uniformly filled food field."""
    if not 0.0 <= fill_ratio <= 1.0:
        raise ValueError("fill_ratio must be between 0 and 1.")
    value = config.food_capacity * fill_ratio
    return [[value for _ in range(cols)] for _ in range(rows)]


def seed_cell(
    grid: EcoGrid,
    row: int,
    col: int,
    config: EcoConfig,
    *,
    energy: float | None = None,
    reproduction_threshold: float | None = None,
) -> EcoCell:
    """Place a new organism and return it."""
    cell = EcoCell(
        energy=config.initial_energy if energy is None else energy,
        reproduction_threshold=(
            config.default_reproduction_threshold
            if reproduction_threshold is None
            else reproduction_threshold
        ),
    )
    grid[row][col] = cell
    return cell


def randomize_ecosystem(
    rows: int,
    cols: int,
    config: EcoConfig,
    *,
    density: float = 0.12,
    rng: random.Random | None = None,
) -> tuple[EcoGrid, FoodGrid]:
    """Create a randomized population and heterogeneous food field."""
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be between 0 and 1.")
    rng = rng or random.Random()
    grid = make_eco_grid(rows, cols)
    food = make_food_grid(rows, cols, config)
    for row in range(rows):
        for col in range(cols):
            food[row][col] = rng.uniform(
                config.food_capacity * 0.35,
                config.food_capacity,
            )
            if rng.random() < density:
                seed_cell(
                    grid,
                    row,
                    col,
                    config,
                    reproduction_threshold=rng.uniform(
                        config.default_reproduction_threshold - 1.0,
                        config.default_reproduction_threshold + 1.0,
                    ),
                )
    return grid, food


def _empty_neighbors(grid: EcoGrid, row: int, col: int) -> list[tuple[int, int]]:
    rows, cols = len(grid), len(grid[0])
    neighbors: list[tuple[int, int]] = []
    for row_offset in (-1, 0, 1):
        for col_offset in (-1, 0, 1):
            if row_offset == 0 and col_offset == 0:
                continue
            target_row = row + row_offset
            target_col = col + col_offset
            if (
                0 <= target_row < rows
                and 0 <= target_col < cols
                and grid[target_row][target_col] is None
            ):
                neighbors.append((target_row, target_col))
    return neighbors


def _mutated_threshold(
    parent_threshold: float,
    config: EcoConfig,
    rng: random.Random,
) -> float:
    mutation = rng.uniform(-config.mutation_amount, config.mutation_amount)
    return max(
        config.minimum_reproduction_threshold,
        min(config.maximum_reproduction_threshold, parent_threshold + mutation),
    )


def step_ecosystem(
    grid: EcoGrid,
    food: FoodGrid,
    config: EcoConfig,
    *,
    rng: random.Random | None = None,
) -> tuple[EcoGrid, FoodGrid, EcoStepReport]:
    """Advance EcoLife by one synchronous generation.

    Food regenerates first. Existing organisms then feed, pay metabolism,
    age, die, and finally reproduce into empty Moore-neighborhood cells.
    Newborns do not act until the following generation.
    """
    if not grid or not grid[0]:
        return [], [], EcoStepReport()
    rows, cols = len(grid), len(grid[0])
    if len(food) != rows or any(len(row) != cols for row in food):
        raise ValueError("Food and organism grids must have matching dimensions.")

    rng = rng or random.Random()
    next_food = [row[:] for row in food]
    survivors = make_eco_grid(rows, cols)
    deaths = 0
    consumed_food = 0.0

    for row in range(rows):
        for col in range(cols):
            next_food[row][col] = min(
                config.food_capacity,
                next_food[row][col] + config.food_regeneration,
            )
            current = grid[row][col]
            if current is None:
                continue

            consumed = min(config.food_consumption, next_food[row][col])
            next_food[row][col] -= consumed
            consumed_food += consumed
            energy = min(
                config.maximum_energy,
                current.energy + consumed - config.metabolism_cost,
            )
            age = current.age + 1
            if energy <= 0 or age > config.maximum_age:
                deaths += 1
                continue

            survivors[row][col] = EcoCell(
                energy=energy,
                reproduction_threshold=current.reproduction_threshold,
                age=age,
                generation=current.generation,
            )

    births = 0
    parent_positions = [
        (row, col)
        for row in range(rows)
        for col in range(cols)
        if survivors[row][col] is not None
    ]
    rng.shuffle(parent_positions)

    for row, col in parent_positions:
        parent = survivors[row][col]
        if parent is None or parent.energy < parent.reproduction_threshold:
            continue
        empty_neighbors = _empty_neighbors(survivors, row, col)
        if not empty_neighbors:
            continue

        child_row, child_col = rng.choice(empty_neighbors)
        parent.energy -= config.reproduction_cost
        survivors[child_row][child_col] = EcoCell(
            energy=config.reproduction_cost,
            reproduction_threshold=_mutated_threshold(
                parent.reproduction_threshold,
                config,
                rng,
            ),
            age=0,
            generation=parent.generation + 1,
        )
        births += 1

    return survivors, next_food, EcoStepReport(
        births=births,
        deaths=deaths,
        consumed_food=consumed_food,
    )


def ecosystem_stats(grid: EcoGrid, food: FoodGrid) -> dict[str, float | int]:
    """Calculate population, energy, food, age, and trait statistics."""
    cells = [cell for row in grid for cell in row if cell is not None]
    food_values = [value for row in food for value in row]
    population = len(cells)
    return {
        "population": population,
        "average_energy": (
            sum(cell.energy for cell in cells) / population if population else 0.0
        ),
        "average_age": (
            sum(cell.age for cell in cells) / population if population else 0.0
        ),
        "average_threshold": (
            sum(cell.reproduction_threshold for cell in cells) / population
            if population
            else 0.0
        ),
        "average_food": (
            sum(food_values) / len(food_values) if food_values else 0.0
        ),
        "max_lineage": max((cell.generation for cell in cells), default=0),
    }
