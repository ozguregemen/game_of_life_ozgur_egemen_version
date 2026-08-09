"""Owned state, simulation lifecycle, and rendering bridge for the 2D lab."""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import pygame

from custom_rules import CustomRuleDefinition, custom_rule_from_document
from brians_brain import (
    DYING,
    FIRING,
    BrainGrid,
    apply_brain_rules,
    make_brain_grid,
    randomize_brain_grid,
)
from cyclic_automaton import (
    DEFAULT_STATE_COUNT as CYCLIC_STATE_COUNT,
    CyclicGrid,
    apply_cyclic_rules,
    make_cyclic_grid,
    randomize_cyclic_grid,
)
from immigration import (
    SPECIES_A,
    SPECIES_B,
    ImmigrationGrid,
    apply_immigration_rules,
    make_immigration_grid,
    randomize_immigration_grid,
)
from langtons_ant import (
    BLACK as ANT_BLACK,
    AntGrid,
    AntState,
    AntStepReport,
    centered_ant,
    make_ant_grid,
    randomize_ant_grid,
    step_ant,
)
from mode_registry import MODE_BY_KEY, MODE_KEYS
from rng_state import encode_random_state, restore_random_state, seeded_random
from rules import RULES, apply_rules_2d
from scientific_analysis import StateObservation
from themes import Menu
from timeline_history import TimelineBinding, TimelineStatus
from wireworld import (
    CONDUCTOR,
    ELECTRON_HEAD,
    ELECTRON_TAIL,
    WireworldGrid,
    apply_wireworld_rules,
    make_wireworld_grid,
    randomize_wireworld_grid,
)
from workspaces.base import WorkspaceController, WorkspaceRenderer

Grid = list[list[int]]
FloatGrid = list[list[float]]


def _integer_grid(rows: int, columns: int, value: int = 0) -> Grid:
    return [[value for _ in range(columns)] for _ in range(rows)]


def _float_grid(rows: int, columns: int) -> FloatGrid:
    return [[0.0 for _ in range(columns)] for _ in range(rows)]


@dataclass
class LifeModeState:
    """Conway-family state, including visualization-derived grids."""

    grid: Grid
    trail: Grid
    activity: FloatGrid
    rng: random.Random
    rule: str = "conway"
    generation: int = 0
    custom_rule: CustomRuleDefinition | None = None


@dataclass
class ImmigrationModeState:
    grid: ImmigrationGrid
    rng: random.Random
    generation: int = 0
    active_species: int = SPECIES_A


@dataclass
class BrainModeState:
    grid: BrainGrid
    rng: random.Random
    generation: int = 0


@dataclass
class AntModeState:
    grid: AntGrid
    ant: AntState
    rng: random.Random
    generation: int = 0
    last_report: AntStepReport = AntStepReport()


@dataclass
class WireworldModeState:
    grid: WireworldGrid
    rng: random.Random
    generation: int = 0
    brush: int = CONDUCTOR


@dataclass
class CyclicModeState:
    grid: CyclicGrid
    rng: random.Random
    generation: int = 0
    brush: int = 1
    threshold: int = 1


