"""Reusable NumPy-to-Pygame rendering for dense cellular state planes."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from typing import TypeAlias

import numpy as np
import pygame

RGBColor: TypeAlias = tuple[int, int, int]
SurfaceKey: TypeAlias = tuple[
    tuple[int, int],
    int,
    tuple[int, int, int, int],
]


class StateGridRasterizer:
    """Blit a 2D state array through a palette using reusable surfaces.

    Simulation arrays use the conventional ``(row, column)`` layout. Pygame's
    surfarray API expects ``(x, y, color)``, so the palette result is presented
    with its first two axes swapped before it is copied to the logical surface.
    Nearest-neighbour scaling preserves crisp cellular pixels.
    """

    def __init__(self, max_cached_sizes: int = 4) -> None:
        if max_cached_sizes < 1:
            raise ValueError("max_cached_sizes must be positive.")
        self.max_cached_sizes = max_cached_sizes
        self._logical_surfaces: OrderedDict[SurfaceKey, pygame.Surface] = (
            OrderedDict()
        )
        self._scaled_surfaces: OrderedDict[SurfaceKey, pygame.Surface] = (
            OrderedDict()
        )

    @staticmethod
    def _surface_key(
        size: tuple[int, int],
        target: pygame.Surface,
    ) -> SurfaceKey:
        return size, target.get_bitsize(), target.get_masks()

    def _surface_for(
        self,
        cache: OrderedDict[SurfaceKey, pygame.Surface],
        size: tuple[int, int],
        target: pygame.Surface,
    ) -> pygame.Surface:
        key = self._surface_key(size, target)
        surface = cache.get(key)
        if surface is not None:
            cache.move_to_end(key)
            return surface
        surface = pygame.Surface(
            size,
            depth=target.get_bitsize(),
            masks=target.get_masks(),
        )
        cache[key] = surface
        if len(cache) > self.max_cached_sizes:
            cache.popitem(last=False)
        return surface

    @staticmethod
    def _validated_palette(colors: Sequence[RGBColor]) -> np.ndarray:
        try:
            palette = np.asarray(colors, dtype=np.int16)
        except (TypeError, ValueError) as exc:
            raise ValueError("Palette must contain RGB integer triples.") from exc
        if palette.ndim != 2 or palette.shape[0] < 1 or palette.shape[1] != 3:
            raise ValueError("Palette must contain at least one RGB color.")
        if np.any(palette < 0) or np.any(palette > 255):
            raise ValueError("Palette channels must be between 0 and 255.")
        return palette.astype(np.uint8, copy=False)

    @staticmethod
    def _validated_states(
        states: np.ndarray | Sequence[Sequence[int]],
        palette_size: int,
    ) -> np.ndarray:
        try:
            state_array = np.asarray(states)
        except (TypeError, ValueError) as exc:
            raise ValueError("State grid must be a rectangular 2D array.") from exc
        if state_array.ndim != 2 or 0 in state_array.shape:
            raise ValueError("State grid must be a non-empty 2D array.")
        if not (
            np.issubdtype(state_array.dtype, np.integer)
            or np.issubdtype(state_array.dtype, np.bool_)
        ):
            raise TypeError("State grid values must be integers.")
        if np.any(state_array < 0) or np.any(state_array >= palette_size):
            raise ValueError("State grid contains a value outside the palette.")
        return state_array

    def blit(
        self,
        target: pygame.Surface,
        states: np.ndarray | Sequence[Sequence[int]],
        palette: Sequence[RGBColor],
        destination: tuple[int, int],
        *,
        cell_size: int = 1,
    ) -> pygame.Rect:
        """Palette-map ``states`` and draw them onto ``target`` in one batch."""
        if cell_size < 1:
            raise ValueError("cell_size must be positive.")
        palette_array = self._validated_palette(palette)
        state_array = self._validated_states(states, len(palette_array))
        rows, columns = state_array.shape
        logical = self._surface_for(
            self._logical_surfaces,
            (columns, rows),
            target,
        )
        rgb_rows = palette_array[state_array]
        pygame.surfarray.blit_array(logical, rgb_rows.swapaxes(0, 1))

        if cell_size == 1:
            return target.blit(logical, destination)

        scaled_size = (columns * cell_size, rows * cell_size)
        scaled = self._surface_for(self._scaled_surfaces, scaled_size, target)
        pygame.transform.scale(logical, scaled_size, scaled)
        return target.blit(scaled, destination)

    def clear(self) -> None:
        """Release cached scratch surfaces, for example after a display reset."""
        self._logical_surfaces.clear()
        self._scaled_surfaces.clear()

    @property
    def cached_surface_count(self) -> int:
        """Return the number of retained logical and scaled scratch surfaces."""
        return len(self._logical_surfaces) + len(self._scaled_surfaces)
