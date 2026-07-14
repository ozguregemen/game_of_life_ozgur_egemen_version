"""Scientific measurements for live and batch cellular-automata experiments."""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from statistics import fmean
from typing import Hashable, Iterable, Literal, Sequence

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


@dataclass(frozen=True)
class AnalysisSample:
    """Measurements for one observed generation."""

    generation: int
    population: int
    density: float
    entropy: float
    change_rate: float
    signature: bytes = field(repr=False)


@dataclass(frozen=True)
class AnalysisSummary:
    """Current measurements and detected long-term behavior."""

    sample_count: int
    period: int | None
    stabilization_generation: int | None
    stable: bool


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
        )

    def reset(self, observation: StateObservation) -> AnalysisSample:
        """Start a new measurement run from an initial observation."""

        self.title = observation.title
        self.population_label = observation.population_label
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
        population = sum(
            value in observation.active_states for value in observation.values
        )
        density = (
            100.0 * population / len(observation.values)
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