@dataclass
class TwoDimensionalWorkspaceState:
    """All persistent 2D model and camera state under one owner."""

    rows: int
    columns: int
    cell_size: int
    life: LifeModeState
    immigration: ImmigrationModeState
    brain: BrainModeState
    ant: AntModeState
    wireworld: WireworldModeState
    cyclic: CyclicModeState
    view_offset_x: int = 0
    view_offset_y: int = 0

    @classmethod
    def create(
        cls,
        rows: int,
        columns: int,
        cell_size: int,
        master_seed: int,
        *,
        cyclic_threshold: int,
    ) -> "TwoDimensionalWorkspaceState":
        return cls(
            rows=rows,
            columns=columns,
            cell_size=cell_size,
            life=LifeModeState(
                _integer_grid(rows, columns),
                _integer_grid(rows, columns),
                _float_grid(rows, columns),
                seeded_random(master_seed, "2d:life"),
            ),
            immigration=ImmigrationModeState(
                make_immigration_grid(rows, columns),
                seeded_random(master_seed, "2d:immigration"),
            ),
            brain=BrainModeState(
                make_brain_grid(rows, columns),
                seeded_random(master_seed, "2d:brians_brain"),
            ),
            ant=AntModeState(
                make_ant_grid(rows, columns),
                centered_ant(rows, columns),
                seeded_random(master_seed, "2d:langtons_ant"),
            ),
            wireworld=WireworldModeState(
                make_wireworld_grid(rows, columns),
                seeded_random(master_seed, "2d:wireworld"),
            ),
            cyclic=CyclicModeState(
                make_cyclic_grid(rows, columns),
                seeded_random(master_seed, "2d:cyclic_automaton"),
                threshold=cyclic_threshold,
            ),
        )

    def mode_state(self, mode: str) -> object:
        return {
            "life": self.life,
            "immigration": self.immigration,
            "brians_brain": self.brain,
            "langtons_ant": self.ant,
            "wireworld": self.wireworld,
            "cyclic_automaton": self.cyclic,
        }[mode]


@dataclass(frozen=True)
class TwoDimensionalWorkspaceServices:
    """UI/application services consumed by the independent 2D controller."""

    active_mode: Callable[[], str]
    is_running: Callable[[], bool]
    set_running: Callable[[bool], None]
    set_status: Callable[[str, float], None]
    invalidate: Callable[[str], None]
    mark_life_dirty: Callable[[], None]
    start_transition: Callable[[int, int, int, int], None]
    clear_transitions: Callable[[], None]
    before_operation: Callable[[], None]
    state_changed: Callable[[], None]
    rebuild_sidebar: Callable[[], None]
    build_sidebar: Callable[[Menu], None]
    overlay_active: Callable[[], bool]
    close_overlays: Callable[[], None]
    handle_overlay_event: Callable[[pygame.event.Event], bool]
    handle_keydown: Callable[[pygame.event.Event], bool]
    handle_pointer_event: Callable[[pygame.event.Event], bool]
    center_view: Callable[[], None]
    zoom: Callable[[float], None]
    record_analysis: Callable[[StateObservation], object]
    reset_analysis: Callable[[StateObservation], object]
    timeline_max_frames: int
    trail_max: int


