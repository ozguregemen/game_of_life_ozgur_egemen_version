"""Full-screen, visual tutorial for one-dimensional cellular automata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import pygame


SEP_CELLULAR_AUTOMATA = "https://plato.stanford.edu/entries/cellular-automata/"
WOLFRAM_1983 = "https://doi.org/10.1103/RevModPhys.55.601"
MATHWORLD_ELEMENTARY_CA = (
    "https://mathworld.wolfram.com/ElementaryCellularAutomaton.html"
)
WOLFRAM_CLASSES = (
    "https://www.wolframscience.com/nks/p231--four-classes-of-behavior/"
)
COOK_RULE_110 = "https://doi.org/10.25088/complexsystems.15.1.1"
RULE_184_TRAFFIC = "https://doi.org/10.11540/bjsiam.12.2_128"


@dataclass(frozen=True)
class TutorialSection:
    """One ordered concept in a tutorial page."""

    title: str
    body: str


@dataclass(frozen=True)
class TutorialPage:
    """User-facing content and renderer kind for one lesson step."""

    kicker: str
    title: str
    lead: str
    sections: tuple[TutorialSection, ...] = ()
    kind: str = "concepts"


@dataclass(frozen=True)
class TutorialSource:
    """A readable citation paired with an external destination."""

    category: str
    title: str
    detail: str
    url: str


@dataclass(frozen=True)
class TutorialServices:
    """Application resources and callbacks used by the tutorial."""

    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    current_rule: Callable[[], int]
    apply_canonical_rule: Callable[[int], None]
    open_url: Callable[[str], bool]
    pause: Callable[[], None]
    set_status: Callable[[str, float], None]


ONE_D_TUTORIAL_PAGES: tuple[TutorialPage, ...] = (
    TutorialPage(
        "LESSON 1 - THE BIG IDEA",
        "One line becomes a history",
        (
            "Begin with one row of cells. Apply the same local rule everywhere, at "
            "the same moment. Put every new row below the previous one and a complete "
            "space-time history appears."
        ),
        (
            TutorialSection(
                "1. Read space from left to right",
                "Each square is one position. Elementary automata use only state 0 "
                "(background) and state 1 (active).",
            ),
            TutorialSection(
                "2. Read time from top to bottom",
                "The first row is generation 0. The next row is generation 1; it is "
                "history, not a second spatial direction.",
            ),
            TutorialSection(
                "3. Every cell follows one local rule",
                "A cell reads only nearby cells. No cell sees the complete line, yet "
                "large triangles and intricate textures can emerge.",
            ),
            TutorialSection(
                "4. Control the experiment",
                "Left click writes, right click erases, Space runs, and N advances "
                "exactly one generation while paused.",
            ),
        ),
        kind="space_time",
    ),
    TutorialPage(
        "LESSON 2 - HISTORY",
        "An idea developed across generations",
        (
            "Cellular automata were not invented as a single game. They grew from "
            "questions about self-reproduction, simple computation and the emergence "
            "of complex behavior."
        ),
        (
            TutorialSection(
                "1940s-1950s - von Neumann and Ulam",
                "John von Neumann studied logical self-reproduction. Ideas from "
                "Stanislaw Ulam about discrete lattices helped lead to a formal, "
                "many-state two-dimensional cellular automaton.",
            ),
            TutorialSection(
                "1980s - Stephen Wolfram",
                "Wolfram systematically investigated very simple one-dimensional "
                "automata, established the familiar rule numbering and proposed four "
                "qualitative classes of behavior.",
            ),
            TutorialSection(
                "2004 - Matthew Cook",
                "Cook published a proof that Rule 110 can perform universal "
                "computation when information is encoded in a carefully prepared "
                "periodic background.",
            ),
            TutorialSection(
                "Today - a scientific caution",
                "A cellular automaton is an abstract dynamical system. Looking like a "
                "natural process does not, by itself, prove that it models that process.",
            ),
        ),
        kind="timeline",
    ),
    TutorialPage(
        "LESSON 3 - THE RULE",
        "Turn eight local decisions into one number",
        (
            "An Elementary cell reads three bits: left, center and right. Eight "
            "neighborhoods are possible. Their eight outputs form a binary number "
            "between 0 and 255."
        ),
        (
            TutorialSection(
                "Why 256?",
                "Three binary inputs give 2^3 = 8 neighborhoods. A binary output is "
                "chosen for each one, giving 2^8 = 256 complete rule tables.",
            ),
            TutorialSection(
                "One update at a time",
                "Match a cell's left-center-right triplet to the table. The displayed "
                "output becomes that center cell in the next generation.",
            ),
        ),
        kind="rule_table",
    ),
    TutorialPage(
        "LESSON 4 - EXPERIMENT DESIGN",
        "The rule is only one part of the experiment",
        (
            "A rule does not define one picture. Seed, boundary, width and duration "
            "also determine what you observe. Record them whenever results are compared."
        ),
        (
            TutorialSection(
                "1. Canonical single-cell seed",
                "One active center cell on a state-0 background makes growth and "
                "left-right structure easy to see.",
            ),
            TutorialSection(
                "2. Infinite background",
                "The represented line expands when activity reaches an edge. Outside "
                "cells evolve uniformly instead of wrapping around.",
            ),
            TutorialSection(
                "3. Fixed-zero boundary",
                "Invisible walls force every outside cell to 0. Edge collisions can "
                "therefore change the long-term result.",
            ),
            TutorialSection(
                "4. Wrap boundary",
                "The first and last cells become neighbors, making a ring. This is "
                "useful for fixed-size and traffic-like experiments.",
            ),
        ),
        kind="boundaries",
    ),
    TutorialPage(
        "LESSON 5 - LANDMARK RULES",
        "See how different four tiny programs can be",
        (
            "Each preview below is generated from its actual rule table. Load an "
            "experiment to return to the lab with an Elementary rule, centered "
            "single-cell seed and infinite state-0 background."
        ),
        kind="examples",
    ),
    TutorialPage(
        "LESSON 6 - BEYOND ELEMENTARY",
        "Change one assumption at a time",
        (
            "Elementary rules are a starting point, not the definition of 1D cellular "
            "automata. The workspace lets you widen the state alphabet, neighborhood "
            "and memory while keeping the experiment measurable."
        ),
        (
            TutorialSection(
                "1. More states or totalistic rules",
                "Use three or four states, or let the neighborhood sum choose the next "
                "state instead of the exact left-to-right arrangement.",
            ),
            TutorialSection(
                "2. A larger neighborhood radius",
                "Radius 2 or 3 lets a cell consult more distant positions. The number "
                "of possible local configurations grows very quickly.",
            ),
            TutorialSection(
                "3. Time memory and reversibility",
                "Higher-order rules also read an earlier row. Reversible constructions "
                "retain enough information to reconstruct the past.",
            ),
            TutorialSection(
                "4. Observe, measure, compare, export",
                "Save a profile, compare two rules under one seed, inspect entropy and "
                "change rate, then export the diagram, metrics and experiment JSON.",
            ),
        ),
        kind="families",
    ),
    TutorialPage(
        "LESSON 7 - SOURCES",
        "Continue from overview to original research",
        (
            "The list is ordered as a reading path: begin with the overview, learn the "
            "notation, then continue to original papers and specialized results."
        ),
        kind="sources",
    ),
)


TUTORIAL_SOURCES: tuple[TutorialSource, ...] = (
    TutorialSource(
        "OVERVIEW",
        "Stanford Encyclopedia of Philosophy - Cellular Automata",
        "History, formal definitions, Wolfram classes and a scholarly bibliography.",
        SEP_CELLULAR_AUTOMATA,
    ),
    TutorialSource(
        "PRIMARY PAPER",
        "Wolfram (1983) - Statistical Mechanics of Cellular Automata",
        "Original Reviews of Modern Physics study of simple one-dimensional automata.",
        WOLFRAM_1983,
    ),
    TutorialSource(
        "RULE CATALOGUE",
        "Wolfram MathWorld - Elementary Cellular Automaton",
        "Transition tables, numbering conventions and the complete 256-rule catalogue.",
        MATHWORLD_ELEMENTARY_CA,
    ),
    TutorialSource(
        "TAXONOMY",
        "Wolfram - Four Classes of Behavior",
        "The author's visual presentation of the qualitative four-class taxonomy.",
        WOLFRAM_CLASSES,
    ),
    TutorialSource(
        "PROOF",
        "Cook (2004) - Universality in Elementary Cellular Automata",
        "Published proof of Rule 110 computational universality.",
        COOK_RULE_110,
    ),
    TutorialSource(
        "APPLICATION",
        "Nishinari (2002) - Cellular Automaton Models of Traffic Flow",
        "Scholarly context for Rule 184 as a prototype traffic cellular automaton.",
        RULE_184_TRAFFIC,
    ),
)


RULE_EXAMPLES: tuple[tuple[int, str, str], ...] = (
    (
        30,
        "Rule 30 - asymmetric complexity",
        "A regular edge surrounds an irregular-looking interior: a classic example "
        "of complex output from a tiny deterministic rule.",
    ),
    (
        90,
        "Rule 90 - an additive fractal",
        "The update is left XOR right. A single cell reveals the self-similar "
        "Sierpinski-triangle structure.",
    ),
    (
        110,
        "Rule 110 - computational universality",
        "Localized structures can interact. Cook's universality construction uses "
        "carefully encoded periodic backgrounds.",
    ),
    (
        184,
        "Rule 184 - transport and traffic",
        "State-1 cells move through state-0 gaps. A wrapped random row makes free flow "
        "and congestion especially easy to investigate.",
    ),
)


class OneDimensionalTutorial:
    """Large-format, visual and keyboard-accessible 1D learning experience."""

    ACCENT = (75, 185, 245)
    GOLD = (245, 186, 72)
    GREEN = (91, 211, 148)
    MAGENTA = (229, 112, 171)

    def __init__(self, services: TutorialServices) -> None:
        self.services = services
        self.active = False
        self.page_index = 0
        self.scroll = 0
        self.content_height = 0
        self._interactions: list[tuple[str, str, pygame.Rect]] = []
        self._local_interactions: list[tuple[str, str, pygame.Rect]] = []
        self._fonts: dict[tuple[int, bool], pygame.font.Font] = {}

    @property
    def page_count(self) -> int:
        return len(ONE_D_TUTORIAL_PAGES)

    @property
    def page(self) -> TutorialPage:
        return ONE_D_TUTORIAL_PAGES[self.page_index]

    def open(self) -> None:
        """Pause the simulation and show the tutorial only on explicit request."""
        self.services.pause()
        self.active = True
        self.scroll = 0

    def close(self) -> None:
        self.active = False
        self._interactions.clear()

    def _font(self, size: int, *, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont("Segoe UI", size, bold=bold)
        return self._fonts[key]

    def _font_sizes(self) -> tuple[int, int, int, int]:
        _, height = self.services.window_size()
        title = max(27, min(42, round(height * 0.038)))
        heading = max(20, min(27, round(height * 0.024)))
        body = max(17, min(22, round(height * 0.019)))
        label = max(14, min(18, round(height * 0.015)))
        return title, heading, body, label

    def geometry(
        self,
    ) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        width, height = self.services.window_size()
        margin = 8 if min(width, height) < 700 else 14
        modal = pygame.Rect(margin, margin, width - margin * 2, height - margin * 2)
        header_height = max(98, min(132, round(height * 0.13)))
        footer_height = max(60, min(76, round(height * 0.075)))
        close = pygame.Rect(modal.right - 50, modal.y + 17, 32, 30)
        viewport = pygame.Rect(
            modal.x + 24,
            modal.y + header_height,
            modal.width - 48,
            modal.height - header_height - footer_height,
        )
        back = pygame.Rect(modal.x + 24, modal.bottom - footer_height + 13, 148, 40)
        next_button = pygame.Rect(
            modal.right - 184,
            modal.bottom - footer_height + 13,
            160,
            40,
        )
        return modal, viewport, close, back, next_button

    def _maximum_scroll(self, viewport: pygame.Rect) -> int:
        return max(0, self.content_height - viewport.height)

    def _move(self, delta: int) -> None:
        target = self.page_index + delta
        if target >= self.page_count:
            self.close()
            self.services.set_status(
                "1D tutorial complete. Choose a landmark rule and run an experiment.",
                5.0,
            )
            return
        self.page_index = max(0, target)
        self.scroll = 0
        self._interactions.clear()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_F2):
                self.close()
            elif event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN, pygame.K_RETURN):
                self._move(1)
            elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP, pygame.K_BACKSPACE):
                self._move(-1)
            elif event.key == pygame.K_HOME:
                self.page_index = 0
                self.scroll = 0
            elif event.key == pygame.K_END:
                self.page_index = self.page_count - 1
                self.scroll = 0
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 56)
            elif event.key == pygame.K_DOWN:
                _, viewport, _, _, _ = self.geometry()
                self.scroll = min(self._maximum_scroll(viewport), self.scroll + 56)
            return True
        if event.type == pygame.MOUSEWHEEL:
            _, viewport, _, _, _ = self.geometry()
            self.scroll = max(
                0,
                min(self._maximum_scroll(viewport), self.scroll - event.y * 58),
            )
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            modal, _, close, back, next_button = self.geometry()
            if close.collidepoint(event.pos) or not modal.collidepoint(event.pos):
                self.close()
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
                if action == "rule":
                    self.services.apply_canonical_rule(int(payload))
                    self.close()
                elif action == "url":
                    opened = self.services.open_url(payload)
                    self.services.set_status(
                        "Source opened in the default browser."
                        if opened
                        else "The source could not be opened; its URL is in README.",
                        4.0,
                    )
                return True
            return True
        return True

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

    @staticmethod
    def _mix(
        first: tuple[int, int, int],
        second: tuple[int, int, int],
        amount: float,
    ) -> tuple[int, int, int]:
        return tuple(
            round(a + (b - a) * amount) for a, b in zip(first, second)
        )

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

    @staticmethod
    def _eca_rows(
        rule: int,
        width: int,
        generations: int,
        *,
        seed: Sequence[int] | None = None,
        wrap: bool = False,
    ) -> list[tuple[int, ...]]:
        if width <= 0 or generations <= 0:
            return []
        if seed is None:
            row = [0] * width
            row[width // 2] = 1
        else:
            values = [1 if value else 0 for value in seed]
            if len(values) >= width:
                start = (len(values) - width) // 2
                row = values[start : start + width]
            else:
                leading = (width - len(values)) // 2
                row = (
                    [0] * leading
                    + values
                    + [0] * (width - leading - len(values))
                )
        rows = [tuple(row)]
        for _ in range(generations - 1):
            following: list[int] = []
            for index in range(width):
                left = row[(index - 1) % width] if wrap else (row[index - 1] if index else 0)
                center = row[index]
                right = row[(index + 1) % width] if wrap else (
                    row[index + 1] if index + 1 < width else 0
                )
                neighborhood = left * 4 + center * 2 + right
                following.append((rule >> neighborhood) & 1)
            row = following
            rows.append(tuple(row))
        return rows

    def _draw_ca_diagram(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        rule: int,
        *,
        generations: int = 22,
        seed: Sequence[int] | None = None,
        wrap: bool = False,
        labels: bool = False,
    ) -> None:
        theme = self.services.theme()
        self._panel(surface, rect, border=self.ACCENT)
        inner = rect.inflate(-28, -28)
        label_margin_x = 48 if labels else 0
        label_margin_y = 30 if labels else 0
        drawing = pygame.Rect(
            inner.x + label_margin_x,
            inner.y + label_margin_y,
            inner.width - label_margin_x,
            inner.height - label_margin_y,
        )
        cell = max(3, min(13, drawing.height // generations))
        columns = max(9, drawing.width // cell)
        if columns % 2 == 0:
            columns -= 1
        rows = self._eca_rows(
            rule,
            columns,
            min(generations, drawing.height // cell),
            seed=seed,
            wrap=wrap,
        )
        diagram_width = columns * cell
        origin_x = drawing.centerx - diagram_width // 2
        origin_y = drawing.y
        active = theme["cell"]
        inactive = self._mix(theme["background"], theme["button"], 0.45)
        for row_index, row in enumerate(rows):
            for column, value in enumerate(row):
                cell_rect = pygame.Rect(
                    origin_x + column * cell,
                    origin_y + row_index * cell,
                    max(1, cell - 1),
                    max(1, cell - 1),
                )
                pygame.draw.rect(surface, active if value else inactive, cell_rect)
        _, _, body_size, label_size = self._font_sizes()
        if labels:
            label_font = self._font(label_size, bold=True)
            space = label_font.render("SPACE", True, self.ACCENT)
            surface.blit(space, (drawing.x, inner.y))
            pygame.draw.line(
                surface,
                self.ACCENT,
                (drawing.x + space.get_width() + 12, inner.y + space.get_height() // 2),
                (drawing.right - 8, inner.y + space.get_height() // 2),
                2,
            )
            pygame.draw.polygon(
                surface,
                self.ACCENT,
                ((drawing.right, inner.y + space.get_height() // 2),
                 (drawing.right - 9, inner.y + space.get_height() // 2 - 5),
                 (drawing.right - 9, inner.y + space.get_height() // 2 + 5)),
            )
            time = label_font.render("TIME", True, self.GOLD)
            rotated = pygame.transform.rotate(time, 90)
            surface.blit(rotated, (inner.x + 3, drawing.y + 12))
            line_x = inner.x + rotated.get_width() // 2 + 3
            pygame.draw.line(
                surface,
                self.GOLD,
                (line_x, drawing.y + rotated.get_height() + 22),
                (line_x, drawing.bottom - 8),
                2,
            )
            pygame.draw.polygon(
                surface,
                self.GOLD,
                ((line_x, drawing.bottom), (line_x - 5, drawing.bottom - 9),
                 (line_x + 5, drawing.bottom - 9)),
            )
            caption = self._font(body_size, bold=True).render(
                f"Rule {rule}: every row is one new generation",
                True,
                theme["text"],
            )
            surface.blit(caption, caption.get_rect(midbottom=(rect.centerx, rect.bottom - 9)))

    def _section_height(
        self,
        section: TutorialSection,
        text_width: int,
    ) -> int:
        _, heading_size, body_size, _ = self._font_sizes()
        body_font = self._font(body_size)
        lines = self._wrap(section.body, body_font, text_width)
        return max(102, 47 + len(lines) * (body_size + 6) + 20)

    def _draw_numbered_sections(
        self,
        canvas: pygame.Surface,
        sections: Sequence[TutorialSection],
        rect: pygame.Rect,
        *,
        visual: Callable[[pygame.Surface, pygame.Rect, int], None] | None = None,
    ) -> int:
        theme = self.services.theme()
        _, heading_size, body_size, label_size = self._font_sizes()
        heading_font = self._font(heading_size, bold=True)
        body_font = self._font(body_size)
        y = rect.y
        for index, section in enumerate(sections):
            visual_width = min(240, round(rect.width * 0.22)) if visual else 0
            text_width = rect.width - 88 - visual_width
            height = self._section_height(section, text_width)
            card = pygame.Rect(rect.x, y, rect.width, height)
            self._panel(canvas, card, border=self._mix(self.ACCENT, theme["grid"], 0.45))
            badge = pygame.Rect(card.x + 18, card.centery - 25, 50, 50)
            pygame.draw.rect(canvas, self.ACCENT, badge, border_radius=9)
            number = self._font(heading_size, bold=True).render(
                str(index + 1), True, (8, 20, 29)
            )
            canvas.blit(number, number.get_rect(center=badge.center))
            text_x = badge.right + 18
            canvas.blit(
                heading_font.render(section.title, True, theme["text"]),
                (text_x, card.y + 17),
            )
            self._draw_wrapped(
                canvas,
                section.body,
                body_font,
                theme["menu_text"],
                pygame.Rect(text_x, card.y + 52, text_width - 18, card.height - 62),
                line_height=body_size + 6,
            )
            if visual is not None:
                visual_rect = pygame.Rect(
                    card.right - visual_width + 8,
                    card.y + 12,
                    visual_width - 22,
                    card.height - 24,
                )
                visual(canvas, visual_rect, index)
            y = card.bottom + 12
        return y

    def _draw_lead(self, canvas: pygame.Surface, width: int) -> int:
        theme = self.services.theme()
        _, _, body_size, _ = self._font_sizes()
        lead_font = self._font(body_size + 1)
        lines = self._wrap(self.page.lead, lead_font, width - 36)
        height = max(72, 30 + len(lines) * (body_size + 8))
        rect = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(canvas, theme["stats_bar"], rect, border_radius=10)
        pygame.draw.rect(canvas, self._mix(self.ACCENT, theme["grid"], 0.5), rect, 1, border_radius=10)
        self._draw_wrapped(
            canvas,
            self.page.lead,
            lead_font,
            theme["text"],
            rect.inflate(-18, -15),
            line_height=body_size + 8,
        )
        return rect.bottom + 16

    def _draw_space_time_page(self, canvas: pygame.Surface, y: int) -> int:
        width = canvas.get_width()
        gap = 18
        if width >= 980:
            visual_width = round(width * 0.47)
            visual = pygame.Rect(0, y, visual_width, 550)
            self._draw_ca_diagram(canvas, visual, 90, generations=28, labels=True)
            sections_rect = pygame.Rect(
                visual.right + gap,
                y,
                width - visual.width - gap,
                800,
            )
            bottom = self._draw_numbered_sections(
                canvas, self.page.sections, sections_rect
            )
            return max(visual.bottom, bottom)
        visual = pygame.Rect(0, y, width, 360)
        self._draw_ca_diagram(canvas, visual, 90, generations=20, labels=True)
        return self._draw_numbered_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, visual.bottom + gap, width, 900),
        )

    def _draw_timeline_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        _, heading_size, body_size, label_size = self._font_sizes()
        heading_font = self._font(heading_size, bold=True)
        body_font = self._font(body_size)
        label_font = self._font(label_size, bold=True)
        line_x = 76
        colors = (self.ACCENT, self.GOLD, self.GREEN, self.MAGENTA)
        cards: list[pygame.Rect] = []
        for index, section in enumerate(self.page.sections):
            text_width = canvas.get_width() - 210
            height = self._section_height(section, text_width) + 8
            card = pygame.Rect(132, y, canvas.get_width() - 132, height)
            cards.append(card)
            y = card.bottom + 14
        if cards:
            pygame.draw.line(
                canvas,
                theme["grid"],
                (line_x, cards[0].centery),
                (line_x, cards[-1].centery),
                5,
            )
        initials = ("VN\nUL", "SW", "MC", "NOW")
        for index, (section, card) in enumerate(zip(self.page.sections, cards)):
            color = colors[index]
            self._panel(canvas, card, border=color)
            pygame.draw.circle(canvas, theme["info_bar"], (line_x, card.centery), 36)
            pygame.draw.circle(canvas, color, (line_x, card.centery), 36, 4)
            lines = initials[index].split("\n")
            for line_index, line in enumerate(lines):
                text = label_font.render(line, True, color)
                offset = (line_index - (len(lines) - 1) / 2) * (label_size + 1)
                canvas.blit(text, text.get_rect(center=(line_x, card.centery + offset)))
            pygame.draw.line(
                canvas, color, (line_x + 37, card.centery), (card.x, card.centery), 3
            )
            canvas.blit(
                heading_font.render(section.title, True, theme["text"]),
                (card.x + 22, card.y + 17),
            )
            self._draw_wrapped(
                canvas,
                section.body,
                body_font,
                theme["menu_text"],
                pygame.Rect(card.x + 22, card.y + 53, card.width - 44, card.height - 62),
                line_height=body_size + 6,
            )
        return y

    def _draw_neighborhood(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        neighborhood: int,
        output: int,
        cell: int,
    ) -> None:
        theme = self.services.theme()
        values = ((neighborhood >> 2) & 1, (neighborhood >> 1) & 1, neighborhood & 1)
        start_x = center[0] - (cell * 3 + 8) // 2
        for index, value in enumerate(values):
            rect = pygame.Rect(start_x + index * (cell + 4), center[1] - cell, cell, cell)
            pygame.draw.rect(surface, theme["cell"] if value else theme["background"], rect, border_radius=3)
            pygame.draw.rect(surface, theme["text"], rect, 2, border_radius=3)
        pygame.draw.line(
            surface,
            self.ACCENT,
            (center[0], center[1] + 7),
            (center[0], center[1] + 25),
            3,
        )
        pygame.draw.polygon(
            surface,
            self.ACCENT,
            ((center[0], center[1] + 31), (center[0] - 6, center[1] + 21),
             (center[0] + 6, center[1] + 21)),
        )
        result = pygame.Rect(0, 0, cell, cell)
        result.center = (center[0], center[1] + 50)
        pygame.draw.rect(surface, theme["cell"] if output else theme["background"], result, border_radius=3)
        pygame.draw.rect(surface, self.GOLD, result, 3, border_radius=3)

    def _draw_rule_table_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        _, heading_size, body_size, label_size = self._font_sizes()
        rule = self.services.current_rule()
        if not 0 <= rule <= 255:
            rule = 30
        heading_font = self._font(heading_size, bold=True)
        body_font = self._font(body_size)
        label_font = self._font(label_size, bold=True)
        header = heading_font.render(
            f"Rule {rule} = {rule:08b} in binary", True, theme["text"]
        )
        canvas.blit(header, (0, y))
        y += header.get_height() + 14
        columns = 8 if canvas.get_width() >= 1000 else 4
        gap = 10
        card_width = (canvas.get_width() - gap * (columns - 1)) // columns
        card_height = 150
        for offset, neighborhood in enumerate(range(7, -1, -1)):
            row = offset // columns
            column = offset % columns
            rect = pygame.Rect(
                column * (card_width + gap),
                y + row * (card_height + gap),
                card_width,
                card_height,
            )
            self._panel(canvas, rect, border=self.ACCENT)
            output = (rule >> neighborhood) & 1
            label = label_font.render(f"{neighborhood:03b}", True, theme["text"])
            canvas.blit(label, label.get_rect(midtop=(rect.centerx, rect.y + 10)))
            self._draw_neighborhood(
                canvas,
                (rect.centerx, rect.y + 70),
                neighborhood,
                output,
                max(18, min(28, card_width // 5)),
            )
            weight = label_font.render(
                f"output {output}  |  bit {neighborhood}", True, theme["menu_text"]
            )
            canvas.blit(weight, weight.get_rect(midbottom=(rect.centerx, rect.bottom - 8)))
        rows = (8 + columns - 1) // columns
        y += rows * (card_height + gap) + 8
        equation = pygame.Rect(0, y, canvas.get_width(), 94)
        self._panel(canvas, equation, border=self.GOLD)
        equation_text = (
            "Read the outputs from neighborhood 111 down to 000. "
            f"For Rule {rule}, those bits are {rule:08b}; the same sequence interpreted "
            f"as a binary integer is {rule}."
        )
        self._draw_wrapped(
            canvas,
            equation_text,
            body_font,
            theme["text"],
            equation.inflate(-22, -17),
            line_height=body_size + 7,
        )
        y = equation.bottom + 14
        return self._draw_numbered_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, y, canvas.get_width(), 500),
        )

    def _draw_boundary_visual(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        index: int,
    ) -> None:
        theme = self.services.theme()
        pygame.draw.rect(surface, theme["stats_bar"], rect, border_radius=7)
        pygame.draw.rect(surface, theme["grid"], rect, 1, border_radius=7)
        cell = max(11, min(20, (rect.width - 34) // 11))
        count = max(7, min(11, (rect.width - 22) // cell))
        start_x = rect.centerx - count * cell // 2
        y = rect.centery - cell // 2
        values = [0] * count
        values[count // 2] = 1
        if index == 3:
            values = [1 if position % 3 == 0 else 0 for position in range(count)]
        for position, value in enumerate(values):
            box = pygame.Rect(start_x + position * cell, y, cell - 2, cell - 2)
            pygame.draw.rect(surface, theme["cell"] if value else theme["background"], box)
            pygame.draw.rect(surface, theme["grid"], box, 1)
        if index == 0:
            pygame.draw.line(surface, self.GOLD, (rect.centerx, rect.y + 10), (rect.centerx, y - 5), 3)
            pygame.draw.polygon(surface, self.GOLD, ((rect.centerx, y), (rect.centerx - 6, y - 9), (rect.centerx + 6, y - 9)))
        elif index == 1:
            pygame.draw.line(surface, self.GREEN, (start_x - 18, rect.centery), (start_x - 2, rect.centery), 3)
            pygame.draw.line(surface, self.GREEN, (start_x + count * cell + 2, rect.centery), (start_x + count * cell + 18, rect.centery), 3)
        elif index == 2:
            pygame.draw.line(surface, self.MAGENTA, (start_x - 5, y - 9), (start_x - 5, y + cell + 7), 5)
            pygame.draw.line(surface, self.MAGENTA, (start_x + count * cell + 3, y - 9), (start_x + count * cell + 3, y + cell + 7), 5)
        else:
            pygame.draw.arc(surface, self.ACCENT, rect.inflate(-16, -8), 0.15, 3.0, 3)
            pygame.draw.arc(surface, self.ACCENT, rect.inflate(-16, -8), 3.3, 6.1, 3)

    def _draw_boundaries_page(self, canvas: pygame.Surface, y: int) -> int:
        return self._draw_numbered_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, y, canvas.get_width(), 1000),
            visual=self._draw_boundary_visual,
        )

    def _draw_examples_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        _, heading_size, body_size, label_size = self._font_sizes()
        heading_font = self._font(heading_size, bold=True)
        body_font = self._font(body_size)
        label_font = self._font(label_size, bold=True)
        width = canvas.get_width()
        for rule, title, detail in RULE_EXAMPLES:
            height = 170
            card = pygame.Rect(0, y, width, height)
            self._panel(canvas, card, border=self.ACCENT)
            preview_width = max(270, min(430, round(width * 0.30)))
            preview = pygame.Rect(card.x + 12, card.y + 12, preview_width, card.height - 24)
            if rule == 184:
                seed = tuple(1 if (index * 7 + 3) % 11 < 5 else 0 for index in range(51))
                self._draw_ca_diagram(
                    canvas, preview, rule, generations=18, seed=seed, wrap=True
                )
            else:
                self._draw_ca_diagram(canvas, preview, rule, generations=18)
            text_x = preview.right + 22
            button_width = 154
            text_width = card.right - text_x - button_width - 34
            badge = pygame.Rect(text_x, card.y + 17, 78, 34)
            pygame.draw.rect(canvas, self.ACCENT, badge, border_radius=6)
            badge_text = heading_font.render(str(rule), True, (8, 20, 29))
            canvas.blit(badge_text, badge_text.get_rect(center=badge.center))
            canvas.blit(
                heading_font.render(title, True, theme["text"]),
                (badge.right + 14, card.y + 18),
            )
            self._draw_wrapped(
                canvas,
                detail,
                body_font,
                theme["menu_text"],
                pygame.Rect(text_x, card.y + 65, text_width, card.height - 78),
                line_height=body_size + 6,
            )
            button = pygame.Rect(card.right - button_width - 16, card.centery - 22, button_width, 44)
            pygame.draw.rect(canvas, theme["button_hover"], button, border_radius=7)
            pygame.draw.rect(canvas, self.ACCENT, button, 2, border_radius=7)
            button_text = label_font.render(f"LOAD RULE {rule}", True, theme["button_text"])
            canvas.blit(button_text, button_text.get_rect(center=button.center))
            self._local_interactions.append(("rule", str(rule), button.copy()))
            y = card.bottom + 14
        return y

    def _draw_family_visual(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        index: int,
    ) -> None:
        theme = self.services.theme()
        pygame.draw.rect(surface, theme["stats_bar"], rect, border_radius=7)
        pygame.draw.rect(surface, theme["grid"], rect, 1, border_radius=7)
        center_y = rect.centery
        if index == 0:
            colors = (theme["background"], self.ACCENT, self.GOLD, self.MAGENTA)
            size = min(32, (rect.width - 24) // 4)
            start = rect.centerx - (size * 4 + 18) // 2
            for value, color in enumerate(colors):
                box = pygame.Rect(start + value * (size + 6), center_y - size // 2, size, size)
                pygame.draw.rect(surface, color, box, border_radius=4)
                pygame.draw.rect(surface, theme["text"], box, 1, border_radius=4)
        elif index == 1:
            size = min(27, (rect.width - 30) // 7)
            start = rect.centerx - size * 5 // 2
            for value in range(5):
                box = pygame.Rect(start + value * size, center_y - size // 2, size - 2, size - 2)
                pygame.draw.rect(surface, self.ACCENT if value == 2 else theme["button_hover"], box)
                pygame.draw.rect(surface, theme["grid"], box, 1)
            pygame.draw.line(surface, self.GOLD, (start, center_y + size), (start + size * 5, center_y + size), 3)
        elif index == 2:
            for row in range(2):
                y = rect.y + 16 + row * 38
                for column in range(7):
                    box = pygame.Rect(rect.centerx - 74 + column * 22, y, 18, 18)
                    active = (column + row) % 3 == 0
                    pygame.draw.rect(surface, self.GREEN if active else theme["background"], box)
                    pygame.draw.rect(surface, theme["grid"], box, 1)
            pygame.draw.line(surface, self.GOLD, (rect.x + 15, rect.centery), (rect.right - 15, rect.centery), 2)
        else:
            labels = ("SEED", "RUN", "MEASURE", "EXPORT")
            label_font = self._font(max(12, self._font_sizes()[3] - 1), bold=True)
            gap = (rect.width - 20) // len(labels)
            for position, label in enumerate(labels):
                x = rect.x + 10 + gap * position + gap // 2
                pygame.draw.circle(surface, self.ACCENT, (x, center_y - 7), 12, 3)
                text = label_font.render(label, True, theme["menu_text"])
                surface.blit(text, text.get_rect(midtop=(x, center_y + 12)))
                if position + 1 < len(labels):
                    pygame.draw.line(surface, theme["grid"], (x + 14, center_y - 7), (x + gap - 14, center_y - 7), 2)

    def _draw_families_page(self, canvas: pygame.Surface, y: int) -> int:
        return self._draw_numbered_sections(
            canvas,
            self.page.sections,
            pygame.Rect(0, y, canvas.get_width(), 1000),
            visual=self._draw_family_visual,
        )

    def _draw_sources_page(self, canvas: pygame.Surface, y: int) -> int:
        theme = self.services.theme()
        _, heading_size, body_size, label_size = self._font_sizes()
        heading_font = self._font(heading_size, bold=True)
        body_font = self._font(body_size)
        label_font = self._font(label_size, bold=True)
        line_x = 39
        card_x = 86
        card_width = canvas.get_width() - card_x
        source_cards: list[pygame.Rect] = []
        for source in TUTORIAL_SOURCES:
            lines = self._wrap(source.detail, body_font, card_width - 230)
            height = max(100, 58 + len(lines) * (body_size + 5))
            card = pygame.Rect(card_x, y, card_width, height)
            source_cards.append(card)
            y = card.bottom + 12
        if source_cards:
            pygame.draw.line(
                canvas,
                theme["grid"],
                (line_x, source_cards[0].centery),
                (line_x, source_cards[-1].centery),
                4,
            )
        for index, (source, card) in enumerate(zip(TUTORIAL_SOURCES, source_cards), start=1):
            self._panel(canvas, card, border=self.ACCENT)
            pygame.draw.circle(canvas, theme["info_bar"], (line_x, card.centery), 25)
            pygame.draw.circle(canvas, self.ACCENT, (line_x, card.centery), 25, 3)
            number = heading_font.render(str(index), True, self.ACCENT)
            canvas.blit(number, number.get_rect(center=(line_x, card.centery)))
            category = label_font.render(source.category, True, self.GOLD)
            canvas.blit(category, (card.x + 18, card.y + 12))
            title = heading_font.render(source.title, True, theme["text"])
            canvas.blit(title, (card.x + 18, card.y + 39))
            button = pygame.Rect(card.right - 164, card.centery - 22, 146, 44)
            self._draw_wrapped(
                canvas,
                source.detail,
                body_font,
                theme["menu_text"],
                pygame.Rect(card.x + 18, card.y + 72, card.width - 210, card.height - 78),
                line_height=body_size + 5,
            )
            pygame.draw.rect(canvas, theme["button_hover"], button, border_radius=7)
            pygame.draw.rect(canvas, self.ACCENT, button, 2, border_radius=7)
            label = label_font.render("OPEN SOURCE", True, theme["button_text"])
            canvas.blit(label, label.get_rect(center=button.center))
            self._local_interactions.append(("url", source.url, button.copy()))
        return y

    def _draw_page_canvas(self, width: int) -> tuple[pygame.Surface, int]:
        canvas = pygame.Surface((width, 2400), pygame.SRCALPHA)
        self._local_interactions = []
        y = self._draw_lead(canvas, width)
        if self.page.kind == "space_time":
            y = self._draw_space_time_page(canvas, y)
        elif self.page.kind == "timeline":
            y = self._draw_timeline_page(canvas, y)
        elif self.page.kind == "rule_table":
            y = self._draw_rule_table_page(canvas, y)
        elif self.page.kind == "boundaries":
            y = self._draw_boundaries_page(canvas, y)
        elif self.page.kind == "examples":
            y = self._draw_examples_page(canvas, y)
        elif self.page.kind == "families":
            y = self._draw_families_page(canvas, y)
        elif self.page.kind == "sources":
            y = self._draw_sources_page(canvas, y)
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
        _, _, _, label_size = self._font_sizes()
        fill = theme["button_hover"] if enabled else theme["button"]
        pygame.draw.rect(screen, fill, rect, border_radius=7)
        border = self.ACCENT if primary and enabled else theme["grid"]
        pygame.draw.rect(screen, border, rect, 2 if primary else 1, border_radius=7)
        color = theme["button_text"] if enabled else theme["menu_text"]
        text = self._font(label_size, bold=True).render(label, True, color)
        screen.blit(text, text.get_rect(center=rect.center))

    def draw(self) -> None:
        if not self.active:
            return
        screen = self.services.screen()
        width, height = self.services.window_size()
        theme = self.services.theme()
        title_size, _, _, label_size = self._font_sizes()
        dimmer = pygame.Surface((width, height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 232))
        screen.blit(dimmer, (0, 0))

        modal, viewport, close, back, next_button = self.geometry()
        pygame.draw.rect(screen, theme["info_bar"], modal, border_radius=12)
        pygame.draw.rect(screen, theme["text"], modal, 2, border_radius=12)

        kicker_font = self._font(label_size, bold=True)
        title_font = self._font(title_size, bold=True)
        kicker = kicker_font.render(self.page.kicker, True, self.ACCENT)
        screen.blit(kicker, (modal.x + 26, modal.y + 18))
        title = title_font.render(self.page.title, True, theme["text"])
        screen.blit(title, (modal.x + 25, modal.y + 45))
        progress = kicker_font.render(
            f"PAGE {self.page_index + 1} OF {self.page_count}",
            True,
            theme["menu_text"],
        )
        screen.blit(progress, progress.get_rect(topright=(modal.right - 72, modal.y + 23)))
        pygame.draw.rect(screen, theme["button"], close, border_radius=6)
        pygame.draw.rect(screen, theme["grid"], close, 1, border_radius=6)
        close_text = self._font(label_size, bold=True).render("X", True, theme["button_text"])
        screen.blit(close_text, close_text.get_rect(center=close.center))

        segment_gap = 6
        segment_width = (modal.width - 52 - segment_gap * (self.page_count - 1)) // self.page_count
        segment_y = viewport.y - 14
        for index in range(self.page_count):
            segment = pygame.Rect(
                modal.x + 26 + index * (segment_width + segment_gap),
                segment_y,
                segment_width,
                5,
            )
            pygame.draw.rect(
                screen,
                self.ACCENT if index <= self.page_index else theme["grid"],
                segment,
                border_radius=3,
            )

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
                self.ACCENT,
                pygame.Rect(track.x, thumb_y, track.width, thumb_height),
                border_radius=2,
            )

        self._draw_navigation_button(
            back,
            "<  PREVIOUS",
            enabled=self.page_index > 0,
        )
        final_page = self.page_index == self.page_count - 1
        self._draw_navigation_button(
            next_button,
            "FINISH" if final_page else "NEXT  >",
            enabled=True,
            primary=True,
        )
        footer = self._font(label_size).render(
            "F2 or Esc closes   |   Left / Right changes lesson   |   Wheel scrolls",
            True,
            theme["menu_text"],
        )
        screen.blit(footer, footer.get_rect(center=(modal.centerx, back.centery)))
