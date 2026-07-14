"""Adapters that expose the established 2D application through workspace contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import pygame

from themes import Menu
from timeline_history import TimelineStatus
from workspaces.base import WorkspaceController, WorkspaceRenderer


@dataclass(frozen=True)
class TwoDimensionalControllerCallbacks:
    """Application callbacks needed by the 2D workspace controller."""

    generation: Callable[[], int]
    advance: Callable[[], bool]
    save_history: Callable[[], None]
    step_back: Callable[[], None]
    step_forward: Callable[[], None]
    seek_history: Callable[[int], bool]
    seek_generation: Callable[[int], bool]
    sync_history: Callable[[], bool]
    history_status: Callable[[], TimelineStatus]
    reset_history: Callable[[], None]
    clear: Callable[[], None]
    randomize: Callable[[float], None]
    snapshot: Callable[[], dict[str, Any]]
    restore: Callable[[Mapping[str, Any]], None]
    build_sidebar: Callable[[Menu], None]
    overlay_active: Callable[[], bool]
    close_overlays: Callable[[], None]
    handle_overlay_event: Callable[[pygame.event.Event], bool]
    handle_keydown: Callable[[pygame.event.Event], bool]
    handle_pointer_event: Callable[[pygame.event.Event], bool]
    center_view: Callable[[], None]
    zoom: Callable[[float], None]


class TwoDimensionalWorkspaceController(WorkspaceController):
    """Coordinate all registered 2D modes behind one dimension interface."""

    key = "2d"

    def __init__(self, callbacks: TwoDimensionalControllerCallbacks) -> None:
        self.callbacks = callbacks

    def activate(self) -> None:
        self.callbacks.center_view()

    def deactivate(self) -> None:
        self.callbacks.close_overlays()

    @property
    def overlay_active(self) -> bool:
        return self.callbacks.overlay_active()

    @property
    def generation(self) -> int:
        return self.callbacks.generation()

    def advance(self) -> bool:
        return self.callbacks.advance()

    def save_history(self) -> None:
        self.callbacks.save_history()

    def step_back(self) -> None:
        self.callbacks.step_back()

    def step_forward(self) -> None:
        self.callbacks.step_forward()

    def seek_history(self, index: int) -> bool:
        return self.callbacks.seek_history(index)

    def seek_generation(self, generation: int) -> bool:
        return self.callbacks.seek_generation(generation)

    def sync_history(self) -> bool:
        return self.callbacks.sync_history()

    def history_status(self) -> TimelineStatus:
        return self.callbacks.history_status()

    def reset_history(self) -> None:
        self.callbacks.reset_history()

    def clear(self) -> None:
        self.callbacks.clear()
        self.callbacks.sync_history()

    def randomize(self, density: float = 0.20) -> None:
        self.callbacks.randomize(density)
        self.callbacks.sync_history()

    def snapshot(self) -> dict[str, Any]:
        return self.callbacks.snapshot()

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        self.callbacks.restore(snapshot)

    def build_sidebar(self, menu: Menu) -> None:
        self.callbacks.build_sidebar(menu)

    def handle_overlay_event(self, event: pygame.event.Event) -> bool:
        return self.callbacks.handle_overlay_event(event)

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        return self.callbacks.handle_keydown(event)

    def handle_pointer_event(self, event: pygame.event.Event) -> bool:
        return self.callbacks.handle_pointer_event(event)

    def center_view(self) -> None:
        self.callbacks.center_view()

    def zoom(self, factor: float) -> None:
        self.callbacks.zoom(factor)


@dataclass(frozen=True)
class TwoDimensionalRendererCallbacks:
    """Drawing callbacks supplied by the existing 2D mode implementation."""

    render_key: Callable[[], str]
    cache_key: Callable[[], tuple[Any, ...]]
    draw_base: Callable[[], None]
    draw_dynamic: Callable[[], None]
    draw_bars: Callable[[], None]
    draw_decorations: Callable[[], None]
    draw_modal: Callable[[], None]
    transition_active: Callable[[], bool]


class TwoDimensionalWorkspaceRenderer(WorkspaceRenderer):
    """Render the selected 2D mode through the shared workspace pipeline."""

    render_key = "2d"

    def __init__(self, callbacks: TwoDimensionalRendererCallbacks) -> None:
        self.callbacks = callbacks

    @property
    def cache_identity(self) -> str:
        return self.callbacks.render_key()

    def cache_key(self) -> tuple[Any, ...]:
        return self.callbacks.cache_key()

    def draw_base(self) -> None:
        self.callbacks.draw_base()

    def draw_dynamic(self) -> None:
        self.callbacks.draw_dynamic()

    def draw_bars(self) -> None:
        self.callbacks.draw_bars()

    def draw_decorations(self) -> None:
        self.callbacks.draw_decorations()

    def draw_modal(self) -> None:
        self.callbacks.draw_modal()

    @property
    def transition_active(self) -> bool:
        return self.callbacks.transition_active()
