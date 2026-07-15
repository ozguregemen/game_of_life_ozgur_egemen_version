import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import life
from one_dimensional_ca import (
    SEED_WIDTH_COMPACT,
    SEED_WIDTH_VIEWPORT,
    SEED_WIDTH_WIDE,
)
from workspaces.elementary_1d import (
    ECA_DIAGRAM_CELL_BUDGET,
    ECA_MAX_DIAGRAM_WIDTH,
)


def reset_mode_timeline(mode: str) -> None:
    life.two_d_timelines[mode].reset()


def timeline_change_count(mode: str) -> int:
    binding = life.two_d_timelines[mode]
    binding.sync()
    return binding.status().frame_count - 1


class PatternPlacementTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "life"
        life.grid = life.make_grid()
        life.trail_grid = life.make_grid()
        life.activity_grid = life.make_float_grid()
        reset_mode_timeline("life")
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

    def test_out_of_bounds_pattern_is_not_partially_placed(self) -> None:
        life.place_selected_pattern(life.ROWS - 1, life.COLS - 1)
        self.assertFalse(any(cell for row in life.grid for cell in row))
        self.assertEqual(timeline_change_count("life"), 0)

    def test_noop_pattern_does_not_add_history(self) -> None:
        for row in (2, 3):
            for col in (2, 3):
                life.grid[row][col] = 1
        reset_mode_timeline("life")
        life.place_selected_pattern(2, 2)
        self.assertEqual(timeline_change_count("life"), 0)

    def test_changed_pattern_adds_one_history_entry(self) -> None:
        life.place_selected_pattern(2, 2)
        self.assertEqual(timeline_change_count("life"), 1)


