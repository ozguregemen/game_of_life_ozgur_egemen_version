"""Built-in, state-aware patterns for non-Life simulation modes."""

from __future__ import annotations

import math
from typing import Any


CYCLIC_STATE_COUNT = 8
WIREWORLD_ASCII_STATES = {".": 0, "H": 1, "T": 2, "C": 3}


def _wireworld_ascii(*rows: str) -> list[list[int]]:
    """Decode a compact Wireworld diagram (head, tail, conductor, empty)."""
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Wireworld ASCII diagrams must be non-empty and rectangular.")
    try:
        return [[WIREWORLD_ASCII_STATES[cell] for cell in row] for row in rows]
    except KeyError as exc:
        raise ValueError(f"Unknown Wireworld ASCII state: {exc.args[0]}") from exc


def _cyclic_phase_gradient(size: int = 8) -> list[list[int]]:
    """Build a diagonal phase gradient across every cyclic state."""
    return [
        [(row + col) % CYCLIC_STATE_COUNT for col in range(size)]
        for row in range(size)
    ]


def _cyclic_concentric_rings(size: int = 9) -> list[list[int]]:
    """Build nested successor-color fronts."""
    return [
        [min(row, col, size - 1 - row, size - 1 - col) for col in range(size)]
        for row in range(size)
    ]


def _cyclic_color_wheel(size: int = 11) -> list[list[int]]:
    """Build eight angular phase sectors meeting at a spiral core."""
    center = (size - 1) / 2
    return [
        [
            int(
                (
                    math.atan2(row - center, col - center) + math.pi
                )
                / (2 * math.pi)
                * CYCLIC_STATE_COUNT
            )
            % CYCLIC_STATE_COUNT
            for col in range(size)
        ]
        for row in range(size)
    ]


