"""Versioned, validated JSON storage for sessions and 1D experiments."""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import unicodedata
import warnings
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from elementary_ca import BOUNDARY_MODES
from mode_registry import MODE_KEYS
from one_dimensional_ca import (
    FAMILY_ELEMENTARY,
    RULE_FAMILIES,
    SEED_WIDTH_COMPACT,
    SEED_WIDTH_MODES,
    RuleSpec,
)
from rules import RULES
from themes import THEMES
from three_dimensional_ca import (
    BOUNDARY_MODES as BOUNDARY_MODES_3D,
    DEFAULT_MAX_AXIS_LENGTH,
    DEFAULT_MAX_VOLUME_BYTES,
    SLICE_AXES,
)
from three_dimensional_modes import (
    ALL_RULE_KEYS_3D,
    ALL_RULES_3D,
    MODE_KEYS_3D,
    MODE_SPATIAL_LIFE,
    mode_for_rule,
    rule_state_count,
)
from three_dimensional_rules import DEFAULT_RULE_3D

SESSION_SCHEMA = "cellular-automata-lab/session"
PROFILE_SCHEMA = "cellular-automata-lab/elementary-profile"
DOCUMENT_VERSION = 1
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
VIEW_MODES_3D = ("all", "clip", "layer")

SESSION_DIRECTORY = Path(__file__).resolve().with_name("sessions")
PROFILE_DIRECTORY = SESSION_DIRECTORY / "eca_profiles"

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


class SessionStorageError(Exception):
    """Base class for readable session persistence failures."""


class DocumentValidationError(SessionStorageError, ValueError):
    """Raised when a JSON document does not match the current schema."""


def safe_storage_filename(name: str) -> str:
    """Convert a display name into a portable JSON filename stem."""
    if not isinstance(name, str):
        raise TypeError("Saved document name must be text.")
    normalized = unicodedata.normalize("NFKC", name).strip()
    if not normalized:
        raise ValueError("Saved document name cannot be empty.")
    stem = _INVALID_FILENAME_CHARACTERS.sub("_", normalized)
    stem = stem.replace("..", "_")
    stem = _WHITESPACE.sub("_", stem).strip(" ._")
    if not stem:
        raise ValueError("Saved document name has no valid filename characters.")
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    return stem.casefold()


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp suitable for JSON metadata."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DocumentValidationError(f"{label} must be a JSON object.")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DocumentValidationError(f"{label} must be a JSON array.")
    return value


