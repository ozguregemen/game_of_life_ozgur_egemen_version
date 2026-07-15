import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

from surface_rasterizer import StateGridRasterizer
from three_dimensional_ca import AXIS_X, Volume3D


class StateGridRasterizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def setUp(self) -> None:
        self.target = pygame.Surface((12, 10), depth=32)
        self.rasterizer = StateGridRasterizer(max_cached_sizes=2)
        self.palette = ((3, 5, 7), (11, 13, 17), (19, 23, 29))

    def test_blit_preserves_row_column_orientation_and_integer_scaling(self) -> None:
        states = np.array(((0, 1), (2, 0)), dtype=np.uint8)

        changed = self.rasterizer.blit(
            self.target,
            states,
            self.palette,
            (2, 1),
            cell_size=3,
        )

        self.assertEqual(changed, pygame.Rect(2, 1, 6, 6))
        self.assertEqual(tuple(self.target.get_at((2, 1))[:3]), self.palette[0])
        self.assertEqual(tuple(self.target.get_at((5, 1))[:3]), self.palette[1])
        self.assertEqual(tuple(self.target.get_at((2, 4))[:3]), self.palette[2])
        self.assertEqual(tuple(self.target.get_at((5, 4))[:3]), self.palette[0])

    def test_reuses_scratch_surfaces_for_repeated_dimensions(self) -> None:
        states = np.zeros((3, 4), dtype=np.uint8)

        self.rasterizer.blit(self.target, states, self.palette, (0, 0), cell_size=2)
        first_count = self.rasterizer.cached_surface_count
        self.rasterizer.blit(self.target, states, self.palette, (1, 1), cell_size=2)

        self.assertEqual(first_count, 2)
        self.assertEqual(self.rasterizer.cached_surface_count, first_count)

    def test_blits_a_zero_copy_noncontiguous_3d_slice(self) -> None:
        volume = Volume3D.empty((2, 2, 2), state_count=3)
        volume.write_slice(AXIS_X, 1, ((0, 1), (2, 0)))
        plane = volume.extract_slice(AXIS_X, 1, copy=False)

        self.rasterizer.blit(
            self.target,
            plane,
            self.palette,
            (0, 0),
            cell_size=2,
        )

        self.assertFalse(plane.flags.c_contiguous)
        self.assertFalse(plane.flags.writeable)
        self.assertEqual(tuple(self.target.get_at((2, 0))[:3]), self.palette[1])
        self.assertEqual(tuple(self.target.get_at((0, 2))[:3]), self.palette[2])

    def test_rejects_invalid_grid_palette_and_scale(self) -> None:
        with self.assertRaisesRegex(ValueError, "rectangular 2D"):
            self.rasterizer.blit(
                self.target,
                ((0,), (1, 0)),
                self.palette,
                (0, 0),
            )
        with self.assertRaisesRegex(ValueError, "outside the palette"):
            self.rasterizer.blit(
                self.target,
                ((3,),),
                self.palette,
                (0, 0),
            )
        with self.assertRaisesRegex(ValueError, "RGB"):
            self.rasterizer.blit(
                self.target,
                ((0,),),
                ((0, 0),),
                (0, 0),
            )
        with self.assertRaisesRegex(ValueError, "cell_size"):
            self.rasterizer.blit(
                self.target,
                ((0,),),
                self.palette,
                (0, 0),
                cell_size=0,
            )


if __name__ == "__main__":
    unittest.main()
