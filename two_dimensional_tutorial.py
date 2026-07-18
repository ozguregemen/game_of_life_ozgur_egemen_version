"""Full-screen, mode-aware tutorial for the two-dimensional workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import pygame

from mode_registry import MODE_BY_KEY
from two_dimensional_tutorial_content import (
    FOUNDATION_PAGES,
    MODE_GUIDES,
    ModeGuide,
    TutorialPage,
    TutorialSection,
)


@dataclass(frozen=True)
class TwoDimensionalTutorialServices:
    """Application resources and callbacks used by the contextual tutorial."""

    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    current_mode: Callable[[], str]
    current_rule_label: Callable[[], str]
    open_url: Callable[[str], bool]
    open_patterns: Callable[[], None]
    pause: Callable[[], None]
    set_status: Callable[[str, float], None]


class TwoDimensionalTutorial:
    """Optional 2D foundations plus a guide for only the active simulation mode."""

    FOUNDATIONS = "foundations"
    MODE = "mode"
    FOUNDATION_ACCENT = (72, 189, 246)
    GOLD = (245, 186, 72)
    GREEN = (91, 211, 148)
    MAGENTA = (229, 112, 171)
    BLUE = (67, 158, 245)
    ORANGE = (246, 139, 54)

    def __init__(self, services: TwoDimensionalTutorialServices) -> None:
        self.services = services
        self.active = False
        self.tab = self.FOUNDATIONS
        self.foundation_page = 0
        self.mode_page = 0
        self.scroll = 0
        self.content_height = 0
        self._last_mode = self.mode_key
        self._fonts: dict[tuple[int, bool], pygame.font.Font] = {}
        self._interactions: list[tuple[str, str, pygame.Rect]] = []
        self._local_interactions: list[tuple[str, str, pygame.Rect]] = []

    @property
    def mode_key(self) -> str:
        mode = self.services.current_mode()
        return mode if mode in MODE_GUIDES else "life"

    @property
    def guide(self) -> ModeGuide:
        return MODE_GUIDES[self.mode_key]

    @property
    def pages(self) -> tuple[TutorialPage, ...]:
        return FOUNDATION_PAGES if self.tab == self.FOUNDATIONS else self.guide.pages

    @property
    def page_index(self) -> int:
        return self.foundation_page if self.tab == self.FOUNDATIONS else self.mode_page

    @page_index.setter
    def page_index(self, value: int) -> None:
        bounded = max(0, min(len(self.pages) - 1, int(value)))
        if self.tab == self.FOUNDATIONS:
            self.foundation_page = bounded
        else:
            self.mode_page = bounded

    @property
    def page(self) -> TutorialPage:
        return self.pages[self.page_index]

    @property
    def mode_tab_label(self) -> str:
        return f"MODE: {self.guide.short_name.upper()}"

    @property
    def accent(self) -> tuple[int, int, int]:
        if self.tab == self.FOUNDATIONS:
            return self.FOUNDATION_ACCENT
        return MODE_BY_KEY[self.mode_key].accent

    def open(self) -> None:
        """Pause and show the tutorial only after an explicit user action."""
        current_mode = self.mode_key
        if current_mode != self._last_mode:
            self.mode_page = 0
            self._last_mode = current_mode
        self.services.pause()
        self.active = True
        self.scroll = 0

    def close(self) -> None:
        self.active = False
        self._interactions.clear()

    def select_tab(self, tab: str) -> None:
        if tab not in (self.FOUNDATIONS, self.MODE):
            raise ValueError(f"Unknown 2D tutorial tab: {tab}")
        if self.tab != tab:
            self.tab = tab
            self.scroll = 0
            self._interactions.clear()

    def _font(self, size: int, *, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont("Segoe UI", size, bold=bold)
        return self._fonts[key]

    def _font_sizes(self) -> tuple[int, int, int, int]:
        _, height = self.services.window_size()
        title = max(26, min(40, round(height * 0.037)))
        heading = max(19, min(27, round(height * 0.024)))
        body = max(16, min(21, round(height * 0.019)))
        label = max(13, min(17, round(height * 0.015)))
        return title, heading, body, label

    def geometry(
        self,
    ) -> tuple[
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
        tuple[pygame.Rect, pygame.Rect],
    ]:
        width, height = self.services.window_size()
        margin = 8 if min(width, height) < 700 else 14
        modal = pygame.Rect(margin, margin, width - margin * 2, height - margin * 2)
        header_height = max(132, min(158, round(height * 0.17)))
        footer_height = max(60, min(76, round(height * 0.075)))
        close = pygame.Rect(modal.right - 50, modal.y + 17, 32, 30)
        viewport = pygame.Rect(
            modal.x + 24,
            modal.y + header_height,
            modal.width - 48,
            modal.height - header_height - footer_height,
        )
        back = pygame.Rect(modal.x + 24, modal.bottom - footer_height + 13, 170, 40)
        next_button = pygame.Rect(
            modal.right - 244,
            modal.bottom - footer_height + 13,
            220,
            40,
        )
        tab_gap = 10
        tab_width = (modal.width - 52 - tab_gap) // 2
        tab_y = viewport.y - 48
        tabs = (
            pygame.Rect(modal.x + 26, tab_y, tab_width, 36),
            pygame.Rect(modal.x + 26 + tab_width + tab_gap, tab_y, tab_width, 36),
        )
        return modal, viewport, close, back, next_button, tabs

    def _maximum_scroll(self, viewport: pygame.Rect) -> int:
        return max(0, self.content_height - viewport.height)

    def _move(self, delta: int) -> None:
        target = self.page_index + delta
        if target >= len(self.pages):
            if self.tab == self.FOUNDATIONS:
                self.select_tab(self.MODE)
                self.mode_page = 0
                return
            self.close()
            self.services.set_status(
                f"{self.guide.name} tutorial complete. Try a verified pattern next.",
                5.0,
            )
            return
        if target < 0:
            if self.tab == self.MODE:
                self.select_tab(self.FOUNDATIONS)
                self.foundation_page = len(FOUNDATION_PAGES) - 1
            else:
                self.foundation_page = 0
            return
        self.page_index = target
        self.scroll = 0
        self._interactions.clear()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_F2):
                self.close()
            elif event.key == pygame.K_TAB:
                self.select_tab(
                    self.MODE if self.tab == self.FOUNDATIONS else self.FOUNDATIONS
                )
            elif event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN, pygame.K_RETURN):
                self._move(1)
            elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP, pygame.K_BACKSPACE):
                self._move(-1)
            elif event.key == pygame.K_HOME:
                self.page_index = 0
                self.scroll = 0
            elif event.key == pygame.K_END:
                self.page_index = len(self.pages) - 1
                self.scroll = 0
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 56)
            elif event.key == pygame.K_DOWN:
                _, viewport, _, _, _, _ = self.geometry()
                self.scroll = min(self._maximum_scroll(viewport), self.scroll + 56)
            return True
        if event.type == pygame.MOUSEWHEEL:
            _, viewport, _, _, _, _ = self.geometry()
            self.scroll = max(
                0,
                min(self._maximum_scroll(viewport), self.scroll - event.y * 58),
            )
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            modal, _, close, back, next_button, tabs = self.geometry()
            if close.collidepoint(event.pos) or not modal.collidepoint(event.pos):
                self.close()
                return True
            if tabs[0].collidepoint(event.pos):
                self.select_tab(self.FOUNDATIONS)
                return True
            if tabs[1].collidepoint(event.pos):
                self.select_tab(self.MODE)
                return True
            if back.collidepoint(event.pos):
                self._move(-1)
                return True
            if next_button.collidepoint(event.pos):
                self._move(1)
                return True
            for action, payload, rect in self._interactions:
                if not rect.collidepoint(event.pos):
                    continue
                if action == "url":
                    opened = self.services.open_url(payload)
                    self.services.set_status(
                        "Source opened in the default browser."
                        if opened
                        else "The source could not be opened; its URL is in README.",
                        4.0,
                    )
                elif action == "patterns":
                    self.close()
                    self.services.open_patterns()
                return True
            return True
        return True

    @staticmethod
    def _mix(
        first: tuple[int, int, int],
        second: tuple[int, int, int],
        amount: float,
    ) -> tuple[int, int, int]:
        return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))

    @staticmethod
    def _wrap(text: str, font: pygame.font.Font, width: int) -> list[str]:
        lines: list[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if current and font.size(candidate)[0] > width:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
        return lines or [""]

    def _draw_wrapped(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        *,
        line_height: int,
    ) -> int:
        y = rect.y
        for line in self._wrap(text, font, rect.width):
            surface.blit(font.render(line, True, color), (rect.x, y))
            y += line_height
        return y

    def _panel(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        border: tuple[int, int, int] | None = None,
    ) -> None:
        theme = self.services.theme()
        pygame.draw.rect(surface, theme["button"], rect, border_radius=10)
        pygame.draw.rect(
            surface,
            border or theme["grid"],
            rect,
            2 if border else 1,
            border_radius=10,
        )

    def _draw_lead(self, canvas: pygame.Surface, width: int) -> int:
        theme = self.services.theme()
        _, _, body_size, _ = self._font_sizes()
        lead_font = self._font(body_size + 1)
        lines = self._wrap(self.page.lead, lead_font, width - 36)
        height = max(72, 30 + len(lines) * (body_size + 8))
        rect = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(canvas, theme["stats_bar"], rect, border_radius=10)
        pygame.draw.rect(
            canvas,
            self._mix(self.accent, theme["grid"], 0.5),
            rect,
            1,
            border_radius=10,
        )
        self._draw_wrapped(
            canvas,
            self.page.lead,
            lead_font,
            theme["text"],
            rect.inflate(-18, -15),
            line_height=body_size + 8,
        )
        return rect.bottom + 16

    def _section_height(self, section: TutorialSection, text_width: int) -> int:
        _, _, body_size, _ = self._font_sizes()
        lines = self._wrap(section.body, self._font(body_size), max(80, text_width))
        return max(94, 48 + len(lines) * (body_size + 6) + 16)

    def _draw_sections(
        self,
        canvas: pygame.Surface,
        sections: Sequence[TutorialSection],
        rect: pygame.Rect,
        *,
        visual: Callable[[pygame.Surface, pygame.Rect, int], None] | None = None,
    ) -> int:
        theme = self.services.theme()
        _, heading_size, body_size, _ = self._font_sizes()
        heading_font = self._font(heading_size, bold=True)
        body_font = self._font(body_size)
        y = rect.y
        for index, section in enumerate(sections):
            visual_width = min(245, round(rect.width * 0.23)) if visual else 0
            text_width = rect.width - 92 - visual_width
            height = self._section_height(section, text_width)
            card = pygame.Rect(rect.x, y, rect.width, height)
            self._panel(canvas, card, border=self._mix(self.accent, theme["grid"], 0.38))
            badge = pygame.Rect(card.x + 17, card.centery - 24, 48, 48)
            pygame.draw.rect(canvas, self.accent, badge, border_radius=9)
            number = heading_font.render(str(index + 1), True, (7, 18, 27))
            canvas.blit(number, number.get_rect(center=badge.center))
            text_x = badge.right + 18
            heading = heading_font.render(section.title, True, theme["text"])
            canvas.blit(heading, (text_x, card.y + 15))
            self._draw_wrapped(
                canvas,
                section.body,
                body_font,
                theme["menu_text"],
                pygame.Rect(text_x, card.y + 49, text_width - 14, card.height - 57),
                line_height=body_size + 6,
            )
            if visual is not None:
                visual_rect = pygame.Rect(
                    card.right - visual_width + 6,
                    card.y + 10,
                    visual_width - 18,
                    card.height - 20,
                )
                visual(canvas, visual_rect, index)
            y = card.bottom + 11
        return y

    def _draw_matrix(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        matrix: Sequence[Sequence[int]],
        palette: Sequence[tuple[int, int, int]],
        *,
        border: tuple[int, int, int] | None = None,
    ) -> None:
        theme = self.services.theme()
        pygame.draw.rect(surface, theme["stats_bar"], rect, border_radius=8)
        pygame.draw.rect(surface, border or theme["grid"], rect, 2, border_radius=8)
        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0
        if not rows or not cols:
            return
        cell = max(3, min((rect.width - 20) // cols, (rect.height - 20) // rows))
        origin_x = rect.centerx - cols * cell // 2
        origin_y = rect.centery - rows * cell // 2
        for row, values in enumerate(matrix):
            for col, state in enumerate(values):
                box = pygame.Rect(
                    origin_x + col * cell,
                    origin_y + row * cell,
                    max(1, cell - 2),
                    max(1, cell - 2),
                )
                color = palette[state] if 0 <= state < len(palette) else palette[0]
                pygame.draw.rect(surface, color, box, border_radius=2)
                pygame.draw.rect(surface, theme["grid"], box, 1, border_radius=2)

    def _draw_lattice_page(self, canvas: pygame.Surface, y: int) -> int:
        width = canvas.get_width()
        gap = 18
        if width < 980:
            visual = pygame.Rect(0, y, width, 330)
            sections = pygame.Rect(0, visual.bottom + gap, width, 850)
        else:
            visual_width = round(width * 0.44)
            visual = pygame.Rect(0, y, visual_width, 530)
            sections = pygame.Rect(visual.right + gap, y, width - visual_width - gap, 850)
        self._draw_neighborhood_map(canvas, visual)
        bottom = self._draw_sections(canvas, self.page.sections, sections)
        return max(visual.bottom, bottom)

    def _draw_neighborhood_map(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        cell = max(18, min(42, (min(rect.width, rect.height) - 92) // 9))
        origin_x = rect.centerx - cell * 9 // 2
        origin_y = rect.centery - cell * 9 // 2 + 12
        center = (4, 4)
        for row in range(9):
            for col in range(9):
                box = pygame.Rect(
                    origin_x + col * cell,
                    origin_y + row * cell,
                    cell - 2,
                    cell - 2,
                )
                near = abs(row - center[0]) <= 1 and abs(col - center[1]) <= 1
                color = self._mix(theme["background"], theme["button"], 0.48)
                if near:
                    color = self._mix(self.accent, theme["background"], 0.45)
                if (row, col) == center:
                    color = self.GOLD
                pygame.draw.rect(surface, color, box, border_radius=3)
                pygame.draw.rect(surface, theme["grid"], box, 1, border_radius=3)
        _, heading_size, _, label_size = self._font_sizes()
        title = self._font(heading_size, bold=True).render(
            "ONE CELL + EIGHT LOCAL NEIGHBORS", True, theme["text"]
        )
        surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 18)))
        label = self._font(label_size, bold=True).render(
            "The rest of the board is not consulted directly", True, theme["menu_text"]
        )
        surface.blit(label, label.get_rect(midbottom=(rect.centerx, rect.bottom - 16)))

    def _draw_synchronous_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        width = canvas.get_width()
        frames = (
            ((0, 0, 0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 1, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 0, 0)),
            ((0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 1, 1, 1, 0), (0, 0, 0, 0, 0), (0, 0, 0, 0, 0)),
            ((0, 0, 0, 0, 0), (0, 0, 1, 0, 0), (0, 0, 1, 0, 0), (0, 0, 1, 0, 0), (0, 0, 0, 0, 0)),
        )
        gap = 42
        frame_width = (width - gap * 2) // 3
        visual_height = min(270, max(190, frame_width // 2))
        label_font = self._font(self._font_sizes()[3], bold=True)
        for index, matrix in enumerate(frames):
            frame = pygame.Rect(index * (frame_width + gap), y, frame_width, visual_height)
            self._draw_matrix(
                canvas,
                frame,
                matrix,
                (theme["background"], self.accent),
                border=self.accent,
            )
            label = label_font.render(f"GENERATION {index}", True, theme["text"])
            canvas.blit(label, label.get_rect(midbottom=(frame.centerx, frame.bottom - 8)))
            if index < 2:
                arrow_x = frame.right + gap // 2
                pygame.draw.line(canvas, self.GOLD, (arrow_x - 12, frame.centery), (arrow_x + 10, frame.centery), 4)
                pygame.draw.polygon(canvas, self.GOLD, ((arrow_x + 17, frame.centery), (arrow_x + 5, frame.centery - 7), (arrow_x + 5, frame.centery + 7)))
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, y + visual_height + 18, width, 850),
        )

    def _draw_model_visual(self, surface: pygame.Surface, rect: pygame.Rect, index: int) -> None:
        theme = self.services.theme()
        pygame.draw.rect(surface, theme["stats_bar"], rect, border_radius=7)
        pygame.draw.rect(surface, theme["grid"], rect, 1, border_radius=7)
        label_font = self._font(max(12, self._font_sizes()[3] - 1), bold=True)
        if index == 0:
            colors = (theme["background"], self.BLUE, self.ORANGE, self.MAGENTA)
            size = min(30, (rect.width - 28) // 4)
            start = rect.centerx - (size * 4 + 18) // 2
            for state, color in enumerate(colors):
                box = pygame.Rect(start + state * (size + 6), rect.centery - size // 2, size, size)
                pygame.draw.rect(surface, color, box, border_radius=4)
                pygame.draw.rect(surface, theme["text"], box, 1, border_radius=4)
        elif index == 1:
            cell = min(22, (rect.height - 16) // 3)
            start_x = rect.centerx - cell * 3 // 2
            start_y = rect.centery - cell * 3 // 2
            for row in range(3):
                for col in range(3):
                    box = pygame.Rect(start_x + col * cell, start_y + row * cell, cell - 2, cell - 2)
                    pygame.draw.rect(surface, self.GOLD if (row, col) == (1, 1) else self.accent, box)
        elif index == 2:
            parts = ("LOCAL", "RULE", "NEXT")
            step = rect.width // len(parts)
            for position, label in enumerate(parts):
                x = rect.x + step * position + step // 2
                pygame.draw.circle(surface, self.accent, (x, rect.centery - 5), 12, 3)
                text = label_font.render(label, True, theme["menu_text"])
                surface.blit(text, text.get_rect(midtop=(x, rect.centery + 13)))
                if position < 2:
                    pygame.draw.line(surface, theme["grid"], (x + 15, rect.centery - 5), (x + step - 15, rect.centery - 5), 2)
        else:
            inner = rect.inflate(-24, -26)
            pygame.draw.line(surface, self.MAGENTA, (inner.x, inner.y), (inner.x, inner.bottom), 5)
            pygame.draw.line(surface, self.MAGENTA, (inner.right, inner.y), (inner.right, inner.bottom), 5)
            for col in range(7):
                box = pygame.Rect(inner.x + 12 + col * max(10, inner.width // 8), rect.centery - 8, 16, 16)
                pygame.draw.rect(surface, self.accent if col == 3 else theme["background"], box)
                pygame.draw.rect(surface, theme["grid"], box, 1)

    def _draw_model_page(self, canvas: pygame.Surface, y: int) -> int:
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, y, canvas.get_width(), 1000),
            visual=self._draw_model_visual,
        )

    def _draw_laboratory_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        width = canvas.get_width()
        flow = pygame.Rect(0, y, width, 150)
        self._panel(canvas, flow, border=self.accent)
        labels = (("SEED", "Draw / Pattern"), ("RUN", "Space / N"), ("MEASURE", "Timeline / Analysis"), ("SAVE", "Session / Export"))
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3])
        step = (flow.width - 50) // 4
        for index, (title, detail) in enumerate(labels):
            center_x = flow.x + 25 + index * step + step // 2
            pygame.draw.circle(canvas, self.accent, (center_x, flow.y + 57), 27, 4)
            text = heading.render(str(index + 1), True, theme["text"])
            canvas.blit(text, text.get_rect(center=(center_x, flow.y + 57)))
            title_text = heading.render(title, True, theme["text"])
            canvas.blit(title_text, title_text.get_rect(midtop=(center_x, flow.y + 91)))
            detail_text = label.render(detail, True, theme["menu_text"])
            canvas.blit(detail_text, detail_text.get_rect(midtop=(center_x, flow.y + 121)))
            if index < 3:
                pygame.draw.line(canvas, self.GOLD, (center_x + 31, flow.y + 57), (center_x + step - 31, flow.y + 57), 3)
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, flow.bottom + 16, width, 900),
        )

    def _mode_palette(self) -> tuple[tuple[int, int, int], ...]:
        theme = self.services.theme()
        if self.mode_key == "immigration":
            return (theme["background"], self.BLUE, self.ORANGE)
        if self.mode_key == "brians_brain":
            return (theme["background"], (90, 235, 255), (128, 82, 190))
        if self.mode_key == "wireworld":
            return (theme["background"], (80, 190, 255), self.MAGENTA, self.GOLD)
        if self.mode_key == "cyclic_automaton":
            return (
                (40, 80, 190), (35, 170, 230), (55, 205, 140), (200, 220, 70),
                (250, 160, 45), (235, 85, 70), (195, 70, 210), (105, 70, 200),
            )
        return (theme["background"], self.accent)

    def _mode_matrix(self) -> tuple[tuple[int, ...], ...]:
        key = self.mode_key
        if key == "life":
            return (
                (0, 0, 0, 0, 0, 0, 0, 0, 0),
                (0, 0, 0, 1, 0, 0, 0, 0, 0),
                (0, 0, 0, 0, 1, 0, 0, 0, 0),
                (0, 0, 1, 1, 1, 0, 0, 0, 0),
                (0, 0, 0, 0, 0, 0, 1, 1, 0),
                (0, 0, 0, 0, 0, 1, 0, 1, 0),
                (0, 0, 0, 0, 0, 0, 1, 0, 0),
                (0, 0, 0, 0, 0, 0, 0, 0, 0),
            )
        if key == "immigration":
            return (
                (0, 0, 1, 0, 0, 0, 2, 0, 0),
                (0, 1, 1, 0, 0, 2, 2, 0, 0),
                (0, 0, 1, 2, 2, 2, 0, 0, 0),
                (0, 0, 0, 1, 2, 0, 0, 0, 0),
                (0, 0, 1, 1, 2, 2, 0, 0, 0),
                (0, 0, 0, 1, 2, 0, 0, 0, 0),
            )
        if key == "brians_brain":
            return (
                (0, 0, 0, 1, 0, 0, 0, 0, 0),
                (0, 0, 1, 2, 1, 0, 0, 0, 0),
                (0, 1, 2, 0, 2, 1, 0, 0, 0),
                (1, 2, 0, 0, 0, 2, 1, 0, 0),
                (0, 1, 2, 0, 2, 1, 0, 0, 0),
                (0, 0, 1, 2, 1, 0, 0, 0, 0),
                (0, 0, 0, 1, 0, 0, 0, 0, 0),
            )
        if key == "wireworld":
            return (
                (0, 0, 0, 3, 0, 0, 0, 0, 0),
                (3, 3, 3, 1, 2, 3, 3, 3, 3),
                (0, 0, 0, 3, 0, 0, 3, 0, 0),
                (0, 0, 0, 3, 3, 3, 3, 0, 0),
                (0, 0, 0, 0, 0, 0, 3, 0, 0),
            )
        if key == "cyclic_automaton":
            return tuple(
                tuple((row + col) % 8 for col in range(12)) for row in range(8)
            )
        return tuple(tuple((row + col) % 2 for col in range(9)) for row in range(7))

    def _draw_mode_emblem(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if self.mode_key != "langtons_ant":
            self._draw_matrix(
                surface,
                rect,
                self._mode_matrix(),
                self._mode_palette(),
                border=self.accent,
            )
            return
        theme = self.services.theme()
        matrix = tuple(tuple(1 if (row + col) % 5 == 0 else 0 for col in range(11)) for row in range(8))
        self._draw_matrix(surface, rect, matrix, (theme["background"], self.accent), border=self.accent)
        triangle = (
            (rect.centerx, rect.centery - 27),
            (rect.centerx - 24, rect.centery + 22),
            (rect.centerx + 24, rect.centery + 22),
        )
        pygame.draw.polygon(surface, self.GOLD, triangle)
        pygame.draw.polygon(surface, theme["text"], triangle, 3)

    def _draw_mode_identity_page(self, canvas: pygame.Surface, y: int) -> int:
        width = canvas.get_width()
        gap = 18
        if width < 980:
            visual = pygame.Rect(0, y, width, 310)
            sections = pygame.Rect(0, visual.bottom + gap, width, 900)
        else:
            visual_width = round(width * 0.42)
            visual = pygame.Rect(0, y, visual_width, 520)
            sections = pygame.Rect(visual.right + gap, y, width - visual_width - gap, 900)
        self._draw_mode_emblem(canvas, visual)
        bottom = self._draw_sections(canvas, self.page.sections, sections)
        return max(visual.bottom, bottom)

    def _draw_rule_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        heading_size = self._font_sizes()[1]
        label_size = self._font_sizes()[3]
        heading = self._font(heading_size, bold=True)
        label = self._font(label_size, bold=True)
        key = self.mode_key
        if key == "life":
            rule = self.services.current_rule_label()
            title = heading.render(f"CURRENT RULE: {rule}", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 16)))
            badges = (("BIRTH", "3", self.GREEN), ("SURVIVE", "2 or 3", self.accent), ("OTHER", "dead / stays dead", self.MAGENTA))
        elif key == "immigration":
            title = heading.render("B3/S23 FIRST - THEN INHERIT COLOR", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 16)))
            badges = (("A + A + B", "new A", self.BLUE), ("A + B + B", "new B", self.ORANGE), ("SURVIVOR", "keeps species", self.GREEN))
        elif key == "brians_brain":
            title = heading.render("EXCITATION AND ONE REFRACTORY STEP", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 16)))
            badges = (("OFF + 2 firing", "FIRING", (90, 235, 255)), ("FIRING", "DYING", self.MAGENTA), ("DYING", "OFF", theme["grid"]))
        elif key == "langtons_ant":
            title = heading.render("READ -> TURN -> FLIP -> MOVE", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 16)))
            badges = (("WHITE", "turn RIGHT", self.GOLD), ("BLACK", "turn LEFT", self.accent), ("THEN", "move forward", self.GREEN))
        elif key == "wireworld":
            title = heading.render("SIGNAL PHASE + LOCAL RECEPTION", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 16)))
            badges = (("HEAD", "TAIL", (80, 190, 255)), ("TAIL", "CONDUCTOR", self.MAGENTA), ("WIRE + 1/2 heads", "HEAD", self.GOLD))
        else:
            title = heading.render("SUCCESSOR PRESSURE AROUND THE COLOR CYCLE", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 16)))
            badges = (("state s", "seek s + 1", self.BLUE), ("count", "successor neighbors", self.GOLD), ("threshold met", "advance", self.GREEN))
        gap = 16
        badge_width = (rect.width - 44 - gap * 2) // 3
        top = rect.y + 65
        for index, (source, result, color) in enumerate(badges):
            card = pygame.Rect(rect.x + 22 + index * (badge_width + gap), top, badge_width, rect.height - 86)
            pygame.draw.rect(surface, theme["stats_bar"], card, border_radius=8)
            pygame.draw.rect(surface, color, card, 3, border_radius=8)
            source_text = label.render(source, True, theme["menu_text"])
            result_text = heading.render(result, True, theme["text"])
            surface.blit(source_text, source_text.get_rect(midtop=(card.centerx, card.y + 18)))
            pygame.draw.line(surface, color, (card.centerx, card.y + 53), (card.centerx, card.y + 82), 4)
            pygame.draw.polygon(surface, color, ((card.centerx, card.y + 91), (card.centerx - 7, card.y + 79), (card.centerx + 7, card.y + 79)))
            surface.blit(result_text, result_text.get_rect(midbottom=(card.centerx, card.bottom - 20)))

    def _draw_mode_rule_page(self, canvas: pygame.Surface, y: int) -> int:
        visual = pygame.Rect(0, y, canvas.get_width(), 250)
        self._draw_rule_visual(canvas, visual)
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, visual.bottom + 16, canvas.get_width(), 950),
        )

    def _draw_mode_experiment_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        width = canvas.get_width()
        visual = pygame.Rect(0, y, width, 235)
        self._draw_mode_emblem(canvas, visual)
        y = self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, visual.bottom + 16, width, 950),
        )
        button = pygame.Rect(0, y + 2, width, 54)
        pygame.draw.rect(canvas, theme["button_hover"], button, border_radius=9)
        pygame.draw.rect(canvas, self.accent, button, 3, border_radius=9)
        text = self._font(self._font_sizes()[1], bold=True).render(
            f"OPEN {self.guide.short_name.upper()} PATTERNS",
            True,
            theme["button_text"],
        )
        canvas.blit(text, text.get_rect(center=button.center))
        self._local_interactions.append(("patterns", self.mode_key, button.copy()))
        return button.bottom + 8

    def _draw_mode_sources_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        _, heading_size, body_size, label_size = self._font_sizes()
        heading = self._font(heading_size, bold=True)
        body = self._font(body_size)
        label = self._font(label_size, bold=True)
        line_x = 39
        card_x = 86
        cards: list[pygame.Rect] = []
        for source in self.guide.sources:
            lines = self._wrap(source.detail, body, canvas.get_width() - card_x - 230)
            height = max(112, 65 + len(lines) * (body_size + 5))
            card = pygame.Rect(card_x, y, canvas.get_width() - card_x, height)
            cards.append(card)
            y = card.bottom + 14
        if cards:
            pygame.draw.line(canvas, theme["grid"], (line_x, cards[0].centery), (line_x, cards[-1].centery), 4)
        for index, (source, card) in enumerate(zip(self.guide.sources, cards), start=1):
            self._panel(canvas, card, border=self.accent)
            pygame.draw.circle(canvas, theme["info_bar"], (line_x, card.centery), 25)
            pygame.draw.circle(canvas, self.accent, (line_x, card.centery), 25, 3)
            number = heading.render(str(index), True, self.accent)
            canvas.blit(number, number.get_rect(center=(line_x, card.centery)))
            category = label.render(source.category, True, self.GOLD)
            canvas.blit(category, (card.x + 18, card.y + 12))
            title = heading.render(source.title, True, theme["text"])
            canvas.blit(title, (card.x + 18, card.y + 39))
            self._draw_wrapped(
                canvas,
                source.detail,
                body,
                theme["menu_text"],
                pygame.Rect(card.x + 18, card.y + 72, card.width - 210, card.height - 78),
                line_height=body_size + 5,
            )
            button = pygame.Rect(card.right - 164, card.centery - 22, 146, 44)
            pygame.draw.rect(canvas, theme["button_hover"], button, border_radius=7)
            pygame.draw.rect(canvas, self.accent, button, 2, border_radius=7)
            open_text = label.render("OPEN SOURCE", True, theme["button_text"])
            canvas.blit(open_text, open_text.get_rect(center=button.center))
            self._local_interactions.append(("url", source.url, button.copy()))
        return y

    def _draw_page_canvas(self, width: int) -> tuple[pygame.Surface, int]:
        canvas = pygame.Surface((width, 2600), pygame.SRCALPHA)
        self._local_interactions = []
        y = self._draw_lead(canvas, width)
        if self.page.kind == "lattice":
            y = self._draw_lattice_page(canvas, y)
        elif self.page.kind == "synchronous":
            y = self._draw_synchronous_page(canvas, y)
        elif self.page.kind == "model":
            y = self._draw_model_page(canvas, y)
        elif self.page.kind == "laboratory":
            y = self._draw_laboratory_page(canvas, y)
        elif self.page.kind == "mode_identity":
            y = self._draw_mode_identity_page(canvas, y)
        elif self.page.kind == "mode_rule":
            y = self._draw_mode_rule_page(canvas, y)
        elif self.page.kind == "mode_experiment":
            y = self._draw_mode_experiment_page(canvas, y)
        elif self.page.kind == "mode_sources":
            y = self._draw_mode_sources_page(canvas, y)
        return canvas, y + 8

    def _draw_navigation_button(
        self,
        rect: pygame.Rect,
        label: str,
        *,
        enabled: bool,
        primary: bool = False,
    ) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        label_size = self._font_sizes()[3]
        pygame.draw.rect(
            screen,
            theme["button_hover"] if enabled else theme["button"],
            rect,
            border_radius=7,
        )
        border = self.accent if primary and enabled else theme["grid"]
        pygame.draw.rect(screen, border, rect, 2 if primary else 1, border_radius=7)
        text = self._font(label_size, bold=True).render(
            label,
            True,
            theme["button_text"] if enabled else theme["menu_text"],
        )
        screen.blit(text, text.get_rect(center=rect.center))

    def draw(self) -> None:
        if not self.active:
            return
        if self.mode_key != self._last_mode:
            self.mode_page = 0
            self._last_mode = self.mode_key
        screen = self.services.screen()
        width, height = self.services.window_size()
        theme = self.services.theme()
        title_size, _, _, label_size = self._font_sizes()
        dimmer = pygame.Surface((width, height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 232))
        screen.blit(dimmer, (0, 0))

        modal, viewport, close, back, next_button, tabs = self.geometry()
        pygame.draw.rect(screen, theme["info_bar"], modal, border_radius=12)
        pygame.draw.rect(screen, theme["text"], modal, 2, border_radius=12)
        kicker_font = self._font(label_size, bold=True)
        title_font = self._font(title_size, bold=True)
        kicker = kicker_font.render(self.page.kicker, True, self.accent)
        screen.blit(kicker, (modal.x + 26, modal.y + 17))
        title = title_font.render(self.page.title, True, theme["text"])
        screen.blit(title, (modal.x + 25, modal.y + 44))
        progress = kicker_font.render(
            f"PAGE {self.page_index + 1} OF {len(self.pages)}",
            True,
            theme["menu_text"],
        )
        screen.blit(progress, progress.get_rect(topright=(modal.right - 72, modal.y + 21)))
        pygame.draw.rect(screen, theme["button"], close, border_radius=6)
        pygame.draw.rect(screen, theme["grid"], close, 1, border_radius=6)
        close_text = kicker_font.render("X", True, theme["button_text"])
        screen.blit(close_text, close_text.get_rect(center=close.center))

        tab_labels = ("2D FOUNDATIONS", self.mode_tab_label)
        for index, (tab_rect, tab_label) in enumerate(zip(tabs, tab_labels)):
            selected = (index == 0 and self.tab == self.FOUNDATIONS) or (
                index == 1 and self.tab == self.MODE
            )
            pygame.draw.rect(
                screen,
                theme["button_hover"] if selected else theme["button"],
                tab_rect,
                border_radius=7,
            )
            pygame.draw.rect(
                screen,
                self.FOUNDATION_ACCENT if index == 0 else MODE_BY_KEY[self.mode_key].accent,
                tab_rect,
                3 if selected else 1,
                border_radius=7,
            )
            tab_text = kicker_font.render(tab_label, True, theme["button_text"])
            screen.blit(tab_text, tab_text.get_rect(center=tab_rect.center))

        pygame.draw.rect(screen, theme["background"], viewport, border_radius=9)
        canvas, content_height = self._draw_page_canvas(viewport.width - 28)
        self.content_height = max(content_height + 20, viewport.height)
        self.scroll = min(self.scroll, self._maximum_scroll(viewport))
        source_rect = pygame.Rect(
            0,
            self.scroll,
            canvas.get_width(),
            min(viewport.height - 18, canvas.height - self.scroll),
        )
        target = (viewport.x + 14, viewport.y + 9)
        old_clip = screen.get_clip()
        screen.set_clip(viewport.inflate(-2, -2))
        screen.blit(canvas, target, source_rect)
        screen.set_clip(old_clip)

        self._interactions = []
        for action, payload, local in self._local_interactions:
            translated = local.move(target[0], target[1] - self.scroll)
            if viewport.colliderect(translated):
                self._interactions.append((action, payload, translated))

        maximum_scroll = self._maximum_scroll(viewport)
        if maximum_scroll:
            track = pygame.Rect(viewport.right - 7, viewport.y + 10, 4, viewport.height - 20)
            pygame.draw.rect(screen, theme["grid"], track, border_radius=2)
            ratio = viewport.height / self.content_height
            thumb_height = max(34, int(track.height * ratio))
            thumb_y = track.y + int((track.height - thumb_height) * self.scroll / maximum_scroll)
            pygame.draw.rect(
                screen,
                self.accent,
                pygame.Rect(track.x, thumb_y, track.width, thumb_height),
                border_radius=2,
            )

        can_go_back = self.page_index > 0 or self.tab == self.MODE
        self._draw_navigation_button(back, "<  PREVIOUS", enabled=can_go_back)
        foundation_end = self.tab == self.FOUNDATIONS and self.page_index == len(self.pages) - 1
        mode_end = self.tab == self.MODE and self.page_index == len(self.pages) - 1
        next_label = "FINISH" if mode_end else (
            "CONTINUE TO MODE" if foundation_end else "NEXT  >"
        )
        self._draw_navigation_button(next_button, next_label, enabled=True, primary=True)
        footer = self._font(label_size).render(
            "F2 or Esc closes   |   Tab switches guide   |   Left / Right changes page   |   Wheel scrolls",
            True,
            theme["menu_text"],
        )
        screen.blit(footer, footer.get_rect(center=(modal.centerx, back.centery)))
