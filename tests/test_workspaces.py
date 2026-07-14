import os
import unittest
from unittest.mock import patch
from typing import Any, Mapping

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import life
from themes import Menu
from workspaces.base import (
    WorkspaceBundle,
    WorkspaceController,
    WorkspaceRegistry,
    WorkspaceRenderer,
)
from workspaces.elementary_1d import (
    ElementaryWorkspaceController,
    ElementaryWorkspaceRenderer,
    ElementaryWorkspaceState,
)
from workspaces.two_dimensional import (
    TwoDimensionalWorkspaceController,
    TwoDimensionalWorkspaceRenderer,
)


class StubController(WorkspaceController):
    key = "stub"

    @property
    def generation(self) -> int:
        return 0

    def advance(self) -> bool:
        return True

    def save_history(self) -> None:
        pass

    def step_back(self) -> None:
        pass

    def clear(self) -> None:
        pass

    def randomize(self, density: float = 0.20) -> None:
        pass

    def snapshot(self) -> dict[str, Any]:
        return {}

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        pass

    def build_sidebar(self, menu: Menu) -> None:
        pass

    def center_view(self) -> None:
        pass

    def zoom(self, factor: float) -> None:
        pass


class StubRenderer(WorkspaceRenderer):
    render_key = "stub:test"

    def cache_key(self) -> tuple[object, ...]:
        return ()

    def draw_base(self) -> None:
        pass

    def draw_bars(self) -> None:
        pass


class OtherRenderer(StubRenderer):
    render_key = "other:test"


class WorkspaceRegistryTests(unittest.TestCase):
    def test_registers_and_retrieves_a_workspace_bundle(self) -> None:
        registry = WorkspaceRegistry()
        workspace = WorkspaceBundle(StubController(), StubRenderer())

        registry.register(workspace)

        self.assertEqual(registry.keys, ("stub",))
        self.assertIs(registry.get("stub"), workspace)

    def test_rejects_duplicate_workspace_keys(self) -> None:
        registry = WorkspaceRegistry()
        workspace = WorkspaceBundle(StubController(), StubRenderer())
        registry.register(workspace)

        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(workspace)

    def test_rejects_mismatched_controller_and_renderer(self) -> None:
        with self.assertRaisesRegex(ValueError, "do not match"):
            WorkspaceBundle(StubController(), OtherRenderer())

    def test_unknown_workspace_has_a_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown workspace"):
            WorkspaceRegistry().get("missing")


class ApplicationWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_generation = life.generation
        self.eca = ElementaryWorkspaceState()
        life.elementary_controller.state = self.eca
        life.elementary_state = self.eca

    def tearDown(self) -> None:
        life.generation = self.original_generation
        life.set_simulation_mode("life")

    def test_application_registers_both_available_dimensions(self) -> None:
        self.assertEqual(life.workspace_registry.keys, ("2d", "1d"))
        self.assertIsInstance(
            life.workspace_registry.get("2d").controller,
            TwoDimensionalWorkspaceController,
        )
        self.assertIsInstance(
            life.workspace_registry.get("2d").renderer,
            TwoDimensionalWorkspaceRenderer,
        )
        self.assertIsInstance(
            life.workspace_registry.get("1d").controller,
            ElementaryWorkspaceController,
        )
        self.assertIsInstance(
            life.workspace_registry.get("1d").renderer,
            ElementaryWorkspaceRenderer,
        )

    def test_active_workspace_follows_dimension_selection(self) -> None:
        life.set_active_dimension("1d")
        self.assertEqual(life.active_workspace().controller.key, "1d")

        life.set_active_dimension("2d")
        self.assertEqual(life.active_workspace().controller.key, "2d")

    def test_generation_counter_is_exposed_by_the_common_interface(self) -> None:
        self.eca.generation = 12
        life.set_active_dimension("1d")
        self.assertEqual(life.active_workspace().controller.generation, 12)

        life.generation = 7
        life.set_active_dimension("2d")
        self.assertEqual(life.active_workspace().controller.generation, 7)

    def test_shared_generation_entry_point_uses_active_controller(self) -> None:
        with patch.object(
            life.two_dimensional_controller,
            "advance",
            return_value=True,
        ) as advance:
            life.set_active_dimension("2d")
            self.assertTrue(life.apply_generation())
        advance.assert_called_once_with()

    def test_workspace_specific_key_is_delegated_to_elementary_controller(self) -> None:
        life.set_active_dimension("1d")

        life.handle_keydown(
            life.pygame.event.Event(life.pygame.KEYDOWN, key=life.pygame.K_e)
        )

        self.assertTrue(self.eca.rule_menu_active)

    def test_pointer_event_is_delegated_to_elementary_controller(self) -> None:
        life.set_active_dimension("1d")
        editor = life.elementary_controller.editor_rect()
        position = (editor.x + self.eca.cell_size // 2, editor.centery)

        life.handle_event(
            life.pygame.event.Event(
                life.pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=position,
            )
        )
        life.handle_event(
            life.pygame.event.Event(
                life.pygame.MOUSEBUTTONUP,
                button=1,
                pos=position,
            )
        )

        self.assertEqual(self.eca.rows[-1][0], 1)
        self.assertEqual(len(self.eca.undo_history), 1)


if __name__ == "__main__":
    unittest.main()
