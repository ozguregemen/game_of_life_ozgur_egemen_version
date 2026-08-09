import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from custom_rules import custom_rule_from_2d
from rule_studio import (
    CustomRuleStudio,
    RuleStudioServices,
    RuleStudioTemplate,
)
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
        self.expressions = []
        self.template = RuleStudioTemplate(
            "HighLife",
            "B36/S23",
            "Adds birth with six neighbors.",
        )
        services = RuleStudioServices(
            screen=lambda: self.screen,
            window_size=lambda: self.screen.get_size(),
            theme=lambda: THEMES["classic"],
            large_font=lambda: pygame.font.Font(None, 30),
            small_font=lambda: pygame.font.Font(None, 22),
            tiny_font=lambda: pygame.font.Font(None, 17),
            active_dimension=lambda: "2d",
            editor_kind=lambda: "life_like",
            context_label=lambda: "Life-like B3/S23",
            current_rule_key=lambda: None,
            templates=lambda: (self.template,),
            create_rule=self._create,
            apply_rule=self.applied.append,
            delete_rule=self._delete,
            pause=self._pause,
            set_status=lambda _message, _duration: None,
            feedback_text=lambda: "",
        )
        self.studio = CustomRuleStudio(services)

    def _pause(self) -> None:
        self.pauses += 1

    def _create(self, expression):
        self.expressions.append(expression)
        self.created.append(self.rule)
        return self.rule

    def _delete(self, rule) -> bool:
        self.deleted.append(rule)
        return True

    def test_catalog_opens_paused_and_applies_selected_rule(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.view = self.studio.LIBRARY_VIEW
            layout = self.studio.geometry()
            row = layout.rows[0][1]
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

    def test_create_auto_applies_then_delete_stays_in_catalog(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)
            )
            self.assertFalse(self.studio.active)
            self.studio.open()
            self.studio.view = self.studio.LIBRARY_VIEW
            layout = self.studio.geometry()
            delete_rect = layout.rows[0][2]
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=delete_rect.center,
                )
            )

        self.assertEqual(self.created, [self.rule])
        self.assertEqual(self.expressions, [None])
        self.assertEqual(self.applied, [self.rule])
        self.assertEqual(self.deleted, [self.rule])
        self.assertTrue(self.studio.active)

    def test_template_card_prefills_expression_and_applies_rule(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=()):
            self.studio.open()
            layout = self.studio.geometry()
            template_rect = layout.templates[0][1]
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=template_rect.center,
                )
            )

        self.assertEqual(self.expressions, ["B36/S23"])
        self.assertEqual(self.applied, [self.rule])
        self.assertFalse(self.studio.active)

    def test_learn_and_library_views_render_without_mutating_rules(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.draw()
            self.studio.view = self.studio.LIBRARY_VIEW
            self.studio.draw()

        self.assertTrue(self.studio.active)
        self.assertFalse(self.applied)


if __name__ == "__main__":
    unittest.main()
