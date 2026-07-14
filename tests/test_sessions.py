import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import life
import session_storage


class ApplicationSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_session = life.capture_session_document("Original Test State")
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
        life.restore_session_document(self.original_session)
        self.profile_patch.stop()
        self.session_patch.stop()
        self.temporary_directory.cleanup()

    def configure_distinct_state(self) -> None:
        life.active_dimension = "1d"
        life.simulation_mode = "wireworld"
        life.current_theme = "neon"
        life.speed = 23
        life.show_grid = False
        life.show_heatmap = True
        life.show_age_numbers = True
        life.show_coordinates = True
        life.show_quadrants = True

        eca = life.elementary_controller.state
        eca.rule = 110
        eca.boundary = life.BOUNDARY_WRAP
        eca.background = 0
        eca.rule_change_reset = False
        eca.seed = (1, 0, 0)
        eca.rows = [(0, 1, 0), (1, 1, 0)]
        eca.generation = 37
        eca.cell_size = 9
        eca.view_offset_x = 41
        eca.view_offset_y = -73

        life.CELL_SIZE = 17
        life.view_offset_x = -91
        life.view_offset_y = 54
        life.current_rule = "highlife"
        life.grid[1][2] = 8
        life.trail_grid[1][2] = 5
        life.activity_grid[1][2] = 2.75
        life.generation = 18
        life.immigration_grid[2][3] = -4
        life.immigration_generation = 19
        life.active_species = life.SPECIES_B
        life.brain_grid[3][4] = life.DYING
        life.brain_generation = 20
        life.ant_grid[4][5] = life.ANT_BLACK
        life.ant_state = life.AntState(4, 5, 2, active=False)
        life.ant_generation = 21
        life.wireworld_grid[5][6] = life.ELECTRON_HEAD
        life.wireworld_generation = 22
        life.wireworld_brush = life.ELECTRON_TAIL
        life.cyclic_grid[6][7] = 6
        life.cyclic_generation = 23
        life.cyclic_brush = 7
        life.cyclic_threshold = 4

    def test_full_session_round_trip_restores_all_workspaces_and_ui(self) -> None:
        self.configure_distinct_state()
        document = life.capture_session_document("Round Trip")
        session_storage.save_session(document, "round_trip")

        life.active_dimension = "2d"
        life.simulation_mode = "life"
        life.current_theme = "classic"
        life.speed = 1
        life.grid[1][2] = 0
        life.elementary_controller.state.rule = 30
        life.CELL_SIZE = 5
        life.view_offset_x = 0
        life.view_offset_y = 0

        self.assertTrue(life.load_saved_session("round_trip"))

        self.assertEqual(life.active_dimension, "1d")
        self.assertEqual(life.simulation_mode, "wireworld")
        self.assertEqual(life.current_theme, "neon")
        self.assertEqual(life.speed, 23)
        self.assertFalse(life.show_grid)
        self.assertTrue(life.show_heatmap)
        self.assertEqual(life.current_rule, "highlife")
        self.assertEqual(life.grid[1][2], 8)
        self.assertEqual(life.trail_grid[1][2], 5)
        self.assertEqual(life.activity_grid[1][2], 2.75)
        self.assertEqual(life.generation, 18)
        self.assertEqual(life.immigration_grid[2][3], -4)
        self.assertEqual(life.brain_grid[3][4], life.DYING)
        self.assertEqual(life.ant_state, life.AntState(4, 5, 2, active=False))
        self.assertEqual(life.wireworld_grid[5][6], life.ELECTRON_HEAD)
        self.assertEqual(life.cyclic_grid[6][7], 6)
        self.assertEqual(life.cyclic_threshold, 4)
        self.assertEqual(life.CELL_SIZE, 17)
        self.assertEqual((life.view_offset_x, life.view_offset_y), (-91, 54))
        eca = life.elementary_controller.state
        self.assertEqual(eca.rule, 110)
        self.assertEqual(eca.boundary, life.BOUNDARY_WRAP)
        self.assertEqual(eca.seed, (1, 0, 0))
        self.assertEqual(eca.rows, [(0, 1, 0), (1, 1, 0)])
        self.assertEqual(eca.generation, 37)
        self.assertEqual(eca.cell_size, 9)
        self.assertEqual((eca.view_offset_x, eca.view_offset_y), (41, -73))
        self.assertEqual(
            eca.generation,
            life.elementary_controller.history_status().generation,
        )
        self.assertEqual(life.elementary_controller.history_status().frame_count, 1)
        self.assertTrue(
            all(
                binding.status().frame_count == 1
                for binding in life.two_d_timelines.values()
            )
        )
        self.assertFalse(life.simulation_active)

    def test_invalid_session_does_not_partially_mutate_live_state(self) -> None:
        document = life.capture_session_document("Invalid")
        document["application"]["theme"] = "missing-theme"
        original_dimension = life.active_dimension
        original_cell = life.grid[0][0]

        with self.assertRaises(session_storage.DocumentValidationError):
            life.restore_session_document(document)

        self.assertEqual(life.active_dimension, original_dimension)
        self.assertEqual(life.grid[0][0], original_cell)

    def test_quick_save_and_load_keyboard_shortcuts(self) -> None:
        life.grid[0][0] = 9
        save_event = life.pygame.event.Event(
            life.pygame.KEYDOWN,
            key=life.pygame.K_s,
            mod=life.pygame.KMOD_CTRL,
        )
        load_event = life.pygame.event.Event(
            life.pygame.KEYDOWN,
            key=life.pygame.K_o,
            mod=life.pygame.KMOD_CTRL,
        )

        life.handle_keydown(save_event)
        life.grid[0][0] = 0
        life.handle_keydown(load_event)

        self.assertEqual(life.grid[0][0], 9)
        self.assertTrue((self.session_directory / "last_session.json").exists())

    def test_elementary_profile_restarts_from_latest_row(self) -> None:
        life.set_active_dimension("1d")
        eca = life.elementary_controller.state
        eca.rule = 90
        eca.boundary = life.BOUNDARY_FIXED
        eca.background = 0
        eca.rule_change_reset = False
        eca.rows = [(0, 1, 0), (1, 0, 1)]
        eca.generation = 12
        profile = life.capture_experiment_profile("Rule 90 Pair")

        eca.rule = 30
        eca.rows = [life.single_eca_seed(life.ECA_WIDTH)]
        eca.generation = 0
        life.restore_experiment_profile(profile)

        self.assertEqual(eca.rule, 90)
        self.assertEqual(eca.boundary, life.BOUNDARY_FIXED)
        self.assertEqual(eca.rows, [(1, 0, 1)])
        self.assertEqual(eca.generation, 0)
        self.assertFalse(eca.rule_change_reset)

    def test_session_manager_exposes_profiles_only_in_1d(self) -> None:
        life.set_active_dimension("2d")
        life.activate_session_menu()
        two_d_keys = {entry["key"] for entry in life.session_menu_entries()}
        self.assertNotIn("save_profile", two_d_keys)

        life.session_manager.close()
        life.set_active_dimension("1d")
        life.activate_session_menu()
        one_d_keys = {entry["key"] for entry in life.session_menu_entries()}
        self.assertIn("save_profile", one_d_keys)
        self.assertIn("browse_profiles", one_d_keys)

    def test_session_manager_draws_inside_the_minimum_window(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(760, 560)
            life.activate_session_menu()
            modal, cards, _ = life.session_menu_geometry()

            self.assertTrue(all(modal.contains(card) for _, card in cards))
            life.draw_scene()
        finally:
            life.session_manager.close()
            life.update_window_size(*original_size)


if __name__ == "__main__":
    unittest.main()
