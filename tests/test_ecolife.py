import random
import unittest

from ecolife import (
    EcoConfig,
    ecosystem_stats,
    make_eco_grid,
    make_food_grid,
    seed_cell,
    step_ecosystem,
)


class EcoLifeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = EcoConfig()

    def test_food_regenerates_without_exceeding_capacity(self) -> None:
        grid = make_eco_grid(2, 2)
        food = make_food_grid(2, 2, self.config, fill_ratio=1.0)
        _, next_food, _ = step_ecosystem(grid, food, self.config)
        self.assertTrue(
            all(value == self.config.food_capacity for row in next_food for value in row)
        )

    def test_cell_consumes_food_and_pays_metabolism(self) -> None:
        grid = make_eco_grid(1, 1)
        food = make_food_grid(1, 1, self.config, fill_ratio=1.0)
        seed_cell(grid, 0, 0, self.config, energy=3.0)

        next_grid, next_food, report = step_ecosystem(grid, food, self.config)

        expected_energy = 3.0 + self.config.food_consumption - self.config.metabolism_cost
        self.assertAlmostEqual(next_grid[0][0].energy, expected_energy)
        self.assertAlmostEqual(report.consumed_food, self.config.food_consumption)
        self.assertLess(next_food[0][0], self.config.food_capacity)

    def test_cell_dies_when_energy_is_exhausted(self) -> None:
        config = EcoConfig(food_consumption=0.1, metabolism_cost=1.0)
        grid = make_eco_grid(1, 1)
        food = make_food_grid(1, 1, config, fill_ratio=0.0)
        seed_cell(grid, 0, 0, config, energy=0.2)

        next_grid, _, report = step_ecosystem(grid, food, config)

        self.assertIsNone(next_grid[0][0])
        self.assertEqual(report.deaths, 1)

    def test_eligible_parent_reproduces_into_empty_neighbor(self) -> None:
        grid = make_eco_grid(3, 3)
        food = make_food_grid(3, 3, self.config, fill_ratio=1.0)
        seed_cell(
            grid,
            1,
            1,
            self.config,
            energy=self.config.maximum_energy,
        )

        next_grid, _, report = step_ecosystem(
            grid,
            food,
            self.config,
            rng=random.Random(7),
        )

        cells = [cell for row in next_grid for cell in row if cell is not None]
        self.assertEqual(report.births, 1)
        self.assertEqual(len(cells), 2)
        child = next(cell for cell in cells if cell.age == 0)
        self.assertEqual(child.generation, 1)
        self.assertGreaterEqual(
            child.reproduction_threshold,
            self.config.minimum_reproduction_threshold,
        )
        self.assertLessEqual(
            child.reproduction_threshold,
            self.config.maximum_reproduction_threshold,
        )

    def test_statistics_describe_population_and_environment(self) -> None:
        grid = make_eco_grid(2, 2)
        food = make_food_grid(2, 2, self.config, fill_ratio=0.5)
        seed_cell(grid, 0, 0, self.config, energy=8.0)
        seed_cell(grid, 1, 1, self.config, energy=4.0)

        stats = ecosystem_stats(grid, food)

        self.assertEqual(stats["population"], 2)
        self.assertEqual(stats["average_energy"], 6.0)
        self.assertEqual(stats["average_food"], self.config.food_capacity * 0.5)


if __name__ == "__main__":
    unittest.main()
