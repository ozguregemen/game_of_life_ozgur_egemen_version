"""Educational, contextual Pygame studio for user-authored CA rules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

import pygame

from custom_rules import CustomRuleDefinition, get_custom_rules


@dataclass(frozen=True)
class RuleStudioTemplate:
    """One documented starting expression shown in the guided builder."""

    title: str
    expression: str
    description: str


@dataclass(frozen=True)
class RuleStudioLayout:
    """Clickable geometry for the current studio view."""

    modal: pygame.Rect
    close: pygame.Rect
    learn_tab: pygame.Rect
    library_tab: pygame.Rect
    content: pygame.Rect
    create: pygame.Rect
    templates: tuple[tuple[RuleStudioTemplate, pygame.Rect], ...]
    rows: tuple[tuple[CustomRuleDefinition, pygame.Rect, pygame.Rect], ...]
    capacity: int


@dataclass(frozen=True)
class RuleStudioServices:
    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    theme: Callable[[], Mapping[str, Any]]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    active_dimension: Callable[[], str]
    editor_kind: Callable[[], str]
    context_label: Callable[[], str]
    current_rule_key: Callable[[], str | None]
    templates: Callable[[], tuple[RuleStudioTemplate, ...]]
    create_rule: Callable[[str | None], CustomRuleDefinition | None]
    apply_rule: Callable[[CustomRuleDefinition], None]
    delete_rule: Callable[[CustomRuleDefinition], bool]
    pause: Callable[[], None]
    set_status: Callable[[str, float], None]
    feedback_text: Callable[[], str]


class CustomRuleStudio:
    """Full-window rule lesson, template builder, and saved-rule catalog."""

    ROW_HEIGHT = 70
    LEARN_VIEW = "learn"
    LIBRARY_VIEW = "library"

    def __init__(self, services: RuleStudioServices) -> None:
        self.services = services
        self.active = False
        self.scroll = 0
        self.view = self.LEARN_VIEW
        self.message = ""

    @property
    def dimension(self) -> str:
        return self.services.active_dimension()

    @property
    def accent(self) -> tuple[int, int, int]:
        return {
            "1d": (70, 190, 235),
            "2d": (80, 220, 105),
            "3d": (190, 110, 245),
        }[self.dimension]

    def rules(self) -> tuple[CustomRuleDefinition, ...]:
        return get_custom_rules(self.dimension)

    def open(self) -> None:
        self.services.pause()
        self.active = True
        self.scroll = 0
        self.view = self.LEARN_VIEW
        self.message = ""

    def close(self) -> None:
        self.active = False

    def geometry(self) -> RuleStudioLayout:
        width, height = self.services.window_size()
        modal = pygame.Rect(18, 38, max(520, width - 36), max(440, height - 76))
        close = pygame.Rect(modal.right - 48, modal.y + 16, 32, 32)
        tab_y = modal.y + 82
        tab_gap = 10
        tab_width = (modal.width - 48 - tab_gap) // 2
        learn_tab = pygame.Rect(modal.x + 24, tab_y, tab_width, 40)
        library_tab = pygame.Rect(learn_tab.right + tab_gap, tab_y, tab_width, 40)
        create = pygame.Rect(
            modal.x + 24,
            modal.bottom - 92,
            modal.width - 48,
            42,
        )
        content = pygame.Rect(
            modal.x + 24,
            learn_tab.bottom + 12,
            modal.width - 48,
            max(100, create.top - learn_tab.bottom - 24),
        )

        template_layout: list[tuple[RuleStudioTemplate, pygame.Rect]] = []
        if self.view == self.LEARN_VIEW:
            templates = self.services.templates()[:4]
            right_x = content.x + content.width // 2 + 10
            right_width = content.right - right_x
            heading_height = 40
            card_gap = 10
            card_width = max(120, (right_width - card_gap) // 2)
            card_height = max(
                78,
                (content.height - heading_height - card_gap) // 2,
            )
            for index, template in enumerate(templates):
                column = index % 2
                row = index // 2
                rect = pygame.Rect(
                    right_x + column * (card_width + card_gap),
                    content.y + heading_height + row * (card_height + card_gap),
                    card_width,
                    card_height,
                )
                template_layout.append((template, rect))

        rules = self.rules()
        rows: list[tuple[CustomRuleDefinition, pygame.Rect, pygame.Rect]] = []
        capacity = max(1, (content.height - 42) // self.ROW_HEIGHT)
        maximum = max(0, len(rules) - capacity)
        self.scroll = max(0, min(maximum, self.scroll))
        if self.view == self.LIBRARY_VIEW:
            for index, rule in enumerate(rules[self.scroll : self.scroll + capacity]):
                row = pygame.Rect(
                    content.x,
                    content.y + 36 + index * self.ROW_HEIGHT,
                    content.width,
                    self.ROW_HEIGHT - 8,
                )
                delete = pygame.Rect(row.right - 78, row.y + 11, 62, row.height - 22)
                rows.append((rule, row, delete))
        return RuleStudioLayout(
            modal,
            close,
            learn_tab,
            library_tab,
            content,
            create,
            tuple(template_layout),
            tuple(rows),
            capacity,
        )

    @staticmethod
    def _fit_text(font: pygame.font.Font, text: str, width: int) -> str:
        if font.size(text)[0] <= width:
            return text
        suffix = "…"
        shortened = text
        while shortened and font.size(shortened + suffix)[0] > width:
            shortened = shortened[:-1]
        return shortened.rstrip() + suffix

    @staticmethod
    def _wrap(font: pygame.font.Font, text: str, width: int) -> tuple[str, ...]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if current and font.size(candidate)[0] > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return tuple(lines)

    @classmethod
    def _draw_wrapped(
        cls,
        screen: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        *,
        line_gap: int = 4,
        maximum_lines: int | None = None,
    ) -> int:
        lines = cls._wrap(font, text, rect.width)
        if maximum_lines is not None:
            lines = lines[:maximum_lines]
        y = rect.y
        for line in lines:
            rendered = font.render(line, True, color)
            screen.blit(rendered, (rect.x, y))
            y += rendered.get_height() + line_gap
        return y

    def _create_and_apply(self, expression: str | None) -> None:
        created = self.services.create_rule(expression)
        if created is not None:
            self.services.apply_rule(created)
            self.close()
        else:
            self.message = (
                self.services.feedback_text()
                or "Rule was not created. Check the notation and try again."
            )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        layout = self.geometry()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key in (pygame.K_TAB, pygame.K_l):
                self.view = (
                    self.LIBRARY_VIEW
                    if self.view == self.LEARN_VIEW
                    else self.LEARN_VIEW
                )
            elif event.key == pygame.K_r:
                self.view = self.LIBRARY_VIEW
            elif event.key in (pygame.K_UP, pygame.K_PAGEUP):
                self.scroll = max(0, self.scroll - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                self.scroll += 1
            elif event.key == pygame.K_c:
                self._create_and_apply(None)
            elif self.view == self.LEARN_VIEW and pygame.K_1 <= event.key <= pygame.K_4:
                index = event.key - pygame.K_1
                templates = self.services.templates()
                if index < len(templates):
                    self._create_and_apply(templates[index].expression)
            return True
        if event.type == pygame.MOUSEWHEEL:
            if self.view == self.LIBRARY_VIEW:
                self.scroll = max(0, self.scroll - event.y)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if layout.close.collidepoint(event.pos) or not layout.modal.collidepoint(
                event.pos
            ):
                self.close()
                return True
            if layout.learn_tab.collidepoint(event.pos):
                self.view = self.LEARN_VIEW
                return True
            if layout.library_tab.collidepoint(event.pos):
                self.view = self.LIBRARY_VIEW
                return True
            if layout.create.collidepoint(event.pos):
                self._create_and_apply(None)
                return True
            for template, rect in layout.templates:
                if rect.collidepoint(event.pos):
                    self._create_and_apply(template.expression)
                    return True
            for rule, row, delete in layout.rows:
                if delete.collidepoint(event.pos):
                    if self.services.delete_rule(rule):
                        self.message = f"Deleted '{rule.name}'."
                    else:
                        self.message = self.services.feedback_text()
                    return True
                if row.collidepoint(event.pos):
                    self.services.apply_rule(rule)
                    self.close()
                    return True
            return True
        return True

    def _guide_content(
        self,
    ) -> tuple[str, str, tuple[tuple[str, str], ...], str]:
        kind = self.services.editor_kind()
        if kind == "one_dimensional":
            return (
                "HOW A 1D RULE BECOMES A LOOKUP TABLE",
                "Every cell reads a local neighborhood. The rule code stores the output for every possible neighborhood; it is not a generation count.",
                (
                    ("FAMILY", "Chooses lookup, totalistic, memory, or reversible behavior."),
                    ("CODE", "Encodes the complete output table as one base-k integer."),
                    ("STATES (k)", "How many values each cell may hold."),
                    ("RADIUS (r)", "How far left and right each cell can read."),
                ),
                "Elementary example: 111 110 101 100 011 010 001 000 → eight output bits. Rule 30 stores 00011110₂.",
            )
        if kind == "generations":
            return (
                "READ S / B / C / M ONE PART AT A TIME",
                "Only state 1 is active. A cell that does not survive enters refractory states 2…C−1 before returning to empty state 0.",
                (
                    ("S", "Active-neighbor counts that let state 1 survive."),
                    ("B", "Active-neighbor counts that create state 1 in empty space."),
                    ("C", "Total states: empty + active + refractory trail."),
                    ("M / N", "M reads 26 Moore neighbors; N reads six face neighbors."),
                ),
                "Example 4/4/5/M: survive with 4, birth with 4, use 5 states and a 26-neighbor Moore neighborhood.",
            )
        dimension_label = "3D" if self.dimension == "3d" else "2D"
        neighbor_text = (
            "The active 3D neighborhood has either 26 Moore or six face neighbors."
            if self.dimension == "3d"
            else "The 2D Moore neighborhood contains the eight cells around the center."
        )
        return (
            f"READ A {dimension_label} LIFE-LIKE B/S RULE",
            f"Each update counts live neighbors around every cell. {neighbor_text}",
            (
                ("B = BIRTH", "A dead cell becomes alive at exactly these counts."),
                ("S = SURVIVE", "A live cell remains alive at exactly these counts."),
                ("UNLISTED", "All other live cells die; other dead cells stay empty."),
                ("SIMULTANEOUS", "Every cell reads the same old generation before writing."),
            ),
            "Example B36/S23: a dead cell is born with 3 or 6 neighbors; a live cell survives with 2 or 3.",
        )

    def _draw_learning_diagram(
        self,
        screen: pygame.Surface,
        panel: pygame.Rect,
        theme: Mapping[str, Any],
    ) -> None:
        kind = self.services.editor_kind()
        tiny = self.services.tiny_font()
        accent = self.accent
        diagram = pygame.Rect(panel.x + 14, panel.bottom - 78, panel.width - 28, 64)
        pygame.draw.rect(screen, theme["button"], diagram, border_radius=6)
        if kind == "one_dimensional":
            size = min(30, max(18, (diagram.width - 145) // 4))
            start_x = diagram.x + 16
            values = (1, 1, 0)
            for index, value in enumerate(values):
                cell = pygame.Rect(start_x + index * (size + 4), diagram.y + 17, size, size)
                pygame.draw.rect(
                    screen,
                    accent if value else theme["background"],
                    cell,
                    border_radius=3,
                )
                pygame.draw.rect(screen, theme["grid"], cell, 1, border_radius=3)
            arrow = tiny.render("→ lookup →", True, theme["menu_text"])
            screen.blit(arrow, (start_x + 3 * (size + 4) + 8, diagram.y + 24))
            output = pygame.Rect(
                start_x + 3 * (size + 4) + arrow.get_width() + 15,
                diagram.y + 17,
                size,
                size,
            )
            pygame.draw.rect(screen, theme["background"], output, border_radius=3)
            pygame.draw.rect(screen, self.accent, output, 2, border_radius=3)
            zero = tiny.render("0", True, theme["menu_text"])
            screen.blit(zero, zero.get_rect(center=output.center))
            screen.blit(
                tiny.render("next state", True, theme["menu_text"]),
                (output.right + 7, diagram.y + 24),
            )
            return
        if kind == "generations":
            labels = ("1 ACTIVE", "2", "3…C−1", "0 EMPTY")
            box_width = max(48, (diagram.width - 55) // 4)
            for index, label in enumerate(labels):
                box = pygame.Rect(
                    diagram.x + 10 + index * (box_width + 10),
                    diagram.y + 16,
                    box_width,
                    32,
                )
                pygame.draw.rect(
                    screen,
                    accent if index == 0 else theme["button_hover"],
                    box,
                    border_radius=4,
                )
                rendered = tiny.render(self._fit_text(tiny, label, box.width - 8), True, theme["button_text"])
                screen.blit(rendered, rendered.get_rect(center=box.center))
                if index < 3:
                    screen.blit(tiny.render("→", True, theme["menu_text"]), (box.right + 1, box.centery - 7))
            return

        if self.dimension == "3d":
            center = (diagram.x + 58, diagram.centery)
            neighbors = (
                (center[0] - 37, center[1]),
                (center[0] + 37, center[1]),
                (center[0] - 19, center[1] - 20),
                (center[0] + 19, center[1] + 20),
                (center[0] + 19, center[1] - 20),
                (center[0] - 19, center[1] + 20),
            )
            for point in neighbors:
                pygame.draw.line(screen, theme["grid"], center, point, 1)
                pygame.draw.circle(screen, accent, point, 4)
            cx, cy = center
            top = ((cx, cy - 10), (cx + 13, cy - 4), (cx, cy + 2), (cx - 13, cy - 4))
            left = ((cx - 13, cy - 4), (cx, cy + 2), (cx, cy + 16), (cx - 13, cy + 9))
            right = ((cx, cy + 2), (cx + 13, cy - 4), (cx + 13, cy + 9), (cx, cy + 16))
            pygame.draw.polygon(screen, (245, 185, 70), top)
            pygame.draw.polygon(screen, (185, 130, 45), left)
            pygame.draw.polygon(screen, (220, 160, 55), right)
            label = "Center voxel + 6 face / 26 Moore neighbors → count → B or S"
            screen.blit(
                tiny.render(
                    self._fit_text(tiny, label, diagram.width - 125),
                    True,
                    theme["menu_text"],
                ),
                (diagram.x + 120, diagram.y + 25),
            )
            return

        cell_size = 16
        start_x = diagram.x + 20
        start_y = diagram.y + 7
        active_neighbors = {(0, 1), (1, 2), (2, 1)}
        for row in range(3):
            for column in range(3):
                cell = pygame.Rect(
                    start_x + column * (cell_size + 2),
                    start_y + row * (cell_size + 2),
                    cell_size,
                    cell_size,
                )
                color = (
                    (245, 185, 70)
                    if (row, column) == (1, 1)
                    else accent
                    if (row, column) in active_neighbors
                    else theme["background"]
                )
                pygame.draw.rect(screen, color, cell, border_radius=2)
                pygame.draw.rect(screen, theme["grid"], cell, 1, border_radius=2)
        label = "Count neighbors → test B for empty or S for live center"
        screen.blit(tiny.render(self._fit_text(tiny, label, diagram.width - 100), True, theme["menu_text"]), (start_x + 72, diagram.y + 25))

    def _draw_learn_view(
        self,
        screen: pygame.Surface,
        theme: Mapping[str, Any],
        layout: RuleStudioLayout,
    ) -> None:
        small = self.services.small_font()
        tiny = self.services.tiny_font()
        left = pygame.Rect(
            layout.content.x,
            layout.content.y,
            layout.content.width // 2 - 10,
            layout.content.height,
        )
        pygame.draw.rect(screen, theme["button"], left, border_radius=8)
        pygame.draw.rect(screen, self.accent, left, 2, border_radius=8)
        title, lead, tokens, example = self._guide_content()
        compact = left.height < 330
        screen.blit(small.render(self._fit_text(small, title, left.width - 28), True, theme["button_text"]), (left.x + 14, left.y + 12))
        lead_y = self._draw_wrapped(
            screen,
            tiny,
            lead,
            theme["menu_text"],
            pygame.Rect(left.x + 14, left.y + 42, left.width - 28, 58),
            maximum_lines=2 if compact else 3,
        )
        token_top = lead_y + 6
        token_gap = 7
        token_width = (left.width - 35) // 2
        example_top = left.bottom - 142
        token_bottom = left.bottom - 12 if compact else example_top - 6
        token_height = max(42, (token_bottom - token_top - token_gap) // 2)
        for index, (token, meaning) in enumerate(tokens):
            column = index % 2
            row = index // 2
            card = pygame.Rect(
                left.x + 14 + column * (token_width + token_gap),
                token_top + row * (token_height + token_gap),
                token_width,
                token_height,
            )
            pygame.draw.rect(screen, theme["button_hover"], card, border_radius=6)
            pygame.draw.rect(screen, self.accent, card, 1, border_radius=6)
            screen.blit(tiny.render(token, True, self.accent), (card.x + 9, card.y + 7))
            self._draw_wrapped(
                screen,
                tiny,
                meaning,
                theme["button_text"],
                pygame.Rect(card.x + 9, card.y + 25, card.width - 18, card.height - 29),
                maximum_lines=max(
                    1,
                    (card.height - 33) // (tiny.get_height() + 2),
                ),
                line_gap=2,
            )
        if not compact:
            example_rect = pygame.Rect(
                left.x + 14,
                example_top,
                left.width - 28,
                54,
            )
            self._draw_wrapped(
                screen,
                tiny,
                example,
                (245, 205, 95),
                example_rect,
                maximum_lines=3,
                line_gap=2,
            )
            self._draw_learning_diagram(screen, left, theme)

        right_x = left.right + 20
        heading = small.render("STARTING TEMPLATES — click one to customize", True, theme["button_text"])
        screen.blit(heading, (right_x, layout.content.y + 4))
        next_step_text = self._fit_text(
            tiny,
            "Then name it, edit the highlighted notation, and press Enter to apply.",
            layout.content.right - right_x,
        )
        next_step = tiny.render(
            next_step_text,
            True,
            theme["menu_text"],
        )
        screen.blit(
            next_step,
            (right_x, layout.content.y + 23),
        )
        mouse = pygame.mouse.get_pos()
        for index, (template, rect) in enumerate(layout.templates):
            hovered = rect.collidepoint(mouse)
            pygame.draw.rect(
                screen,
                theme["button_hover"] if hovered else theme["button"],
                rect,
                border_radius=8,
            )
            pygame.draw.rect(screen, self.accent, rect, 2 if hovered else 1, border_radius=8)
            badge = pygame.Rect(rect.x + 10, rect.y + 10, 25, 25)
            pygame.draw.rect(screen, self.accent, badge, border_radius=5)
            number = tiny.render(str(index + 1), True, (15, 20, 28))
            screen.blit(number, number.get_rect(center=badge.center))
            screen.blit(tiny.render(self._fit_text(tiny, template.title, rect.width - 54), True, theme["button_text"]), (badge.right + 8, rect.y + 8))
            expression = small.render(self._fit_text(small, template.expression, rect.width - 20), True, self.accent)
            screen.blit(expression, (rect.x + 10, rect.y + 39))
            self._draw_wrapped(
                screen,
                tiny,
                template.description,
                theme["menu_text"],
                pygame.Rect(rect.x + 10, rect.y + 67, rect.width - 20, rect.height - 73),
                maximum_lines=max(
                    1,
                    (rect.height - 73) // (tiny.get_height() + 2),
                ),
                line_gap=2,
            )

    def _draw_library_view(
        self,
        screen: pygame.Surface,
        theme: Mapping[str, Any],
        layout: RuleStudioLayout,
    ) -> None:
        small = self.services.small_font()
        tiny = self.services.tiny_font()
        rules = self.rules()
        heading = (
            "MY SAVED RULES — click a row to apply it"
            if rules
            else "MY SAVED RULES"
        )
        screen.blit(small.render(heading, True, theme["button_text"]), layout.content.topleft)
        mouse = pygame.mouse.get_pos()
        current = self.services.current_rule_key()
        for rule, row, delete in layout.rows:
            hovered = row.collidepoint(mouse)
            selected = rule.key == current
            pygame.draw.rect(
                screen,
                theme["button_hover"] if hovered or selected else theme["button"],
                row,
                border_radius=7,
            )
            pygame.draw.rect(
                screen,
                self.accent if selected or hovered else theme["grid"],
                row,
                3 if selected else 1,
                border_radius=7,
            )
            screen.blit(small.render(self._fit_text(small, rule.name, row.width - 118), True, theme["button_text"]), (row.x + 12, row.y + 7))
            summary = tiny.render(self._fit_text(tiny, rule.summary, row.width - 118), True, theme["menu_text"])
            screen.blit(summary, (row.x + 12, row.bottom - summary.get_height() - 8))
            pygame.draw.rect(screen, (105, 48, 55), delete, border_radius=5)
            pygame.draw.rect(screen, (235, 105, 115), delete, 1, border_radius=5)
            delete_text = tiny.render("Delete", True, (255, 235, 238))
            screen.blit(delete_text, delete_text.get_rect(center=delete.center))
        if not rules:
            message = small.render(
                "No saved rules yet — open Learn & Templates or build from current context.",
                True,
                theme["menu_text"],
            )
            screen.blit(message, message.get_rect(center=layout.content.center))

    def draw(self) -> None:
        if not self.active:
            return
        screen = self.services.screen()
        theme = self.services.theme()
        large = self.services.large_font()
        small = self.services.small_font()
        tiny = self.services.tiny_font()
        dimmer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 215))
        screen.blit(dimmer, (0, 0))
        layout = self.geometry()
        pygame.draw.rect(screen, theme["info_bar"], layout.modal, border_radius=12)
        pygame.draw.rect(screen, theme["text"], layout.modal, 2, border_radius=12)
        title = large.render(
            f"Custom Rule Studio · {self.dimension.upper()}",
            True,
            theme["text"],
        )
        screen.blit(title, (layout.modal.x + 24, layout.modal.y + 16))
        context = self._fit_text(tiny, self.services.context_label(), layout.modal.width - 110)
        screen.blit(tiny.render(context, True, theme["menu_text"]), (layout.modal.x + 26, layout.modal.y + 54))
        pygame.draw.rect(screen, theme["button"], layout.close, border_radius=5)
        close_text = small.render("×", True, theme["button_text"])
        screen.blit(close_text, close_text.get_rect(center=layout.close.center))

        rules = self.rules()
        for key, rect, label in (
            (self.LEARN_VIEW, layout.learn_tab, "LEARN & TEMPLATES"),
            (self.LIBRARY_VIEW, layout.library_tab, f"MY RULES ({len(rules)})"),
        ):
            active = self.view == key
            pygame.draw.rect(screen, theme["button_hover"] if active else theme["button"], rect, border_radius=6)
            pygame.draw.rect(screen, self.accent if active else theme["grid"], rect, 3 if active else 1, border_radius=6)
            rendered = small.render(label, True, theme["button_text"])
            screen.blit(rendered, rendered.get_rect(center=rect.center))

        if self.view == self.LEARN_VIEW:
            self._draw_learn_view(screen, theme, layout)
        else:
            self._draw_library_view(screen, theme, layout)

        pygame.draw.rect(screen, theme["button_hover"], layout.create, border_radius=7)
        pygame.draw.rect(screen, self.accent, layout.create, 2, border_radius=7)
        create_text = small.render(
            "Build & Apply a Custom Rule from Current Context (C)",
            True,
            theme["button_text"],
        )
        screen.blit(create_text, create_text.get_rect(center=layout.create.center))

        if self.view == self.LIBRARY_VIEW:
            start = min(len(rules), self.scroll + 1) if rules else 0
            end = min(len(rules), self.scroll + layout.capacity)
            count = f"{start}-{end} / {len(rules)} · "
        else:
            count = "1-4: use template · "
        footer_text = (
            self.message
            or f"{count}Tab: switch guide/library · C: custom builder · Esc: close"
        )
        footer = tiny.render(
            self._fit_text(tiny, footer_text, layout.modal.width - 52),
            True,
            (255, 155, 115) if self.message else theme["menu_text"],
        )
        screen.blit(footer, (layout.modal.x + 26, layout.modal.bottom - 31))
