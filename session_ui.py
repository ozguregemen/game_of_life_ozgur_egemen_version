"""Application-level modal UI for complete sessions and 1D profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame


@dataclass(frozen=True)
class SessionMenuServices:
    """Callbacks and display resources used by :class:`SessionMenu`."""

    active_dimension: Callable[[], str]
    prepare_open: Callable[[], None]
    quick_save: Callable[[], bool]
    quick_load: Callable[[], bool]
    named_save: Callable[[], bool]
    save_profile: Callable[[], bool]
    load_session: Callable[[str], bool]
    load_profile: Callable[[str], bool]
    list_sessions: Callable[[], list[dict[str, str]]]
    list_profiles: Callable[[], list[dict[str, str]]]
    set_status: Callable[[str, float], None]
    window_size: Callable[[], tuple[int, int]]
    screen: Callable[[], pygame.Surface]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]


class SessionMenu:
    """Own session/profile modal navigation, cached catalogs, and rendering."""

    def __init__(self, services: SessionMenuServices) -> None:
        self.services = services
        self.active = False
        self.view = "actions"
        self.scroll = 0
        self.items: list[dict[str, str]] = []

    @staticmethod
    def _fit_text(font: pygame.font.Font, value: str, width: int) -> str:
        """Shorten one modal label so user-provided names stay inside cards."""
        if font.size(value)[0] <= width:
            return value
        ellipsis = "..."
        shortened = value
        while shortened and font.size(shortened + ellipsis)[0] > width:
            shortened = shortened[:-1]
        return shortened.rstrip() + ellipsis

    def open(self) -> None:
        self.services.prepare_open()
        self.active = True
        self.view = "actions"
        self.scroll = 0
        self.items = []

    def close(self) -> None:
        self.active = False

    def show_sessions(self) -> None:
        try:
            self.items = self.services.list_sessions()
        except OSError as exc:
            self.services.set_status(f"Could not list sessions: {exc}", 5.0)
            self.items = []
        self.view = "sessions"
        self.scroll = 0

    def show_profiles(self) -> None:
        try:
            self.items = self.services.list_profiles()
        except OSError as exc:
            self.services.set_status(
                f"Could not list experiment profiles: {exc}",
                5.0,
            )
            self.items = []
        self.view = "profiles"
        self.scroll = 0

    def entries(self) -> list[dict[str, str]]:
        """Return cached rows for the current manager view."""
        if self.view == "actions":
            entries = [
                {
                    "key": "quick_save",
                    "name": "Quick Save · Last Session",
                    "detail": "Ctrl+S · overwrites the recovery slot",
                },
                {
                    "key": "quick_load",
                    "name": "Quick Load · Last Session",
                    "detail": "Ctrl+O · restores all workspaces",
                },
                {
                    "key": "named_save",
                    "name": "Save Named Session",
                    "detail": "Create a separate full-session JSON file",
                },
                {
                    "key": "browse_sessions",
                    "name": "Browse Saved Sessions",
                    "detail": "Load any valid named session",
                },
            ]
            if self.services.active_dimension() == "1d":
                entries.extend(
                    (
                        {
                            "key": "save_profile",
                            "name": "Save 1D Experiment Profile",
                            "detail": (
                                "Rule + boundary + current row as reusable seed"
                            ),
                        },
                        {
                            "key": "browse_profiles",
                            "name": "Browse 1D Experiment Profiles",
                            "detail": "Restart an experiment at generation 0",
                        },
                    )
                )
            return entries

        prefix = "load_session" if self.view == "sessions" else "load_profile"
        return [
            {
                "key": f"{prefix}:{item['identifier']}",
                "name": item["name"],
                "detail": (
                    item["saved_at"]
                    .replace("T", " ")
                    .replace("+00:00", " UTC")
                ),
            }
            for item in self.items
        ]

    def execute(self, key: str) -> None:
        """Run one manager action selected by mouse or number key."""
        if key == "quick_save":
            self.close()
            self.services.quick_save()
        elif key == "quick_load":
            self.close()
            self.services.quick_load()
        elif key == "named_save":
            self.close()
            self.services.named_save()
        elif key == "browse_sessions":
            self.show_sessions()
        elif key == "save_profile":
            self.close()
            self.services.save_profile()
        elif key == "browse_profiles":
            self.show_profiles()
        elif key.startswith("load_session:"):
            self.close()
            self.services.load_session(key.split(":", 1)[1])
        elif key.startswith("load_profile:"):
            self.close()
            self.services.load_profile(key.split(":", 1)[1])

    def geometry(
        self,
    ) -> tuple[pygame.Rect, list[tuple[dict[str, str], pygame.Rect]], int]:
        """Return modal geometry, visible rows, and visible capacity."""
        window_width, window_height = self.services.window_size()
        modal_width = min(660, window_width - 40)
        modal_height = min(520, window_height - 40)
        modal = pygame.Rect(0, 0, modal_width, modal_height)
        modal.center = (window_width // 2, window_height // 2)
        row_height = 52
        list_top = modal.y + 88
        list_bottom = modal.bottom - 44
        capacity = max(1, (list_bottom - list_top) // row_height)
        entries = self.entries()
        visible = entries[self.scroll : self.scroll + capacity]
        cards = [
            (
                entry,
                pygame.Rect(
                    modal.x + 22,
                    list_top + index * row_height,
                    modal.width - 44,
                    row_height - 5,
                ),
            )
            for index, entry in enumerate(visible)
        ]
        return modal, cards, capacity

    def draw(self) -> None:
        """Draw the full-session and Elementary profile manager."""
        if not self.active:
            return
        window_width, window_height = self.services.window_size()
        screen = self.services.screen()
        dimmer = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 195))
        screen.blit(dimmer, (0, 0))
        modal, cards, _ = self.geometry()
        pygame.draw.rect(screen, (24, 30, 35), modal, border_radius=12)
        pygame.draw.rect(screen, (80, 190, 145), modal, 2, border_radius=12)
        titles = {
            "actions": "Session & Experiment Manager",
            "sessions": "Saved Sessions",
            "profiles": "1D Experiment Profiles",
        }
        subtitles = {
            "actions": (
                "Complete state includes both dimensions, all 2D modes, "
                "UI and cameras."
            ),
            "sessions": "Select a session to restore it; Esc returns to actions.",
            "profiles": (
                "Profiles restart 1D from their saved seed at generation 0."
            ),
        }
        screen.blit(
            self.services.large_font().render(
                titles[self.view],
                True,
                (245, 248, 247),
            ),
            (modal.x + 22, modal.y + 16),
        )
        tiny_font = self.services.tiny_font()
        screen.blit(
            tiny_font.render(subtitles[self.view], True, (185, 205, 196)),
            (modal.x + 23, modal.y + 55),
        )

        if not cards and self.view != "actions":
            empty = self.services.small_font().render(
                "No valid saved files found.",
                True,
                (205, 210, 210),
            )
            screen.blit(empty, empty.get_rect(center=modal.center))

        mouse_position = pygame.mouse.get_pos()
        small_font = self.services.small_font()
        for index, (entry, card) in enumerate(cards, start=1):
            hovered = card.collidepoint(mouse_position)
            pygame.draw.rect(
                screen,
                (52, 70, 66) if hovered else (40, 48, 49),
                card,
                border_radius=6,
            )
            pygame.draw.rect(screen, (75, 105, 94), card, 1, border_radius=6)
            number = f"{index}. " if index <= 9 else ""
            name = self._fit_text(
                small_font,
                number + entry["name"],
                card.width - 24,
            )
            detail = self._fit_text(
                tiny_font,
                entry["detail"],
                card.width - 28,
            )
            screen.blit(
                small_font.render(name, True, (245, 248, 247)),
                (card.x + 12, card.y + 6),
            )
            screen.blit(
                tiny_font.render(detail, True, (175, 190, 185)),
                (card.x + 14, card.y + 28),
            )

        footer = "Mouse / 1–9: select · wheel: scroll · Esc: back/close · P: close"
        footer_surface = tiny_font.render(footer, True, (180, 195, 190))
        screen.blit(
            footer_surface,
            (modal.centerx - footer_surface.get_width() // 2, modal.bottom - 28),
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle manager navigation without leaking input to a workspace."""
        if not self.active:
            return False
        entries = self.entries()
        _, _, capacity = self.geometry()
        max_scroll = max(0, len(entries) - capacity)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.close()
                return True
            if event.key == pygame.K_ESCAPE:
                if self.view == "actions":
                    self.close()
                else:
                    self.view = "actions"
                    self.scroll = 0
                    self.items = []
                return True
            if pygame.K_1 <= event.key <= pygame.K_9:
                relative_index = event.key - pygame.K_1
                absolute_index = self.scroll + relative_index
                if relative_index < capacity and absolute_index < len(entries):
                    self.execute(entries[absolute_index]["key"])
                return True

        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(max_scroll, self.scroll - event.y))
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            modal, cards, _ = self.geometry()
            for entry, card in cards:
                if card.collidepoint(event.pos):
                    self.execute(entry["key"])
                    return True
            if not modal.collidepoint(event.pos):
                self.close()
            return True
        return True
