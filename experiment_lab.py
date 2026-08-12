"""UI-independent, bounded batch experiments for 1D, 2D, and 3D CA."""

from __future__ import annotations

import csv
import datetime as dt
import json
import random
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import fmean, pstdev
from types import MappingProxyType
from typing import Any, Callable, Mapping

import numpy as np

from app_metadata import APP_VERSION
from app_paths import APPLICATION_PATHS
from brians_brain import DYING, FIRING, apply_brain_rules, randomize_brain_grid
from cyclic_automaton import apply_cyclic_rules, randomize_cyclic_grid
from immigration import apply_immigration_rules, randomize_immigration_grid
from langtons_ant import centered_ant, make_ant_grid, step_ant
from one_dimensional_ca import (
    RuleSpec,
    next_uniform_background,
    step_one_dimensional,
)
from scientific_analysis import AnalysisSeries, StateObservation
from three_dimensional_ca import Volume3D
from three_dimensional_generations import GenerationsRule3D, step_generations_3d
from three_dimensional_rules import LifeLikeRule3D, step_life_like_3d
from wireworld import apply_wireworld_rules, randomize_wireworld_grid

EXPERIMENT_REPORT_SCHEMA = "cellular-automata-lab-batch-experiment"
EXPERIMENT_REPORT_VERSION = 2
EXPERIMENT_EXPORT_DIRECTORY = APPLICATION_PATHS.exports / "experiment_lab"

ENGINE_1D = "1d"
ENGINE_2D_LIFE = "2d_life"
ENGINE_2D_IMMIGRATION = "2d_immigration"
ENGINE_2D_BRAIN = "2d_brians_brain"
ENGINE_2D_ANT = "2d_langtons_ant"
ENGINE_2D_WIREWORLD = "2d_wireworld"
ENGINE_2D_CYCLIC = "2d_cyclic"
ENGINE_3D_LIFE = "3d_life"
ENGINE_3D_GENERATIONS = "3d_generations"
EXPERIMENT_ENGINES = (
    ENGINE_1D,
    ENGINE_2D_LIFE,
    ENGINE_2D_IMMIGRATION,
    ENGINE_2D_BRAIN,
    ENGINE_2D_ANT,
    ENGINE_2D_WIREWORLD,
    ENGINE_2D_CYCLIC,
    ENGINE_3D_LIFE,
    ENGINE_3D_GENERATIONS,
)

SEED_SINGLE = "single"
SEED_RANDOM = "random"
SEED_KINDS = (SEED_SINGLE, SEED_RANDOM)

MIN_GENERATIONS = 10
MAX_GENERATIONS = 500
MIN_REPETITIONS = 1
MAX_REPETITIONS = 12
MAX_RULES = 8
MAX_BOUNDARIES = 3
MAX_CASES = 128
MAX_CELL_UPDATES = 30_000_000


