from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from experiment_lab import (
    ENGINE_1D,
    ENGINE_2D_ANT,
    ENGINE_2D_BRAIN,
    ENGINE_2D_CYCLIC,
    ENGINE_2D_IMMIGRATION,
    ENGINE_2D_LIFE,
    ENGINE_2D_WIREWORLD,
    ENGINE_3D_GENERATIONS,
    ENGINE_3D_LIFE,
    SEED_RANDOM,
    SEED_SINGLE,
    ExperimentPlan,
    ExperimentRule,
    ExperimentRunner,
    export_experiment_csv,
    export_experiment_json,
    run_experiment_plan,
)
from one_dimensional_ca import RuleSpec


class ExperimentLabTests(unittest.TestCase):
    def one_d_rule(self, code: int = 30) -> ExperimentRule:
        spec = RuleSpec(code=code)
        return ExperimentRule(
            f"eca-{code}",
            f"Rule {code}",
            "1d",
            ENGINE_1D,
            spec.as_dict(),
        )

    def test_plan_rejects_unbounded_workload(self) -> None:
        with self.assertRaisesRegex(ValueError, "cell updates"):
            ExperimentPlan(
                "3d",
                "Spatial Life",
                tuple(
                    ExperimentRule(
                        f"rule-{index}",
                        f"Rule {index}",
                        "3d",
                        ENGINE_3D_LIFE,
                        {
                            "birth": (6,),
                            "survival": (5, 6, 7),
                            "neighborhood": "moore",
                        },
                    )
                    for index in range(8)
                ),
                ("fixed", "wrap", "reflect"),
                (48,),
                (500,),
                2,
                (SEED_RANDOM,),
                (0.2,),
                1,
            )

    def test_repeated_sweep_is_deterministic_and_aggregated(self) -> None:
        plan = ExperimentPlan(
            "1d",
            "Elementary",
            (self.one_d_rule(30), self.one_d_rule(90)),
            ("fixed", "wrap"),
            (31,),
            (20,),
            2,
            (SEED_RANDOM,),
            (0.2,),
            987654,
        )
        first = run_experiment_plan(plan)
        second = run_experiment_plan(plan)

        self.assertEqual(first.runs, second.runs)
        self.assertEqual(first.aggregates, second.aggregates)
        self.assertEqual(len(first.runs), 8)
        self.assertEqual(len(first.aggregates), 4)
        self.assertTrue(all(item.repetitions == 2 for item in first.aggregates))

    def test_translating_rule_records_displacement_speed_and_detection_rate(self) -> None:
        plan = ExperimentPlan(
            "1d",
            "Elementary",
            (self.one_d_rule(170),),
            ("fixed",),
            (31,),
            (10,),
            1,
            (SEED_SINGLE,),
            (0.20,),
            17,
        )

        report = run_experiment_plan(plan)
        run = report.runs[0]
        aggregate = report.aggregates[0]

        self.assertTrue(run.translation_detected)
        self.assertEqual(run.translation_period, 1)
        self.assertEqual(run.translation_displacement, (-1,))
        self.assertEqual(run.translation_speed, 1.0)
        self.assertEqual(aggregate.translation_detection_rate, 100.0)
        self.assertEqual(aggregate.mean_translation_speed, 1.0)

    def test_multi_factor_cartesian_sweep_preserves_each_configuration(self) -> None:
        plan = ExperimentPlan(
            "1d",
            "Elementary",
            (self.one_d_rule(30), self.one_d_rule(90)),
            ("fixed", "wrap"),
            (15, 21),
            (10, 12),
            2,
            (SEED_RANDOM, SEED_SINGLE),
            (0.10, 0.35),
            1234,
        )
        report = run_experiment_plan(plan)

        self.assertEqual(plan.run_count, 80)
        self.assertEqual(len(report.runs), 80)
        self.assertEqual(len(report.aggregates), 48)
        configurations = {
            (
                item.rule_key,
                item.boundary,
                item.size,
                item.generations,
                item.seed_kind,
                item.seed_density,
            )
            for item in report.aggregates
        }
        self.assertEqual(len(configurations), 48)
        paired_seed_sets = {
            rule_key: {
                run.seed
                for run in report.runs
                if run.rule_key == rule_key
                and run.boundary == "fixed"
                and run.size == 15
                and run.generations == 10
                and run.seed_kind == SEED_RANDOM
                and run.seed_density == 0.10
            }
            for rule_key in ("eca-30", "eca-90")
        }
        self.assertEqual(paired_seed_sets["eca-30"], paired_seed_sets["eca-90"])

    def test_dimension_specific_engines_produce_measurements(self) -> None:
        conway = ExperimentRule(
            "conway",
            "Conway",
            "2d",
            ENGINE_2D_LIFE,
            {"birth": (3,), "survival": (2, 3)},
        )
        spatial = ExperimentRule(
            "bays",
            "Bays 5766",
            "3d",
            ENGINE_3D_LIFE,
            {
                "birth": (6,),
                "survival": (5, 6, 7),
                "neighborhood": "moore",
            },
        )
        plans = (
            ExperimentPlan("2d", "Life-like", (conway,), ("fixed",), (9,), (10,), 1, (SEED_SINGLE,), (0.2,), 7),
            ExperimentPlan("3d", "Spatial Life", (spatial,), ("fixed",), (5,), (10,), 1, (SEED_SINGLE,), (0.2,), 7),
        )
        for plan in plans:
            report = run_experiment_plan(plan)
            self.assertEqual(len(report.runs), 1)
            self.assertGreaterEqual(report.runs[0].mean_entropy, 0.0)
            self.assertLessEqual(report.runs[0].mean_entropy, 1.0)
            self.assertGreaterEqual(report.runs[0].final_bounding_box_fill, 0.0)
            self.assertLessEqual(report.runs[0].final_bounding_box_fill, 100.0)
            self.assertGreaterEqual(report.runs[0].final_anisotropy, 0.0)
            self.assertLessEqual(report.runs[0].final_anisotropy, 1.0)
            aggregate = report.aggregates[0]
            self.assertGreaterEqual(aggregate.mean_largest_component_fraction, 0.0)
            self.assertLessEqual(aggregate.mean_largest_component_fraction, 100.0)
            self.assertGreaterEqual(aggregate.translation_detection_rate, 0.0)
            self.assertLessEqual(aggregate.translation_detection_rate, 100.0)

    def test_every_specialized_mode_engine_completes_a_bounded_run(self) -> None:
        rules = (
            ExperimentRule("immigration", "Immigration", "2d", ENGINE_2D_IMMIGRATION, {}),
            ExperimentRule("brain", "Brian's Brain", "2d", ENGINE_2D_BRAIN, {}),
            ExperimentRule("ant", "Langton's Ant", "2d", ENGINE_2D_ANT, {}),
            ExperimentRule("wire", "Wireworld", "2d", ENGINE_2D_WIREWORLD, {}),
            ExperimentRule(
                "cyclic",
                "Cyclic",
                "2d",
                ENGINE_2D_CYCLIC,
                {"state_count": 8, "threshold": 1},
            ),
        )
        for rule in rules:
            report = run_experiment_plan(
                ExperimentPlan(
                    "2d",
                    rule.name,
                    (rule,),
                    ("fixed",),
                    (9,),
                    (10,),
                    1,
                    (SEED_SINGLE if rule.engine == ENGINE_2D_ANT else SEED_RANDOM,),
                    (0.2,),
                    101,
                )
            )
            self.assertEqual(len(report.runs), 1, rule.engine)

        generations = ExperimentRule(
            "445",
            "445",
            "3d",
            ENGINE_3D_GENERATIONS,
            {
                "survival": (4,),
                "birth": (4,),
                "state_count": 5,
                "neighborhood": "moore",
                "seed_density": 0.2,
            },
        )
        report = run_experiment_plan(
            ExperimentPlan(
                "3d",
                "3D Generations",
                (generations,),
                ("reflect",),
                (5,),
                (10,),
                1,
                (SEED_RANDOM,),
                (0.2,),
                202,
            )
        )
        self.assertEqual(len(report.runs), 1)

    def test_background_runner_reports_progress_without_blocking(self) -> None:
        runner = ExperimentRunner()
        try:
            plan = ExperimentPlan(
                "1d",
                "Elementary",
                (self.one_d_rule(),),
                ("fixed",),
                (31,),
                (10,),
                2,
                (SEED_RANDOM,),
                (0.2,),
                5,
            )
            self.assertTrue(runner.request(plan))
            self.assertFalse(runner.request(plan))
            report = None
            for _ in range(1000):
                report = runner.poll()
                if report is not None:
                    break
                threading.Event().wait(0.002)
            self.assertIsNotNone(report)
            self.assertEqual(runner.progress.completed_runs, 2)
        finally:
            runner.shutdown()

    def test_json_and_csv_exports_are_machine_readable(self) -> None:
        plan = ExperimentPlan(
            "1d",
            "Elementary",
            (self.one_d_rule(),),
            ("fixed",),
            (15,),
            (10,),
            1,
            (SEED_SINGLE,),
            (0.2,),
            42,
        )
        report = run_experiment_plan(plan)
        with tempfile.TemporaryDirectory() as temporary:
            with patch("experiment_lab.EXPERIMENT_EXPORT_DIRECTORY", Path(temporary)):
                json_path = export_experiment_json(report)
                csv_path = export_experiment_csv(report)
            document = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(document["schema"], "cellular-automata-lab-batch-experiment")
            self.assertEqual(document["version"], 2)
            self.assertEqual(document["plan"]["master_seed"], 42)
            self.assertIn("final_anisotropy", document["runs"][0])
            self.assertIn("translation_detection_rate", document["aggregates"][0])
            csv_lines = csv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(csv_lines), 2)
            self.assertIn("mean_entropy", csv_lines[0])
            self.assertIn("translation_speed", csv_lines[0])


if __name__ == "__main__":
    unittest.main()
