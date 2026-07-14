from __future__ import annotations

import os
import random
import time
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from typing import Any

os.environ["SDL_VIDEO_CENTERED"] = "1"

import pygame

from brians_brain import (
    DYING,
    FIRING,
    BrainGrid,
    apply_brain_rules,
    brain_stats,
    make_brain_grid,
    randomize_brain_grid,
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
from patterns import get_patterns_for_mode, flip_pattern, rotate_pattern, save_pattern
from rules import RULES, apply_rules_2d, find_patterns
from themes import THEMES, Menu
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

# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 720
MENU_WIDTH = 260
INFO_BAR_HEIGHT = 42
STATS_HEIGHT = 68
GRID_TOP_MARGIN = 8

ROWS = 48
COLS = 72
CELL_SIZE = 12
MIN_CELL_SIZE = 5
MAX_CELL_SIZE = 40

HISTORY_LIMIT = 50
TRAIL_MAX = 10
PATTERN_ROW_HEIGHT = 30

BLACK = (0, 0, 0)

pygame.init()
pygame.display.set_caption("Özgür Egemen's Cellular Automata Lab")
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
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
grid_history: list[tuple[list[list[int]], list[list[int]], list[list[float]], int]] = []

immigration_grid: ImmigrationGrid = make_immigration_grid(ROWS, COLS)
immigration_history: list[tuple[ImmigrationGrid, int]] = []
immigration_generation = 0
active_species = SPECIES_A
immigration_rng = random.Random()

brain_grid: BrainGrid = make_brain_grid(ROWS, COLS)
brain_history: list[tuple[BrainGrid, int]] = []
brain_generation = 0
brain_rng = random.Random()

ant_grid: AntGrid = make_ant_grid(ROWS, COLS)
ant_state = centered_ant(ROWS, COLS)
ant_history: list[tuple[AntGrid, AntState, int, AntStepReport]] = []
ant_generation = 0
ant_last_report = AntStepReport()
ant_rng = random.Random()

wireworld_grid: WireworldGrid = make_wireworld_grid(ROWS, COLS)
wireworld_history: list[tuple[WireworldGrid, int]] = []
wireworld_generation = 0
wireworld_brush = CONDUCTOR
wireworld_rng = random.Random()
WIRE_BRUSH_STATES = (CONDUCTOR, ELECTRON_HEAD, ELECTRON_TAIL)

SIMULATION_MODES = MODE_KEYS
requested_start_mode = os.environ.get("LIFE_START_MODE", "life")
simulation_mode = (
    requested_start_mode if requested_start_mode in SIMULATION_MODES else "life"
)
current_rule = "conway"
current_theme = "classic"
simulation_active = False
single_step_requested = False
speed = 10
generation = 0

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
mode_menu_active = False

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

cell_transition = CellTransition(duration=0.18)
main_menu: Menu

# ---------------------------------------------------------------------------
# Geometry and state helpers
# ---------------------------------------------------------------------------


def grid_viewport() -> pygame.Rect:
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    height = max(1, WINDOW_HEIGHT - INFO_BAR_HEIGHT - STATS_HEIGHT)
    return pygame.Rect(0, INFO_BAR_HEIGHT, width, height)


def grid_origin() -> tuple[int, int]:
    viewport = grid_viewport()
    return (
        viewport.x + view_offset_x,
        viewport.y + GRID_TOP_MARGIN + view_offset_y,
    )


def center_view() -> None:
    global view_offset_x, view_offset_y
    viewport = grid_viewport()
    grid_width = COLS * CELL_SIZE
    grid_height = ROWS * CELL_SIZE
    view_offset_x = (viewport.width - grid_width) // 2
    view_offset_y = (viewport.height - GRID_TOP_MARGIN - grid_height) // 2


def set_status(message: str, duration: float = 2.0) -> None:
    global status_message, status_message_until
    status_message = message
    status_message_until = time.time() + duration


def mark_stats_dirty() -> None:
    global stats_dirty, grid_revision
    stats_dirty = True
    grid_revision += 1


def save_history() -> None:
    if simulation_mode == "wireworld":
        if len(wireworld_history) >= HISTORY_LIMIT:
            wireworld_history.pop(0)
        wireworld_history.append((deepcopy(wireworld_grid), wireworld_generation))
        return

    if simulation_mode == "langtons_ant":
        if len(ant_history) >= HISTORY_LIMIT:
            ant_history.pop(0)
        ant_history.append(
            (deepcopy(ant_grid), ant_state, ant_generation, ant_last_report)
        )
        return

    if simulation_mode == "brians_brain":
        if len(brain_history) >= HISTORY_LIMIT:
            brain_history.pop(0)
        brain_history.append((deepcopy(brain_grid), brain_generation))
        return

    if simulation_mode == "immigration":
        if len(immigration_history) >= HISTORY_LIMIT:
            immigration_history.pop(0)
        immigration_history.append(
            (deepcopy(immigration_grid), immigration_generation)
        )
        return

    if len(grid_history) >= HISTORY_LIMIT:
        grid_history.pop(0)
    grid_history.append(
        (deepcopy(grid), deepcopy(trail_grid), deepcopy(activity_grid), generation)
    )


def step_back() -> None:
    global grid, trail_grid, activity_grid, generation, simulation_active
    global immigration_grid, immigration_generation
    global brain_grid, brain_generation
    global ant_grid, ant_state, ant_generation, ant_last_report
    global wireworld_grid, wireworld_generation
    if simulation_mode == "wireworld":
        if not wireworld_history:
            set_status("No earlier Wireworld generation is available.")
            return
        wireworld_grid, wireworld_generation = wireworld_history.pop()
        simulation_active = False
        set_status(f"Returned to Wireworld generation {wireworld_generation}.")
        return

    if simulation_mode == "langtons_ant":
        if not ant_history:
            set_status("No earlier Langton's Ant step is available.")
            return
        ant_grid, ant_state, ant_generation, ant_last_report = ant_history.pop()
        simulation_active = False
        set_status(f"Returned to Langton step {ant_generation}.")
        return

    if simulation_mode == "brians_brain":
        if not brain_history:
            set_status("No earlier Brian's Brain generation is available.")
            return
        brain_grid, brain_generation = brain_history.pop()
        simulation_active = False
        set_status(f"Returned to Brian's Brain generation {brain_generation}.")
        return

    if simulation_mode == "immigration":
        if not immigration_history:
            set_status("No earlier Immigration generation is available.")
            return
        immigration_grid, immigration_generation = immigration_history.pop()
        simulation_active = False
        set_status(f"Returned to Immigration generation {immigration_generation}.")
        return

    if not grid_history:
        set_status("No earlier generation is available.")
        return

    grid, trail_grid, activity_grid, generation = grid_history.pop()
    simulation_active = False
    cell_transition.transitions.clear()
    mark_stats_dirty()
    set_status(f"Returned to generation {generation}.")


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
    if simulation_mode == "wireworld":
        target_value = wireworld_brush if drawing_value else WIRE_EMPTY
        if wireworld_grid[row][col] == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        wireworld_grid[row][col] = target_value
        return

    if simulation_mode == "langtons_ant":
        target_value = ANT_BLACK if drawing_value else 0
        if ant_grid[row][col] == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        ant_grid[row][col] = target_value
        return

    if simulation_mode == "brians_brain":
        target_value = FIRING if drawing_value else 0
        if brain_grid[row][col] == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        brain_grid[row][col] = target_value
        return

    if simulation_mode == "immigration":
        target_value = active_species if drawing_value else 0
        if species_of(immigration_grid[row][col]) == target_value:
            return
        if drawing_history_pending:
            save_history()
            drawing_history_pending = False
        immigration_grid[row][col] = target_value
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
    if simulation_mode == "immigration":
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
            if not value:
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

    selected_pattern = None
    if changes or ant_changed:
        set_status("Pattern placed.")
    else:
        set_status("Pattern made no changes.")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def clear_grid() -> None:
    global grid, trail_grid, activity_grid, generation, simulation_active
    global immigration_grid, immigration_generation
    global brain_grid, brain_generation
    global ant_grid, ant_state, ant_generation, ant_last_report
    global wireworld_grid, wireworld_generation
    if simulation_mode == "wireworld":
        save_history()
        wireworld_grid = make_wireworld_grid(ROWS, COLS)
        wireworld_generation = 0
        simulation_active = False
        set_status("Wireworld grid cleared.")
        return

    if simulation_mode == "langtons_ant":
        save_history()
        ant_grid = make_ant_grid(ROWS, COLS)
        ant_state = centered_ant(ROWS, COLS)
        ant_generation = 0
        ant_last_report = AntStepReport()
        simulation_active = False
        set_status("Langton's Ant board reset.")
        return

    if simulation_mode == "brians_brain":
        save_history()
        brain_grid = make_brain_grid(ROWS, COLS)
        brain_generation = 0
        simulation_active = False
        set_status("Brian's Brain grid cleared.")
        return

    if simulation_mode == "immigration":
        save_history()
        immigration_grid = make_immigration_grid(ROWS, COLS)
        immigration_generation = 0
        simulation_active = False
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


def randomize_grid(density: float = 0.20) -> None:
    global grid, trail_grid, activity_grid, generation, simulation_active
    global immigration_grid, immigration_generation
    global brain_grid, brain_generation
    global ant_grid, ant_state, ant_generation, ant_last_report
    global wireworld_grid, wireworld_generation
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
        else:
            message = "Langton's Ant uses right-on-white and left-on-black."
        set_status(message)
        return
    rules = list(RULES)
    current_rule = rules[(rules.index(current_rule) + 1) % len(rules)]
    show_rule_overlay_until = time.time() + 2.5
    mark_stats_dirty()
    rebuild_context_menu()


def set_simulation_mode(mode: str) -> None:
    """Select a registered mode and reset transient interface state."""
    global simulation_mode, simulation_active, single_step_requested
    global selected_pattern, pattern_menu_active, mode_menu_active, drawing
    definition = get_mode_definition(mode)
    simulation_mode = mode
    simulation_active = False
    single_step_requested = False
    selected_pattern = None
    pattern_menu_active = False
    mode_menu_active = False
    drawing = False
    cell_transition.transitions.clear()
    if "main_menu" in globals():
        rebuild_context_menu()
    set_status(f"{definition.name}: {definition.status_hint}", 4.0)


def toggle_simulation_mode() -> None:
    """Cycle modes programmatically; the interactive UI uses the chooser."""
    current_index = SIMULATION_MODES.index(simulation_mode)
    set_simulation_mode(SIMULATION_MODES[(current_index + 1) % len(SIMULATION_MODES)])


def activate_mode_menu() -> None:
    """Open the mode chooser and pause the simulation behind it."""
    global mode_menu_active, pattern_menu_active, simulation_active
    mode_menu_active = True
    pattern_menu_active = False
    simulation_active = False


def toggle_active_species() -> None:
    """Change the mode-specific drawing state or rotate the Langton ant."""
    global active_species, ant_state, wireworld_brush
    if simulation_mode == "wireworld":
        index = WIRE_BRUSH_STATES.index(wireworld_brush)
        wireworld_brush = WIRE_BRUSH_STATES[(index + 1) % len(WIRE_BRUSH_STATES)]
        if "main_menu" in globals():
            rebuild_context_menu()
        set_status(f"Wireworld brush: {WIRE_STATE_NAMES[wireworld_brush]}")
        return
    if simulation_mode == "langtons_ant":
        ant_state = rotate_ant_clockwise(ant_state)
        direction = DIRECTION_NAMES[ant_state.direction]
        set_status(f"Ant direction: {direction}")
        return
    if simulation_mode != "immigration":
        set_status("This mode has no alternate drawing state.")
        return
    active_species = SPECIES_B if active_species == SPECIES_A else SPECIES_A
    if "main_menu" in globals():
        rebuild_context_menu()
    label = "A (blue)" if active_species == SPECIES_A else "B (orange)"
    set_status(f"Active species: {label}")


def set_active_species(species: int) -> None:
    """Select an Immigration brush directly from the contextual menu."""
    global active_species
    if simulation_mode != "immigration" or species not in (SPECIES_A, SPECIES_B):
        return
    active_species = species
    rebuild_context_menu()
    label = "A (blue)" if species == SPECIES_A else "B (orange)"
    set_status(f"Active species: {label}")


def set_wireworld_brush(value: int) -> None:
    """Select a Wireworld drawing state directly from the contextual menu."""
    global wireworld_brush
    if simulation_mode != "wireworld" or value not in WIRE_BRUSH_STATES:
        return
    wireworld_brush = value
    rebuild_context_menu()
    set_status(f"Wireworld brush: {WIRE_STATE_NAMES[value]}")


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
    set_status(f"Ant moved to ({row}, {col}).")


def zoom(factor: float) -> None:
    global CELL_SIZE
    new_size = int(round(CELL_SIZE * factor))
    new_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, new_size))
    if new_size == CELL_SIZE:
        return
    CELL_SIZE = new_size
    center_view()
    set_status(f"Cell size: {CELL_SIZE}px")


