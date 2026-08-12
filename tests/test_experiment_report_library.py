from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment_lab import (
    ENGINE_1D,
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


if __name__ == "__main__":
    unittest.main()
