# BACKUP: The entire current file will be copied to life2d_backup.py before making 3D changes.
import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

import pygame
import random
import numpy as np
from patterns import PATTERNS, save_pattern, load_pattern, get_all_patterns, rotate_pattern, flip_pattern, delete_pattern
from themes import THEMES, get_age_color, Button, Menu
from rules import RULES, apply_rules_2d, recognize_pattern, find_patterns, predict_evolution
from visuals import Minimap, CellTransition, GridOverlay, get_enhanced_age_color
import time
import copy

# Grid ayarları
CELL_SIZE = 18  # Slightly smaller cells
MIN_CELL_SIZE = 8  # Minimum cell size for usability
ROWS, COLS = 48, 48  # Fewer rows/cols to fit window
INFO_BAR_HEIGHT = 40
STATS_HEIGHT = 60
MENU_WIDTH = 250
MINIMAP_SIZE = 120
WIDTH = COLS * CELL_SIZE
GRID_TOP_MARGIN = 10
GRID_BOTTOM_MARGIN = 40  # Match stats bar height for clear separation
HEIGHT = ROWS * CELL_SIZE + GRID_TOP_MARGIN + GRID_BOTTOM_MARGIN

# Set window size to fit within 1200x700
WINDOW_WIDTH = WIDTH + MENU_WIDTH
WINDOW_HEIGHT = HEIGHT + INFO_BAR_HEIGHT + STATS_HEIGHT
if WINDOW_WIDTH > 1200:
    WINDOW_WIDTH = 1200
if WINDOW_HEIGHT > 700:
    WINDOW_HEIGHT = 700

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

TRAIL_MAX = 10  # Maximum trail age for dead cell trails

pygame.init()
font = pygame.font.SysFont("Arial", 24, bold=True)
small_font = pygame.font.SysFont("Arial", 16)
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Conway's Game of Life")
clock = pygame.time.Clock()

# Game state
DEPTH = 16  # Number of layers in the 3rd dimension
current_slice = DEPTH // 2  # Start in the middle slice

grid = [[[0 for _ in range(DEPTH)] for _ in range(COLS)] for _ in range(ROWS)]
grid_history = []
current_rule = "conway"
current_theme = "classic"
zoom_level = 1
offset_x = 0
offset_y = 0
selected_pattern = None
rotation = 0
flip_h = False
flip_v = False
çizim_modu = False
çizim_tipi = 1
simulasyon_aktif = False
adim_modu = False
hiz = 10
nesil = 0
grid_goster = True
pattern_menu_active = False

# Visual enhancements
MINIMAP_X = WIDTH + (MENU_WIDTH - MINIMAP_SIZE) // 2
MINIMAP_Y = INFO_BAR_HEIGHT + HEIGHT - MINIMAP_SIZE - 10
minimap = Minimap(MINIMAP_X, MINIMAP_Y, MINIMAP_SIZE, MINIMAP_SIZE, (ROWS, COLS), current_theme)
cell_transition = CellTransition()
grid_overlay = GridOverlay(CELL_SIZE, current_theme)
grid_overlay.show_coordinates = False

# Add a toggle for showing cell age numbers
show_age_numbers = False

# Add a toggle for the heatmap overlay
show_heatmap = False

# Update trail and activity grids to 3D
trail_grid = [[[0 for _ in range(DEPTH)] for _ in range(COLS)] for _ in range(ROWS)]
activity_grid = [[[0 for _ in range(DEPTH)] for _ in range(COLS)] for _ in range(ROWS)]

# Add a variable to track rule overlay display time
show_rule_overlay_until = 0

# Add a function to get trail color (move this above grid_ciz)
def get_trail_color(trail_age):
    if trail_age == 0:
        return (0, 0, 0, 0)
    alpha = int(180 * (trail_age / TRAIL_MAX))
    return (255, 165, 0, alpha)  # Orange

def toggle_age_numbers():
    global show_age_numbers
    show_age_numbers = not show_age_numbers

def activate_pattern_menu():
    global pattern_menu_active
    pattern_menu_active = True

def toggle_heatmap():
    global show_heatmap
    show_heatmap = not show_heatmap