MODE_PATTERNS: dict[str, dict[str, Any]] = {
    "immigration_split_block": {
        "name": "Split-Species Block",
        "mode": "immigration",
        "category": "still_lifes",
        "description": "A stable block divided evenly between both species.",
        "pattern": [[1, 1], [-1, -1]],
    },
    "immigration_beehive": {
        "name": "Two-Species Beehive",
        "mode": "immigration",
        "category": "still_lifes",
        "description": "A stable beehive whose surviving cells retain both species.",
        "pattern": [[0, 1, -1, 0], [1, 0, 0, -1], [0, -1, 1, 0]],
    },
    "immigration_loaf": {
        "name": "Two-Species Loaf",
        "mode": "immigration",
        "category": "still_lifes",
        "description": "A seven-cell stable form split between both species.",
        "pattern": [
            [0, 1, -1, 0],
            [1, 0, 0, -1],
            [0, -1, 0, 1],
            [0, 0, -1, 0],
        ],
    },
    "immigration_blinker": {
        "name": "Two-Species Blinker",
        "mode": "immigration",
        "category": "oscillators",
        "description": "A colored period-2 oscillator demonstrating inheritance.",
        "pattern": [[1], [-1], [1]],
    },
    "immigration_toad": {
        "name": "Two-Species Toad",
        "mode": "immigration",
        "category": "oscillators",
        "description": "A period-2 toad with competing colors across its phases.",
        "pattern": [[0, 1, -1, 1], [-1, 1, -1, 0]],
    },
    "immigration_beacon": {
        "name": "Two-Species Beacon",
        "mode": "immigration",
        "category": "oscillators",
        "description": "A period-2 beacon divided between species A and B.",
        "pattern": [
            [1, -1, 0, 0],
            [-1, 0, 0, 0],
            [0, 0, 0, 1],
            [0, 0, -1, 1],
        ],
    },
    "immigration_glider": {
        "name": "Two-Species Glider",
        "mode": "immigration",
        "category": "spaceships",
        "description": "A Conway glider whose live cells begin with mixed species.",
        "pattern": [[0, 1, 0], [0, 0, -1], [1, -1, 1]],
    },
    "immigration_lwss": {
        "name": "Two-Species LWSS",
        "mode": "immigration",
        "category": "spaceships",
        "description": "A lightweight spaceship seeded with alternating species.",
        "pattern": [
            [0, 1, -1, 1, -1],
            [-1, 0, 0, 0, 1],
            [0, 0, 0, 0, -1],
            [1, 0, 0, -1, 0],
        ],
    },
    "immigration_r_pentomino": {
        "name": "Competitive R-Pentomino",
        "mode": "immigration",
        "category": "competition",
        "description": "A long-lived R-pentomino seed with mixed ancestry.",
        "pattern": [[0, 1, -1], [-1, 1, 0], [0, -1, 0]],
    },
    "immigration_acorn": {
        "name": "Competitive Acorn",
        "mode": "immigration",
        "category": "competition",
        "description": "A small mixed-species seed with a long chaotic evolution.",
        "pattern": [
            [0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, -1, 0, 0, 0],
            [1, -1, 0, 0, 1, -1, 1],
        ],
    },
    "brain_period_3": {
        "name": "Period-3 Oscillator",
        "mode": "brians_brain",
        "category": "oscillators",
        "description": "A compact documented Brian's Brain oscillator.",
        "source": "https://conwaylife.com/wiki/OCA:Brian%27s_Brain",
        "pattern": [
            [0, 0, 1, 0],
            [1, 2, 2, 0],
            [0, 2, 2, 1],
            [0, 1, 0, 0],
        ],
    },
    "brain_period_4": {
        "name": "Period-4 Oscillator",
        "mode": "brians_brain",
        "category": "oscillators",
        "description": "A documented symmetric Brian's Brain period-4 oscillator.",
        "source": "https://conwaylife.com/wiki/OCA:Brian%27s_Brain",
        "pattern": [
            [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 2, 1, 0, 1, 2, 0, 0, 0],
            [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
            [0, 2, 1, 0, 0, 2, 0, 0, 1, 2, 0],
            [0, 0, 1, 2, 0, 2, 0, 2, 1, 0, 0],
            [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
            [1, 2, 0, 0, 0, 2, 0, 0, 0, 2, 1],
            [1, 2, 1, 0, 2, 0, 2, 0, 1, 2, 1],
            [1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1],
            [1, 2, 1, 0, 2, 0, 2, 0, 1, 2, 1],
            [1, 2, 0, 0, 0, 2, 0, 0, 0, 2, 1],
            [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
            [0, 0, 1, 2, 0, 2, 0, 2, 1, 0, 0],
            [0, 2, 1, 0, 0, 2, 0, 0, 1, 2, 0],
            [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
            [0, 0, 0, 2, 1, 0, 1, 2, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
        ],
    },
    "brain_expanding_block": {
        "name": "Expanding 2x2 Block",
        "mode": "brians_brain",
        "category": "wave_seeds",
        "description": "Four firing cells launch an expanding diamond-shaped wave.",
        "pattern": [[1, 1], [1, 1]],
    },
    "brain_wickstretcher": {
        "name": "Two-Sided Wickstretcher",
        "mode": "brians_brain",
        "category": "wickstretchers",
        "description": "A small seed that extends a wick in both directions.",
        "source": "https://conwaylife.com/wiki/OCA:Brian%27s_Brain",
        "pattern": [[1, 1, 1], [1, 0, 1], [0, 2, 0]],
    },
    "brain_parallel_wickstretcher": {
        "name": "Parallel Wickstretcher",
        "mode": "brians_brain",
        "category": "wickstretchers",
        "description": "A four-cell seed producing a different extending wick.",
        "source": "https://conwaylife.com/wiki/OCA:Brian%27s_Brain",
        "pattern": [[1, 0, 0, 1], [1, 0, 0, 1]],
    },
    "langton_single_ant": {
        "name": "Single Ant on White",
        "mode": "langtons_ant",
        "category": "classic_starts",
        "description": "The classic blank-board, north-facing starting state.",
        "pattern": [[0]],
        "ant": {"row": 0, "col": 0, "direction": 0},
    },
    "langton_black_start": {
        "name": "Single Ant on Black",
        "mode": "langtons_ant",
        "category": "classic_starts",
        "description": "A north-facing ant beginning on a black cell.",
        "pattern": [[1]],
        "ant": {"row": 0, "col": 0, "direction": 0},
    },
    "langton_black_box": {
        "name": "Ant in Black Box",
        "mode": "langtons_ant",
        "category": "arenas",
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
        "category": "signals",
        "description": "An electron tail and head moving along a conductor.",
        "pattern": [[2, 1, 3, 3, 3, 3, 3, 3, 3, 3]],
    },
    "wireworld_corner": {
        "name": "Signal Around a Corner",
        "mode": "wireworld",
        "category": "signals",
        "description": "A live signal following a conductor through a right-angle bend.",
        "pattern": [
            [2, 1, 3, 3],
            [0, 0, 0, 3],
            [0, 0, 0, 3],
            [0, 0, 0, 3],
            [0, 0, 0, 3],
        ],
    },
    "wireworld_parallel_bus": {
        "name": "Parallel Signal Bus",
        "mode": "wireworld",
        "category": "signals",
        "description": "Two independent pulses moving along parallel conductors.",
        "pattern": [
            [2, 1, 3, 3, 3, 3, 3, 3, 3, 3],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [2, 1, 3, 3, 3, 3, 3, 3, 3, 3],
        ],
    },
    "wireworld_collision": {
        "name": "Head-On Pulse Collision",
        "mode": "wireworld",
        "category": "signals",
        "description": "Two opposing pulses meet and cancel on a straight conductor.",
        "pattern": [[2, 1, 3, 3, 3, 3, 3, 3, 1, 2]],
    },
    "wireworld_splitter": {
        "name": "Three-Way Signal Splitter",
        "mode": "wireworld",
        "category": "routing",
        "description": "One incoming pulse branches through a T-junction.",
        "pattern": [
            [0, 0, 0, 0, 3],
            [0, 0, 0, 0, 3],
            [2, 1, 3, 3, 3],
            [0, 0, 0, 0, 3],
            [0, 0, 0, 0, 3],
        ],
    },
    "wireworld_clock_loop": {
        "name": "12-Tick Clock Loop",
        "mode": "wireworld",
        "category": "timing",
        "description": "A pulse circulating around a closed conductor every 12 ticks.",
        "pattern": [
            [0, 2, 1, 3, 0],
            [3, 0, 0, 0, 3],
            [3, 0, 0, 0, 3],
            [3, 0, 0, 0, 3],
            [0, 3, 3, 3, 0],
        ],
    },
    "wireworld_classic_diode": {
        "name": "Classic Diode Demonstration",
        "mode": "wireworld",
        "category": "routing",
        "description": "Forward and reverse signals demonstrate one-way conduction.",
        "source": "https://www.quinapalus.com/wires2.html",
        "pattern": _wireworld_ascii(
            ".........CC.......",
            "CTHCCCCTHC.CCTHCCC",
            ".........CC.......",
            "..................",
            "........HC........",
            "CTHCCCCT.CCCCCCCCC",
            "........HC........",
        ),
    },
    "wireworld_classic_or": {
        "name": "Classic OR Gate",
        "mode": "wireworld",
        "category": "logic",
        "description": "The compact Quinapalus OR gate with an active input pulse.",
        "source": "https://www.quinapalus.com/wires3.html",
        "pattern": _wireworld_ascii(
            "CCTHCCCCC.........",
            ".........C........",
            "........CCCCCCTHCC",
            ".........C........",
            "CCCCCCCCC.........",
        ),
    },
    "wireworld_classic_xor": {
        "name": "Classic Exclusive-OR Gate",
        "mode": "wireworld",
        "category": "logic",
        "description": "One active input passes; simultaneous inputs cancel at the junction.",
        "source": "https://www.quinapalus.com/wires4.html",
        "pattern": _wireworld_ascii(
            "CCTHCCCCC.........",
            ".........C........",
            "........CCCC......",
            "........C..CCCCCCC",
            "........CCCC......",
            ".........C........",
            "CCCCCCCCC.........",
        ),
    },
    "wireworld_classic_and_not": {
        "name": "Classic AND-NOT / Clocked NOT",
        "mode": "wireworld",
        "category": "logic",
        "description": "Computes A AND NOT B; a clock on A turns it into an inverter.",
        "source": "https://www.quinapalus.com/wires5.html",
        "pattern": _wireworld_ascii(
            "CCTHCCCCC.........",
            ".........C........",
            "........CCC.......",
            ".........C........",
            "........C.CCCCCCCC",
            ".......C..........",
            "CCCCCCC...........",
        ),
    },
    "wireworld_classic_and": {
        "name": "Clocked AND Gate",
        "mode": "wireworld",
        "category": "logic",
        "description": "A complete two-input AND demonstration with clocks and output.",
        "source": "https://codeheir.com/blog/2024/07/13/wireworld-cellular-automaton/",
        "pattern": _wireworld_ascii(
            "..........H...................",
            ".HCCC....T.C..................",
            "T....C...C.C.....C.CC.........",
            ".CCCC.CCC..C....CCC..C........",
            "...........C.C.C.C.H..CCCCTHCC",
            ".HCCC.CCCC..CCC....T..........",
            "T....C....T..C.C...C..........",
            ".CCCC......H....CCC...........",
            "............CCCC..............",
        ),
    },
    "wireworld_classic_flip_flop": {
        "name": "Set-Reset Flip-Flop",
        "mode": "wireworld",
        "category": "memory",
        "description": "A six-cell storage loop with set, reset, and pulse-stream output.",
        "source": "https://www.quinapalus.com/wires7.html",
        "pattern": _wireworld_ascii(
            "CCCCCCCCCCCCC....................",
            ".............C...................",
            "............CCC..................",
            ".............C...................",
            "............C.CCCCCTHCCCCTHCCCCTH",
            "............C.C..................",
            "...........CCC...................",
            "............C....................",
            "CCCCCCCTHCCC.....................",
        ),
    },
    "wireworld_classic_binary_adder": {
        "name": "Bit-Serial Binary Adder",
        "mode": "wireworld",
        "category": "arithmetic",
        "description": "A compact full binary adder with carry state and serial I/O.",
        "source": "https://www.quinapalus.com/wires8.html",
        "pattern": _wireworld_ascii(
            "..C.....C.....C...............CCCCCC................................",
            ".............................C......C......C.....C.....C.....C.....C",
            "CCCCCCCTHCCCCTHCCCCC.....CCCC..CC..CCCC.............................",
            "....................C...C.....C..T.C..CCCCTHCCCCCCCCCCCCCCCCTHCCCCCC",
            "...................CCCC.C...C.CCH..CCCC.............................",
            "...................C..CC.CCCCC......C...............................",
            "...................CCCC.C...C.C.C..C................................",
            "....................C...C.....T...C.................................",
            "CTHCCCCTHCCCCCCCCCCCC..CCC...HHH.C..................................",
            ".....................C..C.....C..C..................................",
            "..C.....C.....C......C.C.C...C.CC...................................",
            ".....................C.C.C...C.C....................................",
            "......................C..C..CCC.....................................",
            ".........................C...C......................................",
            "..........................CCC.......................................",
        ),
    },
    "wireworld_diodes": {
        "name": "Forward and Reverse Diodes",
        "mode": "wireworld",
        "category": "routing",
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
        "category": "logic",
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
    "cyclic_phase_gradient": {
        "name": "Diagonal Phase Gradient",
        "mode": "cyclic_automaton",
        "category": "wave_seeds",
        "description": "All eight colors arranged as repeating diagonal fronts.",
        "pattern": _cyclic_phase_gradient(),
    },
    "cyclic_concentric_rings": {
        "name": "Concentric Color Rings",
        "mode": "cyclic_automaton",
        "category": "wave_seeds",
        "description": "Nested successor states that launch inward and outward fronts.",
        "pattern": _cyclic_concentric_rings(),
    },
    "cyclic_color_wheel": {
        "name": "Eight-State Color Wheel",
        "mode": "cyclic_automaton",
        "category": "spiral_seeds",
        "description": "Eight phase sectors joined around a compact spiral core.",
        "pattern": _cyclic_color_wheel(),
    },
}
