import unittest

from brians_brain import apply_brain_rules
from cyclic_automaton import apply_cyclic_rules
from immigration import apply_immigration_rules, species_of
from mode_patterns import MODE_PATTERNS
from wireworld import ELECTRON_HEAD, apply_wireworld_rules


class BuiltinModePatternBehaviorTests(unittest.TestCase):
    @staticmethod
    def padded(pattern: list[list[int]], padding: int = 6) -> list[list[int]]:
        """Embed a trimmed catalog pattern in finite empty space."""
        width = len(pattern[0])
        result = [
            [0 for _ in range(width + padding * 2)]
            for _ in range(len(pattern) + padding * 2)
        ]
        for row, values in enumerate(pattern):
            result[row + padding][padding : padding + width] = values
        return result

    def test_brians_brain_oscillator_has_period_three(self) -> None:
        initial = MODE_PATTERNS["brain_period_3"]["pattern"]
        generation = initial
        for _ in range(3):
            generation = apply_brain_rules(generation)
        self.assertEqual(generation, initial)

    def test_brians_brain_large_oscillator_has_period_four(self) -> None:
        initial = self.padded(MODE_PATTERNS["brain_period_4"]["pattern"])
        generation = initial
        for _ in range(4):
            generation = apply_brain_rules(generation)
        self.assertEqual(generation, initial)

    def test_immigration_split_block_remains_stable(self) -> None:
        initial = MODE_PATTERNS["immigration_split_block"]["pattern"]
        generation = apply_immigration_rules(initial)
        self.assertEqual(
            [[species_of(cell) for cell in row] for row in generation],
            initial,
        )

    def test_immigration_still_lifes_keep_their_shape_and_species(self) -> None:
        for key in ("immigration_beehive", "immigration_loaf"):
            with self.subTest(pattern=key):
                initial = MODE_PATTERNS[key]["pattern"]
                generation = apply_immigration_rules(initial)
                self.assertEqual(
                    [[species_of(cell) for cell in row] for row in generation],
                    initial,
                )

    def test_immigration_toad_returns_to_its_occupancy_after_two_ticks(self) -> None:
        initial = self.padded(MODE_PATTERNS["immigration_toad"]["pattern"])
        generation = apply_immigration_rules(apply_immigration_rules(initial))
        self.assertEqual(
            [[cell != 0 for cell in row] for row in generation],
            [[cell != 0 for cell in row] for row in initial],
        )

    def test_wireworld_signal_moves_along_straight_wire(self) -> None:
        initial = MODE_PATTERNS["wireworld_signal_wire"]["pattern"]
        generation = apply_wireworld_rules(initial)
        self.assertEqual(generation[0][:4], [3, 2, 1, 3])

    def test_wireworld_signal_turns_the_corner(self) -> None:
        generation = MODE_PATTERNS["wireworld_corner"]["pattern"]
        for _ in range(4):
            generation = apply_wireworld_rules(generation)
        self.assertEqual(generation[3][3], ELECTRON_HEAD)

    def test_wireworld_splitter_branches_to_both_outputs(self) -> None:
        generation = MODE_PATTERNS["wireworld_splitter"]["pattern"]
        for _ in range(3):
            generation = apply_wireworld_rules(generation)
        heads = {
            (row, col)
            for row, values in enumerate(generation)
            for col, value in enumerate(values)
            if value == ELECTRON_HEAD
        }
        self.assertTrue({(1, 4), (3, 4)}.issubset(heads))

    def test_wireworld_clock_loop_has_period_twelve(self) -> None:
        initial = MODE_PATTERNS["wireworld_clock_loop"]["pattern"]
        generation = initial
        for _ in range(12):
            generation = apply_wireworld_rules(generation)
        self.assertEqual(generation, initial)

    def test_wireworld_head_on_pulses_cancel(self) -> None:
        generation = MODE_PATTERNS["wireworld_collision"]["pattern"]
        for _ in range(4):
            generation = apply_wireworld_rules(generation)
        self.assertFalse(any(ELECTRON_HEAD in row for row in generation))

    def test_wireworld_diodes_pass_only_forward_signal(self) -> None:
        generation = MODE_PATTERNS["wireworld_diodes"]["pattern"]
        for _ in range(12):
            generation = apply_wireworld_rules(generation)
        heads = [
            (row, col)
            for row, values in enumerate(generation)
            for col, value in enumerate(values)
            if value == ELECTRON_HEAD
        ]
        self.assertEqual(heads, [(1, 13)])

    def test_clocked_xor_remains_an_active_circuit(self) -> None:
        generation = MODE_PATTERNS["wireworld_xor"]["pattern"]
        for _ in range(25):
            generation = apply_wireworld_rules(generation)
        self.assertTrue(any(ELECTRON_HEAD in row for row in generation))

    def test_cyclic_phase_gradient_advances_synchronously(self) -> None:
        initial = MODE_PATTERNS["cyclic_phase_gradient"]["pattern"]
        generation = apply_cyclic_rules(initial)
        expected = [[(cell + 1) % 8 for cell in row] for row in initial]
        expected[-1][-1] = initial[-1][-1]

        self.assertEqual(generation, expected)


if __name__ == "__main__":
    unittest.main()