# Create menus
main_menu = Menu(WIDTH, INFO_BAR_HEIGHT, MENU_WIDTH, HEIGHT, current_theme)
main_menu.add_button("Clear Grid", lambda: clear_grid())
main_menu.add_button("Randomize", lambda: randomize_grid())
main_menu.add_button("Step Back", lambda: step_back())
main_menu.add_button("Change Theme", lambda: cycle_theme())
main_menu.add_button("Change Rule", lambda: cycle_rule())
main_menu.add_button("Zoom In", lambda: zoom(1.2))
main_menu.add_button("Zoom Out", lambda: zoom(0.8))
main_menu.add_button("Show Patterns", activate_pattern_menu)
main_menu.add_button("Save Pattern", lambda: save_current_pattern())
main_menu.add_button("Toggle Heatmap", toggle_heatmap)
main_menu.visible = True

def toggle_coordinates():
    grid_overlay.show_coordinates = not grid_overlay.show_coordinates

def toggle_quadrants():
    grid_overlay.show_quadrants = not grid_overlay.show_quadrants

def rastgele_grid(rows, cols, depth, density=0.2):
    """Initialize 3D grid with random pattern"""
    return [[[1 if random.random() < density else 0 for _ in range(depth)] for _ in range(cols)] for _ in range(rows)]

def komsu_sayisi(grid, x, y):
    sayi = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < ROWS and 0 <= ny < COLS:
                if grid[nx][ny] > 0:
                    sayi += 1
    return sayi

def sonraki_nesil(grid):
    yeni = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    for x in range(ROWS):
        for y in range(COLS):
            komsular = komsu_sayisi(grid, x, y)
            if grid[x][y] > 0:
                if komsular == 2 or komsular == 3:
                    yeni[x][y] = grid[x][y] + 1
            else:
                if komsular == 3:
                    yeni[x][y] = 1
    return yeni

def yas_rengi(yas):
    if yas <= 0:
        return BLACK
    elif yas < 5:
        return (0, 100 + yas * 30, 0)
    elif yas < 10:
        return (yas * 20, 255, 0)
    else:
        return (255, 255, 0)

def normalize_grid(grid):
    return {pos: 1 for pos in grid}

def grid_to_string(grid):
    return ''.join(''.join(str(cell) for cell in row) for row in grid)

# Hazır glider yapısı (3x3)
def yerles_glider(grid, x, y):
    glider = [
        [0, 1, 0],
        [0, 0, 1],
        [1, 1, 1]
    ]
    for dx in range(3):
        for dy in range(3):
            if 0 <= x+dx < ROWS and 0 <= y+dy < COLS:
                grid[x+dx][y+dy][current_slice] = glider[dx][dy]

def yerles_pulsar(grid, x, y):
    # 13x13 pulsar deseni
    pulsar_coords = [
        (2, 0), (3, 0), (4, 0), (8, 0), (9, 0), (10, 0),
        (0, 2), (5, 2), (7, 2), (12, 2),
        (0, 3), (5, 3), (7, 3), (12, 3),
        (0, 4), (5, 4), (7, 4), (12, 4),
        (2, 5), (3, 5), (4, 5), (8, 5), (9, 5), (10, 5),
        (2, 7), (3, 7), (4, 7), (8, 7), (9, 7), (10, 7),
        (0, 8), (5, 8), (7, 8), (12, 8),
        (0, 9), (5, 9), (7, 9), (12, 9),
        (0, 10), (5, 10), (7, 10), (12, 10),
        (2, 12), (3, 12), (4, 12), (8, 12), (9, 12), (10, 12)
    ]
    for dx, dy in pulsar_coords:
        if 0 <= x + dx < ROWS and 0 <= y + dy < COLS:
            grid[x + dx][y + dy][current_slice] = 1

def yerles_beacon(grid, x, y):
    beacon = [
        [1, 1, 0, 0],
        [1, 0, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 1]
    ]
    for dx in range(4):
        for dy in range(4):
            if 0 <= x + dx < ROWS and 0 <= y + dy < COLS:
                grid[x + dx][y + dy][current_slice] = beacon[dx][dy]

def yerles_toad(grid, x, y):
    toad = [
        [0, 1, 1, 1],
        [1, 1, 1, 0]
    ]
    for dx in range(2):
        for dy in range(4):
            if 0 <= x + dx < ROWS and 0 <= y + dy < COLS:
                grid[x + dx][y + dy][current_slice] = toad[dx][dy]

