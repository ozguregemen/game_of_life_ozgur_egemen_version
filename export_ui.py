"""Contextual Pygame menu for scientific and visual experiment exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from exporting import ExportRunner


@dataclass(frozen=True)
class ExportMenuServices:
    """Callbacks and display resources used by :class:`ExportMenu`."""

    prepare_open: Callable[[], None]
    context_label: Callable[[], str]
    export_png: Callable[[], bool]
    export_gif: Callable[[], bool]
    export_mp4: Callable[[], bool]
    export_csv: Callable[[], bool]
    export_json: Callable[[], bool]
    set_status: Callable[[str, float], None]
    window_size: Callable[[], tuple[int, int]]
    screen: Callable[[], pygame.Surface]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]


class ExportMenu:
    """Present context-aware exports and report background job completion."""

    def __init__(self, services: ExportMenuServices, runner: ExportRunner) -> None:
        self.services = services
        self.runner = runner
        self.active = False

    @staticmethod
    def _fit_text(font: pygame.font.Font, value: str, width: int) -> str:
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

    def close(self) -> None:
        self.active = False

    def toggle(self) -> None:
        if self.active:
            self.close()
        else:
            self.open()

    def entries(self) -> tuple[dict[str, object], ...]:
        context = self.services.context_label()
        return (
            {
                "key": "png",
                "name": (
                    "PNG Slice Atlas"
                    if context.startswith("3D")
                    else "PNG Diagram"
                ),
                "detail": (
                    "Full 1D space-time diagram"
                    if context.startswith("1D")
                    else "Current orthogonal XY / XZ / YZ slices"
                    if context.startswith("3D")
                    else "Current 2D state grid"
                ),
                "callback": self.services.export_png,
            },
            {
                "key": "gif",
                "name": "Animated GIF",
                "detail": (
                    "Up to 120 sampled 3D slice-atlas frames"
                    if context.startswith("3D")
                    else "Up to 120 evenly sampled timeline frames"
                ),
                "callback": self.services.export_gif,
            },
            {
                "key": "mp4",
                "name": "MP4 Video",
                "detail": (
                    "H.264 3D slice-atlas timeline at 20 frames per second"
                    if context.startswith("3D")
                    else "H.264 timeline video at 20 frames per second"
                ),
                "callback": self.services.export_mp4,
            },
            {
                "key": "csv",
                "name": "Generation Metrics CSV",
                "detail": "Population, density, entropy and change rate",
                "callback": self.services.export_csv,
            },
            {
                "key": "json",
                "name": "Shareable Experiment JSON",
                "detail": "Reloadable session plus active experiment metadata",
                "callback": self.services.export_json,
            },
        )

    def execute(self, key: str) -> None:
        if self.runner.busy:
            self.services.set_status(
                f"Export already running: {self.runner.label}",
                3.0,
            )
            return
        for entry in self.entries():
            if entry["key"] != key:
                continue
            callback = entry["callback"]
            if callable(callback) and callback():
                self.close()
            return

    def update(self) -> None:
        """Report completed worker results on the Pygame event thread."""

        outcome = self.runner.poll()
        if outcome is None:
            return
        if outcome.succeeded:
            assert outcome.path is not None
            self.services.set_status(
                f"{outcome.label} exported to exports/{outcome.path.name}",
                6.0,
            )
        else:
            self.services.set_status(
                f"{outcome.label} export failed: {outcome.error}",
                6.0,
            )

    def geometry(
        self,
    ) -> tuple[pygame.Rect, list[tuple[dict[str, object], pygame.Rect]]]:
        width, height = self.services.window_size()
        modal = pygame.Rect(0, 0, min(650, width - 40), min(460, height - 40))
        modal.center = (width // 2, height // 2)
        row_height = 57
        list_top = modal.y + 92
        entries = self.entries()
        cards = [
            (
                entry,
                pygame.Rect(
                    modal.x + 22,
                    list_top + index * row_height,
                    modal.width - 44,
                    row_height - 6,
                ),
            )
            for index, entry in enumerate(entries)
        ]
        return modal, cards

    def draw(self) -> None:
        self.update()
        if not self.active:
            return
        screen = self.services.screen()
        width, height = self.services.window_size()
        dimmer = pygame.Surface((width, height), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 195))
        screen.blit(dimmer, (0, 0))

        modal, cards = self.geometry()
        pygame.draw.rect(screen, (24, 30, 35), modal, border_radius=12)
        pygame.draw.rect(screen, (90, 195, 255), modal, 2, border_radius=12)
        screen.blit(
            self.services.large_font().render(
                "Export Results",
                True,
                (245, 248, 247),
            ),
            (modal.x + 22, modal.y + 15),
        )
        context = self._fit_text(
            self.services.tiny_font(),
            self.services.context_label(),
            modal.width - 46,
        )
        screen.blit(
            self.services.tiny_font().render(
                context,
                True,
                (180, 205, 215),
            ),
            (modal.x + 23, modal.y + 57),
        )

        mouse_position = pygame.mouse.get_pos()
        small_font = self.services.small_font()
        tiny_font = self.services.tiny_font()
        for index, (entry, card) in enumerate(cards, start=1):
            hovered = card.collidepoint(mouse_position)
            pygame.draw.rect(
                screen,
                (48, 68, 78) if hovered else (39, 48, 53),
                card,
                border_radius=6,
            )
            pygame.draw.rect(screen, (70, 105, 120), card, 1, border_radius=6)
            name = self._fit_text(
                small_font,
                f"{index}. {entry['name']}",
                card.width - 24,
            )
            detail = self._fit_text(
                tiny_font,
                str(entry["detail"]),
                card.width - 28,
            )
            screen.blit(
                small_font.render(name, True, (245, 248, 247)),
                (card.x + 12, card.y + 6),
            )
            screen.blit(
                tiny_font.render(detail, True, (175, 195, 200)),
                (card.x + 14, card.y + 30),
            )

        footer = "Mouse / 1-5: select  |  Esc or X: close"
        if self.runner.busy:
            footer = f"Exporting {self.runner.label} in the background..."
        footer_surface = tiny_font.render(footer, True, (180, 195, 200))
        screen.blit(
            footer_surface,
            (modal.centerx - footer_surface.get_width() // 2, modal.bottom - 27),
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_x):
                self.close()
                return True
            if pygame.K_1 <= event.key <= pygame.K_5:
                self.execute(self.entries()[event.key - pygame.K_1]["key"])
                return True
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            modal, cards = self.geometry()
            for entry, card in cards:
                if card.collidepoint(event.pos):
                    self.execute(str(entry["key"]))
                    return True
            if not modal.collidepoint(event.pos):
                self.close()
            return True
        return True
