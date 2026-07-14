"""Common contracts for dimension-level simulation workspaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

import pygame

from scientific_analysis import StateObservation
from themes import Menu
from timeline_history import TimelineStatus


class WorkspaceController(ABC):
    """Own simulation state, commands, history, and input for one dimension."""

    key: str

    def activate(self) -> None:
        """Prepare this workspace to receive input."""

    def deactivate(self) -> None:
        """Close transient controls when another workspace becomes active."""

    @property
    def overlay_active(self) -> bool:
        """Return whether a workspace-specific modal currently owns input."""
        return False

    @property
    @abstractmethod
    def generation(self) -> int:
        """Return the current generation or step counter."""

    @abstractmethod
    def advance(self) -> bool:
        """Advance the active simulation by one generation or step."""

    @abstractmethod
    def save_history(self) -> None:
        """Mark the beginning of a logical state mutation."""

    @abstractmethod
    def step_back(self) -> None:
        """Restore the preceding timeline frame when available."""

    @abstractmethod
    def step_forward(self) -> None:
        """Restore the next existing history frame when available."""

    @abstractmethod
    def seek_history(self, index: int) -> bool:
        """Restore a chronological history frame by its timeline index."""

    @abstractmethod
    def seek_generation(self, generation: int) -> bool:
        """Restore the most recent frame with an exact generation label."""

    @abstractmethod
    def sync_history(self) -> bool:
        """Commit a pending workspace mutation to its timeline."""

    @abstractmethod
    def history_status(self) -> TimelineStatus:
        """Return timeline navigation and storage information."""

    @abstractmethod
    def reset_history(self) -> None:
        """Discard timeline frames and checkpoint the current state."""

    @abstractmethod
    def analysis_observation(self) -> StateObservation:
        """Return normalized state for scientific measurement."""

    @abstractmethod
    def clear(self) -> None:
        """Reset the active simulation to its empty/default state."""

    @abstractmethod
    def randomize(self, density: float = 0.20) -> None:
        """Create a random initial condition."""

    @abstractmethod
    def snapshot(self) -> dict[str, Any]:
        """Return JSON-compatible persistent workspace state."""

    @abstractmethod
    def restore(self, snapshot: Mapping[str, Any]) -> None:
        """Replace workspace state from a validated snapshot."""

    @abstractmethod
    def build_sidebar(self, menu: Menu) -> None:
        """Populate the contextual sidebar for this workspace."""

    def handle_overlay_event(self, event: pygame.event.Event) -> bool:
        """Handle an event while a workspace modal is open."""
        return False

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        """Handle a workspace-specific key and report whether it was consumed."""
        return False

    def handle_pointer_event(self, event: pygame.event.Event) -> bool:
        """Handle workspace drawing, panning, or other pointer input."""
        return False

    @abstractmethod
    def center_view(self) -> None:
        """Center the workspace content in its viewport."""

    @abstractmethod
    def zoom(self, factor: float) -> None:
        """Scale the workspace view by a multiplicative factor."""


class WorkspaceRenderer(ABC):
    """Draw one workspace without owning its simulation rules."""

    render_key: str

    @property
    def cache_identity(self) -> str:
        """Return the key used by application render and statistics caches."""
        return self.render_key

    @abstractmethod
    def cache_key(self) -> tuple[Any, ...]:
        """Return all visual state that determines cached viewport pixels."""

    @abstractmethod
    def draw_base(self) -> None:
        """Draw the cacheable viewport layer."""

    def draw_dynamic(self) -> None:
        """Draw uncached viewport content such as previews."""

    @abstractmethod
    def draw_bars(self) -> None:
        """Draw the top information and bottom statistics bars."""

    def draw_decorations(self) -> None:
        """Draw non-modal workspace UI above the sidebar."""

    def draw_modal(self) -> None:
        """Draw a workspace-specific modal above status messages."""

    @property
    def transition_active(self) -> bool:
        """Return whether the viewport contains frame-by-frame animation."""
        return False


@dataclass(frozen=True)
class WorkspaceBundle:
    """Pair the controller and renderer for one registered dimension."""

    controller: WorkspaceController
    renderer: WorkspaceRenderer

    def __post_init__(self) -> None:
        if self.controller.key != self.renderer.render_key.split(":", 1)[0]:
            # Render keys may use ``dimension:variant`` but must share the prefix.
            raise ValueError("Workspace controller and renderer keys do not match.")


class WorkspaceRegistry:
    """Store available workspace bundles by dimension key."""

    def __init__(self) -> None:
        self._workspaces: dict[str, WorkspaceBundle] = {}

    def register(self, workspace: WorkspaceBundle) -> None:
        key = workspace.controller.key
        if key in self._workspaces:
            raise ValueError(f"Workspace already registered: {key}")
        self._workspaces[key] = workspace

    def get(self, key: str) -> WorkspaceBundle:
        try:
            return self._workspaces[key]
        except KeyError as exc:
            raise ValueError(f"Unknown workspace: {key}") from exc

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self._workspaces)
