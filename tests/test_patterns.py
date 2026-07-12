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


if __name__ == "__main__":
    unittest.main()