class ApplicationSmokeTests(unittest.TestCase):
    def run_smoke_test(self, mode: str, dimension: str = "2d") -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "SDL_VIDEODRIVER": "dummy",
                "SDL_AUDIODRIVER": "dummy",
                "LIFE_SMOKE_TEST": "1",
                "LIFE_START_MODE": mode,
                "LIFE_START_DIMENSION": dimension,
            }
        )
        result = subprocess.run(
            [sys.executable, "life.py"],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("life")

    def test_immigration_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("immigration")

    def test_brians_brain_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("brians_brain")

    def test_langtons_ant_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("langtons_ant")

    def test_wireworld_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("wireworld")

    def test_cyclic_automaton_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("cyclic_automaton")

    def test_elementary_ca_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("life", "1d")


class DimensionUITests(unittest.TestCase):
    def setUp(self) -> None:
        life.set_simulation_mode("life")
        self.eca = life.ElementaryWorkspaceState()
        life.elementary_controller.state = self.eca
        life.elementary_state = self.eca
        life.elementary_controller.reset_history()
        life.dimension_menu_active = False
        life.mode_menu_active = False
        life.pattern_menu_active = False

    def tearDown(self) -> None:
        life.dimension_menu_active = False
        self.eca.rule_menu_active = False
        self.eca.rule_change_reset = True
        life.rendered_grid_cache.clear()
        life.mode_stats_cache.clear()
        life.set_simulation_mode("life")

    @staticmethod
    def menu_labels() -> list[str]:
        return [data["button"].text for data in life.main_menu.buttons]

    def test_d_opens_dimension_chooser_without_switching(self) -> None:
        life.handle_keydown(
            life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_d)
        )
        self.assertTrue(life.dimension_menu_active)
        self.assertEqual(life.active_dimension, "2d")

    def test_number_key_selects_1d_workspace(self) -> None:
        life.activate_dimension_menu()
        event = life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_1)
        self.assertTrue(life.handle_dimension_menu_event(event))
        self.assertEqual(life.active_dimension, "1d")
        self.assertFalse(life.dimension_menu_active)

    def test_3d_card_is_visible_but_cannot_be_activated(self) -> None:
        life.activate_dimension_menu()
        event = life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_3)
        self.assertTrue(life.handle_dimension_menu_event(event))
        self.assertEqual(life.active_dimension, "2d")
        self.assertFalse(life.dimension_menu_active)
        self.assertIn("planned", life.status_message.lower())

    def test_dimension_cards_fit_without_overlap(self) -> None:
        modal, cards = life.dimension_menu_geometry()
        self.assertEqual(len(cards), len(life.DIMENSION_DEFINITIONS))
        for _, card in cards:
            self.assertTrue(modal.contains(card))
        for index, (_, card) in enumerate(cards):
            self.assertFalse(
                any(card.colliderect(other) for _, other in cards[index + 1 :])
            )

    def test_1d_sidebar_contains_only_relevant_controls(self) -> None:
        life.set_active_dimension("1d")
        labels = self.menu_labels()
        self.assertIn("Select Dimension (D)", labels)
        self.assertIn("Browse Rules 0–255 (E)", labels)
        self.assertTrue(any(label.startswith("Next Featured:") for label in labels))
        self.assertTrue(any(label.startswith("Previous Rule:") for label in labels))
        self.assertTrue(any(label.startswith("Next Rule:") for label in labels))
        self.assertIn("Rule Change: Canonical Reset", labels)
        self.assertTrue(any(label.startswith("Boundary:") for label in labels))
        self.assertTrue(any(label.startswith("Seed Width:") for label in labels))
        self.assertNotIn("Select Mode (M)", labels)
        self.assertNotIn("Show Patterns", labels)

    def test_1d_seed_width_presets_are_odd_bounded_and_undoable(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(1920, 1080)
            life.set_active_dimension("1d")
            self.eca.seed_width_mode = SEED_WIDTH_COMPACT
            life.elementary_controller.reset_history()
            widths = life.elementary_controller.seed_widths()

            self.assertEqual(widths[SEED_WIDTH_COMPACT], life.ECA_WIDTH)
            self.assertLess(
                widths[SEED_WIDTH_COMPACT],
                widths[SEED_WIDTH_VIEWPORT],
            )
            self.assertLess(widths[SEED_WIDTH_VIEWPORT], widths[SEED_WIDTH_WIDE])
            self.assertTrue(all(width % 2 == 1 for width in widths.values()))

            life.elementary_controller.cycle_seed_width()
            self.assertEqual(self.eca.seed_width_mode, SEED_WIDTH_VIEWPORT)
            self.assertEqual(len(self.eca.rows[-1]), widths[SEED_WIDTH_VIEWPORT])

            life.elementary_controller.step_back()
            self.assertEqual(self.eca.seed_width_mode, SEED_WIDTH_COMPACT)
            self.assertEqual(len(self.eca.rows[-1]), life.ECA_WIDTH)
            expected_x = (
                life.elementary_controller.diagram_viewport().width
                - len(self.eca.rows[-1]) * self.eca.cell_size
            ) // 2
            self.assertEqual(self.eca.view_offset_x, expected_x)
        finally:
            life.update_window_size(*original_size)

    def test_wide_1d_diagram_respects_cell_budget_and_uses_rolling_delta(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(1920, 1080)
            life.set_active_dimension("1d")
            self.eca.seed_width_mode = SEED_WIDTH_WIDE
            self.eca.rule = 30
            life.elementary_controller.use_single_seed()
            life.elementary_controller.reset_history()
            row_limit = life.elementary_controller.diagram_row_limit()

            for _ in range(row_limit + 1):
                life.elementary_controller.advance()

            self.assertLessEqual(len(self.eca.rows), row_limit)
            self.assertLessEqual(
                len(self.eca.rows) * len(self.eca.rows[-1]),
                ECA_DIAGRAM_CELL_BUDGET,
            )
            latest_frame = life.elementary_controller.timeline.timeline.frames[-1]
            self.assertIsNotNone(latest_frame.delta)
            self.assertTrue(
                any(
                    operation.kind == "roll" and operation.path == ("rows",)
                    for operation in latest_frame.delta or ()
                )
            )
        finally:
            life.update_window_size(*original_size)

    def test_1d_retention_budget_and_growth_safety_width_are_hard_bounds(self) -> None:
        self.assertLessEqual(
            life.elementary_controller.diagram_row_limit(ECA_MAX_DIAGRAM_WIDTH)
            * ECA_MAX_DIAGRAM_WIDTH,
            ECA_DIAGRAM_CELL_BUDGET,
        )
        life.set_active_dimension("1d")
        edge_row = (1,) + (0,) * (ECA_MAX_DIAGRAM_WIDTH - 1)
        self.eca.rule = 30
        self.eca.boundary = life.BOUNDARY_INFINITE
        self.eca.rows = [edge_row]
        self.eca.row_backgrounds = [0]
        self.eca.previous_row = (0,) * ECA_MAX_DIAGRAM_WIDTH
        self.eca.comparison_rows = [edge_row]
        self.eca.comparison_row_backgrounds = [0]
        self.eca.comparison_previous_row = self.eca.previous_row

        self.assertFalse(life.elementary_controller.advance())
        self.assertEqual(self.eca.generation, 0)
        self.assertEqual(len(self.eca.rows[-1]), ECA_MAX_DIAGRAM_WIDTH)
        self.assertIn("safety width", life.status_message)

    def test_selected_1d_seed_width_survives_canonical_rule_reset(self) -> None:
        life.set_active_dimension("1d")
        self.eca.seed_width_mode = SEED_WIDTH_VIEWPORT
        expected_width = life.elementary_controller.preferred_seed_width()
        life.elementary_controller.use_single_seed()

        life.adjust_eca_rule(1)

        self.assertEqual(len(self.eca.seed), expected_width)
        self.assertEqual(len(self.eca.rows[-1]), expected_width)

    def test_viewport_seed_width_fits_small_window_even_at_large_zoom(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(760, 560)
            life.set_active_dimension("1d")
            self.eca.cell_size = 16
            self.eca.comparison_enabled = False
            widths = life.elementary_controller.seed_widths()
            visible_cells = (
                life.elementary_controller.diagram_panes()[0].width
                // self.eca.cell_size
            )

            self.assertLess(widths[SEED_WIDTH_VIEWPORT], widths[SEED_WIDTH_COMPACT])
            self.assertLessEqual(widths[SEED_WIDTH_VIEWPORT], visible_cells)
            self.eca.seed_width_mode = SEED_WIDTH_VIEWPORT
            life.elementary_controller.use_single_seed()
            self.assertLessEqual(
                life.elementary_controller.editor_rect().width,
                life.eca_diagram_viewport().width,
            )
        finally:
            life.update_window_size(*original_size)

    def test_1d_virtual_grid_continues_outside_finite_row(self) -> None:
        original_theme = life.current_theme
        original_grid = life.show_grid
        try:
            life.set_active_dimension("1d")
            life.current_theme = "classic"
            life.show_grid = True
            self.eca.cell_size = 6
            life.elementary_controller.center_view()
            life.screen.fill(life.THEMES["classic"]["background"])

            life.elementary_renderer.draw_base()

            origin_x, origin_y = life.elementary_controller.grid_origin()
            sample = (origin_x - self.eca.cell_size * 2, origin_y + 2)
            sample_below = (origin_x + 2, origin_y + self.eca.cell_size * 3)
            self.assertGreaterEqual(sample[0], life.eca_diagram_viewport().left)
            self.assertEqual(
                tuple(life.screen.get_at(sample)[:3]),
                life.THEMES["classic"]["grid"],
            )
            self.assertEqual(
                tuple(life.screen.get_at(sample_below)[:3]),
                life.THEMES["classic"]["grid"],
            )
        finally:
            life.current_theme = original_theme
            life.show_grid = original_grid

    def test_1d_virtual_cells_render_their_historical_infinite_background(self) -> None:
        original_theme = life.current_theme
        original_grid = life.show_grid
        try:
            life.set_active_dimension("1d")
            life.current_theme = "classic"
            life.show_grid = False
            self.eca.cell_size = 6
            self.eca.boundary = life.BOUNDARY_INFINITE
            self.eca.rows = [(0, 1, 0), (0, 0, 1, 0, 0)]
            self.eca.row_backgrounds = [1, 0]
            self.eca.background = 0
            self.eca.previous_row = (0, 0, 0, 0, 0)
            self.eca.comparison_rows = list(self.eca.rows)
            self.eca.comparison_row_backgrounds = list(self.eca.row_backgrounds)
            self.eca.comparison_previous_row = self.eca.previous_row
            life.elementary_controller.center_view()
            life.screen.fill(life.THEMES["classic"]["background"])

            life.elementary_renderer.draw_base()

            origin_x, origin_y = life.elementary_controller.grid_origin()
            self.assertEqual(
                tuple(life.screen.get_at((origin_x + 1, origin_y + 1))[:3]),
                life.THEMES["classic"]["cell"],
            )
        finally:
            life.current_theme = original_theme
            life.show_grid = original_grid

    def test_legacy_comparison_restore_uses_its_own_outside_background(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rows = [(0, 1, 0), (1, 0, 1)]
        self.eca.row_backgrounds = [0, 0]
        self.eca.previous_row = (0, 1, 0)
        self.eca.comparison_enabled = True
        self.eca.comparison_rows = [(0, 1, 0), (1, 1, 1)]
        self.eca.comparison_row_backgrounds = [0, 1]
        self.eca.comparison_previous_row = (0, 1, 0)
        self.eca.comparison_background = 1
        snapshot = life.elementary_controller._timeline_snapshot()
        snapshot.pop("row_backgrounds")
        snapshot["comparison"].pop("row_backgrounds")

        life.elementary_controller._restore_simulation_snapshot(snapshot)

        self.assertEqual(self.eca.row_backgrounds, [0, 0])
        self.assertEqual(self.eca.comparison_row_backgrounds, [0, 1])

    def test_switching_dimensions_preserves_2d_grid(self) -> None:
        life.grid = life.make_grid()
        life.grid[4][5] = 1
        life.set_active_dimension("1d")
        life.set_active_dimension("2d")
        self.assertEqual(life.grid[4][5], 1)

    def test_m_does_not_open_2d_mode_chooser_from_1d(self) -> None:
        life.set_active_dimension("1d")
        life.activate_mode_menu()
        self.assertFalse(life.mode_menu_active)
        self.assertIn("2D workspace", life.status_message)

    def test_elementary_generation_dispatch_and_step_back(self) -> None:
        life.set_active_dimension("1d")
        seed = self.eca.rows[-1]
        self.assertTrue(life.apply_generation())
        self.assertEqual(self.eca.generation, 1)
        self.assertNotEqual(self.eca.rows[-1], seed)
        self.assertEqual(life.elementary_controller.history_status().frame_count, 2)

        life.step_back()
        self.assertEqual(self.eca.generation, 0)
        self.assertEqual(self.eca.rows, [seed])

        life.step_forward()
        self.assertEqual(self.eca.generation, 1)

    def test_rule_4_keeps_recording_identical_rows_like_reference_diagram(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rule = 4
        seed = life.single_eca_seed(life.ECA_WIDTH)
        self.eca.rows = [seed]

        for _ in range(4):
            self.assertTrue(life.apply_generation())

        self.assertEqual(self.eca.generation, 4)
        self.assertEqual(self.eca.rows, [seed] * 5)

    def test_adjacent_rule_buttons_wrap_and_use_canonical_defaults(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rule = 0
        self.eca.rows = [tuple(1 for _ in range(life.ECA_WIDTH))]
        self.eca.boundary = life.BOUNDARY_WRAP
        self.eca.background = 1

        life.adjust_eca_rule(-1)

        self.assertEqual(self.eca.rule, 255)
        self.assertEqual(self.eca.rows, [life.single_eca_seed(life.ECA_WIDTH)])
        self.assertEqual(self.eca.boundary, life.BOUNDARY_INFINITE)
        self.assertEqual(self.eca.background, 0)

        life.adjust_eca_rule(1)
        self.assertEqual(self.eca.rule, 0)

    def test_sidebar_previous_and_next_rule_buttons_execute_and_relabel(self) -> None:
        life.set_active_dimension("1d")
        next_button = next(
            data["button"]
            for data in life.main_menu.buttons
            if data["button"].text == "Next Rule: 31"
        )
        self.assertTrue(
            life.main_menu.handle_event(
                life.pygame.event.Event(
                    life.pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=next_button.rect.center,
                )
            )
        )
        self.assertEqual(self.eca.rule, 31)
        self.assertIn("Previous Rule: 30", self.menu_labels())
        self.assertIn("Next Rule: 32", self.menu_labels())

        previous_button = next(
            data["button"]
            for data in life.main_menu.buttons
            if data["button"].text == "Previous Rule: 30"
        )
        life.main_menu.handle_event(
            life.pygame.event.Event(
                life.pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=previous_button.rect.center,
            )
        )
        self.assertEqual(self.eca.rule, 30)

    def test_rule_change_can_explicitly_keep_current_row(self) -> None:
        life.set_active_dimension("1d")
        current = tuple(index % 2 for index in range(life.ECA_WIDTH))
        self.eca.rows = [current]
        self.eca.boundary = life.BOUNDARY_WRAP
        life.toggle_eca_rule_change_reset()

        life.adjust_eca_rule(1)

        self.assertEqual(self.eca.rule, 31)
        self.assertEqual(self.eca.rows, [current])
        self.assertEqual(self.eca.boundary, life.BOUNDARY_WRAP)

    def test_boundary_cycles_through_reference_and_experimental_modes(self) -> None:
        life.set_active_dimension("1d")
        self.assertEqual(self.eca.boundary, life.BOUNDARY_INFINITE)
        life.toggle_eca_boundary()
        self.assertEqual(self.eca.boundary, life.BOUNDARY_FIXED)
        life.toggle_eca_boundary()
        self.assertEqual(self.eca.boundary, life.BOUNDARY_WRAP)
        life.toggle_eca_boundary()
        self.assertEqual(self.eca.boundary, life.BOUNDARY_INFINITE)

    def test_rule_catalog_contains_all_rules_and_selects_a_card(self) -> None:
        life.set_active_dimension("1d")
        life.activate_eca_rule_menu()
        modal, cards = life.eca_rule_menu_geometry()
        self.assertEqual([rule for rule, _ in cards], list(range(256)))
        self.assertTrue(all(modal.contains(card) for _, card in cards))

        rule_110_card = dict(cards)[110]
        event = life.pygame.event.Event(
            life.pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=rule_110_card.center,
        )
        self.assertTrue(life.handle_eca_rule_menu_event(event))
        self.assertEqual(self.eca.rule, 110)
        self.assertFalse(self.eca.rule_menu_active)

    def test_rule_catalog_fits_the_minimum_window(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(760, 560)
            modal, cards = life.eca_rule_menu_geometry()
            self.assertTrue(all(modal.contains(card) for _, card in cards))
            self.assertTrue(all(card.width > 0 and card.height > 0 for _, card in cards))
        finally:
            life.update_window_size(*original_size)

    def test_rule_catalog_accepts_a_typed_rule_number(self) -> None:
        life.set_active_dimension("1d")
        life.activate_eca_rule_menu()
        for key in (life.pygame.K_1, life.pygame.K_8, life.pygame.K_4):
            life.handle_eca_rule_menu_event(
                life.pygame.event.Event(life.pygame.KEYDOWN, key=key)
            )
        life.handle_eca_rule_menu_event(
            life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_RETURN)
        )
        self.assertEqual(self.eca.rule, 184)
        self.assertFalse(self.eca.rule_menu_active)

    def test_infinite_background_state_is_restored_by_step_back(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rule = 1
        life.elementary_controller.reset_history()
        self.assertTrue(life.apply_generation())
        self.assertEqual(self.eca.background, 1)
        life.step_back()
        self.assertEqual(self.eca.background, 0)

    def test_infinite_workspace_expands_before_activity_is_clipped(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rule = 254
        for _ in range(life.ECA_WIDTH // 2 + 2):
            life.apply_generation()

        self.assertGreater(len(self.eca.rows[-1]), life.ECA_WIDTH)
        self.assertEqual(len(self.eca.rows[-1]) % 2, 1)
        life.draw_active_grid()

    def test_one_eca_brush_stroke_creates_one_undo_snapshot(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rows = [tuple(0 for _ in range(life.ECA_WIDTH))]
        life.elementary_controller.reset_history()
        life.drawing_value = 1
        life.drawing_history_pending = True
        life.draw_eca_cell(4)
        life.draw_eca_cell(5)
        life.elementary_controller.sync_history()
        self.assertEqual(self.eca.rows[-1][4:6], (1, 1))
        self.assertEqual(life.elementary_controller.history_status().frame_count, 2)

    def test_elementary_render_reuses_cached_viewport(self) -> None:
        life.set_active_dimension("1d")
        life.rendered_grid_cache.clear()
        life.reset_render_cache_metrics()
        life.invalidate_render_cache(life.ECA_RENDER_KEY)
        life.draw_active_grid()
        life.draw_active_grid()
        self.assertEqual(life.render_cache_misses, 1)
        self.assertEqual(life.render_cache_hits, 1)

    def test_1d_context_menu_fits_minimum_window_height(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(760, 560)
            life.set_active_dimension("1d")
            self.assertTrue(
                all(
                    data["button"].rect.bottom <= life.main_menu.rect.bottom
                    for data in life.main_menu.buttons
                )
            )
        finally:
            life.update_window_size(*original_size)


class ContextualModeUITests(unittest.TestCase):
    def setUp(self) -> None:
        life.mode_menu_active = False
        life.pattern_menu_active = False
        life.set_simulation_mode("life")

    def tearDown(self) -> None:
        life.mode_menu_active = False
        life.set_simulation_mode("life")

    @staticmethod
    def menu_labels() -> list[str]:
        return [data["button"].text for data in life.main_menu.buttons]

    def test_m_opens_chooser_without_immediately_changing_mode(self) -> None:
        life.handle_keydown(life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_m))

        self.assertTrue(life.mode_menu_active)
        self.assertEqual(life.simulation_mode, "life")

    def test_number_key_selects_mode_from_chooser(self) -> None:
        life.activate_mode_menu()
        event = life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_5)

        self.assertTrue(life.handle_mode_menu_event(event))

        self.assertEqual(life.simulation_mode, "wireworld")
        self.assertFalse(life.mode_menu_active)

    def test_six_selects_cyclic_mode_from_chooser(self) -> None:
        life.activate_mode_menu()
        event = life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_6)

        self.assertTrue(life.handle_mode_menu_event(event))

        self.assertEqual(life.simulation_mode, "cyclic_automaton")

    def test_card_click_selects_mode_from_chooser(self) -> None:
        life.activate_mode_menu()
        _, cards = life.mode_menu_geometry()
        brians_brain_card = dict(cards)["brians_brain"]
        event = life.pygame.event.Event(
            life.pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=brians_brain_card.center,
        )

        self.assertTrue(life.handle_mode_menu_event(event))
        self.assertEqual(life.simulation_mode, "brians_brain")
        self.assertFalse(life.mode_menu_active)

    def test_context_menu_only_shows_relevant_mode_actions(self) -> None:
        life.set_simulation_mode("life")
        life_labels = self.menu_labels()
        self.assertTrue(any(label.startswith("Rule:") for label in life_labels))
        self.assertTrue(any(label.startswith("Heatmap:") for label in life_labels))
        self.assertFalse(any("Electron" in label for label in life_labels))

        life.set_simulation_mode("wireworld")
        wireworld_labels = self.menu_labels()
        self.assertIn("Brush: Conductor", wireworld_labels)
        self.assertIn("Brush: Electron Head", wireworld_labels)
        self.assertIn("Brush: Electron Tail", wireworld_labels)
        self.assertFalse(any(label.startswith("Rule:") for label in wireworld_labels))
        self.assertFalse(any(label.startswith("Heatmap:") for label in wireworld_labels))

        life.set_simulation_mode("cyclic_automaton")
        cyclic_labels = self.menu_labels()
        self.assertTrue(any(label.startswith("Brush: Color") for label in cyclic_labels))
        self.assertTrue(any(label.startswith("Threshold:") for label in cyclic_labels))
        self.assertFalse(any("Electron" in label for label in cyclic_labels))

    def test_direct_context_brush_selection_refreshes_active_state(self) -> None:
        life.set_simulation_mode("wireworld")
        life.set_wireworld_brush(life.ELECTRON_HEAD)

        head_button = next(
            data["button"]
            for data in life.main_menu.buttons
            if data["button"].text == "Brush: Electron Head"
        )
        self.assertEqual(life.wireworld_brush, life.ELECTRON_HEAD)
        self.assertTrue(head_button.active)

    def test_context_button_can_be_clicked_without_prior_mouse_motion(self) -> None:
        life.set_simulation_mode("wireworld")
        head_data = next(
            data
            for data in life.main_menu.buttons
            if data["button"].text == "Brush: Electron Head"
        )
        event = life.pygame.event.Event(
            life.pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=head_data["button"].rect.center,
        )

        self.assertTrue(life.main_menu.handle_event(event))
        self.assertEqual(life.wireworld_brush, life.ELECTRON_HEAD)

    def test_mode_cards_fit_modal_without_overlap(self) -> None:
        modal, cards = life.mode_menu_geometry()
        self.assertEqual(len(cards), len(life.MODE_DEFINITIONS))
        for _, card in cards:
            self.assertTrue(modal.contains(card))
        for index, (_, card) in enumerate(cards):
            self.assertFalse(any(card.colliderect(other) for _, other in cards[index + 1 :]))

    def test_dispatch_tables_cover_every_registered_mode(self) -> None:
        expected = set(life.SIMULATION_MODES)
        self.assertEqual(set(life.GENERATION_HANDLERS), expected)
        self.assertEqual(set(life.DRAW_HANDLERS), expected)

    def test_context_menu_fits_minimum_window_height(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(760, 560)
            for mode in life.SIMULATION_MODES:
                with self.subTest(mode=mode):
                    life.set_simulation_mode(mode)
                    self.assertTrue(
                        all(
                            data["button"].rect.bottom <= life.main_menu.rect.bottom
                            for data in life.main_menu.buttons
                        )
                    )
        finally:
            life.update_window_size(*original_size)


class RenderCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        life.set_simulation_mode("wireworld")
        life.wireworld_grid = life.make_wireworld_grid(life.ROWS, life.COLS)
        life.selected_pattern = None
        life.show_grid = True
        life.simulation_active = False
        life.rendered_grid_cache.clear()
        life.mode_stats_cache.clear()
        life.reset_render_cache_metrics()
        life.invalidate_render_cache("wireworld")

    def tearDown(self) -> None:
        life.cell_transition.transitions.clear()
        life.show_grid = True
        life.show_heatmap = False
        life.rendered_grid_cache.clear()
        life.mode_stats_cache.clear()
        life.set_simulation_mode("life")

    def test_unchanged_grid_reuses_cached_viewport(self) -> None:
        renderer = Mock()
        with (
            patch.dict(life.DRAW_HANDLERS, {"wireworld": renderer}),
            patch("life.draw_pattern_preview"),
        ):
            life.draw_active_grid()
            life.draw_active_grid()

        self.assertEqual(renderer.call_count, 1)
        self.assertEqual(life.render_cache_misses, 1)
        self.assertEqual(life.render_cache_hits, 1)

    def test_drawing_a_cell_invalidates_cached_viewport(self) -> None:
        renderer = Mock()
        with (
            patch.dict(life.DRAW_HANDLERS, {"wireworld": renderer}),
            patch("life.draw_pattern_preview"),
        ):
            life.draw_active_grid()
            life.drawing_value = 1
            life.drawing_history_pending = False
            life.draw_cell(2, 2)
            life.draw_active_grid()

        self.assertEqual(renderer.call_count, 2)

    def test_pattern_preview_remains_dynamic_on_cache_hits(self) -> None:
        renderer = Mock()
        preview_clips = []

        def record_clip() -> None:
            preview_clips.append(life.screen.get_clip())

        with (
            patch.dict(life.DRAW_HANDLERS, {"wireworld": renderer}),
            patch("life.draw_pattern_preview", side_effect=record_clip) as preview,
        ):
            life.draw_active_grid()
            life.draw_active_grid()

        self.assertEqual(renderer.call_count, 1)
        self.assertEqual(preview.call_count, 2)
        self.assertEqual(preview_clips, [life.grid_viewport(), life.grid_viewport()])

    def test_visual_setting_change_rebuilds_cache(self) -> None:
        renderer = Mock()
        with (
            patch.dict(life.DRAW_HANDLERS, {"wireworld": renderer}),
            patch("life.draw_pattern_preview"),
        ):
            life.draw_active_grid()
            life.show_grid = False
            life.draw_active_grid()

        self.assertEqual(renderer.call_count, 2)

    def test_cached_viewport_matches_uncached_pixels(self) -> None:
        life.wireworld_grid[3][3:6] = [
            life.ELECTRON_TAIL,
            life.ELECTRON_HEAD,
            life.CONDUCTOR,
        ]
        life.invalidate_render_cache("wireworld")

        life.draw_active_grid()
        viewport = life.grid_viewport()
        uncached = life.screen.subsurface(viewport).copy()
        life.draw_active_grid()
        cached = life.screen.subsurface(viewport).copy()

        self.assertEqual(
            life.pygame.image.tobytes(uncached, "RGB"),
            life.pygame.image.tobytes(cached, "RGB"),
        )

    def test_cached_life_heatmap_matches_uncached_pixels(self) -> None:
        life.set_simulation_mode("life")
        life.grid = life.make_grid()
        life.trail_grid = life.make_grid()
        life.activity_grid = life.make_float_grid()
        life.grid[3][3] = 4
        life.trail_grid[4][4] = life.TRAIL_MAX
        life.activity_grid[5][5] = 8.0
        life.show_heatmap = True
        life.invalidate_render_cache("life")

        life.draw_active_grid()
        viewport = life.grid_viewport()
        uncached = life.screen.subsurface(viewport).copy()
        life.draw_active_grid()
        cached = life.screen.subsurface(viewport).copy()

        self.assertEqual(
            life.pygame.image.tobytes(uncached, "RGB"),
            life.pygame.image.tobytes(cached, "RGB"),
        )

    def test_running_at_sixty_skips_cache_capture(self) -> None:
        original_speed = life.speed
        life.simulation_active = True
        life.speed = 60
        renderer = Mock()
        try:
            with (
                patch.dict(life.DRAW_HANDLERS, {"wireworld": renderer}),
                patch("life.draw_pattern_preview"),
            ):
                life.draw_active_grid()
        finally:
            life.speed = original_speed
            life.simulation_active = False

        self.assertEqual(renderer.call_count, 1)
        self.assertNotIn("wireworld", life.rendered_grid_cache)

    def test_life_transitions_bypass_static_cache(self) -> None:
        life.set_simulation_mode("life")
        life.invalidate_render_cache("life")
        life.cell_transition.start_transition(1, 1, 0, 1)
        renderer = Mock()
        with (
            patch.dict(life.DRAW_HANDLERS, {"life": renderer}),
            patch("life.draw_pattern_preview"),
        ):
            life.draw_active_grid()
            life.draw_active_grid()

        self.assertEqual(renderer.call_count, 2)
        self.assertNotIn("life", life.rendered_grid_cache)

    def test_mode_statistics_are_cached_until_invalidation(self) -> None:
        calculator = Mock(side_effect=({"value": 1}, {"value": 2}))

        first = life.cached_mode_stats("wireworld", calculator)
        second = life.cached_mode_stats("wireworld", calculator)
        life.invalidate_render_cache("wireworld")
        third = life.cached_mode_stats("wireworld", calculator)

        self.assertIs(first, second)
        self.assertIsNot(second, third)
        self.assertEqual(calculator.call_count, 2)


class ImmigrationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "immigration"
        life.simulation_active = False
        life.immigration_grid = life.make_immigration_grid(life.ROWS, life.COLS)
        life.immigration_generation = 0
        life.active_species = life.SPECIES_A
        reset_mode_timeline("immigration")

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_uses_separate_grid_and_history(self) -> None:
        life.immigration_grid[5][4:7] = [
            life.SPECIES_A,
            life.SPECIES_A,
            life.SPECIES_B,
        ]
        reset_mode_timeline("immigration")

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.immigration_generation, 1)
        self.assertEqual(timeline_change_count("immigration"), 1)

    def test_mode_switch_preserves_both_grids(self) -> None:
        life.grid = life.make_grid()
        life.grid[2][2] = 4
        life.immigration_grid[3][3] = life.SPECIES_B

        for _ in life.SIMULATION_MODES:
            life.toggle_simulation_mode()

        self.assertEqual(life.simulation_mode, "immigration")
        self.assertEqual(life.grid[2][2], 4)
        self.assertEqual(life.immigration_grid[3][3], life.SPECIES_B)

    def test_pattern_uses_active_species_and_one_history_entry(self) -> None:
        life.active_species = life.SPECIES_B
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(timeline_change_count("immigration"), 1)
        self.assertTrue(
            all(
                life.immigration_grid[row][col] == life.SPECIES_B
                for row in (2, 3)
                for col in (2, 3)
            )
        )


class BriansBrainIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "brians_brain"
        life.simulation_active = False
        life.brain_grid = life.make_brain_grid(life.ROWS, life.COLS)
        life.brain_generation = 0
        reset_mode_timeline("brians_brain")

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_uses_separate_brain_history(self) -> None:
        life.brain_grid[5][4:6] = [life.FIRING, life.FIRING]
        reset_mode_timeline("brians_brain")

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.brain_generation, 1)
        self.assertEqual(timeline_change_count("brians_brain"), 1)
        self.assertEqual(life.brain_grid[5][4], life.DYING)

    def test_pattern_places_firing_cells(self) -> None:
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(timeline_change_count("brians_brain"), 1)
        self.assertTrue(
            all(
                life.brain_grid[row][col] == life.FIRING
                for row in (2, 3)
                for col in (2, 3)
            )
        )


class LangtonsAntIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "langtons_ant"
        life.simulation_active = False
        life.ant_grid = life.make_ant_grid(life.ROWS, life.COLS)
        life.ant_state = life.centered_ant(life.ROWS, life.COLS)
        life.ant_generation = 0
        life.ant_last_report = life.AntStepReport()
        reset_mode_timeline("langtons_ant")

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_tracks_ant_state_and_history(self) -> None:
        original = life.ant_state

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.ant_generation, 1)
        self.assertEqual(timeline_change_count("langtons_ant"), 1)
        self.assertEqual(life.ant_grid[original.row][original.col], life.ANT_BLACK)
        self.assertNotEqual(life.ant_state, original)

    def test_pattern_places_black_cells(self) -> None:
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(timeline_change_count("langtons_ant"), 1)
        self.assertTrue(
            all(
                life.ant_grid[row][col] == life.ANT_BLACK
                for row in (2, 3)
                for col in (2, 3)
            )
        )

    def test_place_ant_preserves_direction_and_saves_history(self) -> None:
        original_direction = life.ant_state.direction

        life.place_ant(4, 7)

        self.assertEqual((life.ant_state.row, life.ant_state.col), (4, 7))
        self.assertEqual(life.ant_state.direction, original_direction)
        self.assertEqual(timeline_change_count("langtons_ant"), 1)


class WireworldIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "wireworld"
        life.simulation_active = False
        life.wireworld_grid = life.make_wireworld_grid(life.ROWS, life.COLS)
        life.wireworld_generation = 0
        life.wireworld_brush = life.CONDUCTOR
        reset_mode_timeline("wireworld")

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_propagates_signal_and_tracks_history(self) -> None:
        life.wireworld_grid[5][4:7] = [
            life.ELECTRON_TAIL,
            life.ELECTRON_HEAD,
            life.CONDUCTOR,
        ]
        reset_mode_timeline("wireworld")

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.wireworld_generation, 1)
        self.assertEqual(timeline_change_count("wireworld"), 1)
        self.assertEqual(
            life.wireworld_grid[5][4:7],
            [life.CONDUCTOR, life.ELECTRON_TAIL, life.ELECTRON_HEAD],
        )

    def test_pattern_places_conductors(self) -> None:
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(timeline_change_count("wireworld"), 1)
        self.assertTrue(
            all(
                life.wireworld_grid[row][col] == life.CONDUCTOR
                for row in (2, 3)
                for col in (2, 3)
            )
        )

    def test_t_cycles_through_three_wireworld_brushes(self) -> None:
        brushes = []
        for _ in range(3):
            life.toggle_active_species()
            brushes.append(life.wireworld_brush)

        self.assertEqual(
            brushes,
            [life.ELECTRON_HEAD, life.ELECTRON_TAIL, life.CONDUCTOR],
        )

    def test_right_brush_erases_and_adds_one_history_entry(self) -> None:
        life.wireworld_grid[2][2] = life.CONDUCTOR
        reset_mode_timeline("wireworld")
        life.drawing_value = 0
        life.drawing_history_pending = True

        life.draw_cell(2, 2)

        self.assertEqual(life.wireworld_grid[2][2], life.WIRE_EMPTY)
        self.assertEqual(timeline_change_count("wireworld"), 1)


class ModeSpecificPatternIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_active = False
        life.selected_pattern = None
        life.rotation = 0
        life.flip_h = False
        life.flip_v = False
        life.grid = life.make_grid()
        life.immigration_grid = life.make_immigration_grid(life.ROWS, life.COLS)
        life.brain_grid = life.make_brain_grid(life.ROWS, life.COLS)
        life.ant_grid = life.make_ant_grid(life.ROWS, life.COLS)
        life.ant_state = life.centered_ant(life.ROWS, life.COLS)
        life.wireworld_grid = life.make_wireworld_grid(life.ROWS, life.COLS)
        life.cyclic_grid = life.make_cyclic_grid(life.ROWS, life.COLS)
        for mode in life.SIMULATION_MODES:
            reset_mode_timeline(mode)

    def tearDown(self) -> None:
        life.rotation = 0
        life.flip_h = False
        life.flip_v = False
        life.set_simulation_mode("life")

    def pattern_named(self, name: str) -> dict:
        return next(
            pattern
            for pattern in life.available_patterns().values()
            if pattern["name"] == name
        )

    def test_available_patterns_follow_selected_mode(self) -> None:
        for mode in life.SIMULATION_MODES:
            with self.subTest(mode=mode):
                life.set_simulation_mode(mode)
                available = life.available_patterns()
                self.assertTrue(available)
                self.assertTrue(
                    all(pattern["mode"] == mode for pattern in available.values())
                )

    def test_wireworld_pattern_preserves_all_signal_states(self) -> None:
        life.set_simulation_mode("wireworld")
        life.selected_pattern = self.pattern_named("Signal on Straight Wire")

        life.place_selected_pattern(3, 4)

        self.assertEqual(
            life.wireworld_grid[3][4:8],
            [life.ELECTRON_TAIL, life.ELECTRON_HEAD, life.CONDUCTOR, life.CONDUCTOR],
        )
        self.assertEqual(timeline_change_count("wireworld"), 1)

    def test_brain_pattern_preserves_dying_cells(self) -> None:
        life.set_simulation_mode("brians_brain")
        life.selected_pattern = self.pattern_named("Period-3 Oscillator")

        life.place_selected_pattern(3, 4)

        self.assertEqual(life.brain_grid[4][5:7], [life.DYING, life.DYING])
        self.assertEqual(timeline_change_count("brians_brain"), 1)

    def test_immigration_pattern_preserves_both_species(self) -> None:
        life.set_simulation_mode("immigration")
        life.active_species = life.SPECIES_A
        life.selected_pattern = self.pattern_named("Split-Species Block")

        life.place_selected_pattern(3, 4)

        self.assertEqual(
            [life.immigration_grid[3][4:6], life.immigration_grid[4][4:6]],
            [[life.SPECIES_A, life.SPECIES_A], [life.SPECIES_B, life.SPECIES_B]],
        )

    def test_langton_pattern_places_and_rotates_ant_metadata(self) -> None:
        life.set_simulation_mode("langtons_ant")
        life.selected_pattern = self.pattern_named("Single Ant on White")
        life.rotation = 90

        life.place_selected_pattern(4, 7)

        self.assertEqual((life.ant_state.row, life.ant_state.col), (4, 7))
        self.assertEqual(life.DIRECTION_NAMES[life.ant_state.direction], "East")
        self.assertEqual(timeline_change_count("langtons_ant"), 1)

    def test_pattern_from_other_mode_is_rejected(self) -> None:
        life.set_simulation_mode("life")
        life.selected_pattern = next(
            pattern
            for pattern in life.get_patterns_for_mode("wireworld").values()
            if pattern["name"] == "Signal on Straight Wire"
        )

        life.place_selected_pattern(2, 2)

        self.assertFalse(any(cell for row in life.grid for cell in row))
        self.assertEqual(timeline_change_count("life"), 0)

    def test_cropping_preserves_wireworld_states(self) -> None:
        life.wireworld_grid[2][3:6] = [
            life.ELECTRON_TAIL,
            life.ELECTRON_HEAD,
            life.CONDUCTOR,
        ]

        cropped, ant = life.crop_mode_pattern(life.wireworld_grid, "wireworld")

        self.assertEqual(cropped, [[2, 1, 3]])
        self.assertIsNone(ant)

    def test_cyclic_pattern_preserves_zero_as_a_real_color(self) -> None:
        life.set_simulation_mode("cyclic_automaton")
        life.cyclic_grid = life.make_cyclic_grid(
            life.ROWS,
            life.COLS,
            fill_state=7,
        )
        reset_mode_timeline("cyclic_automaton")
        life.selected_pattern = self.pattern_named("Concentric Color Rings")

        life.place_selected_pattern(2, 3)

        self.assertEqual(life.cyclic_grid[2][3], 0)
        self.assertEqual(life.cyclic_grid[6][7], 4)
        self.assertEqual(timeline_change_count("cyclic_automaton"), 1)

    def test_blank_langton_board_can_save_ant_state(self) -> None:
        life.ant_state = life.AntState(6, 9, 3)

        cropped, ant = life.crop_mode_pattern(life.ant_grid, "langtons_ant")

        self.assertEqual(cropped, [[0]])
        self.assertEqual(ant, {"row": 0, "col": 0, "direction": 3})

    def test_saving_langton_pattern_includes_mode_and_ant(self) -> None:
        life.set_simulation_mode("langtons_ant")
        life.ant_state = life.AntState(6, 9, 3)

        with (
            patch("life.get_pattern_name", return_value="Corner Ant"),
            patch("life.save_pattern") as save_pattern,
        ):
            life.save_current_pattern()

        save_pattern.assert_called_once_with(
            [[0]],
            "Corner Ant",
            mode="langtons_ant",
            ant={"row": 0, "col": 0, "direction": 3},
        )


class CyclicAutomatonIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "cyclic_automaton"
        life.simulation_active = False
        life.cyclic_grid = life.make_cyclic_grid(life.ROWS, life.COLS)
        life.cyclic_generation = 0
        life.cyclic_brush = 1
        life.cyclic_threshold = 1
        reset_mode_timeline("cyclic_automaton")

    def tearDown(self) -> None:
        life.set_simulation_mode("life")

    def test_generation_uses_separate_grid_and_history(self) -> None:
        life.cyclic_grid[5][5] = 1
        reset_mode_timeline("cyclic_automaton")

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.cyclic_grid[5][4], 1)
        self.assertEqual(life.cyclic_generation, 1)
        self.assertEqual(timeline_change_count("cyclic_automaton"), 1)

    def test_homogeneous_grid_stops_without_history_entry(self) -> None:
        self.assertFalse(life.apply_generation())

        self.assertFalse(life.simulation_active)
        self.assertEqual(life.cyclic_generation, 0)
        self.assertEqual(timeline_change_count("cyclic_automaton"), 0)

    def test_step_back_restores_previous_cyclic_generation(self) -> None:
        life.cyclic_grid[5][5] = 1
        original = [row[:] for row in life.cyclic_grid]
        reset_mode_timeline("cyclic_automaton")
        life.apply_generation()

        life.step_back()

        self.assertEqual(life.cyclic_grid, original)
        self.assertEqual(life.cyclic_generation, 0)

    def test_t_cycles_through_all_color_brushes(self) -> None:
        for _ in range(life.CYCLIC_STATE_COUNT):
            life.toggle_active_species()

        self.assertEqual(life.cyclic_brush, 1)

    def test_threshold_control_cycles_through_moore_range(self) -> None:
        for _ in range(life.CYCLIC_MAX_THRESHOLD):
            life.cycle_cyclic_threshold()

        self.assertEqual(life.cyclic_threshold, 1)

    def test_right_brush_paints_color_zero(self) -> None:
        life.cyclic_grid[2][2] = 5
        reset_mode_timeline("cyclic_automaton")
        life.drawing_value = 0
        life.drawing_history_pending = True

        life.draw_cell(2, 2)

        self.assertEqual(life.cyclic_grid[2][2], 0)
        self.assertEqual(timeline_change_count("cyclic_automaton"), 1)


class TimelineIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.set_simulation_mode("life")
        life.current_rule = "conway"
        life.grid = life.make_grid()
        life.trail_grid = life.make_grid()
        life.activity_grid = life.make_float_grid()
        life.generation = 0
        life.simulation_active = False
        life.timeline_panel.stop()
        life.grid[8][7:10] = [1, 1, 1]
        reset_mode_timeline("life")

    def tearDown(self) -> None:
        life.timeline_panel.stop()
        life.set_simulation_mode("life")

    def test_workspace_can_seek_and_step_forward_after_undo(self) -> None:
        initial = [row[:] for row in life.grid]
        self.assertTrue(life.apply_generation())
        generation_one = [row[:] for row in life.grid]
        self.assertTrue(life.apply_generation())

        self.assertTrue(life.seek_active_history(0))
        self.assertEqual(life.grid, initial)
        self.assertEqual(life.generation, 0)
        life.step_forward()
        self.assertEqual(life.grid, generation_one)
        self.assertEqual(life.generation, 1)

    def test_editing_a_past_frame_discards_only_its_future(self) -> None:
        self.assertTrue(life.apply_generation())
        self.assertTrue(life.apply_generation())
        self.assertTrue(life.seek_active_history(1))

        life.drawing_value = 1
        life.drawing_history_pending = True
        life.draw_cell(2, 2)
        life.two_dimensional_controller.sync_history()

        status = life.active_history_status()
        self.assertEqual(status.frame_count, 3)
        self.assertEqual(status.cursor, 2)
        self.assertFalse(status.can_step_forward)
        self.assertEqual(life.grid[2][2], 1)

    def test_each_2d_mode_keeps_an_independent_timeline(self) -> None:
        self.assertTrue(life.apply_generation())
        life.set_simulation_mode("immigration")
        life.immigration_grid = life.make_immigration_grid(life.ROWS, life.COLS)
        life.immigration_generation = 0
        life.immigration_grid[5][4:7] = [
            life.SPECIES_A,
            life.SPECIES_A,
            life.SPECIES_B,
        ]
        reset_mode_timeline("immigration")
        self.assertTrue(life.apply_generation())

        self.assertEqual(timeline_change_count("immigration"), 1)
        self.assertEqual(timeline_change_count("life"), 1)

    def test_dragging_timeline_track_seeks_to_first_frame(self) -> None:
        self.assertTrue(life.apply_generation())
        self.assertTrue(life.apply_generation())
        _, _, track, _ = life.timeline_panel.geometry()

        consumed = life.timeline_panel.handle_event(
            life.pygame.event.Event(
                life.pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=(track.left, track.centery),
            )
        )
        life.timeline_panel.handle_event(
            life.pygame.event.Event(
                life.pygame.MOUSEBUTTONUP,
                button=1,
                pos=(track.left, track.centery),
            )
        )

        self.assertTrue(consumed)
        self.assertEqual(life.generation, 0)
        self.assertEqual(life.active_history_status().cursor, 0)

    def test_timeline_playback_runs_forward_and_reverse_over_existing_frames(self) -> None:
        self.assertTrue(life.apply_generation())
        self.assertTrue(life.apply_generation())
        self.assertTrue(life.seek_active_history(0))

        life.timeline_panel.play_direction = 1
        life.timeline_panel.update(1.0)
        self.assertEqual(life.generation, 2)
        self.assertEqual(life.timeline_panel.play_direction, 0)

        life.timeline_panel.play_direction = -1
        life.timeline_panel.update(1.0)
        self.assertEqual(life.generation, 0)
        self.assertEqual(life.timeline_panel.play_direction, 0)

    def test_j_prompt_seeks_an_exact_generation(self) -> None:
        self.assertTrue(life.apply_generation())
        self.assertTrue(life.apply_generation())

        with patch("life.get_text_input", return_value="1"):
            life.request_timeline_generation()

        self.assertEqual(life.generation, 1)
        self.assertEqual(life.active_history_status().generation, 1)

    def test_every_2d_mode_restores_backward_and_forward(self) -> None:
        for mode in life.SIMULATION_MODES:
            with self.subTest(mode=mode):
                life.set_simulation_mode(mode)
                if mode == "life":
                    life.grid = life.make_grid()
                    life.trail_grid = life.make_grid()
                    life.activity_grid = life.make_float_grid()
                    life.grid[5][4:7] = [1, 1, 1]
                    life.generation = 0
                elif mode == "immigration":
                    life.immigration_grid = life.make_immigration_grid(
                        life.ROWS, life.COLS
                    )
                    life.immigration_grid[5][4:7] = [
                        life.SPECIES_A,
                        life.SPECIES_A,
                        life.SPECIES_B,
                    ]
                    life.immigration_generation = 0
                elif mode == "brians_brain":
                    life.brain_grid = life.make_brain_grid(life.ROWS, life.COLS)
                    life.brain_grid[5][4:6] = [life.FIRING, life.FIRING]
                    life.brain_generation = 0
                elif mode == "langtons_ant":
                    life.ant_grid = life.make_ant_grid(life.ROWS, life.COLS)
                    life.ant_state = life.centered_ant(life.ROWS, life.COLS)
                    life.ant_generation = 0
                    life.ant_last_report = life.AntStepReport()
                elif mode == "wireworld":
                    life.wireworld_grid = life.make_wireworld_grid(
                        life.ROWS, life.COLS
                    )
                    life.wireworld_grid[5][4:7] = [
                        life.ELECTRON_TAIL,
                        life.ELECTRON_HEAD,
                        life.CONDUCTOR,
                    ]
                    life.wireworld_generation = 0
                else:
                    life.cyclic_grid = life.make_cyclic_grid(life.ROWS, life.COLS)
                    life.cyclic_grid[5][5] = 1
                    life.cyclic_generation = 0
                    life.cyclic_threshold = 1
                reset_mode_timeline(mode)

                self.assertTrue(life.apply_generation())
                self.assertEqual(life._two_d_generation(), 1)
                life.step_back()
                self.assertEqual(life._two_d_generation(), 0)
                life.step_forward()
                self.assertEqual(life._two_d_generation(), 1)

    def test_rule_parameters_are_part_of_timeline_state(self) -> None:
        original_rule = life.current_rule
        life.cycle_rule()
        changed_rule = life.current_rule
        self.assertNotEqual(changed_rule, original_rule)
        life.step_back()
        self.assertEqual(life.current_rule, original_rule)
        life.step_forward()
        self.assertEqual(life.current_rule, changed_rule)

        life.set_simulation_mode("cyclic_automaton")
        life.cyclic_grid = life.make_cyclic_grid(life.ROWS, life.COLS)
        life.cyclic_generation = 0
        life.cyclic_threshold = 1
        reset_mode_timeline("cyclic_automaton")
        life.cycle_cyclic_threshold()
        self.assertEqual(life.cyclic_threshold, 2)
        life.step_back()
        self.assertEqual(life.cyclic_threshold, 1)
        life.step_forward()
        self.assertEqual(life.cyclic_threshold, 2)


if __name__ == "__main__":
    unittest.main()
