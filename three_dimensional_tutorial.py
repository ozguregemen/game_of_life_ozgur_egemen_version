"""Full-screen, mode-aware tutorial for the three-dimensional workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import pygame

from three_dimensional_modes import MODE_GENERATIONS, MODE_SPATIAL_LIFE
from three_dimensional_patterns import BAYS_5766_GLIDER
from three_dimensional_tutorial_content import (
    THREE_D_FOUNDATION_PAGES,
    THREE_D_MODE_GUIDES,
)
from two_dimensional_tutorial import TwoDimensionalTutorial
from two_dimensional_tutorial_content import TutorialPage, TutorialSection


@dataclass(frozen=True)
class ThreeDimensionalTutorialServices:
    """Application resources and callbacks used by the 3D tutorial."""

    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    current_mode: Callable[[], str]
    current_rule_label: Callable[[], str]
    open_url: Callable[[str], bool]
    start_experiment: Callable[[str], None]
    pause: Callable[[], None]
    set_status: Callable[[str, float], None]


class ThreeDimensionalTutorial(TwoDimensionalTutorial):
    """Shared 3D foundations plus a guide for only the active 3D mode."""

    FOUNDATION_ACCENT = (186, 118, 255)
    SPATIAL_ACCENT = (112, 224, 152)
    GENERATIONS_ACCENT = (225, 124, 255)
    CYAN = (84, 204, 255)
    PURPLE = (172, 102, 236)
    ORANGE = (250, 154, 68)
    RED = (246, 96, 108)

    def __init__(self, services: ThreeDimensionalTutorialServices) -> None:
        super().__init__(services)  # type: ignore[arg-type]
        self.services = services

    @property
    def mode_key(self) -> str:
        mode = self.services.current_mode()
        return mode if mode in THREE_D_MODE_GUIDES else MODE_SPATIAL_LIFE

    @property
    def guide(self):
        return THREE_D_MODE_GUIDES[self.mode_key]

    @property
    def foundation_pages(self) -> tuple[TutorialPage, ...]:
        return THREE_D_FOUNDATION_PAGES

    @property
    def foundation_tab_label(self) -> str:
        return "3D FOUNDATIONS"

    @property
    def mode_accent(self) -> tuple[int, int, int]:
        return (
            self.SPATIAL_ACCENT
            if self.mode_key == MODE_SPATIAL_LIFE
            else self.GENERATIONS_ACCENT
        )

    @staticmethod
    def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
        return tuple(max(0, min(255, round(component * factor))) for component in color)

    def _voxel_faces(
        self,
        center: tuple[float, float],
        size: float,
    ) -> tuple[tuple[tuple[int, int], ...], ...]:
        """Return top, left, and right polygons for one isometric cube."""
        cx, cy = center
        half = size / 2
        rise = size * 0.30
        drop = size * 0.58
        top = (
            (round(cx), round(cy - rise)),
            (round(cx + half), round(cy)),
            (round(cx), round(cy + rise)),
            (round(cx - half), round(cy)),
        )
        left = (
            top[3],
            top[2],
            (top[2][0], round(top[2][1] + drop)),
            (top[3][0], round(top[3][1] + drop)),
        )
        right = (
            top[2],
            top[1],
            (top[1][0], round(top[1][1] + drop)),
            (top[2][0], round(top[2][1] + drop)),
        )
        return top, left, right

    def _draw_voxel(
        self,
        surface: pygame.Surface,
        center: tuple[float, float],
        size: float,
        color: tuple[int, int, int],
        *,
        wire: bool = False,
    ) -> None:
        theme = self.services.theme()
        top, left, right = self._voxel_faces(center, size)
        if wire:
            for face in (top, left, right):
                pygame.draw.polygon(surface, color, face, 2)
            return
        pygame.draw.polygon(surface, self._shade(color, 1.12), top)
        pygame.draw.polygon(surface, self._shade(color, 0.72), left)
        pygame.draw.polygon(surface, self._shade(color, 0.90), right)
        for face in (top, left, right):
            pygame.draw.polygon(surface, theme["background"], face, 1)

    def _draw_cluster(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        voxels: Sequence[tuple[int, int, int, tuple[int, int, int], bool]],
        *,
        scale: float = 1.0,
    ) -> None:
        """Draw a small voxel coordinate set as an isometric teaching diagram."""
        theme = self.services.theme()
        pygame.draw.rect(surface, theme["stats_bar"], rect, border_radius=8)
        pygame.draw.rect(surface, theme["grid"], rect, 1, border_radius=8)
        if not voxels:
            return
        extent = max(
            2,
            max(max(abs(x), abs(y), abs(z)) for x, y, z, _, _ in voxels) * 2 + 2,
        )
        unit = min(rect.width / (extent * 1.35), rect.height / (extent * 1.15)) * scale
        unit = max(12.0, min(45.0, unit))
        origin_x = rect.centerx
        origin_y = rect.centery - unit * 0.22
        ordered = sorted(voxels, key=lambda item: (item[0] + item[1], item[2], item[0]))
        for x, y, z, color, wire in ordered:
            screen_x = origin_x + (x - y) * unit * 0.72
            screen_y = origin_y + (x + y) * unit * 0.34 - z * unit * 0.82
            self._draw_voxel(surface, (screen_x, screen_y), unit * 0.86, color, wire=wire)

    def _draw_title(self, surface: pygame.Surface, rect: pygame.Rect, text: str) -> int:
        theme = self.services.theme()
        heading = self._font(self._font_sizes()[1], bold=True)
        rendered = heading.render(text, True, theme["text"])
        surface.blit(rendered, rendered.get_rect(midtop=(rect.centerx, rect.y + 14)))
        return rect.y + 52

    def _draw_arrow(self, surface: pygame.Surface, left: int, right: int, y: int) -> None:
        middle = (left + right) // 2
        pygame.draw.line(surface, self.GOLD, (middle - 20, y), (middle + 13, y), 4)
        pygame.draw.polygon(
            surface,
            self.GOLD,
            ((middle + 22, y), (middle + 8, y - 8), (middle + 8, y + 8)),
        )

    def _draw_visual_with_sections(
        self,
        canvas: pygame.Surface,
        y: int,
        visual_height: int,
        draw_visual: Callable[[pygame.Surface, pygame.Rect], None],
    ) -> int:
        visual = pygame.Rect(0, y, canvas.get_width(), visual_height)
        draw_visual(canvas, visual)
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, visual.bottom + 16, canvas.get_width(), 1200),
        )

    def _draw_volume_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "ONE COORDINATE (x, y, z) STORES ONE VOXEL STATE")
        viewport = pygame.Rect(rect.x + 45, top, rect.width * 3 // 5, rect.height - 70)
        voxels = []
        for axis, color in (((1, 0, 0), self.RED), ((0, 1, 0), self.GREEN), ((0, 0, 1), self.CYAN)):
            for distance in range(1, 4):
                voxels.append((axis[0] * distance, axis[1] * distance, axis[2] * distance, color, False))
        voxels.append((0, 0, 0, self.GOLD, False))
        self._draw_cluster(surface, viewport, voxels, scale=1.0)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        labels = (
            ("X", self.RED, "+ columns"),
            ("Y", self.GREEN, "+ rows"),
            ("Z", self.CYAN, "+ depth / layers"),
        )
        side = pygame.Rect(viewport.right + 28, top + 15, rect.right - viewport.right - 55, rect.height - 100)
        for index, (name, color, detail) in enumerate(labels):
            card = pygame.Rect(side.x, side.y + index * 78, side.width, 64)
            pygame.draw.rect(surface, theme["stats_bar"], card, border_radius=7)
            pygame.draw.rect(surface, color, card, 2, border_radius=7)
            axis_text = heading.render(name, True, color)
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(axis_text, axis_text.get_rect(midleft=(card.x + 17, card.centery)))
            surface.blit(detail_text, detail_text.get_rect(midleft=(card.x + 65, card.centery)))

    @staticmethod
    def _face_neighbors() -> tuple[tuple[int, int, int], ...]:
        return (
            (-1, 0, 0),
            (1, 0, 0),
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
            (0, 0, 1),
        )

    @staticmethod
    def _moore_neighbors() -> tuple[tuple[int, int, int], ...]:
        return tuple(
            (x, y, z)
            for z in (-1, 0, 1)
            for y in (-1, 0, 1)
            for x in (-1, 0, 1)
            if (x, y, z) != (0, 0, 0)
        )

    def _draw_neighborhoods_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "THE FOCUS VOXEL IS GOLD AND NEVER COUNTS ITSELF")
        gap = 22
        width = (rect.width - 54 - gap) // 2
        label = self._font(self._font_sizes()[3], bold=True)
        heading = self._font(self._font_sizes()[1], bold=True)
        diagrams = (
            ("6 FACE NEIGHBORS", self._face_neighbors(), self.CYAN, "±X, ±Y, ±Z only"),
            ("26 MOORE NEIGHBORS", self._moore_neighbors(), self.PURPLE, "6 faces + 12 edges + 8 corners"),
        )
        for index, (title, coordinates, color, detail) in enumerate(diagrams):
            card = pygame.Rect(rect.x + 16 + index * (width + gap), top, width, rect.height - 68)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 2, border_radius=9)
            title_text = heading.render(title, True, color)
            surface.blit(title_text, title_text.get_rect(midtop=(card.centerx, card.y + 10)))
            cluster = [(x, y, z, color, False) for x, y, z in coordinates]
            cluster.append((0, 0, 0, self.GOLD, False))
            self._draw_cluster(surface, pygame.Rect(card.x + 12, card.y + 42, card.width - 24, card.height - 91), cluster, scale=0.82)
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 11)))

    def _draw_synchronous_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "GENERATION t IS READ-ONLY UNTIL EVERY NEXT STATE IS READY")
        gap = 42
        width = (rect.width - 48 - gap * 2) // 3
        frames = (
            ("1. FREEZE OLD VOLUME", ((0, 0, 0), (1, 0, 0), (0, 1, 0)), "all counts read this snapshot"),
            ("2. CALCULATE NEXT", ((0, 0, 0),), "write into a separate volume"),
            ("3. COMMIT TOGETHER", ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)), "birth appears only after commit"),
        )
        heading = self._font(self._font_sizes()[3], bold=True)
        for index, (title, coordinates, detail) in enumerate(frames):
            card = pygame.Rect(rect.x + 16 + index * (width + gap), top, width, rect.height - 70)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, self.accent, card, 2, border_radius=9)
            title_text = heading.render(title, True, theme["text"])
            surface.blit(title_text, title_text.get_rect(midtop=(card.centerx, card.y + 10)))
            voxels = [(x, y, z, self.accent, False) for x, y, z in coordinates]
            if index == 1:
                voxels = [(0, 0, 0, self.GOLD, True)]
            self._draw_cluster(surface, pygame.Rect(card.x + 13, card.y + 40, card.width - 26, card.height - 95), voxels)
            detail_text = heading.render(detail, True, theme["menu_text"])
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 10)))
            if index < 2:
                self._draw_arrow(surface, card.right, card.right + gap, card.centery)

    def _sample_dense_cluster(self) -> tuple[tuple[int, int, int], ...]:
        return tuple(
            (x, y, z)
            for z in range(-2, 3)
            for y in range(-2, 3)
            for x in range(-2, 3)
            if (x * x + y * y + z * z <= 7 and (x + 2 * y + z) % 3 != 0)
        )

    def _draw_visibility_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "FOUR VIEWS OF THE SAME VOLUME - NO CELL STATE CHANGES")
        gap = 16
        width = (rect.width - 40 - gap * 3) // 4
        coordinates = self._sample_dense_cluster()
        labels = (
            ("FULL", "outer shell hides depth", coordinates, self.accent),
            ("OPACITY", "interior remains in context", coordinates[::2], self.CYAN),
            ("CLIP", "keep one side of a plane", tuple(p for p in coordinates if p[0] <= 0), self.ORANGE),
            ("LAYER", "show exactly z = 0", tuple(p for p in coordinates if p[2] == 0), self.GREEN),
        )
        heading = self._font(self._font_sizes()[3], bold=True)
        for index, (title, detail, points, color) in enumerate(labels):
            card = pygame.Rect(rect.x + 14 + index * (width + gap), top, width, rect.height - 68)
            pygame.draw.rect(surface, theme["button"], card, border_radius=8)
            pygame.draw.rect(surface, color, card, 2, border_radius=8)
            title_text = heading.render(title, True, color)
            surface.blit(title_text, title_text.get_rect(midtop=(card.centerx, card.y + 9)))
            voxels = [(x, y, z, color, False) for x, y, z in points]
            self._draw_cluster(surface, pygame.Rect(card.x + 10, card.y + 37, card.width - 20, card.height - 89), voxels, scale=0.8)
            detail_text = heading.render(detail, True, theme["menu_text"])
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 9)))

    def _draw_camera_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "CAMERA MOTION CHANGES THE PROJECTION, NOT THE VOLUME")
        center = pygame.Rect(rect.centerx - 180, top + 12, 360, rect.height - 95)
        cube_color = self.PURPLE
        self._draw_voxel(surface, center.center, 185, cube_color, wire=True)
        pygame.draw.arc(surface, self.GOLD, center.inflate(190, 80), 0.2, 5.6, 5)
        pygame.draw.polygon(surface, self.GOLD, ((center.right + 85, center.centery - 25), (center.right + 64, center.centery - 37), (center.right + 69, center.centery - 13)))
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for text_value, color, position in (
            ("X FACE", self.RED, (center.right + 115, center.centery + 20)),
            ("Y FACE", self.GREEN, (center.x - 105, center.centery + 20)),
            ("Z FACE", self.CYAN, (center.centerx, center.y - 18)),
        ):
            rendered = heading.render(text_value, True, color)
            surface.blit(rendered, rendered.get_rect(center=position))
        note = label.render("Click an orientation-cube face to snap that face toward the screen", True, theme["menu_text"])
        surface.blit(note, note.get_rect(midbottom=(rect.centerx, rect.bottom - 15)))

    def _draw_editing_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "THE POINTER RAY CHOOSES DEPTH AND THE HIT FACE")
        gap = 38
        width = (rect.width - 48 - gap * 2) // 3
        cards = (
            ("1. RAYCAST", "first occupied voxel is hit", self.CYAN),
            ("2. LEFT CLICK", "add outside the hit face", self.GREEN),
            ("3. RIGHT CLICK", "erase the hit voxel", self.RED),
        )
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (title, detail, color) in enumerate(cards):
            card = pygame.Rect(rect.x + 16 + index * (width + gap), top, width, rect.height - 70)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 2, border_radius=9)
            title_text = label.render(title, True, color)
            surface.blit(title_text, title_text.get_rect(midtop=(card.centerx, card.y + 10)))
            cluster = [(0, 0, 0, self.accent, False), (1, 0, 0, self.accent, False)]
            if index == 1:
                cluster.append((-1, 0, 0, self.GREEN, False))
            if index == 2:
                cluster = [(1, 0, 0, self.accent, False), (0, 0, 0, self.RED, True)]
            diagram = pygame.Rect(card.x + 13, card.y + 39, card.width - 26, card.height - 93)
            self._draw_cluster(surface, diagram, cluster)
            ray_y = diagram.centery
            pygame.draw.line(surface, self.CYAN, (diagram.x + 8, ray_y), (diagram.centerx - 12, ray_y), 4)
            pygame.draw.polygon(surface, self.CYAN, ((diagram.centerx - 4, ray_y), (diagram.centerx - 17, ray_y - 7), (diagram.centerx - 17, ray_y + 7)))
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 9)))
            if index < 2:
                self._draw_arrow(surface, card.right, card.right + gap, card.centery)

    def _draw_laboratory_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "A REPRODUCIBLE 3D EXPERIMENT NEEDS MORE THAN A SCREENSHOT")
        stages = (
            ("32³ / 48³ / 64³", "VOLUME", self.CYAN),
            ("fixed / wrap / reflect", "BOUNDARY", self.ORANGE),
            ("rule + seed + density", "INITIAL STATE", self.GREEN),
            ("timeline + clip + metrics", "OBSERVATION", self.PURPLE),
        )
        gap = 18
        width = (rect.width - 42 - gap * 3) // 4
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (detail, title, color) in enumerate(stages):
            card = pygame.Rect(rect.x + 14 + index * (width + gap), top + 12, width, rect.height - 90)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 3, border_radius=9)
            number = heading.render(str(index + 1), True, theme["background"])
            pygame.draw.circle(surface, color, (card.centerx, card.y + 52), 27)
            surface.blit(number, number.get_rect(center=(card.centerx, card.y + 52)))
            name = heading.render(title, True, theme["text"])
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(name, name.get_rect(midtop=(card.centerx, card.y + 96)))
            surface.blit(detail_text, detail_text.get_rect(midtop=(card.centerx, card.y + 136)))

    def _identity_voxels(self) -> list[tuple[int, int, int, tuple[int, int, int], bool]]:
        if self.mode_key == MODE_SPATIAL_LIFE:
            return [
                (x, y, z, self.SPATIAL_ACCENT, False)
                for z, y, x in BAYS_5766_GLIDER.offsets
            ]
        colors = (self.GENERATIONS_ACCENT, self.ORANGE, self.PURPLE, self.CYAN)
        return [
            (x, y, z, colors[(abs(x) + abs(y) + abs(z)) % len(colors)], False)
            for z in range(-2, 3)
            for y in range(-2, 3)
            for x in range(-2, 3)
            if x * x + y * y + z * z <= 6 and (x + y + z) % 2 == 0
        ]

    def _draw_mode_identity_page(self, canvas: pygame.Surface, y: int) -> int:
        width = canvas.get_width()
        gap = 18
        visual_width = round(width * 0.43)
        visual = pygame.Rect(0, y, visual_width, 520)
        sections = pygame.Rect(visual.right + gap, y, width - visual_width - gap, 1000)
        self._draw_cluster(canvas, visual, self._identity_voxels(), scale=1.0)
        bottom = self._draw_sections(canvas, self.page.sections, sections)
        return max(visual.bottom, bottom)

    def _draw_spatial_notation(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "CURRENT PRESET: " + self.services.current_rule_label())
        cards = (
            ("B6", "empty + 6", "BIRTH", self.GREEN),
            ("S567", "alive + 5, 6, or 7", "SURVIVAL", self.CYAN),
            ("26", "center excluded", "MOORE NEIGHBORS", self.PURPLE),
        )
        gap = 20
        width = (rect.width - 44 - gap * 2) // 3
        heading = self._font(self._font_sizes()[0], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (symbol, detail, name, color) in enumerate(cards):
            card = pygame.Rect(rect.x + 12 + index * (width + gap), top + 8, width, rect.height - 82)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 3, border_radius=9)
            name_text = label.render(name, True, color)
            symbol_text = heading.render(symbol, True, theme["text"])
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, card.y + 17)))
            surface.blit(symbol_text, symbol_text.get_rect(center=(card.centerx, card.centery - 3)))
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 18)))

    def _draw_spatial_birth(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "BAYS 5766: EMPTY FOCUS + EXACTLY 6 LIVE NEIGHBORS -> BIRTH")
        gap = 44
        width = (rect.width - 50 - gap * 2) // 3
        live = self._face_neighbors()
        steps = (
            ("OLD VOLUME", [(x, y, z, self.SPATIAL_ACCENT, False) for x, y, z in live] + [(0, 0, 0, self.GOLD, True)], "focus is empty", self.SPATIAL_ACCENT),
            ("COUNT", [], "6 of 26 are alive", self.GOLD),
            ("NEW VOLUME", [(x, y, z, self.SPATIAL_ACCENT, False) for x, y, z in live] + [(0, 0, 0, self.GREEN, False)], "B6 writes a live focus", self.GREEN),
        )
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (title, voxels, detail, color) in enumerate(steps):
            card = pygame.Rect(rect.x + 14 + index * (width + gap), top, width, rect.height - 68)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 2, border_radius=9)
            title_text = label.render(title, True, theme["text"])
            surface.blit(title_text, title_text.get_rect(midtop=(card.centerx, card.y + 10)))
            if voxels:
                self._draw_cluster(surface, pygame.Rect(card.x + 13, card.y + 39, card.width - 26, card.height - 91), voxels)
            else:
                count = heading.render("6 LIVE", True, self.GOLD)
                possible = label.render("out of 26 possible neighbors", True, theme["menu_text"])
                surface.blit(count, count.get_rect(center=(card.centerx, card.centery - 10)))
                surface.blit(possible, possible.get_rect(midtop=(card.centerx, card.centery + 24)))
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 10)))
            if index < 2:
                self._draw_arrow(surface, card.right, card.right + gap, card.centery)

    def _draw_spatial_survival(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "BAYS 5766: A LIVE FOCUS SURVIVES ONLY WITH 5, 6, OR 7")
        outcomes = (
            (4, "DIES", self.RED),
            (5, "SURVIVES", self.GREEN),
            (7, "SURVIVES", self.GREEN),
            (8, "DIES", self.RED),
        )
        gap = 16
        width = (rect.width - 40 - gap * 3) // 4
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        neighbors = self._moore_neighbors()
        for index, (count, result, color) in enumerate(outcomes):
            card = pygame.Rect(rect.x + 14 + index * (width + gap), top, width, rect.height - 69)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 2, border_radius=9)
            voxels = [(x, y, z, self.SPATIAL_ACCENT, False) for x, y, z in neighbors[:count]]
            voxels.append((0, 0, 0, self.GOLD, False))
            self._draw_cluster(surface, pygame.Rect(card.x + 11, card.y + 10, card.width - 22, card.height - 83), voxels, scale=0.74)
            count_text = label.render(f"{count} LIVE NEIGHBORS", True, theme["text"])
            result_text = heading.render(result, True, color)
            surface.blit(count_text, count_text.get_rect(midbottom=(card.centerx, card.bottom - 42)))
            surface.blit(result_text, result_text.get_rect(midbottom=(card.centerx, card.bottom - 11)))

    def _draw_spatial_glider(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "PERIOD 4: SAME TEN-VOXEL SHAPE, TRANSLATED ONE CELL")
        gap = 44
        width = (rect.width - 50 - gap * 2) // 3
        base = [(x, y, z) for z, y, x in BAYS_5766_GLIDER.offsets]
        frames = (
            ("GENERATION 0", base, "ten-voxel seed"),
            ("FOUR UPDATES", [], "N × 4; all voxels update together"),
            ("GENERATION 4", [(x + 1, y + 1, z + 1) for x, y, z in base], "same shape at shifted coordinates"),
        )
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (title, points, detail) in enumerate(frames):
            card = pygame.Rect(rect.x + 14 + index * (width + gap), top, width, rect.height - 68)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, self.accent if index != 1 else self.GOLD, card, 2, border_radius=9)
            title_text = label.render(title, True, theme["text"])
            surface.blit(title_text, title_text.get_rect(midtop=(card.centerx, card.y + 10)))
            if points:
                voxels = [(x, y, z, self.SPATIAL_ACCENT, False) for x, y, z in points]
                self._draw_cluster(surface, pygame.Rect(card.x + 12, card.y + 38, card.width - 24, card.height - 91), voxels)
            else:
                big = heading.render("t + 4", True, self.GOLD)
                surface.blit(big, big.get_rect(center=(card.centerx, card.centery - 5)))
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 10)))
            if index < 2:
                self._draw_arrow(surface, card.right, card.right + gap, card.centery)

    def _draw_spatial_catalog(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "A RULE IS COUNTS + NEIGHBORHOOD; NOTATION ALONE IS INCOMPLETE")
        presets = (
            ("BAYS 5766", "B6 / S567", "26 Moore", "documented glider", self.GREEN),
            ("BAYS 4555", "B5 / S45", "26 Moore", "alternate Bays rule", self.CYAN),
            ("FACE LIFE", "B3 / S23", "6 face", "exploratory comparison", self.ORANGE),
        )
        gap = 20
        width = (rect.width - 44 - gap * 2) // 3
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (name, notation, neighborhood, detail, color) in enumerate(presets):
            card = pygame.Rect(rect.x + 12 + index * (width + gap), top + 7, width, rect.height - 79)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 3, border_radius=9)
            name_text = heading.render(name, True, color)
            notation_text = self._font(self._font_sizes()[0], bold=True).render(notation, True, theme["text"])
            neighbor_text = heading.render(neighborhood, True, theme["menu_text"])
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, card.y + 17)))
            surface.blit(notation_text, notation_text.get_rect(center=(card.centerx, card.centery - 12)))
            surface.blit(neighbor_text, neighbor_text.get_rect(midtop=(card.centerx, card.centery + 32)))
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 18)))

    def _generation_colors(self, count: int) -> tuple[tuple[int, int, int], ...]:
        if count <= 2:
            return (self.services.theme()["background"], self.GENERATIONS_ACCENT)
        colors = [self.services.theme()["background"], self.GENERATIONS_ACCENT]
        for index in range(2, count):
            amount = (index - 1) / max(1, count - 2)
            colors.append(self._mix(self.ORANGE, self.PURPLE, amount))
        return tuple(colors)

    def _draw_generations_states(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "BIRTH ENTERS STATE 1; FAILED SURVIVAL STARTS A ONE-WAY COOLDOWN")
        states = (
            ("0", "EMPTY", theme["background"]),
            ("1", "ACTIVE", self.GENERATIONS_ACCENT),
            ("2", "REFRACTORY", self.ORANGE),
            ("…", "COOLING", self._mix(self.ORANGE, self.PURPLE, 0.55)),
            ("C−1", "LAST TRAIL", self.PURPLE),
            ("0", "EMPTY AGAIN", theme["background"]),
        )
        gap = 26
        width = (rect.width - 40 - gap * (len(states) - 1)) // len(states)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (symbol, name, color) in enumerate(states):
            card = pygame.Rect(rect.x + 12 + index * (width + gap), top + 20, width, rect.height - 104)
            pygame.draw.rect(surface, theme["button"], card, border_radius=8)
            pygame.draw.rect(surface, color if color != theme["background"] else theme["grid"], card, 2, border_radius=8)
            cube_center = (card.centerx, card.y + 74)
            self._draw_voxel(surface, cube_center, min(62, card.width * 0.55), color)
            symbol_text = heading.render(symbol, True, theme["text"])
            name_text = label.render(name, True, theme["menu_text"])
            surface.blit(symbol_text, symbol_text.get_rect(midtop=(card.centerx, card.y + 123)))
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, card.y + 153)))
            if index < len(states) - 1:
                self._draw_arrow(surface, card.right, card.right + gap, card.centery)
        birth_note = label.render("0 -> 1 is conditional on B; every refractory arrow is unconditional", True, self.GOLD)
        surface.blit(birth_note, birth_note.get_rect(midbottom=(rect.centerx, rect.bottom - 13)))

    def _draw_generations_notation(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "CURRENT PRESET: " + self.services.current_rule_label())
        fields = (
            ("4", "SURVIVAL", "state 1 + four", self.GREEN),
            ("4", "BIRTH", "state 0 + four", self.CYAN),
            ("5", "TOTAL STATES", "0, 1, 2, 3, 4", self.ORANGE),
            ("M", "NEIGHBORHOOD", "26-cell Moore", self.PURPLE),
        )
        gap = 16
        width = (rect.width - 40 - gap * 3) // 4
        title_font = self._font(self._font_sizes()[0], bold=True)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (symbol, name, detail, color) in enumerate(fields):
            card = pygame.Rect(rect.x + 14 + index * (width + gap), top + 10, width, rect.height - 86)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 3, border_radius=9)
            symbol_text = title_font.render(symbol, True, theme["text"])
            name_text = heading.render(name, True, color)
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(symbol_text, symbol_text.get_rect(center=(card.centerx, card.centery - 30)))
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, card.centery + 12)))
            surface.blit(detail_text, detail_text.get_rect(midtop=(card.centerx, card.centery + 53)))

    def _draw_generations_counting(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "VISIBLE DOES NOT MEAN ACTIVE: ONLY STATE 1 CONTRIBUTES TO THE COUNT")
        left = pygame.Rect(rect.x + 24, top, rect.width * 3 // 5, rect.height - 70)
        active_points = self._face_neighbors()[:4]
        refractory_points = ((1, 1, 0), (-1, -1, 0), (1, 0, 1), (0, -1, -1))
        voxels = [(x, y, z, self.GENERATIONS_ACCENT, False) for x, y, z in active_points]
        voxels += [(x, y, z, self.ORANGE, False) for x, y, z in refractory_points]
        voxels.append((0, 0, 0, self.GOLD, True))
        self._draw_cluster(surface, left, voxels)
        side = pygame.Rect(left.right + 25, top + 25, rect.right - left.right - 50, rect.height - 120)
        heading = self._font(self._font_sizes()[0], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        count = heading.render("COUNT = 4", True, self.GENERATIONS_ACCENT)
        active = label.render("4 ACTIVE STATE-1 VOXELS", True, self.GENERATIONS_ACCENT)
        ignored = label.render("4 REFRACTORY VOXELS IGNORED", True, self.ORANGE)
        surface.blit(count, count.get_rect(center=(side.centerx, side.y + 70)))
        surface.blit(active, active.get_rect(midtop=(side.centerx, side.y + 128)))
        surface.blit(ignored, ignored.get_rect(midtop=(side.centerx, side.y + 162)))

    def _draw_generations_445(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "4/4/5/M HAS TWO COUNT DECISIONS AND ONE FIXED COOLDOWN")
        branches = (
            ("EMPTY + 4", "BORN -> 1", self.CYAN),
            ("ACTIVE + 4", "SURVIVES -> 1", self.GREEN),
            ("ACTIVE + OTHER", "DIES -> 2", self.RED),
            ("2 -> 3 -> 4", "THEN -> 0", self.ORANGE),
        )
        gap = 16
        width = (rect.width - 40 - gap * 3) // 4
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        colors = self._generation_colors(5)
        for index, (condition, result, color) in enumerate(branches):
            card = pygame.Rect(rect.x + 14 + index * (width + gap), top, width, rect.height - 69)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 3, border_radius=9)
            condition_text = heading.render(condition, True, theme["text"])
            surface.blit(condition_text, condition_text.get_rect(midtop=(card.centerx, card.y + 16)))
            if index < 3:
                before_color = colors[0] if index == 0 else colors[1]
                after_color = colors[1] if index < 2 else colors[2]
                self._draw_voxel(surface, (card.centerx - 45, card.centery), 55, before_color)
                self._draw_arrow(surface, card.centerx - 18, card.centerx + 18, card.centery + 7)
                self._draw_voxel(surface, (card.centerx + 45, card.centery), 55, after_color)
            else:
                for state, state_color in enumerate(colors[2:], start=2):
                    x = card.x + 45 + (state - 2) * 63
                    self._draw_voxel(surface, (x, card.centery), 44, state_color)
                zero = label.render("0", True, theme["text"])
                surface.blit(zero, zero.get_rect(center=(card.right - 35, card.centery + 8)))
            result_text = label.render(result, True, color)
            surface.blit(result_text, result_text.get_rect(midbottom=(card.centerx, card.bottom - 14)))

    def _draw_generations_binary(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "C = 2 MEANS ACTIVE DEATH RETURNS DIRECTLY TO EMPTY")
        cards = (
            ("3D BRAIN", "/4/2/M", "birth-only; old active always dies", self.CYAN),
            ("CLOUDS 1", "13-26 / 13-14,17-19 / 2 / M", "dense survival and birth regime", self.PURPLE),
        )
        gap = 26
        width = (rect.width - 50 - gap) // 2
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, (name, notation, detail, color) in enumerate(cards):
            card = pygame.Rect(rect.x + 12 + index * (width + gap), top + 10, width, rect.height - 82)
            pygame.draw.rect(surface, theme["button"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 3, border_radius=9)
            name_text = heading.render(name, True, color)
            notation_text = self._font(self._font_sizes()[0], bold=True).render(notation, True, theme["text"])
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, card.y + 20)))
            surface.blit(notation_text, notation_text.get_rect(center=(card.centerx, card.centery - 8)))
            surface.blit(detail_text, detail_text.get_rect(midbottom=(card.centerx, card.bottom - 24)))

    def _draw_generations_pyroclastic(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        top = self._draw_title(surface, rect, "PYROCLASTIC: STATE 1 FRONT + EIGHT REFRACTORY AGES")
        colors = self._generation_colors(10)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        gap = 12
        width = (rect.width - 44 - gap * 9) // 10
        for state in range(10):
            card = pygame.Rect(rect.x + 12 + state * (width + gap), top + 25, width, rect.height - 110)
            pygame.draw.rect(surface, theme["button"], card, border_radius=7)
            pygame.draw.rect(surface, colors[state] if state else theme["grid"], card, 2, border_radius=7)
            self._draw_voxel(surface, (card.centerx, card.y + 72), min(52, card.width * 0.55), colors[state])
            number = heading.render(str(state), True, theme["text"])
            name = "EMPTY" if state == 0 else "ACTIVE" if state == 1 else "TRAIL"
            name_text = label.render(name, True, theme["menu_text"])
            surface.blit(number, number.get_rect(midtop=(card.centerx, card.y + 118)))
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, card.y + 149)))
            if 1 <= state < 9:
                self._draw_arrow(surface, card.right, card.right + gap, card.centery)
        note = label.render("Only state 1 counts; states 2-9 preserve age but cannot be reactivated", True, self.GOLD)
        surface.blit(note, note.get_rect(midbottom=(rect.centerx, rect.bottom - 13)))

    def _draw_mode_experiment_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        width = canvas.get_width()
        visual = pygame.Rect(0, y, width, 260)
        self._panel(canvas, visual, border=self.accent)
        top = self._draw_title(canvas, visual, "START FROM A DOCUMENTED, MODE-COMPATIBLE EXPERIMENT")
        if self.mode_key == MODE_SPATIAL_LIFE:
            voxels = self._identity_voxels()
            action = "LOAD BAYS 5766 GLIDER"
            note = "Installs the ten-voxel seed, B6/S567, and wrapped boundary"
        else:
            voxels = [
                (x, y, z, self.GENERATIONS_ACCENT, False)
                for z in (-1, 0, 1)
                for y in (-1, 0, 1)
                for x in (-1, 0, 1)
                if (x + y + z) % 2 == 0
            ]
            action = "CREATE RANDOM CENTRAL CORE"
            note = "Uses the selected Generations preset's documented seed density"
        self._draw_cluster(canvas, pygame.Rect(visual.x + 30, top, visual.width // 2 - 45, visual.height - 73), voxels, scale=0.85)
        label = self._font(self._font_sizes()[3], bold=True)
        note_text = label.render(note, True, theme["menu_text"])
        canvas.blit(note_text, note_text.get_rect(center=(visual.width * 3 // 4, visual.y + 103)))
        button = pygame.Rect(visual.width // 2 + 35, visual.y + 135, visual.width // 2 - 65, 62)
        pygame.draw.rect(canvas, theme["button_hover"], button, border_radius=9)
        pygame.draw.rect(canvas, self.accent, button, 3, border_radius=9)
        button_text = self._font(self._font_sizes()[1], bold=True).render(action, True, theme["button_text"])
        canvas.blit(button_text, button_text.get_rect(center=button.center))
        self._local_interactions.append(("experiment", self.mode_key, button.copy()))
        y = self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, visual.bottom + 16, width, 1100),
        )
        return y

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.active and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for action, payload, rect in self._interactions:
                if action == "experiment" and rect.collidepoint(event.pos):
                    self.close()
                    self.services.start_experiment(payload)
                    return True
        return super().handle_event(event)

    def _draw_page_canvas(self, width: int) -> tuple[pygame.Surface, int]:
        canvas = pygame.Surface((width, 3000), pygame.SRCALPHA)
        self._local_interactions = []
        y = self._draw_lead(canvas, width)
        kind = self.page.kind
        visual_methods: dict[str, tuple[int, Callable[[pygame.Surface, pygame.Rect], None]]] = {
            "volume": (430, self._draw_volume_visual),
            "neighborhoods": (430, self._draw_neighborhoods_visual),
            "synchronous_3d": (360, self._draw_synchronous_visual),
            "visibility": (370, self._draw_visibility_visual),
            "camera_3d": (390, self._draw_camera_visual),
            "editing_3d": (360, self._draw_editing_visual),
            "laboratory_3d": (340, self._draw_laboratory_visual),
            "spatial_notation": (340, self._draw_spatial_notation),
            "spatial_birth": (380, self._draw_spatial_birth),
            "spatial_survival": (370, self._draw_spatial_survival),
            "spatial_glider": (390, self._draw_spatial_glider),
            "spatial_catalog": (340, self._draw_spatial_catalog),
            "generations_states": (390, self._draw_generations_states),
            "generations_notation": (340, self._draw_generations_notation),
            "generations_counting": (390, self._draw_generations_counting),
            "generations_445": (360, self._draw_generations_445),
            "generations_binary": (330, self._draw_generations_binary),
            "generations_pyroclastic": (370, self._draw_generations_pyroclastic),
        }
        if kind in visual_methods:
            height, method = visual_methods[kind]
            y = self._draw_visual_with_sections(canvas, y, height, method)
        elif kind == "mode_identity_3d":
            y = self._draw_mode_identity_page(canvas, y)
        elif kind == "mode_experiment_3d":
            y = self._draw_mode_experiment_page(canvas, y)
        elif kind == "mode_sources":
            y = self._draw_mode_sources_page(canvas, y)
        return canvas, y + 8
