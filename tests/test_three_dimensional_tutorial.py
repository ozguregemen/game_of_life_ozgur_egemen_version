"""Tests for the shared and active-mode three-dimensional tutorial."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from three_dimensional_modes import MODE_KEYS_3D
from three_dimensional_tutorial import (
    ThreeDimensionalTutorial,
    ThreeDimensionalTutorialServices,
)
from three_dimensional_tutorial_content import (
    THREE_D_FOUNDATION_PAGES,
    THREE_D_MODE_GUIDES,
)


class ThreeDimensionalTutorialTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.Surface((1200, 720))
        self.size = [1200, 720]
        self.mode = ["spatial_life"]
        self.pauses = 0
        self.experiments: list[str] = []
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
        self.tutorial = ThreeDimensionalTutorial(
            ThreeDimensionalTutorialServices(
                screen=lambda: self.screen,
                window_size=lambda: tuple(self.size),
                theme=lambda: self.theme,
                current_mode=lambda: self.mode[0],
                current_rule_label=lambda: "Bays 5766 · B6/S567 · 26 neighbors",
                open_url=self._open_url,
                start_experiment=self.experiments.append,
                pause=self._pause,
                set_status=lambda message, duration: self.statuses.append(message),
            )
        )

    def _pause(self) -> None:
        self.pauses += 1

    def _open_url(self, url: str) -> bool:
        self.opened_urls.append(url)
        return True

    def test_curriculum_covers_every_registered_3d_mode_separately(self) -> None:
        self.assertEqual(set(THREE_D_MODE_GUIDES), set(MODE_KEYS_3D))
        self.assertEqual(len(THREE_D_FOUNDATION_PAGES), 7)
        self.assertEqual(
            {mode: len(guide.pages) for mode, guide in THREE_D_MODE_GUIDES.items()},
            {"spatial_life": 8, "generations": 9},
        )
        self.assertTrue(all(guide.sources for guide in THREE_D_MODE_GUIDES.values()))
        self.assertTrue(
            all(guide.pages[-1].kind == "mode_sources" for guide in THREE_D_MODE_GUIDES.values())
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

    def test_tab_key_switches_between_foundations_and_active_mode(self) -> None:
        self.tutorial.open()

        self.tutorial.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertEqual(self.tutorial.tab, self.tutorial.MODE)
        self.assertEqual(self.tutorial.mode_tab_label, "MODE: SPATIAL LIFE")

        self.tutorial.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertEqual(self.tutorial.tab, self.tutorial.FOUNDATIONS)

    def test_finishing_foundations_continues_to_only_the_active_mode(self) -> None:
        self.mode[0] = "generations"
        self.tutorial.open()
        self.tutorial.foundation_page = len(THREE_D_FOUNDATION_PAGES) - 1

        self.tutorial.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))

        self.assertEqual(self.tutorial.tab, self.tutorial.MODE)
        self.assertEqual(self.tutorial.mode_page, 0)
        self.assertEqual(self.tutorial.guide.name, "3D Generations")

    def test_mode_change_replaces_contextual_guide_and_resets_page(self) -> None:
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.mode_page = 3
        self.mode[0] = "generations"
        self.tutorial.open()

        self.assertEqual(self.tutorial.mode_page, 0)
        self.assertEqual(self.tutorial.mode_tab_label, "MODE: 3D GENERATIONS")
        self.assertNotIn("Bays", self.tutorial.page.title)

    def test_every_page_draws_at_desktop_and_compact_sizes(self) -> None:
        self.tutorial.open()
        for size in ((1200, 720), (760, 560)):
            self.size[:] = size
            self.screen = pygame.Surface(size)
            self.tutorial.select_tab(self.tutorial.FOUNDATIONS)
            for page_index in range(len(THREE_D_FOUNDATION_PAGES)):
                self.tutorial.page_index = page_index
                self.tutorial.scroll = 0
                self.tutorial.draw()
                self.assertGreater(self.tutorial.content_height, 0)
            for mode in MODE_KEYS_3D:
                self.mode[0] = mode
                self.tutorial.select_tab(self.tutorial.MODE)
                for page_index in range(len(THREE_D_MODE_GUIDES[mode].pages)):
                    self.tutorial.page_index = page_index
                    self.tutorial.scroll = 0
                    self.tutorial.draw()
                    self.assertEqual(self.tutorial.guide, THREE_D_MODE_GUIDES[mode])

    def test_source_page_contains_only_the_active_mode_references(self) -> None:
        self.mode[0] = "generations"
        self.tutorial.open()
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.page_index = next(
            index for index, page in enumerate(self.tutorial.pages) if page.kind == "mode_sources"
        )

        self.tutorial.draw()

        local_urls = {
            payload
            for action, payload, _ in self.tutorial._local_interactions
            if action == "url"
        }
        expected = {source.url for source in THREE_D_MODE_GUIDES["generations"].sources}
        other = {source.url for source in THREE_D_MODE_GUIDES["spatial_life"].sources}
        self.assertEqual(local_urls, expected)
        self.assertTrue(local_urls.isdisjoint(other - expected))

    def test_source_button_uses_external_link_callback(self) -> None:
        self.tutorial.open()
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.page_index = next(
            index for index, page in enumerate(self.tutorial.pages) if page.kind == "mode_sources"
        )
        self.tutorial.draw()
        _, expected_url, rect = self.tutorial._interactions[0]

        self.tutorial.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        )

        self.assertEqual(self.opened_urls, [expected_url])
        self.assertTrue(self.statuses)

    def test_experiment_action_closes_tutorial_and_starts_matching_mode(self) -> None:
        self.mode[0] = "spatial_life"
        self.tutorial.open()
        self.tutorial.select_tab(self.tutorial.MODE)
        self.tutorial.page_index = next(
            index
            for index, page in enumerate(self.tutorial.pages)
            if page.kind == "mode_experiment_3d"
        )
        self.tutorial.draw()
        _, payload, rect = next(
            item for item in self.tutorial._interactions if item[0] == "experiment"
        )

        self.tutorial.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        )

        self.assertEqual(payload, "spatial_life")
        self.assertFalse(self.tutorial.active)
        self.assertEqual(self.experiments, ["spatial_life"])


if __name__ == "__main__":
    unittest.main()
