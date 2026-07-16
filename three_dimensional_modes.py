"""Mode and rule registry shared by the complete 3D workspace."""

from __future__ import annotations

from types import MappingProxyType
from typing import TypeAlias

from three_dimensional_generations import (
    DEFAULT_GENERATIONS_RULE_3D,
    GENERATIONS_RULES_3D,
    GenerationsRule3D,
)
from three_dimensional_rules import DEFAULT_RULE_3D, RULES_3D, LifeLikeRule3D

MODE_SPATIAL_LIFE = "spatial_life"
MODE_GENERATIONS = "generations"
MODE_KEYS_3D = (MODE_SPATIAL_LIFE, MODE_GENERATIONS)
MODE_LABELS_3D = MappingProxyType(
    {
        MODE_SPATIAL_LIFE: "Spatial Life",
        MODE_GENERATIONS: "3D Generations",
    }
)

Rule3D: TypeAlias = LifeLikeRule3D | GenerationsRule3D
RULES_BY_MODE_3D = MappingProxyType(
    {
        MODE_SPATIAL_LIFE: RULES_3D,
        MODE_GENERATIONS: GENERATIONS_RULES_3D,
    }
)
DEFAULT_RULE_BY_MODE_3D = MappingProxyType(
    {
        MODE_SPATIAL_LIFE: DEFAULT_RULE_3D,
        MODE_GENERATIONS: DEFAULT_GENERATIONS_RULE_3D,
    }
)
ALL_RULES_3D = MappingProxyType(
    {
        key: rule
        for registry in RULES_BY_MODE_3D.values()
        for key, rule in registry.items()
    }
)
ALL_RULE_KEYS_3D = tuple(ALL_RULES_3D)


def mode_for_rule(rule_key: str) -> str:
    """Return the owning mode for one registered rule key."""
    for mode, registry in RULES_BY_MODE_3D.items():
        if rule_key in registry:
            return mode
    raise KeyError(f"Unknown 3D rule: {rule_key}")


def rule_state_count(rule: Rule3D) -> int:
    """Return the state count required by a registered 3D rule."""
    return rule.state_count if isinstance(rule, GenerationsRule3D) else 2
