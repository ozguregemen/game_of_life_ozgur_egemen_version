"""General one-dimensional cellular automata with finite-state rule families."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Literal, TypeAlias

from elementary_ca import (
    BOUNDARY_FIXED,
    BOUNDARY_INFINITE,
    BOUNDARY_MODES,
    BOUNDARY_WRAP,
    DEFAULT_RULE,
    DEFAULT_WIDTH,
)

CellRow: TypeAlias = tuple[int, ...]
TransitionKind = Literal["lookup", "totalistic"]
MemoryMode = Literal["none", "higher", "reversible"]

FAMILY_ELEMENTARY = "elementary"
FAMILY_TOTALISTIC = "totalistic"
FAMILY_MULTISTATE = "multistate"
FAMILY_RADIUS = "extended_radius"
FAMILY_HIGHER_ORDER = "higher_order"
FAMILY_REVERSIBLE = "reversible"
RULE_FAMILIES = (
    FAMILY_ELEMENTARY,
    FAMILY_TOTALISTIC,
    FAMILY_MULTISTATE,
    FAMILY_RADIUS,
    FAMILY_HIGHER_ORDER,
    FAMILY_REVERSIBLE,
)


@dataclass(frozen=True)
class RuleFamilyDefinition:
    """Fixed semantics and user-facing metadata for a 1D rule family."""

    key: str
    name: str
    summary: str
    transition: TransitionKind
    memory: MemoryMode


RULE_FAMILY_DEFINITIONS = (
    RuleFamilyDefinition(
        FAMILY_ELEMENTARY,
        "Elementary",
        "Binary radius-1 Wolfram rules 0-255.",
        "lookup",
        "none",
    ),
    RuleFamilyDefinition(
        FAMILY_TOTALISTIC,
        "Totalistic",
        "The neighborhood sum selects one of k output states.",
        "totalistic",
        "none",
    ),
    RuleFamilyDefinition(
        FAMILY_MULTISTATE,
        "Multi-state",
        "A full radius-1 lookup table with three or four states.",
        "lookup",
        "none",
    ),
    RuleFamilyDefinition(
        FAMILY_RADIUS,
        "Extended Radius",
        "Binary full-table rules with radius 2 or 3.",
        "lookup",
        "none",
    ),
    RuleFamilyDefinition(
        FAMILY_HIGHER_ORDER,
        "Higher-order",
        "The next row also depends on the preceding generation.",
        "lookup",
        "higher",
    ),
    RuleFamilyDefinition(
        FAMILY_REVERSIBLE,
        "Reversible",
        "A second-order lift from which the preceding row is recoverable.",
        "lookup",
        "reversible",
    ),
)
RULE_FAMILY_BY_KEY = {
    definition.key: definition for definition in RULE_FAMILY_DEFINITIONS
}


@dataclass(frozen=True)
class RuleSpec:
    """Serializable definition of a finite-state one-dimensional CA rule."""

    family: str = FAMILY_ELEMENTARY
    code: int = DEFAULT_RULE
    states: int = 2
    radius: int = 1

    def __post_init__(self) -> None:
        if self.family not in RULE_FAMILY_BY_KEY:
            raise ValueError(f"Unknown 1D rule family: {self.family}")
        if isinstance(self.states, bool) or not isinstance(self.states, int):
            raise TypeError("State count must be an integer.")
        if isinstance(self.radius, bool) or not isinstance(self.radius, int):
            raise TypeError("Radius must be an integer.")
        if isinstance(self.code, bool) or not isinstance(self.code, int):
            raise TypeError("Rule code must be an integer.")
        if not 2 <= self.states <= 4:
            raise ValueError("State count must be between 2 and 4.")
        if not 1 <= self.radius <= 3:
            raise ValueError("Radius must be between 1 and 3.")

        if self.family == FAMILY_ELEMENTARY and (
            self.states != 2 or self.radius != 1
        ):
            raise ValueError("Elementary rules require two states and radius 1.")
        if self.family == FAMILY_MULTISTATE and (
            self.states < 3 or self.radius != 1
        ):
            raise ValueError("Multi-state rules require 3-4 states and radius 1.")
        if self.family == FAMILY_RADIUS and (
            self.states != 2 or self.radius < 2
        ):
            raise ValueError("Extended-radius rules require two states and radius 2-3.")
        if self.family in (FAMILY_HIGHER_ORDER, FAMILY_REVERSIBLE) and (
            self.states != 2 or self.radius != 1
        ):
            raise ValueError(
                "Higher-order and reversible presets require two states and radius 1."
            )
        if self.code < 0 or self.code > self.max_code:
            raise ValueError(
                f"Rule code must be between 0 and {self.max_code} for this family."
            )

    @property
    def definition(self) -> RuleFamilyDefinition:
        return RULE_FAMILY_BY_KEY[self.family]

    @property
    def transition(self) -> TransitionKind:
        return self.definition.transition

    @property
    def memory(self) -> MemoryMode:
        return self.definition.memory

    @property
    def neighborhood_width(self) -> int:
        return self.radius * 2 + 1

    @property
    def output_count(self) -> int:
        if self.transition == "totalistic":
            return (self.states - 1) * self.neighborhood_width + 1
        return self.states ** self.neighborhood_width

    @property
    def max_code(self) -> int:
        return self.states ** self.output_count - 1

    @property
    def label(self) -> str:
        return f"{self.definition.name} code {self.code}"

    def with_code(self, code: int) -> RuleSpec:
        return replace(self, code=code)

    def as_dict(self) -> dict[str, int | str]:
        return {
            "family": self.family,
            "code": self.code,
            "states": self.states,
            "radius": self.radius,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> RuleSpec:
        return cls(
            family=str(value["family"]),
            code=int(value["code"]),
            states=int(value["states"]),
            radius=int(value["radius"]),
        )


def normalize_state_row(values: Iterable[int], states: int) -> CellRow:
    """Validate and freeze a non-empty row whose values fit ``states``."""

    if isinstance(states, bool) or not isinstance(states, int) or states < 2:
        raise ValueError("states must be an integer of at least two")
    row = tuple(values)
    if not row:
        raise ValueError("A one-dimensional automaton row cannot be empty.")
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < states
        for value in row
    ):
        raise ValueError(f"Cell states must be integers from 0 to {states - 1}.")
    return row


def decode_neighborhood(index: int, width: int, states: int) -> CellRow:
    """Decode a base-k lookup index with the leftmost cell most significant."""

    digits = [0] * width
    remaining = index
    for position in range(width - 1, -1, -1):
        digits[position] = remaining % states
        remaining //= states
    return tuple(digits)


def encode_lookup_rule(
    states: int,
    radius: int,
    transition: Callable[[CellRow], int],
) -> int:
    """Encode an explicit neighborhood function as a base-k rule integer."""

    width = radius * 2 + 1
    code = 0
    for index in range(states**width):
        neighborhood = decode_neighborhood(index, width, states)
        output = transition(neighborhood)
        if isinstance(output, bool) or not isinstance(output, int):
            raise TypeError("Transition outputs must be integers.")
        if not 0 <= output < states:
            raise ValueError("Transition output does not fit the state count.")
        code += output * (states**index)
    return code


def encode_totalistic_rule(
    states: int,
    radius: int,
    transition: Callable[[int], int],
) -> int:
    """Encode a neighborhood-sum function as a base-k rule integer."""

    maximum_sum = (states - 1) * (radius * 2 + 1)
    code = 0
    for total in range(maximum_sum + 1):
        output = transition(total)
        if isinstance(output, bool) or not isinstance(output, int):
            raise TypeError("Transition outputs must be integers.")
        if not 0 <= output < states:
            raise ValueError("Transition output does not fit the state count.")
        code += output * (states**total)
    return code


def default_rule_spec(
    family: str = FAMILY_ELEMENTARY,
    *,
    states: int | None = None,
    radius: int | None = None,
) -> RuleSpec:
    """Return a deterministic, visually useful preset for a rule family."""

    if family == FAMILY_ELEMENTARY:
        return RuleSpec(family, DEFAULT_RULE, 2, 1)
    if family == FAMILY_TOTALISTIC:
        state_count = states or 2
        rule_radius = radius or 1
        code = encode_totalistic_rule(
            state_count,
            rule_radius,
            lambda total: total % state_count,
        )
        return RuleSpec(family, code, state_count, rule_radius)
    if family == FAMILY_MULTISTATE:
        state_count = states or 3
        code = encode_lookup_rule(
            state_count,
            1,
            lambda neighborhood: sum(neighborhood) % state_count,
        )
        return RuleSpec(family, code, state_count, 1)
    if family == FAMILY_RADIUS:
        rule_radius = radius or 2
        code = encode_lookup_rule(
            2,
            rule_radius,
            lambda neighborhood: sum(neighborhood) % 2,
        )
        return RuleSpec(family, code, 2, rule_radius)
    if family == FAMILY_HIGHER_ORDER:
        return RuleSpec(family, 90, 2, 1)
    if family == FAMILY_REVERSIBLE:
        return RuleSpec(family, 150, 2, 1)
    raise ValueError(f"Unknown 1D rule family: {family}")


def transition_output(spec: RuleSpec, neighborhood: CellRow) -> int:
    """Return the first-order output selected by the rule code."""

    if len(neighborhood) != spec.neighborhood_width:
        raise ValueError(
            f"Neighborhood must contain {spec.neighborhood_width} cells."
        )
    normalized = normalize_state_row(neighborhood, spec.states)
    if spec.transition == "totalistic":
        index = sum(normalized)
    else:
        index = 0
        for value in normalized:
            index = index * spec.states + value
    return (spec.code // (spec.states**index)) % spec.states


def _cell_at(
    row: CellRow,
    index: int,
    *,
    boundary: str,
    background: int,
) -> int:
    if 0 <= index < len(row):
        return row[index]
    if boundary == BOUNDARY_WRAP:
        return row[index % len(row)]
    return background if boundary == BOUNDARY_INFINITE else 0


def step_one_dimensional(
    row: Iterable[int],
    spec: RuleSpec,
    *,
    boundary: str = BOUNDARY_INFINITE,
    background: int = 0,
    previous_row: Iterable[int] | None = None,
) -> CellRow:
    """Advance one row for lookup, totalistic, and second-order rule families."""

    if boundary not in BOUNDARY_MODES:
        raise ValueError(f"Unknown boundary mode: {boundary}")
    current = normalize_state_row(row, spec.states)
    if not 0 <= background < spec.states:
        raise ValueError("Background state does not fit the rule state count.")
    previous = (
        tuple(0 for _ in current)
        if previous_row is None
        else normalize_state_row(previous_row, spec.states)
    )
    if len(previous) != len(current):
        raise ValueError("previous_row must have the same width as row")

    result: list[int] = []
    for index in range(len(current)):
        neighborhood = tuple(
            _cell_at(
                current,
                index + offset,
                boundary=boundary,
                background=background,
            )
            for offset in range(-spec.radius, spec.radius + 1)
        )
        base = transition_output(spec, neighborhood)
        if spec.memory == "higher":
            output = (base + current[index] * previous[index]) % spec.states
        elif spec.memory == "reversible":
            output = (base - previous[index]) % spec.states
        else:
            output = base
        result.append(output)
    return tuple(result)


def next_uniform_background(
    spec: RuleSpec,
    background: int,
    *,
    previous_background: int = 0,
) -> int:
    """Evolve an infinite uniform background, including second-order memory."""

    if not 0 <= background < spec.states:
        raise ValueError("Background state does not fit the rule state count.")
    if not 0 <= previous_background < spec.states:
        raise ValueError("Previous background does not fit the rule state count.")
    base = transition_output(
        spec,
        tuple(background for _ in range(spec.neighborhood_width)),
    )
    if spec.memory == "higher":
        return (base + background * previous_background) % spec.states
    if spec.memory == "reversible":
        return (base - previous_background) % spec.states
    return base


def reverse_reversible_step(
    current_row: Iterable[int],
    next_row: Iterable[int],
    spec: RuleSpec,
    *,
    boundary: str = BOUNDARY_INFINITE,
    background: int = 0,
) -> CellRow:
    """Recover the preceding row of a reversible second-order trajectory."""

    if spec.memory != "reversible":
        raise ValueError("Rule spec is not a reversible second-order rule.")
    current = normalize_state_row(current_row, spec.states)
    following = normalize_state_row(next_row, spec.states)
    if len(current) != len(following):
        raise ValueError("current_row and next_row must have equal width")
    first_order = step_one_dimensional(
        current,
        replace(spec, family=FAMILY_ELEMENTARY),
        boundary=boundary,
        background=background,
    )
    return tuple(
        (base - following[index]) % spec.states
        for index, base in enumerate(first_order)
    )


def single_state_seed(
    width: int = DEFAULT_WIDTH,
    *,
    states: int = 2,
    value: int = 1,
) -> CellRow:
    """Create a centered non-zero seed for an arbitrary finite state count."""

    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("Seed width must be a positive integer.")
    if not 2 <= states <= 4 or not 0 < value < states:
        raise ValueError("Seed value must be a non-zero valid state.")
    seed = [0] * width
    seed[width // 2] = value
    return tuple(seed)


def random_state_seed(
    width: int = DEFAULT_WIDTH,
    *,
    states: int = 2,
    density: float = 0.20,
    rng: random.Random | None = None,
) -> CellRow:
    """Create a random seed with uniformly selected non-zero states."""

    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("Seed width must be a positive integer.")
    if not 2 <= states <= 4:
        raise ValueError("State count must be between 2 and 4.")
    if not 0.0 <= density <= 1.0:
        raise ValueError("Seed density must be between 0 and 1.")
    generator = rng or random
    return tuple(
        generator.randrange(1, states) if generator.random() < density else 0
        for _ in range(width)
    )


def row_statistics(row: Iterable[int], states: int) -> dict[str, float | int]:
    """Return non-zero population, density, and occupied state diversity."""

    current = normalize_state_row(row, states)
    active = sum(value != 0 for value in current)
    return {
        "active": active,
        "inactive": len(current) - active,
        "density": 100.0 * active / len(current),
        "diversity": len(set(current)),
    }


def short_rule_code(code: int, maximum_characters: int = 16) -> str:
    """Format potentially huge rule integers for compact UI labels."""

    text = str(code)
    if len(text) <= maximum_characters:
        return text
    side = max(3, (maximum_characters - 3) // 2)
    return f"{text[:side]}...{text[-side:]}"
