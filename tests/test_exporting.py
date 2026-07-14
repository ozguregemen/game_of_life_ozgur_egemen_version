"""Tests for safe diagram, animation, metric, and experiment exports."""

from __future__ import annotations

import csv
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from exporting import (
    ExportRunner,
    RasterFrame,
    export_path,
    render_frame_array,
    sampled_indices,
    save_analysis_csv,
    save_experiment_json,
    save_gif,
    save_mp4,
    save_png,
)
from scientific_analysis import AnalysisSample

PALETTE = {0: (1, 2, 3), 1: (240, 230, 220)}


class ExportSamplingTests(unittest.TestCase):
    def test_sampling_preserves_first_last_and_requested_count(self) -> None:
        indices = sampled_indices(1000, 120)

        self.assertEqual(len(indices), 120)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 999)
        self.assertEqual(tuple(sorted(set(indices))), indices)

    def test_short_timelines_keep_every_frame(self) -> None:
        self.assertEqual(sampled_indices(4, 120), (0, 1, 2, 3))

    def test_export_paths_are_sanitized_and_do_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            moment = datetime(2026, 7, 14, 18, 30, tzinfo=timezone.utc)
            first = export_path(
                "Rule 30/../Test",
                ".PNG",
                directory=directory,
                timestamp=moment,
            )
            first.touch()
            second = export_path(
                "Rule 30/../Test",
                ".png",
                directory=directory,
                timestamp=moment,
            )

            self.assertEqual(first.name, "rule_30___test-20260714-183000.png")
            self.assertEqual(second.stem, "rule_30___test-20260714-183000-2")


class RasterExportTests(unittest.TestCase):
    def test_ragged_rows_are_center_aligned(self) -> None:
        frame = RasterFrame(2, ((1,), (1, 1, 1)))
        rendered = render_frame_array(frame, PALETTE)

        self.assertEqual(rendered.shape, (2, 3, 3))
        self.assertEqual(tuple(rendered[0, 0]), PALETTE[0])
        self.assertEqual(tuple(rendered[0, 1]), PALETTE[1])
        self.assertEqual(tuple(rendered[1, 2]), PALETTE[1])

    def test_png_has_expected_nearest_neighbor_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagram.png"
            save_png(
                RasterFrame(0, ((0, 1), (1, 0))),
                PALETTE,
                path,
                scale=3,
            )

            with Image.open(path) as image:
                self.assertEqual(image.size, (6, 6))
                self.assertEqual(image.getpixel((0, 0)), PALETTE[0])
                self.assertEqual(image.getpixel((4, 1)), PALETTE[1])

    def test_gif_contains_multiple_timeline_frames(self) -> None:
        frames = (
            RasterFrame(0, ((0, 1), (0, 0))),
            RasterFrame(1, ((1, 0), (0, 1))),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.gif"
            save_gif(frames, PALETTE, path, scale=2, duration_ms=80)

            with Image.open(path) as image:
                self.assertEqual(image.n_frames, 2)
                self.assertEqual(image.size, (4, 4))
                self.assertEqual(image.info["duration"], 80)

    def test_mp4_is_encoded_as_real_iso_media(self) -> None:
        frames = (
            RasterFrame(0, ((0, 1), (0, 0))),
            RasterFrame(1, ((1, 0), (0, 1))),
            RasterFrame(2, ((1, 1), (1, 1))),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.mp4"
            save_mp4(frames, PALETTE, path, scale=4, fps=5)

            payload = path.read_bytes()
            self.assertGreater(len(payload), 500)
            self.assertIn(b"ftyp", payload[:32])


class DataExportTests(unittest.TestCase):
    def test_csv_has_stable_columns_and_numeric_measurements(self) -> None:
        samples = (
            AnalysisSample(0, 1, 25.0, 0.5, 0.0, b"a"),
            AnalysisSample(1, 2, 50.0, 1.0, 75.0, b"b"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "metrics.csv"
            save_analysis_csv(
                samples,
                path,
                period=2,
                stabilization_generation=0,
            )

            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["generation"], "1")
            self.assertEqual(rows[1]["density_percent"], "50.00000000")
            self.assertEqual(rows[1]["detected_period"], "2")
            self.assertEqual(rows[1]["stabilization_generation"], "0")

    def test_json_is_utf8_and_refuses_implicit_overwrite(self) -> None:
        document = {"name": "Özgür deneyi", "cells": [[0, 1]]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "experiment.json"
            save_experiment_json(document, path)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), document)
            with self.assertRaises(FileExistsError):
                save_experiment_json(document, path)

    def test_export_runner_reports_success_without_blocking_submitter(self) -> None:
        runner = ExportRunner()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "result.txt"
                self.assertTrue(runner.submit("test", lambda: path))
                deadline = time.monotonic() + 2.0
                outcome = None
                while outcome is None and time.monotonic() < deadline:
                    outcome = runner.poll()
                    time.sleep(0.005)
                self.assertIsNotNone(outcome)
                self.assertTrue(outcome.succeeded)
                self.assertEqual(outcome.path, path)
        finally:
            runner.shutdown()

    def test_completed_job_cannot_be_replaced_before_result_is_polled(self) -> None:
        runner = ExportRunner()
        try:
            first = Path("first.txt")
            self.assertTrue(runner.submit("first", lambda: first))
            deadline = time.monotonic() + 2.0
            while runner.busy and time.monotonic() < deadline:
                time.sleep(0.005)

            self.assertFalse(runner.submit("second", lambda: Path("second.txt")))
            self.assertEqual(runner.poll().path, first)
        finally:
            runner.shutdown()


if __name__ == "__main__":
    unittest.main()
