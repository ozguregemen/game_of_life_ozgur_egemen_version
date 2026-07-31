import os
import unittest
from dataclasses import replace

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from themes import Menu
from three_dimensional_patterns import BAYS_5766_GLIDER
from three_dimensional_rendering import orientation_cube_faces
from three_dimensional_modes import MODE_GENERATIONS, MODE_SPATIAL_LIFE
from workspaces.three_dimensional import (
    DEFAULT_VOLUME_SHAPE,
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
        self.tutorial_opens = 0

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
            activate_tutorial=lambda: setattr(
                self, "tutorial_opens", self.tutorial_opens + 1
            ),
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
        self.assertIn("Tutorial: 3D & Mode Guide (F2)", labels)
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
        renderer.draw_decorations()
        self.assertEqual(len(rendered), 1)
        menu = Menu(700, 42, 200, 608, "classic")
        controller.build_sidebar(menu)
        labels = [entry["button"].text for entry in menu.buttons]
        self.assertIn("Fit Full Volume (Ctrl+0)", labels)
        self.assertFalse(any(label.startswith("Axis:") for label in labels))
        self.assertTrue(any(label.startswith("Display:") for label in labels))
        self.assertTrue(any(label.startswith("Coloring:") for label in labels))
        self.assertTrue(any(label.startswith("Lighting:") for label in labels))
        self.assertTrue(any(label.startswith("Outline:") for label in labels))

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

        controller.seed_cluster()
        cells_before = controller.state.volume.cells.copy()
        cube_rect = controller.orientation_cube_face_rect()
        faces = orientation_cube_faces(
            controller.state.camera,
            (cube_rect.x, cube_rect.y, cube_rect.width, cube_rect.height),
        )
        face = faces[-1]
        face_center = (
            round(sum(point[0] for point in face.polygon) / 4),
            round(sum(point[1] for point in face.polygon) / 4),
        )
        controller.handle_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=face_center)
        )
        controller.handle_pointer_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=face_center)
        )
        expected = np.asarray(
            {
                "front": (0, 0, 1),
                "back": (0, 0, -1),
                "right": (1, 0, 0),
                "left": (-1, 0, 0),
                "top": (0, 1, 0),
                "bottom": (0, -1, 0),
            }[face.key],
            dtype=np.float32,
        )
        eye_direction = controller.state.camera.eye - controller.state.camera.target
        eye_direction /= np.linalg.norm(eye_direction)
        np.testing.assert_allclose(eye_direction, expected, atol=1e-6)
        np.testing.assert_array_equal(controller.state.volume.cells, cells_before)
        self.assertIn("Camera aligned", self.messages[-1])

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
        controller.cycle_color_scheme()
        controller.cycle_lighting()
        controller.cycle_outline()
        controller.cycle_voxel_scale()
        controller.cycle_occlusion()
        snapshot = controller.snapshot()

        restored = ThreeDimensionalWorkspaceController(
            hardware_services,
            ThreeDimensionalWorkspaceState(),
        )
        restored.restore(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)
        self.assertEqual(restored.render_settings().mode, "clip")
        self.assertEqual(restored.render_settings().opacity, 0.65)
        self.assertEqual(restored.render_settings().color_scheme, "xyz")
        self.assertEqual(restored.render_settings().lighting, "soft")
        self.assertEqual(restored.render_settings().outline, 0.10)
        self.assertEqual(restored.render_settings().voxel_scale, 0.92)
        self.assertEqual(restored.render_settings().occlusion, 0.0)

    def test_generations_is_a_distinct_playable_mode_with_multistate_history(self) -> None:
        self.controller.set_mode(MODE_GENERATIONS)

        self.assertEqual(self.controller.state.mode_key, MODE_GENERATIONS)
        self.assertEqual(self.controller.state.rule_key, "generations_445")
        self.assertEqual(self.controller.state.volume.state_count, 5)
        self.assertGreater(int(np.count_nonzero(self.controller.state.volume.cells)), 0)
        initial = self.controller.snapshot()

        self.controller.advance()

        self.assertEqual(self.controller.generation, 1)
        self.assertTrue(
            set(np.unique(self.controller.state.volume.cells)).issubset({0, 1, 2, 3, 4})
        )
        self.controller.step_back()
        self.assertEqual(self.controller.snapshot(), initial)

        self.controller.cycle_rule()
        self.assertEqual(self.controller.state.rule_key, "generations_3d_brain")
        self.assertEqual(self.controller.state.volume.state_count, 2)
        self.controller.cycle_mode()
        self.assertEqual(self.controller.state.mode_key, MODE_SPATIAL_LIFE)
        self.assertEqual(self.controller.state.volume.state_count, 2)

    def test_generations_snapshot_restores_mode_rule_and_refractory_states(self) -> None:
        self.controller.set_mode(MODE_GENERATIONS)
        self.controller.state.volume.set_cell((3, 4, 5), 4)
        snapshot = self.controller.snapshot()

        restored = ThreeDimensionalWorkspaceController(
            self.controller.services,
            ThreeDimensionalWorkspaceState(),
        )
        restored.restore(snapshot)

        self.assertEqual(restored.state.mode_key, MODE_GENERATIONS)
        self.assertEqual(restored.state.volume.state_count, 5)
        self.assertEqual(restored.state.volume.get_cell((3, 4, 5)), 4)
        self.assertEqual(restored.snapshot(), snapshot)

    def test_export_snapshot_uses_compact_immutable_volume_bytes(self) -> None:
        snapshot = self.controller.export_snapshot()

        self.assertIsInstance(snapshot["cells"], bytes)
        self.assertEqual(len(snapshot["cells"]), self.controller.state.volume.cell_count)
        before = snapshot["cells"]
        self.controller.state.volume.set_cell((0, 0, 0), 1)
        self.assertEqual(snapshot["cells"], before)

    def test_export_snapshot_rebuilds_an_isolated_render_volume(self) -> None:
        self.controller.state.volume.set_cell((2, 3, 4), 1)
        snapshot = self.controller.export_snapshot()

        exported = self.controller.volume_from_export_snapshot(snapshot)
        exported.set_cell((2, 3, 4), 0)

        self.assertEqual(exported.shape, self.controller.state.volume.shape)
        self.assertEqual(exported.neighborhood, self.controller.rule.neighborhood)
        self.assertEqual(self.controller.state.volume.get_cell((2, 3, 4)), 1)

    def test_volume_presets_are_cubic_and_resizing_is_timeline_reversible(self) -> None:
        self.assertEqual(self.controller.state.volume.shape, DEFAULT_VOLUME_SHAPE)
        self.assertEqual(DEFAULT_VOLUME_SHAPE, (48, 48, 48))
        original = self.controller.snapshot()

        self.controller.cycle_volume_shape()

        self.assertEqual(self.controller.state.volume.shape, (64, 64, 64))
        self.assertEqual(self.controller.generation, 0)
        self.controller.step_back()
        self.assertEqual(self.controller.snapshot(), original)


if __name__ == "__main__":
    unittest.main()
