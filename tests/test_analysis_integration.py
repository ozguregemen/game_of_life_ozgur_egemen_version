"""Application integration tests for live scientific analysis and its panel."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import life


class ScientificAnalysisIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_session = life.capture_session_document("Analysis Test")
        self.original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        life.analysis_panel.close()

    def tearDown(self) -> None:
        life.analysis_panel.close()
        life.update_window_size(*self.original_size)
        life.restore_session_document(self.original_session)

    def configure_life_blinker(self) -> None:
        life.set_simulation_mode("life")
        life.current_rule = "conway"
        life.grid = life.make_grid()
        life.trail_grid = life.make_grid()
        life.activity_grid = life.make_float_grid()
        life.grid[8][7:10] = [1, 1, 1]
        life.generation = 0
        life.two_d_timelines["life"].reset()
        life.analysis_registry.reset(life._analysis_observation_2d("life"))

    def test_life_ages_are_binary_and_blinker_period_is_detected(self) -> None:
        self.configure_life_blinker()
        life.grid[8][8] = 9
        life.analysis_registry.reset(life._analysis_observation_2d("life"))

        self.assertTrue(life.apply_generation())
        self.assertTrue(life.apply_generation())

        series = life.analysis_registry.get("2d:life")
        self.assertEqual([sample.population for sample in series.samples], [3, 3, 3])
        self.assertEqual(series.period, 2)
        self.assertEqual(series.stabilization_generation, 0)
        self.assertTrue(all(0.0 <= sample.entropy <= 1.0 for sample in series.samples))

    def test_immigration_ages_count_as_two_species_not_many_states(self) -> None:
        life.set_simulation_mode("immigration")
        life.immigration_grid = life.make_immigration_grid(life.ROWS, life.COLS)
        life.immigration_grid[2][2] = 7
        life.immigration_grid[2][3] = -11
        life.immigration_generation = 0

        series = life.analysis_registry.reset(
            life._analysis_observation_2d("immigration")
        )

        self.assertEqual(series.latest.population, 2)
        self.assertGreater(series.latest.entropy, 0.0)

    def test_elementary_rule_four_detects_a_stable_row(self) -> None:
        life.set_active_dimension("1d")
        state = life.elementary_controller.state
        state.rule = 4
        state.boundary = life.BOUNDARY_INFINITE
        state.background = 0
        state.seed = life.single_eca_seed(life.ECA_WIDTH)
        state.rows = [state.seed]
        state.generation = 0
        life.elementary_controller.reset_history()

        self.assertTrue(life.apply_generation())

        series = life.analysis_registry.get("1d:elementary")
        self.assertEqual(series.period, 1)
        self.assertEqual(series.stabilization_generation, 0)
        self.assertEqual(series.latest.change_rate, 0.0)

    def test_manual_intervention_at_same_generation_starts_a_new_run(self) -> None:
        self.configure_life_blinker()
        self.assertTrue(life.apply_generation())
        self.assertEqual(
            life.analysis_registry.get("2d:life").summary.sample_count,
            2,
        )

        life.drawing_value = 1
        life.drawing_history_pending = True
        life.draw_cell(2, 2)
        life.two_dimensional_controller.sync_history()

        series = life.analysis_registry.get("2d:life")
        self.assertEqual(series.summary.sample_count, 1)
        self.assertEqual(series.latest.generation, 1)
        self.assertIsNone(series.period)

    def test_analysis_panel_opens_with_i_and_fits_minimum_window(self) -> None:
        self.configure_life_blinker()
        life.update_window_size(760, 560)

        life.handle_keydown(
            life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_i)
        )
        modal, live_tab, comparison_tab, close_button = life.analysis_panel.geometry()

        self.assertTrue(life.analysis_panel.active)
        self.assertTrue(modal.contains(live_tab))
        self.assertTrue(modal.contains(comparison_tab))
        self.assertTrue(modal.contains(close_button))
        life.draw_scene()

    def test_comparison_tab_requests_background_rule_experiment(self) -> None:
        self.configure_life_blinker()
        life.analysis_panel.active = True
        _, _, comparison_tab, _ = life.analysis_panel.geometry()

        with patch.object(life.analysis_panel, "request_comparison") as request:
            consumed = life.analysis_panel.handle_event(
                life.pygame.event.Event(
                    life.pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=comparison_tab.center,
                )
            )

        self.assertTrue(consumed)
        self.assertEqual(life.analysis_panel.tab, "comparison")
        request.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
