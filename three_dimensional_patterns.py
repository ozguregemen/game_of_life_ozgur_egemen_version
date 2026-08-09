"""Source-aware 3D pattern catalog, transforms, and safe custom storage."""

from __future__ import annotations

import datetime as dt
import itertools
import json
import re
import unicodedata
import warnings
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray

from app_paths import APPLICATION_PATHS
from three_dimensional_ca import BOUNDARY_MODES, BOUNDARY_WRAP, Volume3D, VolumeShape
from three_dimensional_modes import (
    ALL_RULES_3D,
    MODE_KEYS_3D,
    mode_for_rule,
    rule_state_count,
)

PATTERN_3D_SCHEMA = "cellular-automata-lab-pattern-3d"
PATTERN_3D_VERSION = 1
PATTERN_3D_DIRECTORY = APPLICATION_PATHS.patterns / "3d"
MAX_PATTERN_3D_VOXELS = 100_000
MAX_PATTERN_3D_COORDINATE = 1_024
GENERIC_MODE_3D = "*"
GENERIC_RULE_3D = "*"

PATTERN_3D_CATEGORY_LABELS = MappingProxyType(
    {
        "documented": "Documented Structures",
        "compact_seeds": "Compact Seeds",
        "shells": "Shells & Surfaces",
        "custom": "My 3D Patterns",
    }
)

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


def safe_pattern_3d_filename(name: str) -> str:
    """Return a portable filename stem for a user-owned 3D pattern."""

    if not isinstance(name, str):
        raise TypeError("3D pattern name must be text.")
    normalized = unicodedata.normalize("NFKC", name).strip()
    if not normalized:
        raise ValueError("3D pattern name cannot be empty.")
    stem = _INVALID_FILENAME_CHARACTERS.sub("_", normalized)
    stem = stem.replace("..", "_")
    stem = _WHITESPACE.sub("_", stem).strip(" ._")
    if not stem:
        raise ValueError("3D pattern name has no valid filename characters.")
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    return stem.casefold()


def _rotation_matrices() -> tuple[NDArray[np.int8], ...]:
    """Return the 24 proper rotations of a cube, identity first."""

    matrices: list[NDArray[np.int8]] = []
    for permutation in itertools.permutations(range(3)):
        for signs in itertools.product((-1, 1), repeat=3):
            matrix = np.zeros((3, 3), dtype=np.int8)
            for row, column in enumerate(permutation):
                matrix[row, column] = signs[row]
            if round(float(np.linalg.det(matrix))) == 1:
                matrices.append(matrix)
    matrices.sort(
        key=lambda matrix: (
            0 if np.array_equal(matrix, np.eye(3, dtype=np.int8)) else 1,
            tuple(int(value) for value in matrix.flat),
        )
    )
    return tuple(matrices)


CUBE_ROTATIONS_3D = _rotation_matrices()


@dataclass(frozen=True)
class PatternTransform3D:
    """One of 24 proper cube rotations with an optional X reflection."""

    rotation: int = 0
    mirrored: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.rotation, bool) or not isinstance(self.rotation, int):
            raise TypeError("3D pattern rotation must be an integer.")
        if not 0 <= self.rotation < len(CUBE_ROTATIONS_3D):
            raise ValueError("3D pattern rotation must be between 0 and 23.")
        if not isinstance(self.mirrored, bool):
            raise TypeError("3D pattern mirrored flag must be boolean.")

    def next_rotation(self) -> "PatternTransform3D":
        return PatternTransform3D((self.rotation + 1) % len(CUBE_ROTATIONS_3D), self.mirrored)

    def toggled_mirror(self) -> "PatternTransform3D":
        return PatternTransform3D(self.rotation, not self.mirrored)