def yerles_pattern(grid, pattern, x, y, rotation=0, flip_h=False, flip_v=False):
    pattern_data = pattern["pattern"]
    if rotation:
        pattern_data = rotate_pattern(pattern_data, rotation)
    if flip_h:
        pattern_data = flip_pattern(pattern_data, True)
    if flip_v:
        pattern_data = flip_pattern(pattern_data, False)
    for dx in range(len(pattern_data)):
        for dy in range(len(pattern_data[0])):
            if 0 <= x + dx < ROWS and 0 <= y + dy < COLS:
                grid[x + dx][y + dy][current_slice] = pattern_data[dx][dy]

def calculate_stats(grid):
    total_cells = ROWS * COLS
    # Only count alive cells in the current slice
    alive_cells = sum(grid[x][y][current_slice] > 0 for x in range(ROWS) for y in range(COLS))
    dead_cells = total_cells - alive_cells
    density = (alive_cells / total_cells) * 100 if total_cells > 0 else 0
    # Only find patterns in the current slice
    current_slice_grid = [[grid[x][y][current_slice] for y in range(COLS)] for x in range(ROWS)]
    patterns = find_patterns(current_slice_grid)
    pattern_counts = {}
    for p in patterns:
        pattern_type = p["pattern"]["type"]
        pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
    return {
        "alive": alive_cells,
        "dead": dead_cells,
        "density": density,
        "patterns": pattern_counts
    }

def show_stats(stats, nesil):
    stats_surface = pygame.Surface((WIDTH, STATS_HEIGHT))
    stats_surface.fill(THEMES[current_theme]["stats_bar"])
    
    # Format statistics
    stats_text = [
        f"Generation: {nesil}",
        f"Alive Cells: {stats['alive']}",
        f"Density: {stats['density']:.1f}%",
        f"Rule: {RULES[current_rule]['name']}"
    ]
    
    # Add pattern counts
    for pattern_type, count in stats['patterns'].items():
        stats_text.append(f"{pattern_type}: {count}")
    
    # Render statistics
    x = 10
    for text in stats_text:
        text_surface = small_font.render(text, True, THEMES[current_theme]["text"])
        stats_surface.blit(text_surface, (x, 10))
        x += 200
    
    screen.blit(stats_surface, (0, HEIGHT + INFO_BAR_HEIGHT))

def show_pattern_menu():
    patterns = get_all_patterns()
    # Place the menu just below the info bar, flush right, and not overlapping the grid
    menu_x = main_menu.rect.x
    menu_y = INFO_BAR_HEIGHT + 10
    menu_height = min(len(patterns) * 30 + 40, WINDOW_HEIGHT - menu_y - 10)
    menu_surface = pygame.Surface((MENU_WIDTH, menu_height))
    menu_surface.fill(THEMES[current_theme]["menu"])
    
    # Detect mouse hover
    mx, my = pygame.mouse.get_pos()
    hover_index = None
    if menu_x <= mx <= menu_x + MENU_WIDTH and menu_y + 10 <= my <= menu_y + 10 + len(patterns) * 30:
        hover_index = (my - (menu_y + 10)) // 30
        if not (0 <= hover_index < len(patterns)):
            hover_index = None
    
    y = 10
    for i, (key, pattern) in enumerate(patterns.items()):
        # Highlight row if hovered
        if hover_index == i:
            pygame.draw.rect(menu_surface, THEMES[current_theme]["button_hover"], (0, y, MENU_WIDTH, 30))
        text = small_font.render(f"{i+1}. {pattern['name']}", True, THEMES[current_theme]["menu_text"])
        menu_surface.blit(text, (10, y))
        if 'description' in pattern:
            desc = small_font.render(pattern['description'], True, THEMES[current_theme]["menu_text"])
            menu_surface.blit(desc, (10, y + 15))
        y += 30
    
    screen.blit(menu_surface, (menu_x, menu_y))

def get_pattern_name():
    input_box = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 - 20, 200, 40)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = True
    text = ''
    done = False
    
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        done = True
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    else:
                        text += event.unicode
        
        screen.fill(THEMES[current_theme]["background"])
        txt_surface = font.render(text, True, color)
        width = max(200, txt_surface.get_width()+10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x+5, input_box.y+5))
        pygame.draw.rect(screen, color, input_box, 2)
        pygame.display.flip()
        clock.tick(30)
    
    return text

def clear_grid():
    """Clear the grid"""
    global grid, grid_history, nesil
    grid = [[[0 for _ in range(DEPTH)] for _ in range(COLS)] for _ in range(ROWS)]
    grid_history = []
    nesil = 0