@dataclass(frozen=True)
class ExperimentRule:
    """Serializable rule or mode recipe evaluated by the batch engine."""

    key: str
    name: str
    dimension: str
    engine: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.name.strip():
            raise ValueError("Experiment rule key and name cannot be empty.")
        if self.dimension not in ("1d", "2d", "3d"):
            raise ValueError("Experiment rule dimension must be 1d, 2d, or 3d.")
        if self.engine not in EXPERIMENT_ENGINES:
            raise ValueError(f"Unknown experiment engine: {self.engine}.")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("Experiment rule parameters must be an object.")
        object.__setattr__(self, "key", self.key.strip())
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    def as_document(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "dimension": self.dimension,
            "engine": self.engine,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class ExperimentContext:
    """Available rule catalog and parameter ranges for one active workspace."""

    dimension: str
    mode_label: str
    rules: tuple[ExperimentRule, ...]
    boundaries: tuple[str, ...]
    size_options: tuple[int, ...]
    default_seed_density: float = 0.20
    seed_kinds: tuple[str, ...] = SEED_KINDS

    def __post_init__(self) -> None:
        if self.dimension not in ("1d", "2d", "3d"):
            raise ValueError("Experiment context dimension must be 1d, 2d, or 3d.")
        if not self.rules or len(self.rules) > MAX_RULES:
            raise ValueError(f"Experiment context needs 1-{MAX_RULES} rules.")
        if any(rule.dimension != self.dimension for rule in self.rules):
            raise ValueError("Every experiment rule must match the context dimension.")
        if not self.boundaries or len(self.boundaries) > MAX_BOUNDARIES:
            raise ValueError("Experiment context needs one to three boundaries.")
        if not self.size_options or any(size < 3 for size in self.size_options):
            raise ValueError("Experiment sizes must be at least three cells per axis.")
        if not 0.01 <= self.default_seed_density <= 0.99:
            raise ValueError("Default seed density must be between 0.01 and 0.99.")
        if not self.seed_kinds or any(kind not in SEED_KINDS for kind in self.seed_kinds):
            raise ValueError("Experiment context must expose supported seed kinds.")


@dataclass(frozen=True)
class ExperimentPlan:
    """Validated immutable parameter sweep submitted to a background runner."""

    dimension: str
    mode_label: str
    rules: tuple[ExperimentRule, ...]
    boundaries: tuple[str, ...]
    sizes: tuple[int, ...]
    generation_counts: tuple[int, ...]
    repetitions: int
    seed_kinds: tuple[str, ...]
    seed_densities: tuple[float, ...]
    master_seed: int

    def __post_init__(self) -> None:
        if self.dimension not in ("1d", "2d", "3d"):
            raise ValueError("Experiment dimension must be 1d, 2d, or 3d.")
        if not self.rules or len(self.rules) > MAX_RULES:
            raise ValueError(f"Select between one and {MAX_RULES} rules.")
        if any(rule.dimension != self.dimension for rule in self.rules):
            raise ValueError("Every selected rule must match the plan dimension.")
        if not self.boundaries or len(self.boundaries) > MAX_BOUNDARIES:
            raise ValueError("Select between one and three boundary modes.")
        if not self.sizes or len(self.sizes) > 3:
            raise ValueError("Select between one and three lattice sizes.")
        maximum_size = {"1d": 1001, "2d": 160, "3d": 48}[self.dimension]
        if any(not 3 <= size <= maximum_size for size in self.sizes):
            raise ValueError("Experiment lattice size is outside its safe range.")
        if not self.generation_counts or len(self.generation_counts) > 3:
            raise ValueError("Select between one and three generation horizons.")
        if any(
            not MIN_GENERATIONS <= generations <= MAX_GENERATIONS
            for generations in self.generation_counts
        ):
            raise ValueError(
                f"Generations must be between {MIN_GENERATIONS} and {MAX_GENERATIONS}."
            )
        if not MIN_REPETITIONS <= self.repetitions <= MAX_REPETITIONS:
            raise ValueError(
                f"Repetitions must be between {MIN_REPETITIONS} and {MAX_REPETITIONS}."
            )
        if not self.seed_kinds or any(kind not in SEED_KINDS for kind in self.seed_kinds):
            raise ValueError("Select at least one supported seed kind.")
        if not self.seed_densities or len(self.seed_densities) > 3:
            raise ValueError("Select between one and three random seed densities.")
        if any(not 0.01 <= density <= 0.99 for density in self.seed_densities):
            raise ValueError("Seed density must be between 0.01 and 0.99.")
        if isinstance(self.master_seed, bool) or not isinstance(self.master_seed, int):
            raise TypeError("Master seed must be an integer.")
        cases = self.run_count
        if cases > MAX_CASES:
            raise ValueError(f"Experiment requests {cases} runs; limit is {MAX_CASES}.")
        dimension = {"1d": 1, "2d": 2, "3d": 3}[self.dimension]
        seed_factor = (
            (len(self.seed_densities) * self.repetitions if SEED_RANDOM in self.seed_kinds else 0)
            + (1 if SEED_SINGLE in self.seed_kinds else 0)
        )
        updates = len(self.rules) * len(self.boundaries) * seed_factor * sum(
            size**dimension * generations
            for size in self.sizes
            for generations in self.generation_counts
        )
        if updates > MAX_CELL_UPDATES:
            raise ValueError(
                f"Experiment requests about {updates:,} cell updates; "
                f"safe limit is {MAX_CELL_UPDATES:,}."
            )

    @property
    def run_count(self) -> int:
        seed_runs = (
            (len(self.seed_densities) * self.repetitions if SEED_RANDOM in self.seed_kinds else 0)
            + (1 if SEED_SINGLE in self.seed_kinds else 0)
        )
        return (
            len(self.rules)
            * len(self.boundaries)
            * len(self.sizes)
            * len(self.generation_counts)
            * seed_runs
        )

    @property
    def size(self) -> int:
        """Return the sole size of an internal concrete run plan."""

        if len(self.sizes) != 1:
            raise ValueError("A concrete run must contain exactly one lattice size.")
        return self.sizes[0]

    @property
    def generations(self) -> int:
        """Return the sole generation horizon of an internal concrete run plan."""

        if len(self.generation_counts) != 1:
            raise ValueError("A concrete run must contain exactly one generation horizon.")
        return self.generation_counts[0]

    @property
    def seed_kind(self) -> str:
        if len(self.seed_kinds) != 1:
            raise ValueError("A concrete run must contain exactly one seed kind.")
        return self.seed_kinds[0]

    @property
    def seed_density(self) -> float:
        if len(self.seed_densities) != 1:
            raise ValueError("A concrete run must contain exactly one seed density.")
        return self.seed_densities[0]

    def concrete(
        self,
        *,
        rule: ExperimentRule,
        boundary: str,
        size: int,
        generations: int,
        seed_kind: str,
        seed_density: float,
    ) -> ExperimentPlan:
        """Return one validated single-configuration plan used by a worker run."""

        return replace(
            self,
            rules=(rule,),
            boundaries=(boundary,),
            sizes=(size,),
            generation_counts=(generations,),
            repetitions=1,
            seed_kinds=(seed_kind,),
            seed_densities=(seed_density,),
        )

    def as_document(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "mode_label": self.mode_label,
            "rules": [rule.as_document() for rule in self.rules],
            "boundaries": list(self.boundaries),
            "sizes": list(self.sizes),
            "generation_counts": list(self.generation_counts),
            "repetitions": self.repetitions,
            "seed_kinds": list(self.seed_kinds),
            "seed_densities": list(self.seed_densities),
            "master_seed": self.master_seed,
        }


@dataclass(frozen=True)
class ExperimentRun:
    rule_key: str
    rule_name: str
    boundary: str
    size: int
    generations: int
    seed_kind: str
    seed_density: float | None
    repetition: int
    seed: int
    final_population: int
    final_density: float
    mean_density: float
    mean_entropy: float
    mean_block_entropy: float
    mean_change_rate: float
    period: int | None
    stabilization_generation: int | None
    final_component_count: int | None
    final_largest_component_fraction: float
    final_bounding_box_fill: float
    final_radius_of_gyration: float
    final_exposed_faces_per_cell: float
    final_anisotropy: float
    translation_detected: bool
    translation_period: int | None
    translation_displacement: tuple[int, ...]
    translation_speed: float


@dataclass(frozen=True)
class ExperimentAggregate:
    """Mean and population SD across repeated runs of one rule/boundary pair."""

    rule_key: str
    rule_name: str
    boundary: str
    size: int
    generations: int
    seed_kind: str
    seed_density: float | None
    repetitions: int
    mean_final_population: float
    sd_final_population: float
    mean_final_density: float
    sd_final_density: float
    mean_density: float
    sd_density: float
    mean_entropy: float
    sd_entropy: float
    mean_block_entropy: float
    sd_block_entropy: float
    mean_change_rate: float
    sd_change_rate: float
    period_detection_rate: float
    mean_detected_period: float | None
    sd_detected_period: float | None
    mean_stabilization_generation: float | None
    sd_stabilization_generation: float | None
    mean_final_component_count: float | None
    sd_final_component_count: float | None
    mean_largest_component_fraction: float
    sd_largest_component_fraction: float
    mean_bounding_box_fill: float
    sd_bounding_box_fill: float
    mean_radius_of_gyration: float
    sd_radius_of_gyration: float
    mean_exposed_faces_per_cell: float
    sd_exposed_faces_per_cell: float
    mean_anisotropy: float
    sd_anisotropy: float
    translation_detection_rate: float
    mean_translation_period: float | None
    sd_translation_period: float | None
    mean_translation_speed: float
    sd_translation_speed: float

    def as_document(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ExperimentReport:
    """Complete reproducible output from one parameter sweep."""

    plan: ExperimentPlan
    runs: tuple[ExperimentRun, ...]
    aggregates: tuple[ExperimentAggregate, ...]
    elapsed_seconds: float
    completed_at: str

    def as_document(self) -> dict[str, Any]:
        return {
            "schema": EXPERIMENT_REPORT_SCHEMA,
            "version": EXPERIMENT_REPORT_VERSION,
            "application_version": APP_VERSION,
            "completed_at": self.completed_at,
            "elapsed_seconds": self.elapsed_seconds,
            "plan": self.plan.as_document(),
            "runs": [dict(run.__dict__) for run in self.runs],
            "aggregates": [aggregate.as_document() for aggregate in self.aggregates],
        }


class ExperimentCancelled(RuntimeError):
    """Raised cooperatively when the user cancels a background sweep."""


@dataclass(frozen=True)
class ExperimentProgress:
    """Thread-safe progress snapshot exposed to the Pygame presentation layer."""

    completed_runs: int = 0
    total_runs: int = 0
    rule_name: str = ""
    boundary: str = ""

    @property
    def fraction(self) -> float:
        return self.completed_runs / self.total_runs if self.total_runs else 0.0


def _seed_for(
    plan: ExperimentPlan,
    seed_kind_index: int,
    density_index: int,
    repetition: int,
) -> int:
    """Pair initial randomness across rules and boundaries for fair comparisons."""

    return (
        plan.master_seed
        + 1_009 * seed_kind_index
        + 101 * density_index
        + repetition
    ) & ((1 << 63) - 1)


def _observation(
    rule: ExperimentRule,
    boundary: str,
    generation: int,
    values: tuple[int, ...],
    state_count: int,
    shape: tuple[int, ...],
    *,
    active_states: tuple[int, ...] = (1,),
    signature: Any = (),
) -> StateObservation:
    return StateObservation(
        key=f"batch:{rule.key}:{boundary}",
        title=rule.name,
        generation=generation,
        values=values,
        state_count=state_count,
        active_states=active_states,
        population_label="Active cells",
        alignment="center" if rule.dimension == "1d" else "left",
        lattice_shape=shape,
        experiment_context=(rule.key, boundary),
        signature_context=signature,
    )


def _life_step_2d(cells: np.ndarray, birth: tuple[int, ...], survival: tuple[int, ...], boundary: str) -> np.ndarray:
    if boundary == "wrap":
        counts = sum(
            np.roll(np.roll(cells, dy, axis=0), dx, axis=1)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dy, dx) != (0, 0)
        )
    else:
        padded = np.pad(cells, 1, mode="constant")
        counts = sum(
            padded[1 + dy : 1 + dy + cells.shape[0], 1 + dx : 1 + dx + cells.shape[1]]
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dy, dx) != (0, 0)
        )
    alive = cells == 1
    return np.where(alive, np.isin(counts, survival), np.isin(counts, birth)).astype(np.uint8)


