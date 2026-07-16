"""Scientific measurements for live and batch cellular-automata experiments."""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from statistics import fmean, pstdev
from typing import Hashable, Iterable, Literal, Sequence

import numpy as np

from elementary_ca import (
    BOUNDARY_INFINITE,
    next_background,
    single_cell_seed,
    step_elementary,
    validate_rule,
)

Alignment = Literal["left", "center"]


@dataclass(frozen=True)
class StateObservation:
    """Normalized state supplied by a simulation workspace."""

    key: str
    title: str
    generation: int
    values: tuple[int, ...]
    state_count: int
    active_states: tuple[int, ...]
    population_label: str = "Population"
    alignment: Alignment = "left"
    experiment_context: Hashable = ()
    signature_context: Hashable = ()
    lattice_shape: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("Observation key cannot be empty.")
        if self.generation < 0:
            raise ValueError("Generation cannot be negative.")
        if self.state_count < 2:
            raise ValueError("State count must be at least two.")
        if any(not 0 <= value < self.state_count for value in self.values):
            raise ValueError("Observation values must fit inside state_count.")
        if any(not 0 <= value < self.state_count for value in self.active_states):
            raise ValueError("Active states must fit inside state_count.")
        shape = self.lattice_shape or (len(self.values),)
        if not 1 <= len(shape) <= 3:
            raise ValueError("Lattice shape must describe one, two, or three dimensions.")
        if any(length < 0 for length in shape):
            raise ValueError("Lattice axes cannot be negative.")
        if math.prod(shape) != len(self.values):
            raise ValueError("Lattice shape must contain every observation value.")
        object.__setattr__(self, "lattice_shape", tuple(int(value) for value in shape))


@dataclass(frozen=True)
class AnalysisSample:
    """Measurements for one observed generation."""

    generation: int
    population: int
    density: float
    entropy: float
    change_rate: float
    signature: bytes = field(repr=False)
    block_entropy: float = 0.0
    neighbor_agreement: float = 0.0
    growth_rate: float = 0.0
    state_utilization: float = 0.0


@dataclass(frozen=True)
class AnalysisSummary:
    """Current measurements and detected long-term behavior."""

    sample_count: int
    period: int | None
    stabilization_generation: int | None
    stable: bool
    heuristic_regime: str


@dataclass(frozen=True)
class DescriptiveStatistics:
    """Descriptive values for one metric over a bounded recent window."""

    current: float
    mean: float
    standard_deviation: float
    minimum: float
    maximum: float
    slope_per_generation: float


@dataclass(frozen=True)
class AnalysisWindowSummary:
    """Reproducible descriptive summary for the latest analysis window."""

    sample_count: int
    start_generation: int
    end_generation: int
    metrics: dict[str, DescriptiveStatistics]
    heuristic_regime: str


def normalized_entropy(values: Sequence[int], state_count: int) -> float:
    """Return Shannon entropy normalized to the inclusive range 0..1."""

    if state_count < 2:
        raise ValueError("state_count must be at least two")
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
        if count
    )
    return entropy / math.log2(state_count) if entropy else 0.0


