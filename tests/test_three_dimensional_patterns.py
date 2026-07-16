import unittest

import numpy as np

from three_dimensional_ca import Volume3D
from three_dimensional_patterns import BAYS_5766_GLIDER, Pattern3D
from three_dimensional_rules import BAYS_5766, step_life_like_3d


def normalized_live_coordinates(cells: np.ndarray) -> tuple[tuple[int, ...], ...]:
    live = np.argwhere(cells != 0)
    live -= live.min(axis=0)
    return tuple(tuple(int(value) for value in row) for row in live)


class ThreeDimensionalPatternTests(unittest.TestCase):
    def test_bays_5766_glider_repeats_translated_after_four_generations(self) -> None:
        volume = Volume3D(
            BAYS_5766_GLIDER.centered_cells((16, 20, 20)),
            neighborhood=BAYS_5766.neighborhood,
        )
        initial = normalized_live_coordinates(volume.cells)
        initial_minimum = np.argwhere(volume.cells != 0).min(axis=0)

        for _ in range(4):
            volume.replace_cells(step_life_like_3d(volume, BAYS_5766))

        final_minimum = np.argwhere(volume.cells != 0).min(axis=0)
        self.assertEqual(normalized_live_coordinates(volume.cells), initial)
        np.testing.assert_array_equal(final_minimum - initial_minimum, (0, 1, 1))
        self.assertEqual(int(np.count_nonzero(volume.cells)), 10)

    def test_pattern_rejects_duplicate_offsets_and_small_volumes(self) -> None:
        with self.assertRaises(ValueError):
            Pattern3D("bad", "Bad", "rule", ((0, 0, 0), (0, 0, 0)), "", "")
        with self.assertRaisesRegex(ValueError, "does not fit"):
            BAYS_5766_GLIDER.centered_cells((1, 1, 1))


if __name__ == "__main__":
    unittest.main()
