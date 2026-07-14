import random
import unittest

from wireworld import (
    CONDUCTOR,
    ELECTRON_HEAD,
    ELECTRON_TAIL,
    EMPTY,
    apply_wireworld_rules,
    make_wireworld_grid,
    randomize_wireworld_grid,
    wireworld_stats,
)


class WireworldTests(unittest.TestCase):
    def test_empty_cell_stays_empty(self) -> None:
        grid = make_wireworld_grid(3, 3)
        grid[1][0] = ELECTRON_HEAD
        self.assertEqual(apply_wireworld_rules(grid)[1][1], EMPTY)

    def test_electron_head_becomes_tail(self) -> None:
        grid = make_wireworld_grid(1, 1)
        grid[0][0] = ELECTRON_HEAD
        self.assertEqual(apply_wireworld_rules(grid)[0][0], ELECTRON_TAIL)

    def test_electron_tail_becomes_conductor(self) -> None:
        grid = make_wireworld_grid(1, 1)
        grid[0][0] = ELECTRON_TAIL
        self.assertEqual(apply_wireworld_rules(grid)[0][0], CONDUCTOR)

    def test_conductor_with_one_or_two_heads_becomes_head(self) -> None:
        for head_positions in (((0, 0),), ((0, 0), (0, 1))):
            with self.subTest(head_count=len(head_positions)):
                grid = make_wireworld_grid(3, 3)
                grid[1][1] = CONDUCTOR
                for row, col in head_positions:
                    grid[row][col] = ELECTRON_HEAD
                self.assertEqual(
                    apply_wireworld_rules(grid)[1][1],
                    ELECTRON_HEAD,
                )

    def test_conductor_with_zero_or_three_heads_stays_conductor(self) -> None:
        for head_positions in ((), ((0, 0), (0, 1), (1, 0))):
            with self.subTest(head_count=len(head_positions)):
                grid = make_wireworld_grid(3, 3)
                grid[1][1] = CONDUCTOR
                for row, col in head_positions:
                    grid[row][col] = ELECTRON_HEAD
                self.assertEqual(apply_wireworld_rules(grid)[1][1], CONDUCTOR)

    def test_signal_moves_along_straight_conductor(self) -> None:
        grid = [[ELECTRON_TAIL, ELECTRON_HEAD, CONDUCTOR, CONDUCTOR]]
        next_grid = apply_wireworld_rules(grid)
        self.assertEqual(
            next_grid,
            [[CONDUCTOR, ELECTRON_TAIL, ELECTRON_HEAD, CONDUCTOR]],
        )

    def test_invalid_cell_state_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            apply_wireworld_rules([[99]])

    def test_random_board_and_statistics(self) -> None:
        grid = randomize_wireworld_grid(
            20,
            20,
            conductor_density=0.5,
            signal_fraction=0.2,
            rng=random.Random(4),
        )
        stats = wireworld_stats(grid)
        self.assertGreater(stats["conductors"], 0)
        self.assertGreater(stats["heads"], 0)
        self.assertGreater(stats["tails"], 0)
        self.assertEqual(stats["occupied"] + stats["empty"], 400)


if __name__ == "__main__":
    unittest.main()
