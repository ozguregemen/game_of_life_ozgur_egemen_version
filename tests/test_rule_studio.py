import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from custom_rules import custom_rule_from_2d
from rule_studio import CustomRuleStudio, RuleStudioServices
from themes import THEMES


class CustomRuleStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def setUp(self) -> None:
        self.screen = pygame.Surface((900, 650))
        self.rule = custom_rule_from_2d("HighLife Lab", "B36/S23")
        self.pauses = 0
        self.applied = []
        self.deleted = []
        self.created = []
        services = RuleStudioServices(
            screen=lambda: self.screen,
            window_size=lambda: self.screen.get_size(),
            theme=lambda: THEMES["classic"],
            large_font=lambda: pygame.font.Font(None, 30),
            small_font=lambda: pygame.font.Font(None, 22),
            tiny_font=lambda: pygame.font.Font(None, 17),
            active_dimension=lambda: "2d",
            context_label=lambda: "Life-like B3/S23",
            current_rule_key=lambda: None,
            create_rule=self._create,
            apply_rule=self.applied.append,
            delete_rule=self._delete,
            pause=self._pause,
            set_status=lambda _message, _duration: None,
        )
        self.studio = CustomRuleStudio(services)

    def _pause(self) -> None:
        self.pauses += 1

    def _create(self):
        self.created.append(self.rule)
        return self.rule

    def _delete(self, rule) -> bool:
        self.deleted.append(rule)
        return True

    def test_catalog_opens_paused_and_applies_selected_rule(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            _modal, _close, _create, rows, _capacity = self.studio.geometry()
            row = rows[0][1]
            handled = self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=row.center,
                )
            )

        self.assertTrue(handled)
        self.assertEqual(self.pauses, 1)
        self.assertEqual(self.applied, [self.rule])
        self.assertFalse(self.studio.active)

    def test_create_and_delete_actions_stay_in_contextual_catalog(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)
            )
            _modal, _close, _create, rows, _capacity = self.studio.geometry()
            delete_rect = rows[0][2]
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=delete_rect.center,
                )
            )

        self.assertEqual(self.created, [self.rule])
        self.assertEqual(self.deleted, [self.rule])
        self.assertTrue(self.studio.active)


if __name__ == "__main__":
    unittest.main()
