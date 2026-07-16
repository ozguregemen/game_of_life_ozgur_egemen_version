from __future__ import annotations

import os
import random
import time
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from typing import Any, Callable, Mapping

os.environ["SDL_VIDEO_CENTERED"] = "1"

import pygame

from analysis_ui import AnalysisPanelServices, ScientificAnalysisPanel
from brians_brain import (
    DYING,
    FIRING,
    BrainGrid,
    apply_brain_rules,
    brain_stats,
    make_brain_grid,
    randomize_brain_grid,
)
from cyclic_automaton import (
    DEFAULT_STATE_COUNT as CYCLIC_STATE_COUNT,
    DEFAULT_THRESHOLD as CYCLIC_DEFAULT_THRESHOLD,
    MOORE_NEIGHBOR_COUNT as CYCLIC_MAX_THRESHOLD,
    CyclicGrid,
    apply_cyclic_rules,
    cyclic_stats,
    make_cyclic_grid,
    randomize_cyclic_grid,
)
from dimension_registry import (
    DIMENSION_BY_KEY,
    DIMENSION_DEFINITIONS,
    DIMENSION_KEYS,
    get_dimension_definition,
)
from elementary_ca import (
    BOUNDARY_FIXED,
    BOUNDARY_INFINITE,
    BOUNDARY_WRAP,
    DEFAULT_RULE as ECA_DEFAULT_RULE,
    DEFAULT_WIDTH as ECA_WIDTH,
    RULE_PRESETS as ECA_RULE_PRESETS,
    single_cell_seed as single_eca_seed,
)
from experiment_exports import (
    ExperimentExportCoordinator,
    ExperimentExportServices,
)
from help_ui import HelpPanelServices, ShortcutHelpPanel
from export_ui import ExportMenu, ExportMenuServices
from exporting import (
    ExportRunner,
    RasterFrame,
    sampled_indices,
)
from immigration import (
    SPECIES_A,
    SPECIES_B,
    ImmigrationGrid,
    apply_immigration_rules,
    cell_age,
    immigration_stats,
    make_immigration_grid,
    randomize_immigration_grid,
    species_of,
)
from langtons_ant import (
    BLACK as ANT_BLACK,
    DIRECTION_NAMES,
    AntGrid,
    AntState,
    AntStepReport,
    ant_stats,
    centered_ant,
    make_ant_grid,
    randomize_ant_grid,
    rotate_ant_clockwise,
    step_ant,
)
from mode_registry import (
    MODE_BY_KEY,
    MODE_DEFINITIONS,
    MODE_KEYS,
    get_mode_definition,
)
from one_dimensional_ca import FAMILY_ELEMENTARY
from patterns import (
    flip_pattern,
    get_pattern_categories_for_mode,
    get_patterns_for_category,
    get_patterns_for_mode,
    rotate_pattern,
    save_pattern,
)
from rules import RULES, apply_rules_2d, find_patterns
from session_storage import (
    DOCUMENT_VERSION,
    PROFILE_SCHEMA,
    SESSION_SCHEMA,
    DocumentValidationError,
    SessionStorageError,
    list_profiles,
    list_sessions,
    load_profile,
    load_session,
    save_profile,
    save_session,
    utc_timestamp,
    validate_profile_document,
    validate_session_document,
)
from session_ui import SessionMenu, SessionMenuServices
from scientific_analysis import (
    AnalysisSeries,
    ElementaryComparisonRunner,
    ScientificAnalysisRegistry,
    StateObservation,
)
from themes import (
    COLORBLIND_CYCLIC_PALETTE,
    COLORBLIND_BLUE,
    COLORBLIND_GREEN,
    COLORBLIND_MAGENTA,
    COLORBLIND_SKY,
    COLORBLIND_YELLOW,
    CYCLIC_PALETTE,
    LIGHT_MODE_BLUE,
    LIGHT_MODE_ORANGE,
    LIGHT_MODE_PURPLE,
    LIGHT_MODE_TEAL,
    THEMES,
    Menu,
)
from timeline_history import TimelineBinding, TimelineStatus
from timeline_ui import TimelinePanel, TimelinePanelServices
from three_dimensional_display import (
    HybridDisplayBackend,
    ThreeDimensionalDisplayError,
)
from ui_preferences import UIPreferences
from visuals import CellTransition, get_enhanced_age_color
from wireworld import (
    CONDUCTOR,
    ELECTRON_HEAD,
    ELECTRON_TAIL,
    EMPTY as WIRE_EMPTY,
    STATE_NAMES as WIRE_STATE_NAMES,
    WireworldGrid,
    apply_wireworld_rules,
    make_wireworld_grid,
    randomize_wireworld_grid,
    wireworld_stats,
)
from workspaces.base import WorkspaceBundle, WorkspaceRegistry
from workspaces.elementary_1d import (
    ECA_RENDER_KEY,
    ElementaryWorkspaceController,
    ElementaryWorkspaceRenderer,
    ElementaryWorkspaceServices,
    ElementaryWorkspaceState,
)
from workspaces.three_dimensional import (
    THREE_D_RENDER_KEY,
    ThreeDimensionalWorkspaceController,
    ThreeDimensionalWorkspaceRenderer,
    ThreeDimensionalWorkspaceServices,
    ThreeDimensionalWorkspaceState,
)
from workspaces.two_dimensional import (
    TwoDimensionalControllerCallbacks,
    TwoDimensionalRendererCallbacks,
    TwoDimensionalWorkspaceController,
    TwoDimensionalWorkspaceRenderer,
)

# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
MENU_WIDTH = 260
INFO_BAR_HEIGHT = 42
STATS_HEIGHT = 68
TIMELINE_HEIGHT = 58
GRID_TOP_MARGIN = 8

ROWS = 48
COLS = 72
CELL_SIZE = 11
MIN_CELL_SIZE = 5
MAX_CELL_SIZE = 40

TIMELINE_MAX_FRAMES = 2000
TRAIL_MAX = 10
PATTERN_ROW_HEIGHT = 30

BLACK = (0, 0, 0)

pygame.init()
APPLICATION_CAPTION = "Özgür Egemen's Cellular Automata Lab"
display_backend = HybridDisplayBackend(
    (WINDOW_WIDTH, WINDOW_HEIGHT),
    APPLICATION_CAPTION,
)
screen = display_backend.surface
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 22, bold=True)
small_font = pygame.font.SysFont("Arial", 16)
tiny_font = pygame.font.SysFont("Arial", 12)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def make_grid(value: int = 0) -> list[list[int]]:
    return [[value for _ in range(COLS)] for _ in range(ROWS)]


def make_float_grid() -> list[list[float]]:
    return [[0.0 for _ in range(COLS)] for _ in range(ROWS)]


grid = make_grid()
trail_grid = make_grid()
activity_grid = make_float_grid()

immigration_grid: ImmigrationGrid = make_immigration_grid(ROWS, COLS)
immigration_generation = 0
active_species = SPECIES_A
immigration_rng = random.Random()

brain_grid: BrainGrid = make_brain_grid(ROWS, COLS)
brain_generation = 0
brain_rng = random.Random()

ant_grid: AntGrid = make_ant_grid(ROWS, COLS)
ant_state = centered_ant(ROWS, COLS)
ant_generation = 0
ant_last_report = AntStepReport()
ant_rng = random.Random()

wireworld_grid: WireworldGrid = make_wireworld_grid(ROWS, COLS)
wireworld_generation = 0
wireworld_brush = CONDUCTOR
wireworld_rng = random.Random()
WIRE_BRUSH_STATES = (CONDUCTOR, ELECTRON_HEAD, ELECTRON_TAIL)

cyclic_grid: CyclicGrid = make_cyclic_grid(ROWS, COLS)
cyclic_generation = 0
cyclic_brush = 1
cyclic_threshold = CYCLIC_DEFAULT_THRESHOLD
cyclic_rng = random.Random()

SIMULATION_MODES = MODE_KEYS
requested_start_mode = os.environ.get("LIFE_START_MODE", "life")
simulation_mode = (
    requested_start_mode if requested_start_mode in SIMULATION_MODES else "life"
)
requested_start_dimension = os.environ.get("LIFE_START_DIMENSION", "2d")
active_dimension = (
    requested_start_dimension
    if requested_start_dimension in DIMENSION_KEYS
    and DIMENSION_BY_KEY[requested_start_dimension].available
    else "2d"
)
current_rule = "conway"
current_theme = "classic"
simulation_active = False
single_step_requested = False
speed = 10
generation = 0
two_d_timelines: dict[str, TimelineBinding] = {}
analysis_registry = ScientificAnalysisRegistry(max_samples=TIMELINE_MAX_FRAMES)
comparison_runner = ElementaryComparisonRunner()
export_runner = ExportRunner()
ui_preferences = UIPreferences.load(
    autosave=os.environ.get("SDL_VIDEODRIVER") != "dummy"
)

show_grid = True
show_heatmap = False
show_age_numbers = False
show_coordinates = False
show_quadrants = False

selected_pattern: dict[str, Any] | None = None
rotation = 0
flip_h = False
flip_v = False
pattern_menu_active = False
pattern_scroll = 0
pattern_menu_category: str | None = None
mode_menu_active = False
dimension_menu_active = False

drawing = False
drawing_value = 1
drawing_history_pending = False

view_offset_x = 0
view_offset_y = 0

show_rule_overlay_until = 0.0
status_message = ""
status_message_until = 0.0

recognized_pattern_cache: dict[str, int] = {}
pattern_scan_generation = -1
pattern_scan_revision = -1
pattern_scan_future: Future[dict[str, int]] | None = None
pattern_scan_executor = ThreadPoolExecutor(max_workers=1)
grid_revision = 0
stats_dirty = True

render_revisions = {
    mode: 0
    for mode in (*SIMULATION_MODES, ECA_RENDER_KEY, THREE_D_RENDER_KEY)
}
rendered_grid_cache: dict[
    str,
    tuple[tuple[Any, ...], pygame.Surface],
] = {}
mode_stats_cache: dict[str, tuple[int, dict[str, Any]]] = {}
render_cache_hits = 0
render_cache_misses = 0

cell_transition = CellTransition(duration=0.18)
main_menu: Menu

# ---------------------------------------------------------------------------
# Geometry and state helpers
# ---------------------------------------------------------------------------


def grid_viewport() -> pygame.Rect:
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    height = max(
        1,
        WINDOW_HEIGHT - INFO_BAR_HEIGHT - STATS_HEIGHT - TIMELINE_HEIGHT,
    )
    return pygame.Rect(0, INFO_BAR_HEIGHT, width, height)


def timeline_rect() -> pygame.Rect:
    """Return the shared history strip between the workspace and stats bar."""
    return pygame.Rect(
        0,
        WINDOW_HEIGHT - STATS_HEIGHT - TIMELINE_HEIGHT,
        max(1, WINDOW_WIDTH - MENU_WIDTH),
        TIMELINE_HEIGHT,
    )


def grid_origin() -> tuple[int, int]:
    viewport = grid_viewport()
    return (
        viewport.x + view_offset_x,
        viewport.y + GRID_TOP_MARGIN + view_offset_y,
    )


def eca_diagram_viewport() -> pygame.Rect:
    """Compatibility wrapper for the extracted 1D workspace geometry."""
    return elementary_controller.diagram_viewport()


def eca_grid_origin() -> tuple[int, int]:
    return elementary_controller.grid_origin()


def eca_editor_rect() -> pygame.Rect:
    return elementary_controller.editor_rect()


def follow_eca_latest() -> None:
    elementary_controller.follow_latest()


def _center_2d_view() -> None:
    global view_offset_x, view_offset_y
    viewport = grid_viewport()
    grid_width = COLS * CELL_SIZE
    grid_height = ROWS * CELL_SIZE
    view_offset_x = (viewport.width - grid_width) // 2
    view_offset_y = (viewport.height - GRID_TOP_MARGIN - grid_height) // 2


def fitted_2d_cell_size() -> int:
    """Return the largest whole-cell zoom that keeps the board visible."""
    viewport = grid_viewport()
    available_height = max(1, viewport.height - GRID_TOP_MARGIN)
    target = min(viewport.width // COLS, available_height // ROWS)
    return max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, target))


def fit_2d_view() -> None:
    """Fit the fixed logical 2D board into the current application viewport."""
    global CELL_SIZE
    CELL_SIZE = fitted_2d_cell_size()
    _center_2d_view()
    set_status(
        f"2D board {COLS}x{ROWS} fitted at {CELL_SIZE}px per cell.",
        3.0,
    )


def describe_2d_board() -> None:
    """Explain the fixed board size without mutating simulation state."""
    set_status(
        f"Finite 2D board: {COLS} columns x {ROWS} rows "
        f"({ROWS * COLS:,} cells).",
        3.5,
    )


def center_view() -> None:
    """Center the active dimension through its workspace controller."""
    active_workspace().controller.center_view()


def set_status(message: str, duration: float = 2.0) -> None:
    global status_message, status_message_until
    status_message = message
    status_message_until = time.time() + duration


def invalidate_render_cache(mode: str | None = None) -> None:
    """Mark one mode's rendered grid and derived statistics as stale."""
    target_mode = simulation_mode if mode is None else mode
    if target_mode not in render_revisions:
        raise ValueError(f"Unknown simulation mode: {target_mode}")
    render_revisions[target_mode] += 1
    rendered_grid_cache.pop(target_mode, None)
    mode_stats_cache.pop(target_mode, None)


def reset_render_cache_metrics() -> None:
    """Reset cache counters used by tests and the render benchmark."""
    global render_cache_hits, render_cache_misses
    render_cache_hits = 0
    render_cache_misses = 0


