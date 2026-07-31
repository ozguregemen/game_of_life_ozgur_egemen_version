import unittest
from math import isclose

import numpy as np

from three_dimensional_ca import Volume3D
from three_dimensional_display import framebuffer_rgb_array
from three_dimensional_rendering import (
    CAMERA_FACE_DIRECTIONS,
    OrbitCamera3D,
    VoxelRenderSettings,
    look_at_matrix,
    perspective_matrix,
    pick_voxel,
    orientation_cube_face_at,
    orientation_cube_faces,
    transparent_order_key,
    voxel_is_visible,
    volume_position_to_world,
    voxel_instance_data,
    voxel_render_instance_data,
)


class FramebufferCaptureTests(unittest.TestCase):
    def test_bottom_up_opengl_bytes_become_top_down_rgb(self) -> None:
        bottom_row = bytes((255, 0, 0, 0, 255, 0))
        top_row = bytes((0, 0, 255, 9, 8, 7))

        pixels = framebuffer_rgb_array(bottom_row + top_row, (2, 2))

        self.assertEqual(tuple(pixels[0, 0]), (0, 0, 255))
        self.assertEqual(tuple(pixels[1, 0]), (255, 0, 0))
        self.assertTrue(pixels.flags["C_CONTIGUOUS"])

    def test_framebuffer_byte_count_is_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "payload"):
            framebuffer_rgb_array(b"bad", (2, 2))


class Camera3DTests(unittest.TestCase):
    def test_camera_reset_orbit_pan_and_zoom_preserve_valid_geometry(self) -> None:
        camera = OrbitCamera3D()
        camera.reset_for_shape((24, 32, 32))
        original_eye = camera.eye.copy()
        original_distance = camera.distance

        camera.orbit(20, -10)
        self.assertFalse(np.allclose(camera.eye, original_eye))
        self.assertTrue(
            isclose(
                float(np.linalg.norm(camera.eye - camera.target)),
                camera.distance,
                abs_tol=1e-5,
            )
        )
        camera.pan(15, 8, 600)
        self.assertFalse(np.allclose(camera.target, np.zeros(3)))
        camera.zoom(1.25)
        self.assertLess(camera.distance, original_distance)

    def test_center_screen_ray_points_at_orbit_target(self) -> None:
        camera = OrbitCamera3D(target=np.asarray((2.0, -1.0, 3.0), dtype=np.float32))
        origin, direction = camera.screen_ray((400, 300), (0, 0, 800, 600))

        expected = camera.target - origin
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(direction, expected, atol=1e-5)

    def test_projection_and_view_matrices_reject_invalid_inputs(self) -> None:
        self.assertEqual(perspective_matrix(45, 1.5, 0.1, 100).shape, (4, 4))
        self.assertEqual(
            look_at_matrix(
                np.asarray((0, 0, 5), dtype=np.float32),
                np.zeros(3, dtype=np.float32),
            ).shape,
            (4, 4),
        )
        with self.assertRaises(ValueError):
            perspective_matrix(45, 0, 0.1, 100)
        with self.assertRaisesRegex(ValueError, "field of view"):
            OrbitCamera3D(fov_y=180)

    def test_transparent_sort_bucket_ignores_zoom_pan_and_tiny_orbits(self) -> None:
        camera = OrbitCamera3D()
        original = transparent_order_key(camera, 12)

        camera.zoom(1.2)
        camera.pan(20, 10, 600)
        self.assertEqual(transparent_order_key(camera, 12), original)

        camera.orbit(0.1, 0.0)
        self.assertEqual(transparent_order_key(camera, 12), original)
        camera.orbit(30.0, 0.0)
        self.assertNotEqual(transparent_order_key(camera, 12), original)
        self.assertNotEqual(transparent_order_key(camera, 13), original)

    def test_camera_snaps_each_volume_face_toward_the_viewer(self) -> None:
        camera = OrbitCamera3D()
        for face, expected in CAMERA_FACE_DIRECTIONS.items():
            with self.subTest(face=face):
                camera.snap_to_face(face)
                eye_direction = camera.eye - camera.target
                eye_direction /= np.linalg.norm(eye_direction)
                np.testing.assert_allclose(eye_direction, expected, atol=1e-6)
                self.assertTrue(np.all(np.isfinite(camera.right)))
                self.assertTrue(np.all(np.isfinite(camera.up)))

    def test_orientation_cube_hit_testing_selects_front_face(self) -> None:
        camera = OrbitCamera3D()
        camera.snap_to_face("front")
        rect = (20, 30, 96, 96)
        faces = orientation_cube_faces(camera, rect)

        self.assertEqual([face.key for face in faces], ["front"])
        self.assertEqual(
            orientation_cube_face_at(camera, rect, (68, 78)),
            "front",
        )
        self.assertIsNone(orientation_cube_face_at(camera, rect, (20, 30)))


