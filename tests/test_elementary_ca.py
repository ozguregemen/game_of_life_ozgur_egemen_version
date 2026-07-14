import random
import unittest

from elementary_ca import (
    BOUNDARY_FIXED,
    BOUNDARY_INFINITE,
    BOUNDARY_WRAP,
    NEIGHBORHOODS,
    neighborhood_output,
    next_background,
    random_seed,
    row_stats,
    rule_bits,
    single_cell_seed,
    step_elementary,
)


class ElementaryCATests(unittest.TestCase):
    def test_rule_30_bits_follow_wolfram_neighborhood_order(self) -> None:
        self.assertEqual(rule_bits(30), (0, 0, 0, 1, 1, 1, 1, 0))
        outputs = tuple(neighborhood_output(30, item) for item in NEIGHBORHOODS)
        self.assertEqual(outputs, rule_bits(30))

    def test_rule_30_single_cell_first_two_generations(self) -> None:
        seed = (0, 0, 0, 1, 0, 0, 0)
        first = step_elementary(seed, 30)
        second = step_elementary(first, 30)
        self.assertEqual(first, (0, 0, 1, 1, 1, 0, 0))
        self.assertEqual(second, (0, 1, 1, 0, 0, 1, 0))

    def test_rule_90_single_cell_forms_two_branches(self) -> None:
        self.assertEqual(
            step_elementary((0, 0, 0, 1, 0, 0, 0), 90),
            (0, 0, 1, 0, 1, 0, 0),
        )

    def test_mathworld_boolean_forms_match_rules_30_and_90(self) -> None:
        for left, center, right in NEIGHBORHOODS:
            with self.subTest(neighborhood=(left, center, right)):
                self.assertEqual(
                    neighborhood_output(30, (left, center, right)),
                    left ^ (center | right),
                )
                self.assertEqual(
                    neighborhood_output(90, (left, center, right)),
                    left ^ right,
                )

    def test_rule_110_single_cell_first_two_generations(self) -> None:
        seed = (0, 0, 0, 1, 0, 0, 0)
        first = step_elementary(seed, 110)
        second = step_elementary(first, 110)
        self.assertEqual(first, (0, 0, 1, 1, 0, 0, 0))
        self.assertEqual(second, (0, 1, 1, 1, 0, 0, 0))

    def test_boundary_modes_differ_at_edges(self) -> None:
        row = (1, 0, 0)
        fixed = step_elementary(row, 90, boundary=BOUNDARY_FIXED)
        wrapped = step_elementary(row, 90, boundary=BOUNDARY_WRAP)
        self.assertNotEqual(fixed, wrapped)
        self.assertEqual(fixed, (0, 1, 0))
        self.assertEqual(wrapped, (0, 1, 1))

    def test_infinite_background_can_evolve_and_feed_visible_edges(self) -> None:
        self.assertEqual(next_background(1, 0), 1)
        self.assertEqual(next_background(1, 1), 0)
        self.assertEqual(
            step_elementary(
                (0, 0, 0),
                90,
                boundary=BOUNDARY_INFINITE,
                background=1,
            ),
            (1, 0, 1),
        )

    def test_fixed_zero_ignores_an_infinite_background_value(self) -> None:
        self.assertEqual(
            step_elementary(
                (0, 0, 0),
                90,
                boundary=BOUNDARY_FIXED,
                background=1,
            ),
            (0, 0, 0),
        )

    def test_single_cell_and_random_seeds_have_requested_width(self) -> None:
        self.assertEqual(single_cell_seed(8), (0, 0, 0, 0, 1, 0, 0, 0))
        seeded = random_seed(12, density=0.5, rng=random.Random(7))
        self.assertEqual(len(seeded), 12)
        self.assertTrue(set(seeded) <= {0, 1})

    def test_row_stats_report_active_density(self) -> None:
        self.assertEqual(
            row_stats((1, 0, 1, 0)),
            {"active": 2, "inactive": 2, "density": 50.0},
        )

    def test_invalid_inputs_raise_clear_errors(self) -> None:
        with self.assertRaises(ValueError):
            step_elementary((), 30)
        with self.assertRaises(ValueError):
            step_elementary((0, 2, 0), 30)
        with self.assertRaises(ValueError):
            step_elementary((0, 1, 0), 256)
        with self.assertRaises(ValueError):
            step_elementary((0, 1, 0), 30, boundary="mirror")


if __name__ == "__main__":
    unittest.main()