def cached_mode_stats(
    mode: str,
    calculator: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Return mode statistics until its underlying state changes."""
    revision = render_revisions[mode]
    cached = mode_stats_cache.get(mode)
    if cached is None or cached[0] != revision:
        cached = (revision, calculator())
        mode_stats_cache[mode] = cached
    return cached[1]


def mark_stats_dirty() -> None:
    global stats_dirty, grid_revision
    stats_dirty = True
    grid_revision += 1
    invalidate_render_cache("life")


def _save_2d_history() -> None:
    two_d_timelines[simulation_mode].prepare_change()


def save_history() -> None:
    """Save history through the active workspace controller."""
    active_workspace().controller.save_history()


def _step_back_2d() -> None:
    _step_2d_history(-1)


def _step_forward_2d() -> None:
    _step_2d_history(1)


def _step_2d_history(amount: int) -> None:
    global simulation_active
    if not two_d_timelines[simulation_mode].step(amount):
        direction = "earlier" if amount < 0 else "later"
        mode_name = MODE_BY_KEY[simulation_mode].name
        set_status(f"No {direction} {mode_name} state is available.")
        return
    simulation_active = False
    set_status(f"Timeline generation: {_two_d_generation()}.")


def _seek_2d_history(index: int) -> bool:
    global simulation_active
    moved = two_d_timelines[simulation_mode].seek(index)
    if moved:
        simulation_active = False
    return moved


def _seek_2d_generation(target_generation: int) -> bool:
    global simulation_active
    moved = two_d_timelines[simulation_mode].seek_generation(target_generation)
    if moved:
        simulation_active = False
    return moved


def _sync_2d_history() -> bool:
    recorded = two_d_timelines[simulation_mode].sync()
    if recorded:
        analysis_registry.observe(_analysis_observation_2d(simulation_mode))
    return recorded


def _two_d_history_status() -> TimelineStatus:
    return two_d_timelines[simulation_mode].status()


def _reset_2d_history() -> None:
    two_d_timelines[simulation_mode].reset()
    analysis_registry.reset(_analysis_observation_2d(simulation_mode))


def step_back() -> None:
    """Undo through the active workspace controller."""
    active_workspace().controller.step_back()


def step_forward() -> None:
    """Move forward through the active workspace's existing timeline."""
    active_workspace().controller.step_forward()


def active_history_status() -> TimelineStatus:
    """Return timeline information for the active workspace."""
    return active_workspace().controller.history_status()


def seek_active_history(index: int) -> bool:
    """Move the active workspace to an exact chronological frame."""
    return active_workspace().controller.seek_history(index)


def seek_active_generation(target_generation: int) -> bool:
    """Move to the most recent exact generation label in active history."""
    return active_workspace().controller.seek_generation(target_generation)


def step_active_timeline(amount: int) -> bool:
    """Move a relative number of frames and report whether movement occurred."""
    status = active_history_status()
    target = status.cursor + amount
    if not 0 <= target < status.frame_count:
        return False
    return seek_active_history(target)


def normalize_pattern_cell(value: int, mode: str) -> int:
    """Convert runtime state such as cell age into a saved pattern state."""
    if mode == "life":
        return 1 if value > 0 else 0
    if mode == "immigration":
        return species_of(value)
    return int(value)


def crop_mode_pattern(
    source: list[list[int]],
    mode: str,
) -> tuple[list[list[int]], dict[str, int] | None]:
    """Crop a mode grid while preserving its meaningful cell states."""
    occupied_positions = [
        (row, col)
        for row in range(ROWS)
        for col in range(COLS)
        if source[row][col] != 0
    ]
    if mode == "langtons_ant":
        occupied_positions.append((ant_state.row, ant_state.col))
    if not occupied_positions:
        return [], None

    min_row = min(row for row, _ in occupied_positions)
    max_row = max(row for row, _ in occupied_positions)
    min_col = min(col for _, col in occupied_positions)
    max_col = max(col for _, col in occupied_positions)

    cropped = [
        [
            normalize_pattern_cell(source[row][col], mode)
            for col in range(min_col, max_col + 1)
        ]
        for row in range(min_row, max_row + 1)
    ]
    ant = None
    if mode == "langtons_ant":
        ant = {
            "row": ant_state.row - min_row,
            "col": ant_state.col - min_col,
            "direction": ant_state.direction,
        }
    return cropped, ant


def transformed_pattern(
    pattern: dict[str, Any],
) -> tuple[list[list[int]], dict[str, int] | None]:
    """Apply rotation/flips to pattern cells and optional ant metadata."""
    data = [list(row) for row in pattern["pattern"]]
    ant = dict(pattern["ant"]) if "ant" in pattern else None
    rows, cols = len(data), len(data[0])

    if rotation:
        if ant is not None:
            ant_row, ant_col = ant["row"], ant["col"]
            if rotation == 90:
                ant["row"], ant["col"] = ant_col, rows - 1 - ant_row
            elif rotation == 180:
                ant["row"], ant["col"] = rows - 1 - ant_row, cols - 1 - ant_col
            else:
                ant["row"], ant["col"] = cols - 1 - ant_col, ant_row
            ant["direction"] = (ant["direction"] + rotation // 90) % 4
        data = [list(row) for row in rotate_pattern(data, rotation)]
        rows, cols = len(data), len(data[0])
    if flip_h:
        data = [list(row) for row in flip_pattern(data, True)]
        if ant is not None:
            ant["col"] = cols - 1 - ant["col"]
            ant["direction"] = (-ant["direction"]) % 4
    if flip_v:
        data = [list(row) for row in flip_pattern(data, False)]
        if ant is not None:
            ant["row"] = rows - 1 - ant["row"]
            ant["direction"] = (2 - ant["direction"]) % 4
    return data, ant


def transformed_pattern_data(pattern: dict[str, Any]) -> list[list[int]]:
    """Return transformed cells for callers that do not need metadata."""
    return transformed_pattern(pattern)[0]


def mouse_to_grid(position: tuple[int, int]) -> tuple[int, int] | None:
    mouse_x, mouse_y = position
    if not grid_viewport().collidepoint(position):
        return None

    origin_x, origin_y = grid_origin()
    col = (mouse_x - origin_x) // CELL_SIZE
    row = (mouse_y - origin_y) // CELL_SIZE

    if 0 <= row < ROWS and 0 <= col < COLS:
        return int(row), int(col)
    return None


def mouse_to_eca_column(position: tuple[int, int]) -> int | None:
    return elementary_controller.mouse_to_column(position)


def draw_eca_cell(column: int) -> None:
    global drawing_history_pending
    elementary_controller.state.drawing_value = drawing_value
    elementary_controller.state.stroke_history_pending = drawing_history_pending
    elementary_controller.draw_cell(column)
    drawing_history_pending = elementary_controller.state.stroke_history_pending


def set_cell(row: int, col: int, value: int) -> bool:
    """Set a cell and return whether the grid changed."""
    old_value = grid[row][col]
    if old_value == value:
        return False

    grid[row][col] = value
    if (old_value > 0) != (value > 0):
        cell_transition.start_transition(row, col, old_value, value)
    mark_stats_dirty()
    return True


def draw_cell(row: int, col: int) -> None:
    """Apply the active brush and save one history entry per changed stroke."""
    global drawing_history_pending
    if simulation_mode == "cyclic_automaton":
        target_value = cyclic_brush if drawing_value else 0
        if cyclic_grid[row][col] == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        cyclic_grid[row][col] = target_value
        invalidate_render_cache("cyclic_automaton")
        return

    if simulation_mode == "wireworld":
        target_value = wireworld_brush if drawing_value else WIRE_EMPTY
        if wireworld_grid[row][col] == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        wireworld_grid[row][col] = target_value
        invalidate_render_cache("wireworld")
        return

    if simulation_mode == "langtons_ant":
        target_value = ANT_BLACK if drawing_value else 0
        if ant_grid[row][col] == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        ant_grid[row][col] = target_value
        invalidate_render_cache("langtons_ant")
        return

    if simulation_mode == "brians_brain":
        target_value = FIRING if drawing_value else 0
        if brain_grid[row][col] == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        brain_grid[row][col] = target_value
        invalidate_render_cache("brians_brain")
        return

    if simulation_mode == "immigration":
        target_value = active_species if drawing_value else 0
        if species_of(immigration_grid[row][col]) == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        immigration_grid[row][col] = target_value
        invalidate_render_cache("immigration")
        return

    if grid[row][col] == drawing_value:
        return
    if drawing_history_pending:
        save_history()
        drawing_history_pending = False
    set_cell(row, col, drawing_value)


def pattern_fits(data: list[list[int]], row: int, col: int) -> bool:
    """Return whether the complete rectangular pattern fits on the grid."""
    return bool(data) and (
        row >= 0
        and col >= 0
        and row + len(data) <= ROWS
        and col + len(data[0]) <= COLS
    )


def pattern_target_value(value: int, pattern_mode: str | None) -> int:
    """Map a pattern cell to the current mode, including legacy binary data."""
    if pattern_mode is not None:
        return value
    if simulation_mode == "cyclic_automaton":
        return cyclic_brush
    if simulation_mode == "immigration":
        return active_species
    if simulation_mode == "brians_brain":
        return FIRING
    if simulation_mode == "langtons_ant":
        return ANT_BLACK
    if simulation_mode == "wireworld":
        return CONDUCTOR
    return 1


def current_pattern_cell(row: int, col: int) -> int:
    """Return the current cell state normalized for pattern comparison."""
    if simulation_mode == "cyclic_automaton":
        return cyclic_grid[row][col]
    if simulation_mode == "immigration":
        return species_of(immigration_grid[row][col])
    if simulation_mode == "brians_brain":
        return brain_grid[row][col]
    if simulation_mode == "langtons_ant":
        return ant_grid[row][col]
    if simulation_mode == "wireworld":
        return wireworld_grid[row][col]
    return 1 if grid[row][col] > 0 else 0


def set_pattern_cell(row: int, col: int, value: int) -> None:
    """Write one already-validated state to the selected mode grid."""
    if simulation_mode == "cyclic_automaton":
        cyclic_grid[row][col] = value
    elif simulation_mode == "immigration":
        immigration_grid[row][col] = value
    elif simulation_mode == "brians_brain":
        brain_grid[row][col] = value
    elif simulation_mode == "langtons_ant":
        ant_grid[row][col] = value
    elif simulation_mode == "wireworld":
        wireworld_grid[row][col] = value
    else:
        set_cell(row, col, value)


def place_selected_pattern(row: int, col: int) -> None:
    global selected_pattern, ant_state
    if selected_pattern is None:
        return

    pattern_mode = selected_pattern.get("mode")
    if pattern_mode is not None and pattern_mode != simulation_mode:
        selected_pattern = None
        set_status("That pattern belongs to a different simulation mode.")
        return

    data, ant = transformed_pattern(selected_pattern)
    if not pattern_fits(data, row, col):
        selected_pattern = None
        set_status("Pattern does not fit inside the grid.")
        return

    changes: list[tuple[int, int, int]] = []
    for delta_row, pattern_row in enumerate(data):
        for delta_col, value in enumerate(pattern_row):
            if not value and pattern_mode != "cyclic_automaton":
                continue
            target_row = row + delta_row
            target_col = col + delta_col
            target_value = pattern_target_value(value, pattern_mode)
            if current_pattern_cell(target_row, target_col) != target_value:
                changes.append((target_row, target_col, target_value))

    next_ant = None
    if simulation_mode == "langtons_ant" and ant is not None:
        next_ant = AntState(
            row + ant["row"],
            col + ant["col"],
            ant["direction"],
        )
    ant_changed = next_ant is not None and next_ant != ant_state
    if changes or ant_changed:
        save_history()
        for target_row, target_col, target_value in changes:
            set_pattern_cell(target_row, target_col, target_value)
        if next_ant is not None:
            ant_state = next_ant
        if simulation_mode != "life":
            invalidate_render_cache()
        _sync_2d_history()

    selected_pattern = None
    if changes or ant_changed:
        set_status("Pattern placed.")
    else:
        set_status("Pattern made no changes.")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _clear_2d_grid() -> None:
    global grid, trail_grid, activity_grid, generation, simulation_active
    global immigration_grid, immigration_generation
    global brain_grid, brain_generation
    global ant_grid, ant_state, ant_generation, ant_last_report
    global wireworld_grid, wireworld_generation
    global cyclic_grid, cyclic_generation
    if simulation_mode == "cyclic_automaton":
        save_history()
        cyclic_grid = make_cyclic_grid(ROWS, COLS)
        cyclic_generation = 0
        simulation_active = False
        invalidate_render_cache("cyclic_automaton")
        set_status("Cyclic Automaton reset to color 0.")
        return

    if simulation_mode == "wireworld":
        save_history()
        wireworld_grid = make_wireworld_grid(ROWS, COLS)
        wireworld_generation = 0
        simulation_active = False
        invalidate_render_cache("wireworld")
        set_status("Wireworld grid cleared.")
        return

    if simulation_mode == "langtons_ant":
        save_history()
        ant_grid = make_ant_grid(ROWS, COLS)
        ant_state = centered_ant(ROWS, COLS)
        ant_generation = 0
        ant_last_report = AntStepReport()
        simulation_active = False
        invalidate_render_cache("langtons_ant")
        set_status("Langton's Ant board reset.")
        return

    if simulation_mode == "brians_brain":
        save_history()
        brain_grid = make_brain_grid(ROWS, COLS)
        brain_generation = 0
        simulation_active = False
        invalidate_render_cache("brians_brain")
        set_status("Brian's Brain grid cleared.")
        return

    if simulation_mode == "immigration":
        save_history()
        immigration_grid = make_immigration_grid(ROWS, COLS)
        immigration_generation = 0
        simulation_active = False
        invalidate_render_cache("immigration")
        set_status("Immigration grid cleared.")
        return

    save_history()
    grid = make_grid()
    trail_grid = make_grid()
    activity_grid = make_float_grid()
    generation = 0
    simulation_active = False
    cell_transition.transitions.clear()
    mark_stats_dirty()
    set_status("Grid cleared.")


def clear_grid() -> None:
    """Clear through the active workspace controller."""
    active_workspace().controller.clear()


def _randomize_2d_grid(density: float = 0.20) -> None:
    global grid, trail_grid, activity_grid, generation, simulation_active
    global immigration_grid, immigration_generation
    global brain_grid, brain_generation
    global ant_grid, ant_state, ant_generation, ant_last_report
    global wireworld_grid, wireworld_generation
    global cyclic_grid, cyclic_generation
    if simulation_mode == "cyclic_automaton":
        save_history()
        cyclic_grid = randomize_cyclic_grid(
            ROWS,
            COLS,
            state_count=CYCLIC_STATE_COUNT,
            rng=cyclic_rng,
        )
        cyclic_generation = 0
        simulation_active = False
        invalidate_render_cache("cyclic_automaton")
        set_status("Random eight-color Cyclic Automaton state created.")
        return

    if simulation_mode == "wireworld":
        save_history()
        wireworld_grid = randomize_wireworld_grid(
            ROWS,
            COLS,
            conductor_density=density,
            signal_fraction=0.08,
            rng=wireworld_rng,
        )
        wireworld_generation = 0
        simulation_active = False
        invalidate_render_cache("wireworld")
        set_status("Random Wireworld conductors and signals created.")
        return

    if simulation_mode == "langtons_ant":
        save_history()
        ant_grid = randomize_ant_grid(
            ROWS,
            COLS,
            density=0.15,
            rng=ant_rng,
        )
        ant_state = centered_ant(ROWS, COLS)
        ant_generation = 0
        ant_last_report = AntStepReport()
        simulation_active = False
        invalidate_render_cache("langtons_ant")
        set_status("Random Langton board created; ant reset to center.")
        return

    if simulation_mode == "brians_brain":
        save_history()
        brain_grid = randomize_brain_grid(
            ROWS,
            COLS,
            density=0.18,
            rng=brain_rng,
        )
        brain_generation = 0
        simulation_active = False
        invalidate_render_cache("brians_brain")
        set_status("Random Brian's Brain state created.")
        return

    if simulation_mode == "immigration":
        save_history()
        immigration_grid = randomize_immigration_grid(
            ROWS,
            COLS,
            density=density,
            rng=immigration_rng,
        )
        immigration_generation = 0
        simulation_active = False
        invalidate_render_cache("immigration")
        set_status("Random two-species Immigration population created.")
        return

    save_history()
    grid = [
        [1 if random.random() < density else 0 for _ in range(COLS)]
        for _ in range(ROWS)
    ]
    trail_grid = make_grid()
    activity_grid = make_float_grid()
    generation = 0
    simulation_active = False
    cell_transition.transitions.clear()
    mark_stats_dirty()
    set_status(f"Random grid created at {density:.0%} density.")


def randomize_grid(density: float = 0.20) -> None:
    """Randomize through the active workspace controller."""
    active_workspace().controller.randomize(density)


def cycle_theme() -> None:
    global current_theme
    themes = list(THEMES)
    current_theme = themes[(themes.index(current_theme) + 1) % len(themes)]
    main_menu.theme = current_theme
    rebuild_context_menu()
    set_status(f"Theme: {current_theme.title()}")


def cycle_rule() -> None:
    global current_rule, show_rule_overlay_until
    if simulation_mode != "life":
        if simulation_mode == "immigration":
            message = "Immigration Game uses Conway B3/S23 for both species."
        elif simulation_mode == "brians_brain":
            message = "Brian's Brain uses the fixed 2-neighbor firing rule."
        elif simulation_mode == "wireworld":
            message = "Wireworld conductors activate beside exactly 1 or 2 heads."
        elif simulation_mode == "cyclic_automaton":
            message = (
                "Cyclic cells advance when enough neighbors have the next color."
            )
        else:
            message = "Langton's Ant uses right-on-white and left-on-black."
        set_status(message)
        return
    save_history()
    rules = list(RULES)
    current_rule = rules[(rules.index(current_rule) + 1) % len(rules)]
    show_rule_overlay_until = time.time() + 2.5
    mark_stats_dirty()
    rebuild_context_menu()
    _sync_2d_history()


def _switch_display_backend(dimension: str) -> bool:
    """Select the software or OpenGL display without changing workspace state."""
    global screen
    try:
        if dimension == "3d":
            screen = display_backend.activate_3d((WINDOW_WIDTH, WINDOW_HEIGHT))
        else:
            screen = display_backend.activate_software((WINDOW_WIDTH, WINDOW_HEIGHT))
    except ThreeDimensionalDisplayError as exc:
        screen = display_backend.surface
        set_status(f"3D renderer unavailable: {exc}", 6.0)
        return False
    if "rendered_grid_cache" in globals():
        rendered_grid_cache.clear()
    return True


def set_active_dimension(dimension: str) -> bool:
    """Switch workspaces while keeping every dimension's simulation state."""
    global active_dimension, simulation_active, single_step_requested
    global selected_pattern, pattern_menu_active, mode_menu_active
    global dimension_menu_active, drawing
    definition = get_dimension_definition(dimension)
    if not definition.available:
        dimension_menu_active = False
        set_status(f"{definition.name}: {definition.status_hint}", 4.0)
        return False

    if not _switch_display_backend(dimension):
        dimension_menu_active = False
        return False

    if "timeline_panel" in globals():
        timeline_panel.stop()

    active_workspace().controller.sync_history()
    active_workspace().controller.deactivate()
    active_dimension = dimension
    simulation_active = False
    single_step_requested = False
    selected_pattern = None
    pattern_menu_active = False
    mode_menu_active = False
    dimension_menu_active = False
    drawing = False
    cell_transition.transitions.clear()
    if "main_menu" in globals():
        active_workspace().controller.activate()
        rebuild_context_menu()
    set_status(f"{definition.name}: {definition.status_hint}", 4.0)
    return True


def activate_dimension_menu() -> None:
    """Open the top-level dimension chooser and pause the workspace."""
    global dimension_menu_active, mode_menu_active, pattern_menu_active
    global simulation_active
    dimension_menu_active = True
    mode_menu_active = False
    pattern_menu_active = False
    if "workspace_registry" in globals():
        active_workspace().controller.deactivate()
    simulation_active = False


def eca_boundary_label(boundary: str | None = None) -> str:
    value = elementary_controller.state.boundary if boundary is None else boundary
    return elementary_controller.boundary_label(value)


def set_eca_rule(rule: int) -> None:
    elementary_controller.set_rule(rule)


def adjust_eca_rule(delta: int) -> None:
    elementary_controller.adjust_rule(delta)


def cycle_eca_rule_preset() -> None:
    elementary_controller.cycle_featured_rule()


def next_featured_eca_rule() -> int:
    return elementary_controller.next_featured_rule()


def toggle_eca_rule_change_reset() -> None:
    elementary_controller.toggle_rule_change_reset()


def toggle_eca_boundary() -> None:
    elementary_controller.toggle_boundary()


def reset_eca_seed(seed: tuple[int, ...], message: str) -> None:
    elementary_controller.reset_seed(seed, message)


def use_single_eca_seed() -> None:
    elementary_controller.use_single_seed()


def set_simulation_mode(mode: str) -> None:
    """Select a registered mode and reset transient interface state."""
    global active_dimension, simulation_mode, simulation_active
    global single_step_requested, dimension_menu_active
    global selected_pattern, pattern_menu_active, mode_menu_active, drawing
    definition = get_mode_definition(mode)
    if not _switch_display_backend("2d"):
        return
    if "timeline_panel" in globals():
        timeline_panel.stop()
    if "workspace_registry" in globals():
        active_workspace().controller.sync_history()
        active_workspace().controller.deactivate()
    active_dimension = "2d"
    simulation_mode = mode
    simulation_active = False
    single_step_requested = False
    selected_pattern = None
    pattern_menu_active = False
    mode_menu_active = False
    dimension_menu_active = False
    drawing = False
    cell_transition.transitions.clear()
    if "main_menu" in globals():
        active_workspace().controller.activate()
        rebuild_context_menu()
    set_status(f"{definition.name}: {definition.status_hint}", 4.0)


def toggle_simulation_mode() -> None:
    """Cycle modes programmatically; the interactive UI uses the chooser."""
    current_index = SIMULATION_MODES.index(simulation_mode)
    set_simulation_mode(SIMULATION_MODES[(current_index + 1) % len(SIMULATION_MODES)])


def activate_mode_menu() -> None:
    """Open the mode chooser and pause the simulation behind it."""
    global mode_menu_active, pattern_menu_active, simulation_active
    if active_dimension != "2d":
        set_status("Simulation modes belong to the 2D workspace; press D to switch.")
        return
    mode_menu_active = True
    pattern_menu_active = False
    simulation_active = False


def toggle_active_species() -> None:
    """Change the mode-specific drawing state or rotate the Langton ant."""
    global active_species, ant_state, wireworld_brush, cyclic_brush
    if simulation_mode == "cyclic_automaton":
        cyclic_brush = (cyclic_brush + 1) % CYCLIC_STATE_COUNT
        if "main_menu" in globals():
            rebuild_context_menu()
        set_status(f"Cyclic brush: color {cyclic_brush}.")
        return

    if simulation_mode == "wireworld":
        index = WIRE_BRUSH_STATES.index(wireworld_brush)
        wireworld_brush = WIRE_BRUSH_STATES[(index + 1) % len(WIRE_BRUSH_STATES)]
        if "main_menu" in globals():
            rebuild_context_menu()
        set_status(f"Wireworld brush: {WIRE_STATE_NAMES[wireworld_brush]}")
        return
    if simulation_mode == "langtons_ant":
        save_history()
        ant_state = rotate_ant_clockwise(ant_state)
        invalidate_render_cache("langtons_ant")
        _sync_2d_history()
        direction = DIRECTION_NAMES[ant_state.direction]
        set_status(f"Ant direction: {direction}")
        return
    if simulation_mode != "immigration":
        set_status("This mode has no alternate drawing state.")
        return
    active_species = SPECIES_B if active_species == SPECIES_A else SPECIES_A
    if "main_menu" in globals():
        rebuild_context_menu()
    label = immigration_species_label(active_species)
    set_status(f"Active species: {label}")


def set_active_species(species: int) -> None:
    """Select an Immigration brush directly from the contextual menu."""
    global active_species
    if simulation_mode != "immigration" or species not in (SPECIES_A, SPECIES_B):
        return
    active_species = species
    rebuild_context_menu()
    label = immigration_species_label(species)
    set_status(f"Active species: {label}")


def set_wireworld_brush(value: int) -> None:
    """Select a Wireworld drawing state directly from the contextual menu."""
    global wireworld_brush
    if simulation_mode != "wireworld" or value not in WIRE_BRUSH_STATES:
        return
    wireworld_brush = value
    rebuild_context_menu()
    set_status(f"Wireworld brush: {WIRE_STATE_NAMES[value]}")


def set_cyclic_brush(value: int) -> None:
    """Select one of the cyclic mode's color states."""
    global cyclic_brush
    if simulation_mode != "cyclic_automaton":
        return
    if not 0 <= value < CYCLIC_STATE_COUNT:
        raise ValueError(f"Cyclic brush must be between 0 and {CYCLIC_STATE_COUNT - 1}.")
    cyclic_brush = value
    rebuild_context_menu()
    set_status(f"Cyclic brush: color {cyclic_brush}.")


def cycle_cyclic_threshold() -> None:
    """Cycle the contact threshold through the Moore-neighborhood range."""
    global cyclic_threshold
    if simulation_mode != "cyclic_automaton":
        return
    save_history()
    cyclic_threshold = cyclic_threshold % CYCLIC_MAX_THRESHOLD + 1
    rebuild_context_menu()
    _sync_2d_history()
    set_status(f"Cyclic contact threshold: {cyclic_threshold}.")


def place_ant(row: int, col: int) -> None:
    """Move and reactivate Langton's ant without changing its heading."""
    global ant_state, simulation_active
    if simulation_mode != "langtons_ant":
        return
    if ant_state.row == row and ant_state.col == col and ant_state.active:
        return
    save_history()
    ant_state = AntState(row, col, ant_state.direction)
    simulation_active = False
    invalidate_render_cache("langtons_ant")
    _sync_2d_history()
    set_status(f"Ant moved to ({row}, {col}).")


def _zoom_2d(factor: float) -> None:
    global CELL_SIZE
    new_size = int(round(CELL_SIZE * factor))
    new_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, new_size))
    if new_size == CELL_SIZE:
        return
    CELL_SIZE = new_size
    _center_2d_view()
    set_status(f"Cell size: {CELL_SIZE}px")


