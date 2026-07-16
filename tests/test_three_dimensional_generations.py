import unittest

import numpy as np

from three_dimensional_ca import Volume3D
from three_dimensional_generations import (
    GENERATIONS_3D_BRAIN,
    GENERATIONS_445,
    GENERATIONS_PYROCLASTIC,
    GenerationsRule3D,
    step_generations_3d,
)


class GenerationsRule3DTests(unittest.TestCase):
    def test_445_birth_survival_and_refractory_progression(self) -> None:
        cells = np.zeros((5, 5, 5), dtype=np.uint8)
        for position in ((1, 2, 2), (3, 2, 2), (2, 1, 2), (2, 3, 2)):
            cells[position] = 1

        born = step_generations_3d(
            Volume3D(cells, state_count=5),
            GENERATIONS_445,
        )
        self.assertEqual(int(born[2, 2, 2]), 1)

        cells[2, 2, 2] = 1
        survived = step_generations_3d(
            Volume3D(cells, state_count=5),
            GENERATIONS_445,
        )
        self.assertEqual(int(survived[2, 2, 2]), 1)

        isolated = np.zeros((3, 3, 3), dtype=np.uint8)
        isolated[1, 1, 1] = 1
        volume = Volume3D(isolated, state_count=5)
        expected_states = (2, 3, 4, 0)
        for expected in expected_states:
            following = step_generations_3d(volume, GENERATIONS_445)
            self.assertEqual(int(following[1, 1, 1]), expected)
            volume.replace_cells(following)

    def test_refractory_voxels_do_not_count_as_active_neighbors(self) -> None:
        cells = np.zeros((5, 5, 5), dtype=np.uint8)
        cells[2, 2, 2] = 1
        for position in ((1, 2, 2), (3, 2, 2), (2, 1, 2), (2, 3, 2)):
            cells[position] = 2

        following = step_generations_3d(
            Volume3D(cells, state_count=5),
            GENERATIONS_445,
        )

        self.assertEqual(int(following[2, 2, 2]), 2)

    def test_step_is_non_mutating_and_validates_state_count(self) -> None:
        cells = np.zeros((3, 3, 3), dtype=np.uint8)
        cells[1, 1, 1] = 1
        volume = Volume3D(cells, state_count=5)

        step_generations_3d(volume, GENERATIONS_445)

        np.testing.assert_array_equal(volume.cells, cells)
        with self.assertRaisesRegex(ValueError, "state_count"):
            step_generations_3d(Volume3D.empty((3, 3, 3)), GENERATIONS_445)

    def test_documented_presets_and_compact_notation(self) -> None:
        self.assertEqual(GENERATIONS_445.notation, "4/4/5/M")
        self.assertEqual(GENERATIONS_3D_BRAIN.notation, "/4/2/M")
        self.assertEqual(GENERATIONS_PYROCLASTIC.notation, "4-7/6-8/10/M")
        with self.assertRaisesRegex(ValueError, "between 0 and 26"):
            GenerationsRule3D(
                "bad",
                "Bad",
                (27,),
                (),
                3,
                GENERATIONS_445.neighborhood,
                "Invalid",
            )


if __name__ == "__main__":
    unittest.main()
