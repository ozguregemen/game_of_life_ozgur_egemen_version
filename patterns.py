import datetime
import json
import re
import unicodedata
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

from app_paths import APPLICATION_PATHS
from mode_patterns import MODE_PATTERNS
from mode_registry import MODE_KEYS, get_mode_definition

# Famous Game of Life patterns
PATTERNS = {
    "glider": {
        "name": "Glider",
        "category": "spaceships",
        "pattern": [
            [0, 1, 0],
            [0, 0, 1],
            [1, 1, 1]
        ]
    },
    "pulsar": {
        "name": "Pulsar",
        "category": "oscillators",
        "pattern": [
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
            [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0]
        ]
    },
    "beacon": {
        "name": "Beacon",
        "category": "oscillators",
        "pattern": [
            [1, 1, 0, 0],
            [1, 0, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 1]
        ]
    },
    "toad": {
        "name": "Toad",
        "category": "oscillators",
        "pattern": [
            [0, 1, 1, 1],
            [1, 1, 1, 0]
        ]
    },
    "blinker": {
        "name": "Blinker",
        "category": "oscillators",
        "pattern": [
            [1],
            [1],
            [1]
        ]
    },
    "block": {
        "name": "Block",
        "category": "still_lifes",
        "pattern": [
            [1, 1],
            [1, 1]
        ]
    },
    "beehive": {
        "name": "Beehive",
        "category": "still_lifes",
        "pattern": [
            [0, 1, 1, 0],
            [1, 0, 0, 1],
            [0, 1, 1, 0]
        ]
    },
    "loaf": {
        "name": "Loaf",
        "category": "still_lifes",
        "pattern": [
            [0, 1, 1, 0],
            [1, 0, 0, 1],
            [0, 1, 0, 1],
            [0, 0, 1, 0]
        ]
    },
    "glider_gun": {
        "name": "Gosper Glider Gun",
        "category": "guns_and_puffers",
        "pattern": [
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
            [0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
            [1,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [1,1,0,0,0,0,0,0,0,0,1,0,0,0,1,0,1,1,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        ]
    },
    "pentadecathlon": {
        "name": "Pentadecathlon",
        "category": "oscillators",
        "pattern": [
            [0,0,1,0,0],
            [1,0,1,0,1],
            [0,1,1,1,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,1,1,1,0],
            [1,0,1,0,1],
            [0,0,1,0,0]
        ]
    },
    "r_pentomino": {
        "name": "R-Pentomino",
        "category": "methuselahs",
        "pattern": [
            [0,1,1],
            [1,1,0],
            [0,1,0]
        ]
    },
    "diehard": {
        "name": "Diehard",
        "category": "methuselahs",
        "pattern": [
            [0,0,0,0,0,0,1,0],
            [1,1,0,0,0,0,0,0],
            [0,1,0,0,0,1,1,1]
        ]
    },
    "acorn": {
        "name": "Acorn",
        "category": "methuselahs",
        "pattern": [
            [0,1,0,0,0,0,0],
            [0,0,0,1,0,0,0],
            [1,1,0,0,1,1,1]
        ]
    },
    "lwss": {
        "name": "Lightweight Spaceship (LWSS)",
        "category": "spaceships",
        "pattern": [
            [0,1,1,1,1],
            [1,0,0,0,1],
            [0,0,0,0,1],
            [1,0,0,1,0]
        ]
    },
    "copperhead": {
        "name": "Copperhead",
        "category": "spaceships",
        "pattern": [
            [0,1,1,0,0,1,1,0],
            [0,0,0,1,1,0,0,0],
            [0,0,0,1,1,0,0,0],
            [1,0,1,0,0,1,0,1],
            [1,0,0,0,0,0,0,1],
            [0,0,0,0,0,0,0,0],
            [1,0,0,0,0,0,0,1],
            [0,1,1,0,0,1,1,0],
            [0,0,1,1,1,1,0,0],
            [0,0,0,0,0,0,0,0],
            [0,0,0,1,1,0,0,0],
            [0,0,0,1,1,0,0,0]
        ]
    },
    "washerwoman": {
        "name": "Washerwoman",
        "category": "guns_and_puffers",
        "pattern": [
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [1,1,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0],
            [1,1,1,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,1,0,1],
            [1,1,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    ]
    },
    "4-8-12_diamond": {
        "name": "4-8-12 Diamond",
        "category": "oscillators",
        "pattern": [
            [0,0,0,0,1,1,1,1,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,1,1,1,1,1,1,1,1,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [1,1,1,1,1,1,1,1,1,1,1,1],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,1,1,1,1,1,1,1,1,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,1,1,1,1,0,0,0,0]
        ]
    },
    "puffer": {
        "name": "Puffer",
        "category": "guns_and_puffers",
        "pattern": [
            [0,1,1,1,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,1,1,1,0],
            [1,0,0,1,0,0,0,0,0,1,1,1,0,0,0,1,1,1,0,0,0,0,0,1,0,0,1],
            [0,0,0,1,0,0,0,0,1,1,0,1,0,0,0,1,0,1,1,0,0,0,0,1,0,0,0],
            [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
            [0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0],
            [0,0,0,1,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,1,0,0,0],
            [0,0,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,1,0,0]     
        ]
    },
    "caterpillar": {
        "name": "Caterpillar",
        "category": "spaceships",
        "pattern": [
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
        ]
    },
    "david-hilbert": {
        "name": "David Hilbert",
        "category": "methuselahs",
        "pattern": [
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0],
            [0,0,1,0,1,1,0,1,0,1,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0],
            [0,0,1,1,0,1,0,1,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,1,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,1,0,0,0,0,0,0,0,0,0],
            [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,1,1,1,0,0,0,0,0,0,0,0],
            [0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,1,0,0,0,0,0,0,0],
            [0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0],
            [0,0,1,1,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
            [0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,1],
            [0,0,1,1,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,1,1,0,1],
            [0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0],
            [0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0],
            [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0],
            [0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,1,0,0,0,1,1,0,0,1,1,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
            [0,0,0,0,1,1,1,0,0,0,0,1,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0],
            [0,0,0,0,1,0,0,0,0,1,0,1,0,1,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0]
        ]
    }
}

PATTERN_STATE_VALUES = {
    "life": frozenset((0, 1)),
    "immigration": frozenset((-1, 0, 1)),
    "brians_brain": frozenset((0, 1, 2)),
    "langtons_ant": frozenset((0, 1)),
    "wireworld": frozenset((0, 1, 2, 3)),
    "cyclic_automaton": frozenset(range(8)),
}

MAX_BUILTIN_PATTERNS_PER_MODE = 20
PATTERN_CATEGORY_LABELS: dict[str, tuple[tuple[str, str], ...]] = {
    "life": (
        ("still_lifes", "Still Lifes"),
        ("oscillators", "Oscillators"),
        ("spaceships", "Spaceships"),
        ("methuselahs", "Methuselahs"),
        ("guns_and_puffers", "Guns & Puffers"),
    ),
    "immigration": (
        ("still_lifes", "Stable Two-Species Forms"),
        ("oscillators", "Two-Species Oscillators"),
        ("spaceships", "Two-Species Spaceships"),
        ("competition", "Competition Seeds"),
    ),
    "brians_brain": (
        ("oscillators", "Oscillators"),
        ("wave_seeds", "Wave Seeds"),
        ("wickstretchers", "Wickstretchers"),
    ),
    "langtons_ant": (
        ("classic_starts", "Classic Starts"),
        ("arenas", "Prepared Arenas"),
    ),
    "wireworld": (
        ("signals", "Signals & Wires"),
        ("routing", "Routing Components"),
        ("timing", "Timing Circuits"),
        ("logic", "Logic Gates"),
        ("memory", "Memory & State"),
        ("arithmetic", "Arithmetic Circuits"),
    ),
    "cyclic_automaton": (
        ("wave_seeds", "Wave Seeds"),
        ("spiral_seeds", "Spiral Seeds"),
    ),
}

PATTERN_DIRECTORY = APPLICATION_PATHS.patterns
_INVALID_FILENAME_CHARACTERS = re.compile(r'[\\/:*?"<>|]+')
_WHITESPACE = re.compile(r"\s+")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_PATTERN_CACHE: dict[str, dict[str, Any]] = {}
_MODE_PATTERN_CACHE: dict[str, dict[str, dict[str, Any]]] = {
    mode: {} for mode in MODE_KEYS
}
_MODE_CATEGORY_CACHE: dict[str, dict[str, dict[str, dict[str, Any]]]] = {
    mode: {} for mode in MODE_KEYS
}


def safe_pattern_filename(name: str) -> str:
    """Convert a display name into a portable JSON filename stem."""
    if not isinstance(name, str):
        raise TypeError("Pattern name must be text.")

    normalized = unicodedata.normalize("NFKC", name).strip()
    if not normalized:
        raise ValueError("Pattern name cannot be empty.")

    stem = _INVALID_FILENAME_CHARACTERS.sub("_", normalized)
    stem = stem.replace("..", "_")
    stem = _WHITESPACE.sub("_", stem).strip(" ._")
    if not stem:
        raise ValueError("Pattern name must contain a valid filename character.")
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    return stem.casefold()


def _validate_pattern_data(data: Any) -> dict[str, Any]:
    """Validate and normalize a pattern document loaded from JSON."""
    if not isinstance(data, dict):
        raise TypeError("Pattern JSON must contain an object.")

    name = data["name"]
    pattern = data["pattern"]
    mode = data.get("mode", "life")
    category = data.get("category", "custom")
    if not isinstance(name, str) or not name.strip():
        raise TypeError("Pattern 'name' must be non-empty text.")
    safe_pattern_filename(name)
    if not isinstance(mode, str) or mode not in PATTERN_STATE_VALUES:
        raise TypeError("Pattern 'mode' must name a registered simulation mode.")
    if (
        not isinstance(category, str)
        or not re.fullmatch(r"[a-z][a-z0-9_]*", category)
    ):
        raise TypeError(
            "Pattern 'category' must be a lowercase identifier such as 'oscillators'."
        )
    if not isinstance(pattern, list) or not pattern:
        raise TypeError("Pattern must be a non-empty two-dimensional list.")
    if not all(isinstance(row, list) and row for row in pattern):
        raise TypeError("Every pattern row must be a non-empty list.")

    width = len(pattern[0])
    if any(len(row) != width for row in pattern):
        raise TypeError("Pattern rows must all have the same length.")
    allowed_states = PATTERN_STATE_VALUES[mode]
    if any(
        not isinstance(cell, (int, bool)) or cell not in allowed_states
        for row in pattern
        for cell in row
    ):
        states = ", ".join(str(state) for state in sorted(allowed_states))
        mode_name = get_mode_definition(mode).name
        raise TypeError(f"{mode_name} pattern cells must be {states}.")

    validated = dict(data)
    validated["name"] = name.strip()
    validated["mode"] = mode
    validated["category"] = category
    validated["pattern"] = [[int(cell) for cell in row] for row in pattern]

    ant = data.get("ant")
    if ant is not None:
        if mode != "langtons_ant" or not isinstance(ant, dict):
            raise TypeError("Only Langton's Ant patterns may contain ant metadata.")
        try:
            ant_row = ant["row"]
            ant_col = ant["col"]
            ant_direction = ant["direction"]
        except KeyError as exc:
            raise TypeError("Ant metadata requires row, col, and direction.") from exc
        if not all(
            isinstance(value, int)
            for value in (ant_row, ant_col, ant_direction)
        ):
            raise TypeError("Ant row, col, and direction must be integers.")
        if not (0 <= ant_row < len(pattern) and 0 <= ant_col < width):
            raise TypeError("Ant position must be inside its pattern.")
        if ant_direction not in (0, 1, 2, 3):
            raise TypeError("Ant direction must be between 0 and 3.")
        validated["ant"] = {
            "row": ant_row,
            "col": ant_col,
            "direction": ant_direction,
        }
    return validated


def _read_pattern_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as pattern_file:
            return _validate_pattern_data(json.load(pattern_file))
    except (
        json.JSONDecodeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        warnings.warn(f"Skipping invalid pattern file '{path.name}': {exc}")
        return None


def _pattern_cache_key(mode: str, name: str) -> str:
    """Return a stable cache key while preserving legacy Life keys."""
    normalized_name = name.casefold()
    return normalized_name if mode == "life" else f"{mode}:{normalized_name}"


def _pattern_filename(name: str, mode: str) -> str:
    """Return a mode-aware filename without renaming legacy Life files."""
    stem = safe_pattern_filename(name)
    return f"{stem}.json" if mode == "life" else f"{mode}__{stem}.json"


def refresh_pattern_cache() -> None:
    """Reload built-in and custom patterns into the shared cache."""
    refreshed: dict[str, dict[str, Any]] = {}
    builtins = {**PATTERNS, **MODE_PATTERNS}
    builtin_counts = {mode: 0 for mode in MODE_KEYS}
    for key, pattern_data in builtins.items():
        document = deepcopy(pattern_data)
        document.setdefault("mode", "life")
        validated = _validate_pattern_data(document)
        builtin_counts[validated["mode"]] += 1
        refreshed[key] = validated

    oversized = {
        mode: count
        for mode, count in builtin_counts.items()
        if count > MAX_BUILTIN_PATTERNS_PER_MODE
    }
    if oversized:
        details = ", ".join(
            f"{mode}={count}" for mode, count in sorted(oversized.items())
        )
        raise ValueError(
            "Built-in pattern catalogs may contain at most "
            f"{MAX_BUILTIN_PATTERNS_PER_MODE} entries per mode ({details})."
        )

    if PATTERN_DIRECTORY.is_dir():
        for path in sorted(PATTERN_DIRECTORY.glob("*.json")):
            pattern_data = _read_pattern_file(path)
            if pattern_data is not None:
                key = _pattern_cache_key(pattern_data["mode"], pattern_data["name"])
                refreshed[key] = pattern_data

    _PATTERN_CACHE.clear()
    _PATTERN_CACHE.update(refreshed)
    for mode in MODE_KEYS:
        mode_cache = _MODE_PATTERN_CACHE.setdefault(mode, {})
        mode_cache.clear()
        category_cache = _MODE_CATEGORY_CACHE.setdefault(mode, {})
        category_cache.clear()
    for key, pattern_data in refreshed.items():
        mode = pattern_data["mode"]
        category = pattern_data["category"]
        _MODE_PATTERN_CACHE[mode][key] = pattern_data
        _MODE_CATEGORY_CACHE[mode].setdefault(category, {})[key] = pattern_data


def save_pattern(
    pattern: Sequence[Sequence[int]],
    name: str,
    description: str = "",
    *,
    mode: str = "life",
    ant: dict[str, int] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Save a custom pattern and refresh the shared cache.

    Existing files are protected by default. Callers must explicitly pass
    ``overwrite=True`` to replace one.
    """
    if mode not in PATTERN_STATE_VALUES:
        raise ValueError(f"Unknown simulation mode: {mode}")
    filename = _pattern_filename(name, mode)
    document: dict[str, Any] = {
        "name": name,
        "mode": mode,
        "description": description,
        "pattern": [list(row) for row in pattern],
        "date_created": datetime.datetime.now().isoformat(),
    }
    if ant is not None:
        document["ant"] = dict(ant)
    pattern_data = _validate_pattern_data(document)
    PATTERN_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = PATTERN_DIRECTORY / filename
    file_mode = "w" if overwrite else "x"
    try:
        with path.open(file_mode, encoding="utf-8") as pattern_file:
            json.dump(pattern_data, pattern_file, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise FileExistsError(
            f"A pattern named '{name}' already exists. Choose another name."
        ) from exc

    refresh_pattern_cache()
    return pattern_data


def delete_pattern(name: str, *, mode: str = "life") -> bool:
    """Delete a custom pattern and refresh the cache when it changes."""
    if mode not in PATTERN_STATE_VALUES:
        raise ValueError(f"Unknown simulation mode: {mode}")
    path = PATTERN_DIRECTORY / _pattern_filename(name, mode)
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    except OSError as exc:
        warnings.warn(f"Could not delete pattern '{name}': {exc}")
        return False

    refresh_pattern_cache()
    return True


def load_pattern(name: str, *, mode: str = "life") -> dict[str, Any] | None:
    """Load and validate one custom pattern without propagating file errors."""
    if mode not in PATTERN_STATE_VALUES:
        raise ValueError(f"Unknown simulation mode: {mode}")
    path = PATTERN_DIRECTORY / _pattern_filename(name, mode)
    return _read_pattern_file(path)


def get_all_patterns() -> dict[str, dict[str, Any]]:
    """Return the shared in-memory pattern cache without touching disk."""
    return _PATTERN_CACHE


def get_patterns_for_mode(mode: str) -> dict[str, dict[str, Any]]:
    """Return the cached built-in and custom patterns for one mode."""
    if mode not in _MODE_PATTERN_CACHE:
        raise ValueError(f"Unknown simulation mode: {mode}")
    return _MODE_PATTERN_CACHE[mode]


def get_pattern_categories_for_mode(mode: str) -> tuple[tuple[str, str, int], ...]:
    """Return ordered, non-empty category metadata from the in-memory cache."""
    if mode not in _MODE_CATEGORY_CACHE:
        raise ValueError(f"Unknown simulation mode: {mode}")

    categories = _MODE_CATEGORY_CACHE[mode]
    configured = dict(PATTERN_CATEGORY_LABELS.get(mode, ()))
    ordered_keys = [
        key for key, _ in PATTERN_CATEGORY_LABELS.get(mode, ()) if key in categories
    ]
    ordered_keys.extend(sorted(set(categories) - set(ordered_keys)))
    return tuple(
        (
            key,
            configured.get(
                key,
                "Custom Patterns" if key == "custom" else key.replace("_", " ").title(),
            ),
            len(categories[key]),
        )
        for key in ordered_keys
    )


def get_patterns_for_category(
    mode: str,
    category: str,
) -> dict[str, dict[str, Any]]:
    """Return one cached mode/category catalog without reading from disk."""
    if mode not in _MODE_CATEGORY_CACHE:
        raise ValueError(f"Unknown simulation mode: {mode}")
    if category == "all":
        return _MODE_PATTERN_CACHE[mode]
    try:
        return _MODE_CATEGORY_CACHE[mode][category]
    except KeyError as exc:
        raise ValueError(f"Unknown pattern category for {mode}: {category}") from exc


def rotate_pattern(
    pattern: Sequence[Sequence[int]],
    degrees: int = 90,
) -> list[Sequence[int]]:
    """Rotate a pattern by the specified degrees (90, 180, or 270)."""
    if degrees not in [90, 180, 270]:
        raise ValueError("Rotation must be 90, 180, or 270 degrees")
    
    # Convert to list of lists if it's not already
    pattern = [list(row) for row in pattern]
    
    # Rotate 90 degrees clockwise
    if degrees == 90:
        return list(zip(*pattern[::-1]))
    # Rotate 180 degrees
    elif degrees == 180:
        return [row[::-1] for row in pattern[::-1]]
    # Rotate 270 degrees clockwise
    else:  # 270
        return list(zip(*pattern))[::-1]

def flip_pattern(
    pattern: Sequence[Sequence[int]],
    horizontal: bool = True,
) -> list[Sequence[int]]:
    """Flip a pattern horizontally or vertically."""
    if horizontal:
        return [row[::-1] for row in pattern]
    else:
        return list(pattern[::-1])


refresh_pattern_cache()
