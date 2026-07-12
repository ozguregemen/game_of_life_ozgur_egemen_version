from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

# Birth/Survival rules. Cell values greater than zero are treated as alive.
RULES = {
    "conway": {
        "name": "Conway's Game of Life",
        "birth": [3],
        "survival": [2, 3],
    },
    "highlife": {
        "name": "HighLife",
        "birth": [3, 6],
        "survival": [2, 3],
    },
    "day_and_night": {
        "name": "Day & Night",
        "birth": [3, 6, 7, 8],
        "survival": [3, 4, 6, 7, 8],
    },
    "seeds": {
        "name": "Seeds",
        "birth": [2],
        "survival": [],
    },
}

PATTERN_TYPES = {
    "still_life": {
        "block": [[1, 1], [1, 1]],
        "beehive": [[0, 1, 1, 0], [1, 0, 0, 1], [0, 1, 1, 0]],
        "loaf": [[0, 1, 1, 0], [1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 0]],
        "boat": [[1, 1, 0], [1, 0, 1], [0, 1, 0]],
        "tub": [[0, 1, 0], [1, 0, 1], [0, 1, 0]],
    },
    "oscillator": {
        "blinker": [[1], [1], [1]],
        "toad": [[0, 1, 1, 1], [1, 1, 1, 0]],
        "beacon": [[1, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 1]],
        "pulsar": [
            [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
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
            [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
        ],
    },
    "spaceship": {
        "glider": [[0, 1, 0], [0, 0, 1], [1, 1, 1]],
        "lwss": [[0, 1, 1, 1, 1], [1, 0, 0, 0, 1], [0, 0, 0, 0, 1], [1, 0, 0, 1, 0]],
        "mwss": [
            [0, 0, 1, 1, 1, 1, 1],
            [0, 1, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 1, 0],
            [1, 0, 1, 0, 0, 0, 0],
        ],
        "hwss": [
            [0, 0, 1, 1, 1, 1, 1, 1],
            [0, 1, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 1, 0],
            [1, 0, 1, 0, 0, 0, 0, 0],
        ],
    },
}


def _validate_rule(rule_name: str) -> dict[str, Any]:
    try:
        return RULES[rule_name]
    except KeyError as exc:
        available = ", ".join(RULES)
        raise ValueError(f"Unknown rule '{rule_name}'. Available rules: {available}") from exc


def count_neighbors(grid: Mapping[tuple[int, int], int], x: int, y: int) -> int:
    """Count live neighbors in a sparse dictionary grid."""
    count = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            if grid.get((x + dx, y + dy), 0) > 0:
                count += 1
    return count


def apply_rules(
    grid: Mapping[tuple[int, int], int],
    rule_name: str = "conway",
) -> dict[tuple[int, int], int]:
    """Apply a rule to a sparse dictionary grid."""
    rule = _validate_rule(rule_name)
    cells_to_check: set[tuple[int, int]] = set()

    for x, y in grid:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cells_to_check.add((x + dx, y + dy))

    new_grid: dict[tuple[int, int], int] = {}
    for x, y in cells_to_check:
        neighbors = count_neighbors(grid, x, y)
        current = grid.get((x, y), 0)
        if current > 0 and neighbors in rule["survival"]:
            new_grid[(x, y)] = current + 1
        elif current <= 0 and neighbors in rule["birth"]:
            new_grid[(x, y)] = 1

    return new_grid


def apply_rules_2d(
    grid: Sequence[Sequence[int]],
    rule_name: str = "conway",
) -> list[list[int]]:
    """Apply a rule to a finite 2D grid.

    Values greater than zero are alive. Surviving cells have their age
    incremented; newborn cells start at age 1. The grid does not wrap.
    """
    if not grid or not grid[0]:
        return []

    rule = _validate_rule(rule_name)
    rows, cols = len(grid), len(grid[0])
    new_grid = [[0 for _ in range(cols)] for _ in range(rows)]

    for x in range(rows):
        for y in range(cols):
            neighbors = 0
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] > 0:
                        neighbors += 1

            current = grid[x][y]
            if current > 0 and neighbors in rule["survival"]:
                new_grid[x][y] = current + 1
            elif current <= 0 and neighbors in rule["birth"]:
                new_grid[x][y] = 1

    return new_grid


def _normalise_pattern(pattern: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(1 if cell > 0 else 0 for cell in row) for row in pattern)


def _rotate_90(pattern: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(row) for row in zip(*pattern[::-1]))


_VARIANT_CACHE: dict[
    tuple[tuple[int, ...], ...],
    tuple[tuple[tuple[int, ...], ...], ...],
] = {}


def _unique_variants(
    pattern: Sequence[Sequence[int]],
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    """Return unique rotations and mirror variants of a pattern."""
    original = _normalise_pattern(pattern)
    cached = _VARIANT_CACHE.get(original)
    if cached is not None:
        return cached

    variants: set[tuple[tuple[int, ...], ...]] = set()
    current = original

    for _ in range(4):
        variants.add(current)
        variants.add(tuple(tuple(reversed(row)) for row in current))
        current = _rotate_90(current)

    result = tuple(variants)
    _VARIANT_CACHE[original] = result
    return result


def _matches_at(
    normalised_grid: Sequence[Sequence[int]],
    template: tuple[tuple[int, ...], ...],
    top: int,
    left: int,
    require_dead_border: bool = True,
) -> bool:
    height = len(template)
    width = len(template[0])

    for row in range(height):
        for col in range(width):
            if normalised_grid[top + row][left + col] != template[row][col]:
                return False

    if not require_dead_border:
        return True

    rows, cols = len(normalised_grid), len(normalised_grid[0])
    border_top = max(0, top - 1)
    border_left = max(0, left - 1)
    border_bottom = min(rows, top + height + 1)
    border_right = min(cols, left + width + 1)

    for row in range(border_top, border_bottom):
        for col in range(border_left, border_right):
            inside = top <= row < top + height and left <= col < left + width
            if not inside and normalised_grid[row][col]:
                return False

    return True


def find_patterns(
    grid: Sequence[Sequence[int]],
    require_dead_border: bool = True,
) -> list[dict[str, Any]]:
    """Find known patterns by scanning templates at their real dimensions.

    The previous implementation always extracted a 5x5 region, which could
    never equal 2x2, 3x3 or 4x4 templates. This implementation normalises cell
    ages, supports rotations/reflections and avoids duplicate matches.
    """
    if not grid or not grid[0]:
        return []

    normalised_grid = [[1 if cell > 0 else 0 for cell in row] for row in grid]
    rows, cols = len(normalised_grid), len(normalised_grid[0])
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, int, int, int]] = set()

    for pattern_type, named_patterns in PATTERN_TYPES.items():
        for name, template in named_patterns.items():
            for variant in _unique_variants(template):
                height = len(variant)
                width = len(variant[0])
                if height > rows or width > cols:
                    continue

                for top in range(rows - height + 1):
                    for left in range(cols - width + 1):
                        if not _matches_at(
                            normalised_grid,
                            variant,
                            top,
                            left,
                            require_dead_border=require_dead_border,
                        ):
                            continue

                        key = (pattern_type, name, top, left, height, width)
                        if key in seen:
                            continue
                        seen.add(key)
                        results.append(
                            {
                                "position": (top, left),
                                "size": (height, width),
                                "pattern": {
                                    "type": pattern_type,
                                    "name": name,
                                    "pattern": [list(row) for row in variant],
                                },
                            }
                        )

    return results


