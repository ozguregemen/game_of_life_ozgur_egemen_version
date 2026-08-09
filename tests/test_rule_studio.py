import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from custom_rules import CustomRulePackage, custom_rule_from_2d
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
        self.exported = []
        self.imported = []
        self.package_refreshes = 0
        self.current_key = None
        self.apply_succeeds = True
        self.feedback = ""
        self.template = RuleStudioTemplate(
            "HighLife",
            "B36/S23",
            "Adds birth with six neighbors.",
        )
        self.package = CustomRulePackage(
            Path("highlife-lab-2d.rule.json"),
            self.rule,
            "2026-08-09T00:00:00+00:00",
            "0.9.0",
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
            current_rule_key=lambda: self.current_key,
            templates=lambda: (self.template,),
            refresh_packages=self._refresh_packages,
            packages=lambda: (self.package,),
            package_directory=lambda: "C:/Rules",
            create_rule=self._create,
            apply_rule=self._apply,
            export_rule=self._export,
            import_rule=self._import,
            delete_rule=self._delete,
            pause=self._pause,
            feedback_text=lambda: self.feedback,
        )
        self.studio = CustomRuleStudio(services)

    def _pause(self) -> None:
        self.pauses += 1

    def _refresh_packages(self) -> None:
        self.package_refreshes += 1

    def _create(self, expression):
        self.expressions.append(expression)
        self.created.append(self.rule)
        return self.rule

    def _delete(self, rule) -> bool:
        self.deleted.append(rule)
        return True

    def _apply(self, rule) -> bool:
        self.applied.append(rule)
        return self.apply_succeeds

    def _export(self, rule) -> bool:
        self.exported.append(rule)
        return True

    def _import(self, package):
        self.imported.append(package)
        return package.rule

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
        self.assertEqual(self.package_refreshes, 1)
        self.assertEqual(self.applied, [self.rule])
        self.assertFalse(self.studio.active)

    def test_create_auto_applies_then_delete_requires_confirmation(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)
            )
            self.assertFalse(self.studio.active)
            self.studio.open()
            self.studio.view = self.studio.LIBRARY_VIEW
            layout = self.studio.geometry()
            delete_rect = layout.rows[0][3]
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=delete_rect.center,
                )
            )
            self.assertEqual(self.deleted, [])
            self.assertEqual(self.studio.pending_delete, self.rule)
            self.studio.draw()
            confirmation = self.studio.delete_confirmation_geometry(layout)
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=confirmation.confirm.center,
                )
            )

        self.assertEqual(self.created, [self.rule])
        self.assertEqual(self.expressions, [None])
        self.assertEqual(self.applied, [self.rule])
        self.assertEqual(self.deleted, [self.rule])
        self.assertIsNone(self.studio.pending_delete)
        self.assertTrue(self.studio.active)

    def test_delete_confirmation_can_be_cancelled_without_mutation(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.view = self.studio.LIBRARY_VIEW
            layout = self.studio.geometry()
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=layout.rows[0][3].center,
                )
            )
            confirmation = self.studio.delete_confirmation_geometry(layout)
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=confirmation.cancel.center,
                )
            )

        self.assertEqual(self.deleted, [])
        self.assertIsNone(self.studio.pending_delete)
        self.assertEqual(self.studio.message, "Deletion cancelled.")

    def test_active_rule_cannot_open_delete_confirmation(self) -> None:
        self.current_key = self.rule.key
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.view = self.studio.LIBRARY_VIEW
            layout = self.studio.geometry()
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=layout.rows[0][3].center,
                )
            )

        self.assertEqual(self.deleted, [])
        self.assertIsNone(self.studio.pending_delete)
        self.assertIn("active", self.studio.message)

    def test_failed_apply_keeps_studio_open_with_feedback(self) -> None:
        self.apply_succeeds = False
        self.feedback = "Rule engine rejected this recipe."
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.view = self.studio.LIBRARY_VIEW
            layout = self.studio.geometry()
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=layout.rows[0][1].center,
                )
            )

        self.assertTrue(self.studio.active)
        self.assertEqual(self.studio.message, self.feedback)

    def test_saved_rule_can_be_exported_without_applying_or_closing(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.view = self.studio.LIBRARY_VIEW
            layout = self.studio.geometry()
            share = layout.rows[0][2]
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=share.center,
                )
            )

        self.assertEqual(self.exported, [self.rule])
        self.assertEqual(self.applied, [])
        self.assertTrue(self.studio.active)

    def test_package_import_adds_rule_then_opens_library(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=()):
            self.studio.open()
            self.studio.view = self.studio.IMPORT_VIEW
            layout = self.studio.geometry()
            import_button = layout.package_rows[0][2]
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=import_button.center,
                )
            )

        self.assertEqual(self.imported, [self.package])
        self.assertEqual(self.studio.view, self.studio.LIBRARY_VIEW)
        self.assertIn("Imported", self.studio.message)
        self.assertTrue(self.studio.active)

    def test_existing_package_is_not_imported_over_catalog_rule(self) -> None:
        with patch("rule_studio.get_custom_rules", return_value=(self.rule,)):
            self.studio.open()
            self.studio.view = self.studio.IMPORT_VIEW
            layout = self.studio.geometry()
            self.studio.handle_event(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=layout.package_rows[0][1].center,
                )
            )

        self.assertEqual(self.imported, [])
        self.assertIn("already", self.studio.message)

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
            self.studio.view = self.studio.IMPORT_VIEW
            self.studio.draw()

        self.assertTrue(self.studio.active)
        self.assertFalse(self.applied)


if __name__ == "__main__":
    unittest.main()