class VoxelGeometryTests(unittest.TestCase):
    def test_render_settings_validate_filter_and_opacity(self) -> None:
        settings = VoxelRenderSettings(
            mode="clip",
            axis="y",
            layer=4,
            keep_lower=False,
            opacity=0.65,
        )
        self.assertEqual(settings.axis, "y")
        self.assertEqual(settings.color_scheme, "state")
        self.assertEqual(settings.lighting, "studio")
        with self.assertRaises(ValueError):
            VoxelRenderSettings(mode="unknown")
        with self.assertRaises(ValueError):
            VoxelRenderSettings(opacity=0.0)
        with self.assertRaises(ValueError):
            VoxelRenderSettings(color_scheme="unknown")
        with self.assertRaises(ValueError):
            VoxelRenderSettings(lighting="unknown")
        with self.assertRaises(ValueError):
            VoxelRenderSettings(outline=0.5)
        with self.assertRaises(ValueError):
            VoxelRenderSettings(voxel_scale=0.1)
        with self.assertRaises(ValueError):
            VoxelRenderSettings(occlusion=1.5)

    def test_instance_data_centers_volume_and_keeps_states(self) -> None:
        volume = Volume3D.empty((3, 5, 7), state_count=3)
        volume.set_cell((1, 2, 3), 2)
        volume.set_cell((0, 0, 0), 1)

        data = voxel_instance_data(volume)

        self.assertEqual(data.shape, (2, 4))
        self.assertTrue(any(np.allclose(row, (-3.0, 2.0, -1.0, 1.0)) for row in data))
        self.assertTrue(any(np.allclose(row, (0.0, 0.0, 0.0, 2.0)) for row in data))
        np.testing.assert_allclose(
            volume_position_to_world((1, 2, 3), volume.shape),
            (0.0, 0.0, 0.0),
        )

    def test_render_instance_data_includes_local_occupancy(self) -> None:
        volume = Volume3D.empty((3, 3, 3), state_count=3)
        volume.set_cell((1, 1, 1), 1)
        volume.set_cell((1, 1, 2), 2)

        data = voxel_render_instance_data(volume)

        self.assertEqual(data.shape, (2, 5))
        np.testing.assert_allclose(data[:, 4], (2 / 27, 2 / 27))

    def test_dda_picking_returns_hit_and_adjacent_empty_voxel(self) -> None:
        volume = Volume3D.empty((3, 3, 3))
        volume.set_cell((1, 1, 1), 1)

        result = pick_voxel(volume, (0, 0, 10), (0, 0, -1))

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.hit, (1, 1, 1))
        self.assertEqual(result.adjacent, (2, 1, 1))

    def test_dda_picking_handles_misses_and_boundary_hits(self) -> None:
        volume = Volume3D.empty((3, 3, 3))
        volume.set_cell((2, 1, 1), 1)

        boundary = pick_voxel(volume, (0, 0, 10), (0, 0, -1))
        miss = pick_voxel(volume, (10, 10, 10), (1, 0, 0))

        self.assertIsNotNone(boundary)
        assert boundary is not None
        self.assertEqual(boundary.hit, (2, 1, 1))
        self.assertIsNone(boundary.adjacent)
        self.assertIsNone(miss)

    def test_layer_filter_hides_voxels_from_ray_picking_too(self) -> None:
        volume = Volume3D.empty((3, 3, 3))
        volume.set_cell((2, 1, 1), 1)
        volume.set_cell((1, 1, 1), 1)
        settings = VoxelRenderSettings(mode="layer", axis="z", layer=1)

        result = pick_voxel(volume, (0, 0, 10), (0, 0, -1), settings)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.hit, (1, 1, 1))
        self.assertIsNone(result.adjacent)
        self.assertFalse(voxel_is_visible((2, 1, 1), settings))
        self.assertTrue(voxel_is_visible((1, 1, 1), settings))


if __name__ == "__main__":
    unittest.main()
