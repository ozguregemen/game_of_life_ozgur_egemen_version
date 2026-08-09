"""Contextual Pygame browser/editor shell for saved custom CA rules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

import pygame

from custom_rules import CustomRuleDefinition, get_custom_rules


@dataclass(frozen=True)
class RuleStudioServices:
    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    theme: Callable[[], Mapping[str, Any]]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    active_dimension: Callable[[], str]
    context_label: Callable[[], str]
    current_rule_key: Callable[[], str | None]
    create_rule: Callable[[], CustomRuleDefinition | None]
    apply_rule: Callable[[CustomRuleDefinition], None]
    delete_rule: Callable[[CustomRuleDefinition], bool]
    pause: Callable[[], None]
    set_status: Callable[[str, float], None]


class CustomRuleStudio:
    """Full-window contextual catalog for user-authored rule recipes."""

    ROW_HEIGHT = 70

    def __init__(self, services: RuleStudioServices) -> None:
        self.services = services
        self.active = False
        self.scroll = 0

    @property
    def dimension(self) -> str:
        return self.services.active_dimension()

    def rules(self) -> tuple[CustomRuleDefinition, ...]:
        return get_custom_rules(self.dimension)

    def open(self) -> None:
        self.services.pause()
        self.active = True
        self.scroll = 0

    def close(self) -> None:
        self.active = False

    def geometry(
        self,
    ) -> tuple[
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
        tuple[tuple[CustomRuleDefinition, pygame.Rect, pygame.Rect], ...],
        int,
    ]:
        width, height = self.services.window_size()
        modal = pygame.Rect(18, 38, max(520, width - 36), max(440, height - 76))
        close = pygame.Rect(modal.right - 48, modal.y + 16, 32, 32)
        create = pygame.Rect(modal.x + 24, modal.y + 118, modal.width - 48, 46)
        list_top = create.bottom + 18
        list_bottom = modal.bottom - 52
        capacity = max(1, (list_bottom - list_top) // self.ROW_HEIGHT)
        rules = self.rules()
        maximum = max(0, len(rules) - capacity)
        self.scroll = max(0, min(maximum, self.scroll))
        visible = rules[self.scroll : self.scroll + capacity]
        rows = []
        for index, rule in enumerate(visible):
            row = pygame.Rect(
                modal.x + 24,
                list_top + index * self.ROW_HEIGHT,
                modal.width - 48,
                self.ROW_HEIGHT - 8,
            )
            delete = pygame.Rect(row.right - 78, row.y + 11, 62, row.height - 22)
            rows.append((rule, row, delete))
        return modal, close, create, tuple(rows), capacity

    @staticmethod
    def _fit_text(font: pygame.font.Font, text: str, width: int) -> str:
        if font.size(text)[0] <= width:
            return text
        suffix = "…"
        shortened = text
        while shortened and font.size(shortened + suffix)[0] > width:
            shortened = shortened[:-1]
        return shortened.rstrip() + suffix

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key in (pygame.K_UP, pygame.K_PAGEUP):
                self.scroll = max(0, self.scroll - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                self.scroll += 1
            elif event.key == pygame.K_c:
                created = self.services.create_rule()
                if created is not None:
                    self.scroll = max(0, len(self.rules()) - 1)
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            modal, close, create, rows, _capacity = self.geometry()
            if close.collidepoint(event.pos) or not modal.collidepoint(event.pos):
                self.close()
                return True
            if create.collidepoint(event.pos):
                created = self.services.create_rule()
                if created is not None:
                    self.scroll = max(0, len(self.rules()) - 1)
                return True
            for rule, row, delete in rows:
                if delete.collidepoint(event.pos):
                    self.services.delete_rule(rule)
                    return True
                if row.collidepoint(event.pos):
                    self.services.apply_rule(rule)
                    self.close()
                    return True
            return True
        return True

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
        modal, close, create, rows, capacity = self.geometry()
        accent = {"1d": (70, 190, 235), "2d": (80, 220, 105), "3d": (190, 110, 245)}[
            self.dimension
        ]
        pygame.draw.rect(screen, theme["info_bar"], modal, border_radius=12)
        pygame.draw.rect(screen, theme["text"], modal, 2, border_radius=12)
        title = large.render(
            f"Custom Rule Studio · {self.dimension.upper()}",
            True,
            theme["text"],
        )
        screen.blit(title, (modal.x + 24, modal.y + 18))
        context = self._fit_text(
            tiny,
            self.services.context_label(),
            modal.width - 110,
        )
        screen.blit(
            tiny.render(context, True, theme["menu_text"]),
            (modal.x + 26, modal.y + 57),
        )
        guidance = {
            "1d": "Name the current family/state/radius recipe and enter a rule code.",
            "2d": "Create a Life-like rule with B/S notation, for example B36/S23.",
            "3d": "Create Spatial Life B/S or Generations S/B/C/M rules for the active mode.",
        }[self.dimension]
        screen.blit(
            tiny.render(
                self._fit_text(tiny, guidance, modal.width - 52),
                True,
                theme["menu_text"],
            ),
            (modal.x + 26, modal.y + 82),
        )
        pygame.draw.rect(screen, theme["button"], close, border_radius=5)
        close_text = small.render("×", True, theme["button_text"])
        screen.blit(close_text, close_text.get_rect(center=close.center))

        pygame.draw.rect(screen, theme["button_hover"], create, border_radius=7)
        pygame.draw.rect(screen, accent, create, 2, border_radius=7)
        create_text = small.render(
            "Create New Rule from Current Context (C)",
            True,
            theme["button_text"],
        )
        screen.blit(create_text, create_text.get_rect(center=create.center))

        mouse = pygame.mouse.get_pos()
        current = self.services.current_rule_key()
        for rule, row, delete in rows:
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
                accent if selected or hovered else theme["grid"],
                row,
                3 if selected else 1,
                border_radius=7,
            )
            name = small.render(
                self._fit_text(small, rule.name, row.width - 118),
                True,
                theme["button_text"],
            )
            screen.blit(name, (row.x + 12, row.y + 7))
            summary = tiny.render(
                self._fit_text(tiny, rule.summary, row.width - 118),
                True,
                theme["menu_text"],
            )
            screen.blit(summary, (row.x + 12, row.bottom - summary.get_height() - 8))
            pygame.draw.rect(screen, (105, 48, 55), delete, border_radius=5)
            pygame.draw.rect(screen, (235, 105, 115), delete, 1, border_radius=5)
            delete_text = tiny.render("Delete", True, (255, 235, 238))
            screen.blit(delete_text, delete_text.get_rect(center=delete.center))

        rules = self.rules()
        start = min(len(rules), self.scroll + 1) if rules else 0
        end = min(len(rules), self.scroll + capacity)
        footer = tiny.render(
            f"{start}-{end} / {len(rules)} · click a rule to apply · wheel/arrow scroll · Esc closes",
            True,
            theme["menu_text"],
        )
        screen.blit(footer, (modal.x + 26, modal.bottom - 34))
