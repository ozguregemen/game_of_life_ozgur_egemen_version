import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from scientific_analysis import StateObservation
from workspaces.two_dimensional import (
    TwoDimensionalWorkspaceController,
    TwoDimensionalWorkspaceServices,
    TwoDimensionalWorkspaceState,
)


class TwoDimensionalWorkspaceArchitectureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mode = "life"
        self.running = False
        self.statuses: list[str] = []
        self.invalidations: list[str] = []
        self.transitions: list[tuple[int, int, int, int]] = []
        self.observations: list[StateObservation] = []
        self.state = TwoDimensionalWorkspaceState.create(
            12,
            16,
            8,
            12345,
            cyclic_threshold=1,
        )
        services = TwoDimensionalWorkspaceServices(
            active_mode=lambda: self.mode,
            is_running=lambda: self.running,
            set_running=self._set_running,
            set_status=lambda message, _duration: self.statuses.append(message),
            invalidate=self.invalidations.append,
            mark_life_dirty=lambda: self.invalidations.append("life"),
            start_transition=lambda row, col, old, new: self.transitions.append(
                (row, col, old, new)
            ),
            clear_transitions=self.transitions.clear,
            before_operation=lambda: None,
            state_changed=lambda: None,
            rebuild_sidebar=lambda: None,
            build_sidebar=lambda _menu: None,
            overlay_active=lambda: False,
            close_overlays=lambda: None,
            handle_overlay_event=lambda _event: False,
            handle_keydown=lambda _event: False,
            handle_pointer_event=lambda _event: False,
            center_view=lambda: None,
            zoom=lambda _factor: None,
            record_analysis=self._record,
            reset_analysis=self._record,
            timeline_max_frames=64,
            trail_max=10,
        )
        self.controller = TwoDimensionalWorkspaceController(services, self.state)

    def _set_running(self, value: bool) -> None:
        self.running = value

    def _record(self, observation: StateObservation) -> None:
        self.observations.append(observation)

    def test_controller_owns_state_instead_of_a_callback_state_adapter(self) -> None:
        self.assertIs(self.controller.state, self.state)
        self.assertFalse(hasattr(self.controller, "callbacks"))
        self.assertEqual(
            set(self.controller.timelines),
            {
                "life",
                "immigration",
                "brians_brain",
                "langtons_ant",
                "wireworld",
                "cyclic_automaton",
            },
        )

    def test_life_generation_and_timeline_are_controller_owned(self) -> None:
        self.state.life.grid[5][6:9] = [1, 1, 1]
        self.controller.timelines["life"].reset()

        self.assertTrue(self.controller.advance())

        self.assertEqual(self.state.life.generation, 1)
        self.assertEqual(
            [
                1 if self.state.life.grid[row][7] > 0 else 0
                for row in range(4, 7)
            ],
            [1, 1, 1],
        )
        self.assertEqual(self.controller.history_status().frame_count, 2)
        self.assertTrue(self.observations)

    def test_modes_keep_independent_state_and_history(self) -> None:
        self.state.life.grid[1][1] = 1
        self.mode = "wireworld"
        self.state.wireworld.grid[4][3:6] = [3, 1, 2]
        self.controller.timelines["wireworld"].reset()

        self.assertTrue(self.controller.advance())

        self.assertEqual(self.state.life.grid[1][1], 1)
        self.assertEqual(self.state.life.generation, 0)
        self.assertEqual(self.state.wireworld.generation, 1)

    def test_snapshot_round_trip_restores_camera_brushes_and_rng(self) -> None:
        self.state.cell_size = 13
        self.state.view_offset_x = -22
        self.state.immigration.active_species = -1
        self.state.cyclic.brush = 6
        self.state.life.rng.random()
        snapshot = self.controller.snapshot()
        expected_random = self.state.life.rng.random()

        self.state.cell_size = 5
        self.state.immigration.active_species = 1
        self.state.cyclic.brush = 1
        self.controller.restore(snapshot)

        self.assertEqual(self.state.cell_size, 13)
        self.assertEqual(self.state.view_offset_x, -22)
        self.assertEqual(self.state.immigration.active_species, -1)
        self.assertEqual(self.state.cyclic.brush, 6)
        self.assertEqual(self.state.life.rng.random(), expected_random)

    def test_controller_input_mutates_only_active_mode(self) -> None:
        self.mode = "brians_brain"

        changed = self.controller.draw_cell(2, 3, 1, begin_history=True)

        self.assertTrue(changed)
        self.assertEqual(self.state.brain.grid[2][3], 1)
        self.assertEqual(self.state.life.grid[2][3], 0)
        self.assertIn("brians_brain", self.invalidations)


if __name__ == "__main__":
    unittest.main()
