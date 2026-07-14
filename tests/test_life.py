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

    def test_brians_brain_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("brians_brain")

    def test_langtons_ant_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("langtons_ant")

    def test_wireworld_dummy_video_driver_startup(self) -> None:
        self.run_smoke_test("wireworld")


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
        life.toggle_simulation_mode()
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


class BriansBrainIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "brians_brain"
        life.simulation_active = False
        life.brain_grid = life.make_brain_grid(life.ROWS, life.COLS)
        life.brain_history.clear()
        life.brain_generation = 0

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_uses_separate_brain_history(self) -> None:
        life.brain_grid[5][4:6] = [life.FIRING, life.FIRING]

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.brain_generation, 1)
        self.assertEqual(len(life.brain_history), 1)
        self.assertEqual(life.brain_grid[5][4], life.DYING)

    def test_pattern_places_firing_cells(self) -> None:
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(len(life.brain_history), 1)
        self.assertTrue(
            all(
                life.brain_grid[row][col] == life.FIRING
                for row in (2, 3)
                for col in (2, 3)
            )
        )


class LangtonsAntIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "langtons_ant"
        life.simulation_active = False
        life.ant_grid = life.make_ant_grid(life.ROWS, life.COLS)
        life.ant_state = life.centered_ant(life.ROWS, life.COLS)
        life.ant_history.clear()
        life.ant_generation = 0
        life.ant_last_report = life.AntStepReport()

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_tracks_ant_state_and_history(self) -> None:
        original = life.ant_state

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.ant_generation, 1)
        self.assertEqual(len(life.ant_history), 1)
        self.assertEqual(life.ant_grid[original.row][original.col], life.ANT_BLACK)
        self.assertNotEqual(life.ant_state, original)

    def test_pattern_places_black_cells(self) -> None:
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(len(life.ant_history), 1)
        self.assertTrue(
            all(
                life.ant_grid[row][col] == life.ANT_BLACK
                for row in (2, 3)
                for col in (2, 3)
            )
        )

    def test_place_ant_preserves_direction_and_saves_history(self) -> None:
        original_direction = life.ant_state.direction

        life.place_ant(4, 7)

        self.assertEqual((life.ant_state.row, life.ant_state.col), (4, 7))
        self.assertEqual(life.ant_state.direction, original_direction)
        self.assertEqual(len(life.ant_history), 1)


class WireworldIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        life.simulation_mode = "wireworld"
        life.simulation_active = False
        life.wireworld_grid = life.make_wireworld_grid(life.ROWS, life.COLS)
        life.wireworld_history.clear()
        life.wireworld_generation = 0
        life.wireworld_brush = life.CONDUCTOR

    def tearDown(self) -> None:
        life.simulation_mode = "life"
        life.simulation_active = False

    def test_generation_propagates_signal_and_tracks_history(self) -> None:
        life.wireworld_grid[5][4:7] = [
            life.ELECTRON_TAIL,
            life.ELECTRON_HEAD,
            life.CONDUCTOR,
        ]

        self.assertTrue(life.apply_generation())

        self.assertEqual(life.wireworld_generation, 1)
        self.assertEqual(len(life.wireworld_history), 1)
        self.assertEqual(
            life.wireworld_grid[5][4:7],
            [life.CONDUCTOR, life.ELECTRON_TAIL, life.ELECTRON_HEAD],
        )

    def test_pattern_places_conductors(self) -> None:
        life.selected_pattern = {
            "name": "Block",
            "pattern": [[1, 1], [1, 1]],
        }

        life.place_selected_pattern(2, 2)

        self.assertEqual(len(life.wireworld_history), 1)
        self.assertTrue(
            all(
                life.wireworld_grid[row][col] == life.CONDUCTOR
                for row in (2, 3)
                for col in (2, 3)
            )
        )

    def test_t_cycles_through_three_wireworld_brushes(self) -> None:
        brushes = []
        for _ in range(3):
            life.toggle_active_species()
            brushes.append(life.wireworld_brush)

        self.assertEqual(
            brushes,
            [life.ELECTRON_HEAD, life.ELECTRON_TAIL, life.CONDUCTOR],
        )

    def test_right_brush_erases_and_adds_one_history_entry(self) -> None:
        life.wireworld_grid[2][2] = life.CONDUCTOR
        life.drawing_value = 0
        life.drawing_history_pending = True

        life.draw_cell(2, 2)

        self.assertEqual(life.wireworld_grid[2][2], life.WIRE_EMPTY)
        self.assertEqual(len(life.wireworld_history), 1)


if __name__ == "__main__":
    unittest.main()
