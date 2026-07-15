"""Tests for generalized finite-state one-dimensional CA rule families."""

from __future__ import annotations

import random
import unittest

from elementary_ca import BOUNDARY_FIXED, BOUNDARY_INFINITE, BOUNDARY_WRAP
from elementary_ca import step_elementary
from one_dimensional_ca import (
    FAMILY_ELEMENTARY,
    FAMILY_HIGHER_ORDER,
    FAMILY_MULTISTATE,
    FAMILY_RADIUS,
    FAMILY_REVERSIBLE,
    FAMILY_TOTALISTIC,
    RuleSpec,
    default_rule_spec,
    encode_lookup_rule,
    encode_totalistic_rule,
    next_uniform_background,
    normalize_state_row,
    random_state_seed,
    reverse_reversible_step,
    row_statistics,
    short_rule_code,
    single_state_seed,
    step_one_dimensional,
    transition_output,
)


class RuleSpecTests(unittest.TestCase):
    def test_elementary_rule_space_matches_wolfram_range(self) -> None:
        spec = RuleSpec(FAMILY_ELEMENTARY, 255, 2, 1)

        self.assertEqual(spec.output_count, 8)
        self.assertEqual(spec.max_code, 255)
        with self.assertRaises(ValueError):
            RuleSpec(FAMILY_ELEMENTARY, 256, 2, 1)

    def test_family_constraints_reject_unbounded_combinations(self) -> None:
        with self.assertRaises(ValueError):
            RuleSpec(FAMILY_MULTISTATE, 0, 2, 1)
        with self.assertRaises(ValueError):
            RuleSpec(FAMILY_RADIUS, 0, 3, 2)
        with self.assertRaises(ValueError):
            RuleSpec(FAMILY_REVERSIBLE, 0, 2, 2)

    def test_mapping_round_trip_preserves_rule_definition(self) -> None:
        original = default_rule_spec(FAMILY_TOTALISTIC, states=4, radius=3)

        self.assertEqual(RuleSpec.from_mapping(original.as_dict()), original)

    def test_compact_rule_code_keeps_both_ends(self) -> None:
        value = 12345678901234567890

        compact = short_rule_code(value, 13)

        self.assertTrue(compact.startswith("12345"))
        self.assertTrue(compact.endswith("67890"))
        self.assertIn("...", compact)


class GeneralRuleEvolutionTests(unittest.TestCase):
    def test_general_elementary_engine_matches_existing_engine_for_all_rules(self) -> None:
        row = tuple(random.Random(44).randrange(2) for _ in range(31))
        for boundary in (BOUNDARY_INFINITE, BOUNDARY_FIXED, BOUNDARY_WRAP):
            for rule in range(256):
                with self.subTest(boundary=boundary, rule=rule):
                    expected = step_elementary(
                        row,
                        rule,
                        boundary=boundary,
                        background=0,
                    )
                    actual = step_one_dimensional(
                        row,
                        RuleSpec(FAMILY_ELEMENTARY, rule, 2, 1),
                        boundary=boundary,
                        background=0,
                    )
                    self.assertEqual(actual, expected)

    def test_totalistic_rule_uses_neighborhood_sum(self) -> None:
        code = encode_totalistic_rule(3, 1, lambda total: total % 3)
        spec = RuleSpec(FAMILY_TOTALISTIC, code, 3, 1)

        self.assertEqual(transition_output(spec, (2, 1, 2)), 2)
        self.assertEqual(transition_output(spec, (1, 1, 1)), 0)

    def test_multistate_lookup_supports_three_distinct_colors(self) -> None:
        code = encode_lookup_rule(3, 1, lambda neighborhood: sum(neighborhood) % 3)
        spec = RuleSpec(FAMILY_MULTISTATE, code, 3, 1)

        result = step_one_dimensional((0, 1, 2, 0), spec, boundary=BOUNDARY_WRAP)

        self.assertEqual(result, (1, 0, 0, 2))
        self.assertTrue(set(result).issubset({0, 1, 2}))

    def test_radius_two_rule_reads_five_cells(self) -> None:
        code = encode_lookup_rule(2, 2, lambda neighborhood: neighborhood[0])
        spec = RuleSpec(FAMILY_RADIUS, code, 2, 2)

        result = step_one_dimensional(
            (1, 0, 0, 0, 0),
            spec,
            boundary=BOUNDARY_FIXED,
        )

        self.assertEqual(result, (0, 0, 1, 0, 0))

    def test_higher_order_rule_depends_on_preceding_row(self) -> None:
        spec = default_rule_spec(FAMILY_HIGHER_ORDER)
        current = (0, 1, 0, 1, 0)
        previous_a = (0, 0, 0, 0, 0)
        previous_b = (0, 1, 0, 0, 0)

        result_a = step_one_dimensional(
            current,
            spec,
            boundary=BOUNDARY_FIXED,
            previous_row=previous_a,
        )
        result_b = step_one_dimensional(
            current,
            spec,
            boundary=BOUNDARY_FIXED,
            previous_row=previous_b,
        )

        self.assertNotEqual(result_a, result_b)
        self.assertNotEqual(result_a[1], result_b[1])

    def test_reversible_rule_recovers_the_exact_preceding_row(self) -> None:
        spec = default_rule_spec(FAMILY_REVERSIBLE)
        previous = (1, 0, 1, 1, 0, 0, 1)
        current = (0, 1, 1, 0, 1, 0, 0)
        following = step_one_dimensional(
            current,
            spec,
            boundary=BOUNDARY_WRAP,
            previous_row=previous,
        )

        recovered = reverse_reversible_step(
            current,
            following,
            spec,
            boundary=BOUNDARY_WRAP,
        )

        self.assertEqual(recovered, previous)

    def test_infinite_background_uses_memory_state(self) -> None:
        spec = default_rule_spec(FAMILY_REVERSIBLE)

        self.assertEqual(
            next_uniform_background(spec, 0, previous_background=1),
            1,
        )


class GeneralSeedAndStatsTests(unittest.TestCase):
    def test_multistate_seed_and_normalization(self) -> None:
        seed = single_state_seed(7, states=4, value=3)

        self.assertEqual(seed, (0, 0, 0, 3, 0, 0, 0))
        self.assertEqual(normalize_state_row(seed, 4), seed)
        with self.assertRaises(ValueError):
            normalize_state_row((0, 4), 4)

    def test_random_seed_only_uses_valid_nonzero_states(self) -> None:
        seed = random_state_seed(
            100,
            states=4,
            density=1.0,
            rng=random.Random(5),
        )

        self.assertTrue(set(seed).issubset({1, 2, 3}))

    def test_statistics_count_nonzero_states_instead_of_summing_values(self) -> None:
        stats = row_statistics((0, 1, 2, 3), 4)

        self.assertEqual(stats["active"], 3)
        self.assertEqual(stats["density"], 75.0)
        self.assertEqual(stats["diversity"], 4)


if __name__ == "__main__":
    unittest.main()