def randomize_grid(density=0.2):
    global grid
    grid = rastgele_grid(ROWS, COLS, DEPTH, density)

def step_back():
    """Step back to previous generation"""
    global grid, grid_history, nesil
    if grid_history:
        grid = copy.deepcopy(grid_history.pop())
        nesil -= 1

def cycle_theme():
    global current_theme, main_menu, minimap, grid_overlay
    themes = list(THEMES.keys())
    current_index = themes.index(current_theme)
    current_theme = themes[(current_index + 1) % len(themes)]
    main_menu.theme = current_theme
    minimap.theme = current_theme
    grid_overlay.theme = current_theme

def cycle_rule():
    global current_rule, show_rule_overlay_until
    rules = list(RULES.keys())
    current_index = rules.index(current_rule)
    current_rule = rules[(current_index + 1) % len(rules)]
    show_rule_overlay_until = time.time() + 2  # Show overlay for 2 seconds

def zoom(factor):
    global CELL_SIZE, zoom_level
    zoom_level *= factor
    CELL_SIZE = int(20 * zoom_level)

def center_view():
    global offset_x, offset_y
    offset_x = 0
    offset_y = 0

def save_current_pattern():
    name = get_pattern_name()
    if name:
        save_pattern(grid, name)

def load_saved_pattern():
    patterns = get_all_patterns()
    if patterns:
        pattern = list(patterns.values())[0]  # Load first pattern for now
        global selected_pattern
        selected_pattern = pattern

def get_heatmap_color(activity):
    if activity == 0:
        return (0, 0, 0, 0)
    elif activity < 5:
        return (0, 0, 255, 80 + activity * 20)  # Blue, increasing alpha
    elif activity < 15:
        return (255, 255, 0, 120 + (activity - 5) * 10)  # Yellow
    else:
        return (255, 0, 0, 180)  # Red, high alpha

# Add these globals
grid_offset_x = 0
grid_offset_y = 0

# Update update_window_size to calculate grid centering offsets

