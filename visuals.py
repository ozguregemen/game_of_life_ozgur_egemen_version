from __future__ import annotations

from typing import Any

import pygame

from themes import THEMES


class Minimap:
    """Compact overview for both 2D and simple 3D-list grids."""

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        grid_size: tuple[int, int],
        theme: str = "classic",
    ) -> None:
        self.rect = pygame.Rect(x, y, width, height)
        self.grid_size = grid_size
        self.theme = theme
        self.cell_size = max(
            1,
            min(width // max(1, grid_size[1]), height // max(1, grid_size[0])),
        )
        self.offset_x = 0
        self.offset_y = 0
        self.zoom_level = 1.0

    def update(self, offset_x: int, offset_y: int, zoom_level: float) -> None:
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.zoom_level = zoom_level

    @staticmethod
    def _is_alive(value: Any) -> bool:
        if isinstance(value, (list, tuple)):
            return any(Minimap._is_alive(item) for item in value)
        return bool(value and value > 0)

    def draw(self, screen: pygame.Surface, grid: list[list[Any]]) -> None:
        pygame.draw.rect(screen, THEMES[self.theme]["menu"], self.rect)
        pygame.draw.rect(screen, THEMES[self.theme]["menu_text"], self.rect, 2)

        rows = min(self.grid_size[0], len(grid))
        cols = min(self.grid_size[1], len(grid[0]) if rows else 0)
        for row in range(rows):
            for col in range(cols):
                if not self._is_alive(grid[row][col]):
                    continue
                cell_rect = pygame.Rect(
                    self.rect.x + col * self.cell_size,
                    self.rect.y + row * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                pygame.draw.rect(screen, THEMES[self.theme]["cell"], cell_rect)


class CellTransition:
    """Tracks short birth/death transitions for individual cells."""

    def __init__(self, duration: float = 0.2) -> None:
        if duration <= 0:
            raise ValueError("duration must be positive")
        self.duration = duration
        self.transitions: dict[tuple[int, int], dict[str, float]] = {}

    def start_transition(
        self,
        x: int,
        y: int,
        start_value: float,
        end_value: float,
    ) -> None:
        self.transitions[(x, y)] = {
            "start": float(start_value),
            "end": float(end_value),
            "progress": 0.0,
        }

    def update(self, delta_time: float) -> None:
        completed: list[tuple[int, int]] = []
        for position, transition in self.transitions.items():
            transition["progress"] = min(
                1.0,
                transition["progress"] + delta_time / self.duration,
            )
            if transition["progress"] >= 1.0:
                completed.append(position)

        for position in completed:
            del self.transitions[position]

    def get_state(self, x: int, y: int) -> dict[str, float] | None:
        """Return start/end/progress values for rendering."""
        transition = self.transitions.get((x, y))
        if transition is None:
            return None
        return transition.copy()

    def get_value(self, x: int, y: int) -> float | None:
        """Backward-compatible interpolated value accessor."""
        transition = self.transitions.get((x, y))
        if transition is None:
            return None
        progress = transition["progress"]
        return (
            transition["start"]
            + (transition["end"] - transition["start"]) * progress
        )


class GridOverlay:
    def __init__(self, cell_size: int, theme: str = "classic") -> None:
        self.cell_size = cell_size
        self.theme = theme
        self.show_coordinates = True
        self.show_quadrants = True

    def draw(
        self,
        screen: pygame.Surface,
        offset_x: int,
        offset_y: int,
        width: int,
        height: int,
    ) -> None:
        if not self.show_coordinates and not self.show_quadrants:
            return

        cell_size = max(1, self.cell_size)
        if self.show_coordinates and cell_size >= 10:
            coordinate_font = pygame.font.SysFont("Arial", 12)
            for x in range(offset_x, offset_x + width, cell_size * 5):
                cell_index = (x - offset_x) // cell_size
                text_surface = coordinate_font.render(
                    str(cell_index),
                    True,
                    THEMES[self.theme]["text"],
                )
                screen.blit(text_surface, (x + 2, offset_y + 2))

            for y in range(offset_y, offset_y + height, cell_size * 5):
                cell_index = (y - offset_y) // cell_size
                text_surface = coordinate_font.render(
                    str(cell_index),
                    True,
                    THEMES[self.theme]["text"],
                )
                screen.blit(text_surface, (offset_x + 2, y + 2))

        if self.show_quadrants:
            center_x = offset_x + width // 2
            center_y = offset_y + height // 2
            pygame.draw.line(
                screen,
                THEMES[self.theme]["grid"],
                (center_x, offset_y),
                (center_x, offset_y + height),
                2,
            )
            pygame.draw.line(
                screen,
                THEMES[self.theme]["grid"],
                (offset_x, center_y),
                (offset_x + width, center_y),
                2,
            )


def get_enhanced_age_color(age: int, theme: str = "classic") -> Any:
    """Return a theme-aware color that changes with cell age."""
    if theme not in THEMES:
        theme = "classic"
    if age <= 0:
        return THEMES[theme]["background"]

    if theme == "classic":
        if age < 5:
            return (0, min(255, 100 + age * 30), 0)
        if age < 10:
            return (min(255, age * 25), 255, 0)
        if age < 15:
            return (255, max(0, 255 - (age - 10) * 25), 0)
        return (255, 0, 0)

    if theme == "neon":
        hue = (age * 20) % 360
        color = pygame.Color(0, 0, 0)
        color.hsva = (hue, 100, 100, 100)
        return color

    if theme == "pastel":
        if age < 5:
            return (255, max(0, 200 - age * 20), max(0, 200 - age * 20))
        if age < 10:
            return (255, max(0, 150 - age * 10), max(0, 150 - age * 10))
        return (255, 100, 100)

    if theme == "colorblind":
        brightness = min(1.0, 0.58 + age * 0.035)
        return tuple(int(channel * brightness) for channel in (240, 228, 66))

    return THEMES[theme]["cell"]