def recognize_pattern(
    grid: Sequence[Sequence[int]],
    x: int,
    y: int,
    size: int = 5,
) -> dict[str, Any] | None:
    """Return a known pattern that contains the requested cell.

    ``size`` is retained for backward compatibility and is not required for
    matching.
    """
    del size
    for match in find_patterns(grid):
        top, left = match["position"]
        height, width = match["size"]
        if top <= x < top + height and left <= y < left + width:
            return match["pattern"]
    return None


def extract_pattern(
    grid: Sequence[Sequence[int]],
    x: int,
    y: int,
    size: int,
) -> list[list[int]]:
    """Extract a square pattern around a position."""
    if size <= 0:
        raise ValueError("size must be positive")

    half = size // 2
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    extracted: list[list[int]] = []

    for row in range(x - half, x - half + size):
        extracted_row = []
        for col in range(y - half, y - half + size):
            if 0 <= row < rows and 0 <= col < cols:
                extracted_row.append(1 if grid[row][col] > 0 else 0)
            else:
                extracted_row.append(0)
        extracted.append(extracted_row)

    return extracted


def match_pattern(
    pattern: Sequence[Sequence[int]],
    template: Sequence[Sequence[int]],
) -> bool:
    return _normalise_pattern(pattern) == _normalise_pattern(template)


def predict_evolution(
    grid: Any,
    steps: int = 10,
    rule_name: str = "conway",
) -> list[Any]:
    """Return copies of the current state and its following states."""
    if steps < 0:
        raise ValueError("steps cannot be negative")

    evolution = [grid]
    current = grid

    for _ in range(steps):
        if isinstance(current, Mapping):
            current = apply_rules(current, rule_name)
        else:
            current = apply_rules_2d(current, rule_name)
        evolution.append(current)

    return evolution
