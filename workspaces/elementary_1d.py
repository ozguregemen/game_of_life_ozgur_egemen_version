"""State, controller, and renderer for the 1D elementary CA workspace."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import pygame

from dimension_registry import DIMENSION_BY_KEY
from elementary_ca import (
    BOUNDARY_FIXED,
    BOUNDARY_INFINITE,
    BOUNDARY_WRAP,
    DEFAULT_RULE,
    DEFAULT_WIDTH,
    RULE_PRESETS,
    ElementaryRow,
    next_background,
    normalize_row,
    random_seed,
    row_stats,
    rule_bits,
    single_cell_seed,
    step_elementary,
    validate_rule,
)
from themes import THEMES, Menu
from timeline_history import TimelineBinding, TimelineStatus
from workspaces.base import WorkspaceController, WorkspaceRenderer

ECA_RENDER_KEY = "elementary_ca"
ECA_EDITOR_HEIGHT = 44
ECA_DIAGRAM_LIMIT = 512
ECA_MIN_CELL_SIZE = 2
ECA_MAX_CELL_SIZE = 16

@dataclass
class ElementaryWorkspaceState:
    """All persistent and transient state owned by the 1D workspace."""

    rule: int = DEFAULT_RULE
    boundary: str = BOUNDARY_INFINITE
    background: int = 0
    rule_change_reset: bool = True
    seed: ElementaryRow = field(
        default_factory=lambda: single_cell_seed(DEFAULT_WIDTH)
    )
    rows: list[ElementaryRow] = field(
        default_factory=lambda: [single_cell_seed(DEFAULT_WIDTH)]
    )
    generation: int = 0
    rng: random.Random = field(default_factory=random.Random)
    cell_size: int = 6
    view_offset_x: int = 0
    view_offset_y: int = 0
    rule_menu_active: bool = False
    rule_menu_input: str = ""
    drawing: bool = False
    drawing_value: int = 1
    stroke_history_pending: bool = False


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


class ElementaryWorkspaceController(WorkspaceController):
    """Own elementary CA rules, history, view state, and user input."""

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

    def diagram_viewport(self) -> pygame.Rect:
        viewport = self.services.viewport()
        return pygame.Rect(
            viewport.x,
            viewport.y + ECA_EDITOR_HEIGHT,
            viewport.width,
            max(1, viewport.height - ECA_EDITOR_HEIGHT),
        )

    def grid_origin(self) -> tuple[int, int]:
        viewport = self.diagram_viewport()
        return (
            viewport.x + self.state.view_offset_x,
            viewport.y + self.services.grid_top_margin + self.state.view_offset_y,
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
        self.state.view_offset_y = min(
            0,
            viewport.height - self.services.grid_top_margin - diagram_height,
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
        self._status(f"Elementary cell size: {self.state.cell_size}px")

    def save_history(self) -> None:
        self.timeline.prepare_change()

    def step_back(self) -> None:
        if not self.timeline.step(-1):
            self._status("No earlier elementary CA state is available.")
            return
        self.services.set_running(False)
        self._status(f"Returned to elementary generation {self.state.generation}.")

    def step_forward(self) -> None:
        if not self.timeline.step(1):
            self._status("No later elementary CA state is available.")
            return
        self.services.set_running(False)
        self._status(f"Advanced to elementary generation {self.state.generation}.")

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
        return self.timeline.sync()

    def history_status(self) -> TimelineStatus:
        return self.timeline.status()

    def reset_history(self) -> None:
        self.timeline.reset()

    def advance(self) -> bool:
        current_row = self.state.rows[-1]
        history_saved = False
        if self.state.boundary == BOUNDARY_INFINITE and (
            current_row[0] != self.state.background
            or current_row[-1] != self.state.background
        ):
            self.save_history()
            history_saved = True
            self.state.rows[-1] = (
                self.state.background,
                *current_row,
                self.state.background,
            )
            current_row = self.state.rows[-1]
            self.state.view_offset_x -= self.state.cell_size

        next_row = step_elementary(
            current_row,
            self.state.rule,
            boundary=self.state.boundary,
            background=self.state.background,
        )
        next_outside = (
            next_background(self.state.rule, self.state.background)
            if self.state.boundary == BOUNDARY_INFINITE
            else 0
        )
        if not history_saved:
            self.save_history()
        self.state.rows.append(next_row)
        self.state.background = next_outside
        if len(self.state.rows) > ECA_DIAGRAM_LIMIT:
            self.state.rows.pop(0)
        self.state.generation += 1
        self.follow_latest()
        self._invalidate()
        self.sync_history()
        return True

    def reset_seed(self, seed: ElementaryRow, message: str) -> None:
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
        self.state.generation = 0
        self.state.background = 0
        self.services.set_running(False)
        self.center_view()
        self._invalidate()
        self.sync_history()
        self._status(message)

    def clear(self) -> None:
        self.reset_seed(
            tuple(0 for _ in range(DEFAULT_WIDTH)),
            "Elementary diagram cleared.",
        )

    def randomize(self, density: float = 0.20) -> None:
        self.reset_seed(
            random_seed(DEFAULT_WIDTH, density=density, rng=self.state.rng),
            f"Random elementary seed created at {density:.0%} density.",
        )

    def use_single_seed(self) -> None:
        self.reset_seed(
            single_cell_seed(DEFAULT_WIDTH),
            "Centered single-cell seed created.",
        )

    def snapshot(self) -> dict[str, Any]:
        """Return the complete diagram and camera state for session storage."""
        return {
            "rule": self.state.rule,
            "boundary": self.state.boundary,
            "background": self.state.background,
            "rule_change_reset": self.state.rule_change_reset,
            "seed": list(self.state.seed),
            "rows": [list(row) for row in self.state.rows],
            "generation": self.state.generation,
            "camera": {
                "cell_size": self.state.cell_size,
                "offset": [
                    self.state.view_offset_x,
                    self.state.view_offset_y,
                ],
            },
        }

    def _timeline_snapshot(self) -> dict[str, Any]:
        """Capture simulation state without camera or transient controls."""
        return {
            "rule": self.state.rule,
            "boundary": self.state.boundary,
            "background": self.state.background,
            "rule_change_reset": self.state.rule_change_reset,
            "seed": list(self.state.seed),
            "rows": [list(row) for row in self.state.rows],
            "generation": self.state.generation,
        }

    def _restore_timeline_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        """Restore a trusted frame and keep its latest row visible."""
        self.state.rule = validate_rule(snapshot["rule"])
        self.state.boundary = str(snapshot["boundary"])
        self.state.background = int(snapshot["background"])
        self.state.rule_change_reset = bool(snapshot["rule_change_reset"])
        self.state.seed = normalize_row(snapshot["seed"])
        self.state.rows = [normalize_row(row) for row in snapshot["rows"]]
        self.state.generation = int(snapshot["generation"])
        self.state.rule_menu_active = False
        self.state.drawing = False
        self.state.stroke_history_pending = False
        self.follow_latest()
        self._invalidate()
        self.services.rebuild_sidebar()

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        """Restore a prevalidated complete elementary workspace snapshot."""
        rows = [normalize_row(row) for row in snapshot["rows"]]
        seed = normalize_row(snapshot["seed"])
        if not rows:
            raise ValueError("Elementary session must contain at least one row.")
        rule = validate_rule(snapshot["rule"])
        boundary = snapshot["boundary"]
        if boundary not in (BOUNDARY_INFINITE, BOUNDARY_FIXED, BOUNDARY_WRAP):
            raise ValueError(f"Unknown elementary boundary: {boundary}")
        background = snapshot["background"]
        if isinstance(background, bool) or background not in (0, 1):
            raise ValueError("Elementary background must be 0 or 1.")
        generation = snapshot["generation"]
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise TypeError("Elementary generation must be an integer.")
        if generation < 0:
            raise ValueError("Elementary generation cannot be negative.")
        rule_change_reset = snapshot["rule_change_reset"]
        if not isinstance(rule_change_reset, bool):
            raise TypeError("Rule-change behavior must be true or false.")
        camera = snapshot["camera"]
        cell_size = int(camera["cell_size"])
        offset_x, offset_y = camera["offset"]

        self.state.rule = rule
        self.state.boundary = boundary
        self.state.background = background
        self.state.rule_change_reset = rule_change_reset
        self.state.seed = seed
        self.state.rows = rows
        self.state.generation = generation
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
            "boundary": self.state.boundary,
            "background": self.state.background,
            "rule_change_reset": self.state.rule_change_reset,
            "seed": list(self.state.rows[-1]),
        }

    def restore_experiment(self, experiment: Mapping[str, Any]) -> None:
        """Restart the workspace from a validated experiment profile."""
        seed = normalize_row(experiment["seed"])
        rule = validate_rule(experiment["rule"])
        boundary = experiment["boundary"]
        if boundary not in (BOUNDARY_INFINITE, BOUNDARY_FIXED, BOUNDARY_WRAP):
            raise ValueError(f"Unknown elementary boundary: {boundary}")
        background = experiment["background"]
        if isinstance(background, bool) or background not in (0, 1):
            raise ValueError("Elementary background must be 0 or 1.")
        rule_change_reset = experiment["rule_change_reset"]
        if not isinstance(rule_change_reset, bool):
            raise TypeError("Rule-change behavior must be true or false.")

        self.save_history()
        self.state.rule = rule
        self.state.boundary = boundary
        self.state.background = background
        self.state.rule_change_reset = rule_change_reset
        self.state.seed = seed
        self.state.rows = [seed]
        self.state.generation = 0
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
        validated_rule = validate_rule(rule)
        if validated_rule == self.state.rule:
            self._status(f"Elementary rule {self.state.rule} is already selected.")
            return
        self.save_history()
        self.state.rule = validated_rule
        if self.state.rule_change_reset:
            self.state.seed = single_cell_seed(DEFAULT_WIDTH)
            self.state.rows = [self.state.seed]
            self.state.boundary = BOUNDARY_INFINITE
            self.state.background = 0
            restart_label = "canonical single-cell seed and infinite background"
        else:
            self.state.seed = self.state.rows[-1]
            self.state.rows = [self.state.seed]
            if self.state.boundary != BOUNDARY_INFINITE:
                self.state.background = 0
            restart_label = "the current row"
        self.state.generation = 0
        self.services.set_running(False)
        self.center_view()
        self._invalidate()
        self.services.rebuild_sidebar()
        self.sync_history()
        self._status(
            f"Rule {self.state.rule} selected; restarted from {restart_label}.",
            4.0,
        )

    def adjust_rule(self, delta: int) -> None:
        self.set_rule((self.state.rule + delta) % 256)

    def next_featured_rule(self) -> int:
        for preset in RULE_PRESETS:
            if preset > self.state.rule:
                return preset
        return RULE_PRESETS[0]

    def cycle_featured_rule(self) -> None:
        self.set_rule(self.next_featured_rule())

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
        self.state.background = 0
        self.state.seed = self.state.rows[-1]
        self.state.rows = [self.state.seed]
        self.state.generation = 0
        self.services.set_running(False)
        self.center_view()
        self._invalidate()
        self.services.rebuild_sidebar()
        self.sync_history()
        self._status(
            f"Elementary boundary: {self.boundary_label(self.state.boundary)}; "
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
        target_value = 1 if self.state.drawing_value else 0
        current = self.state.rows[-1]
        if current[column] == target_value:
            return
        if self.state.stroke_history_pending:
            self.save_history()
            self.state.stroke_history_pending = False
        edited = list(current)
        edited[column] = target_value
        self.state.rows[-1] = tuple(edited)
        if self.state.generation == 0 and len(self.state.rows) == 1:
            self.state.seed = self.state.rows[-1]
        self.services.set_running(False)
        self._invalidate()

    def open_rule_menu(self) -> None:
        self.state.rule_menu_active = True
        self.state.rule_menu_input = ""
        self.services.set_running(False)

    def close_rule_menu(self) -> None:
        self.state.rule_menu_active = False

    def rule_menu_geometry(
        self,
    ) -> tuple[pygame.Rect, list[tuple[int, pygame.Rect]]]:
        window_width, window_height = self.services.window_size()
        modal_width = min(820, window_width - 40)
        modal_height = min(540, window_height - 40)
        modal = pygame.Rect(0, 0, modal_width, modal_height)
        modal.center = (window_width // 2, window_height // 2)

        columns = 16
        rows = 16
        gap = 2
        grid_top = modal.y + 88
        grid_bottom = modal.bottom - 45
        card_width = (modal.width - 40 - gap * (columns - 1)) // columns
        card_height = (grid_bottom - grid_top - gap * (rows - 1)) // rows
        grid_width = columns * card_width + gap * (columns - 1)
        start_x = modal.centerx - grid_width // 2
        cards = []
        for rule in range(256):
            row, column = divmod(rule, columns)
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
                self.adjust_rule(-1)
                self.state.rule_menu_input = ""
                return True
            if event.key == pygame.K_RIGHT:
                self.adjust_rule(1)
                self.state.rule_menu_input = ""
                return True
            if event.key == pygame.K_BACKSPACE:
                self.state.rule_menu_input = self.state.rule_menu_input[:-1]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.state.rule_menu_input:
                    self.set_rule(int(self.state.rule_menu_input))
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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            modal, cards = self.rule_menu_geometry()
            for rule, card in cards:
                if card.collidepoint(event.pos):
                    self.set_rule(rule)
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
                    self.state.drawing_value = 1 if event.button == 1 else 0
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
        menu.set_header("1D · Elementary CA")
        menu.add_button(
            "Select Dimension (D)",
            self.services.activate_dimension_menu,
            accent=accent,
        )
        menu.add_button(
            "Session & Profiles (P)",
            self.services.activate_session_menu,
            accent=(80, 190, 145),
        )
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
        menu.add_button(
            f"Previous Rule: {(self.state.rule - 1) % 256}",
            lambda: self.adjust_rule(-1),
        )
        menu.add_button(
            f"Next Rule: {(self.state.rule + 1) % 256}",
            lambda: self.adjust_rule(1),
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
        menu.add_button("Seed: Single Center", self.use_single_seed)
        menu.add_button("Seed: Random", self.randomize)
        menu.add_button("Clear Diagram", self.clear)
        menu.add_button("Step Back", self.step_back)
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
    """Render the elementary CA state and its rule catalogue."""

    render_key = "1d:elementary_ca"

    def __init__(
        self,
        controller: ElementaryWorkspaceController,
        services: ElementaryWorkspaceServices,
    ) -> None:
        self.controller = controller
        self.services = services

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
            self.controller.editor_rect(),
            self.state.cell_size,
            self.services.theme_name(),
            self.services.show_grid(),
        )

    def draw_base(self) -> None:
        screen = self.services.screen()
        viewport = self.services.viewport()
        diagram_viewport = self.controller.diagram_viewport()
        origin_x, origin_y = self.controller.grid_origin()
        editor = self.controller.editor_rect()
        theme = THEMES[self.services.theme_name()]
        live_color = DIMENSION_BY_KEY["1d"].accent
        tiny_font = self.services.tiny_font()

        old_clip = screen.get_clip()
        screen.set_clip(viewport)
        pygame.draw.rect(
            screen,
            theme["info_bar"],
            (viewport.x, viewport.y, viewport.width, ECA_EDITOR_HEIGHT),
        )
        label = "Editable current row  ·  left click: on  ·  right click: off"
        screen.blit(
            tiny_font.render(label, True, theme["text"]),
            (viewport.x + 10, viewport.y + 5),
        )

        current_row = self.state.rows[-1]
        for column, value in enumerate(current_row):
            x = editor.x + column * self.state.cell_size
            rect = pygame.Rect(x, editor.y, self.state.cell_size, self.state.cell_size)
            if rect.right < viewport.left or rect.left > viewport.right:
                continue
            if value:
                pygame.draw.rect(screen, live_color, rect)
            if self.services.show_grid() and self.state.cell_size >= 4:
                pygame.draw.rect(screen, theme["grid"], rect, 1)
        pygame.draw.rect(screen, live_color, editor, 1)
        pygame.draw.line(
            screen,
            theme["grid"],
            (viewport.x, diagram_viewport.y - 1),
            (viewport.right, diagram_viewport.y - 1),
        )

        screen.set_clip(diagram_viewport)
        first_row = max(
            0,
            (diagram_viewport.top - origin_y) // self.state.cell_size,
        )
        last_row = min(
            len(self.state.rows),
            (
                diagram_viewport.bottom
                - origin_y
                + self.state.cell_size
                - 1
            )
            // self.state.cell_size,
        )
        current_width = len(current_row)
        for row_index in range(first_row, last_row):
            row_data = self.state.rows[row_index]
            row_origin_x = origin_x + (
                (current_width - len(row_data)) * self.state.cell_size // 2
            )
            first_col = max(
                0,
                (diagram_viewport.left - row_origin_x) // self.state.cell_size,
            )
            last_col = min(
                len(row_data),
                (
                    diagram_viewport.right
                    - row_origin_x
                    + self.state.cell_size
                    - 1
                )
                // self.state.cell_size,
            )
            y = origin_y + row_index * self.state.cell_size
            for column in range(first_col, last_col):
                x = row_origin_x + column * self.state.cell_size
                rect = pygame.Rect(
                    x,
                    y,
                    self.state.cell_size,
                    self.state.cell_size,
                )
                if row_data[column]:
                    pygame.draw.rect(screen, live_color, rect)
                if self.services.show_grid() and self.state.cell_size >= 4:
                    pygame.draw.rect(screen, theme["grid"], rect, 1)
        newest = pygame.Rect(
            origin_x,
            origin_y + (len(self.state.rows) - 1) * self.state.cell_size,
            current_width * self.state.cell_size,
            self.state.cell_size,
        )
        pygame.draw.rect(screen, live_color, newest, 1)
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
        info = (
            f"{state_label}   Dimension: 1D   Elementary Rule: {self.state.rule}   "
            f"Speed: {self.services.speed()} gen/s   "
            f"Generation: {self.state.generation}   Boundary: "
            f"{self.controller.boundary_label(self.state.boundary)}"
        )
        screen.blit(
            self.services.small_font().render(info, True, theme["text"]),
            (10, 11),
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
                **row_stats(self.state.rows[-1]),
                "diagram_active": sum(sum(row) for row in self.state.rows),
            },
        )
        current_width = len(self.state.rows[-1])
        history = self.controller.history_status()
        first_line = (
            f"Current row: {stats['active']}/{current_width} active   "
            f"Density: {stats['density']:.2f}%   Rows shown: "
            f"{len(self.state.rows)}   Diagram active cells: "
            f"{stats['diagram_active']}   Outside state: {self.state.background}   "
            f"Timeline: {history.cursor + 1}/{history.frame_count}"
        )
        outputs = "".join(str(value) for value in rule_bits(self.state.rule))
        second_line = (
            f"111 110 101 100 011 010 001 000  →  {outputs}   ·   "
            "Time flows downward; the fixed editor changes the latest row."
        )
        screen.blit(
            self.services.small_font().render(first_line, True, theme["text"]),
            (10, y + 8),
        )
        screen.blit(
            self.services.tiny_font().render(second_line, True, theme["text"]),
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
        screen.blit(
            self.services.large_font().render(
                "Elementary rule catalogue · 0–255",
                True,
                (245, 247, 250),
            ),
            (modal.x + 20, modal.y + 15),
        )
        binary = "".join(str(value) for value in rule_bits(self.state.rule))
        detail = (
            f"Current: Rule {self.state.rule} = {binary}₂   ·   "
            "gold border: featured rule"
        )
        tiny_font = self.services.tiny_font()
        screen.blit(
            tiny_font.render(detail, True, (192, 198, 211)),
            (modal.x + 21, modal.y + 53),
        )
        input_label = f"Type rule: {self.state.rule_menu_input or '—'}"
        input_surface = tiny_font.render(input_label, True, accent)
        screen.blit(
            input_surface,
            (modal.right - input_surface.get_width() - 21, modal.y + 53),
        )

        mouse_position = pygame.mouse.get_pos()
        for rule, card in cards:
            selected = rule == self.state.rule
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

        footer = (
            "Click a rule · type 0–255 + Enter · ←/→ previous/next · "
            "E/Esc closes"
        )
        footer_surface = tiny_font.render(footer, True, (190, 195, 205))
        screen.blit(
            footer_surface,
            (modal.centerx - footer_surface.get_width() // 2, modal.bottom - 29),
        )
