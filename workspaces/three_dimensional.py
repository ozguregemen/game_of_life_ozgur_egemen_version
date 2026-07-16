"""Playable hardware-rendered workspace for multiple 3D automata families."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np
import pygame

from dimension_registry import DIMENSION_BY_KEY
from scientific_analysis import StateObservation
from surface_rasterizer import StateGridRasterizer
from themes import THEMES, Menu
from three_dimensional_ca import (
    AXIS_X,
    AXIS_Y,
    AXIS_Z,
    BOUNDARY_MODES,
    NEIGHBORHOODS_3D,
    SLICE_AXES,
    Volume3D,
)
from three_dimensional_patterns import BAYS_5766_GLIDER, Pattern3D
from three_dimensional_generations import GenerationsRule3D, step_generations_3d
from three_dimensional_modes import (
    ALL_RULES_3D,
    DEFAULT_RULE_BY_MODE_3D,
    MODE_GENERATIONS,
    MODE_KEYS_3D,
    MODE_LABELS_3D,
    MODE_SPATIAL_LIFE,
    RULES_BY_MODE_3D,
    Rule3D,
    mode_for_rule,
    rule_state_count,
)
from three_dimensional_rules import (
    DEFAULT_RULE_3D,
    FACE_LIFE,
    LifeLikeRule3D,
    step_life_like_3d,
)
from three_dimensional_rendering import (
    FILTER_MODES,
    OrbitCamera3D,
    VoxelRenderSettings,
    pick_voxel,
    voxel_is_visible,
)
from timeline_history import TimelineBinding, TimelineStatus
from workspaces.base import WorkspaceController, WorkspaceRenderer

THREE_D_RENDER_KEY = "3d:life_like"
VOLUME_SHAPES_3D = (
    (32, 32, 32),
    (48, 48, 48),
    (64, 64, 64),
)
VOLUME_SHAPE_LABELS_3D = {
    (32, 32, 32): "Small · 32³",
    (48, 48, 48): "Medium · 48³",
    (64, 64, 64): "Large · 64³",
}
DEFAULT_VOLUME_SHAPE = (48, 48, 48)
THREE_D_MIN_CELL_SIZE = 2
THREE_D_MAX_CELL_SIZE = 24
THREE_D_TIMELINE_FRAMES = 300
THREE_D_OPACITIES = (1.0, 0.65, 0.35)
THREE_D_VIEW_LABELS = {
    "all": "Full Volume",
    "clip": "Clipping Plane",
    "layer": "Single Layer",
}


def _new_default_volume() -> Volume3D:
    return Volume3D.empty(
        DEFAULT_VOLUME_SHAPE,
        neighborhood=DEFAULT_RULE_3D.neighborhood,
    )


def _new_default_camera() -> OrbitCamera3D:
    camera = OrbitCamera3D()
    camera.reset_for_shape(DEFAULT_VOLUME_SHAPE)
    return camera


@dataclass
class ThreeDimensionalWorkspaceState:
    """Persistent simulation, orbit-camera, and interaction state."""

    volume: Volume3D = field(default_factory=_new_default_volume)
    mode_key: str = MODE_SPATIAL_LIFE
    rule_key: str = DEFAULT_RULE_3D.key
    generation: int = 0
    slice_axis: str = AXIS_Z
    slice_index: int = DEFAULT_VOLUME_SHAPE[0] // 2
    cell_size: int = 8
    view_offset_x: int = 0
    view_offset_y: int = 0
    camera: OrbitCamera3D = field(default_factory=_new_default_camera)
    selected_voxel: tuple[int, int, int] | None = None
    pointer_button: int = 0
    pointer_origin: tuple[int, int] | None = None
    pointer_dragged: bool = False
    view_mode: str = "all"
    clip_keep_lower: bool = True
    voxel_opacity: float = 1.0
    brush_state: int = 1
    drawing: bool = False
    drawing_value: int = 1
    stroke_history_pending: bool = False
    rng: random.Random = field(default_factory=random.Random)


@dataclass(frozen=True)
class ThreeDimensionalWorkspaceServices:
    """Application services consumed by the 3D controller and renderer."""

    viewport: Callable[[], pygame.Rect]
    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    theme_name: Callable[[], str]
    is_running: Callable[[], bool]
    speed: Callable[[], int]
    show_grid: Callable[[], bool]
    set_running: Callable[[bool], None]
    set_status: Callable[[str, float], None]
    invalidate: Callable[[str], None]
    rebuild_sidebar: Callable[[], None]
    activate_dimension_menu: Callable[[], None]
    activate_session_menu: Callable[[], None]
    activate_analysis: Callable[[], None]
    activate_help: Callable[[], None]
    toggle_grid: Callable[[], None]
    cycle_theme: Callable[[], None]
    cached_stats: Callable[[str, Callable[[], dict[str, Any]]], dict[str, Any]]
    render_revision: Callable[[str], int]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    menu_width: int
    info_bar_height: int
    stats_height: int
    grid_top_margin: int
    record_analysis: Callable[[StateObservation], None]
    reset_analysis: Callable[[StateObservation], None]
    hardware_3d: Callable[[], bool] = lambda: False
    render_volume: Callable[
        [
            Volume3D,
            OrbitCamera3D,
            pygame.Rect,
            int,
            VoxelRenderSettings,
            tuple[int, int, int] | None,
        ],
        bool,
    ] = lambda _volume, _camera, _viewport, _revision, _settings, _selected: False


class ThreeDimensionalWorkspaceController(WorkspaceController):
    """Own 3D simulation state, orbit navigation, history, and editing."""

    key = "3d"

    def __init__(
        self,
        services: ThreeDimensionalWorkspaceServices,
        state: ThreeDimensionalWorkspaceState | None = None,
    ) -> None:
        self.services = services
        self.state = state if state is not None else ThreeDimensionalWorkspaceState()
        self.timeline = TimelineBinding(
            self._timeline_snapshot,
            self._restore_timeline_snapshot,
            lambda: self.state.generation,
            checkpoint_interval=25,
            max_frames=THREE_D_TIMELINE_FRAMES,
        )

    @property
    def generation(self) -> int:
        return self.state.generation

    @property
    def rule(self) -> Rule3D:
        return ALL_RULES_3D[self.state.rule_key]

    @property
    def mode_label(self) -> str:
        return MODE_LABELS_3D[self.state.mode_key]

    def _status(self, message: str, duration: float = 2.5) -> None:
        self.services.set_status(message, duration)

    def _invalidate(self) -> None:
        self.services.invalidate(THREE_D_RENDER_KEY)

    def activate(self) -> None:
        self.services.set_running(False)
        if self.services.hardware_3d():
            self.state.selected_voxel = None
        else:
            self.center_view()

    def deactivate(self) -> None:
        self.state.drawing = False
        self.state.stroke_history_pending = False
        self.state.pointer_button = 0
        self.state.pointer_origin = None
        self.state.pointer_dragged = False

    def slice_count(self, axis: str | None = None) -> int:
        selected = self.state.slice_axis if axis is None else axis
        return self.state.volume.shape[SLICE_AXES.index(selected)]

    def current_slice(self) -> np.ndarray:
        """Return the current read-only renderer plane."""
        return self.state.volume.extract_slice(
            self.state.slice_axis,
            self.state.slice_index,
            copy=False,
        )

    def slice_origin(self) -> tuple[int, int]:
        viewport = self.services.viewport()
        return (
            viewport.x + self.state.view_offset_x,
            viewport.y + self.services.grid_top_margin + self.state.view_offset_y,
        )

    def slice_rect(self) -> pygame.Rect:
        rows, columns = self.state.volume.slice_shape(self.state.slice_axis)
        return pygame.Rect(
            self.slice_origin(),
            (columns * self.state.cell_size, rows * self.state.cell_size),
        )

    def center_view(self) -> None:
        if self.services.hardware_3d():
            self.state.camera.reset_for_shape(self.state.volume.shape)
            self.state.selected_voxel = None
            return
        viewport = self.services.viewport()
        rows, columns = self.state.volume.slice_shape(self.state.slice_axis)
        width = columns * self.state.cell_size
        height = rows * self.state.cell_size
        self.state.view_offset_x = (viewport.width - width) // 2
        self.state.view_offset_y = (
            viewport.height - self.services.grid_top_margin - height
        ) // 2
        self._invalidate()

    def fit_view(self) -> None:
        """Fit the full volume, or the fallback slice, into the viewport."""
        if self.services.hardware_3d():
            self.center_view()
            self._status("3D camera fitted to the complete volume.")
            return
        viewport = self.services.viewport()
        rows, columns = self.state.volume.slice_shape(self.state.slice_axis)
        available_height = max(1, viewport.height - self.services.grid_top_margin)
        size = min(viewport.width // columns, available_height // rows)
        self.state.cell_size = max(
            THREE_D_MIN_CELL_SIZE,
            min(THREE_D_MAX_CELL_SIZE, size),
        )
        self.center_view()
        self._status(f"3D slice fitted at {self.state.cell_size}px per cell.")

    def zoom(self, factor: float) -> None:
        if self.services.hardware_3d():
            self.state.camera.zoom(factor)
            return
        new_size = int(round(self.state.cell_size * factor))
        new_size = max(
            THREE_D_MIN_CELL_SIZE,
            min(THREE_D_MAX_CELL_SIZE, new_size),
        )
        if new_size == self.state.cell_size:
            return
        self.state.cell_size = new_size
        self.center_view()
        self._status(f"3D cell size: {new_size}px")

    def save_history(self) -> None:
        self.timeline.prepare_change()

    def sync_history(self) -> bool:
        recorded = self.timeline.sync()
        if recorded:
            self.services.record_analysis(self.analysis_observation())
        return recorded

    def history_status(self) -> TimelineStatus:
        return self.timeline.status()

    def reset_history(self) -> None:
        self.timeline.reset()
        self.services.reset_analysis(self.analysis_observation())

    def step_back(self) -> None:
        if not self.timeline.step(-1):
            self._status("No earlier 3D state is available.")
            return
        self.services.set_running(False)
        self.services.rebuild_sidebar()
        self._status(f"Returned to 3D generation {self.state.generation}.")

    def step_forward(self) -> None:
        if not self.timeline.step(1):
            self._status("No later 3D state is available.")
            return
        self.services.set_running(False)
        self.services.rebuild_sidebar()
        self._status(f"Advanced to 3D generation {self.state.generation}.")

    def seek_history(self, index: int) -> bool:
        moved = self.timeline.seek(index)
        if moved:
            self.services.set_running(False)
            self.services.rebuild_sidebar()
        return moved

    def seek_generation(self, generation: int) -> bool:
        moved = self.timeline.seek_generation(generation)
        if moved:
            self.services.set_running(False)
            self.services.rebuild_sidebar()
        return moved

    def analysis_observation(self) -> StateObservation:
        return StateObservation(
            key=(
                "3d:generations"
                if self.state.mode_key == MODE_GENERATIONS
                else "3d:life_like"
            ),
            title=f"{self.mode_label}: {self.rule.name} {self.rule.notation}",
            generation=self.state.generation,
            values=tuple(int(value) for value in self.state.volume.cells.flat),
            state_count=self.state.volume.state_count,
            active_states=(1,),
            population_label=(
                "Active voxels"
                if self.state.mode_key == MODE_GENERATIONS
                else "Live voxels"
            ),
            alignment="center",
            experiment_context=(
                self.state.mode_key,
                self.state.rule_key,
                self.state.volume.boundary,
                self.rule.neighborhood.key,
                self.state.volume.shape,
            ),
        )

    def advance(self) -> bool:
        self.save_history()
        self.state.volume.neighborhood = self.rule.neighborhood
        if isinstance(self.rule, GenerationsRule3D):
            following = step_generations_3d(self.state.volume, self.rule)
        else:
            following = step_life_like_3d(self.state.volume, self.rule)
        self.state.volume.replace_cells(following)
        self.state.generation += 1
        self._invalidate()
        self.sync_history()
        return True

    def _replace_initial_cells(self, cells: np.ndarray, message: str) -> None:
        if np.array_equal(cells, self.state.volume.cells) and self.state.generation == 0:
            self._status(message)
            return
        self.save_history()
        self.state.volume.replace_cells(cells)
        self.state.generation = 0
        self.services.set_running(False)
        self._invalidate()
        self.sync_history()
        self._status(message)

    def clear(self) -> None:
        self._replace_initial_cells(
            np.zeros(self.state.volume.shape, dtype=np.uint8),
            "3D volume cleared.",
        )

    def randomize(self, density: float = 0.20) -> None:
        if isinstance(self.rule, GenerationsRule3D):
            self.seed_generations_core(density)
            return
        density = max(0.01, min(0.50, float(density)))
        cells = np.fromiter(
            (
                1 if self.state.rng.random() < density else 0
                for _ in range(self.state.volume.cell_count)
            ),
            dtype=np.uint8,
            count=self.state.volume.cell_count,
        ).reshape(self.state.volume.shape)
        self._replace_initial_cells(
            cells,
            f"Random 3D soup created at {density:.0%} density.",
        )

    def seed_cluster(self) -> None:
        """Create a compact deterministic seed around the volume center."""
        if isinstance(self.rule, GenerationsRule3D):
            self.seed_generations_core()
            return
        cells = np.zeros(self.state.volume.shape, dtype=np.uint8)
        center = tuple(length // 2 for length in self.state.volume.shape)
        z, y, x = center
        cells[z, y, x] = 1
        for dz, dy, dx in (
            (-1, 0, 0),
            (1, 0, 0),
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
            (0, 0, 1),
        ):
            cells[z + dz, y + dy, x + dx] = 1
        self.state.slice_axis = AXIS_Z
        self.state.slice_index = z
        self._replace_initial_cells(cells, "Centered seven-voxel 3D seed created.")
        self.center_view()

    def _generations_core_cells(
        self,
        rule: GenerationsRule3D,
        density: float | None = None,
        shape: tuple[int, int, int] | None = None,
    ) -> np.ndarray:
        """Return the small central random cluster used by documented 3D rules."""
        selected_density = rule.seed_density if density is None else float(density)
        selected_density = max(0.01, min(0.99, selected_density))
        selected_shape = self.state.volume.shape if shape is None else shape
        cells = np.zeros(selected_shape, dtype=np.uint8)
        extents = tuple(min(10, length) for length in selected_shape)
        starts = tuple(
            (length - extent) // 2
            for length, extent in zip(selected_shape, extents, strict=True)
        )
        core_size = int(np.prod(extents))
        core = np.fromiter(
            (
                1 if self.state.rng.random() < selected_density else 0
                for _ in range(core_size)
            ),
            dtype=np.uint8,
            count=core_size,
        ).reshape(extents)
        if not np.any(core):
            core[tuple(length // 2 for length in extents)] = 1
        slices = tuple(
            slice(start, start + extent)
            for start, extent in zip(starts, extents, strict=True)
        )
        cells[slices] = core
        return cells

    def seed_generations_core(self, density: float | None = None) -> None:
        """Seed the active Generations rule inside a bounded central cube."""
        if not isinstance(self.rule, GenerationsRule3D):
            self._status("Random core seeds belong to the 3D Generations mode.")
            return
        cells = self._generations_core_cells(self.rule, density)
        selected_density = self.rule.seed_density if density is None else float(density)
        self._replace_initial_cells(
            cells,
            f"{self.rule.name} central random core created at {selected_density:.0%} density.",
        )
        self.center_view()

    def set_volume_shape(self, shape: tuple[int, int, int]) -> None:
        """Resize to a supported cubic experiment volume and reset its seed."""
        if shape not in VOLUME_SHAPES_3D:
            raise ValueError(f"Unsupported 3D workspace volume: {shape}")
        if shape == self.state.volume.shape:
            return
        self.save_history()
        rule = self.rule
        cells = (
            self._generations_core_cells(rule, shape=shape)
            if isinstance(rule, GenerationsRule3D)
            else np.zeros(shape, dtype=np.uint8)
        )
        self.state.volume = Volume3D(
            cells,
            state_count=rule_state_count(rule),
            boundary=self.state.volume.boundary,
            neighborhood=rule.neighborhood,
        )
        self.state.generation = 0
        self.state.slice_index = shape[SLICE_AXES.index(self.state.slice_axis)] // 2
        self.state.view_mode = "all"
        self.state.selected_voxel = None
        self.services.set_running(False)
        self._invalidate()
        self.sync_history()
        self.center_view()
        self.services.rebuild_sidebar()
        self._status(
            f"3D volume: {VOLUME_SHAPE_LABELS_3D[shape]}. Experiment reset.",
            4.0,
        )

    def cycle_volume_shape(self) -> None:
        current = self.state.volume.shape
        if current not in VOLUME_SHAPES_3D:
            self.set_volume_shape(DEFAULT_VOLUME_SHAPE)
            return
        index = VOLUME_SHAPES_3D.index(current)
        self.set_volume_shape(VOLUME_SHAPES_3D[(index + 1) % len(VOLUME_SHAPES_3D)])

    def seed_pattern(self, pattern: Pattern3D) -> None:
        """Load a documented rule-compatible pattern as one history change."""
        cells = pattern.centered_cells(self.state.volume.shape)
        if (
            self.state.mode_key == MODE_SPATIAL_LIFE
            and self.state.rule_key == pattern.rule_key
            and self.state.volume.boundary == pattern.boundary
            and np.array_equal(cells, self.state.volume.cells)
            and self.state.generation == 0
        ):
            self._status(f"{pattern.name} is already loaded.")
            return
        self.save_history()
        rule = RULES_BY_MODE_3D[MODE_SPATIAL_LIFE][pattern.rule_key]
        self.state.mode_key = MODE_SPATIAL_LIFE
        self.state.rule_key = rule.key
        self.state.volume = Volume3D(
            cells,
            state_count=2,
            neighborhood=rule.neighborhood,
            boundary=pattern.boundary,
        )
        self.state.generation = 0
        self.state.slice_axis = AXIS_Z
        self.state.slice_index = self.slice_count() // 2
        self.state.view_mode = "all"
        self.services.set_running(False)
        self._invalidate()
        self.sync_history()
        self.center_view()
        self.services.rebuild_sidebar()
        self._status(f"Loaded {pattern.name}: {pattern.description}", 5.0)

    def set_mode(self, mode_key: str) -> None:
        """Switch between independent 3D rule families with a suitable seed."""
        if mode_key not in MODE_KEYS_3D:
            raise ValueError(f"Unknown 3D mode: {mode_key}")
        if mode_key == self.state.mode_key:
            return
        self.save_history()
        rule = DEFAULT_RULE_BY_MODE_3D[mode_key]
        if isinstance(rule, GenerationsRule3D):
            cells = self._generations_core_cells(rule)
        else:
            cells = np.zeros(self.state.volume.shape, dtype=np.uint8)
        self.state.mode_key = mode_key
        self.state.rule_key = rule.key
        self.state.volume = Volume3D(
            cells,
            state_count=rule_state_count(rule),
            boundary=self.state.volume.boundary,
            neighborhood=rule.neighborhood,
        )
        self.state.generation = 0
        self.state.selected_voxel = None
        self.state.slice_index = min(self.state.slice_index, self.slice_count() - 1)
        self.services.set_running(False)
        self._invalidate()
        self.sync_history()
        self.center_view()
        self.services.rebuild_sidebar()
        self._status(
            f"3D mode: {self.mode_label}. {rule.name} {rule.notation} loaded.",
            4.0,
        )

    def cycle_mode(self) -> None:
        index = MODE_KEYS_3D.index(self.state.mode_key)
        self.set_mode(MODE_KEYS_3D[(index + 1) % len(MODE_KEYS_3D)])

    def set_rule(self, rule_key: str) -> None:
        registry = RULES_BY_MODE_3D[self.state.mode_key]
        rule = registry[rule_key]
        if rule.key == self.state.rule_key:
            return
        self.save_history()
        self.state.rule_key = rule.key
        if isinstance(rule, GenerationsRule3D):
            cells = self._generations_core_cells(rule)
            self.state.volume = Volume3D(
                cells,
                state_count=rule.state_count,
                boundary=self.state.volume.boundary,
                neighborhood=rule.neighborhood,
            )
            self.state.generation = 0
            self.services.set_running(False)
            self.center_view()
        else:
            self.state.volume.neighborhood = rule.neighborhood
        self._invalidate()
        self.sync_history()
        self.services.rebuild_sidebar()
        self._status(f"3D rule: {rule.name} ({rule.notation}).")

    def cycle_rule(self) -> None:
        keys = tuple(RULES_BY_MODE_3D[self.state.mode_key])
        index = keys.index(self.state.rule_key)
        self.set_rule(keys[(index + 1) % len(keys)])

    def cycle_neighborhood(self) -> None:
        """Switch between 26-neighbor and six-face rule families safely."""
        if not isinstance(self.rule, LifeLikeRule3D):
            self._status(
                "The neighborhood is part of each 3D Generations rule preset."
            )
            return
        if self.rule.neighborhood.key == NEIGHBORHOODS_3D["moore"].key:
            self.set_rule(FACE_LIFE.key)
        else:
            self.set_rule(DEFAULT_RULE_3D.key)

    def cycle_boundary(self) -> None:
        current = self.state.volume.boundary
        index = BOUNDARY_MODES.index(current)
        self.save_history()
        self.state.volume.boundary = BOUNDARY_MODES[(index + 1) % len(BOUNDARY_MODES)]
        self._invalidate()
        self.sync_history()
        self.services.rebuild_sidebar()
        self._status(f"3D boundary: {self.state.volume.boundary.title()}.")

    def cycle_axis(self) -> None:
        index = SLICE_AXES.index(self.state.slice_axis)
        self.state.slice_axis = SLICE_AXES[(index + 1) % len(SLICE_AXES)]
        self.state.slice_index = self.slice_count() // 2
        if not self.services.hardware_3d():
            self.center_view()
        self.services.rebuild_sidebar()
        self._status(f"3D filter axis: {self.state.slice_axis.upper()}.")

    def move_slice(self, amount: int) -> None:
        target = max(0, min(self.slice_count() - 1, self.state.slice_index + amount))
        if target == self.state.slice_index:
            self._status("Already at the outermost slice.")
            return
        self.state.slice_index = target
        if not self.services.hardware_3d():
            self._invalidate()
        self.services.rebuild_sidebar()

    def cycle_view_mode(self) -> None:
        index = FILTER_MODES.index(self.state.view_mode)
        self.state.view_mode = FILTER_MODES[(index + 1) % len(FILTER_MODES)]
        self.state.selected_voxel = None
        self.services.rebuild_sidebar()
        self._status(f"3D display: {THREE_D_VIEW_LABELS[self.state.view_mode]}.")

    def toggle_clip_side(self) -> None:
        self.state.clip_keep_lower = not self.state.clip_keep_lower
        self.services.rebuild_sidebar()
        relation = "0 to plane" if self.state.clip_keep_lower else "plane to maximum"
        self._status(f"Clipping keeps layers from {relation}.")

    def cycle_opacity(self) -> None:
        try:
            index = THREE_D_OPACITIES.index(self.state.voxel_opacity)
        except ValueError:
            index = 0
        self.state.voxel_opacity = THREE_D_OPACITIES[
            (index + 1) % len(THREE_D_OPACITIES)
        ]
        self.services.rebuild_sidebar()
        self._status(f"Voxel opacity: {self.state.voxel_opacity:.0%}.")

    def render_settings(self) -> VoxelRenderSettings:
        return VoxelRenderSettings(
            mode=self.state.view_mode,
            axis=self.state.slice_axis,
            layer=self.state.slice_index,
            keep_lower=self.state.clip_keep_lower,
            opacity=self.state.voxel_opacity,
        )

    def toggle_running(self) -> None:
        running = not self.services.is_running()
        self.services.set_running(running)
        self.services.rebuild_sidebar()
        self._status("3D simulation running." if running else "3D simulation paused.")

    def _timeline_snapshot(self) -> dict[str, Any]:
        """Capture compact immutable bytes for bounded 3D timeline storage."""
        return {
            "mode": self.state.mode_key,
            "rule": self.state.rule_key,
            "state_count": self.state.volume.state_count,
            "boundary": self.state.volume.boundary,
            "shape": self.state.volume.shape,
            "cells": self.state.volume.cells.tobytes(order="C"),
            "generation": self.state.generation,
            "slice_axis": self.state.slice_axis,
            "slice_index": self.state.slice_index,
        }

    def _restore_timeline_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        previous_shape = self.state.volume.shape
        shape = tuple(int(value) for value in snapshot["shape"])
        cells = np.frombuffer(snapshot["cells"], dtype=np.uint8).reshape(shape)
        rule_key = str(snapshot["rule"])
        rule = ALL_RULES_3D[rule_key]
        mode_key = str(snapshot.get("mode", mode_for_rule(rule_key)))
        if mode_for_rule(rule_key) != mode_key:
            raise ValueError("3D timeline rule does not belong to its saved mode.")
        state_count = int(snapshot.get("state_count", rule_state_count(rule)))
        if state_count != rule_state_count(rule):
            raise ValueError("3D timeline state count does not match its rule.")
        self.state.mode_key = mode_key
        self.state.rule_key = rule.key
        self.state.volume = Volume3D(
            cells,
            state_count=state_count,
            boundary=str(snapshot["boundary"]),
            neighborhood=rule.neighborhood,
        )
        self.state.generation = int(snapshot["generation"])
        self.state.slice_axis = str(snapshot.get("slice_axis", self.state.slice_axis))
        self.state.slice_index = min(
            int(snapshot.get("slice_index", self.state.slice_index)),
            self.slice_count() - 1,
        )
        self.state.drawing = False
        self.state.stroke_history_pending = False
        self.state.selected_voxel = None
        if previous_shape != shape:
            if self.services.hardware_3d():
                self.state.camera.reset_for_shape(shape)
            else:
                self.center_view()
        self._invalidate()
        self.services.rebuild_sidebar()

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-compatible simulation, inspection, and orbit-camera state."""
        return {
            "shape": list(self.state.volume.shape),
            "cells": self.state.volume.cells.tolist(),
            "mode": self.state.mode_key,
            "rule": self.state.rule_key,
            "state_count": self.state.volume.state_count,
            "boundary": self.state.volume.boundary,
            "generation": self.state.generation,
            "slice": {
                "axis": self.state.slice_axis,
                "index": self.state.slice_index,
            },
            "camera": self.state.camera.as_dict(),
            "view": {
                "mode": self.state.view_mode,
                "keep_lower": self.state.clip_keep_lower,
                "opacity": self.state.voxel_opacity,
            },
        }

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        """Restore a validated complete 3D workspace snapshot."""
        rule_key = str(snapshot["rule"])
        rule = ALL_RULES_3D[rule_key]
        mode_key = str(snapshot.get("mode", mode_for_rule(rule_key)))
        if mode_for_rule(rule_key) != mode_key:
            raise ValueError("3D session rule does not belong to its saved mode.")
        state_count = int(snapshot.get("state_count", rule_state_count(rule)))
        if state_count != rule_state_count(rule):
            raise ValueError("3D session state count does not match its rule.")
        volume = Volume3D(
            snapshot["cells"],
            state_count=state_count,
            boundary=str(snapshot["boundary"]),
            neighborhood=rule.neighborhood,
        )
        if list(volume.shape) != list(snapshot["shape"]):
            raise ValueError("3D session shape does not match its cell volume.")
        slice_state = snapshot["slice"]
        axis = str(slice_state["axis"])
        index = int(slice_state["index"])
        if axis not in SLICE_AXES or not 0 <= index < volume.shape[SLICE_AXES.index(axis)]:
            raise ValueError("3D session slice is outside the saved volume.")
        camera = snapshot["camera"]
        view_state = snapshot.get(
            "view",
            {"mode": "all", "keep_lower": True, "opacity": 1.0},
        )
        render_settings = VoxelRenderSettings(
            mode=str(view_state["mode"]),
            axis=axis,
            layer=index,
            keep_lower=view_state["keep_lower"],
            opacity=float(view_state["opacity"]),
        )

        self.state.volume = volume
        self.state.mode_key = mode_key
        self.state.rule_key = rule.key
        self.state.generation = int(snapshot["generation"])
        self.state.slice_axis = axis
        self.state.slice_index = index
        self.state.view_mode = render_settings.mode
        self.state.clip_keep_lower = render_settings.keep_lower
        self.state.voxel_opacity = render_settings.opacity
        if "target" in camera:
            self.state.camera = OrbitCamera3D.from_mapping(camera)
        else:
            # Direct callers can still restore pre-OpenGL snapshots. The
            # session validator upgrades these to an orbit camera beforehand.
            self.state.camera = _new_default_camera()
            self.state.camera.reset_for_shape(volume.shape)
            self.state.cell_size = max(
                THREE_D_MIN_CELL_SIZE,
                min(THREE_D_MAX_CELL_SIZE, int(camera["cell_size"])),
            )
            self.state.view_offset_x = int(camera["offset"][0])
            self.state.view_offset_y = int(camera["offset"][1])
        self.state.drawing = False
        self.state.stroke_history_pending = False
        self.state.selected_voxel = None
        self.state.pointer_button = 0
        self.state.pointer_origin = None
        self.state.pointer_dragged = False
        self._invalidate()
        self.reset_history()
        self.services.rebuild_sidebar()

    def plane_to_position(self, row: int, column: int) -> tuple[int, int, int]:
        if self.state.slice_axis == AXIS_Z:
            return self.state.slice_index, row, column
        if self.state.slice_axis == AXIS_Y:
            return row, self.state.slice_index, column
        return row, column, self.state.slice_index

    def mouse_to_position(self, position: tuple[int, int]) -> tuple[int, int, int] | None:
        viewport = self.services.viewport()
        if not viewport.collidepoint(position):
            return None
        origin_x, origin_y = self.slice_origin()
        column = (position[0] - origin_x) // self.state.cell_size
        row = (position[1] - origin_y) // self.state.cell_size
        rows, columns = self.state.volume.slice_shape(self.state.slice_axis)
        if not (0 <= row < rows and 0 <= column < columns):
            return None
        return self.plane_to_position(row, column)

    def draw_cell(self, position: tuple[int, int, int], value: int) -> bool:
        if self.state.volume.get_cell(position) == value:
            return False
        if not self.state.stroke_history_pending:
            self.save_history()
            self.state.stroke_history_pending = True
        self.state.volume.set_cell(position, value)
        self._invalidate()
        return True

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_q:
            self.cycle_axis()
        elif event.key in (pygame.K_COMMA, pygame.K_PAGEUP):
            self.move_slice(-1)
        elif event.key in (pygame.K_PERIOD, pygame.K_PAGEDOWN):
            self.move_slice(1)
        elif event.key == pygame.K_b:
            self.cycle_boundary()
        elif event.key == pygame.K_v:
            self.cycle_volume_shape()
        elif event.key == pygame.K_k:
            self.cycle_neighborhood()
        elif event.key == pygame.K_l:
            self.cycle_view_mode()
        elif event.key == pygame.K_o:
            self.cycle_opacity()
        elif event.key == pygame.K_SLASH:
            self.toggle_clip_side()
        elif event.key == pygame.K_t:
            if isinstance(self.rule, GenerationsRule3D):
                self._status(
                    "Draw active state 1 or erase; refractory states are generated by the rule."
                )
            else:
                self._status("Spatial Life is binary: draw alive or erase.")
        elif event.key == pygame.K_m:
            self.cycle_mode()
        else:
            return False
        return True

    def handle_pointer_event(self, event: pygame.event.Event) -> bool:
        if self.services.hardware_3d():
            return self._handle_voxel_pointer_event(event)
        return self._handle_slice_pointer_event(event)

    def _pick_at(self, position: tuple[int, int]):
        viewport = self.services.viewport()
        if not viewport.collidepoint(position):
            return None
        origin, direction = self.state.camera.screen_ray(
            position,
            (viewport.x, viewport.y, viewport.width, viewport.height),
        )
        return pick_voxel(
            self.state.volume,
            origin,
            direction,
            self.render_settings(),
        )

    def _handle_voxel_pointer_event(self, event: pygame.event.Event) -> bool:
        viewport = self.services.viewport()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button not in (1, 2, 3) or not viewport.collidepoint(event.pos):
                return True
            self.state.pointer_button = event.button
            self.state.pointer_origin = event.pos
            self.state.pointer_dragged = False
            if event.button == 3:
                result = self._pick_at(event.pos)
                if result is not None:
                    self.state.stroke_history_pending = False
                    changed = self.draw_cell(result.hit, 0)
                    if changed:
                        self.sync_history()
                    self.state.stroke_history_pending = False
                    self.state.selected_voxel = None
            return True

        if event.type == pygame.MOUSEMOTION:
            if self.state.pointer_button == 1 and event.buttons[0]:
                if self.state.pointer_origin is not None:
                    dx = event.pos[0] - self.state.pointer_origin[0]
                    dy = event.pos[1] - self.state.pointer_origin[1]
                    if abs(dx) + abs(dy) >= 4:
                        self.state.pointer_dragged = True
                if self.state.pointer_dragged:
                    self.state.camera.orbit(*event.rel)
                    self.state.selected_voxel = None
            elif self.state.pointer_button == 2 and event.buttons[1]:
                self.state.pointer_dragged = True
                self.state.camera.pan(event.rel[0], event.rel[1], viewport.height)
                self.state.selected_voxel = None
            elif not any(event.buttons):
                result = self._pick_at(event.pos)
                self.state.selected_voxel = None if result is None else result.hit
            return True

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and not self.state.pointer_dragged:
                result = self._pick_at(event.pos)
                if result is None:
                    self._status(
                        "No voxel was hit; use Centered Seed or Randomize to start a structure."
                    )
                elif result.adjacent is None:
                    self._status("That voxel is on the camera-facing volume boundary.")
                elif not voxel_is_visible(result.adjacent, self.render_settings()):
                    self._status(
                        "The adjacent cell is outside the visible layer filter."
                    )
                else:
                    self.state.stroke_history_pending = False
                    changed = self.draw_cell(result.adjacent, 1)
                    if changed:
                        self.sync_history()
                    self.state.stroke_history_pending = False
                    self.state.selected_voxel = result.adjacent
            self.state.pointer_button = 0
            self.state.pointer_origin = None
            self.state.pointer_dragged = False
            return True
        return False

    def _handle_slice_pointer_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (1, 3):
                position = self.mouse_to_position(event.pos)
                if position is not None:
                    self.state.drawing = True
                    self.state.drawing_value = 1 if event.button == 1 else 0
                    self.state.stroke_history_pending = False
                    self.draw_cell(position, self.state.drawing_value)
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            if self.state.drawing and self.state.stroke_history_pending:
                self.sync_history()
            self.state.drawing = False
            self.state.stroke_history_pending = False
            return True
        if event.type == pygame.MOUSEMOTION:
            if self.state.drawing:
                position = self.mouse_to_position(event.pos)
                if position is not None:
                    self.draw_cell(position, self.state.drawing_value)
            elif event.buttons[1]:
                self.state.view_offset_x += event.rel[0]
                self.state.view_offset_y += event.rel[1]
                self._invalidate()
            return True
        return False

    def build_sidebar(self, menu: Menu) -> None:
        accent = DIMENSION_BY_KEY["3d"].accent
        menu.clear_buttons()
        menu.set_header(f"3D · {self.mode_label}")
        menu.begin_section(
            "3d_workspace",
            "Workspace",
            tooltip="Navigate dimensions, sessions, analysis, and help.",
        )
        menu.add_button(
            "Select Dimension (D)",
            self.services.activate_dimension_menu,
            accent=accent,
        )
        menu.add_button(
            "Session Save / Load (P)",
            self.services.activate_session_menu,
            accent=(80, 190, 145),
        )
        menu.add_button(
            "Scientific Analysis (I)",
            self.services.activate_analysis,
            accent=(90, 195, 255),
        )
        menu.add_button(
            "Keyboard Help (F1)",
            self.services.activate_help,
            accent=(180, 150, 245),
        )

        menu.begin_section(
            "3d_simulation",
            "Rule & Volume",
            tooltip="Choose a 3D automata family, rule, neighborhood, and boundary.",
        )
        menu.add_button(
            f"{'Pause' if self.services.is_running() else 'Run'} Simulation",
            self.toggle_running,
            accent=accent,
            active=self.services.is_running(),
        )
        menu.add_button(
            f"Mode: {self.mode_label} (M)",
            self.cycle_mode,
            accent=accent,
            tooltip=(
                "Switch between binary Spatial Life and multi-state 3D Generations."
            ),
        )
        menu.add_button(
            f"Rule: {self.rule.notation} · {self.rule.name}",
            self.cycle_rule,
            accent=accent,
            tooltip=self.rule.description,
        )
        menu.add_button(
            f"Neighborhood: {self.rule.neighborhood.size} cells",
            self.cycle_neighborhood,
            tooltip=(
                "Spatial Life can switch neighborhood families; Generations "
                "presets carry their documented neighborhood."
            ),
        )
        menu.add_button(
            f"Boundary: {self.state.volume.boundary.title()}",
            self.cycle_boundary,
        )
        volume_label = VOLUME_SHAPE_LABELS_3D.get(
            self.state.volume.shape,
            "×".join(str(length) for length in reversed(self.state.volume.shape)),
        )
        menu.add_button(
            f"Volume: {volume_label} (V)",
            self.cycle_volume_shape,
            tooltip=(
                "Cycle 32³, 48³, and 64³ experiment volumes. Resizing resets "
                "the current experiment and records the previous state in the timeline."
            ),
        )
        if self.state.mode_key == MODE_SPATIAL_LIFE:
            menu.add_button("Centered Seed", self.seed_cluster)
            menu.add_button(
                "Bays 5766 Glider",
                lambda: self.seed_pattern(BAYS_5766_GLIDER),
                accent=(245, 185, 70),
                tooltip=(
                    "Load Carter Bays' documented ten-voxel, period-four glider "
                    "and select its B6/S567 rule."
                ),
            )
            menu.add_button("Randomize Volume", lambda: self.randomize(0.18))
        else:
            menu.add_button(
                "Random Central Core",
                self.seed_generations_core,
                accent=(245, 185, 70),
                tooltip=(
                    "Create the small central random state-1 seed used for the "
                    "documented 3D Generations experiments."
                ),
            )
            menu.add_button(
                "Explain Current Rule",
                lambda: self._status(
                    f"{self.rule.name} {self.rule.notation}: {self.rule.description}",
                    7.0,
                ),
                tooltip=self.rule.description,
            )
        menu.add_button("Clear Volume", self.clear)

        menu.begin_section(
            "3d_camera",
            "Camera & View",
            tooltip="Orbit, pan, zoom, and reset the perspective voxel view.",
        )
        menu.add_button("Fit Full Volume (Ctrl+0)", self.fit_view, accent=accent)
        menu.add_button("Reset Camera (C)", self.center_view)
        menu.add_button(
            f"Theme: {self.services.theme_name().title()}",
            self.services.cycle_theme,
        )

        if self.services.hardware_3d():
            menu.begin_section(
                "3d_inspection",
                "Volume Inspection",
                tooltip="Clip the volume, isolate one layer, or reveal interior voxels.",
            )
            menu.add_button(
                f"Display: {THREE_D_VIEW_LABELS[self.state.view_mode]} (L)",
                self.cycle_view_mode,
                accent=accent,
                active=self.state.view_mode != "all",
            )
            menu.add_button(
                f"Filter Axis: {self.state.slice_axis.upper()} (Q)",
                self.cycle_axis,
            )
            menu.add_button(
                f"Plane - ({self.state.slice_index + 1}/{self.slice_count()})",
                lambda: self.move_slice(-1),
            )
            menu.add_button(
                f"Plane + ({self.state.slice_index + 1}/{self.slice_count()})",
                lambda: self.move_slice(1),
            )
            if self.state.view_mode == "clip":
                relation = "≤" if self.state.clip_keep_lower else "≥"
                menu.add_button(
                    f"Keep Layers: {relation} Plane (/)",
                    self.toggle_clip_side,
                )
            menu.add_button(
                f"Voxel Opacity: {self.state.voxel_opacity:.0%} (O)",
                self.cycle_opacity,
                active=self.state.voxel_opacity < 1.0,
            )

        if not self.services.hardware_3d():
            menu.begin_section(
                "3d_slice",
                "Slice Fallback",
                expanded=False,
                tooltip="Plane controls used by the headless software fallback.",
            )
            menu.add_button(
                f"Axis: {self.state.slice_axis.upper()} (Q)",
                self.cycle_axis,
                accent=accent,
            )
            menu.add_button(
                f"Previous Slice ({self.state.slice_index + 1}/{self.slice_count()})",
                lambda: self.move_slice(-1),
            )
            menu.add_button(
                f"Next Slice ({self.state.slice_index + 1}/{self.slice_count()})",
                lambda: self.move_slice(1),
            )
            menu.add_button(
                f"Grid Lines: {'On' if self.services.show_grid() else 'Off'}",
                self.services.toggle_grid,
                active=self.services.show_grid(),
            )