def _integer(
    value: Any,
    label: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DocumentValidationError(f"{label} must be an integer.")
    if minimum is not None and value < minimum:
        raise DocumentValidationError(f"{label} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise DocumentValidationError(f"{label} must be at most {maximum}.")
    return value


def _number(
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DocumentValidationError(f"{label} must be a finite number.")
    result = float(value)
    if not math.isfinite(result):
        raise DocumentValidationError(f"{label} must be a finite number.")
    if minimum is not None and result < minimum:
        raise DocumentValidationError(f"{label} must be at least {minimum}.")
    return result


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise DocumentValidationError(f"{label} must be true or false.")
    return value


def _choice(value: Any, label: str, choices: Iterable[str]) -> str:
    choice_set = frozenset(choices)
    if not isinstance(value, str) or value not in choice_set:
        options = ", ".join(sorted(choice_set))
        raise DocumentValidationError(f"{label} must be one of: {options}.")
    return value


def _integer_choice(value: Any, label: str, choices: Iterable[int]) -> int:
    result = _integer(value, label)
    choice_set = frozenset(choices)
    if result not in choice_set:
        options = ", ".join(str(choice) for choice in sorted(choice_set))
        raise DocumentValidationError(f"{label} must be one of: {options}.")
    return result


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise DocumentValidationError(f"{label} must be text.")
    text = value.strip()
    if not text and not allow_empty:
        raise DocumentValidationError(f"{label} cannot be empty.")
    return text


def _pair(
    value: Any,
    label: str,
    converter: Callable[[Any, str], int],
) -> list[int]:
    items = _sequence(value, label)
    if len(items) != 2:
        raise DocumentValidationError(f"{label} must contain exactly two values.")
    return [
        converter(items[0], f"{label}[0]"),
        converter(items[1], f"{label}[1]"),
    ]


def _state_row(value: Any, label: str, states: int) -> list[int]:
    row = _sequence(value, label)
    if not row:
        raise DocumentValidationError(f"{label} cannot be empty.")
    if len(row) > 20_000:
        raise DocumentValidationError(f"{label} is too wide.")
    return [
        _integer(cell, f"{label}[{index}]", minimum=0, maximum=states - 1)
        for index, cell in enumerate(row)
    ]


def _rule_spec(value: Mapping[str, Any], label: str) -> RuleSpec:
    """Validate a generalized rule spec or upgrade a legacy ECA rule field."""
    raw_spec = value.get("rule_spec")
    if raw_spec is None:
        code = _integer(
            value.get("rule"),
            f"{label}.rule",
            minimum=0,
            maximum=255,
        )
        return RuleSpec(FAMILY_ELEMENTARY, code, 2, 1)
    source = _mapping(raw_spec, f"{label}.rule_spec")
    family = _choice(
        source.get("family"),
        f"{label}.rule_spec.family",
        RULE_FAMILIES,
    )
    code = _integer(source.get("code"), f"{label}.rule_spec.code", minimum=0)
    states = _integer(
        source.get("states"),
        f"{label}.rule_spec.states",
        minimum=2,
        maximum=4,
    )
    radius = _integer(
        source.get("radius"),
        f"{label}.rule_spec.radius",
        minimum=1,
        maximum=3,
    )
    try:
        return RuleSpec(family, code, states, radius)
    except (TypeError, ValueError) as exc:
        raise DocumentValidationError(f"{label}.rule_spec is invalid: {exc}") from exc


def _grid(
    value: Any,
    label: str,
    rows: int,
    cols: int,
    converter: Callable[[Any, str], int | float],
) -> list[list[int | float]]:
    source = _sequence(value, label)
    if len(source) != rows:
        raise DocumentValidationError(f"{label} must contain {rows} rows.")
    result: list[list[int | float]] = []
    for row_index, raw_row in enumerate(source):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if len(row) != cols:
            raise DocumentValidationError(
                f"{label}[{row_index}] must contain {cols} cells."
            )
        result.append(
            [
                converter(cell, f"{label}[{row_index}][{col_index}]")
                for col_index, cell in enumerate(row)
            ]
        )
    return result


def _validate_camera(
    value: Any,
    label: str,
    *,
    minimum_size: int,
    maximum_size: int,
) -> dict[str, Any]:
    camera = _mapping(value, label)
    return {
        "cell_size": _integer(
            camera.get("cell_size"),
            f"{label}.cell_size",
            minimum=minimum_size,
            maximum=maximum_size,
        ),
        "offset": _pair(camera.get("offset"), f"{label}.offset", _integer),
    }


def _validate_elementary_workspace(value: Any) -> dict[str, Any]:
    workspace = _mapping(value, "workspaces.1d")
    spec = _rule_spec(workspace, "workspaces.1d")
    background = _integer(
        workspace.get("background"),
        "workspaces.1d.background",
        minimum=0,
        maximum=spec.states - 1,
    )
    rows_source = _sequence(workspace.get("rows"), "workspaces.1d.rows")
    if not rows_source or len(rows_source) > 512:
        raise DocumentValidationError(
            "workspaces.1d.rows must contain between 1 and 512 rows."
        )
    rows = [
        _state_row(row, f"workspaces.1d.rows[{index}]", spec.states)
        for index, row in enumerate(rows_source)
    ]
    row_backgrounds_source = _sequence(
        workspace.get(
            "row_backgrounds",
            [0] * max(0, len(rows) - 1) + [background],
        ),
        "workspaces.1d.row_backgrounds",
    )
    if len(row_backgrounds_source) != len(rows):
        raise DocumentValidationError(
            "workspaces.1d.row_backgrounds must match the diagram row count."
        )
    row_backgrounds = [
        _integer(
            state,
            f"workspaces.1d.row_backgrounds[{index}]",
            minimum=0,
            maximum=spec.states - 1,
        )
        for index, state in enumerate(row_backgrounds_source)
    ]
    seed = _state_row(workspace.get("seed"), "workspaces.1d.seed", spec.states)
    previous_row = _state_row(
        workspace.get("previous_row", [0] * len(rows[-1])),
        "workspaces.1d.previous_row",
        spec.states,
    )
    if len(previous_row) != len(rows[-1]):
        raise DocumentValidationError(
            "workspaces.1d.previous_row must match the latest row width."
        )

    comparison_source = workspace.get("comparison", {})
    comparison = _mapping(comparison_source, "workspaces.1d.comparison")
    comparison_rows_source = _sequence(
        comparison.get("rows", rows),
        "workspaces.1d.comparison.rows",
    )
    if not comparison_rows_source or len(comparison_rows_source) > 512:
        raise DocumentValidationError(
            "workspaces.1d.comparison.rows must contain between 1 and 512 rows."
        )
    comparison_rows = [
        _state_row(
            row,
            f"workspaces.1d.comparison.rows[{index}]",
            spec.states,
        )
        for index, row in enumerate(comparison_rows_source)
    ]
    if len(comparison_rows) != len(rows) or any(
        len(primary) != len(secondary)
        for primary, secondary in zip(rows, comparison_rows)
    ):
        raise DocumentValidationError(
            "workspaces.1d comparison rows must match the primary diagram."
        )
    comparison_previous = _state_row(
        comparison.get("previous_row", [0] * len(comparison_rows[-1])),
        "workspaces.1d.comparison.previous_row",
        spec.states,
    )
    if len(comparison_previous) != len(comparison_rows[-1]):
        raise DocumentValidationError(
            "workspaces.1d.comparison.previous_row must match the latest row width."
        )
    comparison_background = _integer(
        comparison.get("background", background),
        "workspaces.1d.comparison.background",
        minimum=0,
        maximum=spec.states - 1,
    )
    comparison_backgrounds_source = _sequence(
        comparison.get(
            "row_backgrounds",
            [0] * max(0, len(comparison_rows) - 1)
            + [comparison_background],
        ),
        "workspaces.1d.comparison.row_backgrounds",
    )
    if len(comparison_backgrounds_source) != len(comparison_rows):
        raise DocumentValidationError(
            "workspaces.1d.comparison.row_backgrounds must match the diagram row count."
        )
    comparison_row_backgrounds = [
        _integer(
            state,
            f"workspaces.1d.comparison.row_backgrounds[{index}]",
            minimum=0,
            maximum=spec.states - 1,
        )
        for index, state in enumerate(comparison_backgrounds_source)
    ]
    return {
        "rule": spec.code,
        "rule_spec": spec.as_dict(),
        "boundary": _choice(
            workspace.get("boundary"),
            "workspaces.1d.boundary",
            BOUNDARY_MODES,
        ),
        "background": background,
        "previous_background": _integer(
            workspace.get("previous_background", 0),
            "workspaces.1d.previous_background",
            minimum=0,
            maximum=spec.states - 1,
        ),
        "rule_change_reset": _boolean(
            workspace.get("rule_change_reset"),
            "workspaces.1d.rule_change_reset",
        ),
        "seed_width_mode": _choice(
            workspace.get("seed_width_mode", SEED_WIDTH_COMPACT),
            "workspaces.1d.seed_width_mode",
            SEED_WIDTH_MODES,
        ),
        "seed": seed,
        "rows": rows,
        "row_backgrounds": row_backgrounds,
        "previous_row": previous_row,
        "comparison": {
            "enabled": _boolean(
                comparison.get("enabled", False),
                "workspaces.1d.comparison.enabled",
            ),
            "rule": _integer(
                comparison.get("rule", min(90, spec.max_code)),
                "workspaces.1d.comparison.rule",
                minimum=0,
                maximum=spec.max_code,
            ),
            "rows": comparison_rows,
            "row_backgrounds": comparison_row_backgrounds,
            "previous_row": comparison_previous,
            "background": comparison_background,
            "previous_background": _integer(
                comparison.get("previous_background", 0),
                "workspaces.1d.comparison.previous_background",
                minimum=0,
                maximum=spec.states - 1,
            ),
        },
        "generation": _integer(
            workspace.get("generation"),
            "workspaces.1d.generation",
            minimum=0,
        ),
        "camera": _validate_camera(
            workspace.get("camera"),
            "workspaces.1d.camera",
            minimum_size=2,
            maximum_size=16,
        ),
    }


def _validate_2d_workspace(value: Any) -> dict[str, Any]:
    workspace = _mapping(value, "workspaces.2d")
    shape = _pair(
        workspace.get("shape"),
        "workspaces.2d.shape",
        lambda item, label: _integer(item, label, minimum=1, maximum=2_000),
    )
    rows, cols = shape
    states = _mapping(workspace.get("states"), "workspaces.2d.states")

    life = _mapping(states.get("life"), "workspaces.2d.states.life")
    immigration = _mapping(
        states.get("immigration"),
        "workspaces.2d.states.immigration",
    )
    brain = _mapping(
        states.get("brians_brain"),
        "workspaces.2d.states.brians_brain",
    )
    ant = _mapping(
        states.get("langtons_ant"),
        "workspaces.2d.states.langtons_ant",
    )
    wireworld = _mapping(
        states.get("wireworld"),
        "workspaces.2d.states.wireworld",
    )
    cyclic = _mapping(
        states.get("cyclic_automaton"),
        "workspaces.2d.states.cyclic_automaton",
    )

    nonnegative_int = lambda item, label: _integer(item, label, minimum=0)
    signed_int = lambda item, label: _integer(item, label)
    binary_int = lambda item, label: _integer(
        item,
        label,
        minimum=0,
        maximum=1,
    )
    brain_int = lambda item, label: _integer(
        item,
        label,
        minimum=0,
        maximum=2,
    )
    wire_int = lambda item, label: _integer(
        item,
        label,
        minimum=0,
        maximum=3,
    )
    cyclic_int = lambda item, label: _integer(
        item,
        label,
        minimum=0,
        maximum=7,
    )
    activity_number = lambda item, label: _number(item, label, minimum=0.0)

    ant_state = _mapping(ant.get("ant"), "workspaces.2d.states.langtons_ant.ant")
    ant_row = _integer(
        ant_state.get("row"),
        "workspaces.2d.states.langtons_ant.ant.row",
        minimum=0,
        maximum=rows - 1,
    )
    ant_col = _integer(
        ant_state.get("col"),
        "workspaces.2d.states.langtons_ant.ant.col",
        minimum=0,
        maximum=cols - 1,
    )

    return {
        "shape": shape,
        "camera": _validate_camera(
            workspace.get("camera"),
            "workspaces.2d.camera",
            minimum_size=5,
            maximum_size=40,
        ),
        "states": {
            "life": {
                "rule": _choice(
                    life.get("rule"),
                    "workspaces.2d.states.life.rule",
                    RULES,
                ),
                "grid": _grid(
                    life.get("grid"),
                    "workspaces.2d.states.life.grid",
                    rows,
                    cols,
                    nonnegative_int,
                ),
                "trail": _grid(
                    life.get("trail"),
                    "workspaces.2d.states.life.trail",
                    rows,
                    cols,
                    nonnegative_int,
                ),
                "activity": _grid(
                    life.get("activity"),
                    "workspaces.2d.states.life.activity",
                    rows,
                    cols,
                    activity_number,
                ),
                "generation": _integer(
                    life.get("generation"),
                    "workspaces.2d.states.life.generation",
                    minimum=0,
                ),
            },
            "immigration": {
                "grid": _grid(
                    immigration.get("grid"),
                    "workspaces.2d.states.immigration.grid",
                    rows,
                    cols,
                    signed_int,
                ),
                "generation": _integer(
                    immigration.get("generation"),
                    "workspaces.2d.states.immigration.generation",
                    minimum=0,
                ),
                "active_species": _integer_choice(
                    immigration.get("active_species"),
                    "workspaces.2d.states.immigration.active_species",
                    (-1, 1),
                ),
            },
            "brians_brain": {
                "grid": _grid(
                    brain.get("grid"),
                    "workspaces.2d.states.brians_brain.grid",
                    rows,
                    cols,
                    brain_int,
                ),
                "generation": _integer(
                    brain.get("generation"),
                    "workspaces.2d.states.brians_brain.generation",
                    minimum=0,
                ),
            },
            "langtons_ant": {
                "grid": _grid(
                    ant.get("grid"),
                    "workspaces.2d.states.langtons_ant.grid",
                    rows,
                    cols,
                    binary_int,
                ),
                "generation": _integer(
                    ant.get("generation"),
                    "workspaces.2d.states.langtons_ant.generation",
                    minimum=0,
                ),
                "ant": {
                    "row": ant_row,
                    "col": ant_col,
                    "direction": _integer(
                        ant_state.get("direction"),
                        "workspaces.2d.states.langtons_ant.ant.direction",
                        minimum=0,
                        maximum=3,
                    ),
                    "active": _boolean(
                        ant_state.get("active"),
                        "workspaces.2d.states.langtons_ant.ant.active",
                    ),
                },
            },
            "wireworld": {
                "grid": _grid(
                    wireworld.get("grid"),
                    "workspaces.2d.states.wireworld.grid",
                    rows,
                    cols,
                    wire_int,
                ),
                "generation": _integer(
                    wireworld.get("generation"),
                    "workspaces.2d.states.wireworld.generation",
                    minimum=0,
                ),
                "brush": _integer(
                    wireworld.get("brush"),
                    "workspaces.2d.states.wireworld.brush",
                    minimum=1,
                    maximum=3,
                ),
            },
            "cyclic_automaton": {
                "grid": _grid(
                    cyclic.get("grid"),
                    "workspaces.2d.states.cyclic_automaton.grid",
                    rows,
                    cols,
                    cyclic_int,
                ),
                "generation": _integer(
                    cyclic.get("generation"),
                    "workspaces.2d.states.cyclic_automaton.generation",
                    minimum=0,
                ),
                "brush": _integer(
                    cyclic.get("brush"),
                    "workspaces.2d.states.cyclic_automaton.brush",
                    minimum=0,
                    maximum=7,
                ),
                "threshold": _integer(
                    cyclic.get("threshold"),
                    "workspaces.2d.states.cyclic_automaton.threshold",
                    minimum=1,
                    maximum=8,
                ),
            },
        },
    }


def _default_3d_workspace() -> dict[str, Any]:
    """Return the empty 3D state used when upgrading a legacy session."""
    depth, rows, columns = (48, 48, 48)
    return {
        "shape": [depth, rows, columns],
        "cells": [
            [[0 for _ in range(columns)] for _ in range(rows)]
            for _ in range(depth)
        ],
        "mode": MODE_SPATIAL_LIFE,
        "rule": DEFAULT_RULE_3D.key,
        "state_count": 2,
        "boundary": "fixed",
        "generation": 0,
        "slice": {"axis": "z", "index": depth // 2},
        "camera": _default_3d_orbit_camera((depth, rows, columns)),
        "view": {"mode": "all", "keep_lower": True, "opacity": 1.0},
    }


def _default_3d_orbit_camera(shape: Sequence[int]) -> dict[str, Any]:
    """Return the centered isometric camera used for new and legacy sessions."""
    diagonal = math.sqrt(sum(float(length) ** 2 for length in shape))
    return {
        "target": [0.0, 0.0, 0.0],
        "yaw": math.radians(45.0),
        "pitch": math.radians(28.0),
        "distance": max(8.0, diagonal * 1.35),
        "fov_y": 45.0,
    }


def _validate_3d_orbit_camera(
    value: Any,
    label: str,
    shape: Sequence[int],
) -> dict[str, Any]:
    """Validate the perspective camera and upgrade the old slice camera."""
    camera = _mapping(value, label)
    if "target" not in camera:
        _validate_camera(camera, label, minimum_size=2, maximum_size=24)
        return _default_3d_orbit_camera(shape)

    target_source = _sequence(camera.get("target"), f"{label}.target")
    if len(target_source) != 3:
        raise DocumentValidationError(f"{label}.target must contain three values.")
    target = [
        _number(item, f"{label}.target[{index}]")
        for index, item in enumerate(target_source)
    ]
    yaw = _number(camera.get("yaw"), f"{label}.yaw")
    pitch = _number(camera.get("pitch"), f"{label}.pitch")
    distance = _number(camera.get("distance"), f"{label}.distance", minimum=2.0)
    fov_y = _number(camera.get("fov_y", 45.0), f"{label}.fov_y", minimum=1.0)
    if not math.radians(-85.0) <= pitch <= math.radians(85.0):
        raise DocumentValidationError(f"{label}.pitch is outside the orbit limit.")
    if distance > 10_000.0:
        raise DocumentValidationError(f"{label}.distance is too large.")
    if fov_y >= 179.0:
        raise DocumentValidationError(f"{label}.fov_y must be below 179 degrees.")
    return {
        "target": target,
        "yaw": yaw,
        "pitch": pitch,
        "distance": distance,
        "fov_y": fov_y,
    }


def _validate_3d_workspace(value: Any) -> dict[str, Any]:
    """Validate a bounded multi-mode volume plus its slice and camera."""
    workspace = _mapping(value, "workspaces.3d")
    raw_shape = _sequence(workspace.get("shape"), "workspaces.3d.shape")
    if len(raw_shape) != 3:
        raise DocumentValidationError(
            "workspaces.3d.shape must contain depth, rows, and columns."
        )
    shape = [
        _integer(
            item,
            f"workspaces.3d.shape[{index}]",
            minimum=1,
            maximum=DEFAULT_MAX_AXIS_LENGTH,
        )
        for index, item in enumerate(raw_shape)
    ]
    depth, rows, columns = shape
    if depth * rows * columns > DEFAULT_MAX_VOLUME_BYTES:
        raise DocumentValidationError(
            "workspaces.3d volume exceeds the dense uint8 memory limit."
        )

    rule_key = _choice(
        workspace.get("rule"),
        "workspaces.3d.rule",
        ALL_RULE_KEYS_3D,
    )
    inferred_mode = mode_for_rule(rule_key)
    mode_key = _choice(
        workspace.get("mode", inferred_mode),
        "workspaces.3d.mode",
        MODE_KEYS_3D,
    )
    if mode_key != inferred_mode:
        raise DocumentValidationError(
            "workspaces.3d.rule does not belong to workspaces.3d.mode."
        )
    expected_state_count = rule_state_count(ALL_RULES_3D[rule_key])
    state_count = _integer(
        workspace.get("state_count", expected_state_count),
        "workspaces.3d.state_count",
        minimum=2,
        maximum=256,
    )
    if state_count != expected_state_count:
        raise DocumentValidationError(
            "workspaces.3d.state_count does not match the selected rule."
        )

    raw_planes = _sequence(workspace.get("cells"), "workspaces.3d.cells")
    if len(raw_planes) != depth:
        raise DocumentValidationError(
            f"workspaces.3d.cells must contain {depth} depth planes."
        )
    cells: list[list[list[int]]] = []
    for z, raw_plane in enumerate(raw_planes):
        plane = _sequence(raw_plane, f"workspaces.3d.cells[{z}]")
        if len(plane) != rows:
            raise DocumentValidationError(
                f"workspaces.3d.cells[{z}] must contain {rows} rows."
            )
        normalized_plane: list[list[int]] = []
        for y, raw_row in enumerate(plane):
            row = _sequence(raw_row, f"workspaces.3d.cells[{z}][{y}]")
            if len(row) != columns:
                raise DocumentValidationError(
                    f"workspaces.3d.cells[{z}][{y}] must contain {columns} cells."
                )
            normalized_plane.append(
                [
                    _integer(
                        cell,
                        f"workspaces.3d.cells[{z}][{y}][{x}]",
                        minimum=0,
                        maximum=state_count - 1,
                    )
                    for x, cell in enumerate(row)
                ]
            )
        cells.append(normalized_plane)

    slice_state = _mapping(workspace.get("slice"), "workspaces.3d.slice")
    view_state = _mapping(
        workspace.get(
            "view",
            {"mode": "all", "keep_lower": True, "opacity": 1.0},
        ),
        "workspaces.3d.view",
    )
    axis = _choice(
        slice_state.get("axis"),
        "workspaces.3d.slice.axis",
        SLICE_AXES,
    )
    axis_length = shape[SLICE_AXES.index(axis)]
    opacity = _number(
        view_state.get("opacity"),
        "workspaces.3d.view.opacity",
        minimum=0.05,
    )
    if opacity > 1.0:
        raise DocumentValidationError(
            "workspaces.3d.view.opacity must be at most 1.0."
        )
    return {
        "shape": shape,
        "cells": cells,
        "mode": mode_key,
        "rule": rule_key,
        "state_count": state_count,
        "boundary": _choice(
            workspace.get("boundary"),
            "workspaces.3d.boundary",
            BOUNDARY_MODES_3D,
        ),
        "generation": _integer(
            workspace.get("generation"),
            "workspaces.3d.generation",
            minimum=0,
        ),
        "slice": {
            "axis": axis,
            "index": _integer(
                slice_state.get("index"),
                "workspaces.3d.slice.index",
                minimum=0,
                maximum=axis_length - 1,
            ),
        },
        "camera": _validate_3d_orbit_camera(
            workspace.get("camera"),
            "workspaces.3d.camera",
            shape,
        ),
        "view": {
            "mode": _choice(
                view_state.get("mode"),
                "workspaces.3d.view.mode",
                VIEW_MODES_3D,
            ),
            "keep_lower": _boolean(
                view_state.get("keep_lower"),
                "workspaces.3d.view.keep_lower",
            ),
            "opacity": opacity,
        },
    }


def validate_session_document(value: Any) -> dict[str, Any]:
    """Validate and normalize a full application-session document."""
    document = _mapping(value, "session")
    if document.get("schema") != SESSION_SCHEMA:
        raise DocumentValidationError("File is not a Cellular Automata Lab session.")
    if document.get("version") != DOCUMENT_VERSION:
        raise DocumentValidationError(
            f"Unsupported session version: {document.get('version')!r}."
        )
    application = _mapping(document.get("application"), "application")
    display = _mapping(application.get("display"), "application.display")
    workspaces = _mapping(document.get("workspaces"), "workspaces")
    return {
        "schema": SESSION_SCHEMA,
        "version": DOCUMENT_VERSION,
        "name": _text(document.get("name"), "name"),
        "saved_at": _text(document.get("saved_at"), "saved_at"),
        "application": {
            "dimension": _choice(
                application.get("dimension"),
                "application.dimension",
                ("1d", "2d", "3d"),
            ),
            "mode": _choice(
                application.get("mode"),
                "application.mode",
                MODE_KEYS,
            ),
            "theme": _choice(
                application.get("theme"),
                "application.theme",
                THEMES,
            ),
            "speed": _integer(
                application.get("speed"),
                "application.speed",
                minimum=1,
                maximum=60,
            ),
            "display": {
                "grid": _boolean(display.get("grid"), "application.display.grid"),
                "heatmap": _boolean(
                    display.get("heatmap"),
                    "application.display.heatmap",
                ),
                "ages": _boolean(display.get("ages"), "application.display.ages"),
                "coordinates": _boolean(
                    display.get("coordinates"),
                    "application.display.coordinates",
                ),
                "quadrants": _boolean(
                    display.get("quadrants"),
                    "application.display.quadrants",
                ),
            },
        },
        "workspaces": {
            "1d": _validate_elementary_workspace(workspaces.get("1d")),
            "2d": _validate_2d_workspace(workspaces.get("2d")),
            "3d": _validate_3d_workspace(
                workspaces.get("3d", _default_3d_workspace())
            ),
        },
    }


def validate_profile_document(value: Any) -> dict[str, Any]:
    """Validate and normalize a reusable generalized 1D experiment profile."""
    document = _mapping(value, "profile")
    if document.get("schema") != PROFILE_SCHEMA:
        raise DocumentValidationError("File is not a 1D experiment profile.")
    if document.get("version") != DOCUMENT_VERSION:
        raise DocumentValidationError(
            f"Unsupported profile version: {document.get('version')!r}."
        )
    experiment = _mapping(document.get("experiment"), "experiment")
    spec = _rule_spec(experiment, "experiment")
    comparison_source = experiment.get("comparison", {})
    comparison = _mapping(comparison_source, "experiment.comparison")
    return {
        "schema": PROFILE_SCHEMA,
        "version": DOCUMENT_VERSION,
        "name": _text(document.get("name"), "name"),
        "saved_at": _text(document.get("saved_at"), "saved_at"),
        "experiment": {
            "rule": spec.code,
            "rule_spec": spec.as_dict(),
            "boundary": _choice(
                experiment.get("boundary"),
                "experiment.boundary",
                BOUNDARY_MODES,
            ),
            "background": _integer(
                experiment.get("background"),
                "experiment.background",
                minimum=0,
                maximum=spec.states - 1,
            ),
            "rule_change_reset": _boolean(
                experiment.get("rule_change_reset"),
                "experiment.rule_change_reset",
            ),
            "seed_width_mode": _choice(
                experiment.get("seed_width_mode", SEED_WIDTH_COMPACT),
                "experiment.seed_width_mode",
                SEED_WIDTH_MODES,
            ),
            "seed": _state_row(
                experiment.get("seed"),
                "experiment.seed",
                spec.states,
            ),
            "comparison": {
                "enabled": _boolean(
                    comparison.get("enabled", False),
                    "experiment.comparison.enabled",
                ),
                "rule": _integer(
                    comparison.get("rule", min(90, spec.max_code)),
                    "experiment.comparison.rule",
                    minimum=0,
                    maximum=spec.max_code,
                ),
            },
        },
    }


def _document_path(directory: Path, identifier: str) -> Path:
    return directory / f"{safe_storage_filename(identifier)}.json"


def _write_document(
    directory: Path,
    identifier: str,
    document: Mapping[str, Any],
    *,
    overwrite: bool,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = _document_path(directory, identifier)
    if path.exists() and not overwrite:
        raise FileExistsError(f"'{identifier}' already exists.")
    temporary_path = path.with_suffix(".json.tmp")
    try:
        temporary_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as exc:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise SessionStorageError(f"Could not write '{path.name}': {exc}") from exc
    return path


def _read_json(path: Path) -> Any:
    try:
        if path.stat().st_size > MAX_DOCUMENT_BYTES:
            raise SessionStorageError(f"'{path.name}' is too large to load safely.")
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SessionStorageError(f"Saved file not found: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise SessionStorageError(f"'{path.name}' contains invalid JSON.") from exc
    except OSError as exc:
        raise SessionStorageError(f"Could not read '{path.name}': {exc}") from exc


def save_session(
    document: Mapping[str, Any],
    identifier: str | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and atomically save a complete session."""
    normalized = validate_session_document(document)
    return _write_document(
        SESSION_DIRECTORY,
        identifier or normalized["name"],
        normalized,
        overwrite=overwrite,
    )


def load_session(identifier: str) -> dict[str, Any]:
    """Read and validate one complete session."""
    return validate_session_document(
        _read_json(_document_path(SESSION_DIRECTORY, identifier))
    )


def save_profile(
    document: Mapping[str, Any],
    identifier: str | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and atomically save a generalized 1D experiment profile."""
    normalized = validate_profile_document(document)
    return _write_document(
        PROFILE_DIRECTORY,
        identifier or normalized["name"],
        normalized,
        overwrite=overwrite,
    )


def load_profile(identifier: str) -> dict[str, Any]:
    """Read and validate one generalized 1D experiment profile."""
    return validate_profile_document(
        _read_json(_document_path(PROFILE_DIRECTORY, identifier))
    )


def _list_documents(
    directory: Path,
    validator: Callable[[Any], dict[str, Any]],
) -> list[dict[str, str]]:
    if not directory.exists():
        return []
    documents: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            document = validator(_read_json(path))
        except (DocumentValidationError, SessionStorageError) as exc:
            warnings.warn(f"Skipping '{path.name}': {exc}", RuntimeWarning, stacklevel=2)
            continue
        documents.append(
            {
                "identifier": path.stem,
                "name": document["name"],
                "saved_at": document["saved_at"],
            }
        )
    documents.sort(key=lambda item: item["saved_at"], reverse=True)
    return documents


def list_sessions() -> list[dict[str, str]]:
    """Return readable metadata for all valid saved sessions."""
    return _list_documents(SESSION_DIRECTORY, validate_session_document)


def list_profiles() -> list[dict[str, str]]:
    """Return readable metadata for all valid 1D experiment profiles."""
    return _list_documents(PROFILE_DIRECTORY, validate_profile_document)