def activate_pattern_menu() -> None:
    global pattern_menu_active, pattern_scroll
    pattern_menu_active = True
    pattern_scroll = 0


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


def get_pattern_name() -> str | None:
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
                else:
                    text += event.unicode

        draw_scene()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        prompt = font.render("Pattern name", True, (255, 255, 255))
        screen.blit(prompt, (input_box.x, input_box.y - 34))
        pygame.draw.rect(screen, (20, 25, 35), input_box)
        pygame.draw.rect(screen, (70, 170, 255), input_box, 2)

        text_surface = font.render(text, True, (255, 255, 255))
        screen.blit(text_surface, (input_box.x + 8, input_box.y + 8))
        pygame.display.flip()
        clock.tick(60)

    return None


def save_current_pattern() -> None:
    if simulation_mode == "immigration":
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
    return True


GENERATION_HANDLERS = {
    "life": apply_life_generation,
    "immigration": apply_immigration_generation,
    "brians_brain": apply_brain_generation,
    "langtons_ant": apply_ant_generation,
    "wireworld": apply_wireworld_generation,
}


def apply_generation() -> bool:
    """Advance the selected simulation mode."""
    return GENERATION_HANDLERS[simulation_mode]()


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


def calculate_stats() -> dict[str, Any]:
    global recognized_pattern_cache, pattern_scan_generation
    global pattern_scan_revision, pattern_scan_future, stats_dirty

    alive_cells = sum(
        1 for row in grid for cell in row if cell > 0
    )
    total_cells = ROWS * COLS
    density = 100.0 * alive_cells / total_cells if total_cells else 0.0

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
        "alive": alive_cells,
        "dead": total_cells - alive_cells,
        "density": density,
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

    draw_pattern_preview()
    screen.set_clip(old_clip)


