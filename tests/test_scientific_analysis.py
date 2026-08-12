"""Tests for live measurements, cycle detection, and 1D rule comparison."""

from __future__ import annotations

import unittest

from rules import apply_rules
from scientific_analysis import (
    AnalysisSeries,
    ScientificAnalysisRegistry,
    StateObservation,
    compare_elementary_rules,
    neighbor_agreement_rate,
    normalized_block_entropy,
    normalized_entropy,
    state_change_rate,
    structural_metrics,
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

    def test_block_entropy_reaches_one_for_all_binary_length_three_blocks(self) -> None:
        values = tuple(
            bit
            for code in range(8)
            for bit in ((code >> 2) & 1, (code >> 1) & 1, code & 1)
        )

        self.assertAlmostEqual(normalized_block_entropy(values, 2, (24,)), 1.0)
        self.assertEqual(normalized_block_entropy((0,) * 24, 2, (24,)), 0.0)

    def test_neighbor_agreement_uses_orthogonal_pairs_in_two_dimensions(self) -> None:
        values = (0, 0, 1, 1)

        self.assertEqual(neighbor_agreement_rate(values, (2, 2)), 50.0)

    def test_observation_rejects_shape_that_does_not_match_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "shape"):
            StateObservation(
                key="shape",
                title="Shape",
                generation=0,
                values=(0, 1, 0),
                state_count=2,
                active_states=(1,),
                lattice_shape=(2, 2),
            )

    def test_population_density_and_change_are_recorded(self) -> None:
        series = AnalysisSeries("test")
        series.reset(observation(0, (0, 1, 0, 1)))
        sample = series.observe(observation(1, (1, 1, 0, 0)))

        self.assertEqual(sample.population, 2)
        self.assertEqual(sample.density, 50.0)
        self.assertEqual(sample.change_rate, 50.0)
        self.assertAlmostEqual(sample.entropy, 1.0)
        self.assertGreaterEqual(sample.block_entropy, 0.0)
        self.assertAlmostEqual(sample.neighbor_agreement, 2 / 3 * 100)
        self.assertEqual(sample.growth_rate, 0.0)
        self.assertEqual(sample.state_utilization, 100.0)

    def test_window_summary_reports_descriptive_statistics_and_slope(self) -> None:
        series = AnalysisSeries("summary")
        series.reset(observation(0, (0, 0, 0, 0)))
        series.observe(observation(1, (1, 0, 0, 0)))
        series.observe(observation(2, (1, 1, 0, 0)))
        series.observe(observation(3, (1, 1, 1, 0)))

        summary = series.window_summary(window=3)

        density = summary.metrics["density"]
        self.assertEqual(summary.sample_count, 3)
        self.assertAlmostEqual(density.current, 75.0)
        self.assertAlmostEqual(density.mean, 50.0)
        self.assertAlmostEqual(density.slope_per_generation, 25.0)
        self.assertIn("candidate", summary.heuristic_regime.lower())

    def test_series_metadata_tracks_an_expanding_1d_lattice(self) -> None:
        series = AnalysisSeries("expanding")
        series.reset(observation(0, (1,)))
        series.observe(observation(1, (0, 1, 0)))

        self.assertEqual(series.lattice_shape, (3,))

    def test_structural_metrics_measure_components_extent_and_compactness(self) -> None:
        values = (
            1, 1, 0, 0, 0,
            0, 0, 0, 0, 0,
            0, 0, 0, 1, 1,
        )

        metrics = structural_metrics(values, (3, 5), (1,))

        self.assertEqual(metrics.component_count, 2)
        self.assertEqual(metrics.largest_component, 2)
        self.assertEqual(metrics.bounding_box_shape, (3, 5))
        self.assertAlmostEqual(metrics.bounding_box_fill, 4 / 15 * 100)
        self.assertEqual(metrics.centroid, (1.0, 2.0))
        self.assertAlmostEqual(metrics.exposed_faces_per_cell, 3.0)
        self.assertGreater(metrics.radius_of_gyration, 0.0)

    def test_structural_metrics_skip_only_component_labeling_above_limit(self) -> None:
        metrics = structural_metrics((1, 1, 1, 1), (2, 2), (1,), component_limit=3)

        self.assertFalse(metrics.components_computed)
        self.assertIsNone(metrics.component_count)
        self.assertEqual(metrics.population, 4)
        self.assertEqual(metrics.bounding_box_fill, 100.0)

    def test_structural_metrics_empty_state_is_well_defined(self) -> None:
        metrics = structural_metrics((0,) * 8, (2, 2, 2), (1,))

        self.assertEqual(metrics.component_count, 0)
        self.assertEqual(metrics.bounding_box_shape, (0, 0, 0))
        self.assertEqual(metrics.centroid, ())
        self.assertEqual(metrics.exposed_faces_per_cell, 0.0)


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

    def test_glider_detects_translation_aware_period_velocity_and_direction(self) -> None:
        grid = {
            (3, 2): 1,
            (4, 3): 1,
            (2, 4): 1,
            (3, 4): 1,
            (4, 4): 1,
        }
        series = AnalysisSeries("glider")

        def frame(generation: int) -> StateObservation:
            values = tuple(
                1 if grid.get((column, row), 0) else 0
                for row in range(8)
                for column in range(8)
            )
            return StateObservation(
                key="glider",
                title="Glider",
                generation=generation,
                values=values,
                state_count=2,
                active_states=(1,),
                lattice_shape=(8, 8),
            )

        series.reset(frame(0))
        for generation in range(1, 5):
            grid = apply_rules(grid, "conway")
            series.observe(frame(generation))

        recurrence = series.translation_recurrence
        self.assertIsNotNone(recurrence)
        assert recurrence is not None
        self.assertEqual(recurrence.period, 4)
        self.assertEqual(recurrence.displacement, (1, 1))
        self.assertEqual(recurrence.velocity, (0.25, 0.25))
        self.assertAlmostEqual(recurrence.speed, 2**0.5 / 4)
        self.assertTrue(recurrence.moving)
        self.assertIsNone(series.period)

    def test_stationary_oscillator_is_not_misreported_as_motion(self) -> None:
        series = AnalysisSeries("oscillator")
        series.reset(observation(0, (0, 1, 0)))
        series.observe(observation(1, (1, 1, 1)))
        series.observe(observation(2, (0, 1, 0)))

        recurrence = series.translation_recurrence
        self.assertIsNotNone(recurrence)
        assert recurrence is not None
        self.assertEqual(recurrence.period, 2)
        self.assertEqual(recurrence.displacement, (0,))
        self.assertFalse(recurrence.moving)

    def test_recurrence_keeps_non_population_refractory_states(self) -> None:
        first = StateObservation(
            key="refractory",
            title="Generations",
            generation=0,
            values=(0, 2, 0),
            state_count=4,
            active_states=(1,),
        )
        second = StateObservation(
            **{**first.__dict__, "generation": 1, "values": (0, 3, 0)}
        )
        series = AnalysisSeries("refractory")
        series.reset(first)
        series.observe(second)

        self.assertIsNone(series.translation_recurrence)

    def test_series_structure_cache_tracks_latest_generation(self) -> None:
        series = AnalysisSeries("structure")
        first = StateObservation(
            key="structure",
            title="Structure",
            generation=0,
            values=(1, 0, 0, 1),
            state_count=2,
            active_states=(1,),
            lattice_shape=(2, 2),
        )
        series.reset(first)
        initial = series.structure()
        self.assertEqual(initial.component_count, 2)
        self.assertIs(initial, series.structure())

        series.observe(
            StateObservation(**{**first.__dict__, "generation": 1, "values": (1, 1, 0, 0)})
        )
        latest = series.structure()
        self.assertEqual(latest.component_count, 1)
        self.assertIsNot(initial, latest)


class ElementaryComparisonTests(unittest.TestCase):
    def test_comparison_reports_requested_rules_in_order(self) -> None:
        results = compare_elementary_rules((30, 90, 30), generations=12)

        self.assertEqual([result.rule for result in results], [30, 90])
        self.assertTrue(all(result.generations == 12 for result in results))
        self.assertTrue(all(0.0 <= result.mean_entropy <= 1.0 for result in results))
        self.assertTrue(
            all(0.0 <= result.mean_block_entropy <= 1.0 for result in results)
        )
        self.assertTrue(
            all(0.0 <= result.mean_neighbor_agreement <= 100.0 for result in results)
        )
        self.assertTrue(all(0.0 <= result.mean_change_rate <= 100.0 for result in results))

    def test_rule_zero_reaches_a_detected_cycle(self) -> None:
        result = compare_elementary_rules((0,), generations=6)[0]

        self.assertIsNotNone(result.period)
        self.assertIsNotNone(result.stabilization_generation)


if __name__ == "__main__":
    unittest.main()
