import random
import unittest

from langtons_ant import (
    BLACK,
    EAST,
    NORTH,
    SOUTH,
    WEST,
    WHITE,
    AntState,
    ant_stats,
    centered_ant,
    make_ant_grid,
    randomize_ant_grid,
    rotate_ant_clockwise,
    step_ant,
)


class LangtonsAntTests(unittest.TestCase):
    def test_white_cell_turns_right_flips_and_moves(self) -> None:
        grid = make_ant_grid(3, 3)
        next_grid, ant, report = step_ant(grid, AntState(1, 1, NORTH))
        self.assertEqual(next_grid[1][1], BLACK)
        self.assertEqual((ant.row, ant.col, ant.direction), (1, 2, EAST))
        self.assertEqual(report.turned, "right")

    def test_black_cell_turns_left_flips_and_moves(self) -> None:
        grid = make_ant_grid(3, 3)
        grid[1][1] = BLACK
        next_grid, ant, report = step_ant(grid, AntState(1, 1, NORTH))
        self.assertEqual(next_grid[1][1], WHITE)
        self.assertEqual((ant.row, ant.col, ant.direction), (1, 0, WEST))
        self.assertEqual(report.turned, "left")

    def test_first_four_steps_make_a_black_corner(self) -> None:
        grid = make_ant_grid(5, 5)
        ant = centered_ant(5, 5)
        for _ in range(4):
            grid, ant, _ = step_ant(grid, ant)
        self.assertEqual(ant, AntState(2, 2, NORTH))
        self.assertEqual(ant_stats(grid)["black"], 4)

    def test_crossing_boundary_deactivates_ant(self) -> None:
        grid = make_ant_grid(2, 2)
        next_grid, ant, report = step_ant(grid, AntState(0, 0, WEST))
        self.assertEqual(next_grid[0][0], BLACK)
        self.assertFalse(ant.active)
        self.assertTrue(report.exited)

    def test_rotate_ant_clockwise_cycles_directions(self) -> None:
        ant = AntState(1, 1, NORTH)
        directions = []
        for _ in range(4):
            ant = rotate_ant_clockwise(ant)
            directions.append(ant.direction)
        self.assertEqual(directions, [EAST, SOUTH, WEST, NORTH])

    def test_random_board_and_statistics(self) -> None:
        grid = randomize_ant_grid(
            20,
            20,
            density=0.4,
            rng=random.Random(3),
        )
        stats = ant_stats(grid)
        self.assertGreater(stats["black"], 0)
        self.assertGreater(stats["white"], 0)
        self.assertGreater(stats["black_density"], 0.0)


if __name__ == "__main__":
    unittest.main()