def zoom(factor: float) -> None:
    """Zoom through the active workspace controller."""
    active_workspace().controller.zoom(factor)


def activate_pattern_menu() -> None:
    global pattern_menu_active, pattern_scroll, pattern_menu_category
    if active_dimension != "2d":
        set_status("Saved 2D patterns are available in the 2D workspace.")
        return
    pattern_menu_active = True
    pattern_scroll = 0
    pattern_menu_category = None


def toggle_heatmap() -> None:
    global show_heatmap
    show_heatmap = not show_heatmap
    if "main_menu" in globals():
        rebuild_context_menu()
    set_status(f"Heatmap {'on' if show_heatmap else 'off'}.")


def toggle_age_numbers() -> None:
    global show_age_numbers
    show_age_numbers = not show_age_numbers
    if "main_menu" in globals():
        rebuild_context_menu()
    set_status(f"Age numbers {'on' if show_age_numbers else 'off'}.")


def toggle_coordinates() -> None:
    global show_coordinates
    show_coordinates = not show_coordinates
    if "main_menu" in globals():
        rebuild_context_menu()
    set_status(f"Coordinates {'on' if show_coordinates else 'off'}.")


def toggle_quadrants() -> None:
    global show_quadrants
    show_quadrants = not show_quadrants
    if "main_menu" in globals():
        rebuild_context_menu()
    set_status(f"Quadrants {'on' if show_quadrants else 'off'}.")


def toggle_grid_lines() -> None:
    """Toggle grid lines and refresh the contextual control label."""
    global show_grid
    show_grid = not show_grid
    if "main_menu" in globals():
        rebuild_context_menu()
    set_status(f"Grid lines {'on' if show_grid else 'off'}.")


