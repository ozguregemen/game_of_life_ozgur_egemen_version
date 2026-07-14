"""Tests for checkpoint/delta timeline history."""

from __future__ import annotations

import unittest

from timeline_history import TimelineBinding, TimelineHistory, apply_delta, diff_states


class DeltaTests(unittest.TestCase):
    def test_nested_grid_and_appended_row_round_trip(self) -> None:
        previous = {"grid": [[0, 1], [1, 0]], "rows": [[1, 0]]}
        current = {"grid": [[1, 1], [1, 0]], "rows": [[1, 0], [0, 1]]}

        delta = diff_states(previous, current)

        self.assertEqual(apply_delta(previous, delta), current)
        self.assertLess(len(delta), 5)

    def test_truncated_list_round_trip(self) -> None:
        previous = {"rows": [[1], [0], [1]]}
        current = {"rows": [[1]]}

        self.assertEqual(apply_delta(previous, diff_states(previous, current)), current)


class TimelineHistoryTests(unittest.TestCase):
    def test_reconstructs_between_checkpoints(self) -> None:
        history = TimelineHistory(checkpoint_interval=3)
        history.reset({"grid": [[0]]}, 0)
        for generation in range(1, 8):
            history.record({"grid": [[generation % 2]]}, generation)

        self.assertEqual(history.reconstruct(5), {"grid": [[1]]})
        self.assertEqual(history.status().checkpoints, (0, 3, 6))

    def test_forward_and_back_navigation(self) -> None:
        history = TimelineHistory()
        history.reset({"value": 0}, 0)
        history.record({"value": 1}, 1)
        history.record({"value": 2}, 2)

        self.assertEqual(history.step(-1), {"value": 1})
        self.assertTrue(history.status().can_step_forward)
        self.assertEqual(history.step(1), {"value": 2})

    def test_new_state_after_seek_discards_future_branch(self) -> None:
        history = TimelineHistory()
        history.reset({"value": 0}, 0)
        history.record({"value": 1}, 1)
        history.record({"value": 2}, 2)
        history.seek(1)

        history.record({"value": 10}, 2)

        self.assertEqual(history.status().frame_count, 3)
        self.assertEqual(history.current_state(), {"value": 10})
        self.assertFalse(history.status().can_step_forward)

    def test_sync_at_past_frame_does_not_discard_future(self) -> None:
        history = TimelineHistory()
        history.reset({"value": 0}, 0)
        history.record({"value": 1}, 1)
        history.record({"value": 2}, 2)
        history.seek(1)

        self.assertFalse(history.record({"value": 1}, 1))

        self.assertEqual(history.status().frame_count, 3)
        self.assertTrue(history.status().can_step_forward)

    def test_seek_generation_uses_most_recent_duplicate(self) -> None:
        history = TimelineHistory()
        history.reset({"epoch": 1}, 0)
        history.record({"epoch": 1}, 1)
        history.record({"epoch": 2}, 0)
        history.record({"epoch": 2}, 1)

        self.assertEqual(history.seek_generation(1), {"epoch": 2})
        self.assertEqual(history.status().cursor, 3)

    def test_pruning_preserves_reconstructable_first_checkpoint(self) -> None:
        history = TimelineHistory(checkpoint_interval=4, max_frames=5)
        history.reset({"value": 0}, 0)
        for generation in range(1, 9):
            history.record({"value": generation}, generation)

        self.assertEqual(history.status().frame_count, 5)
        self.assertEqual(history.reconstruct(0), {"value": 4})
        self.assertEqual(history.current_state(), {"value": 8})


class TimelineBindingTests(unittest.TestCase):
    def test_binding_restores_workspace_state(self) -> None:
        workspace = {"value": 0, "generation": 0}

        def capture() -> dict[str, int]:
            return dict(workspace)

        def restore(state: dict[str, int]) -> None:
            workspace.update(state)

        binding = TimelineBinding(
            capture,
            restore,
            lambda: workspace["generation"],
        )
        workspace.update(value=1, generation=1)
        binding.sync()
        workspace.update(value=2, generation=2)
        binding.sync()

        self.assertTrue(binding.step(-1))
        self.assertEqual(workspace, {"value": 1, "generation": 1})
        self.assertTrue(binding.step(1))
        self.assertEqual(workspace, {"value": 2, "generation": 2})

    def test_status_does_not_recapture_large_workspace_each_frame(self) -> None:
        workspace = {"value": 0, "generation": 0}
        capture_count = 0

        def capture() -> dict[str, int]:
            nonlocal capture_count
            capture_count += 1
            return dict(workspace)

        binding = TimelineBinding(
            capture,
            lambda state: workspace.update(state),
            lambda: workspace["generation"],
        )

        binding.status()
        binding.status()
        binding.status()

        self.assertEqual(capture_count, 1)


if __name__ == "__main__":
    unittest.main()
