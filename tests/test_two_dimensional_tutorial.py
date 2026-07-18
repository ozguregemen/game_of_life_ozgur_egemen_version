"""Tests for the shared and active-mode two-dimensional tutorial."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from mode_registry import MODE_KEYS
from two_dimensional_tutorial import (
    TwoDimensionalTutorial,
    TwoDimensionalTutorialServices,
)
from two_dimensional_tutorial_content import FOUNDATION_PAGES, MODE_GUIDES


class TwoDimensionalTutorialTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.Surface((1200, 720))
        self.size = [1200, 720]
        self.mode = ["life"]
        self.pauses = 0
        self.pattern_opens = 0
        self.opened_urls: list[str] = []
        self.statuses: list[str] = []
        self.theme = {
            "background": (5, 10, 16),
            "info_bar": (18, 29, 42),
            "stats_bar": (14, 24, 35),
            "button": (35, 48, 61),
            "button_hover": (51, 72, 91),
            "button_text": (238, 242, 247),
            "text": (238, 242, 247),
            "menu_text": (185, 198, 210),
            "grid": (76, 91, 105),
            "cell": (75, 195, 245),
        }
        self.tutorial = TwoDimensionalTutorial(
            TwoDimensionalTutorialServices(
                screen=lambda: self.screen,
                window_size=lambda: tuple(self.size),
                theme=lambda: self.theme,
                current_mode=lambda: self.mode[0],
                current_rule_label=lambda: "Conway's Game of Life · B3/S23",
                open_url=self._open_url,
                open_patterns=self._open_patterns,
                pause=self._pause,
                set_status=lambda message, duration: self.statuses.append(message),
            )
        )

    def _pause(self) -> None:
        self.pauses += 1

    def _open_patterns(self) -> None:
        self.pattern_opens += 1

    def _open_url(self, url: str) -> bool:
        self.opened_urls.append(url)
        return True

    def test_curriculum_covers_every_registered_mode_without_combining_them(self) -> None:
        self.assertEqual(set(MODE_GUIDES), set(MODE_KEYS))
        self.assertEqual(len(FOUNDATION_PAGES), 6)
        self.assertEqual(
            {mode: len(guide.pages) for mode, guide in MODE_GUIDES.items()},
            {
                "life": 6,
                "immigration": 7,
                "brians_brain": 7,
                "langtons_ant": 7,
                "wireworld": 8,
                "cyclic_automaton": 7,
            },
        )
        self.assertTrue(all(guide.sources for guide in MODE_GUIDES.values()))
        self.assertTrue(
            all(
                {"mode_states", "mode_rule_primary", "mode_rule_secondary"}
                <= {page.kind for page in guide.pages}
                for guide in MODE_GUIDES.values()
            )
        )

    def test_explicit_open_pauses_and_starts_in_foundations(self) -> None:
        self.tutorial.open()

        self.assertTrue(self.tutorial.active)
        self.assertEqual(self.tutorial.tab, self.tutorial.FOUNDATIONS)
        self.assertEqual(self.pauses, 1)

    def test_modal_uses_nearly_the_entire_window_and_has_two_tabs(self) -> None:
        modal, viewport, close, back, next_button, tabs = self.tutorial.geometry()

        self.assertGreaterEqual(modal.width, self.size[0] - 30)
        self.assertGreaterEqual(modal.height, self.size[1] - 30)
        self.assertTrue(modal.contains(viewport))
        self.assertTrue(modal.contains(close))
        self.assertTrue(modal.contains(back))
        self.assertTrue(modal.contains(next_button))
        self.assertEqual(len(tabs), 2)
        self.assertFalse(tabs[0].colliderect(tabs[1]))

    def test_tab_key_switches_between_shared_and_active_mode_guides(self) -> None:
        self.tutorial.open()

        self.tutorial.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
        )
        self.assertEqual(self.tutorial.tab, self.tutorial.MODE)
        self.assertEqual(self.tutorial.mode_tab_label, "MODE: LIFE-LIKE")

        self.tutorial.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
        )
        self.assertEqual(self.tutorial.tab, self.tutorial.FOUNDATIONS)

    def test_finishing_foundations_continues_to_only_the_active_mode(self) -> None:
        self.mode[0] = "wireworld"
        self.tutorial.open()
        self.tutorial.foundation_page = len(FOUNDATION_PAGES) - 1

        self.tutorial.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        )

        self.assertEqual(self.tutorial.tab, self.tutorial.MODE)
        self.assertEqual(self.tutorial.mode_page, 0)
        self.assertEqual(self.tutorial.guide.name, "Wireworld")

    def test_mode_change_replaces_contextual_guide_and_resets_its_page(self) -> None:
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.mode_page = 3
        self.mode[0] = "brians_brain"
        self.tutorial.open()

        self.assertEqual(self.tutorial.mode_page, 0)
        self.assertEqual(self.tutorial.mode_tab_label, "MODE: BRIAN'S BRAIN")
        self.assertNotIn("Wireworld", self.tutorial.page.title)

    def test_every_page_draws_for_every_mode_at_desktop_and_compact_sizes(self) -> None:
        self.tutorial.open()
        for size in ((1200, 720), (760, 560)):
            self.size[:] = size
            self.screen = pygame.Surface(size)
            self.tutorial.select_tab(self.tutorial.FOUNDATIONS)
            for page_index in range(len(FOUNDATION_PAGES)):
                self.tutorial.page_index = page_index
                self.tutorial.scroll = 0
                self.tutorial.draw()
                self.assertGreater(self.tutorial.content_height, 0)
            for mode in MODE_KEYS:
                self.mode[0] = mode
                self.tutorial.select_tab(self.tutorial.MODE)
                for page_index in range(len(MODE_GUIDES[mode].pages)):
                    self.tutorial.page_index = page_index
                    self.tutorial.scroll = 0
                    self.tutorial.draw()
                    self.assertEqual(self.tutorial.guide, MODE_GUIDES[mode])

    def test_source_page_contains_only_the_active_mode_references(self) -> None:
        self.mode[0] = "langtons_ant"
        self.tutorial.open()
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.page_index = next(
            index
            for index, page in enumerate(self.tutorial.pages)
            if page.kind == "mode_sources"
        )

        self.tutorial.draw()

        local_urls = {
            payload
            for action, payload, _ in self.tutorial._local_interactions
            if action == "url"
        }
        self.assertEqual(local_urls, {source.url for source in MODE_GUIDES["langtons_ant"].sources})
        self.assertTrue(local_urls.isdisjoint({source.url for source in MODE_GUIDES["wireworld"].sources}))

    def test_source_button_uses_explicit_external_link_callback(self) -> None:
        self.mode[0] = "brians_brain"
        self.tutorial.open()
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.page_index = next(
            index
            for index, page in enumerate(self.tutorial.pages)
            if page.kind == "mode_sources"
        )
        self.tutorial.draw()
        _, expected_url, rect = self.tutorial._interactions[0]

        self.tutorial.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        )

        self.assertEqual(self.opened_urls, [expected_url])
        self.assertTrue(self.statuses)

    def test_experiment_action_closes_tutorial_and_opens_mode_patterns(self) -> None:
        self.mode[0] = "immigration"
        self.tutorial.open()
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.page_index = next(
            index
            for index, page in enumerate(self.tutorial.pages)
            if page.kind == "mode_experiment"
        )
        self.tutorial.draw()
        _, viewport, _, _, _, _ = self.tutorial.geometry()
        self.tutorial.scroll = self.tutorial._maximum_scroll(viewport)
        self.tutorial.draw()
        _, payload, rect = next(
            item for item in self.tutorial._interactions if item[0] == "patterns"
        )

        self.tutorial.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        )

        self.assertEqual(payload, "immigration")
        self.assertFalse(self.tutorial.active)
        self.assertEqual(self.pattern_opens, 1)


if __name__ == "__main__":
    unittest.main()
