import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from three_dimensional_ca import Volume3D
from three_dimensional_patterns import (
    ASYMMETRIC_HOOK_6,
    BAYS_5766_GLIDER,
    HOLLOW_CUBE_26,
    Pattern3D,
    PatternTransform3D,
    delete_custom_pattern_3d,
    get_patterns_3d,
    pattern_from_volume,
    refresh_pattern_3d_cache,
    safe_pattern_3d_filename,
    save_custom_pattern_3d,
)
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

    def test_asymmetric_pattern_exposes_24_rotations_and_distinct_mirrors(self) -> None:
        rotations = {
            tuple(
                sorted(
                    offset
                    for offset, _state in ASYMMETRIC_HOOK_6.transformed_voxels(
                        PatternTransform3D(index)
                    )
                )
            )
            for index in range(24)
        }
        mirrored = {
            tuple(
                sorted(
                    offset
                    for offset, _state in ASYMMETRIC_HOOK_6.transformed_voxels(
                        PatternTransform3D(index, True)
                    )
                )
            )
            for index in range(24)
        }

        self.assertEqual(len(rotations), 24)
        self.assertEqual(len(mirrored), 24)
        self.assertFalse(rotations & mirrored)

    def test_positioning_rejects_whole_pattern_instead_of_clipping(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not fit"):
            HOLLOW_CUBE_26.positioned_voxels((0, 0, 0), (8, 8, 8))
        placed = ASYMMETRIC_HOOK_6.positioned_voxels((3, 3, 3), (8, 8, 8))
        self.assertEqual(len(placed), ASYMMETRIC_HOOK_6.voxel_count)

    def test_custom_multistate_pattern_round_trips_through_utf8_json(self) -> None:
        with TemporaryDirectory() as directory:
            volume = Volume3D.empty((8, 8, 8), state_count=5)
            volume.set_cell((2, 3, 4), 1)
            volume.set_cell((4, 5, 6), 4)
            pattern = pattern_from_volume(
                volume,
                "Örüntü Küpü",
                mode_key="generations",
                rule_key="generations_445",
            )
            with patch(
                "three_dimensional_patterns.PATTERN_3D_DIRECTORY",
                Path(directory),
            ):
                refresh_pattern_3d_cache()
                saved = save_custom_pattern_3d(pattern)
                loaded = get_patterns_3d(
                    mode_key="generations",
                    rule_key="generations_445",
                    category="custom",
                )
                self.assertEqual(loaded, (saved,))
                self.assertEqual(saved.states, (1, 4))
                self.assertIn("örüntü_küpü.json", {path.name for path in Path(directory).iterdir()})
                with self.assertRaises(FileExistsError):
                    save_custom_pattern_3d(pattern)
                self.assertTrue(delete_custom_pattern_3d(saved.key))
                self.assertFalse(delete_custom_pattern_3d(saved.key))
                self.assertFalse(
                    get_patterns_3d(
                        mode_key="generations",
                        rule_key="generations_445",
                        category="custom",
                    )
                )
            refresh_pattern_3d_cache()

    def test_corrupt_custom_json_is_skipped_without_breaking_catalog(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{not valid json", encoding="utf-8")
            with patch(
                "three_dimensional_patterns.PATTERN_3D_DIRECTORY",
                Path(directory),
            ):
                with self.assertWarnsRegex(UserWarning, "Skipping invalid"):
                    refresh_pattern_3d_cache()
                self.assertFalse(
                    get_patterns_3d(
                        mode_key="spatial_life",
                        rule_key="bays_5766",
                        category="custom",
                    )
                )
            refresh_pattern_3d_cache()

    def test_safe_filename_blocks_empty_and_path_segments(self) -> None:
        self.assertEqual(safe_pattern_3d_filename("../A:B"), "a_b")
        with self.assertRaises(ValueError):
            safe_pattern_3d_filename("   ")

    def test_catalog_filters_documented_pattern_by_exact_rule(self) -> None:
        compatible = get_patterns_3d(
            mode_key="spatial_life",
            rule_key="bays_5766",
        )
        incompatible = get_patterns_3d(
            mode_key="spatial_life",
            rule_key="bays_4555",
        )

        self.assertIn(BAYS_5766_GLIDER, compatible)
        self.assertNotIn(BAYS_5766_GLIDER, incompatible)
        self.assertIn(ASYMMETRIC_HOOK_6, incompatible)

    def test_pattern_rejects_extreme_coordinates(self) -> None:
        with self.assertRaisesRegex(ValueError, "supported range"):
            Pattern3D(
                "huge",
                "Huge",
                "*",
                ((0, 0, 1025),),
                "",
                "",
                mode_key="*",
            )

    def test_pattern_json_rejects_boolean_schema_version(self) -> None:
        document = """{
          "schema": "cellular-automata-lab-pattern-3d",
          "version": true,
          "name": "Bad Version",
          "mode": "spatial_life",
          "rule": "bays_5766",
          "voxels": [[0, 0, 0, 1]]
        }"""
        with TemporaryDirectory() as directory:
            Path(directory, "bad-version.json").write_text(document, encoding="utf-8")
            with patch(
                "three_dimensional_patterns.PATTERN_3D_DIRECTORY",
                Path(directory),
            ):
                with self.assertWarnsRegex(UserWarning, "schema or version"):
                    refresh_pattern_3d_cache()
                self.assertFalse(
                    get_patterns_3d(
                        mode_key="spatial_life",
                        rule_key="bays_5766",
                        category="custom",
                    )
                )
            refresh_pattern_3d_cache()


if __name__ == "__main__":
    unittest.main()
