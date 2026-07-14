"""Shared draggable timeline controls for every simulation workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from timeline_history import TimelineStatus


@dataclass(frozen=True)
class TimelinePanelServices:
    """Application callbacks and drawing resources used by the timeline panel."""

    rect: Callable[[], pygame.Rect]
    screen: Callable[[], pygame.Surface]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    tiny_font: Callable[[], pygame.font.Font]
    status: Callable[[], TimelineStatus]
    seek: Callable[[int], bool]
    step: Callable[[int], bool]
    request_generation: Callable[[], None]
    pause_simulation: Callable[[], None]


class TimelinePanel:
    """Render and control chronological history, scrubbing, and playback."""

    def __init__(self, services: TimelinePanelServices) -> None:
        self.services = services
        self.dragging = False
        self.play_direction = 0
        self.playback_rate = 12.0
        self._playback_accumulator = 0.0

    def stop(self) -> None:
        """Stop timeline playback without affecting simulation state."""
        self.play_direction = 0
        self._playback_accumulator = 0.0

    def update(self, delta_time: float) -> None:
        """Play existing frames forward or backward at a bounded rate."""
        if not self.play_direction:
            return
        self.services.pause_simulation()
        self._playback_accumulator += delta_time
        interval = 1.0 / self.playback_rate
        while self._playback_accumulator >= interval:
            if not self.services.step(self.play_direction):
                self.stop()
                return
            self._playback_accumulator -= interval

    def geometry(
        self,
    ) -> tuple[
        pygame.Rect,
        dict[str, pygame.Rect],
        pygame.Rect,
        pygame.Rect,
    ]:
        """Return panel, control-button, track, and generation-button geometry."""
        panel = self.services.rect()
        button_y = panel.y + 24
        buttons = {
            "back": pygame.Rect(panel.x + 8, button_y, 25, 25),
            "reverse": pygame.Rect(panel.x + 36, button_y, 25, 25),
            "stop": pygame.Rect(panel.x + 64, button_y, 25, 25),
            "forward": pygame.Rect(panel.x + 92, button_y, 25, 25),
            "next": pygame.Rect(panel.x + 120, button_y, 25, 25),
        }
        goto_button = pygame.Rect(panel.right - 93, button_y, 85, 25)
        track_left = buttons["next"].right + 16
        track = pygame.Rect(
            track_left,
            panel.y + 34,
            max(20, goto_button.left - track_left - 14),
            6,
        )
        return panel, buttons, track, goto_button

    def draw(self) -> None:
        """Draw current frame, checkpoint marks, scrubber, and controls."""
        panel, buttons, track, goto_button = self.geometry()
        screen = self.services.screen()
        theme = self.services.theme()
        status = self.services.status()
        pygame.draw.rect(screen, theme["stats_bar"], panel)
        pygame.draw.line(screen, theme["grid"], panel.topleft, panel.topright)

        label = (
            f"Timeline  ·  Generation {status.generation}  ·  "
            f"Frame {status.cursor + 1}/{status.frame_count}  ·  "
            f"{status.checkpoint_count} checkpoints + "
            f"{status.delta_frame_count} deltas"
        )
        screen.blit(
            self.services.tiny_font().render(label, True, theme["text"]),
            (panel.x + 8, panel.y + 5),
        )

        button_labels = {
            "back": "<",
            "reverse": "<<",
            "stop": "||",
            "forward": ">>",
            "next": ">",
        }
        for key, rect in buttons.items():
            active = (
                key == "reverse" and self.play_direction < 0
            ) or (key == "forward" and self.play_direction > 0)
            fill = theme["button_hover"] if active else theme["button"]
            pygame.draw.rect(screen, fill, rect, border_radius=3)
            pygame.draw.rect(screen, theme["button_text"], rect, 1, border_radius=3)
            rendered = self.services.tiny_font().render(
                button_labels[key], True, theme["button_text"]
            )
            screen.blit(rendered, rendered.get_rect(center=rect.center))

        pygame.draw.rect(screen, theme["grid"], track, border_radius=3)
        frame_span = max(1, status.frame_count - 1)
        for checkpoint in status.checkpoints:
            marker_x = track.x + round(checkpoint * track.width / frame_span)
            pygame.draw.line(
                screen,
                theme["text"],
                (marker_x, track.y - 4),
                (marker_x, track.bottom + 4),
                1,
            )
        progress_width = round(max(0, status.cursor) * track.width / frame_span)
        if progress_width:
            pygame.draw.rect(
                screen,
                (70, 170, 255),
                (track.x, track.y, progress_width, track.height),
                border_radius=3,
            )
        handle_x = track.x + progress_width
        pygame.draw.circle(screen, (90, 195, 255), (handle_x, track.centery), 7)
        pygame.draw.circle(screen, theme["text"], (handle_x, track.centery), 7, 1)

        pygame.draw.rect(screen, theme["button"], goto_button, border_radius=3)
        pygame.draw.rect(screen, theme["button_text"], goto_button, 1, border_radius=3)
        goto_text = self.services.tiny_font().render(
            "Go to gen (J)", True, theme["button_text"]
        )
        screen.blit(goto_text, goto_text.get_rect(center=goto_button.center))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Consume pointer events inside the timeline panel."""
        panel, buttons, track, goto_button = self.geometry()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not panel.collidepoint(event.pos):
                return False
            self.services.pause_simulation()
            if buttons["back"].collidepoint(event.pos):
                self.stop()
                self.services.step(-1)
            elif buttons["reverse"].collidepoint(event.pos):
                self.play_direction = -1
                self._playback_accumulator = 0.0
            elif buttons["stop"].collidepoint(event.pos):
                self.stop()
            elif buttons["forward"].collidepoint(event.pos):
                self.play_direction = 1
                self._playback_accumulator = 0.0
            elif buttons["next"].collidepoint(event.pos):
                self.stop()
                self.services.step(1)
            elif goto_button.collidepoint(event.pos):
                self.stop()
                self.services.request_generation()
            elif track.inflate(10, 18).collidepoint(event.pos):
                self.stop()
                self.dragging = True
                self._seek_at_x(event.pos[0], track)
            return True

        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._seek_at_x(event.pos[0], track)
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            self._seek_at_x(event.pos[0], track)
            return True

        return False

    def _seek_at_x(self, mouse_x: int, track: pygame.Rect) -> None:
        status = self.services.status()
        if status.frame_count <= 1:
            return
        ratio = (mouse_x - track.x) / max(1, track.width)
        index = round(max(0.0, min(1.0, ratio)) * (status.frame_count - 1))
        if index != status.cursor:
            self.services.seek(index)
