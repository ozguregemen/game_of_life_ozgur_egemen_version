"""Keyboard shortcut and interaction help overlay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import pygame

HelpEntry = tuple[str, str]


@dataclass(frozen=True)
class HelpPanelServices:
    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    context_title: Callable[[], str]
    context_entries: Callable[[], Sequence[HelpEntry]]
    pause: Callable[[], None]


class ShortcutHelpPanel:
    """Draw a context-aware, non-destructive shortcut reference."""

    COMMON_ENTRIES: tuple[HelpEntry, ...] = (
        ("Space", "Run or pause the active simulation"),
        ("N", "Advance one generation while paused"),
        ("Up / Down", "Change simulation speed"),
        ("D / M", "Choose dimension / choose 2D mode"),
        ("P / I / X", "Sessions / scientific analysis / exports"),
        ("J", "Go directly to a recorded generation"),
        ("[ / ]", "Zoom out / zoom in"),
        ("C / G", "Center the view / toggle grid lines"),
        ("Ctrl+S / Ctrl+O", "Quick-save / quick-load the complete session"),
        ("F1 or ?", "Open or close this help panel"),
        ("F2", "Open the guided tutorial from the 1D workspace"),
    )

    def __init__(self, services: HelpPanelServices) -> None:
        self.services = services
        self.active = False

    def open(self) -> None:
        self.services.pause()
        self.active = True

    def close(self) -> None:
        self.active = False

    def toggle(self) -> None:
        if self.active:
            self.close()
        else:
            self.open()

    def geometry(self) -> tuple[pygame.Rect, pygame.Rect]:
        width, height = self.services.window_size()
        modal = pygame.Rect(
            0,
            0,
            min(860, width - 40),
            min(600, height - 40),
        )
        modal.center = (width // 2, height // 2)
        close = pygame.Rect(modal.right - 42, modal.y + 12, 28, 26)
        return modal, close

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            question_mark = event.key == pygame.K_SLASH and bool(
                getattr(event, "mod", pygame.key.get_mods()) & pygame.KMOD_SHIFT
            )
            if event.key in (pygame.K_ESCAPE, pygame.K_F1) or question_mark:
                self.close()
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            modal, close = self.geometry()
            if close.collidepoint(event.pos) or not modal.collidepoint(event.pos):
                self.close()
            return True
        return True

    def draw(self) -> None:
        if not self.active:
            return
        screen = self.services.screen()
        width, height = self.services.window_size()
        theme = self.services.theme()
        dimmer = pygame.Surface((width, height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 205))
        screen.blit(dimmer, (0, 0))
        modal, close = self.geometry()
        pygame.draw.rect(screen, theme["menu"], modal, border_radius=12)
        pygame.draw.rect(screen, theme["menu_text"], modal, 2, border_radius=12)
        pygame.draw.rect(screen, theme["button"], close, border_radius=5)
        close_surface = self.services.small_font().render(
            "×",
            True,
            theme["button_text"],
        )
        screen.blit(
            close_surface,
            close_surface.get_rect(center=close.center),
        )
        screen.blit(
            self.services.large_font().render(
                "Keyboard & Interaction Help",
                True,
                theme["text"],
            ),
            (modal.x + 24, modal.y + 17),
        )
        context_title = self.services.context_title()
        screen.blit(
            self.services.tiny_font().render(
                f"Current context: {context_title}",
                True,
                theme["menu_text"],
            ),
            (modal.x + 25, modal.y + 52),
        )

        columns = (
            ("Common", self.COMMON_ENTRIES),
            ("Current workspace", tuple(self.services.context_entries())),
        )
        gap = 18
        column_width = (modal.width - 48 - gap) // 2
        top = modal.y + 84
        for column, (title, entries) in enumerate(columns):
            x = modal.x + 24 + column * (column_width + gap)
            screen.blit(
                self.services.small_font().render(title, True, theme["text"]),
                (x, top),
            )
            y = top + 30
            for shortcut, description in entries:
                if y + 39 > modal.bottom - 34:
                    break
                row = pygame.Rect(x, y, column_width, 35)
                pygame.draw.rect(screen, theme["button"], row, border_radius=5)
                key_width = min(
                    112,
                    max(58, self.services.tiny_font().size(shortcut)[0] + 18),
                )
                key_rect = pygame.Rect(row.x + 5, row.y + 5, key_width, row.height - 10)
                pygame.draw.rect(screen, theme["button_hover"], key_rect, border_radius=4)
                screen.blit(
                    self.services.tiny_font().render(
                        shortcut,
                        True,
                        theme["button_text"],
                    ),
                    (key_rect.x + 8, key_rect.y + 5),
                )
                available = row.width - key_width - 19
                detail = description
                while detail and self.services.tiny_font().size(detail)[0] > available:
                    detail = detail[:-1]
                if detail != description:
                    detail = detail.rstrip() + "..."
                screen.blit(
                    self.services.tiny_font().render(detail, True, theme["text"]),
                    (key_rect.right + 8, row.y + 11),
                )
                y += 40

        footer = self.services.tiny_font().render(
            "F1, ? or Esc closes · hover sidebar controls for tooltips",
            True,
            theme["menu_text"],
        )
        screen.blit(
            footer,
            (modal.centerx - footer.get_width() // 2, modal.bottom - 25),
        )