def immigration_species_color(value: int) -> tuple[int, int, int]:
    """Return a theme-aware color for an Immigration cell."""
    age = cell_age(value)
    brightness = min(1.0, 0.62 + age * 0.025)
    if species_of(value) == SPECIES_A:
        base = (40, 180, 255)
    else:
        base = (255, 135, 35)
    return tuple(int(channel * brightness) for channel in base)


def brain_state_color(value: int) -> tuple[int, int, int]:
    """Return the conventional bright/dim colors for Brian's Brain."""
    if value == FIRING:
        return (80, 235, 255)
    return (75, 55, 155)


def wireworld_state_color(value: int) -> tuple[int, int, int]:
    """Return conventional colors for the four Wireworld states."""
    colors = {
        WIRE_EMPTY: (10, 12, 18),
        ELECTRON_HEAD: (65, 170, 255),
        ELECTRON_TAIL: (235, 65, 55),
        CONDUCTOR: (245, 190, 35),
    }
    return colors[value]


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

    draw_pattern_preview()
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

    draw_pattern_preview()
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

    draw_pattern_preview()
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
            (175, 40, 45),
            (center_x, origin_y),
            (center_x, origin_y + ROWS * CELL_SIZE),
            2,
        )
        pygame.draw.line(
            screen,
            (175, 40, 45),
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
        ant_color = (230, 35, 45) if ant_state.active else (125, 35, 40)
        pygame.draw.polygon(
            screen,
            ant_color,
            ant_triangle_points(ant_rect, ant_state.direction),
        )

    draw_pattern_preview()
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
            if not value:
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

    if ant is not None:
        ant_rect = pygame.Rect(
            ant["col"] * CELL_SIZE,
            ant["row"] * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )
        pygame.draw.polygon(
            preview,
            (230, 35, 45, 190) if fits else (255, 45, 45, 190),
            ant_triangle_points(ant_rect, ant["direction"]),
        )

    screen.blit(
        preview,
        (origin_x + start_col * CELL_SIZE, origin_y + start_row * CELL_SIZE),
    )


def draw_info_bar() -> None:
    theme = THEMES[current_theme]
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    pygame.draw.rect(screen, theme["info_bar"], (0, 0, width, INFO_BAR_HEIGHT))

    state = "Running" if simulation_active else "Paused"
    if simulation_mode == "wireworld":
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
        species_label = "A (blue)" if active_species == SPECIES_A else "B (orange)"
        text = (
            f"{state}   Mode: Immigration Game   Speed: {speed} gen/s   "
            f"Generation: {immigration_generation}   Brush: {species_label}"
        )
    else:
        text = (
            f"{state}   Mode: Life-like   Speed: {speed} gen/s   "
            f"Generation: {generation}   Rule: {RULES[current_rule]['name']}"
        )
    rendered = small_font.render(text, True, theme["text"])
    screen.blit(rendered, (10, 11))


def draw_stats() -> None:
    theme = THEMES[current_theme]
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    y = WINDOW_HEIGHT - STATS_HEIGHT
    pygame.draw.rect(screen, theme["stats_bar"], (0, y, width, STATS_HEIGHT))

    if simulation_mode == "wireworld":
        stats = wireworld_stats(wireworld_grid)
        first_line = (
            f"Heads: {stats['heads']}   Tails: {stats['tails']}   "
            f"Conductors: {stats['conductors']}   Empty: {stats['empty']}   "
            f"Density: {stats['density']:.2f}%   History: "
            f"{len(wireworld_history)}/{HISTORY_LIMIT}"
        )
        second_line = (
            "Head -> Tail   ·   Tail -> Conductor   ·   "
            "Conductor + exactly 1 or 2 neighboring heads -> Head"
        )
        screen.blit(small_font.render(first_line, True, theme["text"]), (10, y + 8))
        screen.blit(tiny_font.render(second_line, True, theme["text"]), (10, y + 38))
        return

    if simulation_mode == "langtons_ant":
        stats = ant_stats(ant_grid)
        first_line = (
            f"Black: {stats['black']}   White: {stats['white']}   "
            f"Black density: {stats['black_density']:.2f}%   "
            f"Ant: ({ant_state.row}, {ant_state.col})   History: "
            f"{len(ant_history)}/{HISTORY_LIMIT}"
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
        stats = brain_stats(brain_grid)
        first_line = (
            f"Active: {stats['active']}   Firing: {stats['firing']}   "
            f"Dying: {stats['dying']}   Off: {stats['off']}   "
            f"Density: {stats['density']:.2f}%   History: "
            f"{len(brain_history)}/{HISTORY_LIMIT}"
        )
        second_line = (
            "Off + exactly 2 firing neighbors → Firing   ·   "
            "Firing → Dying   ·   Dying → Off"
        )
        screen.blit(small_font.render(first_line, True, theme["text"]), (10, y + 8))
        screen.blit(tiny_font.render(second_line, True, theme["text"]), (10, y + 38))
        return

    if simulation_mode == "immigration":
        stats = immigration_stats(immigration_grid)
        first_line = (
            f"Population: {stats['population']}   Species A: {stats['species_a']}   "
            f"Species B: {stats['species_b']}   Density: {stats['density']:.2f}%   "
            f"History: {len(immigration_history)}/{HISTORY_LIMIT}"
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
        f"Density: {stats['density']:.2f}%   History: {len(grid_history)}/{HISTORY_LIMIT}"
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


def draw_rule_overlay() -> None:
    if simulation_mode != "life" or time.time() >= show_rule_overlay_until:
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


def draw_pattern_menu() -> None:
    if not pattern_menu_active:
        return

    patterns = list(available_patterns().items())
    menu_x, menu_y, menu_height, visible_rows = pattern_menu_geometry()
    visible = patterns[pattern_scroll : pattern_scroll + visible_rows]
    theme = THEMES[current_theme]

    surface = pygame.Surface((MENU_WIDTH, menu_height))
    surface.fill(theme["menu"])
    pygame.draw.rect(surface, theme["menu_text"], surface.get_rect(), 2)
    mode_name = MODE_BY_KEY[simulation_mode].name
    heading = tiny_font.render(
        f"{mode_name} Patterns · Esc closes",
        True,
        theme["menu_text"],
    )
    surface.blit(heading, (10, 8))

    mouse_x, mouse_y = pygame.mouse.get_pos()
    for index, (_, pattern) in enumerate(visible):
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
        label = f"{number}. {pattern['name']}" if number <= 9 else pattern["name"]
        surface.blit(
            tiny_font.render(label, True, theme["menu_text"]),
            (10, row_y + 8),
        )

    footer = f"{pattern_scroll + 1}-{pattern_scroll + len(visible)} / {len(patterns)}"
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

    footer = "Click a card or press 1-5   ·   Esc closes"
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


def draw_status() -> None:
    if not status_message or time.time() >= status_message_until:
        return

    text_surface = small_font.render(status_message, True, (255, 255, 255))
    box = text_surface.get_rect()
    box.inflate_ip(20, 14)
    box.centerx = max(1, WINDOW_WIDTH - MENU_WIDTH) // 2
    box.bottom = WINDOW_HEIGHT - STATS_HEIGHT - 10

    overlay = pygame.Surface(box.size, pygame.SRCALPHA)
    overlay.fill((20, 25, 35, 220))
    screen.blit(overlay, box)
    screen.blit(text_surface, text_surface.get_rect(center=box.center))


DRAW_HANDLERS = {
    "life": draw_grid,
    "immigration": draw_immigration_grid,
    "brians_brain": draw_brain_grid,
    "langtons_ant": draw_ant_grid,
    "wireworld": draw_wireworld_grid,
}


def draw_scene() -> None:
    screen.fill(THEMES[current_theme]["background"])
    DRAW_HANDLERS[simulation_mode]()
    draw_info_bar()
    draw_stats()
    main_menu.draw(screen, tiny_font)
    draw_pattern_menu()
    draw_rule_overlay()
    draw_status()
    draw_mode_menu()


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
            accent=(40, 180, 255),
            active=active_species == SPECIES_A,
        )
    elif action == "species_b":
        menu.add_button(
            "Brush: Species B",
            lambda: set_active_species(SPECIES_B),
            accent=(255, 135, 35),
            active=active_species == SPECIES_B,
        )
    elif action == "rotate_ant":
        menu.add_button(
            "Rotate Ant Clockwise",
            toggle_active_species,
            accent=(230, 35, 45),
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
    else:
        raise ValueError(f"Unknown contextual action: {action}")


def rebuild_context_menu() -> None:
    """Build the sidebar from the selected mode's registered capabilities."""
    definition = get_mode_definition(simulation_mode)
    main_menu.clear_buttons()
    main_menu.set_header(f"{definition.name} Controls")
    main_menu.add_button(
        "Select Mode (M)",
        activate_mode_menu,
        accent=definition.accent,
    )
    for action in definition.contextual_actions:
        add_context_action(main_menu, action)

    main_menu.add_button("Clear Grid", clear_grid)
    main_menu.add_button("Randomize", randomize_grid)
    main_menu.add_button("Step Back", step_back)
    main_menu.add_button(
        f"Grid Lines: {'On' if show_grid else 'Off'}",
        toggle_grid_lines,
        active=show_grid,
    )
    main_menu.add_button("Show Patterns", activate_pattern_menu)
    main_menu.add_button("Save Pattern", save_current_pattern)
    main_menu.add_button(f"Theme: {current_theme.title()}", cycle_theme)
    main_menu.add_button("Center View", center_view)
    main_menu.add_button(
        f"Coordinates: {'On' if show_coordinates else 'Off'}",
        toggle_coordinates,
        active=show_coordinates,
    )
    main_menu.add_button(
        f"Quadrants: {'On' if show_quadrants else 'Off'}",
        toggle_quadrants,
        active=show_quadrants,
    )


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
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)

    menu_x = WINDOW_WIDTH - MENU_WIDTH
    main_menu.rect.x = menu_x
    main_menu.rect.y = INFO_BAR_HEIGHT
    main_menu.rect.height = WINDOW_HEIGHT - INFO_BAR_HEIGHT
    main_menu.relayout()

    center_view()


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

    patterns = list(available_patterns().items())
    _, menu_y, _, visible_rows = pattern_menu_geometry()
    max_scroll = max(0, len(patterns) - visible_rows)

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            pattern_menu_active = False
            return True
        if pygame.K_1 <= event.key <= pygame.K_9:
            relative_index = event.key - pygame.K_1
            absolute_index = pattern_scroll + relative_index
            if relative_index < visible_rows and absolute_index < len(patterns):
                select_pattern(patterns[absolute_index][1])
            return True

    if event.type == pygame.MOUSEWHEEL:
        pattern_scroll = max(0, min(max_scroll, pattern_scroll - event.y))
        return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        mouse_x, mouse_y = event.pos
        menu_x = WINDOW_WIDTH - MENU_WIDTH
        if menu_x <= mouse_x < WINDOW_WIDTH:
            relative_y = mouse_y - menu_y - 32
            if relative_y >= 0:
                relative_index = relative_y // PATTERN_ROW_HEIGHT
                absolute_index = pattern_scroll + relative_index
                if relative_index < visible_rows and absolute_index < len(patterns):
                    select_pattern(patterns[absolute_index][1])
            return True

    return True


def handle_keydown(event: pygame.event.Event) -> None:
    global simulation_active, single_step_requested, speed
    global rotation, flip_h, flip_v, selected_pattern

    if event.key == pygame.K_SPACE:
        simulation_active = not simulation_active
    elif event.key == pygame.K_m:
        activate_mode_menu()
    elif event.key == pygame.K_t:
        toggle_active_species()
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
    elif event.key == pygame.K_c:
        center_view()
    elif event.key == pygame.K_LEFTBRACKET:
        zoom(0.80)
    elif event.key == pygame.K_RIGHTBRACKET:
        zoom(1.20)
    elif pygame.K_1 <= event.key <= pygame.K_9:
        patterns = list(available_patterns().values())
        index = event.key - pygame.K_1
        if index < len(patterns):
            select_pattern(patterns[index])


def handle_event(event: pygame.event.Event) -> bool:
    global drawing, drawing_value, drawing_history_pending
    global view_offset_x, view_offset_y

    if event.type == pygame.QUIT:
        return False

    if event.type == pygame.VIDEORESIZE:
        update_window_size(event.w, event.h)
        return True

    if mode_menu_active:
        handle_mode_menu_event(event)
        return True

    if pattern_menu_active:
        handle_pattern_menu_event(event)
        return True

    if main_menu.handle_event(event):
        return True

    if event.type == pygame.KEYDOWN:
        handle_keydown(event)
        return True

    if event.type == pygame.MOUSEWHEEL:
        zoom(1.10 if event.y > 0 else 0.90)
        return True

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

    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


main_menu = setup_menu()
rebuild_context_menu()
center_view()
set_status("M: choose mode · Space: run/pause · Mouse: draw · Wheel: zoom", 5.0)

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
            pygame.display.flip()
            if smoke_test:
                running = False

    finally:
        pattern_scan_executor.shutdown(wait=True, cancel_futures=True)
        pygame.quit()


if __name__ == "__main__":
    run()
