"""Tests for navigation, accessibility, favorites, and recent experiments."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import life
from themes import (
    COLORBLIND_BLUE,
    COLORBLIND_MAGENTA,
    COLORBLIND_YELLOW,
    THEMES,
    Menu,
    get_age_color,
    one_d_state_color,
)
from ui_preferences import UIPreferences


def contrast_ratio(
    first: tuple[int, int, int],
    second: tuple[int, int, int],
) -> float:
    """Return WCAG relative-luminance contrast for deterministic palette tests."""

    def luminance(color: tuple[int, int, int]) -> float:
        channels = []
        for value in color:
            normalized = value / 255
            channels.append(
                normalized / 12.92
                if normalized <= 0.04045
                else ((normalized + 0.055) / 1.055) ** 2.4
            )
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class CollapsibleMenuTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.Surface((640, 480))
        self.font = pygame.font.SysFont("Arial", 12)

    def test_section_collapse_hides_buttons_and_survives_rebuild(self) -> None:
        menu = Menu(380, 20, 250, 430)
        menu.visible = True
        menu.set_header("Test")
        menu.begin_section("tools", "Tools")
        menu.add_button("Draw", lambda: None, tooltip="Draw cells.")
        self.assertTrue(menu.buttons[0]["visible"])

        section = menu.sections[0]
        consumed = menu.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=section["rect"].center,
            )
        )

        self.assertTrue(consumed)
        self.assertFalse(menu.buttons[0]["visible"])
        menu.clear_buttons()
        menu.begin_section("tools", "Tools", expanded=True)
        menu.add_button("Draw", lambda: None)
        self.assertFalse(menu.sections[0]["expanded"])

    def test_hover_tracks_tooltip_target_without_consuming_motion(self) -> None:
        menu = Menu(380, 20, 250, 430)
        menu.visible = True
        menu.begin_section("tools", "Tools")
        menu.add_button("Draw", lambda: None, tooltip="Draw cells.")
        button = menu.buttons[0]["button"]

        consumed = menu.handle_event(
            pygame.event.Event(
                pygame.MOUSEMOTION,
                pos=button.rect.center,
                rel=(0, 0),
                buttons=(False, False, False),
            )
        )
        menu._hover_started = -1000
        menu.draw(self.screen, self.font)

        self.assertFalse(consumed)
        self.assertEqual(menu._hover_token, ("button", 0))


class PreferenceStorageTests(unittest.TestCase):
    def test_favorites_and_recents_round_trip_and_deduplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ui.json"
            preferences = UIPreferences(path=path)
            self.assertTrue(preferences.toggle_favorite_rule(110))
            preferences.record_recent("session", "alpha", "Alpha")
            preferences.record_recent("profile", "rule_30", "Rule 30")
            preferences.record_recent("session", "alpha", "Alpha New")

            loaded = UIPreferences.load(path)

            self.assertEqual(loaded.favorite_rules, {110})
            self.assertEqual(loaded.recent_experiments[0]["name"], "Alpha New")
            self.assertEqual(len(loaded.recent_experiments), 2)

    def test_corrupt_preferences_fall_back_to_empty_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ui.json"
            path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")

            loaded = UIPreferences.load(path)

            self.assertEqual(loaded.favorite_rules, set())
            self.assertEqual(loaded.recent(), [])


class ApplicationUIImprovementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_session = life.capture_session_document("UI Restore")
        self.original_favorites = set(life.ui_preferences.favorite_rules)
        self.original_recents = life.ui_preferences.recent()
        life.help_panel.close()
        life.one_d_tutorial.close()
        life.two_d_tutorial.close()
        life.three_d_tutorial.close()
        life.ui_preferences.favorite_rules.clear()
        life.ui_preferences.recent_experiments.clear()

    def tearDown(self) -> None:
        life.help_panel.close()
        life.one_d_tutorial.close()
        life.two_d_tutorial.close()
        life.three_d_tutorial.close()
        life.ui_preferences.favorite_rules = self.original_favorites
        life.ui_preferences.recent_experiments = self.original_recents
        life.restore_session_document(self.original_session)

    def test_f1_help_is_contextual_pauses_and_fits_window(self) -> None:
        life.set_active_dimension("1d")
        life.simulation_active = True

        life.handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0))
        modal, close = life.help_panel.geometry()

        self.assertTrue(life.help_panel.active)
        self.assertFalse(life.simulation_active)
        self.assertIn("1D", life.help_context_title())
        self.assertTrue(modal.contains(close))
        life.draw_scene()

    def test_f2_opens_full_screen_tutorial_and_pauses(self) -> None:
        life.set_active_dimension("1d")
        life.simulation_active = True

        life.handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=0))
        modal, viewport, close, back, next_button = life.one_d_tutorial.geometry()

        self.assertTrue(life.one_d_tutorial.active)
        self.assertFalse(life.simulation_active)
        self.assertGreaterEqual(modal.width, life.WINDOW_WIDTH - 30)
        self.assertTrue(modal.contains(viewport))
        self.assertTrue(modal.contains(close))
        self.assertTrue(modal.contains(back))
        self.assertTrue(modal.contains(next_button))
        life.draw_scene()

    def test_f2_opens_2d_foundations_and_only_the_active_mode_guide(self) -> None:
        life.set_simulation_mode("wireworld")
        life.simulation_active = True

        life.handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=0))
        modal, viewport, close, back, next_button, tabs = life.two_d_tutorial.geometry()

        self.assertTrue(life.two_d_tutorial.active)
        self.assertFalse(life.one_d_tutorial.active)
        self.assertFalse(life.simulation_active)
        self.assertEqual(life.two_d_tutorial.tab, life.two_d_tutorial.FOUNDATIONS)
        self.assertEqual(life.two_d_tutorial.guide.name, "Wireworld")
        self.assertEqual(life.two_d_tutorial.mode_tab_label, "MODE: WIREWORLD")
        self.assertGreaterEqual(modal.width, life.WINDOW_WIDTH - 30)
        self.assertTrue(modal.contains(viewport))
        self.assertTrue(modal.contains(close))
        self.assertTrue(modal.contains(back))
        self.assertTrue(modal.contains(next_button))
        self.assertFalse(tabs[0].colliderect(tabs[1]))
        life.draw_scene()

    def test_f2_opens_3d_foundations_and_only_the_active_mode_guide(self) -> None:
        with patch.object(life, "_switch_display_backend", return_value=True):
            self.assertTrue(life.set_active_dimension("3d"))
        life.three_dimensional_controller.set_mode("generations")
        life.simulation_active = True

        life.handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=0))
        modal, viewport, close, back, next_button, tabs = life.three_d_tutorial.geometry()

        self.assertTrue(life.three_d_tutorial.active)
        self.assertFalse(life.one_d_tutorial.active)
        self.assertFalse(life.two_d_tutorial.active)
        self.assertFalse(life.simulation_active)
        self.assertEqual(life.three_d_tutorial.tab, life.three_d_tutorial.FOUNDATIONS)
        self.assertEqual(life.three_d_tutorial.guide.name, "3D Generations")
        self.assertEqual(life.three_d_tutorial.mode_tab_label, "MODE: 3D GENERATIONS")
        self.assertGreaterEqual(modal.width, life.WINDOW_WIDTH - 30)
        self.assertTrue(modal.contains(viewport))
        self.assertTrue(modal.contains(close))
        self.assertTrue(modal.contains(back))
        self.assertTrue(modal.contains(next_button))
        self.assertFalse(tabs[0].colliderect(tabs[1]))
        life.draw_scene()

    def test_3d_tutorial_experiment_loads_documented_spatial_life_seed(self) -> None:
        life.start_three_d_tutorial_experiment("spatial_life")

        controller = life.three_dimensional_controller
        self.assertEqual(controller.state.mode_key, "spatial_life")
        self.assertEqual(controller.state.rule_key, "bays_5766")
        self.assertEqual(controller.state.volume.boundary, "wrap")
        self.assertEqual(int((controller.state.volume.cells != 0).sum()), 10)

    def test_selecting_1d_does_not_open_tutorial_automatically(self) -> None:
        life.set_active_dimension("2d")
        life.activate_dimension_menu()

        self.assertTrue(
            life.handle_dimension_menu_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
            )
        )

        self.assertEqual(life.active_dimension, "1d")
        self.assertFalse(life.one_d_tutorial.active)

    def test_status_badge_is_clickable_and_tool_label_is_explicit(self) -> None:
        life.set_simulation_mode("immigration")
        life.active_species = life.SPECIES_B
        life.simulation_active = False

        life.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=life.run_pause_rect().center,
            )
        )

        self.assertTrue(life.simulation_active)
        self.assertEqual(life.active_tool_label(), "Species B")

    def test_rule_catalog_search_and_favorite_filter(self) -> None:
        life.set_active_dimension("1d")
        life.activate_eca_rule_menu()
        for key in (pygame.K_1, pygame.K_1):
            life.handle_eca_rule_menu_event(
                pygame.event.Event(pygame.KEYDOWN, key=key)
            )
        _, cards = life.eca_rule_menu_geometry()
        self.assertTrue(cards)
        self.assertTrue(all("11" in str(rule) for rule, _ in cards))

        rule, card = next((rule, card) for rule, card in cards if rule == 110)
        life.handle_eca_rule_menu_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=3,
                pos=card.center,
            )
        )
        life.handle_eca_rule_menu_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        )
        _, favorite_cards = life.eca_rule_menu_geometry()

        self.assertEqual(rule, 110)
        self.assertEqual([value for value, _ in favorite_cards], [110])

    def test_colorblind_theme_has_state_palettes_not_only_color_names(self) -> None:
        life.current_theme = "colorblind"
        life.set_simulation_mode("wireworld")

        self.assertIn("colorblind", THEMES)
        self.assertNotEqual(
            life.immigration_species_color(life.SPECIES_A),
            life.immigration_species_color(life.SPECIES_B),
        )
        self.assertEqual(life.wireworld_state_color(life.CONDUCTOR), (240, 228, 66))
        self.assertEqual(
            life.immigration_species_base_color(life.SPECIES_A),
            COLORBLIND_BLUE,
        )
        self.assertEqual(
            life.immigration_species_base_color(life.SPECIES_B),
            COLORBLIND_YELLOW,
        )
        self.assertEqual(life.ant_display_color(), COLORBLIND_BLUE)
        self.assertEqual(len(set(life.COLORBLIND_CYCLIC_PALETTE)), 8)
        self.assertEqual(
            life.export_coordinator.palette()[life.ELECTRON_TAIL],
            COLORBLIND_MAGENTA,
        )

    def test_colorblind_screen_and_export_semantic_palettes_match(self) -> None:
        life.current_theme = "colorblind"

        life.set_simulation_mode("immigration")
        immigration_palette = life.export_coordinator.palette()
        self.assertEqual(
            immigration_palette[life.SPECIES_A],
            life.immigration_species_base_color(life.SPECIES_A),
        )
        self.assertEqual(
            immigration_palette[2],
            life.immigration_species_base_color(life.SPECIES_B),
        )

        life.set_simulation_mode("langtons_ant")
        self.assertEqual(
            life.export_coordinator.palette()[2],
            life.ant_display_color(),
        )

    def test_screen_and_export_palettes_match_across_specialized_modes(self) -> None:
        life.set_active_dimension("2d")
        for theme_name in ("classic", "midnight", "paper", "colorblind"):
            life.current_theme = theme_name
            with self.subTest(theme=theme_name, mode="brians_brain"):
                life.set_simulation_mode("brians_brain")
                palette = life.export_coordinator.palette()
                self.assertEqual(palette[1], life.brain_state_color(life.FIRING))
                self.assertEqual(palette[2], life.brain_state_color(life.DYING))
            with self.subTest(theme=theme_name, mode="cyclic_automaton"):
                life.set_simulation_mode("cyclic_automaton")
                palette = life.export_coordinator.palette()
                self.assertTrue(
                    all(
                        palette[state] == life.cyclic_state_color(state)
                        for state in range(life.CYCLIC_STATE_COUNT)
                    )
                )

    def test_1d_screen_and_export_palettes_share_primary_and_comparison_colors(self) -> None:
        life.set_active_dimension("1d")
        state = life.elementary_controller.state
        state.states = 2
        for theme_name in ("classic", "midnight", "paper", "colorblind"):
            life.current_theme = theme_name
            palette = life.export_coordinator.palette()
            with self.subTest(theme=theme_name):
                self.assertEqual(
                    palette[1],
                    life.elementary_renderer._state_color(1),
                )
                self.assertEqual(
                    palette[2],
                    life.elementary_renderer._state_color(1, secondary=True),
                )
                self.assertNotEqual(palette[1], palette[2])

    def test_colorblind_immigration_species_b_has_a_non_color_marker(self) -> None:
        original_cell_size = life.CELL_SIZE
        life.current_theme = "colorblind"
        life.CELL_SIZE = 12
        rect = pygame.Rect(20, 20, 12, 12)
        base = life.immigration_species_base_color(life.SPECIES_B)
        try:
            pygame.draw.rect(life.screen, base, rect)
            life.draw_immigration_marker(rect, life.SPECIES_B)
            marker = rect.inflate(-4, -4)

            self.assertEqual(
                tuple(life.screen.get_at(marker.topleft)[:3]),
                THEMES["colorblind"]["background"],
            )
        finally:
            life.CELL_SIZE = original_cell_size

    def test_new_general_themes_are_complete_and_age_aware(self) -> None:
        required = set(THEMES["classic"])
        for theme_name in ("midnight", "paper"):
            with self.subTest(theme=theme_name):
                self.assertEqual(set(THEMES[theme_name]), required)
                self.assertEqual(
                    get_age_color(0, theme_name),
                    THEMES[theme_name]["background"],
                )
                self.assertNotEqual(
                    get_age_color(5, theme_name),
                    THEMES[theme_name]["background"],
                )

    def test_accessible_theme_grid_and_state_colors_meet_graphical_contrast(self) -> None:
        for theme_name in ("colorblind", "midnight", "paper"):
            theme = THEMES[theme_name]
            with self.subTest(theme=theme_name):
                self.assertGreaterEqual(
                    contrast_ratio(theme["grid"], theme["background"]),
                    3.0,
                )
                self.assertGreaterEqual(
                    contrast_ratio(theme["cell"], theme["background"]),
                    3.0,
                )
        self.assertGreaterEqual(
            contrast_ratio(COLORBLIND_BLUE, COLORBLIND_YELLOW),
            3.0,
        )
        colorblind_comparison = {
            one_d_state_color(state, 4, "colorblind", secondary=secondary)
            for secondary in (False, True)
            for state in range(1, 4)
        }
        self.assertEqual(len(colorblind_comparison), 6)
        for theme_name in ("pastel", "paper"):
            primary = one_d_state_color(1, 2, theme_name)
            secondary = one_d_state_color(1, 2, theme_name, secondary=True)
            self.assertGreaterEqual(
                contrast_ratio(primary, THEMES[theme_name]["background"]),
                3.0,
            )
            self.assertGreaterEqual(
                contrast_ratio(secondary, THEMES[theme_name]["background"]),
                3.0,
            )
            self.assertGreaterEqual(contrast_ratio(primary, secondary), 3.0)

    def test_2d_fit_cell_size_matches_supported_window_sizes(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        expected = {
            (760, 560): 6,
            (1200, 720): 11,
            (1366, 768): 12,
            (1920, 1080): 18,
        }
        try:
            life.set_active_dimension("2d")
            for window_size, cell_size in expected.items():
                with self.subTest(window=window_size):
                    life.update_window_size(*window_size)
                    self.assertEqual(life.fitted_2d_cell_size(), cell_size)
        finally:
            life.update_window_size(*original_size)

    def test_fit_board_keeps_all_cells_visible_without_mutating_state(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(1200, 720)
            life.set_active_dimension("2d")
            life.grid[3][4] = 7
            generation = life.generation

            life.fit_2d_view()

            viewport = life.grid_viewport()
            origin_x, origin_y = life.grid_origin()
            board = pygame.Rect(
                origin_x,
                origin_y,
                life.COLS * life.CELL_SIZE,
                life.ROWS * life.CELL_SIZE,
            )
            self.assertTrue(viewport.contains(board))
            self.assertEqual(life.grid[3][4], 7)
            self.assertEqual(life.generation, generation)
            self.assertIn(f"{life.COLS}x{life.ROWS}", life.status_message)
        finally:
            life.update_window_size(*original_size)

    def test_resize_warns_when_preserved_2d_zoom_moves_board_offscreen(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        original_cell_size = life.CELL_SIZE
        try:
            life.set_active_dimension("2d")
            life.CELL_SIZE = 20
            life.update_window_size(760, 560)

            self.assertIn("Ctrl+0", life.status_message)
            self.assertEqual(life.CELL_SIZE, 20)
        finally:
            life.CELL_SIZE = original_cell_size
            life.update_window_size(*original_size)

    def test_recent_experiments_appear_in_session_manager_actions(self) -> None:
        life.ui_preferences.record_recent("session", "last_session", "Last Session")
        life.set_active_dimension("2d")
        life.activate_session_menu()

        entries = life.session_menu_entries()

        self.assertTrue(
            any(entry["key"] == "recent_session:last_session" for entry in entries)
        )

    def test_all_expanded_1d_comparison_sections_stay_inside_small_window(self) -> None:
        original_size = (life.WINDOW_WIDTH, life.WINDOW_HEIGHT)
        try:
            life.update_window_size(760, 560)
            life.set_active_dimension("1d")
            life.elementary_controller.state.comparison_enabled = True
            life.rebuild_context_menu()
            view = next(
                section
                for section in life.main_menu.sections
                if section["key"] == "1d_view"
            )
            if not view["expanded"]:
                life.main_menu.toggle_section("1d_view")

            self.assertTrue(
                all(
                    not data["visible"]
                    or data["button"].rect.bottom <= life.main_menu.rect.bottom
                    for data in life.main_menu.buttons
                )
            )
        finally:
            life.elementary_controller.state.comparison_enabled = False
            life.update_window_size(*original_size)


if __name__ == "__main__":
    unittest.main()
