import random
import unittest

from brians_brain import (
    DYING,
    FIRING,
    OFF,
    apply_brain_rules,
    brain_stats,
    randomize_brain_grid,
)


class BriansBrainRuleTests(unittest.TestCase):
    def test_off_cell_fires_with_exactly_two_firing_neighbors(self) -> None:
        grid = [
            [FIRING, FIRING, OFF],
            [OFF, OFF, OFF],
            [OFF, OFF, OFF],
        ]
        self.assertEqual(apply_brain_rules(grid)[1][1], FIRING)

    def test_dying_neighbors_do_not_count_toward_birth(self) -> None:
        grid = [
            [FIRING, DYING, OFF],
            [OFF, OFF, OFF],
            [OFF, OFF, OFF],
        ]
        self.assertEqual(apply_brain_rules(grid)[1][1], OFF)

    def test_firing_cell_becomes_dying(self) -> None:
        self.assertEqual(apply_brain_rules([[FIRING]]), [[DYING]])

    def test_dying_cell_becomes_off(self) -> None:
        self.assertEqual(apply_brain_rules([[DYING]]), [[OFF]])

    def test_random_grid_contains_active_cells(self) -> None:
        grid = randomize_brain_grid(
            20,
            20,
            density=0.5,
            rng=random.Random(7),
        )
        stats = brain_stats(grid)
        self.assertGreater(stats["firing"], 0)
        self.assertGreater(stats["dying"], 0)

    def test_statistics_count_all_three_states(self) -> None:
        stats = brain_stats([[FIRING, DYING, OFF, OFF]])
        self.assertEqual(stats["firing"], 1)
        self.assertEqual(stats["dying"], 1)
        self.assertEqual(stats["active"], 2)
        self.assertEqual(stats["off"], 2)
        self.assertEqual(stats["density"], 50.0)


if __name__ == "__main__":
    unittest.main()