def get_text_input(prompt_text: str) -> str | None:
    """Collect a short name with an in-application modal text field."""
    input_box = pygame.Rect(
        max(20, (WINDOW_WIDTH - MENU_WIDTH) // 2 - 150),
        max(70, WINDOW_HEIGHT // 2 - 25),
        300,
        46,
    )
    text = ""
    active = True

    while active:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_RETURN:
                    return text.strip()
                if event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode and event.unicode.isprintable() and len(text) < 80:
                    text += event.unicode

        draw_scene()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        prompt = font.render(prompt_text, True, (255, 255, 255))
        screen.blit(prompt, (input_box.x, input_box.y - 34))
        pygame.draw.rect(screen, (20, 25, 35), input_box)
        pygame.draw.rect(screen, (70, 170, 255), input_box, 2)

        text_surface = font.render(text, True, (255, 255, 255))
        screen.blit(text_surface, (input_box.x + 8, input_box.y + 8))
        display_backend.present()
        clock.tick(60)

    return None


def get_pattern_name() -> str | None:
    return get_text_input("Pattern name")


def request_timeline_generation() -> None:
    """Prompt for and seek an exact generation in the active timeline."""
    value = get_text_input("Go to generation")
    if value is None:
        return
    try:
        target = int(value)
    except ValueError:
        set_status("Generation must be a non-negative integer.", 3.0)
        return
    if target < 0:
        set_status("Generation must be a non-negative integer.", 3.0)
        return
    if seek_active_generation(target):
        set_status(f"Moved to generation {target}.")
    else:
        set_status(f"Generation {target} is not present in this timeline.", 3.0)


def save_current_pattern() -> None:
    if simulation_mode == "cyclic_automaton":
        source = cyclic_grid
    elif simulation_mode == "immigration":
        source = immigration_grid
    elif simulation_mode == "brians_brain":
        source = brain_grid
    elif simulation_mode == "langtons_ant":
        source = ant_grid
    elif simulation_mode == "wireworld":
        source = wireworld_grid
    else:
        source = grid
    cropped, ant = crop_mode_pattern(source, simulation_mode)
    if not cropped:
        set_status("There are no pattern cells to save.")
        return

    name = get_pattern_name()
    if not name:
        set_status("Pattern save cancelled.")
        return

    try:
        save_pattern(
            cropped,
            name,
            mode=simulation_mode,
            ant=ant,
        )
    except (OSError, TypeError, ValueError) as exc:
        set_status(f"Could not save pattern: {exc}", 4.0)
        return

    set_status(f"Pattern '{name}' saved.")


LAST_SESSION_IDENTIFIER = "last_session"


def capture_session_document(name: str = "Last Session") -> dict[str, Any]:
    """Capture every persistent workspace and shared application setting."""
    return {
        "schema": SESSION_SCHEMA,
        "version": DOCUMENT_VERSION,
        "name": name,
        "saved_at": utc_timestamp(),
        "application": {
            "dimension": active_dimension,
            "mode": simulation_mode,
            "theme": current_theme,
            "speed": speed,
            "display": {
                "grid": show_grid,
                "heatmap": show_heatmap,
                "ages": show_age_numbers,
                "coordinates": show_coordinates,
                "quadrants": show_quadrants,
            },
        },
        "workspaces": {
            key: workspace_registry.get(key).controller.snapshot()
            for key in ("1d", "2d", "3d")
        },
    }


def restore_session_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate then atomically replace the application's persistent state."""
    global active_dimension, simulation_mode, current_theme, speed
    global show_grid, show_heatmap, show_age_numbers
    global show_coordinates, show_quadrants, simulation_active
    global single_step_requested, selected_pattern, pattern_menu_active
    global mode_menu_active, dimension_menu_active
    global drawing, drawing_history_pending

    normalized = validate_session_document(document)
    if normalized["workspaces"]["2d"]["shape"] != [ROWS, COLS]:
        shape = normalized["workspaces"]["2d"]["shape"]
        raise DocumentValidationError(
            f"Session grid is {shape}; this build requires [{ROWS}, {COLS}]."
        )

    application = normalized["application"]
    if not _switch_display_backend(application["dimension"]):
        raise DocumentValidationError(
            "The saved 3D workspace requires an OpenGL 3.3 renderer."
        )
    active_workspace().controller.deactivate()
    workspace_registry.get("1d").controller.restore(normalized["workspaces"]["1d"])
    workspace_registry.get("2d").controller.restore(normalized["workspaces"]["2d"])
    workspace_registry.get("3d").controller.restore(normalized["workspaces"]["3d"])

    active_dimension = application["dimension"]
    simulation_mode = application["mode"]
    current_theme = application["theme"]
    speed = application["speed"]
    display = application["display"]
    show_grid = display["grid"]
    show_heatmap = display["heatmap"]
    show_age_numbers = display["ages"]
    show_coordinates = display["coordinates"]
    show_quadrants = display["quadrants"]

    simulation_active = False
    single_step_requested = False
    selected_pattern = None
    pattern_menu_active = False
    mode_menu_active = False
    dimension_menu_active = False
    session_manager.close()
    if "analysis_panel" in globals():
        analysis_panel.close()
    if "export_manager" in globals():
        export_manager.close()
    drawing = False
    drawing_history_pending = False
    if "help_panel" in globals():
        help_panel.close()
    main_menu.theme = current_theme
    rebuild_context_menu()
    return normalized


def save_quick_session() -> bool:
    """Overwrite the single keyboard-accessible recovery session."""
    try:
        save_session(
            capture_session_document(),
            LAST_SESSION_IDENTIFIER,
            overwrite=True,
        )
    except (OSError, TypeError, ValueError, SessionStorageError) as exc:
        set_status(f"Could not save session: {exc}", 5.0)
        return False
    ui_preferences.record_recent("session", LAST_SESSION_IDENTIFIER, "Last Session")
    set_status("Complete session saved as 'Last Session'.", 3.0)
    return True


def load_quick_session() -> bool:
    """Load the keyboard-accessible recovery session when it exists."""
    return load_saved_session(LAST_SESSION_IDENTIFIER)


def save_named_session() -> bool:
    """Prompt for a name and save a new complete session."""
    name = get_text_input("Session name")
    if not name:
        set_status("Session save cancelled.")
        return False
    try:
        path = save_session(capture_session_document(name), name)
    except FileExistsError as exc:
        set_status(f"Could not save session: {exc}", 5.0)
        return False
    except (OSError, TypeError, ValueError, SessionStorageError) as exc:
        set_status(f"Could not save session: {exc}", 5.0)
        return False
    ui_preferences.record_recent("session", path.stem, name)
    set_status(f"Complete session '{name}' saved.", 3.0)
    return True


def load_saved_session(identifier: str) -> bool:
    """Load one named session without changing state on a validation error."""
    try:
        document = load_session(identifier)
        normalized = restore_session_document(document)
    except (OSError, TypeError, ValueError, SessionStorageError) as exc:
        set_status(f"Could not load session: {exc}", 5.0)
        return False
    ui_preferences.record_recent("session", identifier, normalized["name"])
    set_status(f"Session '{normalized['name']}' loaded; simulation paused.", 4.0)
    return True


def capture_experiment_profile(name: str) -> dict[str, Any]:
    """Capture the current 1D rule, boundary, and latest row as a seed."""
    return {
        "schema": PROFILE_SCHEMA,
        "version": DOCUMENT_VERSION,
        "name": name,
        "saved_at": utc_timestamp(),
        "experiment": elementary_controller.experiment_snapshot(),
    }


def save_current_experiment_profile() -> bool:
    """Prompt for and save a reusable generalized 1D experiment profile."""
    if active_dimension != "1d":
        set_status("Experiment profiles are available in the 1D workspace.")
        return False
    name = get_text_input("1D experiment profile name")
    if not name:
        set_status("Experiment profile save cancelled.")
        return False
    try:
        path = save_profile(capture_experiment_profile(name), name)
    except FileExistsError as exc:
        set_status(f"Could not save experiment profile: {exc}", 5.0)
        return False
    except (OSError, TypeError, ValueError, SessionStorageError) as exc:
        set_status(f"Could not save experiment profile: {exc}", 5.0)
        return False
    ui_preferences.record_recent("profile", path.stem, name)
    set_status(f"1D experiment profile '{name}' saved.", 3.0)
    return True


def restore_experiment_profile(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and restart 1D from an experiment profile."""
    normalized = validate_profile_document(document)
    if active_dimension != "1d":
        set_active_dimension("1d")
    elementary_controller.restore_experiment(normalized["experiment"])
    return normalized


def load_saved_experiment_profile(identifier: str) -> bool:
    """Load one saved 1D experiment profile."""
    try:
        document = load_profile(identifier)
        normalized = restore_experiment_profile(document)
    except (OSError, TypeError, ValueError, SessionStorageError) as exc:
        set_status(f"Could not load experiment profile: {exc}", 5.0)
        return False
    ui_preferences.record_recent("profile", identifier, normalized["name"])
    set_status(f"1D experiment '{normalized['name']}' loaded at generation 0.", 4.0)
    return True


def activate_session_menu() -> None:
    """Open the application-level session and experiment manager."""
    session_manager.open()


def _prepare_session_menu() -> None:
    """Pause and close competing overlays before the manager opens."""
    global simulation_active
    global dimension_menu_active, mode_menu_active, pattern_menu_active
    active_workspace().controller.deactivate()
    dimension_menu_active = False
    mode_menu_active = False
    pattern_menu_active = False
    simulation_active = False


def show_saved_session_catalog() -> None:
    """Display valid complete sessions without reading files every frame."""
    session_manager.show_sessions()


def show_experiment_profile_catalog() -> None:
    """Display valid 1D profiles without reading files every frame."""
    session_manager.show_profiles()


def session_menu_entries() -> list[dict[str, str]]:
    """Return cached rows for the current session-manager view."""
    return session_manager.entries()


def execute_session_menu_entry(key: str) -> None:
    """Run one session-manager action selected by mouse or number key."""
    session_manager.execute(key)


def session_menu_geometry(
) -> tuple[pygame.Rect, list[tuple[dict[str, str], pygame.Rect]], int]:
    """Return modal geometry, visible rows, and total visible capacity."""
    return session_manager.geometry()


def draw_session_menu() -> None:
    """Draw the full-session and generalized 1D profile manager."""
    session_manager.draw()


def handle_session_menu_event(event: pygame.event.Event) -> bool:
    """Handle session manager navigation without leaking events to a workspace."""
    return session_manager.handle_event(event)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def apply_life_generation() -> bool:
    global grid, trail_grid, activity_grid, generation, simulation_active

    if not any(cell > 0 for row in grid for cell in row):
        simulation_active = False
        set_status("Simulation stopped: no live cells.")
        return False

    save_history()
    new_grid = apply_rules_2d(grid, current_rule)

    for row in range(ROWS):
        for col in range(COLS):
            activity_grid[row][col] = max(0.0, activity_grid[row][col] - 0.10)
            trail_grid[row][col] = max(0, trail_grid[row][col] - 1)

            old_alive = grid[row][col] > 0
            new_alive = new_grid[row][col] > 0
            if old_alive != new_alive:
                cell_transition.start_transition(
                    row,
                    col,
                    grid[row][col],
                    new_grid[row][col],
                )
                activity_grid[row][col] += 1.0
                if old_alive and not new_alive:
                    trail_grid[row][col] = TRAIL_MAX

    grid = new_grid
    generation += 1
    mark_stats_dirty()
    return True


def apply_immigration_generation() -> bool:
    """Advance the two-species Immigration Game by one generation."""
    global immigration_grid, immigration_generation, simulation_active
    if not any(cell for row in immigration_grid for cell in row):
        simulation_active = False
        set_status("Immigration stopped: no live cells.")
        return False

    save_history()
    immigration_grid = apply_immigration_rules(immigration_grid)
    immigration_generation += 1
    invalidate_render_cache("immigration")
    return True


def apply_brain_generation() -> bool:
    """Advance Brian's Brain by one generation."""
    global brain_grid, brain_generation, simulation_active
    if not any(cell for row in brain_grid for cell in row):
        simulation_active = False
        set_status("Brian's Brain stopped: no active cells.")
        return False

    save_history()
    brain_grid = apply_brain_rules(brain_grid)
    brain_generation += 1
    invalidate_render_cache("brians_brain")
    return True


def apply_ant_generation() -> bool:
    """Advance Langton's Ant by one turn, flip, and movement step."""
    global ant_grid, ant_state, ant_generation, ant_last_report
    global simulation_active
    if not ant_state.active:
        simulation_active = False
        set_status("Langton's Ant stopped at the board boundary.")
        return False

    save_history()
    ant_grid, ant_state, ant_last_report = step_ant(ant_grid, ant_state)
    ant_generation += 1
    invalidate_render_cache("langtons_ant")
    if ant_last_report.exited:
        simulation_active = False
        set_status("Langton's Ant reached the finite board boundary.", 4.0)
    return True


def apply_wireworld_generation() -> bool:
    """Advance Wireworld by one synchronous signal propagation step."""
    global wireworld_grid, wireworld_generation, simulation_active
    has_signal = any(
        cell in (ELECTRON_HEAD, ELECTRON_TAIL)
        for row in wireworld_grid
        for cell in row
    )
    if not has_signal:
        simulation_active = False
        set_status("Wireworld stopped: no electron signal remains.")
        return False

    save_history()
    wireworld_grid = apply_wireworld_rules(wireworld_grid)
    wireworld_generation += 1
    invalidate_render_cache("wireworld")
    return True


def apply_cyclic_generation() -> bool:
    """Advance the cyclic color field by one synchronous generation."""
    global cyclic_grid, cyclic_generation, simulation_active
    next_grid = apply_cyclic_rules(
        cyclic_grid,
        state_count=CYCLIC_STATE_COUNT,
        threshold=cyclic_threshold,
    )
    if next_grid == cyclic_grid:
        simulation_active = False
        set_status("Cyclic Automaton stopped: no color can advance.")
        return False

    save_history()
    cyclic_grid = next_grid
    cyclic_generation += 1
    invalidate_render_cache("cyclic_automaton")
    return True


GENERATION_HANDLERS = {
    "life": apply_life_generation,
    "immigration": apply_immigration_generation,
    "brians_brain": apply_brain_generation,
    "langtons_ant": apply_ant_generation,
    "wireworld": apply_wireworld_generation,
    "cyclic_automaton": apply_cyclic_generation,
}


def _two_d_generation() -> int:
    """Return the counter belonging to the selected 2D mode."""
    return _generation_for_2d_mode(simulation_mode)


def _generation_for_2d_mode(mode: str) -> int:
    """Return a generation counter without changing the selected mode."""
    return {
        "life": generation,
        "immigration": immigration_generation,
        "brians_brain": brain_generation,
        "langtons_ant": ant_generation,
        "wireworld": wireworld_generation,
        "cyclic_automaton": cyclic_generation,
    }[mode]


def _analysis_observation_2d(mode: str) -> StateObservation:
    """Normalize one 2D mode without treating ages as distinct cell states."""
    title = MODE_BY_KEY[mode].name
    if mode == "life":
        values = tuple(1 if cell > 0 else 0 for row in grid for cell in row)
        return StateObservation(
            key="2d:life",
            title=title,
            generation=generation,
            values=values,
            state_count=2,
            active_states=(1,),
            population_label="Live cells",
            experiment_context=current_rule,
        )
    if mode == "immigration":
        values = tuple(
            1 if cell > 0 else 2 if cell < 0 else 0
            for row in immigration_grid
            for cell in row
        )
        return StateObservation(
            key="2d:immigration",
            title=title,
            generation=immigration_generation,
            values=values,
            state_count=3,
            active_states=(1, 2),
            population_label="Population",
            experiment_context="B3/S23",
        )
    if mode == "brians_brain":
        return StateObservation(
            key="2d:brians_brain",
            title=title,
            generation=brain_generation,
            values=tuple(cell for row in brain_grid for cell in row),
            state_count=3,
            active_states=(FIRING, DYING),
            population_label="Active cells",
            experiment_context="Brian's Brain",
        )
    if mode == "langtons_ant":
        return StateObservation(
            key="2d:langtons_ant",
            title=title,
            generation=ant_generation,
            values=tuple(cell for row in ant_grid for cell in row),
            state_count=2,
            active_states=(ANT_BLACK,),
            population_label="Black cells",
            experiment_context="RL finite",
            signature_context=(
                ant_state.row,
                ant_state.col,
                ant_state.direction,
                ant_state.active,
            ),
        )
    if mode == "wireworld":
        return StateObservation(
            key="2d:wireworld",
            title=title,
            generation=wireworld_generation,
            values=tuple(cell for row in wireworld_grid for cell in row),
            state_count=4,
            active_states=(ELECTRON_HEAD, ELECTRON_TAIL, CONDUCTOR),
            population_label="Occupied cells",
            experiment_context="Wireworld",
        )
    if mode == "cyclic_automaton":
        return StateObservation(
            key="2d:cyclic_automaton",
            title=title,
            generation=cyclic_generation,
            values=tuple(cell for row in cyclic_grid for cell in row),
            state_count=CYCLIC_STATE_COUNT,
            active_states=tuple(range(1, CYCLIC_STATE_COUNT)),
            population_label="Non-zero phase",
            experiment_context=(CYCLIC_STATE_COUNT, cyclic_threshold),
        )
    raise ValueError(f"Unknown 2D analysis mode: {mode}")


def active_analysis_series() -> AnalysisSeries:
    """Return the live series belonging to the active workspace."""
    observation = active_workspace().controller.analysis_observation()
    series = analysis_registry.get(observation.key)
    if series is None:
        series = analysis_registry.reset(observation)
    return series


def elementary_comparison_rules() -> tuple[int, ...]:
    """Compare the current Elementary rule with the featured reference set."""
    if elementary_controller.state.family != FAMILY_ELEMENTARY:
        return tuple(ECA_RULE_PRESETS)
    current = elementary_controller.state.rule
    return tuple(dict.fromkeys((current, *ECA_RULE_PRESETS)))


def toggle_analysis_panel() -> None:
    """Open or close the non-blocking scientific dashboard."""
    timeline_panel.stop()
    analysis_panel.toggle()


def _active_export_timeline_snapshots() -> tuple[Mapping[str, Any], ...]:
    """Reconstruct sampled frames without moving the visible timeline cursor."""
    if active_dimension == "1d":
        binding = elementary_controller.timeline
    elif active_dimension == "3d":
        binding = three_dimensional_controller.timeline
    else:
        binding = two_d_timelines[simulation_mode]
    timeline = binding.timeline
    return tuple(
        timeline.reconstruct(index)
        for index in sampled_indices(len(timeline.frames))
    )


def capture_current_raster() -> RasterFrame:
    """Return the active workspace's normalized PNG source."""
    return export_coordinator.capture_current_raster()


def capture_timeline_rasters() -> tuple[RasterFrame, ...]:
    """Return sampled, normalized animation frames without moving history."""
    return export_coordinator.capture_timeline_rasters()


def capture_shareable_experiment_document() -> dict[str, Any]:
    """Return a reloadable session enriched with active experiment metadata."""
    return export_coordinator.capture_shareable_document()


def _prepare_export_menu() -> None:
    """Pause and commit the current edit boundary before showing exports."""
    global simulation_active, single_step_requested
    global dimension_menu_active, mode_menu_active, pattern_menu_active
    global drawing, drawing_history_pending

    simulation_active = False
    single_step_requested = False
    timeline_panel.stop()
    session_manager.close()
    analysis_panel.close()
    dimension_menu_active = False
    mode_menu_active = False
    pattern_menu_active = False
    drawing = False
    drawing_history_pending = False
    active_workspace().controller.deactivate()
    active_workspace().controller.sync_history()


def activate_export_menu() -> None:
    """Open the contextual result export menu."""
    export_manager.open()


def toggle_export_menu() -> None:
    """Open or close result exports with the global X shortcut."""
    export_manager.toggle()


def _snapshot_2d_mode(mode: str) -> dict[str, Any]:
    """Capture one mode's simulation state for its independent timeline."""
    if mode == "life":
        return {
            "rule": current_rule,
            "grid": deepcopy(grid),
            "trail": deepcopy(trail_grid),
            "activity": deepcopy(activity_grid),
            "generation": generation,
        }
    if mode == "immigration":
        return {
            "grid": deepcopy(immigration_grid),
            "generation": immigration_generation,
        }
    if mode == "brians_brain":
        return {"grid": deepcopy(brain_grid), "generation": brain_generation}
    if mode == "langtons_ant":
        return {
            "grid": deepcopy(ant_grid),
            "generation": ant_generation,
            "ant": {
                "row": ant_state.row,
                "col": ant_state.col,
                "direction": ant_state.direction,
                "active": ant_state.active,
            },
            "report": {
                "turned": ant_last_report.turned,
                "painted_black": ant_last_report.painted_black,
                "exited": ant_last_report.exited,
            },
        }
    if mode == "wireworld":
        return {"grid": deepcopy(wireworld_grid), "generation": wireworld_generation}
    if mode == "cyclic_automaton":
        return {
            "grid": deepcopy(cyclic_grid),
            "generation": cyclic_generation,
            "threshold": cyclic_threshold,
        }
    raise ValueError(f"Unknown 2D mode: {mode}")


def _restore_2d_mode(mode: str, snapshot: Mapping[str, Any]) -> None:
    """Restore one trusted internal timeline frame and preserve its camera."""
    global grid, trail_grid, activity_grid, generation, current_rule
    global immigration_grid, immigration_generation
    global brain_grid, brain_generation
    global ant_grid, ant_state, ant_generation, ant_last_report
    global wireworld_grid, wireworld_generation
    global cyclic_grid, cyclic_generation, cyclic_threshold

    if mode == "life":
        current_rule = str(snapshot["rule"])
        grid = deepcopy(snapshot["grid"])
        trail_grid = deepcopy(snapshot["trail"])
        activity_grid = deepcopy(snapshot["activity"])
        generation = int(snapshot["generation"])
        cell_transition.transitions.clear()
        mark_stats_dirty()
    elif mode == "immigration":
        immigration_grid = deepcopy(snapshot["grid"])
        immigration_generation = int(snapshot["generation"])
        invalidate_render_cache(mode)
    elif mode == "brians_brain":
        brain_grid = deepcopy(snapshot["grid"])
        brain_generation = int(snapshot["generation"])
        invalidate_render_cache(mode)
    elif mode == "langtons_ant":
        ant_grid = deepcopy(snapshot["grid"])
        ant_generation = int(snapshot["generation"])
        saved_ant = snapshot["ant"]
        ant_state = AntState(
            int(saved_ant["row"]),
            int(saved_ant["col"]),
            int(saved_ant["direction"]),
            bool(saved_ant["active"]),
        )
        report = snapshot["report"]
        ant_last_report = AntStepReport(
            str(report["turned"]),
            bool(report["painted_black"]),
            bool(report["exited"]),
        )
        invalidate_render_cache(mode)
    elif mode == "wireworld":
        wireworld_grid = deepcopy(snapshot["grid"])
        wireworld_generation = int(snapshot["generation"])
        invalidate_render_cache(mode)
    elif mode == "cyclic_automaton":
        cyclic_grid = deepcopy(snapshot["grid"])
        cyclic_generation = int(snapshot["generation"])
        cyclic_threshold = int(snapshot["threshold"])
        invalidate_render_cache(mode)
    else:
        raise ValueError(f"Unknown 2D mode: {mode}")
    if "main_menu" in globals():
        rebuild_context_menu()


def _snapshot_2d() -> dict[str, Any]:
    """Return all six 2D mode states and the shared 2D camera."""
    return {
        "shape": [ROWS, COLS],
        "camera": {
            "cell_size": CELL_SIZE,
            "offset": [view_offset_x, view_offset_y],
        },
        "states": {
            "life": {
                "rule": current_rule,
                "grid": deepcopy(grid),
                "trail": deepcopy(trail_grid),
                "activity": deepcopy(activity_grid),
                "generation": generation,
            },
            "immigration": {
                "grid": deepcopy(immigration_grid),
                "generation": immigration_generation,
                "active_species": active_species,
            },
            "brians_brain": {
                "grid": deepcopy(brain_grid),
                "generation": brain_generation,
            },
            "langtons_ant": {
                "grid": deepcopy(ant_grid),
                "generation": ant_generation,
                "ant": {
                    "row": ant_state.row,
                    "col": ant_state.col,
                    "direction": ant_state.direction,
                    "active": ant_state.active,
                },
            },
            "wireworld": {
                "grid": deepcopy(wireworld_grid),
                "generation": wireworld_generation,
                "brush": wireworld_brush,
            },
            "cyclic_automaton": {
                "grid": deepcopy(cyclic_grid),
                "generation": cyclic_generation,
                "brush": cyclic_brush,
                "threshold": cyclic_threshold,
            },
        },
    }


def _restore_2d(snapshot: Mapping[str, Any]) -> None:
    """Replace every 2D mode state from a validated session snapshot."""
    global CELL_SIZE, view_offset_x, view_offset_y
    global grid, trail_grid, activity_grid, generation, current_rule
    global immigration_grid, immigration_generation, active_species
    global brain_grid, brain_generation
    global ant_grid, ant_state, ant_generation, ant_last_report
    global wireworld_grid, wireworld_generation, wireworld_brush
    global cyclic_grid, cyclic_generation, cyclic_brush, cyclic_threshold
    global recognized_pattern_cache, pattern_scan_generation
    global pattern_scan_revision, grid_revision, stats_dirty

    if list(snapshot["shape"]) != [ROWS, COLS]:
        raise ValueError(
            f"Session grid is {snapshot['shape']}; this build requires "
            f"[{ROWS}, {COLS}]."
        )
    camera = snapshot["camera"]
    states = snapshot["states"]
    life_state = states["life"]
    immigration_state = states["immigration"]
    brain_state = states["brians_brain"]
    ant_mode_state = states["langtons_ant"]
    wire_state = states["wireworld"]
    cyclic_state = states["cyclic_automaton"]

    CELL_SIZE = int(camera["cell_size"])
    view_offset_x, view_offset_y = map(int, camera["offset"])

    current_rule = str(life_state["rule"])
    grid = deepcopy(life_state["grid"])
    trail_grid = deepcopy(life_state["trail"])
    activity_grid = deepcopy(life_state["activity"])
    generation = int(life_state["generation"])

    immigration_grid = deepcopy(immigration_state["grid"])
    immigration_generation = int(immigration_state["generation"])
    active_species = int(immigration_state["active_species"])

    brain_grid = deepcopy(brain_state["grid"])
    brain_generation = int(brain_state["generation"])

    ant_grid = deepcopy(ant_mode_state["grid"])
    ant_generation = int(ant_mode_state["generation"])
    saved_ant = ant_mode_state["ant"]
    ant_state = AntState(
        int(saved_ant["row"]),
        int(saved_ant["col"]),
        int(saved_ant["direction"]),
        bool(saved_ant["active"]),
    )
    ant_last_report = AntStepReport()

    wireworld_grid = deepcopy(wire_state["grid"])
    wireworld_generation = int(wire_state["generation"])
    wireworld_brush = int(wire_state["brush"])

    cyclic_grid = deepcopy(cyclic_state["grid"])
    cyclic_generation = int(cyclic_state["generation"])
    cyclic_brush = int(cyclic_state["brush"])
    cyclic_threshold = int(cyclic_state["threshold"])

    cell_transition.transitions.clear()
    recognized_pattern_cache = {}
    pattern_scan_generation = -1
    pattern_scan_revision = -1
    grid_revision += 1
    stats_dirty = True
    for mode in SIMULATION_MODES:
        invalidate_render_cache(mode)
    for binding in two_d_timelines.values():
        binding.reset()
    for mode in SIMULATION_MODES:
        analysis_registry.reset(_analysis_observation_2d(mode))


def _apply_2d_generation() -> bool:
    advanced = GENERATION_HANDLERS[simulation_mode]()
    if advanced:
        _sync_2d_history()
    return advanced


def apply_generation() -> bool:
    """Advance through the active workspace controller."""
    return active_workspace().controller.advance()


# ---------------------------------------------------------------------------
# Statistics and drawing
# ---------------------------------------------------------------------------


def count_recognized_patterns(source: list[list[int]]) -> dict[str, int]:
    """Count known isolated patterns in a grid snapshot."""
    counts: dict[str, int] = {}
    for match in find_patterns(source):
        name = match["pattern"]["name"]
        counts[name] = counts.get(name, 0) + 1
    return counts


def calculate_life_population_stats() -> dict[str, Any]:
    """Calculate Life population values cached between grid mutations."""
    alive_cells = sum(1 for row in grid for cell in row if cell > 0)
    total_cells = ROWS * COLS
    return {
        "alive": alive_cells,
        "dead": total_cells - alive_cells,
        "density": 100.0 * alive_cells / total_cells if total_cells else 0.0,
    }


def calculate_stats() -> dict[str, Any]:
    global recognized_pattern_cache, pattern_scan_generation
    global pattern_scan_revision, pattern_scan_future, stats_dirty

    population_stats = cached_mode_stats(
        "life",
        calculate_life_population_stats,
    )

    if pattern_scan_future is not None and pattern_scan_future.done():
        try:
            scanned_counts = pattern_scan_future.result()
        except Exception as exc:  # Defensive: statistics must never stop the UI.
            set_status(f"Pattern scan failed: {exc}", 4.0)
        else:
            if pattern_scan_revision == grid_revision:
                recognized_pattern_cache = scanned_counts
                stats_dirty = False
        pattern_scan_future = None

    should_scan = stats_dirty and pattern_scan_future is None and (
        not simulation_active
        or generation % 5 == 0
        or pattern_scan_generation < 0
    )
    if should_scan:
        snapshot = [row[:] for row in grid]
        pattern_scan_revision = grid_revision
        pattern_scan_generation = generation
        pattern_scan_future = pattern_scan_executor.submit(
            count_recognized_patterns,
            snapshot,
        )

    return {
        **population_stats,
        "patterns": recognized_pattern_cache,
    }


def get_heatmap_color(activity: float) -> tuple[int, int, int, int]:
    if activity <= 0:
        return (0, 0, 0, 0)
    if activity < 5:
        return (0, 90, 255, min(180, int(55 + activity * 22)))
    if activity < 15:
        return (255, 220, 0, min(190, int(100 + (activity - 5) * 8)))
    return (255, 40, 20, 190)


def get_trail_color(trail_age: int) -> tuple[int, int, int, int]:
    alpha = int(170 * trail_age / TRAIL_MAX)
    return (255, 145, 0, alpha)


def blend_color(
    background: tuple[int, int, int],
    foreground: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(
        int(background[index] + (foreground[index] - background[index]) * amount)
        for index in range(3)
    )


def draw_grid() -> None:
    viewport = grid_viewport()
    origin_x, origin_y = grid_origin()
    theme = THEMES[current_theme]

    old_clip = screen.get_clip()
    screen.set_clip(viewport)
    visible_rects: list[pygame.Rect] = []
    effects_overlay = pygame.Surface(viewport.size, pygame.SRCALPHA)

    for row in range(ROWS):
        y = origin_y + row * CELL_SIZE
        if y + CELL_SIZE < viewport.top or y > viewport.bottom:
            continue

        for col in range(COLS):
            x = origin_x + col * CELL_SIZE
            if x + CELL_SIZE < viewport.left or x > viewport.right:
                continue

            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            visible_rects.append(rect)
            age = grid[row][col]
            transition = cell_transition.get_state(row, col)

            if transition is not None:
                start_alive = transition["start"] > 0
                end_alive = transition["end"] > 0
                progress = transition["progress"]

                if not start_alive and end_alive:
                    visibility = progress
                    visible_age = max(1, transition["end"])
                elif start_alive and not end_alive:
                    visibility = 1.0 - progress
                    visible_age = max(1, transition["start"])
                else:
                    visibility = 1.0
                    visible_age = max(1, age)

                alive_color = get_enhanced_age_color(visible_age, current_theme)
                if hasattr(alive_color, "r"):
                    alive_color = (alive_color.r, alive_color.g, alive_color.b)
                color = blend_color(theme["background"], alive_color, visibility)
                pygame.draw.rect(screen, color, rect)
            elif age > 0:
                color = get_enhanced_age_color(age, current_theme)
                pygame.draw.rect(screen, color, rect)

                if show_age_numbers and CELL_SIZE >= 14:
                    rgb = (
                        (color.r, color.g, color.b)
                        if hasattr(color, "r")
                        else color
                    )
                    text_color = BLACK if sum(rgb) > 400 else (255, 255, 255)
                    age_text = tiny_font.render(str(age), True, text_color)
                    screen.blit(age_text, age_text.get_rect(center=rect.center))

            if show_heatmap:
                heat_color = get_heatmap_color(activity_grid[row][col])
                if heat_color[3] > 0:
                    pygame.draw.rect(
                        effects_overlay,
                        heat_color,
                        rect.move(-viewport.x, -viewport.y),
                    )

            if trail_grid[row][col] > 0 and age <= 0:
                pygame.draw.rect(
                    effects_overlay,
                    get_trail_color(trail_grid[row][col]),
                    rect.move(-viewport.x, -viewport.y),
                )

    screen.blit(effects_overlay, viewport.topleft)
    if show_grid and CELL_SIZE >= 6:
        for rect in visible_rects:
            pygame.draw.rect(screen, theme["grid"], rect, 1)

    if show_quadrants:
        center_x = origin_x + COLS * CELL_SIZE // 2
        center_y = origin_y + ROWS * CELL_SIZE // 2
        pygame.draw.line(
            screen,
            theme["text"],
            (center_x, origin_y),
            (center_x, origin_y + ROWS * CELL_SIZE),
            2,
        )
        pygame.draw.line(
            screen,
            theme["text"],
            (origin_x, center_y),
            (origin_x + COLS * CELL_SIZE, center_y),
            2,
        )

    if show_coordinates and CELL_SIZE >= 10:
        step = 5
        for col in range(0, COLS, step):
            x = origin_x + col * CELL_SIZE + 2
            label = tiny_font.render(str(col), True, theme["text"])
            screen.blit(label, (x, origin_y + 2))
        for row in range(0, ROWS, step):
            y = origin_y + row * CELL_SIZE + 2
            label = tiny_font.render(str(row), True, theme["text"])
            screen.blit(label, (origin_x + 2, y))

    screen.set_clip(old_clip)


def draw_eca_grid() -> None:
    elementary_renderer.draw_base()


def immigration_species_base_color(species: int) -> tuple[int, int, int]:
    """Return the semantic full-brightness color for one Immigration species."""
    if species not in (SPECIES_A, SPECIES_B):
        raise ValueError(f"Unknown Immigration species: {species}")
    if current_theme == "colorblind":
        return COLORBLIND_BLUE if species == SPECIES_A else COLORBLIND_YELLOW
    if current_theme in ("pastel", "paper"):
        return LIGHT_MODE_BLUE if species == SPECIES_A else LIGHT_MODE_ORANGE
    return (40, 180, 255) if species == SPECIES_A else (255, 135, 35)


def immigration_species_label(species: int) -> str:
    """Describe a species using both its identifier and current palette color."""
    if species == SPECIES_A:
        color = "deep blue" if current_theme == "colorblind" else "blue"
        return f"A ({color})"
    if species == SPECIES_B:
        color = "yellow" if current_theme == "colorblind" else "orange"
        return f"B ({color})"
    raise ValueError(f"Unknown Immigration species: {species}")


def immigration_species_color(value: int) -> tuple[int, int, int]:
    """Return an age-adjusted, theme-aware color for an Immigration cell."""
    age = cell_age(value)
    brightness = (
        min(1.0, 0.94 + age * 0.006)
        if current_theme == "colorblind"
        else min(1.0, 0.62 + age * 0.025)
    )
    base = immigration_species_base_color(species_of(value))
    return tuple(int(channel * brightness) for channel in base)


def draw_immigration_marker(
    rect: pygame.Rect,
    value: int,
    surface: pygame.Surface | None = None,
) -> None:
    """Add a non-color Species-B cue in the accessible palette."""
    if current_theme != "colorblind" or species_of(value) != SPECIES_B:
        return
    target = screen if surface is None else surface
    marker = rect.inflate(-max(4, CELL_SIZE // 3), -max(4, CELL_SIZE // 3))
    if marker.width > 0 and marker.height > 0:
        marker_color: tuple[int, ...] = THEMES[current_theme]["background"]
        if target.get_flags() & pygame.SRCALPHA:
            marker_color += (210,)
        pygame.draw.rect(
            target,
            marker_color,
            marker,
            max(1, CELL_SIZE // 8),
        )


def brain_state_color(value: int) -> tuple[int, int, int]:
    """Return the conventional bright/dim colors for Brian's Brain."""
    if current_theme == "colorblind":
        return (240, 228, 66) if value == FIRING else (86, 180, 233)
    if current_theme in ("pastel", "paper"):
        return LIGHT_MODE_TEAL if value == FIRING else LIGHT_MODE_PURPLE
    if current_theme == "midnight":
        return (80, 235, 255) if value == FIRING else (170, 120, 230)
    return (80, 235, 255) if value == FIRING else (75, 55, 155)


def wireworld_state_color(value: int) -> tuple[int, int, int]:
    """Return conventional colors for the four Wireworld states."""
    colors = {
        WIRE_EMPTY: (10, 12, 18),
        ELECTRON_HEAD: (65, 170, 255),
        ELECTRON_TAIL: (235, 65, 55),
        CONDUCTOR: (245, 190, 35),
    }
    if current_theme == "colorblind":
        colors = {
            WIRE_EMPTY: (16, 24, 32),
            ELECTRON_HEAD: COLORBLIND_SKY,
            ELECTRON_TAIL: COLORBLIND_MAGENTA,
            CONDUCTOR: COLORBLIND_YELLOW,
        }
    return colors[value]


def cyclic_state_color(value: int) -> tuple[int, int, int]:
    """Return the fixed eight-state cyclic color wheel."""
    palette = (
        COLORBLIND_CYCLIC_PALETTE
        if current_theme == "colorblind"
        else CYCLIC_PALETTE
    )
    return palette[value]


def draw_immigration_grid() -> None:
    """Render both Immigration species while preserving encoded ages."""
    viewport = grid_viewport()
    origin_x, origin_y = grid_origin()
    theme = THEMES[current_theme]
    old_clip = screen.get_clip()
    screen.set_clip(viewport)

    for row in range(ROWS):
        y = origin_y + row * CELL_SIZE
        if y + CELL_SIZE < viewport.top or y > viewport.bottom:
            continue
        for col in range(COLS):
            x = origin_x + col * CELL_SIZE
            if x + CELL_SIZE < viewport.left or x > viewport.right:
                continue
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            value = immigration_grid[row][col]
            if value:
                color = immigration_species_color(value)
                pygame.draw.rect(screen, color, rect)
                draw_immigration_marker(rect, value)
                if show_age_numbers and CELL_SIZE >= 14:
                    age_text = tiny_font.render(
                        str(cell_age(value)),
                        True,
                        BLACK if sum(color) > 400 else (255, 255, 255),
                    )
                    screen.blit(age_text, age_text.get_rect(center=rect.center))
            if show_grid and CELL_SIZE >= 6:
                pygame.draw.rect(screen, theme["grid"], rect, 1)

    if show_quadrants:
        center_x = origin_x + COLS * CELL_SIZE // 2
        center_y = origin_y + ROWS * CELL_SIZE // 2
        pygame.draw.line(
            screen,
            theme["text"],
            (center_x, origin_y),
            (center_x, origin_y + ROWS * CELL_SIZE),
            2,
        )
        pygame.draw.line(
            screen,
            theme["text"],
            (origin_x, center_y),
            (origin_x + COLS * CELL_SIZE, center_y),
            2,
        )

    if show_coordinates and CELL_SIZE >= 10:
        for col in range(0, COLS, 5):
            label = tiny_font.render(str(col), True, theme["text"])
            screen.blit(label, (origin_x + col * CELL_SIZE + 2, origin_y + 2))
        for row in range(0, ROWS, 5):
            label = tiny_font.render(str(row), True, theme["text"])
            screen.blit(label, (origin_x + 2, origin_y + row * CELL_SIZE + 2))

    screen.set_clip(old_clip)


def draw_brain_grid() -> None:
    """Render firing cells and their one-generation dying trail."""
    viewport = grid_viewport()
    origin_x, origin_y = grid_origin()
    theme = THEMES[current_theme]
    old_clip = screen.get_clip()
    screen.set_clip(viewport)

    for row in range(ROWS):
        y = origin_y + row * CELL_SIZE
        if y + CELL_SIZE < viewport.top or y > viewport.bottom:
            continue
        for col in range(COLS):
            x = origin_x + col * CELL_SIZE
            if x + CELL_SIZE < viewport.left or x > viewport.right:
                continue
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            value = brain_grid[row][col]
            if value:
                pygame.draw.rect(screen, brain_state_color(value), rect)
            if show_grid and CELL_SIZE >= 6:
                pygame.draw.rect(screen, theme["grid"], rect, 1)

    if show_quadrants:
        center_x = origin_x + COLS * CELL_SIZE // 2
        center_y = origin_y + ROWS * CELL_SIZE // 2
        pygame.draw.line(
            screen,
            theme["text"],
            (center_x, origin_y),
            (center_x, origin_y + ROWS * CELL_SIZE),
            2,
        )
        pygame.draw.line(
            screen,
            theme["text"],
            (origin_x, center_y),
            (origin_x + COLS * CELL_SIZE, center_y),
            2,
        )

    if show_coordinates and CELL_SIZE >= 10:
        for col in range(0, COLS, 5):
            label = tiny_font.render(str(col), True, theme["text"])
            screen.blit(label, (origin_x + col * CELL_SIZE + 2, origin_y + 2))
        for row in range(0, ROWS, 5):
            label = tiny_font.render(str(row), True, theme["text"])
            screen.blit(label, (origin_x + 2, origin_y + row * CELL_SIZE + 2))

    screen.set_clip(old_clip)


def draw_wireworld_grid() -> None:
    """Render Wireworld conductors and electron signals."""
    viewport = grid_viewport()
    origin_x, origin_y = grid_origin()
    old_clip = screen.get_clip()
    screen.set_clip(viewport)
    pygame.draw.rect(screen, wireworld_state_color(WIRE_EMPTY), viewport)
    line_color = (55, 62, 72)

    for row in range(ROWS):
        y = origin_y + row * CELL_SIZE
        if y + CELL_SIZE < viewport.top or y > viewport.bottom:
            continue
        for col in range(COLS):
            x = origin_x + col * CELL_SIZE
            if x + CELL_SIZE < viewport.left or x > viewport.right:
                continue
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            value = wireworld_grid[row][col]
            if value != WIRE_EMPTY:
                pygame.draw.rect(screen, wireworld_state_color(value), rect)
            if show_grid and CELL_SIZE >= 6:
                pygame.draw.rect(screen, line_color, rect, 1)

    if show_quadrants:
        center_x = origin_x + COLS * CELL_SIZE // 2
        center_y = origin_y + ROWS * CELL_SIZE // 2
        pygame.draw.line(
            screen,
            (150, 155, 165),
            (center_x, origin_y),
            (center_x, origin_y + ROWS * CELL_SIZE),
            2,
        )
        pygame.draw.line(
            screen,
            (150, 155, 165),
            (origin_x, center_y),
            (origin_x + COLS * CELL_SIZE, center_y),
            2,
        )

    if show_coordinates and CELL_SIZE >= 10:
        for col in range(0, COLS, 5):
            label = tiny_font.render(str(col), True, (205, 210, 220))
            screen.blit(label, (origin_x + col * CELL_SIZE + 2, origin_y + 2))
        for row in range(0, ROWS, 5):
            label = tiny_font.render(str(row), True, (205, 210, 220))
            screen.blit(label, (origin_x + 2, origin_y + row * CELL_SIZE + 2))

    screen.set_clip(old_clip)


def draw_cyclic_grid() -> None:
    """Render every cyclic state as one color in a continuous wheel."""
    viewport = grid_viewport()
    origin_x, origin_y = grid_origin()
    old_clip = screen.get_clip()
    screen.set_clip(viewport)
    pygame.draw.rect(screen, cyclic_state_color(0), viewport)
    line_color = (42, 45, 58)

    for row in range(ROWS):
        y = origin_y + row * CELL_SIZE
        if y + CELL_SIZE < viewport.top or y > viewport.bottom:
            continue
        for col in range(COLS):
            x = origin_x + col * CELL_SIZE
            if x + CELL_SIZE < viewport.left or x > viewport.right:
                continue
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, cyclic_state_color(cyclic_grid[row][col]), rect)
            if show_grid and CELL_SIZE >= 6:
                pygame.draw.rect(screen, line_color, rect, 1)

    if show_quadrants:
        center_x = origin_x + COLS * CELL_SIZE // 2
        center_y = origin_y + ROWS * CELL_SIZE // 2
        pygame.draw.line(
            screen,
            (235, 235, 240),
            (center_x, origin_y),
            (center_x, origin_y + ROWS * CELL_SIZE),
            2,
        )
        pygame.draw.line(
            screen,
            (235, 235, 240),
            (origin_x, center_y),
            (origin_x + COLS * CELL_SIZE, center_y),
            2,
        )

    if show_coordinates and CELL_SIZE >= 10:
        for col in range(0, COLS, 5):
            label = tiny_font.render(str(col), True, (245, 245, 248))
            screen.blit(label, (origin_x + col * CELL_SIZE + 2, origin_y + 2))
        for row in range(0, ROWS, 5):
            label = tiny_font.render(str(row), True, (245, 245, 248))
            screen.blit(label, (origin_x + 2, origin_y + row * CELL_SIZE + 2))

    screen.set_clip(old_clip)


def ant_triangle_points(
    rect: pygame.Rect,
    direction: int,
) -> list[tuple[int, int]]:
    """Return a direction-facing triangle inside one grid cell."""
    margin = max(2, CELL_SIZE // 5)
    left, right = rect.left + margin, rect.right - margin
    top, bottom = rect.top + margin, rect.bottom - margin
    center_x, center_y = rect.center
    if direction == 0:
        return [(center_x, top), (right, bottom), (left, bottom)]
    if direction == 1:
        return [(right, center_y), (left, top), (left, bottom)]
    if direction == 2:
        return [(center_x, bottom), (left, top), (right, top)]
    return [(left, center_y), (right, bottom), (right, top)]


def ant_display_color(active: bool = True) -> tuple[int, int, int]:
    """Return a theme-aware ant color; direction remains shape encoded."""
    if current_theme == "colorblind":
        return COLORBLIND_BLUE if active else COLORBLIND_MAGENTA
    return (230, 35, 45) if active else (125, 35, 40)


def draw_ant_grid() -> None:
    """Render Langton's black/white board and its directional ant."""
    viewport = grid_viewport()
    origin_x, origin_y = grid_origin()
    old_clip = screen.get_clip()
    screen.set_clip(viewport)
    white_color = (235, 235, 225)
    black_color = (24, 25, 30)
    line_color = (105, 108, 112)

    for row in range(ROWS):
        y = origin_y + row * CELL_SIZE
        if y + CELL_SIZE < viewport.top or y > viewport.bottom:
            continue
        for col in range(COLS):
            x = origin_x + col * CELL_SIZE
            if x + CELL_SIZE < viewport.left or x > viewport.right:
                continue
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            color = black_color if ant_grid[row][col] == ANT_BLACK else white_color
            pygame.draw.rect(screen, color, rect)
            if show_grid and CELL_SIZE >= 6:
                pygame.draw.rect(screen, line_color, rect, 1)

    if show_quadrants:
        center_x = origin_x + COLS * CELL_SIZE // 2
        center_y = origin_y + ROWS * CELL_SIZE // 2
        pygame.draw.line(
            screen,
            COLORBLIND_BLUE if current_theme == "colorblind" else (175, 40, 45),
            (center_x, origin_y),
            (center_x, origin_y + ROWS * CELL_SIZE),
            2,
        )
        pygame.draw.line(
            screen,
            COLORBLIND_BLUE if current_theme == "colorblind" else (175, 40, 45),
            (origin_x, center_y),
            (origin_x + COLS * CELL_SIZE, center_y),
            2,
        )

    if show_coordinates and CELL_SIZE >= 10:
        for col in range(0, COLS, 5):
            label = tiny_font.render(str(col), True, black_color)
            screen.blit(label, (origin_x + col * CELL_SIZE + 2, origin_y + 2))
        for row in range(0, ROWS, 5):
            label = tiny_font.render(str(row), True, black_color)
            screen.blit(label, (origin_x + 2, origin_y + row * CELL_SIZE + 2))

    if 0 <= ant_state.row < ROWS and 0 <= ant_state.col < COLS:
        ant_rect = pygame.Rect(
            origin_x + ant_state.col * CELL_SIZE,
            origin_y + ant_state.row * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )
        points = ant_triangle_points(ant_rect, ant_state.direction)
        ant_color = ant_display_color(ant_state.active)
        outline = (
            white_color
            if ant_grid[ant_state.row][ant_state.col] == ANT_BLACK
            else black_color
        )
        pygame.draw.polygon(
            screen,
            ant_color,
            points,
        )
        pygame.draw.polygon(screen, outline, points, 1)
        if not ant_state.active:
            inset = max(2, CELL_SIZE // 4)
            pygame.draw.line(
                screen,
                outline,
                (ant_rect.left + inset, ant_rect.top + inset),
                (ant_rect.right - inset, ant_rect.bottom - inset),
                max(1, CELL_SIZE // 8),
            )
            pygame.draw.line(
                screen,
                outline,
                (ant_rect.right - inset, ant_rect.top + inset),
                (ant_rect.left + inset, ant_rect.bottom - inset),
                max(1, CELL_SIZE // 8),
            )

    screen.set_clip(old_clip)


def pattern_preview_color(
    value: int,
    pattern_mode: str | None,
) -> tuple[int, int, int]:
    """Return a state-aware preview color, including legacy binary patterns."""
    if pattern_mode == "immigration":
        return immigration_species_color(value)
    if pattern_mode == "brians_brain":
        return brain_state_color(value)
    if pattern_mode == "langtons_ant":
        return (20, 20, 25)
    if pattern_mode == "wireworld":
        return wireworld_state_color(value)
    if pattern_mode == "cyclic_automaton":
        return cyclic_state_color(value)
    if pattern_mode == "life":
        color = get_enhanced_age_color(1, current_theme)
    elif simulation_mode == "immigration":
        color = immigration_species_color(active_species)
    elif simulation_mode == "brians_brain":
        color = brain_state_color(FIRING)
    elif simulation_mode == "langtons_ant":
        color = (20, 20, 25)
    elif simulation_mode == "wireworld":
        color = wireworld_state_color(CONDUCTOR)
    elif simulation_mode == "cyclic_automaton":
        color = cyclic_state_color(cyclic_brush)
    else:
        color = get_enhanced_age_color(1, current_theme)
    if hasattr(color, "r"):
        return color.r, color.g, color.b
    return tuple(color)


def draw_pattern_preview() -> None:
    if selected_pattern is None:
        return

    position = mouse_to_grid(pygame.mouse.get_pos())
    if position is None:
        return

    start_row, start_col = position
    origin_x, origin_y = grid_origin()
    data, ant = transformed_pattern(selected_pattern)
    fits = pattern_fits(data, start_row, start_col)
    pattern_mode = selected_pattern.get("mode")

    preview = pygame.Surface(
        (len(data[0]) * CELL_SIZE, len(data) * CELL_SIZE),
        pygame.SRCALPHA,
    )

    for delta_row, pattern_row in enumerate(data):
        for delta_col, value in enumerate(pattern_row):
            if not value and pattern_mode != "cyclic_automaton":
                continue
            preview_color = (
                pattern_preview_color(value, pattern_mode) + (135,)
                if fits
                else (255, 45, 45, 155)
            )
            pygame.draw.rect(
                preview,
                preview_color,
                pygame.Rect(
                    delta_col * CELL_SIZE,
                    delta_row * CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE,
                ),
            )
            if fits and pattern_mode == "immigration":
                draw_immigration_marker(
                    pygame.Rect(
                        delta_col * CELL_SIZE,
                        delta_row * CELL_SIZE,
                        CELL_SIZE,
                        CELL_SIZE,
                    ),
                    value,
                    preview,
                )

    if ant is not None:
        ant_rect = pygame.Rect(
            ant["col"] * CELL_SIZE,
            ant["row"] * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )
        pygame.draw.polygon(
            preview,
            ant_display_color(True) + (190,) if fits else (255, 45, 45, 190),
            ant_triangle_points(ant_rect, ant["direction"]),
        )

    if not fits:
        invalid = (255, 45, 45, 220)
        preview_rect = preview.get_rect()
        line_width = max(2, CELL_SIZE // 6)
        pygame.draw.rect(preview, invalid, preview_rect, line_width)
        pygame.draw.line(
            preview,
            invalid,
            preview_rect.topleft,
            preview_rect.bottomright,
            line_width,
        )
        pygame.draw.line(
            preview,
            invalid,
            preview_rect.topright,
            preview_rect.bottomleft,
            line_width,
        )

    screen.blit(
        preview,
        (origin_x + start_col * CELL_SIZE, origin_y + start_row * CELL_SIZE),
    )


def _draw_2d_info_bar() -> None:
    theme = THEMES[current_theme]
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    pygame.draw.rect(screen, theme["info_bar"], (0, 0, width, INFO_BAR_HEIGHT))

    state = "Running" if simulation_active else "Paused"
    if simulation_mode == "cyclic_automaton":
        text = (
            f"{state}   Mode: Cyclic Cellular Automaton   Speed: {speed} gen/s   "
            f"Generation: {cyclic_generation}   Brush: Color {cyclic_brush}   "
            f"Threshold: {cyclic_threshold}"
        )
    elif simulation_mode == "wireworld":
        brush_label = WIRE_STATE_NAMES[wireworld_brush]
        text = (
            f"{state}   Mode: Wireworld   Speed: {speed} gen/s   "
            f"Generation: {wireworld_generation}   Brush: {brush_label}"
        )
    elif simulation_mode == "langtons_ant":
        direction = DIRECTION_NAMES[ant_state.direction]
        ant_status = "active" if ant_state.active else "stopped"
        text = (
            f"{state}   Mode: Langton's Ant   Step: {ant_generation}   "
            f"Direction: {direction}   Ant: {ant_status}"
        )
    elif simulation_mode == "brians_brain":
        text = (
            f"{state}   Mode: Brian's Brain   Speed: {speed} gen/s   "
            f"Generation: {brain_generation}   Rule: exactly 2 firing neighbors"
        )
    elif simulation_mode == "immigration":
        species_label = immigration_species_label(active_species)
        text = (
            f"{state}   Mode: Immigration Game   Speed: {speed} gen/s   "
            f"Generation: {immigration_generation}   Brush: {species_label}"
        )
    else:
        text = (
            f"{state}   Mode: Life-like   Speed: {speed} gen/s   "
            f"Generation: {generation}   Rule: {RULES[current_rule]['name']}"
        )
    tool_width = min(220, max(150, width // 4))
    available_width = max(40, width - 120 - tool_width - 18)
    shortened = text
    while shortened and small_font.size(shortened)[0] > available_width:
        shortened = shortened[:-1]
    if shortened != text:
        shortened = shortened.rstrip() + "..."
    rendered = small_font.render(shortened, True, theme["text"])
    screen.blit(rendered, (120, 11))


def _draw_2d_stats() -> None:
    theme = THEMES[current_theme]
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    y = WINDOW_HEIGHT - STATS_HEIGHT
    pygame.draw.rect(screen, theme["stats_bar"], (0, y, width, STATS_HEIGHT))
    history = _two_d_history_status()
    timeline_label = f"{history.cursor + 1}/{history.frame_count}"

    if simulation_mode == "cyclic_automaton":
        stats = cached_mode_stats(
            "cyclic_automaton",
            lambda: cyclic_stats(cyclic_grid, state_count=CYCLIC_STATE_COUNT),
        )
        first_line = (
            f"Colors present: {stats['diversity']}/{CYCLIC_STATE_COUNT}   "
            f"Dominant: {stats['dominant_state']} "
            f"({stats['dominant_share']:.1f}%)   "
            f"Normalized entropy: {stats['entropy']:.3f}   Timeline: "
            f"{timeline_label}"
        )
        second_line = (
            f"Color s advances to (s + 1) mod {CYCLIC_STATE_COUNT} when at least "
            f"{cyclic_threshold} Moore neighbors already have the next color."
        )
        screen.blit(small_font.render(first_line, True, theme["text"]), (10, y + 8))
        screen.blit(tiny_font.render(second_line, True, theme["text"]), (10, y + 38))
        return

    if simulation_mode == "wireworld":
        stats = cached_mode_stats(
            "wireworld",
            lambda: wireworld_stats(wireworld_grid),
        )
        first_line = (
            f"Heads: {stats['heads']}   Tails: {stats['tails']}   "
            f"Conductors: {stats['conductors']}   Empty: {stats['empty']}   "
            f"Density: {stats['density']:.2f}%   Timeline: {timeline_label}"
        )
        second_line = (
            "Head -> Tail   ·   Tail -> Conductor   ·   "
            "Conductor + exactly 1 or 2 neighboring heads -> Head"
        )
        screen.blit(small_font.render(first_line, True, theme["text"]), (10, y + 8))
        screen.blit(tiny_font.render(second_line, True, theme["text"]), (10, y + 38))
        return

    if simulation_mode == "langtons_ant":
        stats = cached_mode_stats(
            "langtons_ant",
            lambda: ant_stats(ant_grid),
        )
        first_line = (
            f"Black: {stats['black']}   White: {stats['white']}   "
            f"Black density: {stats['black_density']:.2f}%   "
            f"Ant: ({ant_state.row}, {ant_state.col})   Timeline: {timeline_label}"
        )
        action = (
            f"Last action: turn {ant_last_report.turned}"
            if ant_last_report.turned
            else "Last action: none"
        )
        second_line = (
            f"{action}   ·   White: turn right, paint black   ·   "
            "Black: turn left, paint white"
        )
        screen.blit(small_font.render(first_line, True, theme["text"]), (10, y + 8))
        screen.blit(tiny_font.render(second_line, True, theme["text"]), (10, y + 38))
        return

    if simulation_mode == "brians_brain":
        stats = cached_mode_stats(
            "brians_brain",
            lambda: brain_stats(brain_grid),
        )
        first_line = (
            f"Active: {stats['active']}   Firing: {stats['firing']}   "
            f"Dying: {stats['dying']}   Off: {stats['off']}   "
            f"Density: {stats['density']:.2f}%   Timeline: {timeline_label}"
        )
        second_line = (
            "Off + exactly 2 firing neighbors → Firing   ·   "
            "Firing → Dying   ·   Dying → Off"
        )
        screen.blit(small_font.render(first_line, True, theme["text"]), (10, y + 8))
        screen.blit(tiny_font.render(second_line, True, theme["text"]), (10, y + 38))
        return

    if simulation_mode == "immigration":
        stats = cached_mode_stats(
            "immigration",
            lambda: immigration_stats(immigration_grid),
        )
        first_line = (
            f"Population: {stats['population']}   Species A: {stats['species_a']}   "
            f"Species B: {stats['species_b']}   Density: {stats['density']:.2f}%   "
            f"Timeline: {timeline_label}"
        )
        second_line = (
            f"A share: {stats['balance']:.1f}%   B share: "
            f"{100.0 - stats['balance']:.1f}%   Average age: {stats['average_age']:.1f}   "
            "Birth species follows the majority of its three parents."
        )
        screen.blit(small_font.render(first_line, True, theme["text"]), (10, y + 8))
        screen.blit(tiny_font.render(second_line, True, theme["text"]), (10, y + 38))
        return

    stats = calculate_stats()

    first_line = (
        f"Alive: {stats['alive']}   Dead: {stats['dead']}   "
        f"Density: {stats['density']:.2f}%   Timeline: {timeline_label}"
    )
    screen.blit(
        small_font.render(first_line, True, theme["text"]),
        (10, y + 8),
    )

    if stats["patterns"]:
        patterns_text = ", ".join(
            f"{name}: {count}" for name, count in sorted(stats["patterns"].items())
        )
    else:
        patterns_text = "Recognized isolated patterns: none"

    available_width = max(20, width - 20)
    if tiny_font.size(patterns_text)[0] > available_width:
        ellipsis = "..."
        while patterns_text and tiny_font.size(patterns_text + ellipsis)[0] > available_width:
            patterns_text = patterns_text[:-1]
        patterns_text = patterns_text.rstrip(" ,:") + ellipsis

    rendered = tiny_font.render(patterns_text, True, theme["text"])
    screen.blit(rendered, (10, y + 38))


def _draw_2d_bars() -> None:
    _draw_2d_info_bar()
    _draw_2d_stats()


def draw_rule_overlay() -> None:
    if (
        active_dimension != "2d"
        or simulation_mode != "life"
        or time.time() >= show_rule_overlay_until
    ):
        return

    overlay_width = 390
    overlay_height = 45 + 30 * len(RULES)
    overlay_x = max(10, (WINDOW_WIDTH - MENU_WIDTH - overlay_width) // 2)
    overlay_y = INFO_BAR_HEIGHT + 35
    overlay = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
    overlay.fill((25, 25, 30, 225))

    overlay.blit(font.render("Available rules", True, (255, 255, 255)), (18, 10))
    for index, (key, rule) in enumerate(RULES.items()):
        row_y = 43 + index * 30
        if key == current_rule:
            pygame.draw.rect(
                overlay,
                (85, 85, 10, 190),
                (9, row_y - 2, overlay_width - 18, 27),
            )
            color = (255, 245, 80)
        else:
            color = (210, 210, 210)

        notation = (
            f"B{''.join(map(str, rule['birth']))}/"
            f"S{''.join(map(str, rule['survival']))}"
        )
        overlay.blit(
            small_font.render(f"{rule['name']} — {notation}", True, color),
            (18, row_y),
        )

    screen.blit(overlay, (overlay_x, overlay_y))


def pattern_menu_geometry() -> tuple[int, int, int, int]:
    menu_x = WINDOW_WIDTH - MENU_WIDTH
    menu_y = INFO_BAR_HEIGHT + 8
    menu_height = WINDOW_HEIGHT - menu_y - 8
    visible_rows = max(1, (menu_height - 34) // PATTERN_ROW_HEIGHT)
    return menu_x, menu_y, menu_height, visible_rows


def available_patterns() -> dict[str, dict[str, Any]]:
    """Return the shared cached patterns for the active simulation mode."""
    return get_patterns_for_mode(simulation_mode)


def available_pattern_categories() -> tuple[tuple[str, str, int], ...]:
    """Return ordered category labels and counts for the active mode."""
    return get_pattern_categories_for_mode(simulation_mode)


def pattern_menu_items() -> list[tuple[str, str, str, Any]]:
    """Build rows for the category level or the selected category level."""
    if pattern_menu_category is None:
        items: list[tuple[str, str, str, Any]] = [
            ("category", "all", "All Patterns", len(available_patterns()))
        ]
        items.extend(
            ("category", key, label, count)
            for key, label, count in available_pattern_categories()
        )
        return items

    return [
        ("pattern", key, pattern["name"], pattern)
        for key, pattern in get_patterns_for_category(
            simulation_mode,
            pattern_menu_category,
        ).items()
    ]


def pattern_category_label(category: str) -> str:
    """Return a display label for a cached category key."""
    if category == "all":
        return "All Patterns"
    for key, label, _ in available_pattern_categories():
        if key == category:
            return label
    return category.replace("_", " ").title()


def open_pattern_category(category: str) -> None:
    """Enter one pattern submenu and reset its independent scroll position."""
    global pattern_menu_category, pattern_scroll
    get_patterns_for_category(simulation_mode, category)
    pattern_menu_category = category
    pattern_scroll = 0


def return_to_pattern_categories() -> None:
    """Return to the category level without closing the menu."""
    global pattern_menu_category, pattern_scroll
    pattern_menu_category = None
    pattern_scroll = 0


def _fit_pattern_menu_text(text: str, width: int) -> str:
    """Ellipsize a pattern-menu label to the available width."""
    if tiny_font.size(text)[0] <= width:
        return text
    ellipsis = "..."
    shortened = text
    while shortened and tiny_font.size(shortened + ellipsis)[0] > width:
        shortened = shortened[:-1]
    return shortened.rstrip() + ellipsis


def draw_pattern_menu() -> None:
    if not pattern_menu_active:
        return

    items = pattern_menu_items()
    menu_x, menu_y, menu_height, visible_rows = pattern_menu_geometry()
    visible = items[pattern_scroll : pattern_scroll + visible_rows]
    theme = THEMES[current_theme]

    surface = pygame.Surface((MENU_WIDTH, menu_height))
    surface.fill(theme["menu"])
    pygame.draw.rect(surface, theme["menu_text"], surface.get_rect(), 2)
    mode_name = MODE_BY_KEY[simulation_mode].name
    if pattern_menu_category is None:
        heading_text = f"{mode_name} Pattern Categories · Esc closes"
    else:
        heading_text = (
            f"< Categories · {pattern_category_label(pattern_menu_category)}"
            " · Backspace returns"
        )
    heading = tiny_font.render(
        _fit_pattern_menu_text(heading_text, MENU_WIDTH - 20),
        True,
        theme["menu_text"],
    )
    surface.blit(heading, (10, 8))

    mouse_x, mouse_y = pygame.mouse.get_pos()
    for index, (kind, _, label, payload) in enumerate(visible):
        row_y = 32 + index * PATTERN_ROW_HEIGHT
        absolute_rect = pygame.Rect(
            menu_x,
            menu_y + row_y,
            MENU_WIDTH,
            PATTERN_ROW_HEIGHT,
        )
        if absolute_rect.collidepoint(mouse_x, mouse_y):
            pygame.draw.rect(
                surface,
                theme["button_hover"],
                (2, row_y, MENU_WIDTH - 4, PATTERN_ROW_HEIGHT),
            )

        number = index + 1
        if kind == "category":
            row_label = f"{number}. {label} ({payload})  >"
        else:
            row_label = f"{number}. {label}" if number <= 9 else label
        surface.blit(
            tiny_font.render(
                _fit_pattern_menu_text(row_label, MENU_WIDTH - 20),
                True,
                theme["menu_text"],
            ),
            (10, row_y + 8),
        )

    footer = (
        f"{pattern_scroll + 1}-{pattern_scroll + len(visible)} / {len(items)}"
        if items
        else "0 / 0"
    )
    surface.blit(
        tiny_font.render(footer, True, theme["menu_text"]),
        (MENU_WIDTH - 90, menu_height - 19),
    )
    screen.blit(surface, (menu_x, menu_y))


def mode_menu_geometry() -> tuple[pygame.Rect, list[tuple[str, pygame.Rect]]]:
    """Return the modal and card rectangles for the responsive mode chooser."""
    modal_width = min(760, WINDOW_WIDTH - 40)
    modal_height = min(520, WINDOW_HEIGHT - 40)
    modal = pygame.Rect(0, 0, modal_width, modal_height)
    modal.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

    columns = 2
    rows = (len(MODE_DEFINITIONS) + columns - 1) // columns
    horizontal_margin = 24
    card_gap = 12
    cards_top = modal.y + 70
    cards_bottom = modal.bottom - 48
    card_width = (modal.width - 2 * horizontal_margin - card_gap) // columns
    card_height = (cards_bottom - cards_top - (rows - 1) * card_gap) // rows
    cards: list[tuple[str, pygame.Rect]] = []
    for index, definition in enumerate(MODE_DEFINITIONS):
        row, col = divmod(index, columns)
        card = pygame.Rect(
            modal.x + horizontal_margin + col * (card_width + card_gap),
            cards_top + row * (card_height + card_gap),
            card_width,
            card_height,
        )
        cards.append((definition.key, card))
    return modal, cards


def wrap_text(text: str, render_font: pygame.font.Font, width: int) -> list[str]:
    """Wrap a short UI description to the available pixel width."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and render_font.size(candidate)[0] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_mode_menu() -> None:
    """Draw an explanatory card chooser over the paused application."""
    if not mode_menu_active:
        return

    dimmer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    dimmer.fill((0, 0, 0, 180))
    screen.blit(dimmer, (0, 0))

    modal, cards = mode_menu_geometry()
    pygame.draw.rect(screen, (28, 31, 39), modal, border_radius=10)
    pygame.draw.rect(screen, (205, 210, 220), modal, 2, border_radius=10)
    screen.blit(
        font.render("Choose a simulation mode", True, (245, 247, 250)),
        (modal.x + 24, modal.y + 18),
    )

    mouse_position = pygame.mouse.get_pos()
    for index, (mode_key, card) in enumerate(cards):
        definition = MODE_BY_KEY[mode_key]
        selected = mode_key == simulation_mode
        hovered = card.collidepoint(mouse_position)
        background = (48, 52, 63) if hovered or selected else (38, 42, 52)
        pygame.draw.rect(screen, background, card, border_radius=7)
        border = definition.accent if selected or hovered else (90, 96, 110)
        pygame.draw.rect(screen, border, card, 3 if selected else 2, border_radius=7)

        badge = pygame.Rect(card.x + 12, card.y + 11, 25, 25)
        pygame.draw.rect(screen, definition.accent, badge, border_radius=5)
        number = tiny_font.render(str(index + 1), True, (15, 18, 24))
        screen.blit(number, number.get_rect(center=badge.center))
        screen.blit(
            small_font.render(definition.name, True, (248, 249, 252)),
            (card.x + 47, card.y + 13),
        )

        for line_index, line in enumerate(
            wrap_text(definition.summary, tiny_font, card.width - 24)[:3]
        ):
            screen.blit(
                tiny_font.render(line, True, (195, 200, 212)),
                (card.x + 12, card.y + 47 + line_index * 16),
            )

        if selected:
            current_label = tiny_font.render("Current mode", True, definition.accent)
            screen.blit(
                current_label,
                (card.right - current_label.get_width() - 12, card.y + 16),
            )

    footer = f"Click a card or press 1-{len(MODE_DEFINITIONS)}   ·   Esc closes"
    footer_surface = tiny_font.render(footer, True, (190, 195, 205))
    screen.blit(
        footer_surface,
        (modal.centerx - footer_surface.get_width() // 2, modal.bottom - 31),
    )


def handle_mode_menu_event(event: pygame.event.Event) -> bool:
    """Handle keyboard and mouse selection while the mode chooser is open."""
    global mode_menu_active
    if not mode_menu_active:
        return False

    if event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_ESCAPE, pygame.K_m):
            mode_menu_active = False
            return True
        if pygame.K_1 <= event.key < pygame.K_1 + len(MODE_DEFINITIONS):
            index = event.key - pygame.K_1
            set_simulation_mode(MODE_DEFINITIONS[index].key)
            return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        modal, cards = mode_menu_geometry()
        for mode_key, card in cards:
            if card.collidepoint(event.pos):
                set_simulation_mode(mode_key)
                return True
        if not modal.collidepoint(event.pos):
            mode_menu_active = False
        return True

    return True


def dimension_menu_geometry() -> tuple[pygame.Rect, list[tuple[str, pygame.Rect]]]:
    """Return responsive rectangles for the 1D/2D/3D workspace chooser."""
    modal_width = min(820, WINDOW_WIDTH - 40)
    modal_height = min(390, WINDOW_HEIGHT - 40)
    modal = pygame.Rect(0, 0, modal_width, modal_height)
    modal.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

    horizontal_margin = 24
    card_gap = 12
    cards_top = modal.y + 72
    cards_bottom = modal.bottom - 52
    card_width = (
        modal.width
        - 2 * horizontal_margin
        - card_gap * (len(DIMENSION_DEFINITIONS) - 1)
    ) // len(DIMENSION_DEFINITIONS)
    cards = []
    for index, definition in enumerate(DIMENSION_DEFINITIONS):
        card = pygame.Rect(
            modal.x + horizontal_margin + index * (card_width + card_gap),
            cards_top,
            card_width,
            cards_bottom - cards_top,
        )
        cards.append((definition.key, card))
    return modal, cards


def draw_dimension_menu() -> None:
    """Draw the top-level dimensional workspace chooser."""
    if not dimension_menu_active:
        return

    dimmer = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    dimmer.fill((0, 0, 0, 195))
    screen.blit(dimmer, (0, 0))

    modal, cards = dimension_menu_geometry()
    pygame.draw.rect(screen, (25, 28, 36), modal, border_radius=12)
    pygame.draw.rect(screen, (210, 214, 224), modal, 2, border_radius=12)
    screen.blit(
        font.render("Choose a simulation dimension", True, (245, 247, 250)),
        (modal.x + 24, modal.y + 19),
    )

    mouse_position = pygame.mouse.get_pos()
    for index, (dimension_key, card) in enumerate(cards):
        definition = DIMENSION_BY_KEY[dimension_key]
        selected = dimension_key == active_dimension
        hovered = card.collidepoint(mouse_position) and definition.available
        if definition.available:
            background = (49, 54, 66) if hovered or selected else (37, 41, 51)
            border = definition.accent if hovered or selected else (88, 94, 108)
            title_color = (248, 249, 252)
            body_color = (195, 201, 213)
        else:
            background = (32, 34, 42)
            border = (72, 75, 86)
            title_color = (145, 148, 158)
            body_color = (118, 121, 132)
        pygame.draw.rect(screen, background, card, border_radius=8)
        pygame.draw.rect(screen, border, card, 3 if selected else 2, border_radius=8)

        badge = pygame.Rect(card.x + 13, card.y + 13, 27, 27)
        badge_color = definition.accent if definition.available else (80, 82, 91)
        pygame.draw.rect(screen, badge_color, badge, border_radius=5)
        number = tiny_font.render(str(index + 1), True, (15, 18, 24))
        screen.blit(number, number.get_rect(center=badge.center))
        for line_index, line in enumerate(
            wrap_text(definition.name, small_font, card.width - 28)[:2]
        ):
            screen.blit(
                small_font.render(line, True, title_color),
                (card.x + 13, card.y + 53 + line_index * 20),
            )
        for line_index, line in enumerate(
            wrap_text(definition.summary, tiny_font, card.width - 26)[:6]
        ):
            screen.blit(
                tiny_font.render(line, True, body_color),
                (card.x + 13, card.y + 101 + line_index * 16),
            )

        if selected:
            label = tiny_font.render("Current", True, definition.accent)
            screen.blit(label, (card.right - label.get_width() - 12, card.y + 20))
        elif not definition.available:
            label = tiny_font.render("PLANNED", True, definition.accent)
            screen.blit(label, (card.x + 13, card.bottom - 28))

    footer = "Click a card or press 1-3   ·   workspace state is preserved   ·   Esc closes"
    footer_surface = tiny_font.render(footer, True, (188, 193, 204))
    screen.blit(
        footer_surface,
        (modal.centerx - footer_surface.get_width() // 2, modal.bottom - 32),
    )


def handle_dimension_menu_event(event: pygame.event.Event) -> bool:
    """Handle keyboard and mouse selection in the dimension chooser."""
    global dimension_menu_active
    if not dimension_menu_active:
        return False

    if event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_ESCAPE, pygame.K_d):
            dimension_menu_active = False
            return True
        if pygame.K_1 <= event.key < pygame.K_1 + len(DIMENSION_DEFINITIONS):
            index = event.key - pygame.K_1
            set_active_dimension(DIMENSION_DEFINITIONS[index].key)
            return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        modal, cards = dimension_menu_geometry()
        for dimension_key, card in cards:
            if card.collidepoint(event.pos):
                set_active_dimension(dimension_key)
                return True
        if not modal.collidepoint(event.pos):
            dimension_menu_active = False
        return True

    return True


def activate_eca_rule_menu() -> None:
    """Open the Elementary workspace's complete rule catalogue."""
    elementary_controller.open_rule_menu()


def eca_rule_menu_geometry() -> tuple[pygame.Rect, list[tuple[int, pygame.Rect]]]:
    """Return the Elementary workspace's rule-catalogue layout."""
    return elementary_controller.rule_menu_geometry()


def draw_eca_rule_menu() -> None:
    """Draw the Elementary workspace's rule-selection modal."""
    elementary_renderer.draw_modal()


def handle_eca_rule_menu_event(event: pygame.event.Event) -> bool:
    """Delegate rule-selection input to the Elementary workspace."""
    return elementary_controller.handle_overlay_event(event)


def draw_status() -> None:
    if not status_message or time.time() >= status_message_until:
        return

    text_surface = small_font.render(status_message, True, (255, 255, 255))
    box = text_surface.get_rect()
    box.inflate_ip(20, 14)
    box.centerx = max(1, WINDOW_WIDTH - MENU_WIDTH) // 2
    box.bottom = timeline_rect().top - 8

    overlay = pygame.Surface(box.size, pygame.SRCALPHA)
    overlay.fill((20, 25, 35, 220))
    screen.blit(overlay, box)
    screen.blit(text_surface, text_surface.get_rect(center=box.center))


def run_pause_rect() -> pygame.Rect:
    """Return the clickable status control shared by every workspace."""
    return pygame.Rect(8, 7, 104, INFO_BAR_HEIGHT - 14)


def active_tool_label() -> str:
    """Describe the currently effective drawing tool without relying on color."""
    if active_dimension == "1d":
        return f"Cell state {elementary_controller.state.brush_state}"
    if active_dimension == "3d":
        return "Orbit camera · Add voxel"
    if selected_pattern is not None:
        return f"Pattern: {selected_pattern['name']}"
    if simulation_mode == "immigration":
        return f"Species {'A' if active_species == SPECIES_A else 'B'}"
    if simulation_mode == "wireworld":
        return WIRE_STATE_NAMES[wireworld_brush]
    if simulation_mode == "cyclic_automaton":
        return f"Color state {cyclic_brush}"
    if simulation_mode == "langtons_ant":
        return "Board draw · Shift places ant"
    if simulation_mode == "brians_brain":
        return "Firing cell"
    return "Live cell"


def toggle_simulation_running() -> None:
    global simulation_active
    timeline_panel.stop()
    simulation_active = not simulation_active
    rebuild_context_menu()
    set_status("Simulation running." if simulation_active else "Simulation paused.")


def draw_workspace_status_controls() -> None:
    """Draw high-contrast run/pause and active-tool badges over the info bar."""
    theme = THEMES[current_theme]
    content_width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    run_rect = run_pause_rect()
    run_color = COLORBLIND_BLUE if simulation_active else (95, 105, 115)
    pygame.draw.rect(screen, run_color, run_rect, border_radius=6)
    pygame.draw.rect(screen, theme["text"], run_rect, 1, border_radius=6)
    if simulation_active:
        pygame.draw.polygon(
            screen,
            (255, 255, 255),
            [
                (run_rect.x + 10, run_rect.y + 7),
                (run_rect.x + 10, run_rect.bottom - 7),
                (run_rect.x + 22, run_rect.centery),
            ],
        )
        label = "RUNNING"
    else:
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            (run_rect.x + 10, run_rect.y + 7, 4, run_rect.height - 14),
        )
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            (run_rect.x + 18, run_rect.y + 7, 4, run_rect.height - 14),
        )
        label = "PAUSED"
    screen.blit(
        tiny_font.render(label, True, (255, 255, 255)),
        (run_rect.x + 30, run_rect.y + 8),
    )

    tool_width = min(220, max(150, content_width // 4))
    tool_rect = pygame.Rect(
        max(run_rect.right + 8, content_width - tool_width - 8),
        7,
        tool_width,
        INFO_BAR_HEIGHT - 14,
    )
    pygame.draw.rect(screen, theme["button"], tool_rect, border_radius=6)
    accent = (
        DIMENSION_BY_KEY[active_dimension].accent
        if active_dimension in ("1d", "3d")
        else MODE_BY_KEY[simulation_mode].accent
    )
    pygame.draw.rect(screen, accent, tool_rect, 2, border_radius=6)
    text = f"TOOL · {active_tool_label()}"
    while text and tiny_font.size(text)[0] > tool_rect.width - 16:
        text = text[:-1]
    screen.blit(
        tiny_font.render(text.rstrip(), True, theme["button_text"]),
        (tool_rect.x + 8, tool_rect.y + 8),
    )


def help_context_title() -> str:
    if active_dimension == "1d":
        return f"1D · {elementary_controller.family_name}"
    if active_dimension == "3d":
        return f"3D · {three_dimensional_controller.rule.name}"
    return f"2D · {MODE_BY_KEY[simulation_mode].name}"


def help_context_entries() -> tuple[tuple[str, str], ...]:
    if active_dimension == "1d":
        return (
            ("E", "Open the searchable Elementary rule catalogue"),
            ("Left / Right click", "Write the selected state / erase state"),
            ("Middle drag", "Pan the space-time diagram"),
            ("Seed Width", "Choose compact, viewport, or wide initial rows"),
            ("Rule catalogue: F", "Show all rules or favorite rules only"),
            ("Catalogue right click", "Add or remove a favorite rule"),
            ("Timeline arrows", "Step backward or forward through recorded state"),
        )
    if active_dimension == "3d":
        return (
            ("M", "Switch Spatial Life / 3D Generations mode"),
            ("V", "Cycle 32³, 48³, and 64³ experiment volumes"),
            ("U", "Cycle Softology-inspired voxel color schemes"),
            ("Left drag", "Orbit the perspective camera around the volume"),
            ("Mouse wheel", "Zoom the 3D camera"),
            ("Middle drag", "Pan the camera target"),
            ("Left click", "Add a voxel beside the highlighted voxel"),
            ("Right click", "Erase the highlighted voxel"),
            ("L", "Cycle full volume, clipping plane, and single-layer views"),
            ("Q / , / .", "Change filter axis or move its layer plane"),
            ("/", "Reverse which side of the clipping plane stays visible"),
            ("O", "Cycle solid, 65%, and 35% voxel opacity"),
            ("B", "Cycle fixed, wrapped, and reflected boundaries"),
            ("K", "Switch between 26-neighbor and six-face rule families"),
            ("Ctrl+0 / C", "Fit or reset the complete volume view"),
            ("Timeline arrows", "Step backward or forward through 3D generations"),
        )
    entries = [
        ("Left / Right click", "Draw with the active tool / erase a cell"),
        ("Middle drag", "Pan the grid"),
        ("Ctrl+0", "Fit the complete finite board into the window"),
        ("T", "Cycle the current mode's brush or state"),
        ("1–9", "Select a visible mode-specific pattern"),
    ]
    if simulation_mode == "life":
        entries.extend((("H", "Toggle heatmap"), ("A", "Toggle cell ages")))
    if simulation_mode == "langtons_ant":
        entries.append(("Shift + click", "Place the ant at a grid cell"))
    if selected_pattern is not None:
        entries.extend((("R", "Rotate pattern"), ("F / V", "Flip horizontally / vertically")))
    return tuple(entries)


def toggle_help_panel() -> None:
    """Open contextual shortcut help after closing competing modal UI."""
    global dimension_menu_active, mode_menu_active, pattern_menu_active
    global simulation_active
    if "help_panel" in globals() and help_panel.active:
        help_panel.close()
        return
    simulation_active = False
    dimension_menu_active = False
    mode_menu_active = False
    pattern_menu_active = False
    active_workspace().controller.deactivate()
    session_manager.close()
    analysis_panel.close()
    if "export_manager" in globals():
        export_manager.close()
    help_panel.open()


DRAW_HANDLERS = {
    "life": draw_grid,
    "immigration": draw_immigration_grid,
    "brians_brain": draw_brain_grid,
    "langtons_ant": draw_ant_grid,
    "wireworld": draw_wireworld_grid,
    "cyclic_automaton": draw_cyclic_grid,
}


def active_workspace() -> WorkspaceBundle:
    """Return the controller/renderer pair for the selected dimension."""
    return workspace_registry.get(active_dimension)


def active_render_key() -> str:
    """Return the cache identity for the visible dimensional workspace."""
    return active_workspace().renderer.cache_identity


def active_grid_cache_key() -> tuple[Any, ...]:
    """Return the visual state that determines the cached viewport pixels."""
    return active_workspace().renderer.cache_key()


def _two_d_cache_key() -> tuple[Any, ...]:
    """Return visual state used to cache the active 2D mode."""
    viewport = grid_viewport()
    return (
        render_revisions[simulation_mode],
        viewport.size,
        grid_origin(),
        CELL_SIZE,
        current_theme,
        show_grid,
        show_heatmap,
        show_age_numbers,
        show_coordinates,
        show_quadrants,
    )


def draw_active_grid() -> None:
    """Draw or reuse the active workspace through the shared renderer."""
    global render_cache_hits, render_cache_misses
    viewport = grid_viewport()
    renderer = active_workspace().renderer
    render_key = renderer.cache_identity
    cache_key = renderer.cache_key()
    cache_entry = rendered_grid_cache.get(render_key)
    transition_active = renderer.transition_active

    if not transition_active and cache_entry is not None and cache_entry[0] == cache_key:
        screen.blit(cache_entry[1], viewport.topleft)
        render_cache_hits += 1
    else:
        rendered_grid_cache.clear()
        renderer.draw_base()
        render_cache_misses += 1
        changes_every_frame = simulation_active and speed >= 60
        if not transition_active and not changes_every_frame:
            rendered_grid_cache[render_key] = (
                cache_key,
                screen.subsurface(viewport).copy(),
            )

    renderer.draw_dynamic()


def draw_scene() -> None:
    renderer = active_workspace().renderer
    if active_dimension == "3d" and display_backend.is_opengl:
        display_backend.begin_3d_frame(THEMES[current_theme]["background"])
        renderer.draw_base()
        renderer.draw_dynamic()
    else:
        screen.fill(THEMES[current_theme]["background"])
        draw_active_grid()
    renderer.draw_bars()
    draw_workspace_status_controls()
    timeline_panel.draw()
    main_menu.draw(screen, tiny_font)
    renderer.draw_decorations()
    draw_status()
    renderer.draw_modal()
    analysis_panel.draw()
    draw_dimension_menu()
    draw_session_menu()
    export_manager.draw()
    help_panel.draw()


# ---------------------------------------------------------------------------
# UI setup and events
# ---------------------------------------------------------------------------


def add_context_action(menu: Menu, action: str) -> None:
    """Add one mode-specific control described by the mode registry."""
    if action == "change_rule":
        menu.add_button(
            f"Rule: {RULES[current_rule]['name']}",
            cycle_rule,
            accent=MODE_BY_KEY["life"].accent,
        )
    elif action == "toggle_heatmap":
        menu.add_button(
            f"Heatmap: {'On' if show_heatmap else 'Off'}",
            toggle_heatmap,
            accent=(255, 125, 45),
            active=show_heatmap,
        )
    elif action == "toggle_ages":
        menu.add_button(
            f"Age Numbers: {'On' if show_age_numbers else 'Off'}",
            toggle_age_numbers,
            accent=(225, 215, 80),
            active=show_age_numbers,
        )
    elif action == "species_a":
        menu.add_button(
            "Brush: Species A",
            lambda: set_active_species(SPECIES_A),
            accent=immigration_species_base_color(SPECIES_A),
            active=active_species == SPECIES_A,
            tooltip="Select Species A; its identity is also shown in text.",
        )
    elif action == "species_b":
        menu.add_button(
            "Brush: Species B",
            lambda: set_active_species(SPECIES_B),
            accent=immigration_species_base_color(SPECIES_B),
            active=active_species == SPECIES_B,
            tooltip=(
                "Select Species B; Colorblind mode also draws an inner marker."
            ),
        )
    elif action == "rotate_ant":
        menu.add_button(
            "Rotate Ant Clockwise",
            toggle_active_species,
            accent=ant_display_color(ant_state.active),
            tooltip="Rotate the triangular ant; its direction does not rely on color.",
        )
    elif action == "wire_conductor":
        menu.add_button(
            "Brush: Conductor",
            lambda: set_wireworld_brush(CONDUCTOR),
            accent=wireworld_state_color(CONDUCTOR),
            active=wireworld_brush == CONDUCTOR,
        )
    elif action == "wire_head":
        menu.add_button(
            "Brush: Electron Head",
            lambda: set_wireworld_brush(ELECTRON_HEAD),
            accent=wireworld_state_color(ELECTRON_HEAD),
            active=wireworld_brush == ELECTRON_HEAD,
        )
    elif action == "wire_tail":
        menu.add_button(
            "Brush: Electron Tail",
            lambda: set_wireworld_brush(ELECTRON_TAIL),
            accent=wireworld_state_color(ELECTRON_TAIL),
            active=wireworld_brush == ELECTRON_TAIL,
        )
    elif action == "cyclic_brush":
        menu.add_button(
            f"Brush: Color {cyclic_brush} (T)",
            toggle_active_species,
            accent=cyclic_state_color(cyclic_brush),
            active=True,
        )
    elif action == "cyclic_threshold":
        menu.add_button(
            f"Threshold: {cyclic_threshold} (click to cycle)",
            cycle_cyclic_threshold,
            accent=MODE_BY_KEY["cyclic_automaton"].accent,
        )
    else:
        raise ValueError(f"Unknown contextual action: {action}")


def _build_2d_sidebar(menu: Menu) -> None:
    """Populate the controls shared by all 2D simulation modes."""
    definition = get_mode_definition(simulation_mode)
    menu.clear_buttons()
    menu.set_header(f"2D · {definition.name}")
    menu.begin_section(
        "2d_workspace",
        "Workspace",
        tooltip="Global navigation, saved experiments, analysis, export, and help.",
    )
    menu.add_button(
        "Select Dimension (D)",
        activate_dimension_menu,
        accent=DIMENSION_BY_KEY["2d"].accent,
        tooltip="Switch dimensions without clearing either workspace.",
    )
    menu.add_button(
        "Session & Profiles (P)",
        activate_session_menu,
        accent=(80, 190, 145),
        tooltip="Save, load, or reopen a recently used experiment.",
    )
    menu.add_button(
        "Scientific Analysis (I)",
        toggle_analysis_panel,
        accent=(90, 195, 255),
        tooltip="Open live scientific measurements and period detection.",
    )
    menu.add_button(
        "Export Results (X)",
        activate_export_menu,
        accent=(235, 155, 70),
        tooltip="Export the current grid, timeline, metrics, or experiment JSON.",
    )
    menu.add_button(
        "Keyboard Help (F1)",
        toggle_help_panel,
        accent=(180, 150, 245),
        tooltip="Show common and mode-specific shortcuts.",
    )
    menu.begin_section(
        "2d_tools",
        "Mode & Active Tool",
        tooltip="Choose a simulation and configure its active drawing tool.",
    )
    menu.add_button(
        "Select Mode (M)",
        activate_mode_menu,
        accent=definition.accent,
    )
    for action in definition.contextual_actions:
        add_context_action(menu, action)

    menu.begin_section(
        "2d_experiment",
        "Experiment",
        tooltip="Create, clear, select, and save mode-specific patterns.",
    )
    menu.add_button("Clear Grid", clear_grid)
    menu.add_button("Randomize", randomize_grid)
    menu.add_button("Show Patterns", activate_pattern_menu)
    menu.add_button("Save Pattern", save_current_pattern)
    menu.begin_section(
        "2d_view",
        "View",
        expanded=False,
        tooltip="Grid overlays, accessible palettes, and camera controls.",
    )
    menu.add_button(
        f"Grid Lines: {'On' if show_grid else 'Off'}",
        toggle_grid_lines,
        active=show_grid,
    )
    menu.add_button(
        f"Board: {COLS} x {ROWS} (Finite)",
        describe_2d_board,
        tooltip=(
            f"The shared 2D board has {ROWS * COLS:,} logical cells. "
            "Click for details; zoom and window size do not change its state."
        ),
    )
    menu.add_button(
        "Fit Board to Window (Ctrl+0)",
        fit_2d_view,
        tooltip=(
            f"Choose the largest cell size that keeps all {COLS} x {ROWS} "
            "cells visible."
        ),
    )
    menu.add_button(f"Theme: {current_theme.title()}", cycle_theme)
    menu.add_button("Center View", center_view)
    menu.add_button(
        f"Coordinates: {'On' if show_coordinates else 'Off'}",
        toggle_coordinates,
        active=show_coordinates,
    )
    menu.add_button(
        f"Quadrants: {'On' if show_quadrants else 'Off'}",
        toggle_quadrants,
        active=show_quadrants,
    )


def rebuild_context_menu() -> None:
    """Ask the active workspace to rebuild its contextual sidebar."""
    active_workspace().controller.build_sidebar(main_menu)


def setup_menu() -> Menu:
    menu = Menu(
        WINDOW_WIDTH - MENU_WIDTH,
        INFO_BAR_HEIGHT,
        MENU_WIDTH,
        WINDOW_HEIGHT - INFO_BAR_HEIGHT,
        current_theme,
    )
    menu.visible = True
    return menu


def update_window_size(new_width: int, new_height: int) -> None:
    global WINDOW_WIDTH, WINDOW_HEIGHT, screen
    WINDOW_WIDTH = max(760, new_width)
    WINDOW_HEIGHT = max(560, new_height)
    try:
        screen = display_backend.resize(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            active_dimension == "3d",
        )
    except ThreeDimensionalDisplayError as exc:
        screen = display_backend.surface
        set_status(f"Could not resize the 3D renderer: {exc}", 6.0)

    menu_x = WINDOW_WIDTH - MENU_WIDTH
    main_menu.rect.x = menu_x
    main_menu.rect.y = INFO_BAR_HEIGHT
    main_menu.rect.height = WINDOW_HEIGHT - INFO_BAR_HEIGHT
    main_menu.relayout()

    center_view()
    rebuild_context_menu()
    if active_dimension == "2d" and CELL_SIZE > fitted_2d_cell_size():
        set_status(
            "Part of the finite board is outside the viewport; press Ctrl+0 to fit.",
            3.5,
        )


def select_pattern(pattern: dict[str, Any]) -> None:
    global selected_pattern, rotation, flip_h, flip_v, pattern_menu_active
    pattern_mode = pattern.get("mode")
    if pattern_mode is not None and pattern_mode != simulation_mode:
        set_status("That pattern belongs to a different simulation mode.")
        return
    selected_pattern = pattern
    rotation = 0
    flip_h = False
    flip_v = False
    pattern_menu_active = False
    set_status(f"Selected pattern: {pattern['name']}")


def handle_pattern_menu_event(event: pygame.event.Event) -> bool:
    global pattern_menu_active, pattern_scroll

    if not pattern_menu_active:
        return False

    items = pattern_menu_items()
    _, menu_y, _, visible_rows = pattern_menu_geometry()
    max_scroll = max(0, len(items) - visible_rows)

    def activate_item(item: tuple[str, str, str, Any]) -> None:
        kind, key, _, payload = item
        if kind == "category":
            open_pattern_category(key)
        else:
            select_pattern(payload)

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            pattern_menu_active = False
            return True
        if event.key in (pygame.K_BACKSPACE, pygame.K_LEFT):
            if pattern_menu_category is not None:
                return_to_pattern_categories()
            return True
        if pygame.K_1 <= event.key <= pygame.K_9:
            relative_index = event.key - pygame.K_1
            absolute_index = pattern_scroll + relative_index
            if relative_index < visible_rows and absolute_index < len(items):
                activate_item(items[absolute_index])
            return True

    if event.type == pygame.MOUSEWHEEL:
        pattern_scroll = max(0, min(max_scroll, pattern_scroll - event.y))
        return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        mouse_x, mouse_y = event.pos
        menu_x = WINDOW_WIDTH - MENU_WIDTH
        if menu_x <= mouse_x < WINDOW_WIDTH:
            if menu_y <= mouse_y < menu_y + 32:
                if pattern_menu_category is not None:
                    return_to_pattern_categories()
                return True
            relative_y = mouse_y - menu_y - 32
            if relative_y >= 0:
                relative_index = relative_y // PATTERN_ROW_HEIGHT
                absolute_index = pattern_scroll + relative_index
                if relative_index < visible_rows and absolute_index < len(items):
                    activate_item(items[absolute_index])
            return True

    return True


def _two_d_overlay_active() -> bool:
    return mode_menu_active or pattern_menu_active


def _close_2d_overlays() -> None:
    global mode_menu_active, pattern_menu_active, selected_pattern
    mode_menu_active = False
    pattern_menu_active = False
    selected_pattern = None


def _handle_2d_overlay_event(event: pygame.event.Event) -> bool:
    if mode_menu_active:
        return handle_mode_menu_event(event)
    if pattern_menu_active:
        return handle_pattern_menu_event(event)
    return False


def _handle_2d_keydown(event: pygame.event.Event) -> bool:
    global rotation, flip_h, flip_v, selected_pattern

    if event.key == pygame.K_m:
        activate_mode_menu()
    elif event.key == pygame.K_t:
        toggle_active_species()
    elif event.key == pygame.K_r and selected_pattern:
        rotation = (rotation + 90) % 360
    elif event.key == pygame.K_f and selected_pattern:
        flip_h = not flip_h
    elif event.key == pygame.K_v and selected_pattern:
        flip_v = not flip_v
    elif event.key == pygame.K_ESCAPE:
        selected_pattern = None
    elif event.key == pygame.K_h:
        toggle_heatmap()
    elif event.key == pygame.K_a:
        toggle_age_numbers()
    elif pygame.K_1 <= event.key <= pygame.K_9:
        patterns = list(available_patterns().values())
        index = event.key - pygame.K_1
        if index < len(patterns):
            select_pattern(patterns[index])
    else:
        return False
    return True


def handle_keydown(event: pygame.event.Event) -> None:
    """Handle app-wide commands before delegating workspace-specific keys."""
    global simulation_active, single_step_requested, speed

    modifiers = getattr(event, "mod", pygame.key.get_mods())
    question_mark = event.key == pygame.K_SLASH and bool(modifiers & pygame.KMOD_SHIFT)
    if event.key == pygame.K_F1 or question_mark:
        toggle_help_panel()
    elif event.key == pygame.K_s and modifiers & pygame.KMOD_CTRL:
        save_quick_session()
    elif event.key == pygame.K_o and modifiers & pygame.KMOD_CTRL:
        load_quick_session()
    elif (
        event.key in (pygame.K_0, pygame.K_KP0)
        and modifiers & pygame.KMOD_CTRL
    ):
        if active_dimension == "2d":
            fit_2d_view()
        elif active_dimension == "3d":
            three_dimensional_controller.fit_view()
        else:
            set_status("The 1D workspace follows its active space-time diagram.")
    elif event.key == pygame.K_p:
        activate_session_menu()
    elif event.key == pygame.K_i:
        toggle_analysis_panel()
    elif event.key == pygame.K_x:
        toggle_export_menu()
    elif event.key == pygame.K_j:
        timeline_panel.stop()
        request_timeline_generation()
    elif event.key == pygame.K_SPACE:
        toggle_simulation_running()
    elif event.key == pygame.K_d:
        activate_dimension_menu()
    elif event.key == pygame.K_n:
        if simulation_active:
            set_status("Pause the simulation before stepping with N.")
        else:
            single_step_requested = True
    elif event.key == pygame.K_UP:
        speed = min(60, speed + 1)
    elif event.key == pygame.K_DOWN:
        speed = max(1, speed - 1)
    elif event.key == pygame.K_g:
        toggle_grid_lines()
    elif event.key == pygame.K_c:
        center_view()
    elif event.key == pygame.K_LEFTBRACKET:
        zoom(0.80)
    elif event.key == pygame.K_RIGHTBRACKET:
        zoom(1.20)
    else:
        active_workspace().controller.handle_keydown(event)


def _handle_2d_pointer_event(event: pygame.event.Event) -> bool:
    """Handle drawing and panning inside the established 2D workspace."""
    global drawing, drawing_value, drawing_history_pending
    global view_offset_x, view_offset_y

    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            position = mouse_to_grid(event.pos)
            if (
                simulation_mode == "langtons_ant"
                and position is not None
                and pygame.key.get_mods() & pygame.KMOD_SHIFT
            ):
                place_ant(*position)
                return True
            if selected_pattern and position is not None:
                place_selected_pattern(*position)
                return True

            if position is not None:
                drawing = True
                drawing_value = 1
                drawing_history_pending = True
                draw_cell(*position)
        elif event.button == 3:
            position = mouse_to_grid(event.pos)
            if position is not None:
                drawing = True
                drawing_value = 0
                drawing_history_pending = True
                draw_cell(*position)
        return True

    if event.type == pygame.MOUSEBUTTONUP:
        drawing = False
        drawing_history_pending = False
        _sync_2d_history()
        return True

    if event.type == pygame.MOUSEMOTION:
        if drawing:
            position = mouse_to_grid(event.pos)
            if position is not None:
                draw_cell(*position)
        elif event.buttons[1]:
            view_offset_x += event.rel[0]
            view_offset_y += event.rel[1]
        return True
    return False


def handle_event(event: pygame.event.Event) -> bool:
    if event.type == pygame.QUIT:
        return False

    if event.type == pygame.VIDEORESIZE:
        update_window_size(event.w, event.h)
        return True

    if help_panel.active:
        help_panel.handle_event(event)
        return True

    if export_manager.active:
        export_manager.handle_event(event)
        return True

    if session_manager.active:
        handle_session_menu_event(event)
        return True

    if dimension_menu_active:
        handle_dimension_menu_event(event)
        return True

    if analysis_panel.handle_event(event):
        return True

    controller = active_workspace().controller
    if controller.overlay_active:
        controller.handle_overlay_event(event)
        return True

    if (
        event.type == pygame.MOUSEBUTTONDOWN
        and event.button == 1
        and run_pause_rect().collidepoint(event.pos)
    ):
        toggle_simulation_running()
        return True

    if timeline_panel.handle_event(event):
        return True

    if main_menu.handle_event(event):
        return True

    if event.type == pygame.KEYDOWN:
        handle_keydown(event)
        return True

    if event.type == pygame.MOUSEWHEEL:
        zoom(1.10 if event.y > 0 else 0.90)
        return True

    controller.handle_pointer_event(event)
    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _draw_2d_base() -> None:
    DRAW_HANDLERS[simulation_mode]()


def _draw_2d_dynamic() -> None:
    old_clip = screen.get_clip()
    screen.set_clip(grid_viewport())
    draw_pattern_preview()
    screen.set_clip(old_clip)


def _draw_2d_decorations() -> None:
    draw_pattern_menu()
    draw_rule_overlay()


def _draw_2d_modal() -> None:
    draw_mode_menu()


def _two_d_transition_active() -> bool:
    return simulation_mode == "life" and bool(cell_transition.transitions)


def _set_simulation_running(value: bool) -> None:
    global simulation_active
    simulation_active = value


session_manager = SessionMenu(
    SessionMenuServices(
        active_dimension=lambda: active_dimension,
        prepare_open=_prepare_session_menu,
        quick_save=save_quick_session,
        quick_load=load_quick_session,
        named_save=save_named_session,
        save_profile=save_current_experiment_profile,
        load_session=load_saved_session,
        load_profile=load_saved_experiment_profile,
        list_sessions=list_sessions,
        list_profiles=list_profiles,
        recent_experiments=ui_preferences.recent,
        set_status=set_status,
        window_size=lambda: (WINDOW_WIDTH, WINDOW_HEIGHT),
        screen=lambda: screen,
        large_font=lambda: font,
        small_font=lambda: small_font,
        tiny_font=lambda: tiny_font,
    )
)

two_d_timelines = {
    mode: TimelineBinding(
        lambda mode=mode: _snapshot_2d_mode(mode),
        lambda snapshot, mode=mode: _restore_2d_mode(mode, snapshot),
        lambda mode=mode: _generation_for_2d_mode(mode),
        max_frames=TIMELINE_MAX_FRAMES,
    )
    for mode in SIMULATION_MODES
}

elementary_state = ElementaryWorkspaceState()
elementary_services = ElementaryWorkspaceServices(
    viewport=grid_viewport,
    screen=lambda: screen,
    window_size=lambda: (WINDOW_WIDTH, WINDOW_HEIGHT),
    theme_name=lambda: current_theme,
    is_running=lambda: simulation_active,
    speed=lambda: speed,
    show_grid=lambda: show_grid,
    set_running=_set_simulation_running,
    set_status=set_status,
    invalidate=invalidate_render_cache,
    rebuild_sidebar=lambda: rebuild_context_menu(),
    activate_dimension_menu=activate_dimension_menu,
    activate_session_menu=activate_session_menu,
    activate_analysis=toggle_analysis_panel,
    activate_export=activate_export_menu,
    activate_help=toggle_help_panel,
    toggle_grid=toggle_grid_lines,
    cycle_theme=cycle_theme,
    cached_stats=cached_mode_stats,
    render_revision=lambda key: render_revisions[key],
    large_font=lambda: font,
    small_font=lambda: small_font,
    tiny_font=lambda: tiny_font,
    menu_width=MENU_WIDTH,
    info_bar_height=INFO_BAR_HEIGHT,
    stats_height=STATS_HEIGHT,
    grid_top_margin=GRID_TOP_MARGIN,
    timeline_max_frames=TIMELINE_MAX_FRAMES,
    record_analysis=analysis_registry.observe,
    reset_analysis=analysis_registry.reset,
    favorite_rules=lambda: frozenset(ui_preferences.favorite_rules),
    toggle_favorite_rule=ui_preferences.toggle_favorite_rule,
)
elementary_controller = ElementaryWorkspaceController(
    elementary_services,
    elementary_state,
)
elementary_renderer = ElementaryWorkspaceRenderer(
    elementary_controller,
    elementary_services,
)

three_dimensional_state = ThreeDimensionalWorkspaceState()
three_dimensional_services = ThreeDimensionalWorkspaceServices(
    viewport=grid_viewport,
    screen=lambda: screen,
    window_size=lambda: (WINDOW_WIDTH, WINDOW_HEIGHT),
    theme_name=lambda: current_theme,
    is_running=lambda: simulation_active,
    speed=lambda: speed,
    show_grid=lambda: show_grid,
    set_running=_set_simulation_running,
    set_status=set_status,
    invalidate=invalidate_render_cache,
    rebuild_sidebar=lambda: rebuild_context_menu(),
    activate_dimension_menu=activate_dimension_menu,
    activate_session_menu=activate_session_menu,
    activate_analysis=toggle_analysis_panel,
    activate_help=toggle_help_panel,
    toggle_grid=toggle_grid_lines,
    cycle_theme=cycle_theme,
    cached_stats=cached_mode_stats,
    render_revision=lambda key: render_revisions[key],
    large_font=lambda: font,
    small_font=lambda: small_font,
    tiny_font=lambda: tiny_font,
    menu_width=MENU_WIDTH,
    info_bar_height=INFO_BAR_HEIGHT,
    stats_height=STATS_HEIGHT,
    grid_top_margin=GRID_TOP_MARGIN,
    record_analysis=analysis_registry.observe,
    reset_analysis=analysis_registry.reset,
    hardware_3d=lambda: display_backend.is_opengl,
    render_volume=lambda volume, camera, viewport, revision, settings, selected: (
        display_backend.render_volume(
            volume,
            camera,
            viewport,
            revision=revision,
            alive_color=THEMES[current_theme]["cell"],
            accent_color=DIMENSION_BY_KEY["3d"].accent,
            selected=selected,
            settings=settings,
        )
    ),
)
three_dimensional_controller = ThreeDimensionalWorkspaceController(
    three_dimensional_services,
    three_dimensional_state,
)
three_dimensional_renderer = ThreeDimensionalWorkspaceRenderer(
    three_dimensional_controller,
    three_dimensional_services,
)

two_dimensional_controller = TwoDimensionalWorkspaceController(
    TwoDimensionalControllerCallbacks(
        generation=_two_d_generation,
        advance=_apply_2d_generation,
        save_history=_save_2d_history,
        step_back=_step_back_2d,
        step_forward=_step_forward_2d,
        seek_history=_seek_2d_history,
        seek_generation=_seek_2d_generation,
        sync_history=_sync_2d_history,
        history_status=_two_d_history_status,
        reset_history=_reset_2d_history,
        analysis_observation=lambda: _analysis_observation_2d(simulation_mode),
        clear=_clear_2d_grid,
        randomize=_randomize_2d_grid,
        snapshot=_snapshot_2d,
        restore=_restore_2d,
        build_sidebar=_build_2d_sidebar,
        overlay_active=_two_d_overlay_active,
        close_overlays=_close_2d_overlays,
        handle_overlay_event=_handle_2d_overlay_event,
        handle_keydown=_handle_2d_keydown,
        handle_pointer_event=_handle_2d_pointer_event,
        center_view=_center_2d_view,
        zoom=_zoom_2d,
    )
)
two_dimensional_renderer = TwoDimensionalWorkspaceRenderer(
    TwoDimensionalRendererCallbacks(
        render_key=lambda: simulation_mode,
        cache_key=_two_d_cache_key,
        draw_base=_draw_2d_base,
        draw_dynamic=_draw_2d_dynamic,
        draw_bars=_draw_2d_bars,
        draw_decorations=_draw_2d_decorations,
        draw_modal=_draw_2d_modal,
        transition_active=_two_d_transition_active,
    )
)

workspace_registry = WorkspaceRegistry()
workspace_registry.register(
    WorkspaceBundle(two_dimensional_controller, two_dimensional_renderer)
)
workspace_registry.register(WorkspaceBundle(elementary_controller, elementary_renderer))
workspace_registry.register(
    WorkspaceBundle(three_dimensional_controller, three_dimensional_renderer)
)

analysis_registry.reset(elementary_controller.analysis_observation())
analysis_registry.reset(three_dimensional_controller.analysis_observation())
for analysis_mode in SIMULATION_MODES:
    analysis_registry.reset(_analysis_observation_2d(analysis_mode))

analysis_panel = ScientificAnalysisPanel(
    AnalysisPanelServices(
        screen=lambda: screen,
        window_size=lambda: (WINDOW_WIDTH, WINDOW_HEIGHT),
        content_width=lambda: max(1, WINDOW_WIDTH - MENU_WIDTH),
        theme=lambda: THEMES[current_theme],
        large_font=lambda: font,
        small_font=lambda: small_font,
        tiny_font=lambda: tiny_font,
        live_series=active_analysis_series,
        current_generation=lambda: active_workspace().controller.generation,
        comparison_rules=elementary_comparison_rules,
        current_rule=lambda: (
            elementary_controller.state.rule
            if elementary_controller.state.family == FAMILY_ELEMENTARY
            else -1
        ),
        set_status=set_status,
    ),
    comparison_runner,
)

help_panel = ShortcutHelpPanel(
    HelpPanelServices(
        screen=lambda: screen,
        window_size=lambda: (WINDOW_WIDTH, WINDOW_HEIGHT),
        theme=lambda: THEMES[current_theme],
        large_font=lambda: font,
        small_font=lambda: small_font,
        tiny_font=lambda: tiny_font,
        context_title=help_context_title,
        context_entries=help_context_entries,
        pause=lambda: _set_simulation_running(False),
    )
)

timeline_panel = TimelinePanel(
    TimelinePanelServices(
        rect=timeline_rect,
        screen=lambda: screen,
        theme=lambda: THEMES[current_theme],
        tiny_font=lambda: tiny_font,
        status=active_history_status,
        seek=seek_active_history,
        step=step_active_timeline,
        request_generation=request_timeline_generation,
        pause_simulation=lambda: _set_simulation_running(False),
    )
)

export_coordinator = ExperimentExportCoordinator(
    ExperimentExportServices(
        active_dimension=lambda: active_dimension,
        active_mode=lambda: simulation_mode,
        theme_name=lambda: current_theme,
        current_generation=lambda: active_workspace().controller.generation,
        elementary_rule=lambda: elementary_controller.state.rule,
        elementary_boundary=lambda: elementary_controller.state.boundary,
        elementary_snapshot=elementary_controller.snapshot,
        two_d_snapshot=_snapshot_2d_mode,
        three_d_snapshot=three_dimensional_controller.export_snapshot,
        three_d_context=lambda: {
            "mode": three_dimensional_controller.state.mode_key,
            "rule": three_dimensional_controller.state.rule_key,
            "state_count": three_dimensional_controller.state.volume.state_count,
            "shape": three_dimensional_controller.state.volume.shape,
        },
        timeline_snapshots=_active_export_timeline_snapshots,
        analysis_series=active_analysis_series,
        history_status=active_history_status,
        session_document=capture_session_document,
        set_status=set_status,
    ),
    export_runner,
)

export_manager = ExportMenu(
    ExportMenuServices(
        prepare_open=_prepare_export_menu,
        context_label=export_coordinator.context_label,
        export_png=export_coordinator.export_png,
        export_gif=export_coordinator.export_gif,
        export_mp4=export_coordinator.export_mp4,
        export_csv=export_coordinator.export_csv,
        export_json=export_coordinator.export_json,
        set_status=set_status,
        window_size=lambda: (WINDOW_WIDTH, WINDOW_HEIGHT),
        screen=lambda: screen,
        large_font=lambda: font,
        small_font=lambda: small_font,
        tiny_font=lambda: tiny_font,
    ),
    export_runner,
)

main_menu = setup_menu()
if active_dimension == "3d" and not _switch_display_backend("3d"):
    active_dimension = "2d"
rebuild_context_menu()
center_view()
set_status(
    "F1: help · D: dimension · M: mode · I: analysis · Space: run/pause",
    5.0,
)

def run() -> None:
    """Run the interactive application until the window is closed."""
    global single_step_requested
    running = True
    simulation_accumulator = 0.0
    smoke_test = os.environ.get("LIFE_SMOKE_TEST") == "1"

    try:
        while running:
            delta_time = clock.tick(60) / 1000.0
            cell_transition.update(delta_time)

            for current_event in pygame.event.get():
                running = handle_event(current_event)
                if not running:
                    break

            if not running:
                break

            if (
                not session_manager.active
                and not export_manager.active
                and not help_panel.active
                and not dimension_menu_active
                and not active_workspace().controller.overlay_active
            ):
                timeline_panel.update(delta_time)
            else:
                timeline_panel.stop()

            if simulation_active:
                simulation_accumulator += delta_time
                interval = 1.0 / max(1, speed)
                steps_this_frame = 0

                while simulation_accumulator >= interval and steps_this_frame < 5:
                    apply_generation()
                    simulation_accumulator -= interval
                    steps_this_frame += 1
                    if not simulation_active:
                        break
            else:
                simulation_accumulator = 0.0

            if single_step_requested:
                apply_generation()
                single_step_requested = False

            draw_scene()
            display_backend.present()
            if smoke_test:
                running = False

    finally:
        pattern_scan_executor.shutdown(wait=True, cancel_futures=True)
        comparison_runner.shutdown()
        export_runner.shutdown()
        display_backend.close()
        pygame.quit()


if __name__ == "__main__":
    run()
