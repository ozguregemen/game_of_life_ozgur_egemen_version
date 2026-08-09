import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from custom_rules import (
    KIND_GENERATIONS,
    KIND_LIFE_LIKE,
    CustomRuleDefinition,
    custom_rule_from_1d,
    custom_rule_from_2d,
    custom_rule_from_3d_generations,
    custom_rule_from_3d_life,
    delete_custom_rule,
    export_custom_rule_package,
    get_custom_rule,
    get_custom_rule_packages,
    get_custom_rules,
    import_custom_rule_package,
    parse_generations_notation,
    parse_life_like_notation,
    parse_neighbor_counts,
    refresh_custom_rule_cache,
    refresh_custom_rule_package_cache,
    safe_custom_rule_filename,
    save_custom_rule,
)
from one_dimensional_ca import FAMILY_TOTALISTIC, RuleSpec
from three_dimensional_generations import GenerationsRule3D
from three_dimensional_rules import LifeLikeRule3D


class CustomRuleTests(unittest.TestCase):
    def tearDown(self) -> None:
        refresh_custom_rule_cache()
        refresh_custom_rule_package_cache()

    def test_safe_filename_blocks_traversal_empty_and_reserved_names(self) -> None:
        self.assertEqual(safe_custom_rule_filename("../A:B"), "a_b")
        self.assertEqual(safe_custom_rule_filename("CON"), "_con")
        with self.assertRaises(ValueError):
            safe_custom_rule_filename("   ")

    def test_neighbor_count_parsing_supports_compact_multi_digit_and_ranges(self) -> None:
        self.assertEqual(parse_neighbor_counts("23", 8), (2, 3))
        self.assertEqual(parse_neighbor_counts("567", 26), (5, 6, 7))
        self.assertEqual(parse_neighbor_counts("10", 26), (10,))
        self.assertEqual(parse_neighbor_counts("13-15,18", 26), (13, 14, 15, 18))
        with self.assertRaisesRegex(ValueError, "between 0 and 8"):
            parse_neighbor_counts("9", 8)

    def test_notation_parsers_are_strict_and_normalized(self) -> None:
        self.assertEqual(parse_life_like_notation("b36/s23", maximum=8), ((3, 6), (2, 3)))
        self.assertEqual(
            parse_generations_notation("4/4/5/M"),
            ((4,), (4,), 5, "moore"),
        )
        self.assertEqual(
            parse_generations_notation("/4/2/M"),
            ((), (4,), 2, "moore"),
        )
        self.assertEqual(
            parse_generations_notation("13-26/13-14,17-19/2/M"),
            (tuple(range(13, 27)), (13, 14, 17, 18, 19), 2, "moore"),
        )
        with self.assertRaisesRegex(ValueError, "B3/S23"):
            parse_life_like_notation("3/23", maximum=8)
        with self.assertRaisesRegex(ValueError, "state count"):
            parse_generations_notation("4/4/x/M")

    def test_dimension_specific_factories_build_runtime_rules(self) -> None:
        one_d = custom_rule_from_1d(
            "Totalistic Test",
            RuleSpec(FAMILY_TOTALISTIC, 10, 2, 1),
        )
        two_d = custom_rule_from_2d("Replicator", "B1357/S1357")
        three_d = custom_rule_from_3d_life("Spatial Test", "B6/S567")
        generations = custom_rule_from_3d_generations("Cooling Test", "4/4/5/M")

        self.assertEqual(one_d.one_dimensional_spec().code, 10)
        self.assertEqual(two_d.life_like_2d()["birth"], [1, 3, 5, 7])
        self.assertIsInstance(three_d.three_dimensional_rule(), LifeLikeRule3D)
        self.assertIsInstance(
            generations.three_dimensional_rule(),
            GenerationsRule3D,
        )
        self.assertEqual(generations.kind, KIND_GENERATIONS)
        self.assertEqual(three_d.kind, KIND_LIFE_LIKE)

    def test_utf8_json_round_trip_cache_collision_and_delete(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("custom_rules.CUSTOM_RULE_DIRECTORY", root):
                refresh_custom_rule_cache()
                original = custom_rule_from_2d("Özel Yaşam", "B36/S23")
                saved = save_custom_rule(original)

                self.assertEqual(get_custom_rule(saved.key), saved)
                self.assertEqual(get_custom_rules("2d"), (saved,))
                self.assertTrue((root / "2d" / "özel_yaşam.json").is_file())
                with self.assertRaises(FileExistsError):
                    save_custom_rule(original)
                self.assertTrue(delete_custom_rule(saved.key))
                self.assertFalse(delete_custom_rule(saved.key))
                self.assertFalse(get_custom_rules("2d"))

    def test_corrupt_and_wrong_dimension_json_are_skipped(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "2d"
            target.mkdir(parents=True)
            (target / "broken.json").write_text("{bad", encoding="utf-8")
            (target / "oversized.json").write_bytes(b" " * (64 * 1024 + 1))
            wrong = custom_rule_from_3d_life("Wrong Folder", "B6/S567")
            (target / "wrong.json").write_text(
                json.dumps(wrong.as_document()),
                encoding="utf-8",
            )
            with patch("custom_rules.CUSTOM_RULE_DIRECTORY", root):
                with self.assertWarns(UserWarning):
                    refresh_custom_rule_cache()
                self.assertFalse(get_custom_rules())

    def test_rule_package_export_import_is_versioned_and_collision_safe(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rules = root / "rules"
            packages = root / "packages"
            with (
                patch("custom_rules.CUSTOM_RULE_DIRECTORY", rules),
                patch("custom_rules.CUSTOM_RULE_PACKAGE_DIRECTORY", packages),
            ):
                refresh_custom_rule_cache()
                refresh_custom_rule_package_cache()
                original = custom_rule_from_2d("Özel Paylaşım", "B36/S23")

                first_path = export_custom_rule_package(original)
                second_path = export_custom_rule_package(original)
                self.assertNotEqual(first_path, second_path)
                self.assertTrue(first_path.name.endswith(".rule.json"))
                packages_found = get_custom_rule_packages("2d")
                self.assertEqual(len(packages_found), 2)
                self.assertEqual(packages_found[0].rule, original)

                imported = import_custom_rule_package(packages_found[0])
                self.assertEqual(imported, original)
                self.assertEqual(get_custom_rules("2d"), (original,))
                with self.assertRaises(FileExistsError):
                    import_custom_rule_package(packages_found[1])

    def test_corrupt_rule_packages_are_skipped_without_hiding_valid_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("custom_rules.CUSTOM_RULE_PACKAGE_DIRECTORY", root):
                valid_rule = custom_rule_from_3d_life("Shared Bays", "B6/S567")
                valid_document = {
                    "schema": "cellular-automata-lab-rule-package",
                    "version": 1,
                    "exported_at": "2026-08-09T00:00:00+00:00",
                    "application_version": "0.9.0",
                    "rule": valid_rule.as_document(),
                }
                (root / "valid.rule.json").write_text(
                    json.dumps(valid_document),
                    encoding="utf-8",
                )
                (root / "broken.rule.json").write_text("{bad", encoding="utf-8")
                (root / "oversized.rule.json").write_bytes(
                    b" " * (64 * 1024 + 1)
                )

                with self.assertWarns(UserWarning):
                    refresh_custom_rule_package_cache()

                packages_found = get_custom_rule_packages("3d")
                self.assertEqual(len(packages_found), 1)
                self.assertEqual(packages_found[0].rule, valid_rule)

    def test_invalid_definition_rejects_cross_dimension_kind(self) -> None:
        with self.assertRaisesRegex(ValueError, "currently support"):
            CustomRuleDefinition(
                "custom:2d:bad",
                "Bad",
                "2d",
                KIND_GENERATIONS,
                {"birth": [3], "survival": [2, 3]},
            )


if __name__ == "__main__":
    unittest.main()
