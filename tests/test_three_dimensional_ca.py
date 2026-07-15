import unittest

import numpy as np

from three_dimensional_ca import (
    AXIS_X,
    AXIS_Y,
    AXIS_Z,
    BOUNDARY_FIXED,
    BOUNDARY_REFLECT,
    BOUNDARY_WRAP,
    MOORE_NEIGHBORHOOD,
    NEIGHBORHOODS_3D,
    VON_NEUMANN_NEIGHBORHOOD,
    Neighborhood3D,
    Volume3D,
    VolumeLimits,
    moore_neighborhood,
    normalize_volume_shape,
    von_neumann_neighborhood,
)


class VolumeLimitTests(unittest.TestCase):
    def test_shape_uses_depth_rows_columns_and_rejects_invalid_dimensions(self) -> None:
        self.assertEqual(normalize_volume_shape((2, 3, 4)), (2, 3, 4))
        self.assertEqual(
            normalize_volume_shape(np.array((2, 3, 4), dtype=np.int16)),
            (2, 3, 4),
        )
        with self.assertRaisesRegex(ValueError, "depth, rows, and columns"):
            normalize_volume_shape((2, 3))
        with self.assertRaisesRegex(ValueError, "positive"):
            normalize_volume_shape((2, 0, 4))
        with self.assertRaisesRegex(TypeError, "integer"):
            normalize_volume_shape((2, 3.5, 4))

    def test_limits_reject_axis_cell_volume_and_working_allocations(self) -> None:
        with self.assertRaisesRegex(MemoryError, "axis"):
            Volume3D.empty(
                (5, 1, 1),
                limits=VolumeLimits(
                    max_axis_length=4,
                    max_cells=100,
                    max_volume_bytes=100,
                    max_working_bytes=1_000,
                ),
            )
        with self.assertRaisesRegex(MemoryError, "cells"):
            Volume3D.empty(
                (3, 3, 3),
                limits=VolumeLimits(
                    max_axis_length=4,
                    max_cells=20,
                    max_volume_bytes=100,
                    max_working_bytes=1_000,
                ),
            )
        with self.assertRaisesRegex(MemoryError, "bytes"):
            Volume3D.empty(
                (3, 3, 3),
                limits=VolumeLimits(
                    max_axis_length=4,
                    max_cells=100,
                    max_volume_bytes=20,
                    max_working_bytes=1_000,
                ),
            )

        constrained = Volume3D.empty(
            (3, 3, 3),
            limits=VolumeLimits(
                max_axis_length=4,
                max_cells=100,
                max_volume_bytes=100,
                max_working_bytes=100,
            ),
        )
        with self.assertRaisesRegex(MemoryError, "working bytes"):
            constrained.neighbor_counts()

    def test_memory_report_exposes_dense_and_neighbor_budgets(self) -> None:
        volume = Volume3D.empty((3, 4, 5))

        report = volume.memory_report()

        self.assertEqual(report["shape"], (3, 4, 5))
        self.assertEqual(report["cell_count"], 60)
        self.assertEqual(report["volume_bytes"], 60)
        self.assertGreater(report["neighbor_working_bytes"], report["volume_bytes"])


class NeighborhoodDefinitionTests(unittest.TestCase):
    def test_builtin_neighborhood_sizes_and_radii_are_exact(self) -> None:
        self.assertEqual(MOORE_NEIGHBORHOOD.size, 26)
        self.assertEqual(MOORE_NEIGHBORHOOD.radius, 1)
        self.assertEqual(VON_NEUMANN_NEIGHBORHOOD.size, 6)
        self.assertEqual(VON_NEUMANN_NEIGHBORHOOD.radius, 1)
        self.assertEqual(moore_neighborhood(2).size, 124)
        self.assertEqual(von_neumann_neighborhood(2).size, 24)
        self.assertEqual(set(NEIGHBORHOODS_3D), {"moore", "von_neumann"})

    def test_custom_neighborhood_rejects_center_duplicates_and_empty_offsets(self) -> None:
        with self.assertRaisesRegex(ValueError, "center"):
            Neighborhood3D("bad", "Bad", ((0, 0, 0),))
        with self.assertRaisesRegex(ValueError, "unique"):
            Neighborhood3D("bad", "Bad", ((0, 0, 1), (0, 0, 1)))
        with self.assertRaisesRegex(ValueError, "at least one"):
            Neighborhood3D("bad", "Bad", ())
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            Neighborhood3D("", "Bad", ((0, 0, 1),))

    def test_large_neighborhood_uses_a_non_overflowing_count_dtype(self) -> None:
        volume = Volume3D.empty((2, 2, 2), fill_state=1)

        counts = volume.neighbor_counts(
            neighborhood=moore_neighborhood(3),
            boundary=BOUNDARY_WRAP,
        )

        self.assertEqual(counts.dtype, np.dtype(np.uint16))
        self.assertEqual(int(counts[0, 0, 0]), 342)


