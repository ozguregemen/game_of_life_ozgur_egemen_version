import numpy as np
from collections import deque

# Game rules
RULES = {
    "conway": {
        "name": "Conway's Game of Life",
        "birth": [3],
        "survival": [2, 3]
    },
    "highlife": {
        "name": "HighLife",
        "birth": [3, 6],
        "survival": [2, 3]
    },
    "day_and_night": {
        "name": "Day & Night",
        "birth": [3, 6, 7, 8],
        "survival": [3, 4, 6, 7, 8]
    },
    "seeds": {
        "name": "Seeds",
        "birth": [2],
        "survival": []
    }
}

# Pattern recognition
PATTERN_TYPES = {
    "still_life": {
        "block": [[1, 1], [1, 1]],
        "beehive": [[0, 1, 1, 0], [1, 0, 0, 1], [0, 1, 1, 0]],
        "loaf": [[0, 1, 1, 0], [1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 0]],
        "boat": [[1, 1, 0], [1, 0, 1], [0, 1, 0]],
        "tub": [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
    },
    "oscillator": {
        "blinker": [[1], [1], [1]],
        "toad": [[0, 1, 1, 1], [1, 1, 1, 0]],
        "beacon": [[1, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 1]],
        "pulsar": [[0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                  [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
                  [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
                  [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
                  [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
                  [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
                  [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
                  [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
                  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0]]
    },
    "spaceship": {
        "glider": [[0, 1, 0], [0, 0, 1], [1, 1, 1]],
        "lwss": [[0, 1, 1, 1, 1], [1, 0, 0, 0, 1], [0, 0, 0, 0, 1], [1, 0, 0, 1, 0]],
        "mwss": [[0, 0, 1, 1, 1, 1, 1], [0, 1, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 0, 1], [0, 0, 0, 0, 0, 1, 0], [1, 0, 1, 0, 0, 0, 0]],
        "hwss": [[0, 0, 1, 1, 1, 1, 1, 1], [0, 1, 0, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 0, 0, 1], [0, 0, 0, 0, 0, 0, 1, 0], [1, 0, 1, 0, 0, 0, 0, 0]]
    }
}

def apply_rules(grid, rule_name="conway"):
    """Apply the specified rules to the sparse grid (dictionary-based)"""
    rule = RULES[rule_name]
    new_grid = {}
    cells_to_check = set()
    for pos in grid:
        x, y = pos
        cells_to_check.add(pos)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                cells_to_check.add((x + dx, y + dy))
    for pos in cells_to_check:
        x, y = pos
        neighbors = count_neighbors(grid, x, y)
        current = grid.get(pos, 0)
        if current > 0:
            if neighbors in rule["survival"]:
                new_grid[pos] = current + 1
        else:
            if neighbors in rule["birth"]:
                new_grid[pos] = 1
    return new_grid

def count_neighbors(grid, x, y):
    """Count the number of live neighbors for a cell (sparse dict version)"""
    count = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            if grid.get((x + dx, y + dy), 0):
                count += 1
    return count

def recognize_pattern(grid, x, y, size=5):
    """Recognize patterns in the grid around the given position"""
    pattern = extract_pattern(grid, x, y, size)
    if not pattern:
        return None
    
    # Check for each pattern type
    for pattern_type, patterns in PATTERN_TYPES.items():
        for name, template in patterns.items():
            if match_pattern(pattern, template):
                return {
                    "type": pattern_type,
                    "name": name,
                    "pattern": template
                }
    return None

def extract_pattern(grid, x, y, size):
    """Extract a pattern from the grid around the given position (2D list version)"""
    pattern = []
    half = size // 2
    for i in range(x - half, x + half + 1):
        row = []
        for j in range(y - half, y + half + 1):
            if 0 <= i < len(grid) and 0 <= j < len(grid[0]):
                row.append(grid[i][j])
            else:
                row.append(0)
        pattern.append(row)
    return pattern

def match_pattern(pattern, template):
    """Check if a pattern matches a template"""
    if len(pattern) != len(template) or len(pattern[0]) != len(template[0]):
        return False
    
    for i in range(len(pattern)):
        for j in range(len(pattern[0])):
            if pattern[i][j] != template[i][j]:
                return False
    return True

def predict_evolution(grid, steps=10):
    """Predict the evolution of the grid for a number of steps"""
    evolution = [grid]
    current = grid
    
    for _ in range(steps):
        current = apply_rules(current)
        evolution.append(current)
    
    return evolution

def find_patterns(grid):
    """Find all patterns in the grid (2D list version)"""
    patterns = []
    for x in range(len(grid)):
        for y in range(len(grid[0])):
            if grid[x][y] == 1:
                pattern = recognize_pattern(grid, x, y)
                if pattern:
                    patterns.append({
                        "position": (x, y),
                        "pattern": pattern
                    })
    return patterns

# New function for 2D list grid
def apply_rules_2d(grid, rule_name="conway"):
    """Apply the specified rules to a 2D list grid"""
    rule = RULES[rule_name]
    rows, cols = len(grid), len(grid[0])
    new_grid = [[0 for _ in range(cols)] for _ in range(rows)]
    for x in range(rows):
        for y in range(cols):
            neighbors = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] > 0:
                        neighbors += 1
            current = grid[x][y]
            if current > 0:
                if neighbors in rule["survival"]:
                    new_grid[x][y] = current + 1
            else:
                if neighbors in rule["birth"]:
                    new_grid[x][y] = 1
    return new_grid 