class ThreeDimensionalWorkspaceRenderer(WorkspaceRenderer):
    """Render the volume as voxels, with a slice fallback for dummy SDL."""

    render_key = THREE_D_RENDER_KEY

    def __init__(
        self,
        controller: ThreeDimensionalWorkspaceController,
        services: ThreeDimensionalWorkspaceServices,
    ) -> None:
        self.controller = controller
        self.services = services
        self.rasterizer = StateGridRasterizer(max_cached_sizes=6)

    @staticmethod
    def _fit_text(font: pygame.font.Font, value: str, width: int) -> str:
        if font.size(value)[0] <= width:
            return value
        suffix = "…"
        shortened = value
        while shortened and font.size(shortened + suffix)[0] > width:
            shortened = shortened[:-1]
        return shortened.rstrip() + suffix

    def cache_key(self) -> tuple[Any, ...]:
        state = self.controller.state
        return (
            self.services.render_revision(THREE_D_RENDER_KEY),
            state.mode_key,
            state.rule_key,
            state.volume.state_count,
            self.services.viewport().size,
            state.slice_axis,
            state.slice_index,
            state.cell_size,
            state.view_offset_x,
            state.view_offset_y,
            tuple(float(value) for value in state.camera.target),
            state.camera.yaw,
            state.camera.pitch,
            state.camera.distance,
            state.view_mode,
            state.clip_keep_lower,
            state.voxel_opacity,
            self.services.theme_name(),
            self.services.show_grid(),
        )

    @staticmethod
    def _state_palette(
        background: tuple[int, int, int],
        active: tuple[int, int, int],
        state_count: int,
    ) -> tuple[tuple[int, int, int], ...]:
        """Build a bright-to-warm palette for active and refractory states."""
        if state_count == 2:
            return background, active
        decay = (255, 42, 10)
        colors = [background, active]
        for state in range(2, state_count):
            amount = (state - 1) / max(1, state_count - 2)
            colors.append(
                tuple(
                    round(source + (target - source) * amount)
                    for source, target in zip(active, decay, strict=True)
                )
            )
        return tuple(colors)

    def draw_base(self) -> None:
        screen = self.services.screen()
        viewport = self.services.viewport()
        theme = THEMES[self.services.theme_name()]
        if self.services.hardware_3d():
            self.services.render_volume(
                self.controller.state.volume,
                self.controller.state.camera,
                viewport,
                self.services.render_revision(THREE_D_RENDER_KEY),
                self.controller.render_settings(),
                self.controller.state.selected_voxel,
            )
            return
        old_clip = screen.get_clip()
        screen.set_clip(viewport)
        pygame.draw.rect(screen, theme["background"], viewport)
        plane = self.controller.current_slice()
        origin = self.controller.slice_origin()
        self.rasterizer.blit(
            screen,
            plane,
            self._state_palette(
                theme["background"],
                theme["cell"],
                self.controller.state.volume.state_count,
            ),
            origin,
            cell_size=self.controller.state.cell_size,
        )
        rect = self.controller.slice_rect()
        cell_size = self.controller.state.cell_size
        if self.services.show_grid() and cell_size >= 4:
            rows, columns = plane.shape
            for column in range(columns + 1):
                x = rect.x + column * cell_size
                pygame.draw.line(screen, theme["grid"], (x, rect.top), (x, rect.bottom))
            for row in range(rows + 1):
                y = rect.y + row * cell_size
                pygame.draw.line(screen, theme["grid"], (rect.left, y), (rect.right, y))
        pygame.draw.rect(screen, DIMENSION_BY_KEY["3d"].accent, rect, 2)
        screen.set_clip(old_clip)

    def _stats(self) -> dict[str, Any]:
        volume = self.controller.state.volume
        active = int(np.count_nonzero(volume.cells == 1))
        refractory = int(np.count_nonzero(volume.cells > 1))
        occupied = active + refractory
        slice_active = int(np.count_nonzero(self.controller.current_slice() == 1))
        return {
            "active": active,
            "refractory": refractory,
            "occupied": occupied,
            "density": 100.0 * active / volume.cell_count,
            "slice_active": slice_active,
        }

    def draw_bars(self) -> None:
        screen = self.services.screen()
        width, height = self.services.window_size()
        content_width = max(1, width - self.services.menu_width)
        theme = THEMES[self.services.theme_name()]
        pygame.draw.rect(
            screen,
            theme["info_bar"],
            (0, 0, content_width, self.services.info_bar_height),
        )
        state_label = "Running" if self.services.is_running() else "Paused"
        state = self.controller.state
        rule = self.controller.rule
        info = (
            f"{state_label}   Dimension: 3D   Mode: {self.controller.mode_label}   "
            f"Rule: {rule.notation}   "
            f"Neighbors: {rule.neighborhood.size}   Speed: {self.services.speed()} gen/s   "
            f"Generation: {state.generation}   Boundary: {state.volume.boundary.title()}"
        )
        info_font = self.services.small_font()
        tool_width = min(220, max(150, content_width // 4))
        available = max(40, content_width - 120 - tool_width - 18)
        screen.blit(
            info_font.render(self._fit_text(info_font, info, available), True, theme["text"]),
            (120, 11),
        )

        stats_y = height - self.services.stats_height
        pygame.draw.rect(
            screen,
            theme["stats_bar"],
            (0, stats_y, content_width, self.services.stats_height),
        )
        stats = self.services.cached_stats(THREE_D_RENDER_KEY, self._stats)
        history = self.controller.history_status()
        shape = state.volume.shape
        if self.services.hardware_3d():
            filter_label = THREE_D_VIEW_LABELS[state.view_mode]
            if state.view_mode != "all":
                filter_label += (
                    f" {state.slice_axis.upper()}:{state.slice_index + 1}"
                )
            first_line = (
                f"Active voxels: {stats['active']}/{state.volume.cell_count}   "
                f"Density: {stats['density']:.2f}%   "
                f"Volume: {shape[2]}×{shape[1]}×{shape[0]}   "
                f"View: {filter_label} @ {state.voxel_opacity:.0%}   "
                f"Timeline: {history.cursor + 1}/{history.frame_count}"
            )
            second_line = (
                f"{rule.name} {rule.notation}   ·   refractory: {stats['refractory']}   ·   "
                "left drag: orbit   ·   "
                "wheel: zoom   ·   middle drag: pan   ·   left click: add   ·   right click: erase"
            )
        else:
            first_line = (
                f"Active voxels: {stats['active']}/{state.volume.cell_count}   "
                f"Density: {stats['density']:.2f}%   Slice active: {stats['slice_active']}   "
                f"Volume: {shape[2]}×{shape[1]}×{shape[0]}   "
                f"Timeline: {history.cursor + 1}/{history.frame_count}"
            )
            second_line = (
                f"{state.slice_axis.upper()} slice {state.slice_index + 1}/{self.controller.slice_count()}   ·   "
                f"{rule.name} {rule.notation}   ·   dummy-video slice fallback"
            )
        screen.blit(
            info_font.render(
                self._fit_text(info_font, first_line, content_width - 20),
                True,
                theme["text"],
            ),
            (10, stats_y + 8),
        )
        detail_font = self.services.tiny_font()
        screen.blit(
            detail_font.render(
                self._fit_text(detail_font, second_line, content_width - 20),
                True,
                theme["text"],
            ),
            (10, stats_y + 38),
        )