class Volume3DTests(unittest.TestCase):
    def test_volume_owns_a_contiguous_uint8_copy_and_exposes_read_only_views(self) -> None:
        source = np.zeros((2, 3, 4), dtype=np.uint16)
        volume = Volume3D(source)
        source[0, 0, 0] = 1

        self.assertEqual(volume.shape, (2, 3, 4))
        self.assertEqual((volume.depth, volume.rows, volume.columns), (2, 3, 4))
        self.assertEqual(volume.cells.dtype, np.dtype(np.uint8))
        self.assertTrue(volume.cells.flags.c_contiguous)
        self.assertFalse(volume.cells.flags.writeable)
        self.assertEqual(volume.get_cell((0, 0, 0)), 0)
        with self.assertRaises(ValueError):
            volume.cells[0, 0, 0] = 1
        with self.assertRaises(AttributeError):
            volume.state_count = 3

    def test_invalid_state_counts_dtypes_and_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 2 and 256"):
            Volume3D.empty((1, 1, 1), state_count=257)
        with self.assertRaisesRegex(TypeError, "integers"):
            Volume3D(np.zeros((2, 2, 2), dtype=np.float32))
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            Volume3D(np.full((2, 2, 2), 2, dtype=np.uint8))
        with self.assertRaisesRegex(ValueError, "between 0 and 2"):
            Volume3D.empty((2, 2, 2), state_count=3, fill_state=3)

    def test_cell_fill_replace_and_copy_mutations_preserve_invariants(self) -> None:
        volume = Volume3D.empty((2, 3, 4), state_count=4)
        volume.set_cell((1, 2, 3), 3)
        self.assertEqual(volume.get_cell((1, 2, 3)), 3)
        with self.assertRaises(IndexError):
            volume.set_cell((-1, 0, 0), 1)
        with self.assertRaisesRegex(ValueError, "between 0 and 3"):
            volume.set_cell((0, 0, 0), 4)

        duplicate = volume.copy()
        duplicate.fill(2)
        self.assertEqual(volume.get_cell((0, 0, 0)), 0)
        self.assertEqual(duplicate.get_cell((0, 0, 0)), 2)

        volume.replace_cells(np.ones((2, 3, 4), dtype=np.uint8))
        self.assertEqual(int(volume.cells.sum()), 24)
        with self.assertRaisesRegex(ValueError, "does not match"):
            volume.replace_cells(np.zeros((2, 3, 3), dtype=np.uint8))

    def test_boundary_configuration_and_sampling_are_explicit(self) -> None:
        cells = np.zeros((3, 3, 3), dtype=np.uint8)
        cells[2, 2, 2] = 1
        volume = Volume3D(cells, outside_state=1)

        self.assertEqual(volume.sample((-1, -1, -1)), 1)
        self.assertEqual(
            volume.sample((-1, -1, -1), boundary=BOUNDARY_WRAP),
            1,
        )
        cells[1, 0, 0] = 1
        reflected = Volume3D(cells)
        self.assertEqual(
            reflected.sample((-1, 0, 0), boundary=BOUNDARY_REFLECT),
            1,
        )
        volume.boundary = BOUNDARY_WRAP
        self.assertEqual(volume.boundary, BOUNDARY_WRAP)
        with self.assertRaisesRegex(ValueError, "Unknown 3D boundary"):
            volume.boundary = "infinite"
        with self.assertRaisesRegex(ValueError, "outside_state"):
            volume.outside_state = 2

    def test_slice_api_preserves_axis_orientation_and_copy_semantics(self) -> None:
        cells = np.arange(24, dtype=np.uint8).reshape((2, 3, 4))
        volume = Volume3D(cells, state_count=24)

        np.testing.assert_array_equal(volume.extract_slice(AXIS_Z, 1), cells[1, :, :])
        np.testing.assert_array_equal(volume.extract_slice(AXIS_Y, 1), cells[:, 1, :])
        np.testing.assert_array_equal(volume.extract_slice(AXIS_X, 2), cells[:, :, 2])
        self.assertEqual(volume.slice_shape(AXIS_Z), (3, 4))
        self.assertEqual(volume.slice_shape(AXIS_Y), (2, 4))
        self.assertEqual(volume.slice_shape(AXIS_X), (2, 3))

        copied = volume.extract_slice(AXIS_Z, 0)
        copied.fill(0)
        self.assertNotEqual(volume.get_cell((0, 0, 1)), 0)
        zero_copy = volume.extract_slice(AXIS_Z, 0, copy=False)
        self.assertFalse(zero_copy.flags.writeable)
        with self.assertRaises(ValueError):
            zero_copy[0, 0] = 1

    def test_slice_writes_validate_axis_index_shape_and_state(self) -> None:
        volume = Volume3D.empty((2, 3, 4), state_count=3)
        plane = np.full((2, 4), 2, dtype=np.uint8)

        volume.write_slice(AXIS_Y, 1, plane)

        np.testing.assert_array_equal(volume.extract_slice(AXIS_Y, 1), plane)
        with self.assertRaisesRegex(ValueError, "Slice axis"):
            volume.extract_slice("time", 0)
        with self.assertRaises(IndexError):
            volume.extract_slice(AXIS_Z, -1)
        with self.assertRaises(TypeError):
            volume.extract_slice(AXIS_Z, True)
        with self.assertRaisesRegex(ValueError, "does not match"):
            volume.write_slice(AXIS_Y, 0, np.zeros((3, 4), dtype=np.uint8))
        with self.assertRaisesRegex(ValueError, "between 0 and 2"):
            volume.write_slice(AXIS_Y, 0, np.full((2, 4), 3, dtype=np.uint8))

    def test_fixed_and_wrap_neighbor_counts_differ_at_volume_edges(self) -> None:
        cells = np.zeros((3, 3, 3), dtype=np.uint8)
        cells[2, 2, 2] = 1
        volume = Volume3D(cells)

        fixed = volume.neighbor_counts(boundary=BOUNDARY_FIXED)
        wrapped = volume.neighbor_counts(boundary=BOUNDARY_WRAP)

        self.assertEqual(int(fixed[0, 0, 0]), 0)
        self.assertEqual(int(wrapped[0, 0, 0]), 1)
        self.assertEqual(fixed.dtype, np.dtype(np.uint8))

    def test_fixed_nonzero_outside_state_contributes_to_edge_counts(self) -> None:
        volume = Volume3D.empty(
            (3, 3, 3),
            boundary=BOUNDARY_FIXED,
            outside_state=1,
        )

        counts = volume.neighbor_counts(active_states=(1,))

        self.assertEqual(int(counts[0, 0, 0]), 19)
        self.assertEqual(int(counts[1, 1, 1]), 0)

    def test_neighborhood_selection_changes_vectorized_counts(self) -> None:
        volume = Volume3D.empty((3, 3, 3))
        for position in (
            (0, 1, 1),
            (2, 1, 1),
            (1, 0, 1),
            (1, 2, 1),
            (1, 1, 0),
            (1, 1, 2),
            (0, 0, 0),
        ):
            volume.set_cell(position, 1)

        face_counts = volume.neighbor_counts(
            neighborhood=VON_NEUMANN_NEIGHBORHOOD
        )
        moore_counts = volume.neighbor_counts(neighborhood=MOORE_NEIGHBORHOOD)

        self.assertEqual(int(face_counts[1, 1, 1]), 6)
        self.assertEqual(int(moore_counts[1, 1, 1]), 7)
        values = volume.neighbor_values(
            (1, 1, 1),
            neighborhood=VON_NEUMANN_NEIGHBORHOOD,
        )
        self.assertEqual(values.dtype, np.dtype(np.uint8))
        self.assertEqual(values.tolist(), [1] * 6)

    def test_none_active_states_counts_every_nonzero_state(self) -> None:
        volume = Volume3D.empty((3, 3, 3), state_count=4)
        volume.set_cell((1, 1, 0), 2)
        volume.set_cell((1, 1, 2), 3)

        any_nonzero = volume.neighbor_counts(
            active_states=None,
            neighborhood=VON_NEUMANN_NEIGHBORHOOD,
        )
        only_two = volume.neighbor_counts(
            active_states=(2,),
            neighborhood=VON_NEUMANN_NEIGHBORHOOD,
        )

        self.assertEqual(int(any_nonzero[1, 1, 1]), 2)
        self.assertEqual(int(only_two[1, 1, 1]), 1)

    def test_vectorized_counts_match_scalar_sampling_for_every_boundary(self) -> None:
        rng = np.random.default_rng(73)
        volume = Volume3D(
            rng.integers(0, 2, size=(4, 4, 4), dtype=np.uint8)
        )

        for boundary in (BOUNDARY_FIXED, BOUNDARY_WRAP, BOUNDARY_REFLECT):
            for neighborhood in (
                MOORE_NEIGHBORHOOD,
                VON_NEUMANN_NEIGHBORHOOD,
            ):
                with self.subTest(
                    boundary=boundary,
                    neighborhood=neighborhood.key,
                ):
                    counts = volume.neighbor_counts(
                        active_states=(1,),
                        boundary=boundary,
                        neighborhood=neighborhood,
                    )
                    for position in np.ndindex(volume.shape):
                        expected = int(
                            np.count_nonzero(
                                volume.neighbor_values(
                                    position,
                                    boundary=boundary,
                                    neighborhood=neighborhood,
                                )
                                == 1
                            )
                        )
                        self.assertEqual(int(counts[position]), expected)


if __name__ == "__main__":
    unittest.main()
