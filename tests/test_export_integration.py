"""Application integration tests for contextual experiment exports."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import life
from session_storage import validate_session_document


class ExportIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_session = life.capture_session_document("Export Test")
        self.original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        life.export_manager.close()
        life.simulation_active = False

    def tearDown(self) -> None:
        life.export_manager.close()
        life.update_window_size(*self.original_size)
        life.restore_session_document(self.original_session)

    def configure_life_blinker(self) -> None:
        life.set_active_dimension("2d")
        life.set_simulation_mode("life")
        life.current_rule = "conway"
        life.grid = life.make_grid()
        life.trail_grid = life.make_grid()
        life.activity_grid = life.make_float_grid()
        life.grid[8][7:10] = [1, 1, 1]
        life.generation = 0
        life.two_d_timelines["life"].reset()
        life.analysis_registry.reset(life._analysis_observation_2d("life"))

    def test_1d_png_raster_contains_complete_space_time_diagram(self) -> None:
        life.set_active_dimension("1d")
        state = life.elementary_controller.state
        state.rule = 90
        state.seed = life.single_eca_seed(life.ECA_WIDTH)
        state.rows = [state.seed]
        state.generation = 0
        state.background = 0
        life.elementary_controller.reset_history()
        for _ in range(4):
            life.apply_generation()

        frame = life.capture_current_raster()

        self.assertEqual(frame.generation, 4)
        self.assertEqual(len(frame.rows), 5)
        self.assertEqual(frame.rows, tuple(tuple(row) for row in state.rows))

    def test_1d_comparison_export_places_both_diagrams_side_by_side(self) -> None:
        life.set_active_dimension("1d")
        state = life.elementary_controller.state
        state.rows = [(0, 1, 0), (1, 1, 1)]
        state.comparison_enabled = True
        state.comparison_rows = [(0, 1, 0), (1, 0, 1)]
        state.previous_row = (0, 1, 0)
        state.comparison_previous_row = (0, 1, 0)
        state.generation = 1

        frame = life.capture_current_raster()

        self.assertEqual(frame.rows[0], (0, 1, 0, 0, 0, 0, 0, 1, 0))
        self.assertEqual(frame.rows[1], (1, 1, 1, 0, 0, 0, 1, 0, 1))

    def test_2d_life_ages_are_normalized_for_visual_exports(self) -> None:
        self.configure_life_blinker()
        life.grid[8][8] = 19

        frame = life.capture_current_raster()

        self.assertEqual(frame.rows[8][7:10], (1, 1, 1))
        self.assertEqual(set(cell for row in frame.rows for cell in row), {0, 1})

    def test_langton_ant_is_visible_as_an_overlay_state(self) -> None:
        life.set_active_dimension("2d")
        life.set_simulation_mode("langtons_ant")
        life.ant_grid = life.make_ant_grid(life.ROWS, life.COLS)
        life.ant_state = life.centered_ant(life.ROWS, life.COLS)
        life.ant_generation = 0

        frame = life.capture_current_raster()

        self.assertEqual(
            frame.rows[life.ant_state.row][life.ant_state.col],
            2,
        )

    def test_timeline_capture_does_not_move_visible_cursor(self) -> None:
        self.configure_life_blinker()
        for _ in range(4):
            life.apply_generation()
        binding = life.two_d_timelines["life"]
        self.assertTrue(binding.seek(1))
        cursor_before = binding.timeline.cursor

        frames = life.capture_timeline_rasters()

        self.assertEqual(binding.timeline.cursor, cursor_before)
        self.assertEqual(frames[0].generation, 0)
        self.assertEqual(frames[-1].generation, 4)

    def test_x_opens_contextual_menu_pauses_and_fits_minimum_window(self) -> None:
        self.configure_life_blinker()
        life.update_window_size(760, 560)
        life.simulation_active = True

        life.handle_keydown(
            life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_x)
        )
        modal, cards = life.export_manager.geometry()

        self.assertTrue(life.export_manager.active)
        self.assertFalse(life.simulation_active)
        self.assertEqual(len(cards), 5)
        self.assertTrue(all(modal.contains(card) for _, card in cards))
        life.draw_scene()

    def test_shareable_json_remains_a_valid_reloadable_session(self) -> None:
        self.configure_life_blinker()
        life.apply_generation()

        document = life.capture_shareable_experiment_document()
        normalized = validate_session_document(document)
        metadata = document["experiment_export"]

        self.assertEqual(normalized["application"]["dimension"], "2d")
        self.assertEqual(metadata["mode"], "life")
        self.assertEqual(metadata["generation"], 1)
        self.assertEqual(metadata["timeline"]["frame_count"], 2)
        self.assertEqual(len(metadata["analysis"]["samples"]), 2)


if __name__ == "__main__":
    unittest.main()
