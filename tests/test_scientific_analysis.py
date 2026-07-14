"""Tests for live measurements, cycle detection, and 1D rule comparison."""

from __future__ import annotations

import unittest

from scientific_analysis import (
    AnalysisSeries,
    ScientificAnalysisRegistry,
    StateObservation,
    compare_elementary_rules,
    normalized_entropy,
    state_change_rate,
)


def observation(generation: int, values: tuple[int, ...]) -> StateObservation:
    return StateObservation(
        key="test",
        title="Test CA",
        generation=generation,
        values=values,
        state_count=2,
        active_states=(1,),
    )


class ScientificMetricTests(unittest.TestCase):
    def test_entropy_is_zero_for_uniform_and_one_for_balanced_binary_state(self) -> None:
        self.assertEqual(normalized_entropy((0, 0, 0, 0), 2), 0.0)
        self.assertAlmostEqual(normalized_entropy((0, 0, 1, 1), 2), 1.0)

    def test_change_rate_counts_changed_positions(self) -> None:
        self.assertEqual(state_change_rate((0, 1, 0, 1), (0, 0, 0, 0)), 50.0)

    def test_center_alignment_compares_expanding_1d_rows_correctly(self) -> None:
        self.assertEqual(
            state_change_rate((1,), (0, 1, 0), alignment="center"),
            0.0,
        )

    def test_population_density_and_change_are_recorded(self) -> None:
        series = AnalysisSeries("test")
        series.reset(observation(0, (0, 1, 0, 1)))
        sample = series.observe(observation(1, (1, 1, 0, 0)))

        self.assertEqual(sample.population, 2)
        self.assertEqual(sample.density, 50.0)
        self.assertEqual(sample.change_rate, 50.0)
        self.assertAlmostEqual(sample.entropy, 1.0)


class ScientificDetectionTests(unittest.TestCase):
    def test_fixed_point_detects_period_one_and_stabilization_generation(self) -> None:
        series = AnalysisSeries("stable")
        series.reset(observation(0, (0, 1, 0)))
        series.observe(observation(1, (0, 1, 0)))

        self.assertEqual(series.period, 1)
        self.assertEqual(series.stabilization_generation, 0)
        self.assertTrue(series.summary.stable)

    def test_blinker_like_sequence_detects_period_two(self) -> None:
        series = AnalysisSeries("periodic")
        series.reset(observation(0, (0, 1, 0)))
        series.observe(observation(1, (1, 1, 1)))
        series.observe(observation(2, (0, 1, 0)))

        self.assertEqual(series.period, 2)
        self.assertEqual(series.stabilization_generation, 0)
        self.assertFalse(series.summary.stable)

    def test_non_contiguous_generation_starts_a_new_experiment(self) -> None:
        series = AnalysisSeries("reset")
        series.reset(observation(0, (0, 1)))
        series.observe(observation(1, (1, 1)))
        series.observe(observation(0, (1, 0)))

        self.assertEqual(len(series.samples), 1)
        self.assertEqual(series.latest.generation, 0)
        self.assertIsNone(series.period)

    def test_experiment_context_change_resets_but_dynamic_signature_context_does_not(self) -> None:
        series = AnalysisSeries("context")
        first = StateObservation(
            key="context",
            title="Context",
            generation=0,
            values=(0, 1),
            state_count=2,
            active_states=(1,),
            experiment_context=(30, "infinite"),
            signature_context=0,
        )
        dynamic_change = StateObservation(
            **{
                **first.__dict__,
                "generation": 1,
                "signature_context": 1,
            }
        )
        new_experiment = StateObservation(
            **{
                **dynamic_change.__dict__,
                "generation": 2,
                "experiment_context": (90, "infinite"),
            }
        )

        series.reset(first)
        series.observe(dynamic_change)
        self.assertEqual(len(series.samples), 2)
        series.observe(new_experiment)
        self.assertEqual(len(series.samples), 1)

    def test_registry_keeps_modes_independent(self) -> None:
        registry = ScientificAnalysisRegistry()
        registry.observe(observation(0, (0, 1)))
        other = StateObservation(
            key="other",
            title="Other CA",
            generation=0,
            values=(1, 1),
            state_count=2,
            active_states=(1,),
        )
        registry.observe(other)

        self.assertEqual(registry.get("test").latest.population, 1)
        self.assertEqual(registry.get("other").latest.population, 2)


class ElementaryComparisonTests(unittest.TestCase):
    def test_comparison_reports_requested_rules_in_order(self) -> None:
        results = compare_elementary_rules((30, 90, 30), generations=12)

        self.assertEqual([result.rule for result in results], [30, 90])
        self.assertTrue(all(result.generations == 12 for result in results))
        self.assertTrue(all(0.0 <= result.mean_entropy <= 1.0 for result in results))
        self.assertTrue(all(0.0 <= result.mean_change_rate <= 100.0 for result in results))

    def test_rule_zero_reaches_a_detected_cycle(self) -> None:
        result = compare_elementary_rules((0,), generations=6)[0]

        self.assertIsNotNone(result.period)
        self.assertIsNotNone(result.stabilization_generation)


if __name__ == "__main__":
    unittest.main()
