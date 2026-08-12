"""State, controller, and renderer for the generalized 1D CA workspace."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import numpy as np
import pygame

from custom_rules import CustomRuleDefinition, custom_rule_from_document
from dimension_registry import DIMENSION_BY_KEY
from elementary_ca import (
    BOUNDARY_FIXED,
    BOUNDARY_INFINITE,
    BOUNDARY_WRAP,
    DEFAULT_RULE,
    DEFAULT_WIDTH,
    RULE_PRESETS,
    rule_bits,
    validate_rule,
)
from one_dimensional_ca import (
    FAMILY_ELEMENTARY,
    FAMILY_HIGHER_ORDER,
    FAMILY_MULTISTATE,
    FAMILY_RADIUS,
    FAMILY_REVERSIBLE,
    FAMILY_TOTALISTIC,
    RULE_FAMILIES,
    RULE_FAMILY_BY_KEY,
    SEED_WIDTH_COMPACT,
    SEED_WIDTH_MODES,
    SEED_WIDTH_VIEWPORT,
    SEED_WIDTH_WIDE,
    CellRow,
    RuleSpec,
    default_rule_spec,
    next_uniform_background,
    normalize_state_row,
    random_state_seed,
    row_statistics,
    short_rule_code,
    single_state_seed,
    step_one_dimensional,
)
from rng_state import encode_random_state, restore_random_state
from scientific_analysis import StateObservation
from surface_rasterizer import StateGridRasterizer
from themes import THEMES, Menu, one_d_state_color
from timeline_history import TimelineBinding, TimelineStatus
from workspaces.base import WorkspaceController, WorkspaceRenderer

ECA_RENDER_KEY = "elementary_ca"
ECA_EDITOR_HEIGHT = 44
ECA_DIAGRAM_LIMIT = 512
ECA_DIAGRAM_CELL_BUDGET = 64_000
ECA_MIN_CELL_SIZE = 2
ECA_MAX_CELL_SIZE = 16
ECA_MIN_SEED_WIDTH = 9
ECA_MAX_SEED_WIDTH = 801
ECA_MAX_DIAGRAM_WIDTH = 4095
ECA_SURFARRAY_CELL_THRESHOLD = 4_096

@dataclass
class ElementaryWorkspaceState:
    """All persistent and transient state owned by the 1D workspace."""

    rule: int = DEFAULT_RULE
    family: str = FAMILY_ELEMENTARY
    states: int = 2
    radius: int = 1
    boundary: str = BOUNDARY_INFINITE
    background: int = 0
    previous_background: int = 0
    rule_change_reset: bool = True
    seed_width_mode: str = SEED_WIDTH_COMPACT
    seed: CellRow = field(
        default_factory=lambda: single_state_seed(DEFAULT_WIDTH)
    )
    rows: list[CellRow] = field(
        default_factory=lambda: [single_state_seed(DEFAULT_WIDTH)]
    )
    row_backgrounds: list[int] = field(default_factory=lambda: [0])
    previous_row: CellRow = field(
        default_factory=lambda: tuple(0 for _ in range(DEFAULT_WIDTH))
    )
    comparison_enabled: bool = False
    comparison_rule: int = 90
    comparison_rows: list[CellRow] = field(
        default_factory=lambda: [single_state_seed(DEFAULT_WIDTH)]
    )
    comparison_row_backgrounds: list[int] = field(default_factory=lambda: [0])
    comparison_previous_row: CellRow = field(
        default_factory=lambda: tuple(0 for _ in range(DEFAULT_WIDTH))
    )
    comparison_background: int = 0
    comparison_previous_background: int = 0
    generation: int = 0
    rng: random.Random = field(default_factory=random.Random)
    cell_size: int = 6
    view_offset_x: int = 0
    view_offset_y: int = 0
    rule_menu_active: bool = False
    rule_menu_input: str = ""
    rule_menu_target: str = "primary"
    rule_menu_favorites_only: bool = False
    drawing: bool = False
    drawing_value: int = 1
    brush_state: int = 1
    stroke_history_pending: bool = False
    custom_rule: CustomRuleDefinition | None = None


@dataclass(frozen=True)
class ElementaryWorkspaceServices:
    """Application services used by the extracted 1D workspace."""

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
    activate_experiment_lab: Callable[[], None]
    activate_export: Callable[[], None]
    activate_help: Callable[[], None]
    activate_tutorial: Callable[[], None]
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
    timeline_max_frames: int
    record_analysis: Callable[[StateObservation], None]
    reset_analysis: Callable[[StateObservation], None]
    favorite_rules: Callable[[], frozenset[int]]
    toggle_favorite_rule: Callable[[int], bool]
    activate_custom_rule_studio: Callable[[], None] = lambda: None


class ElementaryWorkspaceController(WorkspaceController):
    """Own generalized 1D rules, history, view state, and user input."""

    key = "1d"

    def __init__(
        self,
        services: ElementaryWorkspaceServices,
        state: ElementaryWorkspaceState | None = None,
    ) -> None:
        self.services = services
        self.state = state if state is not None else ElementaryWorkspaceState()
        self.timeline = TimelineBinding(
            self._timeline_snapshot,
            self._restore_timeline_snapshot,
            lambda: self.state.generation,
            max_frames=self.services.timeline_max_frames,
        )

    def _status(self, message: str, duration: float = 2.0) -> None:
        self.services.set_status(message, duration)

    def _invalidate(self) -> None:
        self.services.invalidate(ECA_RENDER_KEY)

    def activate(self) -> None:
        self.services.set_running(False)
        self.center_view()

    def deactivate(self) -> None:
        self.state.rule_menu_active = False
        self.state.drawing = False
        self.state.stroke_history_pending = False

    @property
    def overlay_active(self) -> bool:
        return self.state.rule_menu_active

    @property
    def generation(self) -> int:
        return self.state.generation

    @property
    def rule_spec(self) -> RuleSpec:
        """Return the normalized primary rule definition."""
        return RuleSpec(
            self.state.family,
            self.state.rule,
            self.state.states,
            self.state.radius,
        )

    @property
    def comparison_spec(self) -> RuleSpec:
        """Return the secondary rule with matching family parameters."""
        return self.rule_spec.with_code(self.state.comparison_rule)

    @property
    def family_name(self) -> str:
        return RULE_FAMILY_BY_KEY[self.state.family].name

    @staticmethod
    def _odd_width(value: int) -> int:
        """Clamp a candidate seed width and keep its center cell exact."""
        clamped = max(ECA_MIN_SEED_WIDTH, min(ECA_MAX_SEED_WIDTH, int(value)))
        return clamped if clamped % 2 else clamped - 1

    def seed_widths(self) -> dict[str, int]:
        """Return seed-width presets calculated for the current viewport."""
        visible_cells = self.diagram_panes()[0].width // self.state.cell_size
        viewport_width = self._odd_width(visible_cells)
        wide_width = self._odd_width(viewport_width * 2 - 1)
        return {
            SEED_WIDTH_COMPACT: DEFAULT_WIDTH,
            SEED_WIDTH_VIEWPORT: viewport_width,
            SEED_WIDTH_WIDE: wide_width,
        }

    def preferred_seed_width(self) -> int:
        """Return the current preset width without resizing an active diagram."""
        mode = self.state.seed_width_mode
        if mode not in SEED_WIDTH_MODES:
            mode = SEED_WIDTH_COMPACT
        return self.seed_widths()[mode]

    def seed_width_label(self) -> str:
        """Describe the selected starting-width policy and its current size."""
        labels = {
            SEED_WIDTH_COMPACT: "Compact",
            SEED_WIDTH_VIEWPORT: "Viewport",
            SEED_WIDTH_WIDE: "Wide",
        }
        mode = self.state.seed_width_mode
        return f"{labels.get(mode, 'Compact')} ({self.preferred_seed_width()})"

    def diagram_row_limit(self, width: int | None = None) -> int:
        """Bound retained space-time cells while preserving a useful tail."""
        current_width = width or len(self.state.rows[-1])
        budget_limit = ECA_DIAGRAM_CELL_BUDGET // max(1, current_width)
        return min(
            ECA_DIAGRAM_LIMIT,
            max(1, budget_limit),
        )

    @staticmethod
    def _matching_background_history(
        values: list[int],
        rows: list[CellRow],
        current_background: int,
    ) -> list[int]:
        """Return one outside-state sample per row, including legacy state."""
        if len(values) == len(rows):
            return list(values)
        return [0] * max(0, len(rows) - 1) + [current_background]

    def diagram_viewport(self) -> pygame.Rect:
        viewport = self.services.viewport()
        return pygame.Rect(
            viewport.x,
            viewport.y + ECA_EDITOR_HEIGHT,
            viewport.width,
            max(1, viewport.height - ECA_EDITOR_HEIGHT),
        )

    def diagram_panes(self) -> tuple[pygame.Rect, ...]:
        """Return one full-width pane or two equal comparison panes."""
        viewport = self.diagram_viewport()
        if not self.state.comparison_enabled:
            return (viewport,)
        gap = 10
        pane_width = max(1, (viewport.width - gap) // 2)
        return (
            pygame.Rect(viewport.x, viewport.y, pane_width, viewport.height),
            pygame.Rect(
                viewport.x + pane_width + gap,
                viewport.y,
                viewport.width - pane_width - gap,
                viewport.height,
            ),
        )

    def grid_origin(self, comparison: bool = False) -> tuple[int, int]:
        """Return a diagram origin while preserving a shared pan offset."""
        viewport = self.diagram_viewport()
        pane = self.diagram_panes()[1 if comparison else 0]
        diagram_width = len(self.state.rows[-1]) * self.state.cell_size
        centered_full = (viewport.width - diagram_width) // 2
        pan_delta = self.state.view_offset_x - centered_full
        label_height = 20 if self.state.comparison_enabled else 0
        return (
            pane.x + (pane.width - diagram_width) // 2 + pan_delta,
            pane.y
            + self.services.grid_top_margin
            + label_height
            + self.state.view_offset_y,
        )

    def editor_rect(self) -> pygame.Rect:
        viewport = self.services.viewport()
        width = len(self.state.rows[-1]) * self.state.cell_size
        return pygame.Rect(
            viewport.x + self.state.view_offset_x,
            viewport.y + 25,
            width,
            self.state.cell_size,
        )

    def follow_latest(self) -> None:
        viewport = self.diagram_viewport()
        diagram_height = len(self.state.rows) * self.state.cell_size
        label_height = 20 if self.state.comparison_enabled else 0
        self.state.view_offset_y = min(
            0,
            viewport.height
            - self.services.grid_top_margin
            - label_height
            - diagram_height,
        )

    def center_view(self) -> None:
        viewport = self.diagram_viewport()
        diagram_width = len(self.state.rows[-1]) * self.state.cell_size
        self.state.view_offset_x = (viewport.width - diagram_width) // 2
        self.state.view_offset_y = 0
        self.follow_latest()

    def zoom(self, factor: float) -> None:
        new_size = int(round(self.state.cell_size * factor))
        new_size = max(ECA_MIN_CELL_SIZE, min(ECA_MAX_CELL_SIZE, new_size))
        if new_size == self.state.cell_size:
            return
        self.state.cell_size = new_size
        self.center_view()
        self._invalidate()
        self._status(f"1D cell size: {self.state.cell_size}px")

    def save_history(self) -> None:
        self.timeline.prepare_change()

    def step_back(self) -> None:
        if not self.timeline.step(-1):
            self._status("No earlier 1D CA state is available.")
            return
        self.services.set_running(False)
        self._status(f"Returned to 1D generation {self.state.generation}.")

    def step_forward(self) -> None:
        if not self.timeline.step(1):
            self._status("No later 1D CA state is available.")
            return
        self.services.set_running(False)
        self._status(f"Advanced to 1D generation {self.state.generation}.")

    def seek_history(self, index: int) -> bool:
        moved = self.timeline.seek(index)
        if moved:
            self.services.set_running(False)
        return moved

    def seek_generation(self, generation: int) -> bool:
        moved = self.timeline.seek_generation(generation)
        if moved:
            self.services.set_running(False)
        return moved

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

    def analysis_observation(self) -> StateObservation:
        spec = self.rule_spec
        return StateObservation(
            key=f"1d:{self.state.family}",
            title=f"{self.family_name} Code {self.state.rule}",
            generation=self.state.generation,
            values=tuple(self.state.rows[-1]),
            state_count=self.state.states,
            active_states=tuple(range(1, self.state.states)),
            population_label="Active cells",
            alignment="center",
            lattice_shape=(len(self.state.rows[-1]),),
            experiment_context=(
                tuple(spec.as_dict().items()),
                self.state.boundary,
                self.state.rule_change_reset,
                self.state.seed_width_mode,
            ),
            signature_context=(
                self.state.background,
                self.state.previous_background,
                self.state.previous_row if spec.memory != "none" else (),
            ),
        )

    def advance(self) -> bool:
        spec = self.rule_spec
        comparison_spec = self.comparison_spec if self.state.comparison_enabled else spec
        current_row = self.state.rows[-1]
        comparison_row = self.state.comparison_rows[-1]
        self.state.row_backgrounds = self._matching_background_history(
            self.state.row_backgrounds,
            self.state.rows,
            self.state.background,
        )
        self.state.comparison_row_backgrounds = self._matching_background_history(
            self.state.comparison_row_backgrounds,
            self.state.comparison_rows,
            self.state.comparison_background,
        )
        history_saved = False
        edge_changed = any(
            value != self.state.background
            for value in (*current_row[: spec.radius], *current_row[-spec.radius :])
        )
        if self.state.comparison_enabled:
            edge_changed = edge_changed or any(
                value != self.state.comparison_background
                for value in (
                    *comparison_row[: spec.radius],
                    *comparison_row[-spec.radius :],
                )
            )
        if self.state.boundary == BOUNDARY_INFINITE and edge_changed:
            expanded_width = len(current_row) + 2 * spec.radius
            if expanded_width > ECA_MAX_DIAGRAM_WIDTH:
                self.services.set_running(False)
                self._status(
                    "1D diagram reached its 4,095-cell safety width; "
                    "restart or choose a new seed to continue.",
                    5.0,
                )
                return False
            self.save_history()
            history_saved = True
            primary_padding = (self.state.background,) * spec.radius
            comparison_padding = (self.state.comparison_background,) * spec.radius
            previous_padding = (self.state.previous_background,) * spec.radius
            comparison_previous_padding = (
                self.state.comparison_previous_background,
            ) * spec.radius
            current_row = (
                *primary_padding,
                *current_row,
                *primary_padding,
            )
            comparison_row = (
                *comparison_padding,
                *comparison_row,
                *comparison_padding,
            )
            self.state.previous_row = (
                *previous_padding,
                *self.state.previous_row,
                *previous_padding,
            )
            self.state.comparison_previous_row = (
                *comparison_previous_padding,
                *self.state.comparison_previous_row,
                *comparison_previous_padding,
            )
            self.state.view_offset_x -= self.state.cell_size * spec.radius

        next_row = step_one_dimensional(
            current_row,
            spec,
            boundary=self.state.boundary,
            background=self.state.background,
            previous_row=self.state.previous_row,
        )
        next_outside = (
            next_uniform_background(
                spec,
                self.state.background,
                previous_background=self.state.previous_background,
            )
            if self.state.boundary == BOUNDARY_INFINITE
            else 0
        )
        if self.state.comparison_enabled:
            comparison_next = step_one_dimensional(
                comparison_row,
                comparison_spec,
                boundary=self.state.boundary,
                background=self.state.comparison_background,
                previous_row=self.state.comparison_previous_row,
            )
            comparison_next_outside = (
                next_uniform_background(
                    comparison_spec,
                    self.state.comparison_background,
                    previous_background=self.state.comparison_previous_background,
                )
                if self.state.boundary == BOUNDARY_INFINITE
                else 0
            )
        else:
            comparison_row = current_row
            comparison_next = next_row
            comparison_next_outside = next_outside
        if not history_saved:
            self.save_history()
        self.state.rows.append(next_row)
        self.state.comparison_rows.append(comparison_next)
        self.state.row_backgrounds.append(next_outside)
        self.state.comparison_row_backgrounds.append(comparison_next_outside)
        self.state.previous_row = current_row
        self.state.comparison_previous_row = comparison_row
        self.state.previous_background = self.state.background
        self.state.comparison_previous_background = self.state.comparison_background
        self.state.background = next_outside
        self.state.comparison_background = comparison_next_outside
        row_limit = self.diagram_row_limit(len(next_row))
        excess = max(0, len(self.state.rows) - row_limit)
        if excess:
            del self.state.rows[:excess]
            del self.state.comparison_rows[:excess]
            del self.state.row_backgrounds[:excess]
            del self.state.comparison_row_backgrounds[:excess]
        self.state.generation += 1
        self.follow_latest()
        self._invalidate()
        self.sync_history()
        return True

    def reset_seed(self, seed: CellRow, message: str) -> None:
        seed = normalize_state_row(seed, self.state.states)
        if (
            self.state.rows == [seed]
            and self.state.generation == 0
            and self.state.background == 0
            and self.state.seed == seed
        ):
            self._status(message)
            return
        self.save_history()
        self.state.seed = seed
        self.state.rows = [seed]
        self.state.row_backgrounds = [0]
        self.state.previous_row = tuple(0 for _ in seed)
        self.state.comparison_rows = [seed]
        self.state.comparison_row_backgrounds = [0]
        self.state.comparison_previous_row = tuple(0 for _ in seed)
        self.state.generation = 0
        self.state.background = 0
        self.state.previous_background = 0
        self.state.comparison_background = 0
        self.state.comparison_previous_background = 0
        self.services.set_running(False)
        self.center_view()
        self._invalidate()
        self.sync_history()
        self._status(message)

    def clear(self) -> None:
        self.reset_seed(
            tuple(0 for _ in range(self.preferred_seed_width())),
            "1D diagram cleared.",
        )

    def randomize(self, density: float = 0.20) -> None:
        self.reset_seed(
            random_state_seed(
                self.preferred_seed_width(),
                states=self.state.states,
                density=density,
                rng=self.state.rng,
            ),
            f"Random {self.family_name} seed created at {density:.0%} density.",
        )

    def use_single_seed(self) -> None:
        self.reset_seed(
            single_state_seed(
                self.preferred_seed_width(),
                states=self.state.states,
            ),
            "Centered single-cell seed created.",
        )

    def cycle_seed_width(self) -> None:
        """Select the next starting-width preset and restart canonically."""
        self.save_history()
        current = (
            self.state.seed_width_mode
            if self.state.seed_width_mode in SEED_WIDTH_MODES
            else SEED_WIDTH_COMPACT
        )
        index = SEED_WIDTH_MODES.index(current)
        self.state.seed_width_mode = SEED_WIDTH_MODES[
            (index + 1) % len(SEED_WIDTH_MODES)
        ]
        width = self.preferred_seed_width()
        self._restart_diagrams(
            single_state_seed(width, states=self.state.states)
        )
        self._status(
            f"1D seed width: {self.seed_width_label()}; diagram restarted.",
            3.0,
        )

    @staticmethod
    def _matching_memory_row(row: CellRow, target: CellRow) -> CellRow:
        """Return valid second-order memory even after direct legacy mutation."""
        return row if len(row) == len(target) else tuple(0 for _ in target)

    def _comparison_snapshot(self) -> dict[str, Any]:
        """Capture a synchronized comparison trajectory with legacy fallbacks."""
        rows = self.state.comparison_rows
        synchronized = (
            self.state.comparison_enabled
            and len(rows) == len(self.state.rows)
            and all(
                len(comparison) == len(primary)
                for primary, comparison in zip(self.state.rows, rows)
            )
        )
        if not synchronized:
            rows = list(self.state.rows)
        row_backgrounds = self._matching_background_history(
            (
                self.state.comparison_row_backgrounds
                if synchronized
                else self.state.row_backgrounds
            ),
            rows,
            (
                self.state.comparison_background
                if synchronized
                else self.state.background
            ),
        )
        latest = rows[-1]
        previous = self._matching_memory_row(
            self.state.comparison_previous_row
            if synchronized
            else self.state.previous_row,
            latest,
        )
        return {
            "enabled": self.state.comparison_enabled,
            "rule": self.state.comparison_rule,
            "rows": [list(row) for row in rows],
            "row_backgrounds": row_backgrounds,
            "previous_row": list(previous),
            "background": (
                self.state.comparison_background
                if synchronized
                else self.state.background
            ),
            "previous_background": (
                self.state.comparison_previous_background
                if synchronized
                else self.state.previous_background
            ),
        }

    def snapshot(self) -> dict[str, Any]:
        """Return the complete diagram and camera state for session storage."""
        row_backgrounds = self._matching_background_history(
            self.state.row_backgrounds,
            self.state.rows,
            self.state.background,
        )
        return {
            "rule": self.state.rule,
            "rule_spec": self.rule_spec.as_dict(),
            "custom_rule": (
                self.state.custom_rule.as_document()
                if self.state.custom_rule is not None
                else None
            ),
            "boundary": self.state.boundary,
            "background": self.state.background,
            "previous_background": self.state.previous_background,
            "rule_change_reset": self.state.rule_change_reset,
            "seed_width_mode": self.state.seed_width_mode,
            "seed": list(self.state.seed),
            "rows": [list(row) for row in self.state.rows],
            "row_backgrounds": row_backgrounds,
            "previous_row": list(
                self._matching_memory_row(
                    self.state.previous_row,
                    self.state.rows[-1],
                )
            ),
            "comparison": self._comparison_snapshot(),
            "generation": self.state.generation,
            "camera": {
                "cell_size": self.state.cell_size,
                "offset": [
                    self.state.view_offset_x,
                    self.state.view_offset_y,
                ],
            },
            "rng": encode_random_state(self.state.rng),
        }

    def _timeline_snapshot(self) -> dict[str, Any]:
        """Capture simulation state without camera or transient controls."""
        row_backgrounds = self._matching_background_history(
            self.state.row_backgrounds,
            self.state.rows,
            self.state.background,
        )
        return {
            "rule": self.state.rule,
            "rule_spec": self.rule_spec.as_dict(),
            "custom_rule": (
                self.state.custom_rule.as_document()
                if self.state.custom_rule is not None
                else None
            ),
            "boundary": self.state.boundary,
            "background": self.state.background,
            "previous_background": self.state.previous_background,
            "rule_change_reset": self.state.rule_change_reset,
            "seed_width_mode": self.state.seed_width_mode,
            "seed": list(self.state.seed),
            "rows": [list(row) for row in self.state.rows],
            "row_backgrounds": row_backgrounds,
            "previous_row": list(
                self._matching_memory_row(
                    self.state.previous_row,
                    self.state.rows[-1],
                )
            ),
            "comparison": self._comparison_snapshot(),
            "generation": self.state.generation,
        }

    @staticmethod
    def _spec_from_snapshot(snapshot: Mapping[str, Any]) -> RuleSpec:
        rule_spec = snapshot.get("rule_spec")
        if isinstance(rule_spec, Mapping):
            return RuleSpec.from_mapping(rule_spec)
        return RuleSpec(FAMILY_ELEMENTARY, validate_rule(snapshot["rule"]), 2, 1)

    def _restore_simulation_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        """Restore trusted generalized state with legacy Elementary defaults."""
        spec = self._spec_from_snapshot(snapshot)
        rows = [normalize_state_row(row, spec.states) for row in snapshot["rows"]]
        seed = normalize_state_row(snapshot["seed"], spec.states)
        previous_row = normalize_state_row(
            snapshot.get("previous_row", tuple(0 for _ in rows[-1])),
            spec.states,
        )
        comparison = snapshot.get("comparison")
        comparison_mapping = comparison if isinstance(comparison, Mapping) else {}
        comparison_rule = int(
            comparison_mapping.get("rule", min(90, spec.max_code))
        )
        comparison_rule = max(0, min(spec.max_code, comparison_rule))
        comparison_rows = [
            normalize_state_row(row, spec.states)
            for row in comparison_mapping.get("rows", rows)
        ]
        row_backgrounds = [
            int(value)
            for value in snapshot.get(
                "row_backgrounds",
                [0] * max(0, len(rows) - 1) + [int(snapshot["background"])],
            )
        ]
        if len(row_backgrounds) != len(rows):
            row_backgrounds = [0] * max(0, len(rows) - 1) + [
                int(snapshot["background"])
            ]
        comparison_background = int(
            comparison_mapping.get("background", snapshot["background"])
        )
        comparison_background_fallback = [0] * max(
            0,
            len(comparison_rows) - 1,
        ) + [comparison_background]
        comparison_row_backgrounds = [
            int(value)
            for value in comparison_mapping.get(
                "row_backgrounds",
                comparison_background_fallback,
            )
        ]
        if len(comparison_row_backgrounds) != len(comparison_rows):
            comparison_row_backgrounds = comparison_background_fallback
        comparison_previous_row = normalize_state_row(
            comparison_mapping.get(
                "previous_row",
                tuple(0 for _ in comparison_rows[-1]),
            ),
            spec.states,
        )

        self.state.family = spec.family
        self.state.rule = spec.code
        self.state.states = spec.states
        self.state.radius = spec.radius
        self.state.custom_rule = None
        custom_document = snapshot.get("custom_rule")
        if isinstance(custom_document, Mapping):
            custom_rule = custom_rule_from_document(custom_document)
            if (
                custom_rule.dimension != "1d"
                or custom_rule.one_dimensional_spec() != spec
            ):
                raise ValueError(
                    "Embedded 1D custom rule does not match its rule spec."
                )
            self.state.custom_rule = custom_rule
        self.state.boundary = str(snapshot["boundary"])
        self.state.background = int(snapshot["background"])
        self.state.previous_background = int(snapshot.get("previous_background", 0))
        self.state.rule_change_reset = bool(snapshot["rule_change_reset"])
        seed_width_mode = str(
            snapshot.get("seed_width_mode", SEED_WIDTH_COMPACT)
        )
        self.state.seed_width_mode = (
            seed_width_mode
            if seed_width_mode in SEED_WIDTH_MODES
            else SEED_WIDTH_COMPACT
        )
        self.state.seed = seed
        self.state.rows = rows
        self.state.row_backgrounds = row_backgrounds
        self.state.previous_row = previous_row
        self.state.comparison_enabled = bool(comparison_mapping.get("enabled", False))
        self.state.comparison_rule = comparison_rule
        self.state.comparison_rows = comparison_rows
        self.state.comparison_row_backgrounds = comparison_row_backgrounds
        self.state.comparison_previous_row = comparison_previous_row
        self.state.comparison_background = comparison_background
        self.state.comparison_previous_background = int(
            comparison_mapping.get("previous_background", 0)
        )
        self.state.generation = int(snapshot["generation"])
        self.state.brush_state = min(self.state.brush_state, spec.states - 1)

    def _restore_timeline_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        """Restore a trusted frame and keep its latest row visible."""
        previous_width = len(self.state.rows[-1])
        self._restore_simulation_snapshot(snapshot)
        self.state.rule_menu_active = False
        self.state.drawing = False
        self.state.stroke_history_pending = False
        if len(self.state.rows[-1]) != previous_width:
            self.center_view()
        else:
            self.follow_latest()
        self._invalidate()
        self.services.rebuild_sidebar()

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        """Restore a prevalidated complete generalized 1D workspace snapshot."""
        spec = self._spec_from_snapshot(snapshot)
        rows = [normalize_state_row(row, spec.states) for row in snapshot["rows"]]
        if not rows:
            raise ValueError("1D session must contain at least one row.")
        boundary = snapshot["boundary"]
        if boundary not in (BOUNDARY_INFINITE, BOUNDARY_FIXED, BOUNDARY_WRAP):
            raise ValueError(f"Unknown 1D boundary: {boundary}")
        background = snapshot["background"]
        if (
            isinstance(background, bool)
            or not isinstance(background, int)
            or not 0 <= background < spec.states
        ):
            raise ValueError("1D background does not fit the state count.")
        generation = snapshot["generation"]
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise TypeError("1D generation must be an integer.")
        if generation < 0:
            raise ValueError("1D generation cannot be negative.")
        rule_change_reset = snapshot["rule_change_reset"]
        if not isinstance(rule_change_reset, bool):
            raise TypeError("Rule-change behavior must be true or false.")
        camera = snapshot["camera"]
        cell_size = int(camera["cell_size"])
        offset_x, offset_y = camera["offset"]

        self._restore_simulation_snapshot(snapshot)
        restore_random_state(self.state.rng, snapshot["rng"])
        if len(self.state.previous_row) != len(self.state.rows[-1]):
            raise ValueError("Previous 1D row must match the latest row width.")
        if not self.state.comparison_rows:
            raise ValueError("Comparison diagram must contain at least one row.")
        if len(self.state.comparison_previous_row) != len(
            self.state.comparison_rows[-1]
        ):
            raise ValueError("Comparison previous row must match its latest row.")
        self.state.cell_size = max(
            ECA_MIN_CELL_SIZE,
            min(ECA_MAX_CELL_SIZE, cell_size),
        )
        self.state.view_offset_x = int(offset_x)
        self.state.view_offset_y = int(offset_y)
        self.state.rule_menu_active = False
        self.state.rule_menu_input = ""
        self.state.drawing = False
        self.state.stroke_history_pending = False
        self.services.set_running(False)
        self._invalidate()
        self.reset_history()

    def experiment_snapshot(self) -> dict[str, Any]:
        """Return a reusable rule/boundary/current-row experiment setup."""
        return {
            "rule": self.state.rule,
            "rule_spec": self.rule_spec.as_dict(),
            "custom_rule": (
                self.state.custom_rule.as_document()
                if self.state.custom_rule is not None
                else None
            ),
            "boundary": self.state.boundary,
            "background": self.state.background,
            "rule_change_reset": self.state.rule_change_reset,
            "seed_width_mode": self.state.seed_width_mode,
            "seed": list(self.state.rows[-1]),
            "comparison": {
                "enabled": self.state.comparison_enabled,
                "rule": self.state.comparison_rule,
            },
            "rng": encode_random_state(self.state.rng),
        }

    def restore_experiment(self, experiment: Mapping[str, Any]) -> None:
        """Restart the workspace from a validated experiment profile."""
        spec = self._spec_from_snapshot(experiment)
        seed = normalize_state_row(experiment["seed"], spec.states)
        boundary = experiment["boundary"]
        if boundary not in (BOUNDARY_INFINITE, BOUNDARY_FIXED, BOUNDARY_WRAP):
            raise ValueError(f"Unknown 1D boundary: {boundary}")
        background = experiment["background"]
        if (
            isinstance(background, bool)
            or not isinstance(background, int)
            or not 0 <= background < spec.states
        ):
            raise ValueError("1D background does not fit the state count.")
        rule_change_reset = experiment["rule_change_reset"]
        if not isinstance(rule_change_reset, bool):
            raise TypeError("Rule-change behavior must be true or false.")
        seed_width_mode = str(
            experiment.get("seed_width_mode", SEED_WIDTH_COMPACT)
        )
        if seed_width_mode not in SEED_WIDTH_MODES:
            raise ValueError(f"Unknown 1D seed width mode: {seed_width_mode}")
        comparison = experiment.get("comparison")
        comparison_mapping = comparison if isinstance(comparison, Mapping) else {}
        comparison_rule = max(
            0,
            min(spec.max_code, int(comparison_mapping.get("rule", 0))),
        )
        restore_random_state(self.state.rng, experiment["rng"])

        self.save_history()
        custom_document = experiment.get("custom_rule")
        self.state.custom_rule = None
        if isinstance(custom_document, Mapping):
            custom_rule = custom_rule_from_document(custom_document)
            if (
                custom_rule.dimension != "1d"
                or custom_rule.one_dimensional_spec() != spec
            ):
                raise ValueError(
                    "Embedded 1D custom rule does not match its rule spec."
                )
            self.state.custom_rule = custom_rule
        self.state.family = spec.family
        self.state.rule = spec.code
        self.state.states = spec.states
        self.state.radius = spec.radius
        self.state.boundary = boundary
        self.state.background = background
        self.state.previous_background = 0
        self.state.rule_change_reset = rule_change_reset
        self.state.seed_width_mode = seed_width_mode
        self.state.seed = seed
        self.state.rows = [seed]
        self.state.row_backgrounds = [background]
        self.state.previous_row = tuple(0 for _ in seed)
        self.state.comparison_enabled = bool(
            comparison_mapping.get("enabled", False)
        )
        self.state.comparison_rule = comparison_rule
        self.state.comparison_rows = [seed]
        self.state.comparison_row_backgrounds = [background]
        self.state.comparison_previous_row = tuple(0 for _ in seed)
        self.state.comparison_background = background
        self.state.comparison_previous_background = 0
        self.state.generation = 0
        self.state.brush_state = min(self.state.brush_state, spec.states - 1)
        self.services.set_running(False)
        self.center_view()
        self._invalidate()
        self.services.rebuild_sidebar()
        self.sync_history()

    @staticmethod
    def boundary_label(boundary: str) -> str:
        return {
            BOUNDARY_INFINITE: "Infinite Background",
            BOUNDARY_FIXED: "Fixed Zero",
            BOUNDARY_WRAP: "Wrap",
        }[boundary]

    def set_rule(self, rule: int) -> None:
        validated_rule = self.rule_spec.with_code(rule).code
        if validated_rule == self.state.rule:
            self._status(f"Rule code {self.state.rule} is already selected.")
            return
        self.save_history()
        self.state.custom_rule = None
        self.state.rule = validated_rule
        if self.state.rule_change_reset:
            seed = single_state_seed(
                self.preferred_seed_width(),
                states=self.state.states,
            )
            self.state.boundary = BOUNDARY_INFINITE
            background = 0
            previous_row = None
            previous_background = 0
            restart_label = "canonical single-cell seed and infinite background"
        else:
            seed = self.state.rows[-1]
            background = self.state.background
            previous_row = self.state.previous_row
            previous_background = self.state.previous_background
            restart_label = "the current row"
        self._restart_diagrams(
            seed,
            background=background,
            previous_row=previous_row,
            previous_background=previous_background,
        )
        self._status(
            f"{self.family_name} code {self.state.rule} selected; "
            f"restarted from {restart_label}.",
            4.0,
        )

    def load_canonical_elementary_rule(self, rule: int) -> None:
        """Load one tutorial rule under reproducible canonical conditions."""
        validated_rule = validate_rule(rule)
        self.save_history()
        self.state.custom_rule = None
        self.state.family = FAMILY_ELEMENTARY
        self.state.rule = validated_rule
        self.state.states = 2
        self.state.radius = 1
        self.state.brush_state = 1
        self.state.boundary = BOUNDARY_INFINITE
        self.state.rule_change_reset = True
        self.state.comparison_enabled = False
        self.state.comparison_rule = 90 if validated_rule != 90 else 30
        self._restart_diagrams(
            single_state_seed(
                self.preferred_seed_width(),
                states=2,
            )
        )
        self._status(
            f"Tutorial experiment loaded: Rule {validated_rule}, centered "
            "single-cell seed, infinite state-0 background.",
            5.0,
        )

    def adjust_rule(self, delta: int) -> None:
        self.set_rule((self.state.rule + delta) % (self.rule_spec.max_code + 1))

    def next_featured_rule(self) -> int:
        if self.state.family != FAMILY_ELEMENTARY:
            return default_rule_spec(
                self.state.family,
                states=self.state.states,
                radius=self.state.radius,
            ).code
        for preset in RULE_PRESETS:
            if preset > self.state.rule:
                return preset
        return RULE_PRESETS[0]

    def cycle_featured_rule(self) -> None:
        self.set_rule(self.next_featured_rule())

    def _restart_diagrams(
        self,
        seed: CellRow,
        *,
        background: int = 0,
        previous_row: CellRow | None = None,
        previous_background: int = 0,
    ) -> None:
        """Restart primary and comparison trajectories from one shared seed."""
        seed = normalize_state_row(seed, self.state.states)
        prior = normalize_state_row(
            previous_row if previous_row is not None else (0 for _ in seed),
            self.state.states,
        )
        if len(prior) != len(seed):
            prior = tuple(0 for _ in seed)
        self.state.seed = seed
        self.state.rows = [seed]
        self.state.row_backgrounds = [background]
        self.state.previous_row = prior
        self.state.comparison_rows = [seed]
        self.state.comparison_row_backgrounds = [background]
        self.state.comparison_previous_row = prior
        self.state.background = background
        self.state.previous_background = previous_background
        self.state.comparison_background = background
        self.state.comparison_previous_background = previous_background
        self.state.generation = 0
        self.services.set_running(False)
        self.center_view()
        self._invalidate()
        self.services.rebuild_sidebar()
        self.sync_history()

    def cycle_rule_family(self) -> None:
        """Select the next generalized rule family and its canonical preset."""
        self.save_history()
        self.state.custom_rule = None
        current_index = RULE_FAMILIES.index(self.state.family)
        family = RULE_FAMILIES[(current_index + 1) % len(RULE_FAMILIES)]
        spec = default_rule_spec(family)
        self.state.family = spec.family
        self.state.rule = spec.code
        self.state.states = spec.states
        self.state.radius = spec.radius
        self.state.comparison_rule = min(
            spec.max_code,
            90 if family == FAMILY_ELEMENTARY else (spec.code + 1),
        )
        self.state.brush_state = 1
        self.state.boundary = BOUNDARY_INFINITE
        self._restart_diagrams(
            single_state_seed(
                self.preferred_seed_width(),
                states=spec.states,
            )
        )
        self._status(
            f"1D family: {spec.definition.name}. {spec.definition.summary}",
            5.0,
        )

    def cycle_state_count(self) -> None:
        if self.state.family not in (FAMILY_TOTALISTIC, FAMILY_MULTISTATE):
            self._status("This family has a fixed two-state alphabet.")
            return
        choices = (2, 3, 4) if self.state.family == FAMILY_TOTALISTIC else (3, 4)
        next_states = choices[(choices.index(self.state.states) + 1) % len(choices)]
        spec = default_rule_spec(
            self.state.family,
            states=next_states,
            radius=self.state.radius,
        )
        self.save_history()
        self.state.custom_rule = None
        self.state.rule = spec.code
        self.state.states = spec.states
        self.state.comparison_rule = min(spec.max_code, spec.code + 1)
        self.state.brush_state = 1
        self._restart_diagrams(
            single_state_seed(
                self.preferred_seed_width(),
                states=spec.states,
            )
        )
        self._status(f"State count changed to {spec.states}; diagram restarted.")

    def cycle_radius(self) -> None:
        if self.state.family not in (FAMILY_TOTALISTIC, FAMILY_RADIUS):
            self._status("This family has a fixed radius of one.")
            return
        choices = (1, 2, 3) if self.state.family == FAMILY_TOTALISTIC else (2, 3)
        next_radius = choices[(choices.index(self.state.radius) + 1) % len(choices)]
        spec = default_rule_spec(
            self.state.family,
            states=self.state.states,
            radius=next_radius,
        )
        self.save_history()
        self.state.custom_rule = None
        self.state.rule = spec.code
        self.state.radius = spec.radius
        self.state.comparison_rule = min(spec.max_code, spec.code + 1)
        self._restart_diagrams(
            single_state_seed(
                self.preferred_seed_width(),
                states=spec.states,
            )
        )
        self._status(f"Neighborhood radius changed to {spec.radius}.")

    def apply_custom_rule(self, rule: CustomRuleDefinition) -> None:
        """Load a named 1D recipe under reproducible seed conditions."""

        if rule.dimension != "1d":
            raise ValueError("Custom rule does not belong to the 1D workspace.")
        spec = rule.one_dimensional_spec()
        if self.state.custom_rule is not None and self.state.custom_rule.key == rule.key:
            self._status(f"Custom rule '{rule.name}' is already active.")
            return
        self.save_history()
        self.state.family = spec.family
        self.state.rule = spec.code
        self.state.states = spec.states
        self.state.radius = spec.radius
        self.state.custom_rule = rule
        self.state.brush_state = min(max(1, self.state.brush_state), spec.states - 1)
        self.state.comparison_rule = min(spec.max_code, spec.code + 1)
        self.state.comparison_enabled = False
        self.state.boundary = BOUNDARY_INFINITE
        self._restart_diagrams(
            single_state_seed(self.preferred_seed_width(), states=spec.states)
        )
        self._status(
            f"Custom 1D rule: {rule.name} · {rule.notation}. Canonical seed loaded.",
            5.0,
        )

    def toggle_comparison(self) -> None:
        self.save_history()
        self.state.comparison_enabled = not self.state.comparison_enabled
        if self.state.comparison_rule > self.rule_spec.max_code:
            self.state.comparison_rule = min(90, self.rule_spec.max_code)
        seed = self.state.rows[-1]
        self._restart_diagrams(seed)
        label = "enabled" if self.state.comparison_enabled else "disabled"
        self._status(f"Side-by-side rule comparison {label}; diagram restarted.")

    def adjust_comparison_rule(self, delta: int) -> None:
        if not self.state.comparison_enabled:
            self.toggle_comparison()
            return
        maximum = self.rule_spec.max_code
        new_code = (self.state.comparison_rule + delta) % (maximum + 1)
        if new_code == self.state.comparison_rule:
            return
        self.save_history()
        self.state.comparison_rule = new_code
        self._restart_diagrams(self.state.seed)
        self._status(f"Comparison rule code changed to {new_code}.")

    def cycle_brush_state(self) -> None:
        self.state.brush_state = self.state.brush_state % (self.state.states - 1) + 1
        self.services.rebuild_sidebar()
        self._status(f"1D brush state: {self.state.brush_state}.")

    def toggle_rule_change_reset(self) -> None:
        self.save_history()
        self.state.rule_change_reset = not self.state.rule_change_reset
        self.services.rebuild_sidebar()
        label = (
            "Canonical Reset"
            if self.state.rule_change_reset
            else "Keep Current Row"
        )
        self.sync_history()
        self._status(f"Rule-change behavior: {label}.")

    def toggle_boundary(self) -> None:
        self.save_history()
        boundaries = (BOUNDARY_INFINITE, BOUNDARY_FIXED, BOUNDARY_WRAP)
        current_index = boundaries.index(self.state.boundary)
        self.state.boundary = boundaries[(current_index + 1) % len(boundaries)]
        self._restart_diagrams(self.state.rows[-1])
        self._status(
            f"1D boundary: {self.boundary_label(self.state.boundary)}; "
            "diagram restarted."
        )

    def mouse_to_column(self, position: tuple[int, int]) -> int | None:
        editor = self.editor_rect()
        if not editor.collidepoint(position):
            return None
        column = (position[0] - editor.x) // self.state.cell_size
        if 0 <= column < len(self.state.rows[-1]):
            return int(column)
        return None

    def draw_cell(self, column: int) -> None:
        target_value = self.state.drawing_value
        current = self.state.rows[-1]
        comparison_current = self.state.comparison_rows[-1]
        primary_unchanged = current[column] == target_value
        comparison_unchanged = (
            not self.state.comparison_enabled
            or comparison_current[column] == target_value
        )
        if primary_unchanged and comparison_unchanged:
            return
        if self.state.stroke_history_pending:
            self.save_history()
            self.state.stroke_history_pending = False
        edited = list(current)
        edited[column] = target_value
        self.state.rows[-1] = tuple(edited)
        if self.state.comparison_enabled:
            comparison_edited = list(comparison_current)
            comparison_edited[column] = target_value
            self.state.comparison_rows[-1] = tuple(comparison_edited)
        if self.state.generation == 0 and len(self.state.rows) == 1:
            self.state.seed = self.state.rows[-1]
        self.services.set_running(False)
        self._invalidate()

    def open_rule_menu(self) -> None:
        if self.state.family != FAMILY_ELEMENTARY:
            self._status("The 0-255 catalogue is available for Elementary rules.")
            return
        self.state.rule_menu_target = "primary"
        self.state.rule_menu_active = True
        self.state.rule_menu_input = ""
        self.state.rule_menu_favorites_only = False
        self.services.set_running(False)

    def open_comparison_rule_menu(self) -> None:
        """Open the Elementary catalogue with the secondary rule selected."""
        if self.state.family != FAMILY_ELEMENTARY:
            self._status("Direct catalogue selection is available for Elementary rules.")
            return
        if not self.state.comparison_enabled:
            self.toggle_comparison()
        self.state.rule_menu_target = "comparison"
        self.state.rule_menu_active = True
        self.state.rule_menu_input = ""
        self.state.rule_menu_favorites_only = False
        self.services.set_running(False)

    def _catalog_rule(self) -> int:
        return (
            self.state.comparison_rule
            if self.state.rule_menu_target == "comparison"
            else self.state.rule
        )

    def _set_catalog_rule(self, rule: int) -> None:
        if self.state.rule_menu_target == "comparison":
            delta = rule - self.state.comparison_rule
            self.adjust_comparison_rule(delta)
        else:
            self.set_rule(rule)

    def _adjust_catalog_rule(self, delta: int) -> None:
        if self.state.rule_menu_target == "comparison":
            self.adjust_comparison_rule(delta)
        else:
            self.adjust_rule(delta)

    def close_rule_menu(self) -> None:
        self.state.rule_menu_active = False

    def filtered_catalog_rules(self) -> tuple[int, ...]:
        """Return catalogue rules matching the numeric search and favorite filter."""
        favorites = self.services.favorite_rules()
        query = self.state.rule_menu_input
        return tuple(
            rule
            for rule in range(256)
            if (not query or query in str(rule))
            and (not self.state.rule_menu_favorites_only or rule in favorites)
        )

    def rule_menu_geometry(
        self,
    ) -> tuple[pygame.Rect, list[tuple[int, pygame.Rect]]]:
        window_width, window_height = self.services.window_size()
        modal_width = min(820, window_width - 40)
        modal_height = min(540, window_height - 40)
        modal = pygame.Rect(0, 0, modal_width, modal_height)
        modal.center = (window_width // 2, window_height // 2)

        columns = 16
        rules = self.filtered_catalog_rules()
        rows = max(1, (len(rules) + columns - 1) // columns)
        gap = 2
        grid_top = modal.y + 88
        grid_bottom = modal.bottom - 45
        card_width = (modal.width - 40 - gap * (columns - 1)) // columns
        card_height = min(
            24,
            max(12, (grid_bottom - grid_top - gap * (rows - 1)) // rows),
        )
        grid_width = columns * card_width + gap * (columns - 1)
        start_x = modal.centerx - grid_width // 2
        cards = []
        for index, rule in enumerate(rules):
            row, column = divmod(index, columns)
            cards.append(
                (
                    rule,
                    pygame.Rect(
                        start_x + column * (card_width + gap),
                        grid_top + row * (card_height + gap),
                        card_width,
                        card_height,
                    ),
                )
            )
        return modal, cards

    def handle_overlay_event(self, event: pygame.event.Event) -> bool:
        if not self.state.rule_menu_active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_e):
                self.close_rule_menu()
                return True
            if event.key == pygame.K_LEFT:
                self._adjust_catalog_rule(-1)
                self.state.rule_menu_input = ""
                return True
            if event.key == pygame.K_RIGHT:
                self._adjust_catalog_rule(1)
                self.state.rule_menu_input = ""
                return True
            if event.key == pygame.K_BACKSPACE:
                self.state.rule_menu_input = self.state.rule_menu_input[:-1]
                return True
            if event.key == pygame.K_f:
                self.state.rule_menu_favorites_only = (
                    not self.state.rule_menu_favorites_only
                )
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.state.rule_menu_input:
                    self._set_catalog_rule(int(self.state.rule_menu_input))
                    self.close_rule_menu()
                return True
            if pygame.K_0 <= event.key <= pygame.K_9:
                digit = str(event.key - pygame.K_0)
                candidate = (self.state.rule_menu_input + digit)[-3:]
                if int(candidate) <= 255:
                    self.state.rule_menu_input = candidate
                else:
                    self._status("Elementary rule numbers range from 0 to 255.")
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            modal, cards = self.rule_menu_geometry()
            for rule, card in cards:
                if card.collidepoint(event.pos):
                    if event.button == 3:
                        selected = self.services.toggle_favorite_rule(rule)
                        label = "added to" if selected else "removed from"
                        self._status(f"Rule {rule} {label} favorites.")
                    else:
                        self._set_catalog_rule(rule)
                        self.close_rule_menu()
                    return True
            if not modal.collidepoint(event.pos):
                self.close_rule_menu()
            return True
        return True

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_e:
            self.open_rule_menu()
            return True
        if event.key == pygame.K_m:
            self._status("Simulation modes belong to the 2D workspace; press D to switch.")
            return True
        if event.key == pygame.K_t:
            self._status(
                "The 1D workspace uses rule and boundary controls in the sidebar."
            )
            return True
        return False

    def handle_pointer_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (1, 3):
                column = self.mouse_to_column(event.pos)
                if column is not None:
                    self.state.drawing = True
                    self.state.drawing_value = (
                        self.state.brush_state if event.button == 1 else 0
                    )
                    self.state.stroke_history_pending = True
                    self.draw_cell(column)
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            self.state.drawing = False
            self.state.stroke_history_pending = False
            self.sync_history()
            return True
        if event.type == pygame.MOUSEMOTION:
            if self.state.drawing:
                column = self.mouse_to_column(event.pos)
                if column is not None:
                    self.draw_cell(column)
            elif event.buttons[1]:
                self.state.view_offset_x += event.rel[0]
                self.state.view_offset_y += event.rel[1]
            return True
        return False

    def build_sidebar(self, menu: Menu) -> None:
        accent = DIMENSION_BY_KEY["1d"].accent
        menu.clear_buttons()
        rule_heading = (
            self.state.custom_rule.name
            if self.state.custom_rule is not None
            else self.family_name
        )
        menu.set_header(f"1D · {rule_heading}")
        menu.begin_section(
            "1d_workspace",
            "Workspace",
            tooltip="Open global navigation, saved experiments, analysis, export, and help.",
        )
        menu.add_button(
            "Select Dimension (D)",
            self.services.activate_dimension_menu,
            accent=accent,
            tooltip="Switch between the 1D and 2D workspaces without losing state.",
        )
        menu.add_button(
            "Session & Profiles (P)",
            self.services.activate_session_menu,
            accent=(80, 190, 145),
            tooltip="Save, load, or reopen a recently used experiment.",
        )
        menu.add_button(
            "Scientific Analysis (I)",
            self.services.activate_analysis,
            accent=(90, 195, 255),
            tooltip="Inspect population, density, entropy, change rate, and periods.",
        )
        menu.add_button(
            "Experiment Lab (Shift+I)",
            self.services.activate_experiment_lab,
            accent=(90, 220, 130),
            tooltip="Compare selected rules, boundaries, sizes, seeds, and run lengths.",
        )
        menu.add_button(
            "Export Results (X)",
            self.services.activate_export,
            accent=(235, 155, 70),
            tooltip="Export the diagram, animation, metrics, or experiment JSON.",
        )
        menu.add_button(
            "Tutorial: How 1D Works (F2)",
            self.services.activate_tutorial,
            accent=(75, 175, 235),
            tooltip="Open a full-screen visual guide to 1D rules, history, and controls.",
        )
        menu.add_button(
            "Keyboard Help (F1)",
            self.services.activate_help,
            accent=(180, 150, 245),
            tooltip="Show all common and 1D-specific keyboard shortcuts.",
        )
        menu.begin_section(
            "1d_rules",
            "Rule & Comparison",
            tooltip="Choose a rule family and compare two rules under equal conditions.",
        )
        menu.add_button(
            "Custom Rule Studio",
            self.services.activate_custom_rule_studio,
            accent=(245, 185, 70),
            active=self.state.custom_rule is not None,
            tooltip="Create, browse, apply, or delete named 1D rule recipes.",
        )
        menu.add_button(
            f"Family: {self.family_name}",
            self.cycle_rule_family,
            accent=accent,
        )
        if self.state.family == FAMILY_ELEMENTARY:
            menu.add_button(
                "Browse Rules 0–255 (E)",
                self.open_rule_menu,
                accent=accent,
            )
            menu.add_button(
                f"Next Featured: {self.next_featured_rule()}",
                self.cycle_featured_rule,
                accent=(225, 182, 70),
            )
        else:
            menu.add_button(
                f"Code: {short_rule_code(self.state.rule)}",
                self.cycle_featured_rule,
                accent=(225, 182, 70),
            )
        rule_term = "Rule" if self.state.family == FAMILY_ELEMENTARY else "Code"
        menu.add_button(
            f"Previous {rule_term}: {short_rule_code((self.state.rule - 1) % (self.rule_spec.max_code + 1))}",
            lambda: self.adjust_rule(-1),
        )
        menu.add_button(
            f"Next {rule_term}: {short_rule_code((self.state.rule + 1) % (self.rule_spec.max_code + 1))}",
            lambda: self.adjust_rule(1),
        )
        if self.state.family in (FAMILY_TOTALISTIC, FAMILY_MULTISTATE):
            menu.add_button(
                f"States: {self.state.states}",
                self.cycle_state_count,
            )
        if self.state.family in (FAMILY_TOTALISTIC, FAMILY_RADIUS):
            menu.add_button(
                f"Radius: {self.state.radius}",
                self.cycle_radius,
            )
        if self.state.states > 2:
            menu.add_button(
                f"Brush State: {self.state.brush_state}",
                self.cycle_brush_state,
                accent=accent,
            )
        menu.add_button(
            f"Compare: {'On' if self.state.comparison_enabled else 'Off'}",
            self.toggle_comparison,
            active=self.state.comparison_enabled,
            accent=(235, 170, 70),
        )
        if self.state.comparison_enabled:
            if self.state.family == FAMILY_ELEMENTARY:
                menu.add_button(
                    f"Compare Rule: {self.state.comparison_rule}",
                    self.open_comparison_rule_menu,
                    accent=(235, 170, 70),
                )
            menu.add_button(
                f"Compare −: {short_rule_code((self.state.comparison_rule - 1) % (self.rule_spec.max_code + 1))}",
                lambda: self.adjust_comparison_rule(-1),
            )
            menu.add_button(
                f"Compare +: {short_rule_code((self.state.comparison_rule + 1) % (self.rule_spec.max_code + 1))}",
                lambda: self.adjust_comparison_rule(1),
            )
        menu.begin_section(
            "1d_experiment",
            "Seed & Boundary",
            tooltip="Control restart behavior, boundary conditions, and initial rows.",
        )
        reset_label = (
            "Canonical Reset"
            if self.state.rule_change_reset
            else "Keep Current Row"
        )
        menu.add_button(
            f"Rule Change: {reset_label}",
            self.toggle_rule_change_reset,
            active=self.state.rule_change_reset,
        )
        menu.add_button(
            f"Boundary: {self.boundary_label(self.state.boundary)}",
            self.toggle_boundary,
        )
        menu.add_button(
            f"Seed Width: {self.seed_width_label()}",
            self.cycle_seed_width,
            tooltip=(
                "Cycle Compact, Viewport, and Wide starting widths. "
                "Changing width restarts from a centered single cell."
            ),
        )
        menu.add_button("Seed: Single Center", self.use_single_seed)
        menu.add_button("Seed: Random", self.randomize)
        menu.add_button("Clear Diagram", self.clear)
        menu.begin_section(
            "1d_view",
            "View",
            expanded=False,
            tooltip="Change grid visibility, accessible palette, and camera position.",
        )
        menu.add_button(
            f"Grid Lines: {'On' if self.services.show_grid() else 'Off'}",
            self.services.toggle_grid,
            active=self.services.show_grid(),
        )
        menu.add_button(
            f"Theme: {self.services.theme_name().title()}",
            self.services.cycle_theme,
        )
        menu.add_button("Center Diagram", self.center_view)


class ElementaryWorkspaceRenderer(WorkspaceRenderer):
    """Render generalized 1D state and the Elementary rule catalogue."""

    render_key = "1d:elementary_ca"

    def __init__(
        self,
        controller: ElementaryWorkspaceController,
        services: ElementaryWorkspaceServices,
    ) -> None:
        self.controller = controller
        self.services = services
        self.diagram_backend = "auto"
        self.last_diagram_backend = "rects"
        self._rasterizer = StateGridRasterizer()

    @property
    def state(self) -> ElementaryWorkspaceState:
        return self.controller.state

    @property
    def cache_identity(self) -> str:
        return ECA_RENDER_KEY

    def cache_key(self) -> tuple[Any, ...]:
        viewport = self.services.viewport()
        return (
            self.services.render_revision(ECA_RENDER_KEY),
            viewport.size,
            self.controller.grid_origin(),
            (
                self.controller.grid_origin(comparison=True)
                if self.state.comparison_enabled
                else None
            ),
            self.controller.editor_rect(),
            self.state.cell_size,
            self.state.family,
            self.state.states,
            self.state.comparison_enabled,
            self.state.comparison_rule,
            self.services.theme_name(),
            self.services.show_grid(),
        )

    @staticmethod
    def _fit_text(font: pygame.font.Font, value: str, width: int) -> str:
        if font.size(value)[0] <= width:
            return value
        ellipsis = "..."
        shortened = value
        while shortened and font.size(shortened + ellipsis)[0] > width:
            shortened = shortened[:-1]
        return shortened.rstrip() + ellipsis

    def _state_color(
        self,
        value: int,
        *,
        secondary: bool = False,
    ) -> tuple[int, int, int]:
        """Return a stable palette color for a non-zero finite state."""
        return one_d_state_color(
            value,
            self.state.states,
            self.services.theme_name(),
            secondary=secondary,
        )

    def _draw_virtual_grid(
        self,
        pane: pygame.Rect,
        origin: tuple[int, int],
        *,
        top_padding: int = 0,
    ) -> None:
        """Draw an origin-aligned grid over visible finite and virtual cells."""
        if not self.services.show_grid() or self.state.cell_size < 4:
            return
        screen = self.services.screen()
        line_color = THEMES[self.services.theme_name()]["grid"]
        origin_x, origin_y = origin
        size = self.state.cell_size
        grid_top = min(pane.bottom, pane.top + top_padding)
        first_x = origin_x + (
            (pane.left - origin_x + size - 1) // size
        ) * size
        first_y = origin_y + (
            (grid_top - origin_y + size - 1) // size
        ) * size
        for x in range(first_x, pane.right + 1, size):
            pygame.draw.line(screen, line_color, (x, grid_top), (x, pane.bottom))
        for y in range(first_y, pane.bottom + 1, size):
            pygame.draw.line(screen, line_color, (pane.left, y), (pane.right, y))

    def _draw_diagram(
        self,
        rows: list[CellRow],
        row_backgrounds: list[int],
        pane: pygame.Rect,
        origin: tuple[int, int],
        *,
        secondary: bool,
        label: str | None,
    ) -> None:
        screen = self.services.screen()
        old_clip = screen.get_clip()
        screen.set_clip(pane)
        if label is not None:
            label_surface = self.services.tiny_font().render(
                label,
                True,
                self._state_color(1, secondary=secondary),
            )
            screen.blit(label_surface, (pane.x + 7, pane.y + 3))

        bounds = self._visible_diagram_bounds(rows, pane, origin)
        use_surfarray = self._should_use_surfarray(rows, bounds)
        if use_surfarray:
            self._draw_diagram_surfarray(
                rows,
                row_backgrounds,
                origin,
                bounds,
                secondary=secondary,
            )
            self.last_diagram_backend = "surfarray"
        else:
            self._draw_diagram_rects(
                rows,
                row_backgrounds,
                pane,
                origin,
                secondary=secondary,
            )
            self.last_diagram_backend = "rects"
        self._draw_virtual_grid(
            pane,
            origin,
            top_padding=20 if label is not None else 0,
        )
        current_width = len(rows[-1])
        newest = pygame.Rect(
            origin[0],
            origin[1] + (len(rows) - 1) * self.state.cell_size,
            current_width * self.state.cell_size,
            self.state.cell_size,
        )
        pygame.draw.rect(
            screen,
            self._state_color(1, secondary=secondary),
            newest,
            1,
        )
        screen.set_clip(old_clip)

    def _visible_diagram_bounds(
        self,
        rows: list[CellRow],
        pane: pygame.Rect,
        origin: tuple[int, int],
    ) -> tuple[int, int, int, int]:
        """Return visible row and world-column bounds for a diagram pane."""
        size = self.state.cell_size
        origin_x, origin_y = origin
        first_row = max(0, (pane.top - origin_y) // self.state.cell_size)
        last_row = min(
            len(rows),
            (pane.bottom - origin_y + self.state.cell_size - 1)
            // self.state.cell_size,
        )
        first_col = (pane.left - origin_x) // size
        last_col = -(-(pane.right - origin_x) // size)
        return first_row, last_row, first_col, last_col

    def _should_use_surfarray(
        self,
        rows: list[CellRow],
        bounds: tuple[int, int, int, int],
    ) -> bool:
        """Choose bulk rendering for large, cell-aligned visible diagrams."""
        if self.diagram_backend not in {"auto", "rects", "surfarray"}:
            raise ValueError(f"Unknown 1D diagram backend: {self.diagram_backend}")
        if self.diagram_backend == "rects":
            return False
        first_row, last_row, first_col, last_col = bounds
        if first_row >= last_row or first_col >= last_col:
            return False
        current_width = len(rows[-1])
        aligned = all(
            (current_width - len(rows[row_index])) % 2 == 0
            for row_index in range(first_row, last_row)
        )
        if not aligned:
            return False
        visible_cells = (last_row - first_row) * (last_col - first_col)
        return (
            self.diagram_backend == "surfarray"
            or visible_cells >= ECA_SURFARRAY_CELL_THRESHOLD
        )

    def _draw_diagram_surfarray(
        self,
        rows: list[CellRow],
        row_backgrounds: list[int],
        origin: tuple[int, int],
        bounds: tuple[int, int, int, int],
        *,
        secondary: bool,
    ) -> None:
        """Rasterize the visible state plane with one surfarray transfer."""
        first_row, last_row, first_col, last_col = bounds
        current_width = len(rows[-1])
        visible_states = np.empty(
            (last_row - first_row, last_col - first_col),
            dtype=np.int16,
        )
        for target_row, row_index in enumerate(range(first_row, last_row)):
            row_data = rows[row_index]
            outside_state = (
                row_backgrounds[row_index]
                if row_index < len(row_backgrounds)
                else 0
            )
            visible_states[target_row].fill(outside_state)
            row_first_col = (current_width - len(row_data)) // 2
            copy_first = max(first_col, row_first_col)
            copy_last = min(last_col, row_first_col + len(row_data))
            if copy_first >= copy_last:
                continue
            source_first = copy_first - row_first_col
            source_last = copy_last - row_first_col
            target_first = copy_first - first_col
            target_last = copy_last - first_col
            visible_states[target_row, target_first:target_last] = row_data[
                source_first:source_last
            ]

        palette = tuple(
            self._state_color(value, secondary=secondary)
            for value in range(self.state.states)
        )
        self._rasterizer.blit(
            self.services.screen(),
            visible_states,
            palette,
            (
                origin[0] + first_col * self.state.cell_size,
                origin[1] + first_row * self.state.cell_size,
            ),
            cell_size=self.state.cell_size,
        )

    def _draw_diagram_rects(
        self,
        rows: list[CellRow],
        row_backgrounds: list[int],
        pane: pygame.Rect,
        origin: tuple[int, int],
        *,
        secondary: bool,
    ) -> None:
        """Draw small or non-cell-aligned diagrams with the legacy path."""
        screen = self.services.screen()
        origin_x, origin_y = origin
        first_row, last_row, _, _ = self._visible_diagram_bounds(
            rows,
            pane,
            origin,
        )
        current_width = len(rows[-1])
        for row_index in range(first_row, last_row):
            row_data = rows[row_index]
            row_origin_x = origin_x + (
                (current_width - len(row_data)) * self.state.cell_size // 2
            )
            first_col = max(
                0,
                (pane.left - row_origin_x) // self.state.cell_size,
            )
            last_col = min(
                len(row_data),
                (pane.right - row_origin_x + self.state.cell_size - 1)
                // self.state.cell_size,
            )
            y = origin_y + row_index * self.state.cell_size
            outside_state = (
                row_backgrounds[row_index]
                if row_index < len(row_backgrounds)
                else 0
            )
            if outside_state:
                row_right = row_origin_x + len(row_data) * self.state.cell_size
                color = self._state_color(
                    outside_state,
                    secondary=secondary,
                )
                left_edge = min(max(row_origin_x, pane.left), pane.right)
                right_edge = min(max(row_right, pane.left), pane.right)
                if left_edge > pane.left:
                    pygame.draw.rect(
                        screen,
                        color,
                        (pane.left, y, left_edge - pane.left, self.state.cell_size),
                    )
                if right_edge < pane.right:
                    pygame.draw.rect(
                        screen,
                        color,
                        (right_edge, y, pane.right - right_edge, self.state.cell_size),
                    )
            for column in range(first_col, last_col):
                value = row_data[column]
                rect = pygame.Rect(
                    row_origin_x + column * self.state.cell_size,
                    y,
                    self.state.cell_size,
                    self.state.cell_size,
                )
                if value:
                    pygame.draw.rect(
                        screen,
                        self._state_color(value, secondary=secondary),
                        rect,
                    )

    def draw_base(self) -> None:
        screen = self.services.screen()
        viewport = self.services.viewport()
        diagram_viewport = self.controller.diagram_viewport()
        editor = self.controller.editor_rect()
        theme = THEMES[self.services.theme_name()]
        tiny_font = self.services.tiny_font()

        old_clip = screen.get_clip()
        screen.set_clip(viewport)
        pygame.draw.rect(
            screen,
            theme["info_bar"],
            (viewport.x, viewport.y, viewport.width, ECA_EDITOR_HEIGHT),
        )
        label = (
            "Editable current row  ·  left click: state "
            f"{self.state.brush_state}  ·  right click: state 0"
        )
        screen.blit(
            tiny_font.render(label, True, theme["text"]),
            (viewport.x + 10, viewport.y + 5),
        )

        current_row = self.state.rows[-1]
        if self.state.boundary == BOUNDARY_INFINITE and self.state.background:
            outside_color = self._state_color(self.state.background)
            left_edge = min(max(editor.left, viewport.left), viewport.right)
            right_edge = min(max(editor.right, viewport.left), viewport.right)
            if left_edge > viewport.left:
                pygame.draw.rect(
                    screen,
                    outside_color,
                    (
                        viewport.left,
                        editor.y,
                        left_edge - viewport.left,
                        self.state.cell_size,
                    ),
                )
            if right_edge < viewport.right:
                pygame.draw.rect(
                    screen,
                    outside_color,
                    (
                        right_edge,
                        editor.y,
                        viewport.right - right_edge,
                        self.state.cell_size,
                    ),
                )
        for column, value in enumerate(current_row):
            x = editor.x + column * self.state.cell_size
            rect = pygame.Rect(x, editor.y, self.state.cell_size, self.state.cell_size)
            if rect.right < viewport.left or rect.left > viewport.right:
                continue
            if value:
                pygame.draw.rect(screen, self._state_color(value), rect)
        editor_pane = pygame.Rect(
            viewport.x,
            editor.y,
            viewport.width,
            editor.height,
        )
        self._draw_virtual_grid(editor_pane, editor.topleft)
        pygame.draw.rect(screen, self._state_color(1), editor, 1)
        pygame.draw.line(
            screen,
            theme["grid"],
            (viewport.x, diagram_viewport.y - 1),
            (viewport.right, diagram_viewport.y - 1),
        )

        panes = self.controller.diagram_panes()
        primary_label = None
        if self.state.comparison_enabled:
            primary_label = f"Primary · code {short_rule_code(self.state.rule)}"
        self._draw_diagram(
            self.state.rows,
            self.controller._matching_background_history(
                self.state.row_backgrounds,
                self.state.rows,
                self.state.background,
            ),
            panes[0],
            self.controller.grid_origin(),
            secondary=False,
            label=primary_label,
        )
        if self.state.comparison_enabled:
            self._draw_diagram(
                self.state.comparison_rows,
                self.controller._matching_background_history(
                    self.state.comparison_row_backgrounds,
                    self.state.comparison_rows,
                    self.state.comparison_background,
                ),
                panes[1],
                self.controller.grid_origin(comparison=True),
                secondary=True,
                label=(
                    "Comparison · code "
                    f"{short_rule_code(self.state.comparison_rule)}"
                ),
            )
            divider_x = (panes[0].right + panes[1].left) // 2
            pygame.draw.line(
                screen,
                theme["grid"],
                (divider_x, diagram_viewport.y),
                (divider_x, diagram_viewport.bottom),
            )
        screen.set_clip(old_clip)

    def draw_bars(self) -> None:
        screen = self.services.screen()
        window_width, window_height = self.services.window_size()
        theme = THEMES[self.services.theme_name()]
        width = max(1, window_width - self.services.menu_width)
        state_label = "Running" if self.services.is_running() else "Paused"
        pygame.draw.rect(
            screen,
            theme["info_bar"],
            (0, 0, width, self.services.info_bar_height),
        )
        rule_identity = (
            f"{self.state.custom_rule.name} ({self.controller.family_name} "
            f"{short_rule_code(self.state.rule)})"
            if self.state.custom_rule is not None
            else f"{self.controller.family_name}: {short_rule_code(self.state.rule)}"
        )
        info = (
            f"{state_label}   Dimension: 1D   {rule_identity}   "
            f"States: {self.state.states}   "
            f"Radius: {self.state.radius}   "
            f"Speed: {self.services.speed()} gen/s   "
            f"Generation: {self.state.generation}   Boundary: "
            f"{self.controller.boundary_label(self.state.boundary)}"
        )
        info_font = self.services.small_font()
        tool_width = min(220, max(150, width // 4))
        available_info_width = max(40, width - 120 - tool_width - 18)
        screen.blit(
            info_font.render(
                self._fit_text(info_font, info, available_info_width),
                True,
                theme["text"],
            ),
            (120, 11),
        )

        y = window_height - self.services.stats_height
        pygame.draw.rect(
            screen,
            theme["stats_bar"],
            (0, y, width, self.services.stats_height),
        )
        stats = self.services.cached_stats(
            ECA_RENDER_KEY,
            lambda: {
                **row_statistics(self.state.rows[-1], self.state.states),
                "diagram_active": sum(
                    value != 0 for row in self.state.rows for value in row
                ),
            },
        )
        current_width = len(self.state.rows[-1])
        history = self.controller.history_status()
        first_line = (
            f"Current row: {stats['active']}/{current_width} active   "
            f"Density: {stats['density']:.2f}%   Rows shown: "
            f"{len(self.state.rows)}   Diagram active cells: "
            f"{stats['diagram_active']}   Outside state: {self.state.background}   "
            f"Diversity: {stats['diversity']}/{self.state.states}   "
            f"Timeline: {history.cursor + 1}/{history.frame_count}"
        )
        if self.state.family == FAMILY_ELEMENTARY:
            outputs = "".join(str(value) for value in rule_bits(self.state.rule))
            rule_detail = f"111 110 101 100 011 010 001 000  →  {outputs}"
        else:
            rule_detail = self.controller.rule_spec.definition.summary
        comparison_detail = (
            "   ·   Comparison code: "
            f"{short_rule_code(self.state.comparison_rule)}"
            if self.state.comparison_enabled
            else ""
        )
        second_line = (
            f"{rule_detail}{comparison_detail}   ·   "
            "Time flows downward; the fixed editor changes the latest row."
        )
        stats_font = self.services.small_font()
        detail_font = self.services.tiny_font()
        screen.blit(
            stats_font.render(
                self._fit_text(stats_font, first_line, width - 20),
                True,
                theme["text"],
            ),
            (10, y + 8),
        )
        screen.blit(
            detail_font.render(
                self._fit_text(detail_font, second_line, width - 20),
                True,
                theme["text"],
            ),
            (10, y + 38),
        )

    def draw_modal(self) -> None:
        if not self.state.rule_menu_active:
            return
        screen = self.services.screen()
        window_width, window_height = self.services.window_size()
        dimmer = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 195))
        screen.blit(dimmer, (0, 0))
        modal, cards = self.controller.rule_menu_geometry()
        accent = DIMENSION_BY_KEY["1d"].accent
        pygame.draw.rect(screen, (25, 28, 36), modal, border_radius=12)
        pygame.draw.rect(screen, (210, 214, 224), modal, 2, border_radius=12)
        target_label = (
            "Comparison rule catalogue"
            if self.state.rule_menu_target == "comparison"
            else "Elementary rule catalogue"
        )
        screen.blit(
            self.services.large_font().render(
                f"{target_label} · 0–255",
                True,
                (245, 247, 250),
            ),
            (modal.x + 20, modal.y + 15),
        )
        selected_rule = self.controller._catalog_rule()
        binary = "".join(str(value) for value in rule_bits(selected_rule))
        detail = (
            f"Current: Rule {selected_rule} = {binary}₂   ·   "
            "gold: featured · star: favorite"
        )
        tiny_font = self.services.tiny_font()
        screen.blit(
            tiny_font.render(detail, True, (192, 198, 211)),
            (modal.x + 21, modal.y + 53),
        )
        favorite_label = "Favorites" if self.state.rule_menu_favorites_only else "All"
        input_label = (
            f"Search: {self.state.rule_menu_input or '—'} · {favorite_label}"
        )
        input_surface = tiny_font.render(input_label, True, accent)
        screen.blit(
            input_surface,
            (modal.right - input_surface.get_width() - 21, modal.y + 53),
        )

        mouse_position = pygame.mouse.get_pos()
        favorites = self.services.favorite_rules()
        for rule, card in cards:
            selected = rule == selected_rule
            hovered = card.collidepoint(mouse_position)
            featured = rule in RULE_PRESETS
            background = (54, 91, 112) if selected else (48, 52, 63)
            if hovered and not selected:
                background = (62, 68, 82)
            pygame.draw.rect(screen, background, card, border_radius=3)
            border = (
                accent
                if selected
                else (225, 182, 70)
                if featured
                else (82, 88, 102)
            )
            pygame.draw.rect(
                screen,
                border,
                card,
                2 if selected or featured else 1,
                border_radius=3,
            )
            number = tiny_font.render(str(rule), True, (247, 248, 251))
            screen.blit(number, number.get_rect(center=card.center))
            if rule in favorites:
                star = tiny_font.render("★", True, (240, 220, 90))
                screen.blit(star, (card.x + 2, card.y + 1))

        if not cards:
            empty = self.services.small_font().render(
                "No rules match this search/filter.",
                True,
                (205, 210, 220),
            )
            screen.blit(empty, empty.get_rect(center=modal.center))

        footer = (
            "Type to search · Enter selects exact rule · right click favorites · "
            "F filters favorites · E/Esc closes"
        )
        footer_surface = tiny_font.render(footer, True, (190, 195, 205))
        screen.blit(
            footer_surface,
            (modal.centerx - footer_surface.get_width() // 2, modal.bottom - 29),
        )
