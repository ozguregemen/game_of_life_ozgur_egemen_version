import random
import unittest

from cyclic_automaton import (
    DEFAULT_STATE_COUNT,
    apply_cyclic_rules,
    cyclic_stats,
    make_cyclic_grid,
    randomize_cyclic_grid,
)


class CyclicAutomatonTests(unittest.TestCase):
    def test_cell_advances_when_successor_reaches_threshold(self) -> None:
        grid = make_cyclic_grid(3, 3)
        grid[0][0] = 1
        grid[0][1] = 1

        next_grid = apply_cyclic_rules(grid, threshold=2)

        self.assertEqual(next_grid[1][1], 1)

    def test_cell_stays_when_successor_is_below_threshold(self) -> None:
        grid = make_cyclic_grid(3, 3)
        grid[0][0] = 1

        next_grid = apply_cyclic_rules(grid, threshold=2)

        self.assertEqual(next_grid[1][1], 0)

    def test_last_state_wraps_to_zero(self) -> None:
        grid = [[DEFAULT_STATE_COUNT - 1, 0]]

        self.assertEqual(apply_cyclic_rules(grid), [[0, 0]])

    def test_updates_are_synchronous(self) -> None:
        grid = [[0, 1, 2]]

        self.assertEqual(apply_cyclic_rules(grid), [[1, 2, 2]])

    def test_grid_edges_do_not_wrap(self) -> None:
        grid = make_cyclic_grid(3, 3)
        grid[2][2] = 1

        self.assertEqual(apply_cyclic_rules(grid)[0][0], 0)

    def test_invalid_parameters_and_cells_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_cyclic_grid(0, 2)
        with self.assertRaises(ValueError):
            make_cyclic_grid(2, 2, state_count=2)
        with self.assertRaises(ValueError):
            apply_cyclic_rules([[0]], threshold=0)
        with self.assertRaises(ValueError):
            apply_cyclic_rules([[DEFAULT_STATE_COUNT]])
        with self.assertRaises(ValueError):
            apply_cyclic_rules([[0], [0, 1]])

    def test_random_board_is_reproducible_and_uses_valid_states(self) -> None:
        first = randomize_cyclic_grid(12, 12, rng=random.Random(4))
        second = randomize_cyclic_grid(12, 12, rng=random.Random(4))

        self.assertEqual(first, second)
        self.assertTrue(
            all(0 <= cell < DEFAULT_STATE_COUNT for row in first for cell in row)
        )
        self.assertGreater(len({cell for row in first for cell in row}), 1)

    def test_statistics_report_diversity_dominance_and_entropy(self) -> None:
        stats = cyclic_stats([[0, 0], [1, 2]], state_count=3)

        self.assertEqual(stats["counts"], [2, 1, 1])
        self.assertEqual(stats["diversity"], 3)
        self.assertEqual(stats["dominant_state"], 0)
        self.assertEqual(stats["dominant_share"], 50.0)
        self.assertGreater(stats["entropy"], 0.9)
        self.assertEqual(cyclic_stats([[0]], state_count=3)["entropy"], 0.0)


if __name__ == "__main__":
    unittest.main()
