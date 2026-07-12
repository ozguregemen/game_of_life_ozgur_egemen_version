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
        life.simulation_mode = "life"
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
    def run_smoke_test(self, mode: str) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "SDL_VIDEODRIVER": "dummy",
                "SDL_AUDIODRIVER": "dummy",
                "LIFE_SMOKE_TEST": "1",
                "LIFE_START_MODE": mode,
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

    def test_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("life")

    def test_immigration_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("immigration")


class ImmigrationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "immigration"
        life.simulation_active = False
        life.immigration_grid = life.make_immigration_grid(life.ROWS, life.COLS)
        life.immigration_history.clear()
        life.grid_history.clear()
        life.immigration_generation = 0
        life.active_species = life.SPECIES_A

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_uses_separate_grid_and_history(self) -> None:
        life.immigration_grid[5][4:7] = [
            life.SPECIES_A,
            life.SPECIES_A,
            life.SPECIES_B,
        ]

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.immigration_generation, 1)
        self.assertEqual(len(life.immigration_history), 1)
        self.assertEqual(life.grid_history, [])

    def test_mode_switch_preserves_both_grids(self) -> None:
        life.grid = life.make_grid()
        life.grid[2][2] = 4
        life.immigration_grid[3][3] = life.SPECIES_B

        life.toggle_simulation_mode()
        life.toggle_simulation_mode()

        self.assertEqual(life.simulation_mode, "immigration")
        self.assertEqual(life.grid[2][2], 4)
        self.assertEqual(life.immigration_grid[3][3], life.SPECIES_B)

    def test_pattern_uses_active_species_and_one_history_entry(self) -> None:
        life.active_species = life.SPECIES_B
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(len(life.immigration_history), 1)
        self.assertTrue(
            all(
                life.immigration_grid[row][col] == life.SPECIES_B
                for row in (2, 3)
                for col in (2, 3)
            )
        )


if __name__ == "__main__":
    unittest.main()
