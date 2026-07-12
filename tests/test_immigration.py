import random
import unittest

from immigration import (
    SPECIES_A,
    SPECIES_B,
    apply_immigration_rules,
    immigration_stats,
    randomize_immigration_grid,
)


class ImmigrationRuleTests(unittest.TestCase):
    def test_species_a_majority_controls_birth(self) -> None:
        grid = [
            [SPECIES_A, SPECIES_A, 0],
            [SPECIES_B, 0, 0],
            [0, 0, 0],
        ]
        self.assertEqual(apply_immigration_rules(grid)[1][1], SPECIES_A)

    def test_species_b_majority_controls_birth(self) -> None:
        grid = [
            [SPECIES_A, SPECIES_B, 0],
            [SPECIES_B, 0, 0],
            [0, 0, 0],
        ]
        self.assertEqual(apply_immigration_rules(grid)[1][1], SPECIES_B)

    def test_survivor_keeps_species_and_increments_age(self) -> None:
        grid = [
            [0, SPECIES_A, 0],
            [SPECIES_B, -4, 0],
            [0, 0, 0],
        ]
        self.assertEqual(apply_immigration_rules(grid)[1][1], -5)

    def test_lonely_cells_of_both_species_die(self) -> None:
        grid = [[SPECIES_A, 0, SPECIES_B]]
        self.assertEqual(apply_immigration_rules(grid), [[0, 0, 0]])

    def test_random_population_contains_both_species(self) -> None:
        grid = randomize_immigration_grid(
            20,
            20,
            density=0.5,
            rng=random.Random(12),
        )
        stats = immigration_stats(grid)
        self.assertGreater(stats["species_a"], 0)
        self.assertGreater(stats["species_b"], 0)

    def test_statistics_report_species_balance_and_age(self) -> None:
        grid = [[2, -4, 0], [1, -1, 0]]
        stats = immigration_stats(grid)
        self.assertEqual(stats["population"], 4)
        self.assertEqual(stats["species_a"], 2)
        self.assertEqual(stats["species_b"], 2)
        self.assertEqual(stats["balance"], 50.0)
        self.assertEqual(stats["average_age"], 2.0)


if __name__ == "__main__":
    unittest.main()
