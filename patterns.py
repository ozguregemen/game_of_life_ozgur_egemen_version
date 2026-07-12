import datetime
import json
import re
import unicodedata
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

# Famous Game of Life patterns
PATTERNS = {
    "glider": {
        "name": "Glider",
        "pattern": [
            [0, 1, 0],
            [0, 0, 1],
            [1, 1, 1]
        ]
    },
    "pulsar": {
        "name": "Pulsar",
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
        "pattern": [
            [1, 1, 0, 0],
            [1, 0, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 1]
        ]
    },
    "toad": {
        "name": "Toad",
        "pattern": [
            [0, 1, 1, 1],
            [1, 1, 1, 0]
        ]
    },
    "blinker": {
        "name": "Blinker",
        "pattern": [
            [1],
            [1],
            [1]
        ]
    },
    "block": {
        "name": "Block",
        "pattern": [
            [1, 1],
            [1, 1]
        ]
    },
    "beehive": {
        "name": "Beehive",
        "pattern": [
            [0, 1, 1, 0],
            [1, 0, 0, 1],
            [0, 1, 1, 0]
        ]
    },
    "loaf": {
        "name": "Loaf",
        "pattern": [
            [0, 1, 1, 0],
            [1, 0, 0, 1],
            [0, 1, 0, 1],
            [0, 0, 1, 0]
        ]
    },
    "glider_gun": {
        "name": "Gosper Glider Gun",
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
        "pattern": [
            [0,1,1],
            [1,1,0],
            [0,1,0]
        ]
    },
    "diehard": {
        "name": "Diehard",
        "pattern": [
            [0,0,0,0,0,0,1,0],
            [1,1,0,0,0,0,0,0],
            [0,1,0,0,0,1,1,1]
        ]
    },
    "acorn": {
        "name": "Acorn",
        "pattern": [
            [0,1,0,0,0,0,0],
            [0,0,0,1,0,0,0],
            [1,1,0,0,1,1,1]
        ]
    },
    "lwss": {
        "name": "Lightweight Spaceship (LWSS)",
        "pattern": [
            [0,1,1,1,1],
            [1,0,0,0,1],
            [0,0,0,0,1],
            [1,0,0,1,0]
        ]
    },
    "copperhead": {
        "name": "Copperhead",
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

PATTERN_DIRECTORY = Path(__file__).resolve().with_name("patterns")
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
    if not isinstance(name, str) or not name.strip():
        raise TypeError("Pattern 'name' must be non-empty text.")
    safe_pattern_filename(name)
    if not isinstance(pattern, list) or not pattern:
        raise TypeError("Pattern must be a non-empty two-dimensional list.")
    if not all(isinstance(row, list) and row for row in pattern):
        raise TypeError("Every pattern row must be a non-empty list.")

    width = len(pattern[0])
    if any(len(row) != width for row in pattern):
        raise TypeError("Pattern rows must all have the same length.")
    if any(
        not isinstance(cell, (int, bool)) or cell not in (0, 1)
        for row in pattern
        for cell in row
    ):
        raise TypeError("Pattern cells must be 0 or 1.")

    validated = dict(data)
    validated["name"] = name.strip()
    validated["pattern"] = [[int(cell) for cell in row] for row in pattern]
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


def refresh_pattern_cache() -> None:
    """Reload built-in and custom patterns into the shared cache."""
    refreshed = deepcopy(PATTERNS)
    if PATTERN_DIRECTORY.is_dir():
        for path in sorted(PATTERN_DIRECTORY.glob("*.json")):
            pattern_data = _read_pattern_file(path)
            if pattern_data is not None:
                refreshed[pattern_data["name"].casefold()] = pattern_data

    _PATTERN_CACHE.clear()
    _PATTERN_CACHE.update(refreshed)


def save_pattern(
    pattern: Sequence[Sequence[int]],
    name: str,
    description: str = "",
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Save a custom pattern and refresh the shared cache.

    Existing files are protected by default. Callers must explicitly pass
    ``overwrite=True`` to replace one.
    """
    filename = f"{safe_pattern_filename(name)}.json"
    pattern_data = _validate_pattern_data(
        {
            "name": name,
            "description": description,
            "pattern": [list(row) for row in pattern],
            "date_created": datetime.datetime.now().isoformat(),
        }
    )
    PATTERN_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = PATTERN_DIRECTORY / filename
    mode = "w" if overwrite else "x"
    try:
        with path.open(mode, encoding="utf-8") as pattern_file:
            json.dump(pattern_data, pattern_file, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise FileExistsError(
            f"A pattern named '{name}' already exists. Choose another name."
        ) from exc

    refresh_pattern_cache()
    return pattern_data


def delete_pattern(name: str) -> bool:
    """Delete a custom pattern and refresh the cache when it changes."""
    path = PATTERN_DIRECTORY / f"{safe_pattern_filename(name)}.json"
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    except OSError as exc:
        warnings.warn(f"Could not delete pattern '{name}': {exc}")
        return False

    refresh_pattern_cache()
    return True


def load_pattern(name: str) -> dict[str, Any] | None:
    """Load and validate one custom pattern without propagating file errors."""
    path = PATTERN_DIRECTORY / f"{safe_pattern_filename(name)}.json"
    return _read_pattern_file(path)


def get_all_patterns() -> dict[str, dict[str, Any]]:
    """Return the shared in-memory pattern cache without touching disk."""
    return _PATTERN_CACHE


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
