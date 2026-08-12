from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment_lab import (
    ENGINE_1D,
    EXPERIMENT_REPORT_VERSION,
    SEED_RANDOM,
    ExperimentPlan,
    ExperimentRule,
    run_experiment_plan,
)
from experiment_report_library import (
    ExperimentReportLibrary,
    compare_reports,
    load_experiment_report,
)
from one_dimensional_ca import RuleSpec


class ExperimentReportLibraryTests(unittest.TestCase):
    def report(self, code: int, seed: int = 123):
        rule = ExperimentRule(
            f"eca-{code}",
            f"Rule {code}",
            "1d",
            ENGINE_1D,
            RuleSpec(code=code).as_dict(),
        )
        return run_experiment_plan(
            ExperimentPlan(
                "1d",
                "Elementary",
                (rule,),
                ("fixed",),
                (31,),
                (20,),
                2,
                (SEED_RANDOM,),
                (0.20,),
                seed,
            )
        )

    def test_save_refresh_load_and_delete_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            library = ExperimentReportLibrary(Path(temporary))
            report = self.report(30)

            saved = library.save(report, "Rule 30 / baseline")

            self.assertTrue(saved.path.is_file())
            self.assertNotIn("/", saved.path.name)
            self.assertEqual(saved.name, "Rule 30 / baseline")
            self.assertEqual(library.load(saved), report)
            self.assertEqual(len(library.refresh()), 1)
            library.delete(saved)
            self.assertEqual(library.entries, ())

    def test_corrupt_report_is_isolated_from_valid_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            library = ExperimentReportLibrary(directory)
            saved = library.save(self.report(30), "Valid")
            (directory / "broken.json").write_text("{broken", encoding="utf-8")

            entries = library.refresh()

            self.assertEqual(entries, (saved,))
            self.assertEqual(len(library.errors), 1)

    def test_loader_rejects_wrong_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "wrong.json"
            path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid experiment report"):
                load_experiment_report(path)

    def test_version_one_report_migrates_with_explicit_missing_metric_defaults(self) -> None:
        report = self.report(30)
        document = report.as_document()
        document["version"] = 1
        run_fields = (
            "final_component_count",
            "final_largest_component_fraction",
            "final_bounding_box_fill",
            "final_radius_of_gyration",
            "final_exposed_faces_per_cell",
            "final_anisotropy",
            "translation_detected",
            "translation_period",
            "translation_displacement",
            "translation_speed",
        )
        aggregate_fields = (
            "mean_final_component_count",
            "sd_final_component_count",
            "mean_largest_component_fraction",
            "sd_largest_component_fraction",
            "mean_bounding_box_fill",
            "sd_bounding_box_fill",
            "mean_radius_of_gyration",
            "sd_radius_of_gyration",
            "mean_exposed_faces_per_cell",
            "sd_exposed_faces_per_cell",
            "mean_anisotropy",
            "sd_anisotropy",
            "translation_detection_rate",
            "mean_translation_period",
            "sd_translation_period",
            "mean_translation_speed",
            "sd_translation_speed",
        )
        for run in document["runs"]:
            for field in run_fields:
                run.pop(field)
        for aggregate in document["aggregates"]:
            for field in aggregate_fields:
                aggregate.pop(field)

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "legacy.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            migrated = load_experiment_report(path)

        self.assertFalse(migrated.runs[0].translation_detected)
        self.assertEqual(migrated.runs[0].translation_displacement, ())
        self.assertEqual(migrated.aggregates[0].mean_anisotropy, 0.0)
        self.assertEqual(migrated.as_document()["version"], EXPERIMENT_REPORT_VERSION)

    def test_comparison_summarizes_two_reports_and_flags_grid_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            library = ExperimentReportLibrary(Path(temporary))
            first = library.save(self.report(30, 100), "Rule 30")
            second = library.save(self.report(90, 200), "Rule 90")
            comparison = compare_reports(
                ((first, library.load(first)), (second, library.load(second))),
                "entropy",
            )

            self.assertEqual(len(comparison.entries), 2)
            self.assertIn(comparison.best, comparison.entries)
            self.assertEqual(comparison.metric_label, "State entropy")
            self.assertTrue(any("Ranges show" in note for note in comparison.notes))

            structural = compare_reports(
                ((first, library.load(first)), (second, library.load(second))),
                "cohesion",
            )
            motion = compare_reports(
                ((first, library.load(first)), (second, library.load(second))),
                "translation_speed",
            )
            self.assertEqual(structural.metric_label, "Largest component share")
            self.assertEqual(motion.unit, " cells/gen")


if __name__ == "__main__":
    unittest.main()