@dataclass(frozen=True)
class Pattern3D:
    """A finite state-bearing voxel arrangement and its compatibility metadata."""

    key: str
    name: str
    rule_key: str
    offsets: tuple[tuple[int, int, int], ...]
    description: str
    source_url: str
    boundary: str = "fixed"
    mode_key: str = "spatial_life"
    states: tuple[int, ...] = ()
    category: str = "documented"
    builtin: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.name.strip() or not self.rule_key.strip():
            raise ValueError("3D pattern identity fields cannot be empty.")
        if self.mode_key not in (*MODE_KEYS_3D, GENERIC_MODE_3D):
            raise ValueError(f"Unknown 3D pattern mode: {self.mode_key!r}.")
        if self.rule_key != GENERIC_RULE_3D:
            if self.rule_key not in ALL_RULES_3D:
                raise ValueError(f"Unknown 3D pattern rule: {self.rule_key!r}.")
            if self.mode_key != GENERIC_MODE_3D and mode_for_rule(self.rule_key) != self.mode_key:
                raise ValueError("3D pattern rule does not belong to its mode.")
        if not self.offsets or len(set(self.offsets)) != len(self.offsets):
            raise ValueError("3D pattern offsets must be non-empty and unique.")
        if len(self.offsets) > MAX_PATTERN_3D_VOXELS:
            raise ValueError("3D pattern contains too many voxels.")
        if any(
            len(offset) != 3
            or any(isinstance(value, bool) or not isinstance(value, int) for value in offset)
            for offset in self.offsets
        ):
            raise TypeError("Every 3D pattern offset must contain integer z, y, and x.")
        if any(
            abs(value) > MAX_PATTERN_3D_COORDINATE
            for offset in self.offsets
            for value in offset
        ):
            raise ValueError("3D pattern coordinates exceed the supported range.")
        states = self.states or (1,) * len(self.offsets)
        if len(states) != len(self.offsets):
            raise ValueError("3D pattern states must match its voxel offsets.")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in states):
            raise TypeError("3D pattern voxel states must be positive integers.")
        if self.rule_key != GENERIC_RULE_3D:
            maximum_state = rule_state_count(ALL_RULES_3D[self.rule_key]) - 1
            if any(value > maximum_state for value in states):
                raise ValueError("3D pattern state exceeds its rule's state count.")
        if self.boundary not in BOUNDARY_MODES:
            raise ValueError(f"Unknown 3D pattern boundary: {self.boundary!r}.")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.category):
            raise ValueError("3D pattern category must be a lowercase identifier.")
        object.__setattr__(self, "states", tuple(states))

    @property
    def voxel_count(self) -> int:
        return len(self.offsets)

    def compatible_with(self, mode_key: str, rule_key: str) -> bool:
        """Return whether this pattern can be placed under the selected rule."""

        if mode_key not in MODE_KEYS_3D or rule_key not in ALL_RULES_3D:
            return False
        if self.mode_key not in (GENERIC_MODE_3D, mode_key):
            return False
        if self.rule_key not in (GENERIC_RULE_3D, rule_key):
            return False
        maximum_state = rule_state_count(ALL_RULES_3D[rule_key]) - 1
        return max(self.states) <= maximum_state

    def transformed_voxels(
        self,
        transform: PatternTransform3D | None = None,
    ) -> tuple[tuple[tuple[int, int, int], int], ...]:
        """Return offset/state pairs after a cube rotation and optional mirror."""

        selected = PatternTransform3D() if transform is None else transform
        matrix = CUBE_ROTATIONS_3D[selected.rotation]
        result: list[tuple[tuple[int, int, int], int]] = []
        for offset, state in zip(self.offsets, self.states, strict=True):
            vector = np.asarray(offset, dtype=np.int64)
            if selected.mirrored:
                vector[2] *= -1
            rotated = matrix @ vector
            result.append((tuple(int(value) for value in rotated), state))
        return tuple(result)

    def positioned_voxels(
        self,
        anchor: tuple[int, int, int],
        shape: VolumeShape,
        transform: PatternTransform3D | None = None,
    ) -> tuple[tuple[tuple[int, int, int], int], ...]:
        """Translate a complete transformed pattern or reject it without clipping."""

        if len(anchor) != 3:
            raise ValueError("3D pattern anchor must contain z, y, and x.")
        limits = np.asarray(shape, dtype=np.int64)
        translated: list[tuple[tuple[int, int, int], int]] = []
        for offset, state in self.transformed_voxels(transform):
            position = np.asarray(anchor, dtype=np.int64) + np.asarray(offset, dtype=np.int64)
            if np.any(position < 0) or np.any(position >= limits):
                raise ValueError(f"Pattern '{self.name}' does not fit in volume {shape}.")
            translated.append((tuple(int(value) for value in position), state))
        return tuple(translated)

    def centered_cells(self, shape: VolumeShape) -> NDArray[np.uint8]:
        """Return this pattern centered inside a new volume."""

        cells = np.zeros(shape, dtype=np.uint8)
        center = tuple(length // 2 for length in shape)
        for position, state in self.positioned_voxels(center, shape):
            cells[position] = state
        return cells


def _offsets_where(predicate: Any, radius: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (z, y, x)
        for z in range(-radius, radius + 1)
        for y in range(-radius, radius + 1)
        for x in range(-radius, radius + 1)
        if predicate(z, y, x)
    )


# Published as the common/evident 3D glider for Life 5766. The source lists
# coordinates as (i, j, k); the isotropic Moore neighborhood permits mapping
# them directly to the engine's canonical (z, y, x) axes.
BAYS_5766_GLIDER = Pattern3D(
    key="bays_5766_glider",
    name="Bays 5766 Glider",
    rule_key="bays_5766",
    offsets=(
        (0, 0, 0),
        (0, 0, 1),
        (0, 0, -1),
        (0, -1, 1),
        (0, -2, 0),
        (1, 0, 0),
        (1, 0, 1),
        (1, 0, -1),
        (1, -1, 1),
        (1, -2, 0),
    ),
    description=(
        "Carter Bays' common Life 5766 glider: ten voxels, period four, "
        "translating diagonally by one cell per period."
    ),
    source_url="https://www.ibiblio.org/e-notes/Life/Gliders.htm",
    boundary=BOUNDARY_WRAP,
)

AXIAL_CROSS_7 = Pattern3D(
    "axial_cross_7",
    "Axial Cross (7)",
    GENERIC_RULE_3D,
    ((0, 0, 0), (-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)),
    "A center voxel plus its six face neighbors; a compact baseline seed.",
    "",
    mode_key=GENERIC_MODE_3D,
    category="compact_seeds",
)

CORNER_CUBE_8 = Pattern3D(
    "corner_cube_8",
    "Solid Cube (8)",
    GENERIC_RULE_3D,
    tuple(itertools.product((-1, 0), repeat=3)),
    "A 2x2x2 solid cube for testing dense local interactions.",
    "",
    mode_key=GENERIC_MODE_3D,
    category="compact_seeds",
)

ASYMMETRIC_HOOK_6 = Pattern3D(
    "asymmetric_hook_6",
    "Asymmetric Hook (6)",
    GENERIC_RULE_3D,
    ((0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 1, 0), (1, 1, 0), (2, 1, 0)),
    "A chiral orientation marker designed for exploring all cube rotations.",
    "",
    mode_key=GENERIC_MODE_3D,
    category="compact_seeds",
)

HOLLOW_CUBE_26 = Pattern3D(
    "hollow_cube_26",
    "Hollow Cube Shell (26)",
    GENERIC_RULE_3D,
    _offsets_where(lambda z, y, x: max(abs(z), abs(y), abs(x)) == 1, 1),
    "The complete surface of a 3x3x3 cube with an empty center.",
    "",
    mode_key=GENERIC_MODE_3D,
    category="shells",
)

OCTAHEDRON_18 = Pattern3D(
    "octahedron_18",
    "Octahedron Shell (18)",
    GENERIC_RULE_3D,
    _offsets_where(lambda z, y, x: abs(z) + abs(y) + abs(x) == 2, 2),
    "A Manhattan-radius-two octahedral surface for anisotropy experiments.",
    "",
    mode_key=GENERIC_MODE_3D,
    category="shells",
)

SPHERE_33 = Pattern3D(
    "sphere_33",
    "Discrete Sphere (33)",
    GENERIC_RULE_3D,
    _offsets_where(lambda z, y, x: z * z + y * y + x * x <= 4, 2),
    "A compact Euclidean-radius-two ball for isotropic growth experiments.",
    "",
    mode_key=GENERIC_MODE_3D,
    category="shells",
)


BUILTIN_PATTERNS_3D = MappingProxyType(
    {
        pattern.key: pattern
        for pattern in (
            BAYS_5766_GLIDER,
            AXIAL_CROSS_7,
            CORNER_CUBE_8,
            ASYMMETRIC_HOOK_6,
            HOLLOW_CUBE_26,
            OCTAHEDRON_18,
            SPHERE_33,
        )
    }
)

_CUSTOM_PATTERN_CACHE_3D: dict[str, Pattern3D] = {}


def pattern_from_volume(
    volume: Volume3D,
    name: str,
    *,
    mode_key: str,
    rule_key: str,
    description: str = "",
) -> Pattern3D:
    """Crop occupied voxels from a volume into a centered custom pattern."""

    safe_pattern_3d_filename(name)
    if mode_key not in MODE_KEYS_3D or rule_key not in ALL_RULES_3D:
        raise ValueError("Custom 3D pattern mode or rule is unknown.")
    if mode_for_rule(rule_key) != mode_key:
        raise ValueError("Custom 3D pattern rule does not belong to its mode.")
    occupied = np.argwhere(volume.cells != 0)
    if not len(occupied):
        raise ValueError("There are no occupied voxels to save.")
    minimum = occupied.min(axis=0)
    maximum = occupied.max(axis=0)
    center = (minimum + maximum) // 2
    offsets = tuple(
        tuple(int(value) for value in coordinate - center)
        for coordinate in occupied
    )
    states = tuple(int(volume.cells[tuple(coordinate)]) for coordinate in occupied)
    return Pattern3D(
        key=f"custom:{safe_pattern_3d_filename(name)}",
        name=name.strip(),
        rule_key=rule_key,
        offsets=offsets,
        states=states,
        description=description.strip(),
        source_url="",
        boundary=volume.boundary,
        mode_key=mode_key,
        category="custom",
        builtin=False,
    )


def _pattern_document(pattern: Pattern3D) -> dict[str, Any]:
    return {
        "schema": PATTERN_3D_SCHEMA,
        "version": PATTERN_3D_VERSION,
        "name": pattern.name,
        "mode": pattern.mode_key,
        "rule": pattern.rule_key,
        "category": "custom",
        "description": pattern.description,
        "boundary": pattern.boundary,
        "voxels": [
            [*offset, state]
            for offset, state in zip(pattern.offsets, pattern.states, strict=True)
        ],
        "saved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


def _validate_pattern_document(value: Any) -> Pattern3D:
    if not isinstance(value, Mapping):
        raise TypeError("3D pattern JSON must contain an object.")
    version = value["version"]
    if (
        value["schema"] != PATTERN_3D_SCHEMA
        or isinstance(version, bool)
        or not isinstance(version, int)
        or version != PATTERN_3D_VERSION
    ):
        raise ValueError("Unsupported 3D pattern schema or version.")
    name = value["name"]
    mode_key = value["mode"]
    rule_key = value["rule"]
    voxels = value["voxels"]
    if not isinstance(name, str) or not name.strip():
        raise TypeError("3D pattern name must be non-empty text.")
    safe_pattern_3d_filename(name)
    if not isinstance(mode_key, str) or mode_key not in MODE_KEYS_3D:
        raise TypeError("3D pattern mode is invalid.")
    if not isinstance(rule_key, str) or rule_key not in ALL_RULES_3D:
        raise TypeError("3D pattern rule is invalid.")
    if mode_for_rule(rule_key) != mode_key:
        raise ValueError("3D pattern rule does not belong to its saved mode.")
    if not isinstance(voxels, list) or not voxels:
        raise TypeError("3D pattern voxels must be a non-empty list.")
    if len(voxels) > MAX_PATTERN_3D_VOXELS:
        raise ValueError("3D pattern contains too many voxels.")
    offsets: list[tuple[int, int, int]] = []
    states: list[int] = []
    for voxel in voxels:
        if (
            not isinstance(voxel, list)
            or len(voxel) != 4
            or any(isinstance(item, bool) or not isinstance(item, int) for item in voxel)
        ):
            raise TypeError("Every 3D pattern voxel must contain integer z, y, x, and state.")
        offsets.append((voxel[0], voxel[1], voxel[2]))
        states.append(voxel[3])
    description = value.get("description", "")
    boundary = value.get("boundary", "fixed")
    if not isinstance(description, str) or not isinstance(boundary, str):
        raise TypeError("3D pattern description and boundary must be text.")
    return Pattern3D(
        key=f"custom:{safe_pattern_3d_filename(name)}",
        name=name.strip(),
        rule_key=rule_key,
        offsets=tuple(offsets),
        states=tuple(states),
        description=description.strip(),
        source_url="",
        boundary=boundary,
        mode_key=mode_key,
        category="custom",
        builtin=False,
    )


def _read_pattern_3d_file(path: Path) -> Pattern3D | None:
    try:
        with path.open("r", encoding="utf-8") as pattern_file:
            return _validate_pattern_document(json.load(pattern_file))
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
        warnings.warn(f"Skipping invalid 3D pattern file '{path.name}': {exc}")
        return None


def refresh_pattern_3d_cache() -> None:
    """Read custom 3D patterns once at startup or after a storage mutation."""

    refreshed: dict[str, Pattern3D] = {}
    if PATTERN_3D_DIRECTORY.is_dir():
        for path in sorted(PATTERN_3D_DIRECTORY.glob("*.json")):
            pattern = _read_pattern_3d_file(path)
            if pattern is not None:
                refreshed[pattern.key] = pattern
    _CUSTOM_PATTERN_CACHE_3D.clear()
    _CUSTOM_PATTERN_CACHE_3D.update(refreshed)


def get_patterns_3d(
    *,
    mode_key: str | None = None,
    rule_key: str | None = None,
    category: str | None = None,
) -> tuple[Pattern3D, ...]:
    """Return the in-memory catalog filtered for one workspace context."""

    patterns = (*BUILTIN_PATTERNS_3D.values(), *_CUSTOM_PATTERN_CACHE_3D.values())
    if mode_key is not None:
        if mode_key not in MODE_KEYS_3D:
            raise ValueError(f"Unknown 3D mode: {mode_key}")
        patterns = tuple(
            pattern
            for pattern in patterns
            if pattern.mode_key in (GENERIC_MODE_3D, mode_key)
        )
    if rule_key is not None:
        if mode_key is None:
            raise ValueError("Filtering 3D patterns by rule also requires a mode.")
        patterns = tuple(
            pattern for pattern in patterns if pattern.compatible_with(mode_key, rule_key)
        )
    if category is not None and category != "all":
        patterns = tuple(pattern for pattern in patterns if pattern.category == category)
    return tuple(patterns)


def save_custom_pattern_3d(pattern: Pattern3D, *, overwrite: bool = False) -> Pattern3D:
    """Validate and atomically save a custom 3D pattern."""

    if pattern.builtin or pattern.category != "custom":
        raise ValueError("Only custom 3D patterns can be saved.")
    saved_pattern = _validate_pattern_document(_pattern_document(pattern))
    filename = f"{safe_pattern_3d_filename(saved_pattern.name)}.json"
    PATTERN_3D_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = PATTERN_3D_DIRECTORY / filename
    temporary = path.with_suffix(".tmp")
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"A 3D pattern named '{pattern.name}' already exists. Choose another name."
        )
    try:
        with temporary.open("w", encoding="utf-8") as pattern_file:
            json.dump(_pattern_document(saved_pattern), pattern_file, ensure_ascii=False, indent=2)
            pattern_file.flush()
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    refresh_pattern_3d_cache()
    return _CUSTOM_PATTERN_CACHE_3D[saved_pattern.key]


def delete_custom_pattern_3d(pattern_key: str) -> bool:
    """Delete one custom pattern and refresh the shared cache."""

    pattern = _CUSTOM_PATTERN_CACHE_3D.get(pattern_key)
    if pattern is None:
        return False
    path = PATTERN_3D_DIRECTORY / f"{safe_pattern_3d_filename(pattern.name)}.json"
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    refresh_pattern_3d_cache()
    return True


PATTERNS_3D = BUILTIN_PATTERNS_3D
refresh_pattern_3d_cache()
