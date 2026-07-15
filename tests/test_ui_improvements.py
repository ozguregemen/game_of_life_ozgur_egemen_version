"""Tests for navigation, accessibility, favorites, and recent experiments."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import life
from themes import THEMES, Menu
from ui_preferences import UIPreferences


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
        life.ui_preferences.favorite_rules.clear()
        life.ui_preferences.recent_experiments.clear()

    def tearDown(self) -> None:
        life.help_panel.close()
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
        self.assertEqual(len(set(life.COLORBLIND_CYCLIC_PALETTE)), 8)
        self.assertEqual(
            life.export_coordinator.palette()[life.ELECTRON_TAIL],
            (213, 94, 0),
        )

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
