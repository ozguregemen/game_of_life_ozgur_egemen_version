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
from one_dimensional_ca import (
    FAMILY_TOTALISTIC,
    SEED_WIDTH_COMPACT,
    default_rule_spec,
)


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

    def test_legacy_documents_default_to_compact_1d_seed_width(self) -> None:
        session = self.valid_session("Legacy Width")
        session["workspaces"]["1d"].pop("seed_width_mode", None)
        session["workspaces"]["1d"].pop("row_backgrounds", None)
        session["workspaces"]["1d"]["comparison"]["background"] = 1
        session["workspaces"]["1d"]["comparison"].pop(
            "row_backgrounds",
            None,
        )
        normalized_session = session_storage.validate_session_document(session)

        profile = life.capture_experiment_profile("Legacy Profile")
        profile["experiment"].pop("seed_width_mode", None)
        normalized_profile = session_storage.validate_profile_document(profile)

        self.assertEqual(
            normalized_session["workspaces"]["1d"]["seed_width_mode"],
            SEED_WIDTH_COMPACT,
        )
        self.assertEqual(
            len(normalized_session["workspaces"]["1d"]["row_backgrounds"]),
            len(normalized_session["workspaces"]["1d"]["rows"]),
        )
        self.assertEqual(
            normalized_session["workspaces"]["1d"]["comparison"][
                "row_backgrounds"
            ][-1],
            1,
        )
        self.assertEqual(
            normalized_profile["experiment"]["seed_width_mode"],
            SEED_WIDTH_COMPACT,
        )

    def test_generalized_profile_preserves_family_states_and_comparison(self) -> None:
        original = life.capture_session_document("Profile Restore")
        try:
            state = life.elementary_controller.state
            spec = default_rule_spec(FAMILY_TOTALISTIC, states=3, radius=2)
            state.family = spec.family
            state.rule = spec.code
            state.states = spec.states
            state.radius = spec.radius
            state.rows = [(0, 1, 2, 1, 0)]
            state.seed = state.rows[-1]
            state.previous_row = (0, 0, 0, 0, 0)
            state.comparison_enabled = True
            state.comparison_rule = max(0, spec.code - 1)
            document = life.capture_experiment_profile("Totalistic Pair")

            path = session_storage.save_profile(document)
            loaded = session_storage.load_profile(path.stem)

            self.assertEqual(loaded["experiment"]["rule_spec"], spec.as_dict())
            self.assertEqual(loaded["experiment"]["seed"], [0, 1, 2, 1, 0])
            self.assertTrue(loaded["experiment"]["comparison"]["enabled"])
        finally:
            life.restore_session_document(original)

    def test_unsupported_version_is_rejected(self) -> None:
        document = deepcopy(self.valid_session())
        document["version"] = 999

        with self.assertRaisesRegex(
            session_storage.DocumentValidationError,
            "Unsupported session version",
        ):
            session_storage.validate_session_document(document)

    def test_legacy_session_without_3d_workspace_gets_an_empty_volume(self) -> None:
        document = self.valid_session("Legacy 2D")
        document["workspaces"].pop("3d")

        normalized = session_storage.validate_session_document(document)

        spatial = normalized["workspaces"]["3d"]
        self.assertEqual(spatial["shape"], [48, 48, 48])
        self.assertEqual(spatial["generation"], 0)
        self.assertEqual(spatial["rule"], "bays_5766")

    def test_invalid_3d_cell_is_rejected_before_storage(self) -> None:
        document = self.valid_session("Invalid 3D")
        document["workspaces"]["3d"]["cells"][0][0][0] = 2

        with self.assertRaisesRegex(
            session_storage.DocumentValidationError,
            "workspaces.3d.cells",
        ):
            session_storage.validate_session_document(document)

    def test_generations_session_accepts_refractory_states_and_rejects_overflow(self) -> None:
        document = self.valid_session("Generations 3D")
        spatial = document["workspaces"]["3d"]
        spatial["mode"] = "generations"
        spatial["rule"] = "generations_445"
        spatial["state_count"] = 5
        spatial["cells"][0][0][0] = 4

        normalized = session_storage.validate_session_document(document)

        self.assertEqual(normalized["workspaces"]["3d"]["cells"][0][0][0], 4)
        spatial["cells"][0][0][0] = 5
        with self.assertRaisesRegex(
            session_storage.DocumentValidationError,
            "workspaces.3d.cells",
        ):
            session_storage.validate_session_document(document)

    def test_legacy_3d_slice_camera_is_upgraded_to_orbit_camera(self) -> None:
        document = self.valid_session("Legacy 3D Camera")
        document["workspaces"]["3d"]["camera"] = {
            "cell_size": 12,
            "offset": [15, -8],
        }

        normalized = session_storage.validate_session_document(document)
        camera = normalized["workspaces"]["3d"]["camera"]

        self.assertEqual(camera["target"], [0.0, 0.0, 0.0])
        self.assertGreater(camera["distance"], 8.0)
        self.assertIn("yaw", camera)
        self.assertIn("pitch", camera)

    def test_invalid_3d_orbit_camera_is_rejected(self) -> None:
        document = self.valid_session("Invalid 3D Camera")
        document["workspaces"]["3d"]["camera"]["pitch"] = 10.0

        with self.assertRaisesRegex(
            session_storage.DocumentValidationError,
            "pitch",
        ):
            session_storage.validate_session_document(document)

    def test_legacy_3d_session_gets_default_volume_view(self) -> None:
        document = self.valid_session("Legacy 3D View")
        document["workspaces"]["3d"].pop("view")

        normalized = session_storage.validate_session_document(document)

        self.assertEqual(
            normalized["workspaces"]["3d"]["view"],
            {"mode": "all", "keep_lower": True, "opacity": 1.0},
        )

    def test_invalid_3d_view_opacity_is_rejected(self) -> None:
        document = self.valid_session("Invalid 3D Opacity")
        document["workspaces"]["3d"]["view"]["opacity"] = 1.5

        with self.assertRaisesRegex(
            session_storage.DocumentValidationError,
            "opacity",
        ):
            session_storage.validate_session_document(document)


if __name__ == "__main__":
    unittest.main()
