import json
import os
import tempfile
import unittest
import warnings
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import life
import session_storage


class SessionStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.session_directory = root / "sessions"
        self.profile_directory = self.session_directory / "eca_profiles"
        self.session_patch = patch.object(
            session_storage,
            "SESSION_DIRECTORY",
            self.session_directory,
        )
        self.profile_patch = patch.object(
            session_storage,
            "PROFILE_DIRECTORY",
            self.profile_directory,
        )
        self.session_patch.start()
        self.profile_patch.start()

    def tearDown(self) -> None:
        self.profile_patch.stop()
        self.session_patch.stop()
        self.temporary_directory.cleanup()

    def valid_session(self, name: str = "Test Session") -> dict:
        return life.capture_session_document(name)

    def test_safe_filename_blocks_path_characters_and_parent_segments(self) -> None:
        filename = session_storage.safe_storage_filename('../My / Session:*?"<>|')
        self.assertNotIn("..", filename)
        self.assertFalse(any(character in filename for character in '/\\:*?"<>|'))

    def test_session_round_trip_uses_utf8_and_requires_explicit_overwrite(self) -> None:
        document = self.valid_session("Örnek Oturum")
        path = session_storage.save_session(document)

        self.assertEqual(path.parent, self.session_directory)
        self.assertEqual(
            session_storage.load_session("Örnek Oturum")["name"],
            "Örnek Oturum",
        )
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            session_storage.save_session(document)

        session_storage.save_session(document, overwrite=True)

    def test_invalid_grid_is_rejected_before_writing(self) -> None:
        document = self.valid_session()
        document["workspaces"]["2d"]["states"]["wireworld"]["grid"][0].pop()

        with self.assertRaisesRegex(
            session_storage.DocumentValidationError,
            "must contain",
        ):
            session_storage.save_session(document)
        self.assertFalse(self.session_directory.exists())

    def test_corrupt_json_has_a_readable_error(self) -> None:
        self.session_directory.mkdir(parents=True)
        (self.session_directory / "broken.json").write_text(
            "{not json",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(session_storage.SessionStorageError, "invalid JSON"):
            session_storage.load_session("broken")

    def test_catalog_skips_corrupt_and_wrong_schema_files(self) -> None:
        session_storage.save_session(self.valid_session("Valid"))
        (self.session_directory / "broken.json").write_text("{", encoding="utf-8")
        (self.session_directory / "wrong.json").write_text(
            json.dumps({"schema": "wrong"}),
            encoding="utf-8",
        )

        with warnings.catch_warnings(record=True) as caught:
            catalog = session_storage.list_sessions()

        self.assertEqual([item["name"] for item in catalog], ["Valid"])
        self.assertEqual(len(caught), 2)

    def test_profile_round_trip_preserves_rule_boundary_and_seed(self) -> None:
        document = life.capture_experiment_profile("Kural 110 Deneyi")
        saved = session_storage.save_profile(document)

        loaded = session_storage.load_profile(saved.stem)

        self.assertEqual(loaded["name"], "Kural 110 Deneyi")
        self.assertEqual(loaded["experiment"], document["experiment"])

    def test_unsupported_version_is_rejected(self) -> None:
        document = deepcopy(self.valid_session())
        document["version"] = 999

        with self.assertRaisesRegex(
            session_storage.DocumentValidationError,
            "Unsupported session version",
        ):
            session_storage.validate_session_document(document)


if __name__ == "__main__":
    unittest.main()
