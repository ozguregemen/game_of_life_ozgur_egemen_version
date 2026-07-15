import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

import patterns


class PatternStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.pattern_directory = Path(self.temporary_directory.name)
        self.directory_patch = patch.object(
            patterns,
            "PATTERN_DIRECTORY",
            self.pattern_directory,
        )
        self.directory_patch.start()
        patterns.refresh_pattern_cache()

    def tearDown(self) -> None:
        self.directory_patch.stop()
        self.temporary_directory.cleanup()
        patterns.refresh_pattern_cache()

    def test_safe_filename_removes_path_characters_and_parent_segments(self) -> None:
        filename = patterns.safe_pattern_filename('../My / Pattern:*?"<>|')
        self.assertNotIn("..", filename)
        self.assertFalse(any(character in filename for character in '/\\:*?"<>|'))

    def test_empty_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            patterns.save_pattern([[1]], "   ")

    def test_existing_pattern_requires_explicit_overwrite(self) -> None:
        patterns.save_pattern([[1]], "Example")
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            patterns.save_pattern([[1, 1]], "Example")

    def test_corrupt_json_is_skipped_without_breaking_cache(self) -> None:
        self.pattern_directory.mkdir(exist_ok=True)
        (self.pattern_directory / "broken.json").write_text(
            "{not json",
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as caught:
            patterns.refresh_pattern_cache()

        self.assertIn("glider", patterns.get_all_patterns())
        self.assertEqual(len(caught), 1)

    def test_invalid_two_dimensional_pattern_is_skipped(self) -> None:
        self.pattern_directory.mkdir(exist_ok=True)
        (self.pattern_directory / "invalid.json").write_text(
            json.dumps({"name": "Invalid", "pattern": [[1], [1, 0]]}),
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True):
            patterns.refresh_pattern_cache()

        self.assertNotIn("invalid", patterns.get_all_patterns())

    def test_get_all_patterns_reuses_same_cache(self) -> None:
        self.assertIs(patterns.get_all_patterns(), patterns.get_all_patterns())

    def test_builtin_patterns_are_grouped_by_simulation_mode(self) -> None:
        for mode in patterns.MODE_KEYS:
            with self.subTest(mode=mode):
                mode_patterns = patterns.get_patterns_for_mode(mode)
                self.assertTrue(mode_patterns)
                self.assertTrue(
                    all(pattern["mode"] == mode for pattern in mode_patterns.values())
                )

        self.assertIn("glider", patterns.get_patterns_for_mode("life"))
        self.assertNotIn("glider", patterns.get_patterns_for_mode("wireworld"))

    def test_mode_cache_is_reused_without_disk_reads(self) -> None:
        self.assertIs(
            patterns.get_patterns_for_mode("wireworld"),
            patterns.get_patterns_for_mode("wireworld"),
        )

    def test_builtin_catalog_sizes_respect_the_per_mode_cap(self) -> None:
        expected_sizes = {
            "life": 20,
            "immigration": 10,
            "brians_brain": 5,
            "langtons_ant": 3,
            "wireworld": 8,
            "cyclic_automaton": 3,
        }
        for mode, expected in expected_sizes.items():
            with self.subTest(mode=mode):
                catalog = patterns.get_patterns_for_mode(mode)
                self.assertEqual(len(catalog), expected)
                self.assertLessEqual(
                    len(catalog),
                    patterns.MAX_BUILTIN_PATTERNS_PER_MODE,
                )
                self.assertTrue(
                    all(pattern["category"] != "custom" for pattern in catalog.values())
                )

    def test_mode_categories_are_cached_and_cover_every_pattern(self) -> None:
        categories = patterns.get_pattern_categories_for_mode("life")
        self.assertEqual(categories[0], ("still_lifes", "Still Lifes", 3))
        self.assertEqual(sum(count for _, _, count in categories), 20)
        self.assertIs(
            patterns.get_patterns_for_category("life", "still_lifes"),
            patterns.get_patterns_for_category("life", "still_lifes"),
        )

    def test_custom_pattern_appears_in_automatic_custom_category(self) -> None:
        saved = patterns.save_pattern([[1]], "My Seed", mode="life")

        self.assertEqual(saved["category"], "custom")
        self.assertIn(
            ("custom", "Custom Patterns", 1),
            patterns.get_pattern_categories_for_mode("life"),
        )
        self.assertIn(
            "my seed",
            patterns.get_patterns_for_category("life", "custom"),
        )

    def test_legacy_json_without_mode_defaults_to_life(self) -> None:
        self.pattern_directory.mkdir(exist_ok=True)
        (self.pattern_directory / "legacy.json").write_text(
            json.dumps({"name": "Legacy", "pattern": [[1]]}),
            encoding="utf-8",
        )

        patterns.refresh_pattern_cache()

        self.assertEqual(patterns.load_pattern("Legacy")["mode"], "life")
        self.assertIn("legacy", patterns.get_patterns_for_mode("life"))

    def test_same_display_name_can_be_saved_for_different_modes(self) -> None:
        life_pattern = patterns.save_pattern([[1]], "Example", mode="life")
        wire_pattern = patterns.save_pattern([[2, 1, 3]], "Example", mode="wireworld")

        self.assertEqual(life_pattern["mode"], "life")
        self.assertEqual(wire_pattern["mode"], "wireworld")
        self.assertIsNotNone(patterns.load_pattern("Example", mode="life"))
        self.assertIsNotNone(patterns.load_pattern("Example", mode="wireworld"))

    def test_wireworld_rejects_invalid_cell_state(self) -> None:
        with self.assertRaisesRegex(TypeError, "Wireworld"):
            patterns.save_pattern([[4]], "Invalid Wire", mode="wireworld")

    def test_cyclic_pattern_accepts_all_eight_states(self) -> None:
        saved = patterns.save_pattern(
            [list(range(8))],
            "Color Cycle",
            mode="cyclic_automaton",
        )

        self.assertEqual(saved["pattern"], [list(range(8))])

    def test_cyclic_pattern_rejects_ninth_state(self) -> None:
        with self.assertRaisesRegex(TypeError, "Cyclic Cellular Automaton"):
            patterns.save_pattern([[8]], "Invalid Color", mode="cyclic_automaton")

    def test_langton_ant_metadata_must_fit_pattern(self) -> None:
        with self.assertRaisesRegex(TypeError, "inside"):
            patterns.save_pattern(
                [[0]],
                "Invalid Ant",
                mode="langtons_ant",
                ant={"row": 2, "col": 0, "direction": 0},
            )


if __name__ == "__main__":
    unittest.main()
