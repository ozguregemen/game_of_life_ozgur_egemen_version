from __future__ import annotations

import os
import random
import time
from copy import deepcopy
from typing import Any

os.environ["SDL_VIDEO_CENTERED"] = "1"

import pygame

from patterns import get_all_patterns, flip_pattern, rotate_pattern, save_pattern
from rules import RULES, apply_rules_2d, find_patterns
from themes import THEMES, Menu
from visuals import CellTransition, get_enhanced_age_color

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

drawing = False
drawing_value = 1
stroke_history_saved = False

view_offset_x = 0
view_offset_y = 0

show_rule_overlay_until = 0.0
status_message = ""
status_message_until = 0.0

pattern_cache: dict[str, int] = {}
pattern_cache_generation = -1
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
    global stats_dirty
    stats_dirty = True


def save_history() -> None:
    if len(grid_history) >= HISTORY_LIMIT:
        grid_history.pop(0)
    grid_history.append(
        (deepcopy(grid), deepcopy(trail_grid), deepcopy(activity_grid), generation)
    )


def step_back() -> None:
    global grid, trail_grid, activity_grid, generation, simulation_active
    if not grid_history:
        set_status("No earlier generation is available.")
        return

    grid, trail_grid, activity_grid, generation = grid_history.pop()
    simulation_active = False
    cell_transition.transitions.clear()
    mark_stats_dirty()
    set_status(f"Returned to generation {generation}.")


def crop_live_pattern(source: list[list[int]]) -> list[list[int]]:
    live_positions = [
        (row, col)
        for row in range(ROWS)
        for col in range(COLS)
        if source[row][col] > 0
    ]
    if not live_positions:
        return []

    min_row = min(row for row, _ in live_positions)
    max_row = max(row for row, _ in live_positions)
    min_col = min(col for _, col in live_positions)
    max_col = max(col for _, col in live_positions)

    return [
        [
            1 if source[row][col] > 0 else 0
            for col in range(min_col, max_col + 1)
        ]
        for row in range(min_row, max_row + 1)
    ]


def transformed_pattern_data(pattern: dict[str, Any]) -> list[list[int]]:
    data = [list(row) for row in pattern["pattern"]]
    if rotation:
        data = [list(row) for row in rotate_pattern(data, rotation)]
    if flip_h:
        data = [list(row) for row in flip_pattern(data, True)]
    if flip_v:
        data = [list(row) for row in flip_pattern(data, False)]
    return data


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


def set_cell(row: int, col: int, value: int) -> None:
    old_value = grid[row][col]
    if old_value == value:
        return

    grid[row][col] = value
    if (old_value > 0) != (value > 0):
        cell_transition.start_transition(row, col, old_value, value)
    mark_stats_dirty()


def place_selected_pattern(row: int, col: int) -> None:
    global selected_pattern
    if selected_pattern is None:
        return

    data = transformed_pattern_data(selected_pattern)
    save_history()

    changed = False
    for delta_row, pattern_row in enumerate(data):
        for delta_col, value in enumerate(pattern_row):
            target_row = row + delta_row
            target_col = col + delta_col
            if not (0 <= target_row < ROWS and 0 <= target_col < COLS):
                continue
            if value and grid[target_row][target_col] <= 0:
                set_cell(target_row, target_col, 1)
                changed = True

    selected_pattern = None
    if changed:
        set_status("Pattern placed.")
    else:
        set_status("Pattern did not fit or added no new cells.")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def clear_grid() -> None:
    global grid, trail_grid, activity_grid, generation, simulation_active
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
    for button_data in main_menu.buttons:
        button_data["button"].theme = current_theme
    set_status(f"Theme: {current_theme.title()}")


def cycle_rule() -> None:
    global current_rule, show_rule_overlay_until
    rules = list(RULES)
    current_rule = rules[(rules.index(current_rule) + 1) % len(rules)]
    show_rule_overlay_until = time.time() + 2.5
    mark_stats_dirty()


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
    set_status(f"Heatmap {'on' if show_heatmap else 'off'}.")


def toggle_age_numbers() -> None:
    global show_age_numbers
    show_age_numbers = not show_age_numbers
    set_status(f"Age numbers {'on' if show_age_numbers else 'off'}.")


def toggle_coordinates() -> None:
    global show_coordinates
    show_coordinates = not show_coordinates
    set_status(f"Coordinates {'on' if show_coordinates else 'off'}.")


