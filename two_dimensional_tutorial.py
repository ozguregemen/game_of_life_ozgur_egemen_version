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
    def foundation_pages(self) -> tuple[TutorialPage, ...]:
        return FOUNDATION_PAGES

    @property
    def pages(self) -> tuple[TutorialPage, ...]:
        return self.foundation_pages if self.tab == self.FOUNDATIONS else self.guide.pages

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
    def foundation_tab_label(self) -> str:
        return "2D FOUNDATIONS"

    @property
    def mode_accent(self) -> tuple[int, int, int]:
        return MODE_BY_KEY[self.mode_key].accent

    @property
    def accent(self) -> tuple[int, int, int]:
        if self.tab == self.FOUNDATIONS:
            return self.FOUNDATION_ACCENT
        return self.mode_accent

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
                self.foundation_page = len(self.foundation_pages) - 1
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
        cell = max(18, min(36, (min(rect.width, rect.height) - 112) // 9))
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
            "ONE FOCUS CELL READS EIGHT NEIGHBORS", True, theme["text"]
        )
        surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 18)))
        focus_label = self._font(label_size, bold=True).render(
            "GOLD = focus cell whose next state is being decided", True, self.GOLD
        )
        neighbor_label = self._font(label_size, bold=True).render(
            "BLUE = the only eight cells it can read this generation", True, self.accent
        )
        surface.blit(focus_label, focus_label.get_rect(midtop=(rect.centerx, origin_y + cell * 9 + 12)))
        surface.blit(neighbor_label, neighbor_label.get_rect(midtop=(rect.centerx, origin_y + cell * 9 + 35)))

    def _draw_synchronous_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        width = canvas.get_width()
        frames = (
            (
                (0, 0, 0, 0, 0, 0, 0),
                (0, 1, 1, 0, 0, 0, 0),
                (0, 1, 0, 0, 0, 0, 0),
                (0, 0, 0, 0, 0, 0, 0),
            ),
            (
                (0, 0, 0, 0, 0, 0, 0),
                (0, 0, 1, 1, 0, 0, 0),
                (0, 0, 1, 0, 0, 0, 0),
                (0, 0, 0, 0, 0, 0, 0),
            ),
            (
                (0, 0, 0, 0, 0, 0, 0),
                (0, 0, 0, 1, 1, 0, 0),
                (0, 0, 0, 1, 0, 0, 0),
                (0, 0, 0, 0, 0, 0, 0),
            ),
        )
        captions = (
            ("GENERATION 0 - READ", "Every destination inspects the cell on its left."),
            ("GENERATION 1 - COMMIT", "All calculated results appear together; the shape moved right."),
            ("GENERATION 2 - REPEAT", "The same rule is applied again. This is not a return to generation 0."),
        )
        gap = 42
        frame_width = (width - gap * 2) // 3
        visual_height = min(310, max(230, frame_width // 2))
        heading_font = self._font(self._font_sizes()[3], bold=True)
        label_font = self._font(self._font_sizes()[3], bold=True)
        for index, matrix in enumerate(frames):
            frame = pygame.Rect(index * (frame_width + gap), y, frame_width, visual_height)
            self._panel(canvas, frame, border=self.accent)
            title = heading_font.render(captions[index][0], True, theme["text"])
            canvas.blit(title, title.get_rect(midtop=(frame.centerx, frame.y + 12)))
            self._draw_matrix(
                canvas,
                pygame.Rect(frame.x + 16, frame.y + 44, frame.width - 32, frame.height - 108),
                matrix,
                (theme["background"], self.accent),
                border=self.accent,
            )
            detail_lines = self._wrap(captions[index][1], label_font, frame.width - 28)
            for line_index, line in enumerate(detail_lines[:2]):
                label = label_font.render(line, True, theme["menu_text"])
                canvas.blit(
                    label,
                    label.get_rect(midtop=(frame.centerx, frame.bottom - 53 + line_index * 20)),
                )
            if index < 2:
                arrow_x = frame.right + gap // 2
                pygame.draw.line(canvas, self.GOLD, (arrow_x - 12, frame.centery), (arrow_x + 10, frame.centery), 4)
                pygame.draw.polygon(canvas, self.GOLD, ((arrow_x + 17, frame.centery), (arrow_x + 5, frame.centery - 7), (arrow_x + 5, frame.centery + 7)))
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, y + visual_height + 18, width, 850),
        )

    def _draw_behaviors_page(self, canvas: pygame.Surface, y: int) -> int:
        """Explain stable, periodic, translating, and transient outcomes visually."""
        theme = self.services.theme()
        width = canvas.get_width()
        palette = (theme["background"], self.accent)
        block = (
            (0, 0, 0, 0),
            (0, 1, 1, 0),
            (0, 1, 1, 0),
            (0, 0, 0, 0),
        )
        vertical = (
            (0, 0, 0, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 0, 0, 0),
        )
        horizontal = (
            (0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0),
            (0, 1, 1, 1, 0),
            (0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0),
        )
        glider_a = (
            (0, 1, 0, 0, 0),
            (0, 0, 1, 0, 0),
            (1, 1, 1, 0, 0),
            (0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0),
        )
        glider_b = (
            (0, 0, 0, 0, 0),
            (0, 0, 1, 0, 0),
            (0, 0, 0, 1, 0),
            (0, 1, 1, 1, 0),
            (0, 0, 0, 0, 0),
        )
        lone = (
            (0, 0, 0),
            (0, 1, 0),
            (0, 0, 0),
        )
        empty = tuple(tuple(0 for _ in range(3)) for _ in range(3))
        rows = (
            ("STABLE - PERIOD 1", "Gen 0", block, "Gen 1 = Gen 0", block, "The block never changes."),
            ("OSCILLATOR - PERIOD 2", "Gen 0", vertical, "Gen 1", horizontal, "Gen 2 returns to Gen 0 because the blinker repeats every two updates."),
            ("TRANSLATING", "Gen 0", glider_a, "Gen 4", glider_b, "The glider repeats its shape one cell down and right."),
            ("TRANSIENT / DECAY", "Gen 0", lone, "Gen 1", empty, "A lone Conway cell has no surviving neighbors and disappears."),
        )
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        compact = width < 1100
        row_height = 232 if compact else 176
        for index, (title, left_label, left, right_label, right, detail) in enumerate(rows):
            row = pygame.Rect(0, y + index * (row_height + 12), width, row_height)
            self._panel(canvas, row, border=self.accent)
            title_text = heading.render(title, True, self.accent if index != 1 else self.GOLD)
            canvas.blit(title_text, (row.x + 18, row.y + 15))
            if compact:
                left_rect = pygame.Rect(row.x + 20, row.y + 55, 165, row.height - 72)
                right_rect = pygame.Rect(row.x + 220, row.y + 55, 165, row.height - 72)
            else:
                left_rect = pygame.Rect(row.x + 250, row.y + 12, 190, row.height - 24)
                right_rect = pygame.Rect(row.x + 510, row.y + 12, 190, row.height - 24)
            self._draw_matrix(canvas, left_rect, left, palette, border=self.accent)
            self._draw_matrix(canvas, right_rect, right, palette, border=self.accent)
            for text_value, rect_value in ((left_label, left_rect), (right_label, right_rect)):
                rendered = label.render(text_value, True, theme["text"])
                canvas.blit(rendered, rendered.get_rect(midbottom=(rect_value.centerx, rect_value.bottom - 6)))
            arrow_x = (left_rect.right + right_rect.x) // 2
            pygame.draw.line(canvas, self.GOLD, (arrow_x - 23, row.centery), (arrow_x + 17, row.centery), 4)
            pygame.draw.polygon(canvas, self.GOLD, ((arrow_x + 25, row.centery), (arrow_x + 12, row.centery - 8), (arrow_x + 12, row.centery + 8)))
            detail_start = right_rect.right
            if index == 1 and width >= 1100:
                third_rect = pygame.Rect(row.x + 770, row.y + 12, 190, row.height - 24)
                self._draw_matrix(canvas, third_rect, vertical, palette, border=self.GOLD)
                third_label = label.render("Gen 2 = Gen 0", True, self.GOLD)
                canvas.blit(third_label, third_label.get_rect(midbottom=(third_rect.centerx, third_rect.bottom - 6)))
                self._draw_arrow_between(canvas, right_rect.right, third_rect.x, row.centery)
                detail_start = third_rect.right
            detail_rect = pygame.Rect(
                detail_start + 28,
                row.y + (68 if compact else 40),
                row.right - detail_start - 46,
                row.height - (82 if compact else 54),
            )
            self._draw_wrapped(canvas, detail, label, theme["menu_text"], detail_rect, line_height=self._font_sizes()[3] + 6)
        visual_bottom = y + len(rows) * (row_height + 12)
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, visual_bottom + 8, width, 900),
        )

    def _draw_boundaries_page(self, canvas: pygame.Surface, y: int) -> int:
        """Contrast this app's fixed edge with a wrapped toroidal edge."""
        theme = self.services.theme()
        width = canvas.get_width()
        gap = 20
        panel_width = (width - gap) // 2
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        for index, title in enumerate(("FIXED EDGE - THIS APP", "WRAPPED EDGE - COMPARISON")):
            panel = pygame.Rect(index * (panel_width + gap), y, panel_width, 330)
            self._panel(canvas, panel, border=self.accent if index == 0 else self.GOLD)
            title_text = heading.render(title, True, self.accent if index == 0 else self.GOLD)
            canvas.blit(title_text, title_text.get_rect(midtop=(panel.centerx, panel.y + 16)))
            cell = 43
            grid = pygame.Rect(panel.centerx - cell * 4 // 2, panel.y + 65, cell * 4, cell * 4)
            for row in range(4):
                for col in range(4):
                    box = pygame.Rect(grid.x + col * cell, grid.y + row * cell, cell - 3, cell - 3)
                    pygame.draw.rect(canvas, self.accent if (row, col) == (1, 3) else theme["background"], box)
                    pygame.draw.rect(canvas, theme["grid"], box, 2)
            if index == 0:
                pygame.draw.line(canvas, self.MAGENTA, (grid.right + 10, grid.y), (grid.right + 10, grid.bottom), 5)
                cross = label.render("OUTSIDE = INACTIVE", True, self.MAGENTA)
                canvas.blit(cross, cross.get_rect(midtop=(panel.centerx, grid.bottom + 26)))
            else:
                arrow_y = grid.centery
                pygame.draw.arc(canvas, self.GOLD, pygame.Rect(grid.x - 44, grid.y - 22, grid.width + 88, grid.height + 44), 0.2, 2.95, 4)
                pygame.draw.polygon(canvas, self.GOLD, ((grid.x - 25, arrow_y), (grid.x - 10, arrow_y - 8), (grid.x - 10, arrow_y + 8)))
                wrapped = label.render("RIGHT CONNECTS TO LEFT", True, self.GOLD)
                canvas.blit(wrapped, wrapped.get_rect(midtop=(panel.centerx, grid.bottom + 26)))
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, y + 350, width, 900),
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

    def _draw_arrow_between(self, surface: pygame.Surface, left: int, right: int, y: int) -> None:
        """Draw one high-contrast left-to-right transition arrow."""
        middle = (left + right) // 2
        pygame.draw.line(surface, self.GOLD, (middle - 19, y), (middle + 13, y), 4)
        pygame.draw.polygon(
            surface,
            self.GOLD,
            ((middle + 22, y), (middle + 9, y - 8), (middle + 9, y + 8)),
        )

    def _draw_step_sequence(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        title: str,
        steps: Sequence[dict[str, object]],
    ) -> None:
        """Draw explicit before/reason/after panels for a local transition."""
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        heading_size = self._font_sizes()[1]
        label_size = self._font_sizes()[3]
        heading = self._font(heading_size, bold=True)
        label = self._font(label_size, bold=True)
        title_text = heading.render(title, True, theme["text"])
        surface.blit(title_text, title_text.get_rect(midtop=(rect.centerx, rect.y + 14)))
        gap = 38
        count = len(steps)
        card_width = (rect.width - 40 - gap * (count - 1)) // count
        top = rect.y + 54
        height = rect.height - 72
        for index, step in enumerate(steps):
            card = pygame.Rect(rect.x + 20 + index * (card_width + gap), top, card_width, height)
            pygame.draw.rect(surface, theme["stats_bar"], card, border_radius=9)
            pygame.draw.rect(surface, step.get("color", self.accent), card, 2, border_radius=9)
            caption = label.render(str(step["caption"]), True, theme["text"])
            surface.blit(caption, caption.get_rect(midtop=(card.centerx, card.y + 10)))
            matrix = step.get("matrix")
            if matrix is not None:
                palette = step.get("palette", self._mode_palette())
                self._draw_matrix(
                    surface,
                    pygame.Rect(card.x + 14, card.y + 39, card.width - 28, card.height - 101),
                    matrix,
                    palette,
                    border=step.get("color", self.accent),
                )
            else:
                big = heading.render(str(step.get("big", "")), True, step.get("color", self.accent))
                surface.blit(big, big.get_rect(center=(card.centerx, card.centery - 3)))
            detail_lines = self._wrap(str(step.get("detail", "")), label, card.width - 22)
            for line_index, line in enumerate(detail_lines[:2]):
                rendered = label.render(line, True, theme["menu_text"])
                surface.blit(
                    rendered,
                    rendered.get_rect(midtop=(card.centerx, card.bottom - 51 + line_index * 19)),
                )
            if index < count - 1:
                self._draw_arrow_between(surface, card.right, card.right + gap, card.centery)

    def _state_cards(self) -> tuple[tuple[str, tuple[int, int, int], str], ...]:
        theme = self.services.theme()
        if self.mode_key == "life":
            return (
                ("DEAD", theme["background"], "uses Birth list"),
                ("ALIVE", self.accent, "uses Survival list"),
            )
        if self.mode_key == "immigration":
            return (
                ("EMPTY", theme["background"], "counts 0"),
                ("SPECIES A", self.BLUE, "alive; counts 1"),
                ("SPECIES B", self.ORANGE, "alive; counts 1"),
            )
        if self.mode_key == "brians_brain":
            return (
                ("OFF", theme["background"], "can be excited"),
                ("FIRING", (90, 235, 255), "counts as firing"),
                ("DYING", (128, 82, 190), "not counted"),
                ("OFF AGAIN", theme["background"], "ready again"),
            )
        if self.mode_key == "langtons_ant":
            return (
                ("WHITE TILE", theme["background"], "turn right"),
                ("BLACK TILE", self.accent, "turn left"),
                ("ANT ARROW", self.GOLD, "position + heading"),
            )
        if self.mode_key == "wireworld":
            return (
                ("EMPTY", theme["background"], "no circuit"),
                ("HEAD", (80, 190, 255), "pulse front"),
                ("TAIL", self.MAGENTA, "pulse wake"),
                ("CONDUCTOR", self.GOLD, "circuit path"),
            )
        return tuple(
            (f"STATE {state}", color, f"seeks {(state + 1) % 8}")
            for state, color in enumerate(self._mode_palette())
        )

    def _draw_state_system_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        if self.mode_key == "cyclic_automaton":
            self._draw_cyclic_state_ring(surface, rect)
            return
        self._panel(surface, rect, border=self.accent)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        title = "READ THE STATE SYSTEM FROM LEFT TO RIGHT"
        if self.mode_key in ("life", "immigration", "langtons_ant"):
            title = "THESE STATES STORE DIFFERENT INFORMATION"
        title_text = heading.render(title, True, theme["text"])
        surface.blit(title_text, title_text.get_rect(midtop=(rect.centerx, rect.y + 15)))
        cards = self._state_cards()
        columns = min(len(cards), 4)
        rows = (len(cards) + columns - 1) // columns
        gap = 14
        usable_width = rect.width - 42
        card_width = (usable_width - gap * (columns - 1)) // columns
        card_height = (rect.height - 72 - gap * (rows - 1)) // rows
        for index, (name, color, detail) in enumerate(cards):
            row, col = divmod(index, columns)
            card = pygame.Rect(
                rect.x + 21 + col * (card_width + gap),
                rect.y + 55 + row * (card_height + gap),
                card_width,
                card_height,
            )
            pygame.draw.rect(surface, theme["stats_bar"], card, border_radius=8)
            pygame.draw.rect(surface, color if color != theme["background"] else theme["grid"], card, 3, border_radius=8)
            swatch_size = min(55, card.height - 72)
            swatch = pygame.Rect(card.centerx - swatch_size // 2, card.y + 18, swatch_size, swatch_size)
            pygame.draw.rect(surface, color, swatch, border_radius=7)
            pygame.draw.rect(surface, theme["text"], swatch, 1, border_radius=7)
            if self.mode_key == "langtons_ant" and name == "ANT ARROW":
                pygame.draw.polygon(surface, theme["background"], ((swatch.centerx, swatch.y + 7), (swatch.x + 8, swatch.bottom - 8), (swatch.right - 8, swatch.bottom - 8)))
            name_text = label.render(name, True, theme["text"])
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, swatch.bottom + 10)))
            surface.blit(detail_text, detail_text.get_rect(midtop=(card.centerx, swatch.bottom + 31)))
            if rows == 1 and index < len(cards) - 1 and self.mode_key in ("brians_brain", "cyclic_automaton"):
                self._draw_arrow_between(surface, card.right, card.right + gap, card.centery)
            if rows == 1 and index in (1, 2) and self.mode_key == "wireworld":
                self._draw_arrow_between(surface, card.right, card.right + gap, card.centery)

    def _draw_cyclic_state_ring(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw the eight-state successor relation as an actual closed cycle."""
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        title = heading.render("EACH STATE SEEKS THE NEXT; STATE 7 WRAPS TO STATE 0", True, theme["text"])
        surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 14)))
        positions = (
            (0.50, 0.23),
            (0.68, 0.29),
            (0.77, 0.50),
            (0.68, 0.71),
            (0.50, 0.77),
            (0.32, 0.71),
            (0.23, 0.50),
            (0.32, 0.29),
        )
        points = [
            pygame.Vector2(rect.x + rect.width * x, rect.y + rect.height * y)
            for x, y in positions
        ]
        palette = self._mode_palette()
        for index, start in enumerate(points):
            end = points[(index + 1) % len(points)]
            direction = end - start
            unit = direction.normalize()
            line_start = start + unit * 31
            line_end = end - unit * 31
            pygame.draw.line(surface, theme["grid"], line_start, line_end, 4)
            tip = line_start + (line_end - line_start) * 0.72
            perpendicular = pygame.Vector2(-unit.y, unit.x)
            pygame.draw.polygon(
                surface,
                self.GOLD,
                (tip + unit * 10, tip - unit * 8 + perpendicular * 6, tip - unit * 8 - perpendicular * 6),
            )
        for state, (point, color) in enumerate(zip(points, palette)):
            pygame.draw.circle(surface, color, point, 27)
            pygame.draw.circle(surface, theme["text"], point, 27, 2)
            number = heading.render(str(state), True, theme["background"] if state in (2, 3, 4) else theme["text"])
            surface.blit(number, number.get_rect(center=point))
        center = label.render("successor = (state + 1) mod 8", True, self.GOLD)
        surface.blit(center, center.get_rect(center=rect.center))

    def _draw_ant_step(
        self,
        surface: pygame.Surface,
        card: pygame.Rect,
        *,
        tile_black: bool,
        heading: str,
        moved: bool,
    ) -> None:
        theme = self.services.theme()
        cell = max(20, min(34, (card.height - 92) // 5, (card.width - 26) // 5))
        grid = pygame.Rect(card.centerx - cell * 5 // 2, card.y + 40, cell * 5, cell * 5)
        center = (2, 2)
        for row in range(5):
            for col in range(5):
                box = pygame.Rect(grid.x + col * cell, grid.y + row * cell, cell - 2, cell - 2)
                black = tile_black and (row, col) == center
                pygame.draw.rect(surface, self.accent if black else theme["background"], box)
                pygame.draw.rect(surface, theme["grid"], box, 1)
        row, col = center
        if moved:
            if heading == "right":
                col += 1
            elif heading == "left":
                col -= 1
            elif heading == "down":
                row += 1
            else:
                row -= 1
        cx = grid.x + col * cell + cell // 2
        cy = grid.y + row * cell + cell // 2
        points_by_heading = {
            "up": ((cx, cy - 12), (cx - 10, cy + 9), (cx + 10, cy + 9)),
            "right": ((cx + 12, cy), (cx - 9, cy - 10), (cx - 9, cy + 10)),
            "down": ((cx, cy + 12), (cx - 10, cy - 9), (cx + 10, cy - 9)),
            "left": ((cx - 12, cy), (cx + 9, cy - 10), (cx + 9, cy + 10)),
        }
        pygame.draw.polygon(surface, self.GOLD, points_by_heading[heading])
        pygame.draw.polygon(surface, theme["text"], points_by_heading[heading], 2)

    def _draw_ant_rule_visual(self, surface: pygame.Surface, rect: pygame.Rect, *, black: bool) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        turn = "LEFT" if black else "RIGHT"
        title = heading.render(f"READ -> TURN {turn} -> FLIP -> MOVE", True, theme["text"])
        surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 13)))
        captions = (
            f"1. READ {'BLACK' if black else 'WHITE'}",
            f"2. TURN {turn}",
            f"3. FLIP TO {'WHITE' if black else 'BLACK'}",
            "4. MOVE FORWARD",
        )
        gap = 34
        width = (rect.width - 38 - gap * 3) // 4
        for index, caption in enumerate(captions):
            card = pygame.Rect(rect.x + 19 + index * (width + gap), rect.y + 51, width, rect.height - 69)
            pygame.draw.rect(surface, theme["stats_bar"], card, border_radius=8)
            pygame.draw.rect(surface, self.accent, card, 2, border_radius=8)
            rendered = label.render(caption, True, theme["text"])
            surface.blit(rendered, rendered.get_rect(midtop=(card.centerx, card.y + 10)))
            heading_value = "left" if black and index >= 1 else "right" if not black and index >= 1 else "up"
            tile_black = black if index < 2 else not black
            self._draw_ant_step(surface, card, tile_black=tile_black, heading=heading_value, moved=index == 3)
            if index < 3:
                self._draw_arrow_between(surface, card.right, card.right + gap, card.centery)

    def _primary_rule_steps(self) -> tuple[str, tuple[dict[str, object], ...]]:
        theme = self.services.theme()
        key = self.mode_key
        if key == "life":
            palette = (theme["background"], self.accent, theme["button_hover"])
            before = ((1, 1, 0), (1, 2, 0), (0, 0, 0))
            after = ((1, 1, 0), (1, 1, 0), (0, 0, 0))
            return (
                "CONWAY EXAMPLE: B3/S23 (OTHER LIFE-LIKE RULES USE DIFFERENT LISTS)",
                (
                    {"caption": "OLD BOARD", "matrix": before, "palette": palette, "detail": "center is DEAD", "color": self.accent},
                    {"caption": "COUNT NEIGHBORS", "big": "3 LIVE", "detail": "exactly three", "color": self.GOLD},
                    {"caption": "NEW BOARD", "matrix": after, "palette": palette, "detail": "B3 -> center is BORN", "color": self.GREEN},
                ),
            )
        if key == "immigration":
            palette = (
                theme["background"],
                self.BLUE,
                self.ORANGE,
                theme["button_hover"],
                theme["text"],
            )
            before = ((1, 2, 0), (2, 3, 0), (0, 0, 0))
            after = ((1, 2, 0), (2, 4, 0), (0, 0, 0))
            return (
                "STAGE 1: COUNT BOTH SPECIES AS ALIVE",
                (
                    {"caption": "OLD BOARD", "matrix": before, "palette": palette, "detail": "A + B + B around empty", "color": self.accent},
                    {"caption": "OCCUPANCY COUNT", "big": "3 ALIVE", "detail": "colors do not alter B3", "color": self.GOLD},
                    {"caption": "BIRTH OCCURS", "matrix": after, "palette": palette, "detail": "color is assigned next", "color": self.GREEN},
                ),
            )
        if key == "brians_brain":
            firing = (90, 235, 255)
            palette = (theme["background"], firing, (128, 82, 190), theme["button_hover"])
            before = ((1, 0, 0), (0, 3, 1), (0, 0, 0))
            after = ((2, 0, 0), (0, 1, 2), (0, 0, 0))
            return (
                "ONLY FIRING NEIGHBORS ARE COUNTED",
                (
                    {"caption": "OLD BOARD", "matrix": before, "palette": palette, "detail": "center is OFF", "color": firing},
                    {"caption": "COUNT", "big": "2 FIRING", "detail": "exactly two", "color": self.GOLD},
                    {"caption": "NEW BOARD", "matrix": after, "palette": palette, "detail": "center starts FIRING", "color": self.GREEN},
                ),
            )
        if key == "wireworld":
            palette = self._mode_palette()
            frames = (
                (3, 3, 2, 1, 3, 3, 3, 3, 3),
                (3, 3, 3, 2, 1, 3, 3, 3, 3),
                (3, 3, 3, 3, 2, 1, 3, 3, 3),
                (3, 3, 3, 3, 3, 2, 1, 3, 3),
            )
            steps = tuple(
                {
                    "caption": f"GEN {index}",
                    "matrix": (frame,),
                    "palette": palette,
                    "detail": "TAIL behind HEAD",
                    "color": self.GOLD,
                }
                for index, frame in enumerate(frames)
            )
            return "THE HEAD-TAIL PHASE RECREATES THE PULSE ONE CELL AHEAD", steps
        palette = self._mode_palette()
        before = ((4, 0, 0), (4, 3, 0), (4, 0, 0))
        after = ((4, 0, 0), (4, 4, 0), (4, 0, 0))
        return (
            "STATE 3 SEEKS ONLY STATE 4",
            (
                {"caption": "OLD BOARD", "matrix": before, "palette": palette, "detail": "center is state 3", "color": palette[3]},
                {"caption": "COUNT SUCCESSOR", "big": "3 x STATE 4", "detail": "threshold reached", "color": palette[4]},
                {"caption": "NEW BOARD", "matrix": after, "palette": palette, "detail": "center advances to 4", "color": self.GREEN},
            ),
        )

    def _neighbor_matrix(self, count: int, center: int, neighbor: int = 1) -> tuple[tuple[int, ...], ...]:
        positions = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2))
        matrix = [[0, 0, 0], [0, center, 0], [0, 0, 0]]
        for row, col in positions[:count]:
            matrix[row][col] = neighbor
        return tuple(tuple(row) for row in matrix)

    def _secondary_rule_steps(self) -> tuple[str, tuple[dict[str, object], ...]]:
        theme = self.services.theme()
        key = self.mode_key
        if key == "life":
            palette = (theme["background"], self.accent)
            return (
                "A LIVE CENTER USES S23",
                tuple(
                    {
                        "caption": f"{count} LIVE NEIGHBOR{'S' if count != 1 else ''}",
                        "matrix": self._neighbor_matrix(count, 1),
                        "palette": palette,
                        "detail": result,
                        "color": color,
                    }
                    for count, result, color in (
                        (1, "dies: isolation", self.MAGENTA),
                        (2, "survives", self.GREEN),
                        (3, "survives", self.GREEN),
                        (4, "dies: crowding", self.MAGENTA),
                    )
                ),
            )
        if key == "immigration":
            palette = (theme["background"], self.BLUE, self.ORANGE, theme["button_hover"])
            return (
                "STAGE 2: COLOR ONLY A NEWBORN",
                (
                    {"caption": "A + A + B", "matrix": ((1, 1, 0), (2, 3, 0), (0, 0, 0)), "palette": palette, "detail": "newborn becomes A", "color": self.BLUE},
                    {"caption": "A + B + B", "matrix": ((1, 2, 0), (2, 3, 0), (0, 0, 0)), "palette": palette, "detail": "newborn becomes B", "color": self.ORANGE},
                    {"caption": "EXISTING SURVIVOR", "big": "A STAYS A", "detail": "neighbors never recolor it", "color": self.GREEN},
                ),
            )
        if key == "brians_brain":
            firing = (90, 235, 255)
            palette = (theme["background"], firing, (128, 82, 190))
            return (
                "THE REFRACTORY CYCLE IS UNCONDITIONAL",
                (
                    {"caption": "GEN t", "matrix": ((1,),), "palette": palette, "detail": "FIRING; excites neighbors", "color": firing},
                    {"caption": "GEN t + 1", "matrix": ((2,),), "palette": palette, "detail": "DYING; not counted", "color": self.MAGENTA},
                    {"caption": "GEN t + 2", "matrix": ((0,),), "palette": palette, "detail": "OFF; ready again", "color": theme["grid"]},
                ),
            )
        if key == "wireworld":
            palette = self._mode_palette()
            return (
                "THE CENTER CONDUCTOR COUNTS NEIGHBORING HEADS",
                tuple(
                    {
                        "caption": f"{count} HEAD NEIGHBOR{'S' if count != 1 else ''}",
                        "matrix": self._neighbor_matrix(count, 3, 1),
                        "palette": palette,
                        "detail": "becomes HEAD" if count in (1, 2) else "stays CONDUCTOR",
                        "color": (80, 190, 255) if count in (1, 2) else self.GOLD,
                    }
                    for count in range(4)
                ),
            )
        palette = self._mode_palette()
        below = self._neighbor_matrix(2, 3, 4)
        enough = self._neighbor_matrix(3, 3, 4)
        return (
            "EXAMPLE THRESHOLD = 3 SUCCESSOR NEIGHBORS",
            (
                {"caption": "COUNT = 2", "matrix": below, "palette": palette, "detail": "below threshold: stays 3", "color": palette[3]},
                {"caption": "COUNT = 3", "matrix": enough, "palette": palette, "detail": "threshold met: becomes 4", "color": palette[4]},
            ),
        )

    def _draw_mode_lesson_page(self, canvas: pygame.Surface, y: int) -> int:
        """Draw a state, rule, process, or application lesson with mode-specific evidence."""
        width = canvas.get_width()
        kind = self.page.kind
        visual_height = 340
        visual = pygame.Rect(0, y, width, visual_height)
        if kind == "mode_states":
            self._draw_state_system_visual(canvas, visual)
        elif kind == "mode_rule_primary" and self.mode_key == "langtons_ant":
            self._draw_ant_rule_visual(canvas, visual, black=False)
        elif kind == "mode_rule_secondary" and self.mode_key == "langtons_ant":
            self._draw_ant_rule_visual(canvas, visual, black=True)
        elif kind == "mode_rule_primary":
            title, steps = self._primary_rule_steps()
            self._draw_step_sequence(canvas, visual, title, steps)
        elif kind == "mode_rule_secondary":
            title, steps = self._secondary_rule_steps()
            self._draw_step_sequence(canvas, visual, title, steps)
        elif kind == "mode_process":
            self._draw_process_visual(canvas, visual)
        else:
            self._draw_application_visual(canvas, visual)
        return self._draw_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, visual.bottom + 16, width, 1100),
        )

    def _draw_process_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        key = self.mode_key
        if key == "immigration":
            palette = (theme["background"], self.BLUE, self.ORANGE)
            steps = (
                {"caption": "OCCUPANCY", "matrix": ((0, 1, 1, 0), (1, 1, 1, 0), (0, 1, 0, 0)), "palette": (theme["background"], theme["text"]), "detail": "predict B3/S23 geometry", "color": theme["text"]},
                {"caption": "SAME CELLS + LINEAGE", "matrix": ((0, 1, 2, 0), (1, 2, 2, 0), (0, 1, 0, 0)), "palette": palette, "detail": "colors preserve ancestry", "color": self.accent},
                {"caption": "NEXT BIRTH", "matrix": ((0, 1, 2, 0), (1, 2, 2, 0), (0, 1, 2, 0)), "palette": palette, "detail": "majority parents color it", "color": self.GREEN},
            )
            self._draw_step_sequence(surface, rect, "ONE GEOMETRY LAYER + ONE LINEAGE LAYER", steps)
            return
        if key == "brians_brain":
            palette = self._mode_palette()
            frames = (
                ((0, 0, 1, 2, 0, 0),),
                ((0, 0, 0, 1, 2, 0),),
                ((0, 0, 0, 0, 1, 2),),
                ((0, 0, 0, 0, 0, 1),),
            )
            steps = tuple(
                {"caption": f"GEN {index}", "matrix": frame, "palette": palette, "detail": "firing front + dying wake", "color": (90, 235, 255)}
                for index, frame in enumerate(frames)
            )
            self._draw_step_sequence(surface, rect, "NEW FIRING APPEARS AHEAD; OLD FIRING COOLS BEHIND", steps)
            return
        if key == "langtons_ant":
            self._panel(surface, rect, border=self.accent)
            heading = self._font(self._font_sizes()[1], bold=True)
            label = self._font(self._font_sizes()[3], bold=True)
            title = heading.render("A SIX-STEP TRACE: THE BOARD REMEMBERS EVERY VISIT", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 15)))
            grid = pygame.Rect(rect.centerx - 250, rect.y + 58, 500, 238)
            cell = 39
            origin = (grid.centerx - cell * 6 // 2, grid.centery - cell * 6 // 2)
            for row in range(6):
                for col in range(6):
                    box = pygame.Rect(origin[0] + col * cell, origin[1] + row * cell, cell - 2, cell - 2)
                    pygame.draw.rect(surface, theme["background"], box)
                    pygame.draw.rect(surface, theme["grid"], box, 1)
            path = ((3, 3), (3, 4), (4, 4), (4, 3), (4, 2), (3, 2), (3, 3))
            points = []
            for step, (row, col) in enumerate(path):
                center = (origin[0] + col * cell + cell // 2, origin[1] + row * cell + cell // 2)
                points.append(center)
                if step < len(path) - 1:
                    pygame.draw.rect(surface, self.accent, pygame.Rect(center[0] - 13, center[1] - 13, 26, 26), border_radius=3)
                    number = label.render(str(step + 1), True, theme["text"])
                    surface.blit(number, number.get_rect(center=center))
            pygame.draw.lines(surface, self.GOLD, False, points, 4)
            note = label.render("Re-entering a flipped tile changes the next turn", True, self.GOLD)
            surface.blit(note, note.get_rect(midbottom=(rect.centerx, rect.bottom - 16)))
            return
        if key == "wireworld":
            matrix = (
                (0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                (3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3),
                (0, 0, 0, 3, 0, 0, 0, 3, 0, 0, 0, 0, 0),
                (3, 3, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3),
                (0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0),
            )
            self._panel(surface, rect, border=self.accent)
            heading = self._font(self._font_sizes()[1], bold=True)
            label = self._font(self._font_sizes()[3], bold=True)
            title = heading.render("JUNCTION GEOMETRY CHANGES HOW MANY HEADS REACH A CELL", True, theme["text"])
            surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 15)))
            self._draw_matrix(surface, pygame.Rect(rect.x + 150, rect.y + 56, rect.width - 300, rect.height - 104), matrix, self._mode_palette(), border=self.accent)
            for text_value, position in (("INPUT A", (rect.x + 55, rect.y + 105)), ("INPUT B", (rect.x + 55, rect.y + 230)), ("OUTPUT", (rect.right - 75, rect.centery))):
                rendered = label.render(text_value, True, self.GOLD)
                surface.blit(rendered, rendered.get_rect(center=position))
            return
        palette = self._mode_palette()
        frames = tuple(
            tuple(tuple((row + col + generation) % 8 for col in range(8)) for row in range(5))
            for generation in range(3)
        )
        steps = tuple(
            {"caption": f"GEN {index}", "matrix": frame, "palette": palette, "detail": "successor front advances", "color": palette[(index + 3) % 8]}
            for index, frame in enumerate(frames)
        )
        self._draw_step_sequence(surface, rect, "COLOR BANDS ADVANCE AROUND THE CYCLIC STATE RING", steps)

    def _draw_application_visual(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.accent)
        heading = self._font(self._font_sizes()[1], bold=True)
        label = self._font(self._font_sizes()[3], bold=True)
        title = heading.render("BUILD -> INJECT -> STEP -> READ", True, theme["text"])
        surface.blit(title, title.get_rect(midtop=(rect.centerx, rect.y + 15)))
        stages = (
            ("1", "CONDUCTOR", "fixed geometry", self.GOLD),
            ("2", "HEAD + TAIL", "input pulse", (80, 190, 255)),
            ("3", "STEP", "inspect junctions", self.MAGENTA),
            ("4", "OUTPUT", "pulse = logical 1", self.GREEN),
        )
        gap = 34
        width = (rect.width - 40 - gap * 3) // 4
        for index, (number, name, detail, color) in enumerate(stages):
            card = pygame.Rect(rect.x + 20 + index * (width + gap), rect.y + 58, width, rect.height - 82)
            pygame.draw.rect(surface, theme["stats_bar"], card, border_radius=9)
            pygame.draw.rect(surface, color, card, 3, border_radius=9)
            pygame.draw.circle(surface, color, (card.centerx, card.y + 55), 29)
            number_text = heading.render(number, True, theme["background"])
            surface.blit(number_text, number_text.get_rect(center=(card.centerx, card.y + 55)))
            name_text = heading.render(name, True, theme["text"])
            detail_text = label.render(detail, True, theme["menu_text"])
            surface.blit(name_text, name_text.get_rect(midtop=(card.centerx, card.y + 103)))
            surface.blit(detail_text, detail_text.get_rect(midtop=(card.centerx, card.y + 139)))
            if index < 3:
                self._draw_arrow_between(surface, card.right, card.right + gap, card.centery)

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
        elif self.page.kind == "behaviors":
            y = self._draw_behaviors_page(canvas, y)
        elif self.page.kind == "model":
            y = self._draw_model_page(canvas, y)
        elif self.page.kind == "boundaries":
            y = self._draw_boundaries_page(canvas, y)
        elif self.page.kind == "laboratory":
            y = self._draw_laboratory_page(canvas, y)
        elif self.page.kind == "mode_identity":
            y = self._draw_mode_identity_page(canvas, y)
        elif self.page.kind in {
            "mode_states",
            "mode_rule_primary",
            "mode_rule_secondary",
            "mode_process",
            "mode_application",
        }:
            y = self._draw_mode_lesson_page(canvas, y)
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

        tab_labels = (self.foundation_tab_label, self.mode_tab_label)
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
                self.FOUNDATION_ACCENT if index == 0 else self.mode_accent,
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
