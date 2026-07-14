import unittest

from mode_registry import (
    MODE_BY_KEY,
    MODE_DEFINITIONS,
    MODE_KEYS,
    get_mode_definition,
)


class ModeRegistryTests(unittest.TestCase):
    def test_mode_keys_are_unique_and_ordered(self) -> None:
        keys = tuple(definition.key for definition in MODE_DEFINITIONS)
        self.assertEqual(keys, MODE_KEYS)
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_modes_have_user_facing_metadata(self) -> None:
        for definition in MODE_DEFINITIONS:
            with self.subTest(mode=definition.key):
                self.assertTrue(definition.name)
                self.assertTrue(definition.summary)
                self.assertTrue(definition.status_hint)
                self.assertEqual(len(definition.accent), 3)
                self.assertTrue(all(0 <= channel <= 255 for channel in definition.accent))

    def test_expected_modes_are_registered(self) -> None:
        self.assertEqual(
            set(MODE_BY_KEY),
            {
                "life",
                "immigration",
                "brians_brain",
                "langtons_ant",
                "wireworld",
                "cyclic_automaton",
            },
        )

    def test_unknown_mode_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_mode_definition("missing")


if __name__ == "__main__":
    unittest.main()
