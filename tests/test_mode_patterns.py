import unittest
from copy import deepcopy

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

    def test_classic_diode_passes_forward_and_blocks_reverse(self) -> None:
        generation = MODE_PATTERNS["wireworld_classic_diode"]["pattern"]
        for _ in range(8):
            generation = apply_wireworld_rules(generation)

        self.assertEqual(generation[1][16], ELECTRON_HEAD)
        self.assertFalse(
            any(
                generation[row][col] == ELECTRON_HEAD
                for row in (4, 5, 6)
                for col in range(10, len(generation[0]))
            )
        )

    def test_classic_or_gate_accepts_either_or_both_inputs(self) -> None:
        initial = MODE_PATTERNS["wireworld_classic_or"]["pattern"]
        both_inputs = deepcopy(initial)
        both_inputs[4][2:4] = [2, 1]

        for case in (initial, both_inputs):
            with self.subTest(inputs="both" if case is both_inputs else "one"):
                generation = case
                for _ in range(10):
                    generation = apply_wireworld_rules(generation)
                self.assertEqual(generation[2][13], ELECTRON_HEAD)

    def test_classic_xor_gate_cancels_simultaneous_inputs(self) -> None:
        one_input = MODE_PATTERNS["wireworld_classic_xor"]["pattern"]
        both_inputs = deepcopy(one_input)
        both_inputs[6][2:4] = [2, 1]

        one_output = one_input
        both_output = both_inputs
        for _ in range(10):
            one_output = apply_wireworld_rules(one_output)
            both_output = apply_wireworld_rules(both_output)

        self.assertEqual(one_output[3][13], ELECTRON_HEAD)
        self.assertFalse(
            any(cell == ELECTRON_HEAD for cell in both_output[3][11:])
        )

    def test_classic_and_not_gate_matches_truth_cases(self) -> None:
        source = MODE_PATTERNS["wireworld_classic_and_not"]["pattern"]
        a_only = deepcopy(source)
        a_only[0][2:4] = [3, 3]
        a_only[6][0:2] = [2, 1]
        both_inputs = deepcopy(source)
        both_inputs[6][0:2] = [2, 1]

        for _ in range(10):
            a_only = apply_wireworld_rules(a_only)
            both_inputs = apply_wireworld_rules(both_inputs)

        self.assertEqual(a_only[4][11], ELECTRON_HEAD)
        self.assertFalse(
            any(cell == ELECTRON_HEAD for cell in both_inputs[4][10:])
        )

    def test_clocked_and_gate_repeats_every_ten_ticks(self) -> None:
        initial = MODE_PATTERNS["wireworld_classic_and"]["pattern"]
        generation = initial
        for _ in range(10):
            generation = apply_wireworld_rules(generation)
        self.assertEqual(generation, initial)

    def test_flip_flop_keeps_a_circulating_state(self) -> None:
        generation = MODE_PATTERNS["wireworld_classic_flip_flop"]["pattern"]
        for _ in range(6):
            generation = apply_wireworld_rules(generation)
        for _ in range(24):
            generation = apply_wireworld_rules(generation)
            self.assertTrue(
                any(
                    generation[row][col] == ELECTRON_HEAD
                    for row in range(2, 7)
                    for col in range(11, 17)
                )
            )

    def test_binary_adder_outputs_three_plus_six_as_nine(self) -> None:
        generation = MODE_PATTERNS["wireworld_classic_binary_adder"]["pattern"]
        for _ in range(47):
            generation = apply_wireworld_rules(generation)

        output_heads = [
            col
            for col in range(42, 61)
            if generation[3][col] == ELECTRON_HEAD
        ]
        self.assertEqual(output_heads, [42, 60])

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
