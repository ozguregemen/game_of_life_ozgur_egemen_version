import unittest

import numpy as np

from three_dimensional_ca import BOUNDARY_WRAP, Volume3D
from three_dimensional_rules import (
    BAYS_4555,
    BAYS_5766,
    FACE_LIFE,
    LifeLikeRule3D,
    step_life_like_3d,
)


class LifeLikeRule3DTests(unittest.TestCase):
    def test_bays_5766_birth_survival_and_death_counts(self) -> None:
        cells = np.zeros((5, 5, 5), dtype=np.uint8)
        neighbors = (
            (1, 2, 2),
            (3, 2, 2),
            (2, 1, 2),
            (2, 3, 2),
            (2, 2, 1),
            (2, 2, 3),
        )
        for position in neighbors:
            cells[position] = 1

        born = step_life_like_3d(Volume3D(cells), BAYS_5766)
        self.assertEqual(int(born[2, 2, 2]), 1)

        cells[2, 2, 2] = 1
        survives = step_life_like_3d(Volume3D(cells), BAYS_5766)
        self.assertEqual(int(survives[2, 2, 2]), 1)

        cells[1, 2, 2] = 0
        cells[3, 2, 2] = 0
        dies = step_life_like_3d(Volume3D(cells), BAYS_5766)
        self.assertEqual(int(dies[2, 2, 2]), 0)

    def test_step_is_non_mutating_and_respects_wrap_boundary(self) -> None:
        cells = np.zeros((3, 3, 3), dtype=np.uint8)
        for position in (
            (2, 0, 0),
            (0, 2, 0),
            (0, 0, 2),
            (2, 2, 0),
            (2, 0, 2),
            (0, 2, 2),
        ):
            cells[position] = 1
        volume = Volume3D(cells, boundary=BOUNDARY_WRAP)

        result = step_life_like_3d(volume, BAYS_5766)

        self.assertEqual(int(result[0, 0, 0]), 1)
        np.testing.assert_array_equal(volume.cells, cells)

    def test_presets_have_valid_notation_and_matching_neighborhoods(self) -> None:
        self.assertEqual(BAYS_5766.notation, "B6/S567")
        self.assertEqual(BAYS_4555.notation, "B5/S45")
        self.assertEqual(FACE_LIFE.notation, "B3/S23")
        self.assertEqual(BAYS_5766.neighborhood.size, 26)
        self.assertEqual(FACE_LIFE.neighborhood.size, 6)

    def test_rule_rejects_neighbor_counts_outside_its_neighborhood(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 0 and 6"):
            LifeLikeRule3D(
                "bad",
                "Bad",
                (7,),
                (),
                FACE_LIFE.neighborhood,
                "Invalid",
            )


if __name__ == "__main__":
    unittest.main()