def update_window_size(new_width, new_height):
    global WINDOW_WIDTH, WINDOW_HEIGHT, CELL_SIZE, WIDTH, HEIGHT, screen, main_menu, minimap, grid_offset_x, grid_offset_y
    WINDOW_WIDTH, WINDOW_HEIGHT = new_width, new_height
    available_width = WINDOW_WIDTH - MENU_WIDTH
    available_height = WINDOW_HEIGHT - INFO_BAR_HEIGHT - STATS_HEIGHT
    CELL_SIZE = min(available_width // COLS, (available_height - GRID_TOP_MARGIN - GRID_BOTTOM_MARGIN) // ROWS)
    CELL_SIZE = max(CELL_SIZE, MIN_CELL_SIZE)
    WIDTH = COLS * CELL_SIZE
    HEIGHT = ROWS * CELL_SIZE + GRID_TOP_MARGIN + GRID_BOTTOM_MARGIN
    # Center the grid
    grid_area_width = COLS * CELL_SIZE
    grid_area_height = ROWS * CELL_SIZE + GRID_TOP_MARGIN + GRID_BOTTOM_MARGIN
    grid_offset_x = max((available_width - grid_area_width) // 2, 0)
    grid_offset_y = max((available_height - grid_area_height) // 2, 0) + INFO_BAR_HEIGHT
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    # Move menu to right edge
    menu_x = WINDOW_WIDTH - MENU_WIDTH
    main_menu.rect.x = menu_x
    for button_data in main_menu.buttons:
        button_data["button"].rect.x = menu_x + 10
    minimap.rect.x = menu_x + (MENU_WIDTH - MINIMAP_SIZE) // 2
    minimap.rect.y = WINDOW_HEIGHT - MINIMAP_SIZE - 10

def grid_ciz(grid, hiz, nesil, simulasyon_aktif, grid_goster=True, preview_pattern=None, preview_pos=None):
    global show_age_numbers, show_heatmap, current_slice
    screen.fill(THEMES[current_theme]["background"])
    
    # Draw only the current Z slice
    z = current_slice
    for x in range(ROWS):
        for y in range(COLS):
            rect = pygame.Rect(
                y * CELL_SIZE + grid_offset_x,
                x * CELL_SIZE + grid_offset_y + INFO_BAR_HEIGHT + GRID_TOP_MARGIN,
                CELL_SIZE,
                CELL_SIZE
            )
            age = grid[x][y][z]
            transition_value = cell_transition.get_value(x, y)
            if transition_value is not None:
                alive_color = get_enhanced_age_color(1, current_theme)
                dead_color = THEMES[current_theme]["background"]
                t = min(max(transition_value, 0), 1)
                color = (
                    int(dead_color[0] + (alive_color[0] - dead_color[0]) * t),
                    int(dead_color[1] + (alive_color[1] - dead_color[1]) * t),
                    int(dead_color[2] + (alive_color[2] - dead_color[2]) * t)
                )
                pygame.draw.rect(screen, color, rect)
            elif age > 0:
                color = get_enhanced_age_color(age, current_theme)
                pygame.draw.rect(screen, color, rect)
                if show_age_numbers:
                    age_text = small_font.render(str(age), True, (0,0,0) if sum(color[:3]) > 400 else (255,255,255))
                    text_rect = age_text.get_rect(center=rect.center)
                    screen.blit(age_text, text_rect)
            if grid_goster:
                pygame.draw.rect(screen, THEMES[current_theme]["grid"], rect, 1)
    
    # Draw pattern preview if provided
    if preview_pattern and preview_pos:
        px, py = preview_pos
        pattern_data = preview_pattern["pattern"]
        for dx in range(len(pattern_data)):
            for dy in range(len(pattern_data[0])):
                gx = px + dx
                gy = py + dy
                if 0 <= gx < ROWS and 0 <= gy < COLS and pattern_data[dx][dy]:
                    rect = pygame.Rect(
                        gy * CELL_SIZE + grid_offset_x,
                        gx * CELL_SIZE + grid_offset_y + INFO_BAR_HEIGHT + GRID_TOP_MARGIN,
                        CELL_SIZE,
                        CELL_SIZE
                    )
                    # Draw with alpha for ghost effect
                    s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    base_color = get_enhanced_age_color(1, current_theme)
                    if hasattr(base_color, 'r'):
                        rgb = (base_color.r, base_color.g, base_color.b)
                    else:
                        rgb = base_color
                    color = rgb + (120,)
                    s.fill(color)
                    screen.blit(s, rect.topleft)
    
    # Draw grid overlay, aligned with grid margins
    grid_overlay.draw(
        screen,
        grid_offset_x,
        grid_offset_y + INFO_BAR_HEIGHT + GRID_TOP_MARGIN,
        WIDTH,
        HEIGHT
    )
    
    # Draw heatmap overlay if enabled
    if show_heatmap:
        for x in range(ROWS):
            for y in range(COLS):
                activity = activity_grid[x][y][z]
                color = get_heatmap_color(activity)
                if color[3] > 0:
                    s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                    s.fill(color)
                    rect = pygame.Rect(
                        y * CELL_SIZE + grid_offset_x,
                        x * CELL_SIZE + grid_offset_y + INFO_BAR_HEIGHT + GRID_TOP_MARGIN,
                        CELL_SIZE,
                        CELL_SIZE
                    )
                    screen.blit(s, rect.topleft)
    
    # Draw trail overlay
    for x in range(ROWS):
        for y in range(COLS):
            trail_age = trail_grid[x][y][z]
            if trail_age > 0 and grid[x][y][z] == 0:
                color = get_trail_color(trail_age)
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                s.fill(color)
                rect = pygame.Rect(
                    y * CELL_SIZE + grid_offset_x,
                    x * CELL_SIZE + grid_offset_y + INFO_BAR_HEIGHT + GRID_TOP_MARGIN,
                    CELL_SIZE,
                    CELL_SIZE
                )
                screen.blit(s, rect.topleft)
    
    # Draw info bar
    pygame.draw.rect(screen, THEMES[current_theme]["info_bar"], (0, 0, WIDTH, INFO_BAR_HEIGHT))
    text = f"FPS: {hiz}   Generation: {nesil}"
    if not simulasyon_aktif:
        text += "   [Paused]"
    fps_text = font.render(text, True, THEMES[current_theme]["text"])
    screen.blit(fps_text, (10, 10))
    
    # Draw main menu
    main_menu.draw(screen, small_font)
    
    # Draw minimap
    minimap.update(grid_offset_x, grid_offset_y, zoom_level)
    minimap.draw(screen, grid)
    
    # Add a function to draw the rule overlay
    if show_rule_overlay_until > 0 and time.time() < show_rule_overlay_until:
        show_rule_overlay()
    
    pygame.display.flip()

def show_rule_overlay():
    overlay_width = 350
    overlay_height = 40 + 30 * len(RULES)
    overlay_x = (WINDOW_WIDTH - MENU_WIDTH - overlay_width) // 2
    overlay_y = INFO_BAR_HEIGHT + 40
    overlay_surface = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
    overlay_surface.fill((30, 30, 30, 220))
    title = font.render("Available Rules", True, (255, 255, 255))
    overlay_surface.blit(title, (20, 10))
    rules = list(RULES.keys())
    for i, rule in enumerate(rules):
        name = RULES[rule]["name"]
        if rule == current_rule:
            # Draw a highlight box behind the current rule
            pygame.draw.rect(overlay_surface, (80, 80, 0, 180), (10, 40 + i * 30, overlay_width - 20, 28))
            color = (255, 255, 0)
        else:
            color = (200, 200, 200)
        rule_text = small_font.render(f"{i+1}. {name}", True, color)
        overlay_surface.blit(rule_text, (20, 40 + i * 30))
    screen.blit(overlay_surface, (overlay_x, overlay_y))

def apply_rules_3d(grid, rule_name="conway"):
    rule = RULES[rule_name]
    rows, cols, depth = len(grid), len(grid[0]), len(grid[0][0])
    new_grid = [[[0 for _ in range(depth)] for _ in range(cols)] for _ in range(rows)]
    for x in range(rows):
        for y in range(cols):
            for z in range(depth):
                neighbors = 0
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        for dz in [-1, 0, 1]:
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                            nx, ny, nz = x + dx, y + dy, z + dz
                            if 0 <= nx < rows and 0 <= ny < cols and 0 <= nz < depth:
                                if grid[nx][ny][nz] > 0:
                                    neighbors += 1
                current = grid[x][y][z]
                if current > 0:
                    if neighbors in rule["survival"]:
                        new_grid[x][y][z] = current + 1
                else:
                    if neighbors in rule["birth"]:
                        new_grid[x][y][z] = 1
    return new_grid

print('Starting Game of Life...')

try:
    # Initialize grid with random pattern
    grid = rastgele_grid(ROWS, COLS, DEPTH)

    # Main game loop
    while True:
        dt = clock.tick(hiz) / 1000.0  # Convert to seconds
        cell_transition.update(dt)
        events = pygame.event.get()

        # Always check for QUIT event first
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

        # Pattern menu logic
        if pattern_menu_active:
            patterns = list(get_all_patterns().values())
            PATTERN_ROW_OFFSET = 10  # matches y = 10 in show_pattern_menu
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pattern_menu_active = False
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        pattern_index = event.key - pygame.K_1
                        if pattern_index < len(patterns):
                            selected_pattern = patterns[pattern_index]
                            rotation = 0
                            flip_h = False
                            flip_v = False
                            pattern_menu_active = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    menu_x = main_menu.rect.x
                    menu_y = INFO_BAR_HEIGHT + 10
                    menu_width = MENU_WIDTH
                    for i, pattern in enumerate(patterns):
                        row_y = menu_y + PATTERN_ROW_OFFSET + i * 30
                        if menu_x <= mx <= menu_x + menu_width and row_y <= my <= row_y + 30:
                            selected_pattern = pattern
                            rotation = 0
                            flip_h = False
                            flip_v = False
                            pattern_menu_active = False
                            break
            show_pattern_menu()
            pygame.display.flip()
            continue  # Skip the rest of the main loop

        # Normal game event handling
        for event in events:
            if main_menu.handle_event(event):
                continue
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    if selected_pattern:
                        mx, my = pygame.mouse.get_pos()
                        gx = (my - INFO_BAR_HEIGHT - GRID_TOP_MARGIN) // CELL_SIZE
                        gy = (mx - grid_offset_x) // CELL_SIZE
                        if 0 <= gx < ROWS and 0 <= gy < COLS:
                            yerles_pattern(grid, selected_pattern, gx, gy, rotation, flip_h, flip_v)
                        selected_pattern = None
                    else:
                        çizim_modu = True
                        çizim_tipi = 1
                elif event.button == 3:  # Right click
                    çizim_modu = True
                    çizim_tipi = 0
                elif event.button == 4:  # Mouse wheel up
                    zoom(1.1)
                elif event.button == 5:  # Mouse wheel down
                    zoom(0.9)
            elif event.type == pygame.MOUSEBUTTONUP:
                çizim_modu = False
            elif event.type == pygame.MOUSEMOTION:
                if çizim_modu:
                    mx, my = pygame.mouse.get_pos()
                    gx = (my - INFO_BAR_HEIGHT - GRID_TOP_MARGIN) // CELL_SIZE
                    gy = (mx - grid_offset_x) // CELL_SIZE
                    if 0 <= gx < ROWS and 0 <= gy < COLS:
                        old_value = grid[gx][gy][current_slice]
                        grid[gx][gy][current_slice] = çizim_tipi
                        if old_value != çizim_tipi:
                            cell_transition.start_transition(gx, gy, old_value, çizim_tipi)
                elif event.buttons[1]:  # Middle mouse button
                    grid_offset_x += event.rel[0]
                    grid_offset_y += event.rel[1]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    simulasyon_aktif = not simulasyon_aktif
                elif event.key == pygame.K_n:
                    adim_modu = True
                elif event.key == pygame.K_UP:
                    hiz = min(60, hiz + 1)
                elif event.key == pygame.K_DOWN:
                    hiz = max(1, hiz - 1)
                elif event.key == pygame.K_g:
                    grid_goster = not grid_goster
                elif event.key == pygame.K_r:
                    if selected_pattern:
                        rotation = (rotation + 90) % 360
                elif event.key == pygame.K_f:
                    if selected_pattern:
                        flip_h = not flip_h
                elif event.key == pygame.K_v:
                    if selected_pattern:
                        flip_v = not flip_v
                elif event.key == pygame.K_ESCAPE:
                    selected_pattern = None
                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                    patterns = get_all_patterns()
                    pattern_index = event.key - pygame.K_1
                    if pattern_index < len(patterns):
                        selected_pattern = list(patterns.values())[pattern_index]
                        rotation = 0
                        flip_h = False
                        flip_v = False
                elif event.key == pygame.K_w:
                    current_slice = min(DEPTH - 1, current_slice + 1)
                elif event.key == pygame.K_s:
                    current_slice = max(0, current_slice - 1)
            elif event.type == pygame.VIDEORESIZE:
                update_window_size(event.w, event.h)
                continue

        if simulasyon_aktif or adim_modu:
            # Update activity grid decay
            for x in range(ROWS):
                for y in range(COLS):
                    for z in range(DEPTH):
                        activity_grid[x][y][z] = max(0, activity_grid[x][y][z] - 0.1)  # Decay activity over time
                        trail_grid[x][y][z] = max(0, trail_grid[x][y][z] - 1)  # Decay trail for all cells
            
            # Store grid history
            if len(grid_history) >= 50:
                grid_history.pop(0)
            grid_history.append(copy.deepcopy(grid))
            
            # Apply rules and update grid
            new_grid = apply_rules_3d(grid, current_rule)
            for x in range(ROWS):
                for y in range(COLS):
                    for z in range(DEPTH):
                        if new_grid[x][y][z] != grid[x][y][z]:
                            cell_transition.start_transition(x, y, grid[x][y][z], new_grid[x][y][z])
                            activity_grid[x][y][z] += 1  # Increase activity for changed cells
                            if grid[x][y][z] > 0 and new_grid[x][y][z] == 0:
                                trail_grid[x][y][z] = TRAIL_MAX  # Set trail for newly dead cells
            grid = new_grid
            nesil += 1
            adim_modu = False

        stats = calculate_stats(grid)
        show_stats(stats, nesil)
        preview_pattern = None
        preview_pos = None
        if selected_pattern:
            mx, my = pygame.mouse.get_pos()
            gx = (my - INFO_BAR_HEIGHT - GRID_TOP_MARGIN) // CELL_SIZE
            gy = (mx - grid_offset_x) // CELL_SIZE
            if 0 <= gx < ROWS and 0 <= gy < COLS:
                preview_pattern = selected_pattern
                preview_pos = (gx, gy)
        grid_ciz(grid, hiz, nesil, simulasyon_aktif, grid_goster, preview_pattern, preview_pos)

    pygame.quit()
except Exception as e:
    import traceback
    print('Exception occurred:')
    traceback.print_exc()
    input('Press Enter to exit...')