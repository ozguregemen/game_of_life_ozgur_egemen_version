import os
import random
import unittest
from unittest.mock import patch
from typing import Any, Mapping

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import life
from custom_rules import custom_rule_from_1d
from elementary_ca import BOUNDARY_INFINITE
from one_dimensional_ca import (
    FAMILY_ELEMENTARY,
    FAMILY_HIGHER_ORDER,
    FAMILY_MULTISTATE,
    default_rule_spec,
)
from scientific_analysis import StateObservation
from themes import Menu
from timeline_history import TimelineStatus
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

    def step_forward(self) -> None:
        pass

    def seek_history(self, index: int) -> bool:
        return False

    def seek_generation(self, generation: int) -> bool:
        return False

    def sync_history(self) -> bool:
        return False

    def history_status(self) -> TimelineStatus:
        return TimelineStatus(0, 1, 0, (0,), (0,), False, False, 1, 0, 0)

    def reset_history(self) -> None:
        pass

    def analysis_observation(self) -> StateObservation:
        return StateObservation(
            key="stub",
            title="Stub",
            generation=0,
            values=(0,),
            state_count=2,
            active_states=(1,),
        )

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
        life.elementary_renderer.diagram_backend = "auto"
        life.elementary_controller.reset_history()

    def tearDown(self) -> None:
        life.generation = self.original_generation
        life.elementary_renderer.diagram_backend = "auto"
        life.set_simulation_mode("life")

    def test_application_registers_both_available_dimensions(self) -> None:
        self.assertEqual(life.workspace_registry.keys, ("2d", "1d", "3d"))
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
        self.assertEqual(life.elementary_controller.history_status().frame_count, 2)

    def test_tutorial_rule_loader_restores_canonical_elementary_protocol(self) -> None:
        life.set_active_dimension("1d")
        spec = default_rule_spec(FAMILY_MULTISTATE, states=3)
        self.eca.family = spec.family
        self.eca.rule = spec.code
        self.eca.states = spec.states
        self.eca.radius = spec.radius
        self.eca.rule_change_reset = False
        self.eca.comparison_enabled = True

        life.elementary_controller.load_canonical_elementary_rule(184)

        self.assertEqual(self.eca.family, FAMILY_ELEMENTARY)
        self.assertEqual(self.eca.rule, 184)
        self.assertEqual(self.eca.states, 2)
        self.assertEqual(self.eca.radius, 1)
        self.assertEqual(self.eca.boundary, BOUNDARY_INFINITE)
        self.assertTrue(self.eca.rule_change_reset)
        self.assertFalse(self.eca.comparison_enabled)
        self.assertEqual(self.eca.generation, 0)
        self.assertEqual(sum(self.eca.rows[0]), 1)

    def test_custom_1d_rule_restores_embedded_recipe_from_snapshot(self) -> None:
        life.set_active_dimension("1d")
        custom = custom_rule_from_1d(
            "Named Rule 110",
            life.elementary_controller.rule_spec.with_code(110),
        )

        life.elementary_controller.apply_custom_rule(custom)
        snapshot = life.elementary_controller.snapshot()
        life.elementary_controller.set_rule(30)
        life.elementary_controller.restore(snapshot)

        self.assertEqual(life.elementary_controller.state.custom_rule, custom)
        self.assertEqual(life.elementary_controller.rule_spec.code, 110)


    def test_multistate_family_uses_selected_brush_and_valid_states(self) -> None:
        life.set_active_dimension("1d")
        spec = default_rule_spec(FAMILY_MULTISTATE, states=3)
        self.eca.family = spec.family
        self.eca.rule = spec.code
        self.eca.states = spec.states
        self.eca.radius = spec.radius
        self.eca.brush_state = 2
        life.elementary_controller.use_single_seed()

        editor = life.elementary_controller.editor_rect()
        column = len(self.eca.rows[-1]) // 2 + 1
        position = (
            editor.x + column * self.eca.cell_size + 1,
            editor.centery,
        )
        life.elementary_controller.handle_pointer_event(
            life.pygame.event.Event(
                life.pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=position,
            )
        )
        life.elementary_controller.handle_pointer_event(
            life.pygame.event.Event(
                life.pygame.MOUSEBUTTONUP,
                button=1,
                pos=position,
            )
        )

        self.assertEqual(self.eca.rows[-1][column], 2)
        self.assertTrue(life.elementary_controller.advance())
        self.assertTrue(set(self.eca.rows[-1]).issubset({0, 1, 2}))

    def test_side_by_side_comparison_advances_two_rules_from_one_seed(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rule = 30
        self.eca.comparison_rule = 90
        life.elementary_controller.toggle_comparison()

        for _ in range(5):
            life.elementary_controller.advance()

        self.assertEqual(len(self.eca.rows), len(self.eca.comparison_rows))
        self.assertNotEqual(self.eca.rows, self.eca.comparison_rows)
        panes = life.elementary_controller.diagram_panes()
        self.assertEqual(len(panes), 2)
        self.assertLess(panes[0].right, panes[1].left)

    def test_elementary_catalog_can_target_only_the_comparison_rule(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rule = 30
        self.eca.comparison_rule = 90
        self.eca.comparison_enabled = True

        life.elementary_controller.open_comparison_rule_menu()
        life.elementary_controller._set_catalog_rule(110)

        self.assertEqual(self.eca.rule, 30)
        self.assertEqual(self.eca.comparison_rule, 110)
        self.assertEqual(self.eca.rows, [self.eca.seed])

    def test_multistate_renderer_draws_without_binary_assumptions(self) -> None:
        life.set_active_dimension("1d")
        spec = default_rule_spec(FAMILY_MULTISTATE, states=3)
        self.eca.family = spec.family
        self.eca.rule = spec.code
        self.eca.states = spec.states
        self.eca.radius = spec.radius
        self.eca.rows = [(0, 1, 2, 0)]
        self.eca.seed = self.eca.rows[0]
        self.eca.previous_row = (0, 0, 0, 0)
        self.eca.comparison_rows = list(self.eca.rows)
        self.eca.comparison_previous_row = self.eca.previous_row

        life.elementary_renderer.draw_base()
        life.elementary_renderer.draw_bars()

    def test_large_1d_diagram_uses_surfarray_without_visual_changes(self) -> None:
        life.set_active_dimension("1d")
        original_theme = life.current_theme
        original_grid = life.show_grid
        rng = random.Random(47)
        width = 121
        row_count = 36
        self.eca.cell_size = 6
        self.eca.rows = [
            tuple(1 if rng.random() < 0.38 else 0 for _ in range(width))
            for _ in range(row_count)
        ]
        self.eca.row_backgrounds = [
            int(index % 7 == 0) for index in range(row_count)
        ]
        self.eca.seed = self.eca.rows[0]
        self.eca.previous_row = (0,) * width
        self.eca.comparison_rows = list(self.eca.rows)
        self.eca.comparison_row_backgrounds = list(self.eca.row_backgrounds)
        self.eca.comparison_previous_row = self.eca.previous_row
        try:
            life.current_theme = "classic"
            life.show_grid = False
            life.elementary_controller.center_view()

            life.screen.fill(life.THEMES["classic"]["background"])
            life.elementary_renderer.diagram_backend = "rects"
            life.elementary_renderer.draw_base()
            legacy_pixels = pygame.surfarray.array3d(life.screen)

            life.screen.fill(life.THEMES["classic"]["background"])
            life.elementary_renderer.diagram_backend = "auto"
            life.elementary_renderer.draw_base()
            bulk_pixels = pygame.surfarray.array3d(life.screen)

            self.assertEqual(
                life.elementary_renderer.last_diagram_backend,
                "surfarray",
            )
            self.assertTrue((legacy_pixels == bulk_pixels).all())
        finally:
            life.current_theme = original_theme
            life.show_grid = original_grid

    def test_surfarray_backend_falls_back_for_half_cell_row_alignment(self) -> None:
        life.set_active_dimension("1d")
        self.eca.rows = [(0, 1, 0), (0, 1, 1, 0)]
        self.eca.row_backgrounds = [0, 0]
        self.eca.comparison_rows = list(self.eca.rows)
        self.eca.comparison_row_backgrounds = [0, 0]
        life.elementary_controller.center_view()
        life.elementary_renderer.diagram_backend = "surfarray"

        life.elementary_renderer.draw_base()

        self.assertEqual(life.elementary_renderer.last_diagram_backend, "rects")

    def test_higher_order_memory_round_trips_through_timeline(self) -> None:
        life.set_active_dimension("1d")
        spec = default_rule_spec(FAMILY_HIGHER_ORDER)
        self.eca.family = spec.family
        self.eca.rule = spec.code
        self.eca.states = spec.states
        self.eca.radius = spec.radius
        self.eca.rows = [(0, 1, 1, 0, 1)]
        self.eca.seed = self.eca.rows[-1]
        self.eca.previous_row = (1, 0, 1, 0, 0)
        self.eca.comparison_rows = list(self.eca.rows)
        self.eca.comparison_previous_row = self.eca.previous_row
        life.elementary_controller.reset_history()
        life.elementary_controller.advance()
        life.elementary_controller.advance()
        expected_rows = list(self.eca.rows)
        expected_previous = self.eca.previous_row

        life.elementary_controller.step_back()
        life.elementary_controller.step_forward()

        self.assertEqual(self.eca.rows, expected_rows)
        self.assertEqual(self.eca.previous_row, expected_previous)


if __name__ == "__main__":
    unittest.main()
