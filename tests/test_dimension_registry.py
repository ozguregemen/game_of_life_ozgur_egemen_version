import unittest

from dimension_registry import (
    DIMENSION_BY_KEY,
    DIMENSION_DEFINITIONS,
    DIMENSION_KEYS,
    get_dimension_definition,
)


class DimensionRegistryTests(unittest.TestCase):
    def test_dimensions_are_unique_and_ordered(self) -> None:
        keys = tuple(definition.key for definition in DIMENSION_DEFINITIONS)
        self.assertEqual(keys, DIMENSION_KEYS)
        self.assertEqual(len(keys), len(set(keys)))

    def test_expected_dimensions_and_availability(self) -> None:
        self.assertEqual(set(DIMENSION_BY_KEY), {"1d", "2d", "3d"})
        self.assertTrue(DIMENSION_BY_KEY["1d"].available)
        self.assertTrue(DIMENSION_BY_KEY["2d"].available)
        self.assertTrue(DIMENSION_BY_KEY["3d"].available)

    def test_all_dimensions_have_user_facing_metadata(self) -> None:
        for definition in DIMENSION_DEFINITIONS:
            with self.subTest(dimension=definition.key):
                self.assertTrue(definition.name)
                self.assertTrue(definition.summary)
                self.assertTrue(definition.status_hint)
                self.assertEqual(len(definition.accent), 3)

    def test_unknown_dimension_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_dimension_definition("4d")


if __name__ == "__main__":
    unittest.main()