def toggle_quadrants() -> None:
    global show_quadrants
    show_quadrants = not show_quadrants
    set_status(f"Quadrants {'on' if show_quadrants else 'off'}.")


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
    cropped = crop_live_pattern(grid)
    if not cropped:
        set_status("There are no live cells to save.")
        return

    name = get_pattern_name()
    if not name:
        set_status("Pattern save cancelled.")
        return

    try:
        save_pattern(cropped, name)
    except (OSError, ValueError) as exc:
        set_status(f"Could not save pattern: {exc}", 4.0)
        return

    set_status(f"Pattern '{name}' saved.")


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def apply_generation() -> bool:
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


# ---------------------------------------------------------------------------
# Statistics and drawing
# ---------------------------------------------------------------------------


def calculate_stats() -> dict[str, Any]:
    global pattern_cache, pattern_cache_generation, stats_dirty

    alive_cells = sum(
        1 for row in grid for cell in row if cell > 0
    )
    total_cells = ROWS * COLS
    density = 100.0 * alive_cells / total_cells if total_cells else 0.0

    should_scan = stats_dirty and (
        not simulation_active
        or generation % 5 == 0
        or pattern_cache_generation < 0
    )
    if should_scan:
        counts: dict[str, int] = {}
        for match in find_patterns(grid):
            name = match["pattern"]["name"]
            counts[name] = counts.get(name, 0) + 1
        pattern_cache = counts
        pattern_cache_generation = generation
        stats_dirty = False

    return {
        "alive": alive_cells,
        "dead": total_cells - alive_cells,
        "density": density,
        "patterns": pattern_cache,
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

    for row in range(ROWS):
        y = origin_y + row * CELL_SIZE
        if y + CELL_SIZE < viewport.top or y > viewport.bottom:
            continue

        for col in range(COLS):
            x = origin_x + col * CELL_SIZE
            if x + CELL_SIZE < viewport.left or x > viewport.right:
                continue

            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
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
                    overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    overlay.fill(heat_color)
                    screen.blit(overlay, rect.topleft)

            if trail_grid[row][col] > 0 and age <= 0:
                overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                overlay.fill(get_trail_color(trail_grid[row][col]))
                screen.blit(overlay, rect.topleft)

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


def draw_pattern_preview() -> None:
    if selected_pattern is None:
        return

    position = mouse_to_grid(pygame.mouse.get_pos())
    if position is None:
        return

    start_row, start_col = position
    origin_x, origin_y = grid_origin()
    data = transformed_pattern_data(selected_pattern)
    base_color = get_enhanced_age_color(1, current_theme)
    if hasattr(base_color, "r"):
        base_color = (base_color.r, base_color.g, base_color.b)

    for delta_row, pattern_row in enumerate(data):
        for delta_col, value in enumerate(pattern_row):
            if not value:
                continue

            row = start_row + delta_row
            col = start_col + delta_col
            if not (0 <= row < ROWS and 0 <= col < COLS):
                continue

            overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            overlay.fill(tuple(base_color) + (125,))
            screen.blit(
                overlay,
                (origin_x + col * CELL_SIZE, origin_y + row * CELL_SIZE),
            )


def draw_info_bar() -> None:
    theme = THEMES[current_theme]
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    pygame.draw.rect(screen, theme["info_bar"], (0, 0, width, INFO_BAR_HEIGHT))

    state = "Running" if simulation_active else "Paused"
    text = (
        f"{state}   Speed: {speed} gen/s   Generation: {generation}   "
        f"Rule: {RULES[current_rule]['name']}"
    )
    rendered = small_font.render(text, True, theme["text"])
    screen.blit(rendered, (10, 11))


def draw_stats() -> None:
    theme = THEMES[current_theme]
    stats = calculate_stats()
    width = max(1, WINDOW_WIDTH - MENU_WIDTH)
    y = WINDOW_HEIGHT - STATS_HEIGHT
    pygame.draw.rect(screen, theme["stats_bar"], (0, y, width, STATS_HEIGHT))

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

    rendered = tiny_font.render(patterns_text, True, theme["text"])
    screen.blit(rendered, (10, y + 38))


def draw_rule_overlay() -> None:
    if time.time() >= show_rule_overlay_until:
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


def draw_pattern_menu() -> None:
    if not pattern_menu_active:
        return

    patterns = list(get_all_patterns().items())
    menu_x, menu_y, menu_height, visible_rows = pattern_menu_geometry()
    visible = patterns[pattern_scroll : pattern_scroll + visible_rows]
    theme = THEMES[current_theme]

    surface = pygame.Surface((MENU_WIDTH, menu_height))
    surface.fill(theme["menu"])
    pygame.draw.rect(surface, theme["menu_text"], surface.get_rect(), 2)
    surface.blit(
        small_font.render("Choose pattern · Esc closes", True, theme["menu_text"]),
        (10, 8),
    )

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


def draw_scene() -> None:
    screen.fill(THEMES[current_theme]["background"])
    draw_grid()
    draw_info_bar()
    draw_stats()
    main_menu.draw(screen, tiny_font)
    draw_pattern_menu()
    draw_rule_overlay()
    draw_status()


# ---------------------------------------------------------------------------
# UI setup and events
# ---------------------------------------------------------------------------


def setup_menu() -> Menu:
    menu = Menu(
        WINDOW_WIDTH - MENU_WIDTH,
        INFO_BAR_HEIGHT,
        MENU_WIDTH,
        WINDOW_HEIGHT - INFO_BAR_HEIGHT,
        current_theme,
    )
    menu.add_button("Clear Grid", clear_grid)
    menu.add_button("Randomize", randomize_grid)
    menu.add_button("Step Back", step_back)
    menu.add_button("Change Theme", cycle_theme)
    menu.add_button("Change Rule", cycle_rule)
    menu.add_button("Zoom In", lambda: zoom(1.20))
    menu.add_button("Zoom Out", lambda: zoom(0.80))
    menu.add_button("Center View", center_view)
    menu.add_button("Show Patterns", activate_pattern_menu)
    menu.add_button("Save Pattern", save_current_pattern)
    menu.add_button("Toggle Heatmap", toggle_heatmap)
    menu.add_button("Toggle Ages", toggle_age_numbers)
    menu.add_button("Toggle Coordinates", toggle_coordinates)
    menu.add_button("Toggle Quadrants", toggle_quadrants)
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

    for button_data in main_menu.buttons:
        button_data["button"].rect.x = menu_x + 10

    center_view()


def select_pattern(pattern: dict[str, Any]) -> None:
    global selected_pattern, rotation, flip_h, flip_v, pattern_menu_active
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

    patterns = list(get_all_patterns().items())
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
    global simulation_active, single_step_requested, speed, show_grid
    global rotation, flip_h, flip_v, selected_pattern

    if event.key == pygame.K_SPACE:
        simulation_active = not simulation_active
    elif event.key == pygame.K_n:
        single_step_requested = True
    elif event.key == pygame.K_UP:
        speed = min(60, speed + 1)
    elif event.key == pygame.K_DOWN:
        speed = max(1, speed - 1)
    elif event.key == pygame.K_g:
        show_grid = not show_grid
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
        patterns = list(get_all_patterns().values())
        index = event.key - pygame.K_1
        if index < len(patterns):
            select_pattern(patterns[index])


def handle_event(event: pygame.event.Event) -> bool:
    global drawing, drawing_value, stroke_history_saved
    global view_offset_x, view_offset_y

    if event.type == pygame.QUIT:
        return False

    if pattern_menu_active:
        handle_pattern_menu_event(event)
        return True

    if main_menu.handle_event(event):
        return True

    if event.type == pygame.VIDEORESIZE:
        update_window_size(event.w, event.h)
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
            if selected_pattern and position is not None:
                place_selected_pattern(*position)
                return True

            if position is not None:
                drawing = True
                drawing_value = 1
                stroke_history_saved = False
                save_history()
                stroke_history_saved = True
                set_cell(*position, drawing_value)
        elif event.button == 3:
            position = mouse_to_grid(event.pos)
            if position is not None:
                drawing = True
                drawing_value = 0
                stroke_history_saved = False
                save_history()
                stroke_history_saved = True
                set_cell(*position, drawing_value)
        return True

    if event.type == pygame.MOUSEBUTTONUP:
        drawing = False
        stroke_history_saved = False
        return True

    if event.type == pygame.MOUSEMOTION:
        if drawing:
            position = mouse_to_grid(event.pos)
            if position is not None:
                set_cell(*position, drawing_value)
        elif event.buttons[1]:
            view_offset_x += event.rel[0]
            view_offset_y += event.rel[1]
        return True

    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


main_menu = setup_menu()
center_view()
set_status("Space: run/pause · N: step · Left/Right mouse: draw/erase", 5.0)

running = True
simulation_accumulator = 0.0

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

finally:
    pygame.quit()