class TwoDimensionalWorkspaceController(WorkspaceController):
    """Own all six 2D simulations, histories, analysis samples, and sessions."""

    key = "2d"

    def __init__(
        self,
        services: TwoDimensionalWorkspaceServices,
        state: TwoDimensionalWorkspaceState,
    ) -> None:
        self.services = services
        self.state = state
        self.timelines = {
            mode: TimelineBinding(
                lambda mode=mode: self._snapshot_mode(mode),
                lambda snapshot, mode=mode: self._restore_mode(mode, snapshot),
                lambda mode=mode: self.generation_for(mode),
                max_frames=services.timeline_max_frames,
            )
            for mode in MODE_KEYS
        }

    @property
    def mode(self) -> str:
        return self.services.active_mode()

    def activate(self) -> None:
        self.center_view()

    def deactivate(self) -> None:
        self.close_overlays()

    @property
    def overlay_active(self) -> bool:
        return self.services.overlay_active()

    @property
    def generation(self) -> int:
        self.services.before_operation()
        return self.generation_for(self.mode)

    def generation_for(self, mode: str) -> int:
        return int(getattr(self.state.mode_state(mode), "generation"))

    def grid_for(self, mode: str) -> Grid:
        return getattr(self.state.mode_state(mode), "grid")

    def _status(self, message: str, duration: float = 2.0) -> None:
        self.services.set_status(message, duration)

    def save_history(self) -> None:
        self.services.before_operation()
        self.timelines[self.mode].prepare_change()

    def _step(self, amount: int) -> None:
        if not self.timelines[self.mode].step(amount):
            direction = "earlier" if amount < 0 else "later"
            self._status(f"No {direction} {MODE_BY_KEY[self.mode].name} state is available.")
            return
        self.services.set_running(False)
        self._status(f"Timeline generation: {self.generation}.")

    def step_back(self) -> None:
        self._step(-1)

    def step_forward(self) -> None:
        self._step(1)

    def seek_history(self, index: int) -> bool:
        moved = self.timelines[self.mode].seek(index)
        if moved:
            self.services.set_running(False)
        return moved

    def seek_generation(self, generation: int) -> bool:
        moved = self.timelines[self.mode].seek_generation(generation)
        if moved:
            self.services.set_running(False)
        return moved

    def sync_history(self) -> bool:
        self.services.before_operation()
        recorded = self.timelines[self.mode].sync()
        if recorded:
            self.services.record_analysis(self.analysis_observation())
        return recorded

    def history_status(self) -> TimelineStatus:
        return self.timelines[self.mode].status()

    def reset_history(self) -> None:
        self.services.before_operation()
        self.timelines[self.mode].reset()
        self.services.reset_analysis(self.analysis_observation())

    def reset_all_histories(self) -> None:
        for mode, binding in self.timelines.items():
            binding.reset()
            self.services.reset_analysis(self.analysis_observation(mode))

    def apply_custom_life_rule(self, rule: CustomRuleDefinition) -> None:
        """Activate one validated 2D Life-like rule without altering its grid."""

        if rule.dimension != "2d":
            raise ValueError("Custom rule does not belong to the 2D workspace.")
        rule.life_like_2d()
        state = self.state.life
        if state.custom_rule is not None and state.custom_rule.key == rule.key:
            self._status(f"Custom rule '{rule.name}' is already active.")
            return
        self.services.before_operation()
        self.timelines["life"].prepare_change()
        state.rule = rule.key
        state.custom_rule = rule
        self.services.set_running(False)
        self.services.mark_life_dirty()
        self.services.state_changed()
        self.timelines["life"].sync()
        self.services.rebuild_sidebar()
        self._status(f"Custom 2D rule: {rule.name} · {rule.notation}.", 5.0)

    def set_builtin_life_rule(self, rule_key: str) -> None:
        """Activate one built-in Life-like rule and clear custom metadata."""

        if rule_key not in RULES:
            raise ValueError(f"Unknown built-in Life-like rule: {rule_key}")
        state = self.state.life
        if state.rule == rule_key and state.custom_rule is None:
            return
        self.services.before_operation()
        self.timelines["life"].prepare_change()
        state.rule = rule_key
        state.custom_rule = None
        self.services.set_running(False)
        self.services.mark_life_dirty()
        self.services.state_changed()
        self.timelines["life"].sync()
        self.services.rebuild_sidebar()

    def set_life_cell(self, row: int, column: int, value: int) -> bool:
        life = self.state.life
        old_value = life.grid[row][column]
        if old_value == value:
            return False
        life.grid[row][column] = value
        if (old_value > 0) != (value > 0):
            self.services.start_transition(row, column, old_value, value)
        self.services.mark_life_dirty()
        return True

    def draw_cell(
        self,
        row: int,
        column: int,
        drawing_value: int,
        *,
        begin_history: bool,
    ) -> bool:
        """Apply the active mode brush and report whether a cell changed."""
        self.services.before_operation()
        mode = self.mode
        state = self.state.mode_state(mode)
        if mode == "cyclic_automaton":
            target = self.state.cyclic.brush if drawing_value else 0
        elif mode == "wireworld":
            target = self.state.wireworld.brush if drawing_value else 0
        elif mode == "langtons_ant":
            target = ANT_BLACK if drawing_value else 0
        elif mode == "brians_brain":
            target = FIRING if drawing_value else 0
        elif mode == "immigration":
            target = self.state.immigration.active_species if drawing_value else 0
        else:
            target = drawing_value
        grid = getattr(state, "grid")
        comparable = grid[row][column]
        if mode == "immigration":
            comparable = 1 if comparable > 0 else -1 if comparable < 0 else 0
        if comparable == target:
            return False
        if begin_history:
            self.save_history()
        if mode == "life":
            self.set_life_cell(row, column, target)
        else:
            grid[row][column] = target
            self.services.invalidate(mode)
        self.services.state_changed()
        return True

    def current_pattern_cell(self, row: int, column: int) -> int:
        self.services.before_operation()
        mode = self.mode
        value = self.grid_for(mode)[row][column]
        if mode == "immigration":
            return 1 if value > 0 else -1 if value < 0 else 0
        if mode == "life":
            return 1 if value > 0 else 0
        return value

    def set_pattern_cell(self, row: int, column: int, value: int) -> None:
        if self.mode == "life":
            self.set_life_cell(row, column, value)
        else:
            self.grid_for(self.mode)[row][column] = value
            self.services.invalidate(self.mode)
        self.services.state_changed()

    def set_active_species(self, species: int) -> None:
        if species not in (SPECIES_A, SPECIES_B):
            raise ValueError("Immigration species must be -1 or 1.")
        self.state.immigration.active_species = species
        self.services.state_changed()

    def set_wireworld_brush(self, brush: int) -> None:
        if brush not in (CONDUCTOR, ELECTRON_HEAD, ELECTRON_TAIL):
            raise ValueError("Unknown Wireworld brush.")
        self.state.wireworld.brush = brush
        self.services.state_changed()

    def set_cyclic_brush(self, brush: int) -> None:
        if not 0 <= brush < CYCLIC_STATE_COUNT:
            raise ValueError("Cyclic brush is outside the state range.")
        self.state.cyclic.brush = brush
        self.services.state_changed()

    def cycle_cyclic_threshold(self, maximum: int) -> int:
        self.services.before_operation()
        self.save_history()
        self.state.cyclic.threshold = self.state.cyclic.threshold % maximum + 1
        self.services.state_changed()
        self.sync_history()
        return self.state.cyclic.threshold

    def rotate_ant(self, rotate: Callable[[AntState], AntState]) -> AntState:
        self.services.before_operation()
        self.save_history()
        self.state.ant.ant = rotate(self.state.ant.ant)
        self.services.invalidate("langtons_ant")
        self.services.state_changed()
        self.sync_history()
        return self.state.ant.ant

    def place_ant(self, row: int, column: int) -> bool:
        self.services.before_operation()
        ant = self.state.ant.ant
        if ant.row == row and ant.col == column and ant.active:
            return False
        self.save_history()
        self.state.ant.ant = AntState(row, column, ant.direction)
        self.services.set_running(False)
        self.services.invalidate("langtons_ant")
        self.services.state_changed()
        self.sync_history()
        return True

    def advance(self) -> bool:
        self.services.before_operation()
        mode = self.mode
        if mode == "life":
            changed = self._advance_life()
        elif mode == "immigration":
            changed = self._advance_immigration()
        elif mode == "brians_brain":
            changed = self._advance_brain()
        elif mode == "langtons_ant":
            changed = self._advance_ant()
        elif mode == "wireworld":
            changed = self._advance_wireworld()
        else:
            changed = self._advance_cyclic()
        if changed:
            self.services.state_changed()
            self.sync_history()
        return changed

    def _advance_life(self) -> bool:
        state = self.state.life
        if not any(cell > 0 for row in state.grid for cell in row):
            self.services.set_running(False)
            self._status("Simulation stopped: no live cells.")
            return False
        self.save_history()
        rule_definition: str | Mapping[str, Any] = state.rule
        if state.custom_rule is not None:
            rule_definition = state.custom_rule.life_like_2d()
        new_grid = apply_rules_2d(state.grid, rule_definition)
        for row in range(self.state.rows):
            for column in range(self.state.columns):
                state.activity[row][column] = max(0.0, state.activity[row][column] - 0.10)
                state.trail[row][column] = max(0, state.trail[row][column] - 1)
                old_alive = state.grid[row][column] > 0
                new_alive = new_grid[row][column] > 0
                if old_alive != new_alive:
                    self.services.start_transition(
                        row,
                        column,
                        state.grid[row][column],
                        new_grid[row][column],
                    )
                    state.activity[row][column] += 1.0
                    if old_alive and not new_alive:
                        state.trail[row][column] = self.services.trail_max
        state.grid = new_grid
        state.generation += 1
        self.services.mark_life_dirty()
        return True

    def _advance_immigration(self) -> bool:
        state = self.state.immigration
        if not any(cell for row in state.grid for cell in row):
            self.services.set_running(False)
            self._status("Immigration stopped: no live cells.")
            return False
        self.save_history()
        state.grid = apply_immigration_rules(state.grid)
        state.generation += 1
        self.services.invalidate("immigration")
        return True

    def _advance_brain(self) -> bool:
        state = self.state.brain
        if not any(cell for row in state.grid for cell in row):
            self.services.set_running(False)
            self._status("Brian's Brain stopped: no active cells.")
            return False
        self.save_history()
        state.grid = apply_brain_rules(state.grid)
        state.generation += 1
        self.services.invalidate("brians_brain")
        return True

    def _advance_ant(self) -> bool:
        state = self.state.ant
        if not state.ant.active:
            self.services.set_running(False)
            self._status("Langton's Ant stopped at the board boundary.")
            return False
        self.save_history()
        state.grid, state.ant, state.last_report = step_ant(state.grid, state.ant)
        state.generation += 1
        self.services.invalidate("langtons_ant")
        if state.last_report.exited:
            self.services.set_running(False)
            self._status("Langton's Ant reached the finite board boundary.", 4.0)
        return True

    def _advance_wireworld(self) -> bool:
        state = self.state.wireworld
        if not any(
            cell in (ELECTRON_HEAD, ELECTRON_TAIL)
            for row in state.grid
            for cell in row
        ):
            self.services.set_running(False)
            self._status("Wireworld stopped: no electron signal remains.")
            return False
        self.save_history()
        state.grid = apply_wireworld_rules(state.grid)
        state.generation += 1
        self.services.invalidate("wireworld")
        return True

    def _advance_cyclic(self) -> bool:
        state = self.state.cyclic
        next_grid = apply_cyclic_rules(
            state.grid,
            state_count=CYCLIC_STATE_COUNT,
            threshold=state.threshold,
        )
        if next_grid == state.grid:
            self.services.set_running(False)
            self._status("Cyclic Automaton stopped: no color can advance.")
            return False
        self.save_history()
        state.grid = next_grid
        state.generation += 1
        self.services.invalidate("cyclic_automaton")
        return True

    def clear(self) -> None:
        self.services.before_operation()
        self.save_history()
        mode = self.mode
        if mode == "life":
            state = self.state.life
            state.grid = _integer_grid(self.state.rows, self.state.columns)
            state.trail = _integer_grid(self.state.rows, self.state.columns)
            state.activity = _float_grid(self.state.rows, self.state.columns)
            state.generation = 0
            self.services.clear_transitions()
            self.services.mark_life_dirty()
            message = "Grid cleared."
        elif mode == "immigration":
            state = self.state.immigration
            state.grid = make_immigration_grid(self.state.rows, self.state.columns)
            state.generation = 0
            message = "Immigration grid cleared."
        elif mode == "brians_brain":
            state = self.state.brain
            state.grid = make_brain_grid(self.state.rows, self.state.columns)
            state.generation = 0
            message = "Brian's Brain grid cleared."
        elif mode == "langtons_ant":
            state = self.state.ant
            state.grid = make_ant_grid(self.state.rows, self.state.columns)
            state.ant = centered_ant(self.state.rows, self.state.columns)
            state.generation = 0
            state.last_report = AntStepReport()
            message = "Langton's Ant board reset."
        elif mode == "wireworld":
            state = self.state.wireworld
            state.grid = make_wireworld_grid(self.state.rows, self.state.columns)
            state.generation = 0
            message = "Wireworld grid cleared."
        else:
            state = self.state.cyclic
            state.grid = make_cyclic_grid(self.state.rows, self.state.columns)
            state.generation = 0
            message = "Cyclic Automaton reset to color 0."
        self.services.set_running(False)
        self.services.invalidate(mode)
        self.services.state_changed()
        self.sync_history()
        self._status(message)

    def randomize(self, density: float = 0.20) -> None:
        self.services.before_operation()
        self.save_history()
        mode = self.mode
        if mode == "life":
            state = self.state.life
            state.grid = [
                [1 if state.rng.random() < density else 0 for _ in range(self.state.columns)]
                for _ in range(self.state.rows)
            ]
            state.trail = _integer_grid(self.state.rows, self.state.columns)
            state.activity = _float_grid(self.state.rows, self.state.columns)
            state.generation = 0
            self.services.clear_transitions()
            self.services.mark_life_dirty()
            message = f"Random grid created at {density:.0%} density."
        elif mode == "immigration":
            state = self.state.immigration
            state.grid = randomize_immigration_grid(
                self.state.rows, self.state.columns, density=density, rng=state.rng
            )
            state.generation = 0
            message = "Random two-species Immigration population created."
        elif mode == "brians_brain":
            state = self.state.brain
            state.grid = randomize_brain_grid(
                self.state.rows, self.state.columns, density=0.18, rng=state.rng
            )
            state.generation = 0
            message = "Random Brian's Brain state created."
        elif mode == "langtons_ant":
            state = self.state.ant
            state.grid = randomize_ant_grid(
                self.state.rows, self.state.columns, density=0.15, rng=state.rng
            )
            state.ant = centered_ant(self.state.rows, self.state.columns)
            state.generation = 0
            state.last_report = AntStepReport()
            message = "Random Langton board created; ant reset to center."
        elif mode == "wireworld":
            state = self.state.wireworld
            state.grid = randomize_wireworld_grid(
                self.state.rows,
                self.state.columns,
                conductor_density=density,
                signal_fraction=0.08,
                rng=state.rng,
            )
            state.generation = 0
            message = "Random Wireworld conductors and signals created."
        else:
            state = self.state.cyclic
            state.grid = randomize_cyclic_grid(
                self.state.rows,
                self.state.columns,
                state_count=CYCLIC_STATE_COUNT,
                rng=state.rng,
            )
            state.generation = 0
            message = "Random eight-color Cyclic Automaton state created."
        self.services.set_running(False)
        self.services.invalidate(mode)
        self.services.state_changed()
        self.sync_history()
        self._status(message)

    def analysis_observation(self, mode: str | None = None) -> StateObservation:
        selected = self.mode if mode is None else mode
        title = MODE_BY_KEY[selected].name
        state = self.state.mode_state(selected)
        grid = getattr(state, "grid")
        if selected == "life":
            values = tuple(1 if cell > 0 else 0 for row in grid for cell in row)
            context: object = (
                self.state.life.custom_rule.notation
                if self.state.life.custom_rule is not None
                else self.state.life.rule
            )
            state_count, active, label = 2, (1,), "Live cells"
            signature: tuple[object, ...] = ()
        elif selected == "immigration":
            values = tuple(1 if cell > 0 else 2 if cell < 0 else 0 for row in grid for cell in row)
            context = "B3/S23"
            state_count, active, label = 3, (1, 2), "Population"
            signature = ()
        elif selected == "brians_brain":
            values = tuple(cell for row in grid for cell in row)
            context = "Brian's Brain"
            state_count, active, label = 3, (FIRING, DYING), "Active cells"
            signature = ()
        elif selected == "langtons_ant":
            values = tuple(cell for row in grid for cell in row)
            ant = self.state.ant.ant
            context = "RL finite"
            state_count, active, label = 2, (ANT_BLACK,), "Black cells"
            signature = (ant.row, ant.col, ant.direction, ant.active)
        elif selected == "wireworld":
            values = tuple(cell for row in grid for cell in row)
            context = "Wireworld"
            state_count = 4
            active = (ELECTRON_HEAD, ELECTRON_TAIL, CONDUCTOR)
            label = "Occupied cells"
            signature = ()
        else:
            values = tuple(cell for row in grid for cell in row)
            context = (CYCLIC_STATE_COUNT, self.state.cyclic.threshold)
            state_count = CYCLIC_STATE_COUNT
            active = tuple(range(1, CYCLIC_STATE_COUNT))
            label = "Non-zero phase"
            signature = ()
        return StateObservation(
            key=f"2d:{selected}",
            title=title,
            generation=int(getattr(state, "generation")),
            values=values,
            state_count=state_count,
            active_states=active,
            population_label=label,
            lattice_shape=(self.state.rows, self.state.columns),
            experiment_context=context,
            signature_context=signature,
        )

    def _snapshot_mode(self, mode: str) -> dict[str, Any]:
        self.services.before_operation()
        state = self.state.mode_state(mode)
        if mode == "life":
            return {
                "rule": self.state.life.rule,
                "custom_rule": (
                    self.state.life.custom_rule.as_document()
                    if self.state.life.custom_rule is not None
                    else None
                ),
                "grid": deepcopy(self.state.life.grid),
                "trail": deepcopy(self.state.life.trail),
                "activity": deepcopy(self.state.life.activity),
                "generation": self.state.life.generation,
            }
        result = {"grid": deepcopy(getattr(state, "grid")), "generation": getattr(state, "generation")}
        if mode == "langtons_ant":
            ant = self.state.ant.ant
            report = self.state.ant.last_report
            result["ant"] = {"row": ant.row, "col": ant.col, "direction": ant.direction, "active": ant.active}
            result["report"] = {"turned": report.turned, "painted_black": report.painted_black, "exited": report.exited}
        elif mode == "cyclic_automaton":
            result["threshold"] = self.state.cyclic.threshold
        return result

    def _restore_mode(self, mode: str, snapshot: Mapping[str, Any]) -> None:
        state = self.state.mode_state(mode)
        setattr(state, "grid", deepcopy(snapshot["grid"]))
        setattr(state, "generation", int(snapshot["generation"]))
        if mode == "life":
            self.state.life.rule = str(snapshot["rule"])
            self.state.life.custom_rule = None
            custom_document = snapshot.get("custom_rule")
            if isinstance(custom_document, Mapping):
                custom_rule = custom_rule_from_document(custom_document)
                if (
                    custom_rule.dimension != "2d"
                    or custom_rule.key != self.state.life.rule
                ):
                    raise ValueError(
                        "Embedded 2D custom rule does not match its rule key."
                    )
                self.state.life.custom_rule = custom_rule
            self.state.life.trail = deepcopy(snapshot["trail"])
            self.state.life.activity = deepcopy(snapshot["activity"])
            self.services.clear_transitions()
            self.services.mark_life_dirty()
        elif mode == "langtons_ant":
            saved = snapshot["ant"]
            self.state.ant.ant = AntState(int(saved["row"]), int(saved["col"]), int(saved["direction"]), bool(saved["active"]))
            report = snapshot["report"]
            self.state.ant.last_report = AntStepReport(str(report["turned"]), bool(report["painted_black"]), bool(report["exited"]))
        elif mode == "cyclic_automaton":
            self.state.cyclic.threshold = int(snapshot["threshold"])
        self.services.invalidate(mode)
        self.services.state_changed()
        self.services.rebuild_sidebar()

    def snapshot(self) -> dict[str, Any]:
        self.services.before_operation()
        return {
            "shape": [self.state.rows, self.state.columns],
            "camera": {
                "cell_size": self.state.cell_size,
                "offset": [self.state.view_offset_x, self.state.view_offset_y],
            },
            "states": {
                "life": self._snapshot_mode("life"),
                "immigration": {**self._snapshot_mode("immigration"), "active_species": self.state.immigration.active_species},
                "brians_brain": self._snapshot_mode("brians_brain"),
                "langtons_ant": {key: value for key, value in self._snapshot_mode("langtons_ant").items() if key != "report"},
                "wireworld": {**self._snapshot_mode("wireworld"), "brush": self.state.wireworld.brush},
                "cyclic_automaton": {**self._snapshot_mode("cyclic_automaton"), "brush": self.state.cyclic.brush},
            },
            "rng": {
                "life": encode_random_state(self.state.life.rng),
                "immigration": encode_random_state(self.state.immigration.rng),
                "brians_brain": encode_random_state(self.state.brain.rng),
                "langtons_ant": encode_random_state(self.state.ant.rng),
                "wireworld": encode_random_state(self.state.wireworld.rng),
                "cyclic_automaton": encode_random_state(self.state.cyclic.rng),
            },
        }

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        if list(snapshot["shape"]) != [self.state.rows, self.state.columns]:
            raise ValueError(f"Session grid is {snapshot['shape']}; this build requires [{self.state.rows}, {self.state.columns}].")
        camera = snapshot["camera"]
        self.state.cell_size = int(camera["cell_size"])
        self.state.view_offset_x, self.state.view_offset_y = map(int, camera["offset"])
        states = snapshot["states"]
        self._restore_mode("life", states["life"])
        self._restore_mode("immigration", states["immigration"])
        self.state.immigration.active_species = int(states["immigration"]["active_species"])
        self._restore_mode("brians_brain", states["brians_brain"])
        ant_snapshot = dict(states["langtons_ant"])
        ant_snapshot["report"] = {"turned": "none", "painted_black": False, "exited": False}
        self._restore_mode("langtons_ant", ant_snapshot)
        self._restore_mode("wireworld", states["wireworld"])
        self.state.wireworld.brush = int(states["wireworld"]["brush"])
        self._restore_mode("cyclic_automaton", states["cyclic_automaton"])
        self.state.cyclic.brush = int(states["cyclic_automaton"]["brush"])
        rng = snapshot["rng"]
        restore_random_state(self.state.life.rng, rng["life"])
        restore_random_state(self.state.immigration.rng, rng["immigration"])
        restore_random_state(self.state.brain.rng, rng["brians_brain"])
        restore_random_state(self.state.ant.rng, rng["langtons_ant"])
        restore_random_state(self.state.wireworld.rng, rng["wireworld"])
        restore_random_state(self.state.cyclic.rng, rng["cyclic_automaton"])
        self.services.set_running(False)
        self.reset_all_histories()
        self.services.state_changed()

    def build_sidebar(self, menu: Menu) -> None:
        self.services.build_sidebar(menu)

    def close_overlays(self) -> None:
        self.services.close_overlays()

    def handle_overlay_event(self, event: pygame.event.Event) -> bool:
        return self.services.handle_overlay_event(event)

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        return self.services.handle_keydown(event)

    def handle_pointer_event(self, event: pygame.event.Event) -> bool:
        return self.services.handle_pointer_event(event)

    def center_view(self) -> None:
        self.services.center_view()

    def zoom(self, factor: float) -> None:
        self.services.zoom(factor)


@dataclass(frozen=True)
class TwoDimensionalRendererCallbacks:
    """Drawing callbacks supplied by the Pygame presentation layer."""

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