def _random_binary_grid(size: int, density: float, rng: random.Random) -> np.ndarray:
    return np.fromiter(
        (1 if rng.random() < density else 0 for _ in range(size * size)),
        dtype=np.uint8,
        count=size * size,
    ).reshape(size, size)


def _run_one_dimensional(
    plan: ExperimentPlan,
    rule: ExperimentRule,
    boundary: str,
    seed: int,
    cancelled: threading.Event,
) -> AnalysisSeries:
    spec = RuleSpec.from_mapping(rule.parameters)
    rng = random.Random(seed)
    if plan.seed_kind == SEED_SINGLE:
        row = tuple(1 if index == plan.size // 2 else 0 for index in range(plan.size))
    else:
        row = tuple(
            rng.randrange(1, spec.states) if rng.random() < plan.seed_density else 0
            for _ in range(plan.size)
        )
    previous = tuple(0 for _ in row)
    background = previous_background = 0
    series = AnalysisSeries(rule.key, max_samples=plan.generations + 1)
    series.reset(_observation(rule, boundary, 0, row, spec.states, (plan.size,), signature=(background, previous_background)))
    for generation in range(1, plan.generations + 1):
        if cancelled.is_set():
            raise ExperimentCancelled("Experiment cancelled.")
        following = step_one_dimensional(
            row,
            spec,
            boundary=boundary,
            background=background,
            previous_row=previous,
        )
        next_bg = next_uniform_background(
            spec,
            background,
            previous_background=previous_background,
        )
        previous, row = row, following
        previous_background, background = background, next_bg
        series.observe(_observation(rule, boundary, generation, row, spec.states, (plan.size,), signature=(background, previous_background)))
    return series


def _run_two_dimensional(
    plan: ExperimentPlan,
    rule: ExperimentRule,
    boundary: str,
    seed: int,
    cancelled: threading.Event,
) -> AnalysisSeries:
    rng = random.Random(seed)
    size = plan.size
    engine = rule.engine
    ant = None
    if engine == ENGINE_2D_LIFE:
        cells: Any = _random_binary_grid(size, plan.seed_density, rng)
        if plan.seed_kind == SEED_SINGLE:
            cells.fill(0)
            cells[size // 2, size // 2] = 1
        state_count, active_states = 2, (1,)
    elif engine == ENGINE_2D_IMMIGRATION:
        cells = randomize_immigration_grid(size, size, density=plan.seed_density, rng=rng)
        state_count, active_states = 3, (1, 2)
    elif engine == ENGINE_2D_BRAIN:
        cells = randomize_brain_grid(size, size, density=plan.seed_density, rng=rng)
        state_count, active_states = 3, (FIRING, DYING)
    elif engine == ENGINE_2D_ANT:
        cells = make_ant_grid(size, size)
        ant = centered_ant(size, size)
        state_count, active_states = 2, (1,)
    elif engine == ENGINE_2D_WIREWORLD:
        cells = randomize_wireworld_grid(
            size,
            size,
            conductor_density=plan.seed_density,
            rng=rng,
        )
        state_count, active_states = 4, (1, 2, 3)
    elif engine == ENGINE_2D_CYCLIC:
        count = int(rule.parameters.get("state_count", 8))
        cells = randomize_cyclic_grid(size, size, state_count=count, rng=rng)
        state_count, active_states = count, tuple(range(1, count))
    else:
        raise ValueError(f"Unsupported 2D experiment engine: {engine}.")

    def values() -> tuple[int, ...]:
        if engine == ENGINE_2D_IMMIGRATION:
            return tuple(1 if value > 0 else 2 if value < 0 else 0 for row in cells for value in row)
        if isinstance(cells, np.ndarray):
            return tuple(int(value) for value in cells.flat)
        return tuple(int(value) for row in cells for value in row)

    series = AnalysisSeries(rule.key, max_samples=plan.generations + 1)
    signature = () if ant is None else (ant.row, ant.col, ant.direction, ant.active)
    series.reset(_observation(rule, boundary, 0, values(), state_count, (size, size), active_states=active_states, signature=signature))
    for generation in range(1, plan.generations + 1):
        if cancelled.is_set():
            raise ExperimentCancelled("Experiment cancelled.")
        if engine == ENGINE_2D_LIFE:
            cells = _life_step_2d(
                cells,
                tuple(rule.parameters["birth"]),
                tuple(rule.parameters["survival"]),
                boundary,
            )
        elif engine == ENGINE_2D_IMMIGRATION:
            cells = apply_immigration_rules(cells)
        elif engine == ENGINE_2D_BRAIN:
            cells = apply_brain_rules(cells)
        elif engine == ENGINE_2D_ANT:
            cells, ant, _ = step_ant(cells, ant)
        elif engine == ENGINE_2D_WIREWORLD:
            cells = apply_wireworld_rules(cells)
        else:
            cells = apply_cyclic_rules(
                cells,
                state_count=state_count,
                threshold=int(rule.parameters.get("threshold", 1)),
            )
        signature = () if ant is None else (ant.row, ant.col, ant.direction, ant.active)
        series.observe(_observation(rule, boundary, generation, values(), state_count, (size, size), active_states=active_states, signature=signature))
    return series


def _rule_3d(rule: ExperimentRule) -> LifeLikeRule3D | GenerationsRule3D:
    from custom_rules import NEIGHBORHOODS_3D

    neighborhood = NEIGHBORHOODS_3D[str(rule.parameters["neighborhood"])]
    if rule.engine == ENGINE_3D_LIFE:
        return LifeLikeRule3D(
            rule.key,
            rule.name,
            tuple(rule.parameters["birth"]),
            tuple(rule.parameters["survival"]),
            neighborhood,
            "Batch experiment rule.",
        )
    return GenerationsRule3D(
        rule.key,
        rule.name,
        tuple(rule.parameters["survival"]),
        tuple(rule.parameters["birth"]),
        int(rule.parameters["state_count"]),
        neighborhood,
        "Batch experiment rule.",
        float(rule.parameters.get("seed_density", 0.20)),
    )


def _run_three_dimensional(
    plan: ExperimentPlan,
    rule: ExperimentRule,
    boundary: str,
    seed: int,
    cancelled: threading.Event,
) -> AnalysisSeries:
    runtime_rule = _rule_3d(rule)
    state_count = runtime_rule.state_count if isinstance(runtime_rule, GenerationsRule3D) else 2
    rng = random.Random(seed)
    shape = (plan.size,) * 3
    cells = np.fromiter(
        (1 if rng.random() < plan.seed_density else 0 for _ in range(plan.size**3)),
        dtype=np.uint8,
        count=plan.size**3,
    ).reshape(shape)
    if plan.seed_kind == SEED_SINGLE:
        cells.fill(0)
        center = plan.size // 2
        cells[center, center, center] = 1
    volume = Volume3D(
        cells,
        state_count=state_count,
        boundary=boundary,
        neighborhood=runtime_rule.neighborhood,
    )
    series = AnalysisSeries(rule.key, max_samples=plan.generations + 1)
    series.reset(_observation(rule, boundary, 0, tuple(int(value) for value in volume.cells.flat), state_count, shape))
    for generation in range(1, plan.generations + 1):
        if cancelled.is_set():
            raise ExperimentCancelled("Experiment cancelled.")
        following = (
            step_generations_3d(volume, runtime_rule)
            if isinstance(runtime_rule, GenerationsRule3D)
            else step_life_like_3d(volume, runtime_rule)
        )
        volume.replace_cells(following)
        series.observe(_observation(rule, boundary, generation, tuple(int(value) for value in volume.cells.flat), state_count, shape))
    return series


def _run_summary(
    plan: ExperimentPlan,
    rule: ExperimentRule,
    boundary: str,
    repetition: int,
    seed: int,
    cancelled: threading.Event,
) -> ExperimentRun:
    if plan.dimension == "1d":
        series = _run_one_dimensional(plan, rule, boundary, seed, cancelled)
    elif plan.dimension == "2d":
        series = _run_two_dimensional(plan, rule, boundary, seed, cancelled)
    else:
        series = _run_three_dimensional(plan, rule, boundary, seed, cancelled)
    samples = series.samples
    final = samples[-1]
    temporal = samples[1:] or samples
    structure = series.structure()
    recurrence = series.translation_recurrence
    moving_recurrence = recurrence if recurrence is not None and recurrence.moving else None
    return ExperimentRun(
        rule_key=rule.key,
        rule_name=rule.name,
        boundary=boundary,
        size=plan.size,
        generations=plan.generations,
        seed_kind=plan.seed_kind,
        seed_density=plan.seed_density if plan.seed_kind == SEED_RANDOM else None,
        repetition=repetition,
        seed=seed,
        final_population=final.population,
        final_density=final.density,
        mean_density=fmean(sample.density for sample in samples),
        mean_entropy=fmean(sample.entropy for sample in samples),
        mean_block_entropy=fmean(sample.block_entropy for sample in samples),
        mean_change_rate=fmean(sample.change_rate for sample in temporal),
        period=series.period,
        stabilization_generation=series.stabilization_generation,
        final_component_count=structure.component_count,
        final_largest_component_fraction=structure.largest_component_fraction,
        final_bounding_box_fill=structure.bounding_box_fill,
        final_radius_of_gyration=structure.radius_of_gyration,
        final_exposed_faces_per_cell=structure.exposed_faces_per_cell,
        final_anisotropy=structure.anisotropy,
        translation_detected=moving_recurrence is not None,
        translation_period=(moving_recurrence.period if moving_recurrence else None),
        translation_displacement=(
            moving_recurrence.displacement if moving_recurrence else ()
        ),
        translation_speed=(moving_recurrence.speed if moving_recurrence else 0.0),
    )


def _aggregate(runs: tuple[ExperimentRun, ...]) -> tuple[ExperimentAggregate, ...]:
    grouped: dict[
        tuple[str, str, int, int, str, float | None],
        list[ExperimentRun],
    ] = {}
    for run in runs:
        grouped.setdefault(
            (
                run.rule_key,
                run.boundary,
                run.size,
                run.generations,
                run.seed_kind,
                run.seed_density,
            ),
            [],
        ).append(run)
    aggregates: list[ExperimentAggregate] = []
    for _, selected in grouped.items():
        final_populations = [float(run.final_population) for run in selected]
        final_densities = [run.final_density for run in selected]
        densities = [run.mean_density for run in selected]
        entropies = [run.mean_entropy for run in selected]
        block_entropies = [run.mean_block_entropy for run in selected]
        change_rates = [run.mean_change_rate for run in selected]
        periods = [float(run.period) for run in selected if run.period is not None]
        stabilizations = [run.stabilization_generation for run in selected if run.stabilization_generation is not None]
        component_counts = [
            float(run.final_component_count)
            for run in selected
            if run.final_component_count is not None
        ]
        largest_component_fractions = [
            run.final_largest_component_fraction for run in selected
        ]
        bounding_box_fills = [run.final_bounding_box_fill for run in selected]
        radii_of_gyration = [run.final_radius_of_gyration for run in selected]
        exposed_faces = [run.final_exposed_faces_per_cell for run in selected]
        anisotropies = [run.final_anisotropy for run in selected]
        translation_periods = [
            float(run.translation_period)
            for run in selected
            if run.translation_detected and run.translation_period is not None
        ]
        translation_speeds = [run.translation_speed for run in selected]
        aggregates.append(
            ExperimentAggregate(
                selected[0].rule_key,
                selected[0].rule_name,
                selected[0].boundary,
                selected[0].size,
                selected[0].generations,
                selected[0].seed_kind,
                selected[0].seed_density,
                len(selected),
                fmean(final_populations),
                pstdev(final_populations),
                fmean(final_densities),
                pstdev(final_densities),
                fmean(densities),
                pstdev(densities),
                fmean(entropies),
                pstdev(entropies),
                fmean(block_entropies),
                pstdev(block_entropies),
                fmean(change_rates),
                pstdev(change_rates),
                100.0 * sum(run.period is not None for run in selected) / len(selected),
                fmean(periods) if periods else None,
                pstdev(periods) if periods else None,
                fmean(stabilizations) if stabilizations else None,
                pstdev(stabilizations) if stabilizations else None,
                fmean(component_counts) if component_counts else None,
                pstdev(component_counts) if component_counts else None,
                fmean(largest_component_fractions),
                pstdev(largest_component_fractions),
                fmean(bounding_box_fills),
                pstdev(bounding_box_fills),
                fmean(radii_of_gyration),
                pstdev(radii_of_gyration),
                fmean(exposed_faces),
                pstdev(exposed_faces),
                fmean(anisotropies),
                pstdev(anisotropies),
                100.0
                * sum(run.translation_detected for run in selected)
                / len(selected),
                fmean(translation_periods) if translation_periods else None,
                pstdev(translation_periods) if translation_periods else None,
                fmean(translation_speeds),
                pstdev(translation_speeds),
            )
        )
    return tuple(aggregates)


def run_experiment_plan(
    plan: ExperimentPlan,
    *,
    cancelled: threading.Event | None = None,
    progress: Callable[[int, int, str, str], None] | None = None,
) -> ExperimentReport:
    """Execute a deterministic bounded sweep without touching Pygame state."""

    cancellation = cancelled or threading.Event()
    started = time.perf_counter()
    runs: list[ExperimentRun] = []
    for rule in plan.rules:
        for boundary in plan.boundaries:
            for size in plan.sizes:
                for generations in plan.generation_counts:
                    configurations: list[tuple[str, float, int, int, int]] = []
                    if SEED_RANDOM in plan.seed_kinds:
                        configurations.extend(
                            (SEED_RANDOM, density, repetition, 0, density_index)
                            for density_index, density in enumerate(plan.seed_densities)
                            for repetition in range(1, plan.repetitions + 1)
                        )
                    if SEED_SINGLE in plan.seed_kinds:
                        configurations.append((SEED_SINGLE, plan.seed_densities[0], 1, 1, 0))
                    for (
                        seed_kind,
                        seed_density,
                        repetition,
                        seed_kind_index,
                        density_index,
                    ) in configurations:
                        run_plan = plan.concrete(
                            rule=rule,
                            boundary=boundary,
                            size=size,
                            generations=generations,
                            seed_kind=seed_kind,
                            seed_density=seed_density,
                        )
                        seed = _seed_for(
                            plan,
                            seed_kind_index,
                            density_index,
                            repetition,
                        )
                        runs.append(
                            _run_summary(
                                run_plan,
                                rule,
                                boundary,
                                repetition,
                                seed,
                                cancellation,
                            )
                        )
                        if progress is not None:
                            progress(len(runs), plan.run_count, rule.name, boundary)
    frozen_runs = tuple(runs)
    return ExperimentReport(
        plan,
        frozen_runs,
        _aggregate(frozen_runs),
        time.perf_counter() - started,
        dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    )


class ExperimentRunner:
    """Single-worker cooperative runner that never blocks the Pygame event loop."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ca-lab")
        self._future: Future[ExperimentReport] | None = None
        self._cancelled = threading.Event()
        self._progress = ExperimentProgress()
        self._progress_lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._future is not None and not self._future.done()

    @property
    def progress(self) -> ExperimentProgress:
        with self._progress_lock:
            return self._progress

    def _record_progress(
        self,
        completed_runs: int,
        total_runs: int,
        rule_name: str,
        boundary: str,
    ) -> None:
        with self._progress_lock:
            self._progress = ExperimentProgress(
                completed_runs,
                total_runs,
                rule_name,
                boundary,
            )

    def request(self, plan: ExperimentPlan) -> bool:
        if self.running:
            return False
        self._cancelled = threading.Event()
        with self._progress_lock:
            self._progress = ExperimentProgress(total_runs=plan.run_count)
        self._future = self._executor.submit(
            run_experiment_plan,
            plan,
            cancelled=self._cancelled,
            progress=self._record_progress,
        )
        return True

    def cancel(self) -> bool:
        if not self.running:
            return False
        self._cancelled.set()
        return True

    def poll(self) -> ExperimentReport | None:
        if self._future is None or not self._future.done():
            return None
        future = self._future
        self._future = None
        return future.result()

    def shutdown(self) -> None:
        self._cancelled.set()
        self._executor.shutdown(wait=True, cancel_futures=True)


def _safe_report_stem(report: ExperimentReport) -> str:
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dimension = report.plan.dimension.replace("/", "-")
    return f"{dimension}-experiment-{timestamp}"


def export_experiment_json(report: ExperimentReport) -> Path:
    """Atomically write the complete reproducible report document."""

    EXPERIMENT_EXPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = EXPERIMENT_EXPORT_DIRECTORY / f"{_safe_report_stem(report)}.json"
    temporary = path.with_suffix(".json.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as output:
            json.dump(report.as_document(), output, ensure_ascii=False, indent=2)
            output.flush()
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return path


def export_experiment_csv(report: ExperimentReport) -> Path:
    """Write one tidy run row with group statistics and its reproducible seed."""

    EXPERIMENT_EXPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = EXPERIMENT_EXPORT_DIRECTORY / f"{_safe_report_stem(report)}.csv"
    temporary = path.with_suffix(".csv.tmp")
    run_fields = tuple(ExperimentRun.__dataclass_fields__)
    group_keys = (
        "rule_key",
        "rule_name",
        "boundary",
        "size",
        "generations",
        "seed_kind",
        "seed_density",
        "repetitions",
    )
    aggregate_fields = tuple(
        f"group_{name}"
        for name in ExperimentAggregate.__dataclass_fields__
        if name not in group_keys
    )
    fields = (*run_fields, *aggregate_fields)
    aggregates = {
        (
            aggregate.rule_key,
            aggregate.boundary,
            aggregate.size,
            aggregate.generations,
            aggregate.seed_kind,
            aggregate.seed_density,
        ): aggregate
        for aggregate in report.aggregates
    }
    try:
        with temporary.open("x", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for run in report.runs:
                row = dict(run.__dict__)
                aggregate = aggregates[
                    (
                        run.rule_key,
                        run.boundary,
                        run.size,
                        run.generations,
                        run.seed_kind,
                        run.seed_density,
                    )
                ]
                for name in ExperimentAggregate.__dataclass_fields__:
                    if name in group_keys:
                        continue
                    row[f"group_{name}"] = getattr(aggregate, name)
                writer.writerow(row)
            output.flush()
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return path
