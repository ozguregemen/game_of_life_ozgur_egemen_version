"""Tests for the full-screen, visual 1D tutorial."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from tutorial_ui import (
    ONE_D_TUTORIAL_PAGES,
    RULE_EXAMPLES,
    TUTORIAL_SOURCES,
    OneDimensionalTutorial,
    TutorialServices,
)


class OneDimensionalTutorialTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.Surface((1200, 720))
        self.size = [1200, 720]
        self.rule = 30
        self.pauses = 0
        self.applied: list[int] = []
        self.opened_urls: list[str] = []
        self.statuses: list[str] = []
        self.large = pygame.font.SysFont("Arial", 24)
        self.small = pygame.font.SysFont("Arial", 16)
        self.tiny = pygame.font.SysFont("Arial", 13)
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
        self.tutorial = OneDimensionalTutorial(
            TutorialServices(
                screen=lambda: self.screen,
                window_size=lambda: tuple(self.size),
                theme=lambda: self.theme,
                large_font=lambda: self.large,
                small_font=lambda: self.small,
                tiny_font=lambda: self.tiny,
                current_rule=lambda: self.rule,
                apply_canonical_rule=self.applied.append,
                open_url=self._open_url,
                pause=self._pause,
                set_status=lambda message, duration: self.statuses.append(message),
            )
        )

    def _pause(self) -> None:
        self.pauses += 1

    def _open_url(self, url: str) -> bool:
        self.opened_urls.append(url)
        return True

    def test_curriculum_has_ordered_visual_lessons_and_sources(self) -> None:
        self.assertEqual(len(ONE_D_TUTORIAL_PAGES), 7)
        self.assertEqual(
            [page.kind for page in ONE_D_TUTORIAL_PAGES],
            [
                "space_time",
                "timeline",
                "rule_table",
                "boundaries",
                "examples",
                "families",
                "sources",
            ],
        )
        self.assertTrue(all(len(page.sections) == 4 for page in ONE_D_TUTORIAL_PAGES[:2]))
        self.assertEqual({rule for rule, _, _ in RULE_EXAMPLES}, {30, 90, 110, 184})
        self.assertGreaterEqual(len(TUTORIAL_SOURCES), 5)
        self.assertTrue(all(source.url.startswith("https://") for source in TUTORIAL_SOURCES))

    def test_explicit_open_pauses_without_resetting_progress(self) -> None:
        self.tutorial.page_index = 4

        self.tutorial.open()

        self.assertTrue(self.tutorial.active)
        self.assertEqual(self.tutorial.page_index, 4)
        self.assertEqual(self.pauses, 1)

    def test_modal_uses_nearly_the_entire_window(self) -> None:
        modal, viewport, close, back, next_button = self.tutorial.geometry()

        self.assertGreaterEqual(modal.width, self.size[0] - 30)
        self.assertGreaterEqual(modal.height, self.size[1] - 30)
        self.assertTrue(modal.contains(viewport))
        self.assertTrue(modal.contains(close))
        self.assertTrue(modal.contains(back))
        self.assertTrue(modal.contains(next_button))

    def test_keyboard_navigation_is_bounded_and_finish_closes(self) -> None:
        self.tutorial.page_index = 0
        self.tutorial.open()
        self.tutorial.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        )
        self.assertEqual(self.tutorial.page_index, 0)

        for _ in range(self.tutorial.page_count - 1):
            self.tutorial.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
            )
        self.assertEqual(self.tutorial.page_index, self.tutorial.page_count - 1)

        self.tutorial.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        )
        self.assertFalse(self.tutorial.active)

    def test_rule_90_visual_is_generated_from_the_actual_rule(self) -> None:
        rows = self.tutorial._eca_rows(90, 7, 4)

        self.assertEqual(rows[0], (0, 0, 0, 1, 0, 0, 0))
        self.assertEqual(rows[1], (0, 0, 1, 0, 1, 0, 0))
        self.assertEqual(rows[2], (0, 1, 0, 0, 0, 1, 0))
        self.assertEqual(rows[3], (1, 0, 1, 0, 1, 0, 1))

    def test_custom_seed_is_centered_to_the_requested_preview_width(self) -> None:
        padded = self.tutorial._eca_rows(184, 9, 2, seed=(1, 0, 1), wrap=True)
        cropped = self.tutorial._eca_rows(
            184, 9, 2, seed=tuple(range(11)), wrap=True
        )

        self.assertEqual(padded[0], (0, 0, 0, 1, 0, 1, 0, 0, 0))
        self.assertTrue(all(len(row) == 9 for row in padded))
        self.assertTrue(all(len(row) == 9 for row in cropped))

    def test_every_page_draws_at_desktop_and_compact_sizes(self) -> None:
        self.tutorial.open()
        for size in ((1200, 720), (760, 560)):
            self.size[:] = size
            self.screen = pygame.Surface(size)
            for page_index in range(self.tutorial.page_count):
                self.tutorial.page_index = page_index
                self.tutorial.scroll = 0
                self.tutorial.draw()
                self.assertGreater(self.tutorial.content_height, 0)

    def test_landmark_rule_button_applies_rule_and_returns_to_lab(self) -> None:
        self.tutorial.open()
        self.tutorial.page_index = 4
        self.tutorial.draw()
        action, payload, rect = next(
            item
            for item in self.tutorial._interactions
            if item[0] == "rule" and item[1] == "30"
        )

        self.tutorial.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        )

        self.assertEqual(action, "rule")
        self.assertEqual(payload, "30")
        self.assertEqual(self.applied, [30])
        self.assertFalse(self.tutorial.active)

    def test_source_button_uses_explicit_external_link_callback(self) -> None:
        self.tutorial.open()
        self.tutorial.page_index = 6
        self.tutorial.draw()
        _, expected_url, rect = self.tutorial._interactions[0]

        self.tutorial.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        )

        self.assertEqual(self.opened_urls, [expected_url])
        self.assertTrue(self.tutorial.active)
        self.assertTrue(self.statuses)

    def test_compact_source_page_scrolls_without_overflow(self) -> None:
        self.size[:] = [760, 560]
        self.screen = pygame.Surface(tuple(self.size))
        self.tutorial.open()
        self.tutorial.page_index = 6

        self.tutorial.draw()
        _, viewport, _, _, _ = self.tutorial.geometry()

        self.assertGreater(self.tutorial.content_height, viewport.height)
        self.tutorial.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1))
        self.assertGreater(self.tutorial.scroll, 0)


if __name__ == "__main__":
    unittest.main()
