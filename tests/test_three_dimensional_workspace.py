import os
import unittest
from dataclasses import replace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from themes import Menu
from three_dimensional_patterns import BAYS_5766_GLIDER
from workspaces.three_dimensional import (
    THREE_D_RENDER_KEY,
    ThreeDimensionalWorkspaceController,
    ThreeDimensionalWorkspaceRenderer,
    ThreeDimensionalWorkspaceServices,
    ThreeDimensionalWorkspaceState,
)


class ThreeDimensionalWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def setUp(self) -> None:
        self.screen = pygame.Surface((900, 650))
        self.viewport = pygame.Rect(0, 42, 700, 500)
        self.running = False
        self.grid = True
        self.theme = "classic"
        self.revisions = {THREE_D_RENDER_KEY: 0}
        self.messages: list[str] = []
        self.analysis = []

        def invalidate(key: str) -> None:
            self.revisions[key] += 1

        services = ThreeDimensionalWorkspaceServices(
            viewport=lambda: self.viewport,
            screen=lambda: self.screen,
            window_size=lambda: self.screen.get_size(),
            theme_name=lambda: self.theme,
            is_running=lambda: self.running,
            speed=lambda: 10,
            show_grid=lambda: self.grid,
            set_running=lambda value: setattr(self, "running", value),
            set_status=lambda message, _duration: self.messages.append(message),
            invalidate=invalidate,
            rebuild_sidebar=lambda: None,
            activate_dimension_menu=lambda: None,
            activate_session_menu=lambda: None,
            activate_analysis=lambda: None,
            activate_help=lambda: None,
            toggle_grid=lambda: setattr(self, "grid", not self.grid),
            cycle_theme=lambda: None,
            cached_stats=lambda _key, calculator: calculator(),
            render_revision=lambda key: self.revisions[key],
            large_font=lambda: pygame.font.Font(None, 28),
            small_font=lambda: pygame.font.Font(None, 20),
            tiny_font=lambda: pygame.font.Font(None, 16),
            menu_width=200,
            info_bar_height=42,
            stats_height=68,
            grid_top_margin=8,
            record_analysis=self.analysis.append,
            reset_analysis=lambda observation: self.analysis.append(observation),
        )
        self.controller = ThreeDimensionalWorkspaceController(
            services,
            ThreeDimensionalWorkspaceState(),
        )
        self.renderer = ThreeDimensionalWorkspaceRenderer(self.controller, services)
        self.controller.center_view()

    def test_seed_advance_and_timeline_navigation_are_playable(self) -> None:
        self.controller.seed_cluster()
        seeded = self.controller.state.volume.cells.copy()

        self.assertTrue(self.controller.advance())
        self.assertEqual(self.controller.generation, 1)
        self.assertEqual(self.controller.history_status().frame_count, 3)

        self.controller.step_back()
        self.assertEqual(self.controller.generation, 0)
        self.assertTrue((self.controller.state.volume.cells == seeded).all())
        self.controller.step_forward()
        self.assertEqual(self.controller.generation, 1)

    def test_slice_axis_navigation_and_pointer_editing_map_to_volume(self) -> None:
        self.controller.state.slice_axis = "z"
        self.controller.state.slice_index = 3
        self.controller.center_view()
        rect = self.controller.slice_rect()
        point = (
            rect.x + 2 * self.controller.state.cell_size + 1,
            rect.y + self.controller.state.cell_size + 1,
        )

        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)
        self.controller.handle_pointer_event(down)
        self.controller.handle_pointer_event(up)

        self.assertEqual(self.controller.state.volume.get_cell((3, 1, 2)), 1)
        self.assertEqual(self.controller.history_status().frame_count, 2)
        self.controller.cycle_axis()
        self.assertEqual(self.controller.state.slice_axis, "y")
        self.controller.move_slice(10_000)
        self.assertEqual(
            self.controller.state.slice_index,
            self.controller.slice_count() - 1,
        )

    def test_snapshot_round_trip_preserves_volume_rule_slice_and_camera(self) -> None:
        self.controller.randomize(0.12)
        self.controller.cycle_boundary()
        self.controller.cycle_axis()
        self.controller.move_slice(2)
        snapshot = self.controller.snapshot()

        restored = ThreeDimensionalWorkspaceController(
            self.controller.services,
            ThreeDimensionalWorkspaceState(),
        )
        restored.restore(snapshot)

        self.assertEqual(restored.snapshot(), snapshot)

    def test_renderer_draws_all_axes_and_sidebar_without_surface_errors(self) -> None:
        menu = Menu(700, 42, 200, 608, "classic")
        for axis in ("z", "y", "x"):
            with self.subTest(axis=axis):
                self.controller.state.slice_axis = axis
                self.controller.state.slice_index = 0
                self.controller.center_view()
                self.renderer.draw_base()
                self.renderer.draw_bars()
        self.controller.build_sidebar(menu)
        labels = [entry["button"].text for entry in menu.buttons]
        self.assertIn("Session Save / Load (P)", labels)
        self.assertTrue(any(label.startswith("Rule: B") for label in labels))
        self.assertTrue(any(label.startswith("Axis:") for label in labels))

    def test_hardware_renderer_and_orbit_voxel_controls_use_world_space(self) -> None:
        rendered: list[tuple[object, object]] = []
        services = replace(
            self.controller.services,
            hardware_3d=lambda: True,
            render_volume=lambda volume, _camera, _viewport, _revision, _settings, selected: (
                rendered.append((volume, selected)) or True
            ),
        )
        controller = ThreeDimensionalWorkspaceController(
            services,
            ThreeDimensionalWorkspaceState(),
        )
        renderer = ThreeDimensionalWorkspaceRenderer(controller, services)
        controller.seed_cluster()
        renderer.draw_base()
        self.assertEqual(len(rendered), 1)
        menu = Menu(700, 42, 200, 608, "classic")
        controller.build_sidebar(menu)
        labels = [entry["button"].text for entry in menu.buttons]
        self.assertIn("Fit Full Volume (Ctrl+0)", labels)
        self.assertFalse(any(label.startswith("Axis:") for label in labels))
        self.assertTrue(any(label.startswith("Display:") for label in labels))

        center = self.viewport.center
        initial_yaw = controller.state.camera.yaw
        controller.handle_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=center)
        )
        controller.handle_pointer_event(
            pygame.event.Event(
                pygame.MOUSEMOTION,
                pos=(center[0] + 20, center[1] + 4),
                rel=(20, 4),
                buttons=(1, 0, 0),
            )
        )
        controller.handle_pointer_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONUP,
                button=1,
                pos=(center[0] + 20, center[1] + 4),
            )
        )
        self.assertNotEqual(controller.state.camera.yaw, initial_yaw)

        controller.center_view()
        hit = controller._pick_at(center)
        self.assertIsNotNone(hit)
        before = int((controller.state.volume.cells != 0).sum())
        controller.handle_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=center)
        )
        self.assertEqual(int((controller.state.volume.cells != 0).sum()), before - 1)

    def test_view_filters_and_documented_glider_are_session_persistent(self) -> None:
        hardware_services = replace(
            self.controller.services,
            hardware_3d=lambda: True,
        )
        controller = ThreeDimensionalWorkspaceController(
            hardware_services,
            ThreeDimensionalWorkspaceState(),
        )
        controller.seed_pattern(BAYS_5766_GLIDER)
        self.assertEqual(controller.state.rule_key, "bays_5766")
        self.assertEqual(controller.state.volume.boundary, "wrap")
        self.assertEqual(int((controller.state.volume.cells != 0).sum()), 10)

        controller.cycle_view_mode()
        controller.cycle_axis()
        controller.move_slice(2)
        controller.toggle_clip_side()
        controller.cycle_opacity()
        snapshot = controller.snapshot()

        restored = ThreeDimensionalWorkspaceController(
            hardware_services,
            ThreeDimensionalWorkspaceState(),
        )
        restored.restore(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)
        self.assertEqual(restored.render_settings().mode, "clip")
        self.assertEqual(restored.render_settings().opacity, 0.65)


if __name__ == "__main__":
    unittest.main()
