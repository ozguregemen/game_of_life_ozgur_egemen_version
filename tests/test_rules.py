import unittest

from rules import apply_rules_2d, find_patterns


class ConwayRuleTests(unittest.TestCase):
    def test_block_remains_stable(self) -> None:
        grid = [
            [0, 0, 0, 0],
            [0, 1, 1, 0],
            [0, 1, 1, 0],
            [0, 0, 0, 0],
        ]

        result = apply_rules_2d(grid)

        self.assertEqual(
            [[1 if cell else 0 for cell in row] for row in result],
            grid,
        )

    def test_blinker_returns_to_start_after_two_generations(self) -> None:
        grid = [
            [0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0],
        ]

        second_generation = apply_rules_2d(apply_rules_2d(grid))

        self.assertEqual(
            [[1 if cell else 0 for cell in row] for row in second_generation],
            grid,
        )

    def test_lonely_cell_dies(self) -> None:
        grid = [[0, 0, 0], [0, 1, 0], [0, 0, 0]]
        self.assertEqual(apply_rules_2d(grid), [[0, 0, 0]] * 3)

    def test_dead_cell_with_three_neighbors_is_born(self) -> None:
        grid = [[1, 1, 0], [1, 0, 0], [0, 0, 0]]
        self.assertEqual(apply_rules_2d(grid)[1][1], 1)

    def test_surviving_cell_age_increments(self) -> None:
        grid = [[2, 2, 0], [2, 0, 0], [0, 0, 0]]
        result = apply_rules_2d(grid)
        self.assertEqual(result[0][0], 3)
        self.assertEqual(result[1][1], 1)


class PatternRecognitionTests(unittest.TestCase):
    def assert_pattern_recognized(
        self,
        pattern: list[list[int]],
        expected_name: str,
    ) -> None:
        grid = [[0] * 9 for _ in range(9)]
        for row, values in enumerate(pattern, start=2):
            for col, value in enumerate(values, start=2):
                grid[row][col] = value

        names = {match["pattern"]["name"] for match in find_patterns(grid)}
        self.assertIn(expected_name, names)

    def test_recognizes_block(self) -> None:
        self.assert_pattern_recognized([[1, 1], [1, 1]], "block")

    def test_recognizes_blinker(self) -> None:
        self.assert_pattern_recognized([[1, 1, 1]], "blinker")

    def test_recognizes_glider(self) -> None:
        self.assert_pattern_recognized(
            [[0, 1, 0], [0, 0, 1], [1, 1, 1]],
            "glider",
        )


if __name__ == "__main__":
    unittest.main()
