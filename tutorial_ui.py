"""Guided, source-backed tutorials for the cellular automata workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import pygame


SEP_CELLULAR_AUTOMATA = "https://plato.stanford.edu/entries/cellular-automata/"
WOLFRAM_1983 = (
    "https://doi.org/10.1103/RevModPhys.55.601"
)
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
    """One compact explanatory card on a tutorial page."""

    title: str
    body: str


@dataclass(frozen=True)
class TutorialPage:
    """Text and optional interactive content for a tutorial step."""

    kicker: str
    title: str
    lead: str
    sections: tuple[TutorialSection, ...] = ()
    kind: str = "sections"


@dataclass(frozen=True)
class TutorialSource:
    """A readable citation paired with an external destination."""

    title: str
    detail: str
    url: str


@dataclass(frozen=True)
class TutorialServices:
    """Application resources and callbacks used by the 1D tutorial."""

    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    content_width: Callable[[], int]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    current_rule: Callable[[], int]
    apply_canonical_rule: Callable[[int], None]
    open_url: Callable[[str], bool]
    pause: Callable[[], None]
    mark_seen: Callable[[], None]
    set_status: Callable[[str, float], None]


ONE_D_TUTORIAL_PAGES: tuple[TutorialPage, ...] = (
    TutorialPage(
        "START HERE",
        "A line that becomes a history",
        (
            "A one-dimensional cellular automaton is a row of cells. Every cell "
            "updates at the same discrete instant from a local rule; stacking the "
            "new rows downward turns time into a visible space-time diagram."
        ),
        (
            TutorialSection(
                "Space is horizontal",
                "Each square is one position. In the Elementary family a square is "
                "either state 0 (background) or state 1 (active).",
            ),
            TutorialSection(
                "Time flows downward",
                "The top row is the seed at generation 0. Every row below it is the "
                "next simultaneous update; it is history, not another spatial axis.",
            ),
            TutorialSection(
                "Local rule, global pattern",
                "No cell sees the whole line. Large triangles, periodic textures and "
                "apparently random structures emerge from repeated local decisions.",
            ),
            TutorialSection(
                "Try the editor",
                "Left click writes the selected state, right click erases, Space runs, "
                "and N advances exactly one generation while paused.",
            ),
        ),
    ),
    TutorialPage(
        "HISTORY",
        "Who developed cellular automata?",
        (
            "There is no single inventor of every 1D rule. Cellular automata grew "
            "from several research programs; the Elementary rules are one especially "
            "simple and influential family."
        ),
        (
            TutorialSection(
                "1940s-1950s: von Neumann and Ulam",
                "John von Neumann studied logical self-reproduction. Following ideas "
                "from Stanislaw Ulam about discrete lattices, he developed a formal "
                "cellular-automaton model with many states in two dimensions.",
            ),
            TutorialSection(
                "1980s: Stephen Wolfram",
                "Wolfram systematically investigated simple one-dimensional cellular "
                "automata, introduced the now-standard rule numbering and proposed a "
                "four-class qualitative taxonomy of long-term behavior.",
            ),
            TutorialSection(
                "2004: Matthew Cook",
                "Cook published a proof that Rule 110 can perform universal "
                "computation with a specially encoded periodic background. The claim "
                "is stronger than merely producing a complicated single-cell pattern.",
            ),
            TutorialSection(
                "What the history does not imply",
                "A cellular automaton is an abstract dynamical system. Visual "
                "similarity to nature is not by itself evidence that the rule models a "
                "particular physical or biological process.",
            ),
        ),
    ),
    TutorialPage(
        "THE RULE",
        "Decode a Wolfram rule number",
        (
            "An Elementary cell reads three bits: left, itself and right. There are "
            "eight possible neighborhoods. The eight output bits, ordered from 111 "
            "to 000, form a binary number between 0 and 255."
        ),
        (
            TutorialSection(
                "Why exactly 256 rules?",
                "Three binary inputs give 2^3 = 8 neighborhoods. Choosing a binary "
                "output independently for each neighborhood gives 2^8 = 256 rules.",
            ),
            TutorialSection(
                "Read one update",
                "Find the current left-center-right triplet in the table below. Its "
                "output becomes the center cell in the next row. All centers update "
                "from the old row, never from partially updated neighbors.",
            ),
        ),
        kind="rule_table",
    ),
    TutorialPage(
        "EXPERIMENT DESIGN",
        "Seeds and boundaries are part of the question",
        (
            "A rule does not define one picture. The observed diagram also depends on "
            "the initial row, boundary model, width and number of generations. Record "
            "these controls whenever you compare experiments."
        ),
        (
            TutorialSection(
                "Canonical single-cell view",
                "Use a centered state-1 cell on a state-0 background. This is the "
                "familiar presentation for rules such as 30 and 90, but it samples "
                "only one initial condition.",
            ),
            TutorialSection(
                "Infinite background",
                "The represented row may expand as activity reaches an edge. Outside "
                "cells evolve uniformly, approximating an unbounded line without "
                "silently wrapping the left side onto the right.",
            ),
            TutorialSection(
                "Fixed zero",
                "Cells beyond the finite row are forced to state 0. This is useful for "
                "a bounded experiment, but edge interactions can change the result.",
            ),
            TutorialSection(
                "Wrap",
                "The first and last cells are neighbors, making a ring. This preserves "
                "a fixed population of sites and is often useful with random seeds.",
            ),
        ),
    ),
    TutorialPage(
        "LANDMARK EXPERIMENTS",
        "Four rules worth running",
        (
            "Use the buttons to load a reproducible Elementary experiment: centered "
            "single-cell seed, state-0 infinite background and canonical rule reset. "
            "The tutorial closes so you can immediately press Space."
        ),
        kind="examples",
    ),
    TutorialPage(
        "BEYOND ELEMENTARY",
        "The 1D workspace is a small laboratory",
        (
            "Elementary rules are the beginning, not the definition of 1D cellular "
            "automata. Change one assumption at a time and compare trajectories under "
            "the same seed and measurement protocol."
        ),
        (
            TutorialSection(
                "Totalistic and multi-state",
                "A totalistic rule depends on a neighborhood sum. Multi-state systems "
                "use alphabets larger than {0,1}, allowing richer local memory.",
            ),
            TutorialSection(
                "Larger radius",
                "Radius 2 or 3 lets a cell consult more distant positions. The rule "
                "table grows rapidly, so code values can become very large.",
            ),
            TutorialSection(
                "Higher-order and reversible",
                "Higher-order rules also use an earlier time slice. Reversible "
                "constructions preserve enough information to reconstruct the past.",
            ),
            TutorialSection(
                "A reproducible workflow",
                "Save a 1D profile, compare two rules side by side, inspect entropy and "
                "change rate, then export the diagram, CSV metrics and experiment JSON.",
            ),
        ),
    ),
    TutorialPage(
        "SOURCES & NEXT STEPS",
        "Continue with primary and scholarly references",
        (
            "These links separate historical background, formal definitions, original "
            "research and later proofs. Clicking Open Source launches the page in your "
            "default browser."
        ),
        kind="sources",
    ),
)


TUTORIAL_SOURCES: tuple[TutorialSource, ...] = (
    TutorialSource(
        "Stanford Encyclopedia of Philosophy",
        "History, formal CA definition, Wolfram classes and bibliography.",
        SEP_CELLULAR_AUTOMATA,
    ),
    TutorialSource(
        "Wolfram (1983), Statistical Mechanics of Cellular Automata",
        "Original Reviews of Modern Physics paper on simple 1D automata.",
        WOLFRAM_1983,
    ),
    TutorialSource(
        "Wolfram MathWorld: Elementary Cellular Automaton",
        "Rule numbering, transition tables and the 256-rule catalogue.",
        MATHWORLD_ELEMENTARY_CA,
    ),
    TutorialSource(
        "Wolfram: Four Classes of Behavior",
        "Author's presentation of the qualitative four-class taxonomy.",
        WOLFRAM_CLASSES,
    ),
    TutorialSource(
        "Cook (2004), Universality in Elementary Cellular Automata",
        "Published proof of Rule 110 computational universality.",
        COOK_RULE_110,
    ),
    TutorialSource(
        "Nishinari (2002), Cellular Automaton Models of Traffic Flow",
        "Scholarly context for Rule 184 as a prototype traffic CA.",
        RULE_184_TRAFFIC,
    ),
)


RULE_EXAMPLES: tuple[tuple[int, str, str], ...] = (
    (
        30,
        "Rule 30 - asymmetric complexity",
        "A single cell produces a regular left edge and irregular-looking interior. "
        "A classic example of complex output from a tiny deterministic rule.",
    ),
    (
        90,
        "Rule 90 - additive fractal",
        "The update is left XOR right. A single cell generates the Sierpinski-triangle "
        "structure and makes self-similarity especially easy to inspect.",
    ),
    (
        110,
        "Rule 110 - computational universality",
        "Supports interacting localized structures. Cook's universality proof uses "
        "carefully encoded periodic backgrounds, not merely a lone center cell.",
    ),
    (
        184,
        "Rule 184 - transport and traffic",
        "With wrap boundary and a suitable random row, state-1 cells can be interpreted "
        "as vehicles moving through state-0 gaps. Try changing the density.",
    ),
)


class OneDimensionalTutorial:
    """Responsive, keyboard-navigable tutorial for the 1D workspace."""

    def __init__(self, services: TutorialServices) -> None:
        self.services = services
        self.active = False
        self.page_index = 0
        self.scroll = 0
        self.content_height = 0
        self._interactions: list[tuple[str, str, pygame.Rect]] = []

    @property
    def page_count(self) -> int:
        return len(ONE_D_TUTORIAL_PAGES)

    @property
    def page(self) -> TutorialPage:
        return ONE_D_TUTORIAL_PAGES[self.page_index]

    def open(self, *, automatic: bool = False) -> None:
        """Pause the lab and open at the beginning unless resuming manually."""
        self.services.pause()
        self.active = True
        if automatic:
            self.page_index = 0
            self.services.mark_seen()
        self.scroll = 0

    def close(self) -> None:
        self.active = False
        self._interactions.clear()

    def geometry(
        self,
    ) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        width, height = self.services.window_size()
        content_width = max(1, self.services.content_width())
        modal = pygame.Rect(
            0,
            0,
            max(420, min(980, content_width - 28)),
            max(480, min(680, height - 28)),
        )
        modal.center = (content_width // 2, height // 2)
        close = pygame.Rect(modal.right - 43, modal.y + 14, 28, 26)
        viewport = pygame.Rect(
            modal.x + 20,
            modal.y + 104,
            modal.width - 40,
            modal.height - 166,
        )
        back = pygame.Rect(modal.x + 20, modal.bottom - 48, 118, 32)
        next_button = pygame.Rect(modal.right - 156, back.y, 136, back.height)
        return modal, viewport, close, back, next_button

    def _maximum_scroll(self, viewport: pygame.Rect) -> int:
        return max(0, self.content_height - viewport.height)

    def _move(self, delta: int) -> None:
        target = self.page_index + delta
        if target >= self.page_count:
            self.services.mark_seen()
            self.close()
            self.services.set_status(
                "1D tutorial complete. Choose a landmark rule and begin an experiment.",
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
                self.scroll = max(0, self.scroll - 42)
            elif event.key == pygame.K_DOWN:
                _, viewport, _, _, _ = self.geometry()
                self.scroll = min(self._maximum_scroll(viewport), self.scroll + 42)
            return True
        if event.type == pygame.MOUSEWHEEL:
            _, viewport, _, _, _ = self.geometry()
            self.scroll = max(
                0,
                min(
                    self._maximum_scroll(viewport),
                    self.scroll - event.y * 46,
                ),
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
                if rect.collidepoint(event.pos):
                    if action == "rule":
                        self.services.apply_canonical_rule(int(payload))
                        self.close()
                    elif action == "url":
                        opened = self.services.open_url(payload)
                        message = (
                            "Source opened in the default browser."
                            if opened
                            else "The source could not be opened; see its URL in README."
                        )
                        self.services.set_status(message, 4.0)
                    return True
            return True
        return True

    @staticmethod
    def _wrap(
        text: str,
        font: pygame.font.Font,
        width: int,
    ) -> list[str]:
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

    def _draw_section_card(
        self,
        canvas: pygame.Surface,
        rect: pygame.Rect,
        section: TutorialSection,
    ) -> int:
        theme = self.services.theme()
        pygame.draw.rect(canvas, theme["button"], rect, border_radius=7)
        pygame.draw.rect(canvas, theme["grid"], rect, 1, border_radius=7)
        canvas.blit(
            self.services.small_font().render(section.title, True, theme["text"]),
            (rect.x + 13, rect.y + 11),
        )
        body_bottom = self._draw_wrapped(
            canvas,
            section.body,
            self.services.tiny_font(),
            theme["menu_text"],
            pygame.Rect(rect.x + 13, rect.y + 39, rect.width - 26, rect.height - 48),
            line_height=17,
        )
        return body_bottom

    def _section_height(self, section: TutorialSection, width: int) -> int:
        lines = self._wrap(section.body, self.services.tiny_font(), width - 26)
        return max(112, 52 + len(lines) * 17)

    def _draw_sections(
        self,
        canvas: pygame.Surface,
        sections: Sequence[TutorialSection],
        start_y: int,
    ) -> int:
        width = canvas.get_width()
        gap = 12
        columns = 2 if width >= 690 else 1
        card_width = (width - gap * (columns - 1)) // columns
        y = start_y
        for row_start in range(0, len(sections), columns):
            row = sections[row_start : row_start + columns]
            height = max(
                self._section_height(section, card_width) for section in row
            )
            for column, section in enumerate(row):
                rect = pygame.Rect(
                    column * (card_width + gap),
                    y,
                    card_width,
                    height,
                )
                self._draw_section_card(canvas, rect, section)
            y += height + gap
        return y

    def _draw_rule_table(self, canvas: pygame.Surface, start_y: int) -> int:
        theme = self.services.theme()
        rule = self.services.current_rule()
        if not 0 <= rule <= 255:
            rule = 30
        title = self.services.small_font().render(
            f"Current example: Rule {rule} = {rule:08b} (binary)",
            True,
            theme["text"],
        )
        canvas.blit(title, (0, start_y))
        y = start_y + 31
        gap = 5
        cell_width = max(52, (canvas.get_width() - gap * 7) // 8)
        total_width = cell_width * 8 + gap * 7
        x = max(0, (canvas.get_width() - total_width) // 2)
        for offset, neighborhood in enumerate(range(7, -1, -1)):
            output = (rule >> neighborhood) & 1
            card = pygame.Rect(x + offset * (cell_width + gap), y, cell_width, 70)
            pygame.draw.rect(canvas, theme["button"], card, border_radius=5)
            pygame.draw.rect(canvas, theme["grid"], card, 1, border_radius=5)
            triplet = f"{neighborhood:03b}"
            top = self.services.tiny_font().render(
                triplet,
                True,
                theme["menu_text"],
            )
            canvas.blit(top, top.get_rect(center=(card.centerx, card.y + 19)))
            pygame.draw.line(
                canvas,
                theme["grid"],
                (card.x + 7, card.y + 35),
                (card.right - 7, card.y + 35),
            )
            result_color = theme["cell"] if output else theme["background"]
            output_box = pygame.Rect(0, 0, 16, 16)
            output_box.center = (card.centerx, card.y + 51)
            pygame.draw.rect(canvas, result_color, output_box, border_radius=2)
            pygame.draw.rect(canvas, theme["text"], output_box, 1, border_radius=2)
        caption = (
            "Read outputs left-to-right as 111, 110, 101, 100, 011, 010, "
            "001, 000. The same bits read as a binary integer name the rule."
        )
        return self._draw_wrapped(
            canvas,
            caption,
            self.services.tiny_font(),
            theme["menu_text"],
            pygame.Rect(0, y + 82, canvas.get_width(), 70),
            line_height=17,
        ) + 10

    def _draw_examples(self, canvas: pygame.Surface, start_y: int) -> int:
        theme = self.services.theme()
        y = start_y
        gap = 10
        for rule, title, detail in RULE_EXAMPLES:
            lines = self._wrap(detail, self.services.tiny_font(), canvas.get_width() - 184)
            height = max(92, 48 + len(lines) * 17)
            rect = pygame.Rect(0, y, canvas.get_width(), height)
            pygame.draw.rect(canvas, theme["button"], rect, border_radius=7)
            pygame.draw.rect(canvas, theme["grid"], rect, 1, border_radius=7)
            badge = pygame.Rect(rect.x + 12, rect.y + 12, 62, 30)
            pygame.draw.rect(canvas, (75, 175, 235), badge, border_radius=5)
            badge_text = self.services.small_font().render(
                str(rule),
                True,
                (10, 20, 28),
            )
            canvas.blit(badge_text, badge_text.get_rect(center=badge.center))
            canvas.blit(
                self.services.small_font().render(title, True, theme["text"]),
                (rect.x + 86, rect.y + 11),
            )
            self._draw_wrapped(
                canvas,
                detail,
                self.services.tiny_font(),
                theme["menu_text"],
                pygame.Rect(rect.x + 86, rect.y + 39, rect.width - 250, rect.height - 45),
                line_height=17,
            )
            button = pygame.Rect(rect.right - 150, rect.centery - 16, 136, 32)
            pygame.draw.rect(canvas, theme["button_hover"], button, border_radius=5)
            pygame.draw.rect(canvas, (75, 175, 235), button, 2, border_radius=5)
            button_text = self.services.tiny_font().render(
                f"Load Rule {rule}",
                True,
                theme["button_text"],
            )
            canvas.blit(button_text, button_text.get_rect(center=button.center))
            self._local_interactions.append(("rule", str(rule), button.copy()))
            y += height + gap
        return y

    def _draw_sources(self, canvas: pygame.Surface, start_y: int) -> int:
        theme = self.services.theme()
        y = start_y
        for source in TUTORIAL_SOURCES:
            detail_lines = self._wrap(
                source.detail,
                self.services.tiny_font(),
                canvas.get_width() - 194,
            )
            height = max(82, 47 + len(detail_lines) * 17)
            rect = pygame.Rect(0, y, canvas.get_width(), height)
            pygame.draw.rect(canvas, theme["button"], rect, border_radius=7)
            pygame.draw.rect(canvas, theme["grid"], rect, 1, border_radius=7)
            canvas.blit(
                self.services.small_font().render(
                    source.title,
                    True,
                    theme["text"],
                ),
                (rect.x + 13, rect.y + 10),
            )
            self._draw_wrapped(
                canvas,
                source.detail,
                self.services.tiny_font(),
                theme["menu_text"],
                pygame.Rect(rect.x + 13, rect.y + 37, rect.width - 190, rect.height - 42),
                line_height=17,
            )
            button = pygame.Rect(rect.right - 158, rect.centery - 16, 144, 32)
            pygame.draw.rect(canvas, theme["button_hover"], button, border_radius=5)
            pygame.draw.rect(canvas, (75, 175, 235), button, 2, border_radius=5)
            label = self.services.tiny_font().render(
                "Open Source",
                True,
                theme["button_text"],
            )
            canvas.blit(label, label.get_rect(center=button.center))
            self._local_interactions.append(("url", source.url, button.copy()))
            y += height + 9
        return y

    def _draw_page_canvas(self, width: int) -> tuple[pygame.Surface, int]:
        theme = self.services.theme()
        canvas = pygame.Surface((width, 1400), pygame.SRCALPHA)
        self._local_interactions: list[tuple[str, str, pygame.Rect]] = []
        y = 0
        y = self._draw_wrapped(
            canvas,
            self.page.lead,
            self.services.small_font(),
            theme["menu_text"],
            pygame.Rect(0, y, width, 160),
            line_height=21,
        ) + 15

        if self.page.sections:
            y = self._draw_sections(canvas, self.page.sections, y)
        if self.page.kind == "rule_table":
            y = self._draw_rule_table(canvas, y + 4)
        elif self.page.kind == "examples":
            y = self._draw_examples(canvas, y)
        elif self.page.kind == "sources":
            y = self._draw_sources(canvas, y)
        return canvas, y

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
        fill = theme["button_hover"] if enabled else theme["button"]
        pygame.draw.rect(screen, fill, rect, border_radius=5)
        border = (75, 175, 235) if primary and enabled else theme["grid"]
        pygame.draw.rect(screen, border, rect, 2 if primary else 1, border_radius=5)
        color = theme["button_text"] if enabled else theme["menu_text"]
        text = self.services.tiny_font().render(label, True, color)
        screen.blit(text, text.get_rect(center=rect.center))

    def draw(self) -> None:
        if not self.active:
            return
        screen = self.services.screen()
        width, height = self.services.window_size()
        theme = self.services.theme()
        dimmer = pygame.Surface((width, height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 210))
        screen.blit(dimmer, (0, 0))

        modal, viewport, close, back, next_button = self.geometry()
        shadow = pygame.Surface((modal.width + 14, modal.height + 14), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 105))
        screen.blit(shadow, (modal.x + 6, modal.y + 6))
        pygame.draw.rect(screen, theme["info_bar"], modal, border_radius=12)
        pygame.draw.rect(screen, theme["text"], modal, 2, border_radius=12)

        accent = (75, 175, 235)
        kicker = self.services.tiny_font().render(self.page.kicker, True, accent)
        screen.blit(kicker, (modal.x + 21, modal.y + 15))
        title = self.services.large_font().render(self.page.title, True, theme["text"])
        screen.blit(title, (modal.x + 20, modal.y + 39))
        progress = self.services.tiny_font().render(
            f"1D Tutorial  |  {self.page_index + 1} of {self.page_count}",
            True,
            theme["menu_text"],
        )
        screen.blit(progress, (modal.x + 21, modal.y + 75))
        pygame.draw.rect(screen, theme["button"], close, border_radius=5)
        pygame.draw.rect(screen, theme["grid"], close, 1, border_radius=5)
        close_text = self.services.small_font().render("x", True, theme["button_text"])
        screen.blit(close_text, close_text.get_rect(center=close.center))

        pygame.draw.rect(screen, theme["stats_bar"], viewport, border_radius=7)
        canvas, content_height = self._draw_page_canvas(viewport.width - 20)
        self.content_height = max(content_height, viewport.height)
        self.scroll = min(self.scroll, self._maximum_scroll(viewport))
        source_rect = pygame.Rect(
            0,
            self.scroll,
            canvas.get_width(),
            min(viewport.height - 16, canvas.height - self.scroll),
        )
        target = (viewport.x + 10, viewport.y + 8)
        old_clip = screen.get_clip()
        screen.set_clip(viewport.inflate(-2, -2))
        screen.blit(canvas, target, source_rect)
        screen.set_clip(old_clip)

        self._interactions = []
        for action, payload, local in self._local_interactions:
            translated = local.move(target[0], target[1] - self.scroll)
            if viewport.colliderect(translated):
                self._interactions.append((action, payload, translated))

        if self._maximum_scroll(viewport):
            track = pygame.Rect(viewport.right - 6, viewport.y + 8, 3, viewport.height - 16)
            pygame.draw.rect(screen, theme["grid"], track, border_radius=2)
            ratio = viewport.height / self.content_height
            thumb_height = max(24, int(track.height * ratio))
            progress_ratio = self.scroll / self._maximum_scroll(viewport)
            thumb_y = track.y + int((track.height - thumb_height) * progress_ratio)
            pygame.draw.rect(
                screen,
                accent,
                pygame.Rect(track.x, thumb_y, track.width, thumb_height),
                border_radius=2,
            )

        self._draw_navigation_button(
            back,
            "<  Previous",
            enabled=self.page_index > 0,
        )
        final_page = self.page_index == self.page_count - 1
        self._draw_navigation_button(
            next_button,
            "Finish" if final_page else "Next  >",
            enabled=True,
            primary=True,
        )
        footer = self.services.tiny_font().render(
            "F2 or Esc closes  |  Left/Right changes page  |  Wheel scrolls",
            True,
            theme["menu_text"],
        )
        screen.blit(
            footer,
            footer.get_rect(center=(modal.centerx, modal.bottom - 32)),
        )
