import os
import subprocess
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import life


class PatternPlacementTests(unittest.TestCase):
    def setUp(self) -> None:
        life.grid = life.make_grid()
        life.trail_grid = life.make_grid()
        life.activity_grid = life.make_float_grid()
        life.grid_history.clear()
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

    def test_out_of_bounds_pattern_is_not_partially_placed(self) -> None:
        life.place_selected_pattern(life.ROWS - 1, life.COLS - 1)
        self.assertFalse(any(cell for row in life.grid for cell in row))
        self.assertEqual(life.grid_history, [])

    def test_noop_pattern_does_not_add_history(self) -> None:
        for row in (2, 3):
            for col in (2, 3):
                life.grid[row][col] = 1
        life.place_selected_pattern(2, 2)
        self.assertEqual(life.grid_history, [])

    def test_changed_pattern_adds_one_history_entry(self) -> None:
        life.place_selected_pattern(2, 2)
        self.assertEqual(len(life.grid_history), 1)


class ApplicationSmokeTests(unittest.TestCase):
    def test_dummy_video_driver_startup(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "SDL_VIDEODRIVER": "dummy",
                "SDL_AUDIODRIVER": "dummy",
                "LIFE_SMOKE_TEST": "1",
            }
        )
        result = subprocess.run(
            [sys.executable, "life.py"],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
