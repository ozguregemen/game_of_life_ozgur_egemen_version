"""Metadata registry for the application's simulation modes."""

from __future__ import annotations

from dataclasses import dataclass

Color = tuple[int, int, int]


@dataclass(frozen=True)
class ModeDefinition:
    """User-facing metadata and contextual actions for one simulation mode."""

    key: str
    name: str
    summary: str
    accent: Color
    contextual_actions: tuple[str, ...]
    status_hint: str


MODE_DEFINITIONS = (
    ModeDefinition(
        key="life",
        name="Life-like",
        summary="Conway, HighLife, Day & Night, and Seeds birth/survival rules.",
        accent=(80, 220, 105),
        contextual_actions=("change_rule", "toggle_heatmap", "toggle_ages"),
        status_hint="Choose rules, draw cells, and inspect recurring patterns.",
    ),
    ModeDefinition(
        key="immigration",
        name="Immigration Game",
        summary="Two species compete while following Conway's B3/S23 rules.",
        accent=(55, 175, 255),
        contextual_actions=("species_a", "species_b", "toggle_ages"),
        status_hint="Choose a species brush; births inherit the local majority.",
    ),
    ModeDefinition(
        key="brians_brain",
        name="Brian's Brain",
        summary="Three-state waves move through off, firing, and dying cells.",
        accent=(80, 235, 255),
        contextual_actions=(),
        status_hint="Draw firing cells and watch their one-step dying trails.",
    ),
    ModeDefinition(
        key="langtons_ant",
        name="Langton's Ant",
        summary="A directional agent turns, flips cells, and builds complex trails.",
        accent=(235, 70, 75),
        contextual_actions=("rotate_ant",),
        status_hint="Rotate with T or move the ant with Shift + left click.",
    ),
    ModeDefinition(
        key="wireworld",
        name="Wireworld",
        summary="Electron heads and tails carry signals through conductor circuits.",
        accent=(245, 190, 35),
        contextual_actions=("wire_conductor", "wire_head", "wire_tail"),
        status_hint="Choose a circuit brush and propagate electron signals.",
    ),
    ModeDefinition(
        key="cyclic_automaton",
        name="Cyclic Cellular Automaton",
        summary="Colors consume their predecessor and self-organize into waves.",
        accent=(195, 80, 245),
        contextual_actions=("cyclic_brush", "cyclic_threshold"),
        status_hint="Randomize, tune the threshold, and watch color fronts organize.",
    ),
)

MODE_BY_KEY = {definition.key: definition for definition in MODE_DEFINITIONS}
MODE_KEYS = tuple(MODE_BY_KEY)


def get_mode_definition(key: str) -> ModeDefinition:
    """Return one registered mode or raise a clear error for an unknown key."""
    try:
        return MODE_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f"Unknown simulation mode: {key}") from exc
