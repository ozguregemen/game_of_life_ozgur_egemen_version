"""Repeatable CPU-side render benchmark for every interactive simulation mode."""

from __future__ import annotations

import argparse
import cProfile
import json
import os
import pstats
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import life

ScenarioSetup = Callable[[], None]


def _reset_interface_state(mode: str) -> None:
    life.set_simulation_mode(mode)
    life.invalidate_render_cache(mode)
    life.simulation_active = False
    life.selected_pattern = None
    life.pattern_menu_active = False
    life.mode_menu_active = False
    life.show_grid = True
    life.show_coordinates = False
    life.show_quadrants = False
    life.show_age_numbers = False
    life.show_heatmap = False
    life.status_message = ""
    life.stats_dirty = False
    life.recognized_pattern_cache = {}
    life.center_view()


def setup_life_dense() -> None:
    _reset_interface_state("life")
    rng = random.Random(11)
    life.grid = [
        [rng.randrange(1, 16) if rng.random() < 0.42 else 0 for _ in range(life.COLS)]
        for _ in range(life.ROWS)
    ]
    life.trail_grid = life.make_grid()
    life.activity_grid = life.make_float_grid()


def setup_life_heatmap() -> None:
    setup_life_dense()
    rng = random.Random(12)
    life.show_heatmap = True
    life.trail_grid = [
        [rng.randrange(0, life.TRAIL_MAX + 1) for _ in range(life.COLS)]
        for _ in range(life.ROWS)
    ]
    life.activity_grid = [
        [rng.random() * 2.5 for _ in range(life.COLS)]
        for _ in range(life.ROWS)
    ]


def setup_immigration() -> None:
    _reset_interface_state("immigration")
    life.immigration_grid = life.randomize_immigration_grid(
        life.ROWS,
        life.COLS,
        density=0.42,
        rng=random.Random(13),
    )


def setup_brians_brain() -> None:
    _reset_interface_state("brians_brain")
    life.brain_grid = life.randomize_brain_grid(
        life.ROWS,
        life.COLS,
        density=0.42,
        rng=random.Random(14),
    )


def setup_langtons_ant() -> None:
    _reset_interface_state("langtons_ant")
    life.ant_grid = life.randomize_ant_grid(
        life.ROWS,
        life.COLS,
        density=0.42,
        rng=random.Random(15),
    )
    life.ant_state = life.centered_ant(life.ROWS, life.COLS)


def setup_wireworld() -> None:
    _reset_interface_state("wireworld")
    life.wireworld_grid = life.randomize_wireworld_grid(
        life.ROWS,
        life.COLS,
        conductor_density=0.42,
        signal_fraction=0.12,
        rng=random.Random(16),
    )


def setup_cyclic_automaton() -> None:
    _reset_interface_state("cyclic_automaton")
    life.cyclic_grid = life.randomize_cyclic_grid(
        life.ROWS,
        life.COLS,
        state_count=life.CYCLIC_STATE_COUNT,
        rng=random.Random(17),
    )


SCENARIOS: dict[str, ScenarioSetup] = {
    "life_dense": setup_life_dense,
    "life_heatmap": setup_life_heatmap,
    "immigration": setup_immigration,
    "brians_brain": setup_brians_brain,
    "langtons_ant": setup_langtons_ant,
    "wireworld": setup_wireworld,
    "cyclic_automaton": setup_cyclic_automaton,
}


def _draw_frames(
    frame_count: int,
    *,
    invalidate_each_frame: bool = False,
) -> list[float]:
    durations_ms: list[float] = []
    for _ in range(frame_count):
        if invalidate_each_frame:
            life.invalidate_render_cache()
        start = time.perf_counter_ns()
        life.draw_scene()
        durations_ms.append((time.perf_counter_ns() - start) / 1_000_000)
    return durations_ms


def benchmark_scenario(
    name: str,
    *,
    warmup_frames: int,
    measured_frames: int,
    invalidate_each_frame: bool,
    simulate_running: bool,
) -> dict[str, float | int | str]:
    SCENARIOS[name]()
    life.simulation_active = simulate_running
    if simulate_running:
        life.speed = 60
    _draw_frames(
        warmup_frames,
        invalidate_each_frame=invalidate_each_frame,
    )
    life.reset_render_cache_metrics()
    durations = _draw_frames(
        measured_frames,
        invalidate_each_frame=invalidate_each_frame,
    )
    ordered = sorted(durations)
    p95_index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    median_ms = statistics.median(durations)
    return {
        "scenario": name,
        "cache_mode": "forced_rebuild" if invalidate_each_frame else "reuse",
        "simulation": "running" if simulate_running else "paused",
        "frames": measured_frames,
        "cache_hits": life.render_cache_hits,
        "cache_misses": life.render_cache_misses,
        "mean_ms": statistics.fmean(durations),
        "median_ms": median_ms,
        "p95_ms": ordered[p95_index],
        "min_ms": ordered[0],
        "estimated_fps": 1000.0 / median_ms if median_ms else 0.0,
    }


def profile_scenario(
    name: str,
    frame_count: int,
    *,
    invalidate_each_frame: bool,
    simulate_running: bool,
) -> None:
    SCENARIOS[name]()
    life.simulation_active = simulate_running
    if simulate_running:
        life.speed = 60
    _draw_frames(5)
    profiler = cProfile.Profile()
    profiler.enable()
    _draw_frames(frame_count, invalidate_each_frame=invalidate_each_frame)
    profiler.disable()
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--scenario", choices=tuple(SCENARIOS))
    parser.add_argument("--profile", choices=tuple(SCENARIOS))
    parser.add_argument(
        "--invalidate-each-frame",
        action="store_true",
        help="Force a grid rebuild to measure the uncached rendering path.",
    )
    parser.add_argument(
        "--simulate-running",
        action="store_true",
        help="Mark the simulation as running at 60 gen/s during measurement.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.frames <= 0 or args.warmup < 0:
        raise SystemExit("--frames must be positive and --warmup cannot be negative.")

    try:
        if args.profile:
            profile_scenario(
                args.profile,
                args.frames,
                invalidate_each_frame=args.invalidate_each_frame,
                simulate_running=args.simulate_running,
            )
            return

        scenario_names = [args.scenario] if args.scenario else list(SCENARIOS)
        results = [
            benchmark_scenario(
                name,
                warmup_frames=args.warmup,
                measured_frames=args.frames,
                invalidate_each_frame=args.invalidate_each_frame,
                simulate_running=args.simulate_running,
            )
            for name in scenario_names
        ]
        print(json.dumps(results, indent=2))
    finally:
        life.pattern_scan_executor.shutdown(wait=True, cancel_futures=True)
        life.pygame.quit()


if __name__ == "__main__":
    main()
