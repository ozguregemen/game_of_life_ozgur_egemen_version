import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app_paths
from app_paths import ApplicationPaths, resolve_application_paths
from rng_state import decode_random_state, derive_seed, encode_random_state
from ui_preferences import PREFERENCES_SCHEMA, UIPreferences


class ApplicationPathTests(unittest.TestCase):
    def test_portable_override_keeps_all_user_data_under_one_root(self) -> None:
        paths = resolve_application_paths(
            {app_paths.DATA_HOME_ENVIRONMENT: "~/portable-ca"},
            platform="linux",
            home=Path("/ignored"),
        )

        self.assertEqual(paths.data, Path("~/portable-ca").expanduser())
        self.assertEqual(paths.preferences, paths.data / "config/ui_preferences.json")
        self.assertEqual(paths.profiles, paths.data / "sessions/eca_profiles")

    def test_windows_paths_use_local_data_and_roaming_config(self) -> None:
        paths = resolve_application_paths(
            {"LOCALAPPDATA": "C:/Local", "APPDATA": "C:/Roaming"},
            platform="win32",
            home=Path("C:/Users/test"),
        )

        self.assertEqual(paths.data, Path("C:/Local/cellular-automata-lab"))
        self.assertEqual(paths.config, Path("C:/Roaming/cellular-automata-lab"))

    def test_legacy_migration_copies_missing_files_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy_sessions = root / "legacy/sessions"
            legacy_profiles = legacy_sessions / "eca_profiles"
            legacy_patterns = root / "legacy/patterns"
            for directory in (legacy_sessions, legacy_profiles, legacy_patterns):
                directory.mkdir(parents=True, exist_ok=True)
            (legacy_sessions / "one.json").write_text("{\"old\": 1}", encoding="utf-8")
            (legacy_profiles / "profile.json").write_text("{}", encoding="utf-8")
            (legacy_patterns / "shape.json").write_text("{}", encoding="utf-8")
            legacy_preferences = root / "legacy/ui_preferences.json"
            legacy_preferences.write_text("{}", encoding="utf-8")
            destination = ApplicationPaths(root / "data", root / "config")
            destination.sessions.mkdir(parents=True)
            (destination.sessions / "one.json").write_text(
                "{\"new\": 1}", encoding="utf-8"
            )

            with (
                patch.object(app_paths, "APPLICATION_PATHS", destination),
                patch.object(app_paths, "LEGACY_SESSION_DIRECTORY", legacy_sessions),
                patch.object(app_paths, "LEGACY_PROFILE_DIRECTORY", legacy_profiles),
                patch.object(app_paths, "LEGACY_PATTERN_DIRECTORY", legacy_patterns),
                patch.object(app_paths, "LEGACY_PREFERENCES_PATH", legacy_preferences),
            ):
                result = app_paths.migrate_legacy_user_data()

            self.assertEqual(result["sessions"], 0)
            self.assertEqual(result["profiles"], 1)
            self.assertEqual(result["patterns"], 1)
            self.assertEqual(result["preferences"], 1)
            self.assertEqual(
                (destination.sessions / "one.json").read_text(encoding="utf-8"),
                "{\"new\": 1}",
            )


class RandomStateTests(unittest.TestCase):
    def test_json_round_trip_continues_the_exact_random_stream(self) -> None:
        generator = random.Random(4815162342)
        generator.random()
        encoded = encode_random_state(generator)
        serialized = json.loads(json.dumps(encoded))
        restored = random.Random()
        restored.setstate(decode_random_state(serialized))

        self.assertEqual(
            [generator.random() for _ in range(20)],
            [restored.random() for _ in range(20)],
        )

    def test_derived_streams_are_stable_and_independent(self) -> None:
        self.assertEqual(derive_seed(42, "1d"), derive_seed(42, "1d"))
        self.assertNotEqual(derive_seed(42, "1d"), derive_seed(42, "3d"))


class PreferenceMigrationTests(unittest.TestCase):
    def test_version_one_preferences_remain_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "preferences.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": PREFERENCES_SCHEMA,
                        "version": 1,
                        "favorite_rules": [30, 110],
                        "recent_experiments": [],
                    }
                ),
                encoding="utf-8",
            )

            preferences = UIPreferences.load(path, autosave=False)

            self.assertEqual(preferences.favorite_rules, {30, 110})


if __name__ == "__main__":
    unittest.main()
