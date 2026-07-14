"""Built-in, state-aware patterns for non-Life simulation modes."""

from __future__ import annotations

from typing import Any


MODE_PATTERNS: dict[str, dict[str, Any]] = {
    "immigration_split_block": {
        "name": "Split-Species Block",
        "mode": "immigration",
        "description": "A stable block divided evenly between both species.",
        "pattern": [[1, 1], [-1, -1]],
    },
    "immigration_blinker": {
        "name": "Two-Species Blinker",
        "mode": "immigration",
        "description": "A colored period-2 oscillator demonstrating inheritance.",
        "pattern": [[1], [-1], [1]],
    },
    "immigration_glider": {
        "name": "Two-Species Glider",
        "mode": "immigration",
        "description": "A Conway glider whose live cells begin with mixed species.",
        "pattern": [[0, 1, 0], [0, 0, -1], [1, -1, 1]],
    },
    "brain_period_3": {
        "name": "Period-3 Oscillator",
        "mode": "brians_brain",
        "description": "A compact documented Brian's Brain oscillator.",
        "source": "https://conwaylife.com/wiki/OCA:Brian%27s_Brain",
        "pattern": [
            [0, 0, 1, 0],
            [1, 2, 2, 0],
            [0, 2, 2, 1],
            [0, 1, 0, 0],
        ],
    },
    "brain_wickstretcher": {
        "name": "Two-Sided Wickstretcher",
        "mode": "brians_brain",
        "description": "A small seed that extends a wick in both directions.",
        "source": "https://conwaylife.com/wiki/OCA:Brian%27s_Brain",
        "pattern": [[1, 1, 1], [1, 0, 1], [0, 2, 0]],
    },
    "brain_parallel_wickstretcher": {
        "name": "Parallel Wickstretcher",
        "mode": "brians_brain",
        "description": "A four-cell seed producing a different extending wick.",
        "source": "https://conwaylife.com/wiki/OCA:Brian%27s_Brain",
        "pattern": [[1, 0, 0, 1], [1, 0, 0, 1]],
    },
    "langton_single_ant": {
        "name": "Single Ant on White",
        "mode": "langtons_ant",
        "description": "The classic blank-board, north-facing starting state.",
        "pattern": [[0]],
        "ant": {"row": 0, "col": 0, "direction": 0},
    },
    "langton_black_start": {
        "name": "Single Ant on Black",
        "mode": "langtons_ant",
        "description": "A north-facing ant beginning on a black cell.",
        "pattern": [[1]],
        "ant": {"row": 0, "col": 0, "direction": 0},
    },
    "langton_black_box": {
        "name": "Ant in Black Box",
        "mode": "langtons_ant",
        "description": "A centered ant enclosed by a five-cell black border.",
        "pattern": [
            [1, 1, 1, 1, 1],
            [1, 0, 0, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1],
        ],
        "ant": {"row": 2, "col": 2, "direction": 0},
    },
    "wireworld_signal_wire": {
        "name": "Signal on Straight Wire",
        "mode": "wireworld",
        "description": "An electron tail and head moving along a conductor.",
        "pattern": [[2, 1, 3, 3, 3, 3, 3, 3, 3, 3]],
    },
    "wireworld_diodes": {
        "name": "Forward and Reverse Diodes",
        "mode": "wireworld",
        "description": "Two standard diode layouts showing direction-sensitive flow.",
        "source": "https://cellpylib.org/wireworld.html",
        "pattern": [
            [0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 0, 0, 0, 0],
            [2, 1, 3, 3, 3, 3, 3, 0, 3, 3, 3, 3, 3, 3],
            [0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 0, 0, 0, 0],
            [2, 1, 3, 3, 3, 3, 0, 3, 3, 3, 3, 3, 3, 3],
            [0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 0, 0, 0, 0],
        ],
    },
    "wireworld_xor": {
        "name": "Clocked XOR Gate",
        "mode": "wireworld",
        "description": "Two clock inputs feeding a documented Wireworld XOR gate.",
        "source": "https://cellpylib.org/wireworld.html",
        "pattern": [
            [0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 3, 1, 2, 3, 3, 3, 3, 1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 3, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 3, 3, 3, 3, 2],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 0, 0, 0, 0],
            [0, 0, 0, 3, 3, 2, 1, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0],
            [0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ],
    },
}