def normalized_block_entropy(
    values: Sequence[int],
    state_count: int,
    lattice_shape: Sequence[int],
) -> float:
    """Return normalized Shannon entropy of non-overlapping local blocks.

    One-dimensional lattices use length-three blocks; 2D and 3D lattices use
    2x2 and 2x2x2 blocks. Incomplete edge blocks are excluded so the statistic
    is independent of padding conventions.
    """

    if state_count < 2:
        raise ValueError("state_count must be at least two")
    shape = tuple(int(length) for length in lattice_shape)
    if not 1 <= len(shape) <= 3 or math.prod(shape) != len(values):
        raise ValueError("lattice_shape must match one to three dimensions")
    if not values:
        return 0.0
    block_shape = (3,) if len(shape) == 1 else (2,) * len(shape)
    trimmed_shape = tuple(
        length - length % block
        for length, block in zip(shape, block_shape, strict=True)
    )
    if any(length == 0 for length in trimmed_shape):
        return normalized_entropy(values, state_count)

    lattice = np.asarray(values, dtype=np.uint16).reshape(shape)
    trimmed = lattice[
        tuple(slice(0, length) for length in trimmed_shape)
    ]
    interleaved_shape: list[int] = []
    for length, block in zip(trimmed_shape, block_shape, strict=True):
        interleaved_shape.extend((length // block, block))
    grouped_axes = tuple(range(0, len(interleaved_shape), 2)) + tuple(
        range(1, len(interleaved_shape), 2)
    )
    block_cell_count = math.prod(block_shape)
    blocks = (
        trimmed.reshape(interleaved_shape)
        .transpose(grouped_axes)
        .reshape(-1, block_cell_count)
    )

    code_capacity = state_count**block_cell_count
    if code_capacity <= np.iinfo(np.uint64).max:
        powers = np.power(
            np.uint64(state_count),
            np.arange(block_cell_count, dtype=np.uint64),
            dtype=np.uint64,
        )
        codes = blocks.astype(np.uint64, copy=False) @ powers
        _, counts = np.unique(codes, return_counts=True)
    else:
        _, counts = np.unique(blocks, axis=0, return_counts=True)
    probabilities = counts.astype(np.float64) / counts.sum()
    entropy = -float(np.sum(probabilities * np.log2(probabilities)))
    maximum = block_cell_count * math.log2(state_count)
    return entropy / maximum if entropy and maximum else 0.0


def neighbor_agreement_rate(
    values: Sequence[int],
    lattice_shape: Sequence[int],
) -> float:
    """Return equal-state agreement across interior orthogonal neighbor pairs."""

    shape = tuple(int(length) for length in lattice_shape)
    if not 1 <= len(shape) <= 3 or math.prod(shape) != len(values):
        raise ValueError("lattice_shape must match one to three dimensions")
    if not values:
        return 0.0
    lattice = np.asarray(values, dtype=np.uint16).reshape(shape)
    agreeing = 0
    pair_count = 0
    for axis, length in enumerate(shape):
        if length < 2:
            continue
        left = [slice(None)] * len(shape)
        right = [slice(None)] * len(shape)
        left[axis] = slice(0, -1)
        right[axis] = slice(1, None)
        first = lattice[tuple(left)]
        second = lattice[tuple(right)]
        agreeing += int(np.count_nonzero(first == second))
        pair_count += first.size
    return 100.0 * agreeing / pair_count if pair_count else 0.0


def _descriptive_statistics(
    samples: Sequence[AnalysisSample],
    attribute: str,
) -> DescriptiveStatistics:
    values = [float(getattr(sample, attribute)) for sample in samples]
    generations = [float(sample.generation) for sample in samples]
    mean_value = fmean(values)
    mean_generation = fmean(generations)
    denominator = sum(
        (generation - mean_generation) ** 2 for generation in generations
    )
    slope = (
        sum(
            (generation - mean_generation) * (value - mean_value)
            for generation, value in zip(generations, values, strict=True)
        )
        / denominator
        if denominator
        else 0.0
    )
    return DescriptiveStatistics(
        current=values[-1],
        mean=mean_value,
        standard_deviation=pstdev(values),
        minimum=min(values),
        maximum=max(values),
        slope_per_generation=slope,
    )


def state_change_rate(
    previous: Sequence[int],
    current: Sequence[int],
    *,
    alignment: Alignment = "left",
    background: int = 0,
) -> float:
    """Return the percentage of positions that changed between two states."""

    if not previous and not current:
        return 0.0
    width = max(len(previous), len(current))
    if alignment == "center":
        previous_left = (width - len(previous)) // 2
        current_left = (width - len(current)) // 2
    else:
        previous_left = 0
        current_left = 0

    changed = 0
    for index in range(width):
        previous_index = index - previous_left
        current_index = index - current_left
        previous_value = (
            previous[previous_index]
            if 0 <= previous_index < len(previous)
            else background
        )
        current_value = (
            current[current_index]
            if 0 <= current_index < len(current)
            else background
        )
        changed += previous_value != current_value
    return 100.0 * changed / width if width else 0.0


def _state_signature(observation: StateObservation) -> bytes:
    digest = hashlib.blake2b(digest_size=16)
    digest.update(bytes(observation.values))
    digest.update(repr(observation.experiment_context).encode("utf-8"))
    digest.update(repr(observation.signature_context).encode("utf-8"))
    digest.update(repr(observation.lattice_shape).encode("utf-8"))
    digest.update(len(observation.values).to_bytes(8, "big"))
    return digest.digest()


class AnalysisSeries:
    """Bounded measurements and online cycle detection for one experiment."""

    def __init__(self, key: str, *, max_samples: int = 2000) -> None:
        if max_samples < 2:
            raise ValueError("max_samples must be at least two")
        self.key = key
        self.max_samples = max_samples
        self.title = key
        self.population_label = "Population"
        self.lattice_shape: tuple[int, ...] = ()
        self.state_count = 2
        self.samples: list[AnalysisSample] = []
        self.period: int | None = None
        self.stabilization_generation: int | None = None
        self._seen: dict[bytes, int] = {}
        self._last_values: tuple[int, ...] = ()
        self._last_context: Hashable = ()

    @property
    def latest(self) -> AnalysisSample | None:
        return self.samples[-1] if self.samples else None

    @property
    def summary(self) -> AnalysisSummary:
        return AnalysisSummary(
            sample_count=len(self.samples),
            period=self.period,
            stabilization_generation=self.stabilization_generation,
            stable=self.period == 1,
            heuristic_regime=self.heuristic_regime(),
        )

    def heuristic_regime(self, *, window: int = 32) -> str:
        """Return an explicitly heuristic label for the recent trajectory."""

        if self.period == 1:
            return "Fixed point"
        if self.period is not None:
            return f"Periodic orbit (p={self.period})"
        if len(self.samples) < 4:
            return "Insufficient samples"
        recent = self.samples[-max(2, min(window, len(self.samples))) :]
        mean_change = fmean(sample.change_rate for sample in recent[1:])
        mean_block = fmean(sample.block_entropy for sample in recent)
        if mean_change < 0.05:
            return "Quiescent candidate"
        if mean_change >= 20.0 and mean_block >= 0.55:
            return "Highly active candidate"
        if mean_change >= 1.0 and mean_block >= 0.15:
            return "Complex / transient candidate"
        return "Ordered / transient candidate"

    def window_summary(self, *, window: int = 100) -> AnalysisWindowSummary:
        """Return descriptive statistics for the most recent samples."""

        if window < 2:
            raise ValueError("Analysis window must contain at least two samples")
        if not self.samples:
            raise ValueError("No analysis samples are available")
        selected = self.samples[-min(window, len(self.samples)) :]
        attributes = (
            "population",
            "density",
            "entropy",
            "block_entropy",
            "change_rate",
            "neighbor_agreement",
            "growth_rate",
            "state_utilization",
        )
        return AnalysisWindowSummary(
            sample_count=len(selected),
            start_generation=selected[0].generation,
            end_generation=selected[-1].generation,
            metrics={
                attribute: _descriptive_statistics(selected, attribute)
                for attribute in attributes
            },
            heuristic_regime=self.heuristic_regime(window=min(window, 32)),
        )

    def reset(self, observation: StateObservation) -> AnalysisSample:
        """Start a new measurement run from an initial observation."""

        self.title = observation.title
        self.population_label = observation.population_label
        self.lattice_shape = observation.lattice_shape
        self.state_count = observation.state_count
        self.samples.clear()
        self.period = None
        self.stabilization_generation = None
        self._seen.clear()
        self._last_values = ()
        self._last_context = observation.experiment_context
        return self._append(observation, change_rate=0.0)

    def observe(self, observation: StateObservation) -> AnalysisSample:
        """Measure a state, resetting when a trajectory is no longer contiguous."""

        latest = self.latest
        if latest is None:
            return self.reset(observation)
        signature = _state_signature(observation)
        if (
            observation.generation != latest.generation + 1
            or observation.experiment_context != self._last_context
        ):
            if (
                observation.generation == latest.generation
                and signature == latest.signature
            ):
                return latest
            return self.reset(observation)

        change_rate = state_change_rate(
            self._last_values,
            observation.values,
            alignment=observation.alignment,
        )
        return self._append(observation, change_rate=change_rate)

    def _append(
        self,
        observation: StateObservation,
        *,
        change_rate: float,
    ) -> AnalysisSample:
        signature = _state_signature(observation)
        self.lattice_shape = observation.lattice_shape
        self.state_count = observation.state_count
        population = sum(
            value in observation.active_states for value in observation.values
        )
        density = (
            100.0 * population / len(observation.values)
            if observation.values
            else 0.0
        )
        previous_population = self.samples[-1].population if self.samples else population
        growth_rate = (
            100.0 * (population - previous_population) / len(observation.values)
            if observation.values
            else 0.0
        )
        sample = AnalysisSample(
            generation=observation.generation,
            population=population,
            density=density,
            entropy=normalized_entropy(observation.values, observation.state_count),
            change_rate=change_rate,
            signature=signature,
            block_entropy=normalized_block_entropy(
                observation.values,
                observation.state_count,
                observation.lattice_shape,
            ),
            neighbor_agreement=neighbor_agreement_rate(
                observation.values,
                observation.lattice_shape,
            ),
            growth_rate=growth_rate,
            state_utilization=(
                100.0 * len(set(observation.values)) / observation.state_count
                if observation.values
                else 0.0
            ),
        )

        previous_generation = self._seen.get(signature)
        if previous_generation is not None:
            detected_period = observation.generation - previous_generation
            if detected_period > 0:
                if self.period is None or detected_period <= self.period:
                    self.period = detected_period
                    if self.stabilization_generation is None:
                        self.stabilization_generation = previous_generation
                    else:
                        self.stabilization_generation = min(
                            self.stabilization_generation,
                            previous_generation,
                        )
        else:
            self._seen[signature] = observation.generation

        self.samples.append(sample)
        self._last_values = observation.values
        self._last_context = observation.experiment_context
        if len(self.samples) > self.max_samples:
            del self.samples[: len(self.samples) - self.max_samples]
            self._seen = {
                stored.signature: stored.generation for stored in self.samples
            }
        return sample


class ScientificAnalysisRegistry:
    """Own independent live analysis series for every workspace or mode."""

    def __init__(self, *, max_samples: int = 2000) -> None:
        self.max_samples = max_samples
        self._series: dict[str, AnalysisSeries] = {}

    def reset(self, observation: StateObservation) -> AnalysisSeries:
        series = self._series.setdefault(
            observation.key,
            AnalysisSeries(observation.key, max_samples=self.max_samples),
        )
        series.reset(observation)
        return series

    def observe(self, observation: StateObservation) -> AnalysisSample:
        series = self._series.get(observation.key)
        if series is None:
            series = self.reset(observation)
            latest = series.latest
            assert latest is not None
            return latest
        return series.observe(observation)

    def get(self, key: str) -> AnalysisSeries | None:
        return self._series.get(key)


@dataclass(frozen=True)
class ElementaryRuleComparison:
    """Aggregate measurements for one canonical Elementary CA run."""

    rule: int
    generations: int
    mean_population: float
    final_population: int
    mean_density: float
    final_density: float
    mean_entropy: float
    mean_block_entropy: float
    mean_neighbor_agreement: float
    mean_change_rate: float
    period: int | None
    stabilization_generation: int | None


def compare_elementary_rules(
    rules: Iterable[int],
    *,
    generations: int = 160,
) -> list[ElementaryRuleComparison]:
    """Run comparable canonical single-seed experiments for several rules."""

    if generations < 1:
        raise ValueError("generations must be positive")
    normalized_rules = tuple(dict.fromkeys(validate_rule(rule) for rule in rules))
    if not normalized_rules:
        raise ValueError("At least one rule is required")

    width = generations * 2 + 1
    results: list[ElementaryRuleComparison] = []
    for rule in normalized_rules:
        row = single_cell_seed(width)
        background = 0
        series = AnalysisSeries(f"rule:{rule}", max_samples=generations + 1)
        series.reset(
            _elementary_observation(rule, row, 0, background)
        )
        for generation in range(1, generations + 1):
            row = step_elementary(
                row,
                rule,
                boundary=BOUNDARY_INFINITE,
                background=background,
            )
            background = next_background(rule, background)
            series.observe(
                _elementary_observation(rule, row, generation, background)
            )

        samples = series.samples
        final = samples[-1]
        results.append(
            ElementaryRuleComparison(
                rule=rule,
                generations=generations,
                mean_population=fmean(sample.population for sample in samples),
                final_population=final.population,
                mean_density=fmean(sample.density for sample in samples),
                final_density=final.density,
                mean_entropy=fmean(sample.entropy for sample in samples),
                mean_block_entropy=fmean(
                    sample.block_entropy for sample in samples
                ),
                mean_neighbor_agreement=fmean(
                    sample.neighbor_agreement for sample in samples
                ),
                mean_change_rate=fmean(sample.change_rate for sample in samples[1:]),
                period=series.period,
                stabilization_generation=series.stabilization_generation,
            )
        )
    return results


def _elementary_observation(
    rule: int,
    row: Sequence[int],
    generation: int,
    background: int,
) -> StateObservation:
    return StateObservation(
        key=f"rule:{rule}",
        title=f"Elementary Rule {rule}",
        generation=generation,
        values=tuple(row),
        state_count=2,
        active_states=(1,),
        population_label="Active cells",
        alignment="center",
        lattice_shape=(len(row),),
        experiment_context=(rule, BOUNDARY_INFINITE),
        signature_context=background,
    )


class ElementaryComparisonRunner:
    """Run rule comparisons off the Pygame event thread."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="eca-analysis",
        )
        self._future: Future[list[ElementaryRuleComparison]] | None = None
        self._request: tuple[tuple[int, ...], int] | None = None

    @property
    def running(self) -> bool:
        return self._future is not None and not self._future.done()

    def request(
        self,
        rules: Iterable[int],
        *,
        generations: int = 160,
    ) -> bool:
        request = (tuple(dict.fromkeys(rules)), generations)
        if self.running or request == self._request:
            return False
        self._request = request
        self._future = self._executor.submit(
            compare_elementary_rules,
            request[0],
            generations=generations,
        )
        return True

    def poll(self) -> list[ElementaryRuleComparison] | None:
        if self._future is None or not self._future.done():
            return None
        future = self._future
        self._future = None
        try:
            return future.result()
        except Exception:
            self._request = None
            raise

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
