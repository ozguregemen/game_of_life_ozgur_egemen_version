"""Persistent report history and descriptive cross-experiment comparisons."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from app_paths import APPLICATION_PATHS
from experiment_lab import (
    EXPERIMENT_REPORT_SCHEMA,
    EXPERIMENT_REPORT_VERSION,
    ExperimentAggregate,
    ExperimentPlan,
    ExperimentReport,
    ExperimentRule,
    ExperimentRun,
)

REPORT_LIBRARY_DIRECTORY = APPLICATION_PATHS.experiment_reports
MAX_SAVED_REPORTS = 100
COMPARISON_METRICS = {
    "final_density": ("Final density", "mean_final_density", "%"),
    "entropy": ("State entropy", "mean_entropy", ""),
    "block_entropy": ("Block entropy", "mean_block_entropy", ""),
    "change_rate": ("Change rate", "mean_change_rate", "%"),
}


@dataclass(frozen=True)
class SavedExperimentSummary:
    """Small metadata record used by the report-library browser."""

    path: Path
    name: str
    dimension: str
    mode_label: str
    completed_at: str
    run_count: int
    configuration_count: int
    rule_names: tuple[str, ...]


@dataclass(frozen=True)
class ReportComparisonEntry:
    """Equal-configuration summary of one saved report for one metric."""

    summary: SavedExperimentSummary
    mean: float
    minimum: float
    maximum: float
    best_configuration: str
    design_summary: str


@dataclass(frozen=True)
class ReportComparison:
    """Descriptive comparison plus explicit compatibility cautions."""

    metric_key: str
    metric_label: str
    unit: str
    entries: tuple[ReportComparisonEntry, ...]
    notes: tuple[str, ...]

    @property
    def best(self) -> ReportComparisonEntry:
        return max(self.entries, key=lambda entry: entry.mean)


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a JSON object.")
    return value


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a JSON array.")
    return value


def _finite_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{label} must be numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def report_from_document(document: Mapping[str, Any]) -> ExperimentReport:
    """Validate and reconstruct an exported ExperimentReport document."""

    root = _require_mapping(document, "report")
    if root.get("schema") != EXPERIMENT_REPORT_SCHEMA:
        raise ValueError("Unsupported experiment-report schema.")
    if root.get("version") != EXPERIMENT_REPORT_VERSION:
        raise ValueError("Unsupported experiment-report version.")
    plan_document = _require_mapping(root["plan"], "plan")
    rules = tuple(
        ExperimentRule(
            key=str(rule_document["key"]),
            name=str(rule_document["name"]),
            dimension=str(rule_document["dimension"]),
            engine=str(rule_document["engine"]),
            parameters=_require_mapping(rule_document["parameters"], "rule parameters"),
        )
        for rule_document in (
            _require_mapping(value, "rule")
            for value in _require_sequence(plan_document["rules"], "plan.rules")
        )
    )
    plan = ExperimentPlan(
        dimension=str(plan_document["dimension"]),
        mode_label=str(plan_document["mode_label"]),
        rules=rules,
        boundaries=tuple(
            str(value)
            for value in _require_sequence(
                plan_document["boundaries"], "plan.boundaries"
            )
        ),
        sizes=tuple(
            int(value)
            for value in _require_sequence(plan_document["sizes"], "plan.sizes")
        ),
        generation_counts=tuple(
            int(value)
            for value in _require_sequence(
                plan_document["generation_counts"], "plan.generation_counts"
            )
        ),
        repetitions=int(plan_document["repetitions"]),
        seed_kinds=tuple(
            str(value)
            for value in _require_sequence(
                plan_document["seed_kinds"], "plan.seed_kinds"
            )
        ),
        seed_densities=tuple(
            _finite_number(value, "seed density")
            for value in _require_sequence(
                plan_document["seed_densities"], "plan.seed_densities"
            )
        ),
        master_seed=int(plan_document["master_seed"]),
    )
    runs = tuple(
        ExperimentRun(**dict(_require_mapping(value, "run")))
        for value in _require_sequence(root["runs"], "runs")
    )
    aggregates = tuple(
        ExperimentAggregate(**dict(_require_mapping(value, "aggregate")))
        for value in _require_sequence(root["aggregates"], "aggregates")
    )
    if not runs or not aggregates:
        raise ValueError("An experiment report must contain runs and aggregates.")
    return ExperimentReport(
        plan=plan,
        runs=runs,
        aggregates=aggregates,
        elapsed_seconds=_finite_number(root["elapsed_seconds"], "elapsed_seconds"),
        completed_at=str(root["completed_at"]),
    )


def load_experiment_report(path: Path) -> ExperimentReport:
    """Read one UTF-8 report with controlled parse and validation failures."""

    try:
        with Path(path).open("r", encoding="utf-8") as source:
            document = json.load(source)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Could not read experiment report: {exc}") from exc
    try:
        return report_from_document(_require_mapping(document, "report"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid experiment report: {exc}") from exc


def _display_name(report: ExperimentReport) -> str:
    timestamp = report.completed_at.replace("T", " ")[:19]
    return f"{report.plan.dimension.upper()} · {report.plan.mode_label} · {timestamp}"


def _safe_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_value).strip("._-")
    slug = slug.replace("..", "-")
    return slug[:80] or "experiment"


def _summary(
    path: Path,
    report: ExperimentReport,
    name: str | None = None,
) -> SavedExperimentSummary:
    return SavedExperimentSummary(
        path=path,
        name=(name or _display_name(report)).strip(),
        dimension=report.plan.dimension,
        mode_label=report.plan.mode_label,
        completed_at=report.completed_at,
        run_count=len(report.runs),
        configuration_count=len(report.aggregates),
        rule_names=tuple(rule.name for rule in report.plan.rules),
    )


class ExperimentReportLibrary:
    """Cached, bounded collection of application-managed report documents."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory or REPORT_LIBRARY_DIRECTORY)
        self.entries: tuple[SavedExperimentSummary, ...] = ()
        self.errors: tuple[str, ...] = ()

    def refresh(self) -> tuple[SavedExperimentSummary, ...]:
        entries: list[SavedExperimentSummary] = []
        errors: list[str] = []
        try:
            paths = tuple(self.directory.glob("*.json")) if self.directory.is_dir() else ()
        except OSError as exc:
            self.entries = ()
            self.errors = (str(exc),)
            return self.entries
        for path in paths:
            try:
                with path.open("r", encoding="utf-8") as source:
                    document = _require_mapping(json.load(source), "report")
                report = report_from_document(document)
                name_value = document.get("library_name")
                name = str(name_value).strip() if name_value is not None else None
                entries.append(_summary(path, report, name or None))
            except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{path.name}: {exc}")
        entries.sort(key=lambda item: item.completed_at, reverse=True)
        self.entries = tuple(entries)
        self.errors = tuple(errors)
        return self.entries

    def save(
        self,
        report: ExperimentReport,
        name: str | None = None,
    ) -> SavedExperimentSummary:
        current = self.refresh()
        if len(current) >= MAX_SAVED_REPORTS:
            raise ValueError(
                f"The report library is limited to {MAX_SAVED_REPORTS} saved experiments."
            )
        display_name = (name or _display_name(report)).strip()
        if not display_name:
            raise ValueError("Saved experiment name cannot be empty.")
        self.directory.mkdir(parents=True, exist_ok=True)
        base = _safe_slug(display_name)
        path = self.directory / f"{base}.json"
        suffix = 2
        while path.exists():
            path = self.directory / f"{base}-{suffix}.json"
            suffix += 1
        temporary = path.with_suffix(".json.tmp")
        document = report.as_document()
        document["library_name"] = display_name
        try:
            temporary.unlink(missing_ok=True)
            with temporary.open("x", encoding="utf-8") as output:
                json.dump(document, output, ensure_ascii=False, indent=2)
                output.flush()
            temporary.replace(path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        self.refresh()
        return next(entry for entry in self.entries if entry.path == path)

    def load(self, entry: SavedExperimentSummary) -> ExperimentReport:
        if entry.path.parent.resolve() != self.directory.resolve():
            raise ValueError("Saved report is outside the experiment library.")
        return load_experiment_report(entry.path)

    def delete(self, entry: SavedExperimentSummary) -> None:
        if entry.path.parent.resolve() != self.directory.resolve():
            raise ValueError("Saved report is outside the experiment library.")
        entry.path.unlink()
        self.refresh()


def compare_reports(
    reports: Sequence[tuple[SavedExperimentSummary, ExperimentReport]],
    metric_key: str,
) -> ReportComparison:
    """Compare equal-weight configuration means without claiming causality."""

    if metric_key not in COMPARISON_METRICS:
        raise ValueError(f"Unknown comparison metric: {metric_key}.")
    if not 2 <= len(reports) <= 3:
        raise ValueError("Select two or three saved reports to compare.")
    metric_label, attribute, unit = COMPARISON_METRICS[metric_key]
    entries: list[ReportComparisonEntry] = []
    for summary, report in reports:
        values = [float(getattr(item, attribute)) for item in report.aggregates]
        best = max(report.aggregates, key=lambda item: float(getattr(item, attribute)))
        entries.append(
            ReportComparisonEntry(
                summary=summary,
                mean=sum(values) / len(values),
                minimum=min(values),
                maximum=max(values),
                best_configuration=(
                    f"{best.rule_name}, {best.boundary}, size {best.size}, "
                    f"generation {best.generations}"
                ),
                design_summary=(
                    f"rules {len(report.plan.rules)} · boundaries "
                    f"{','.join(report.plan.boundaries)} · sizes "
                    f"{','.join(str(value) for value in report.plan.sizes)} · generations "
                    f"{','.join(str(value) for value in report.plan.generation_counts)} · "
                    f"repetitions {report.plan.repetitions}"
                ),
            )
        )

    notes: list[str] = []
    dimensions = {report.plan.dimension for _summary_item, report in reports}
    modes = {report.plan.mode_label for _summary_item, report in reports}
    if len(dimensions) > 1 or len(modes) > 1:
        notes.append(
            "Dimensions or modes differ; treat the comparison as descriptive, not like-for-like."
        )
    factor_signatures = {
        (
            report.plan.boundaries,
            report.plan.sizes,
            report.plan.generation_counts,
            report.plan.seed_kinds,
            report.plan.seed_densities,
            report.plan.repetitions,
        )
        for _summary_item, report in reports
    }
    if len(factor_signatures) > 1:
        notes.append(
            "Parameter grids differ; experiment-level means give each configuration equal weight."
        )
    if not notes:
        notes.append(
            "The experiments share dimension, mode, and parameter grid; seeds may still differ."
        )
    notes.append(
        "Ranges show configuration spread and are not confidence intervals or causal effects."
    )
    return ReportComparison(
        metric_key,
        metric_label,
        unit,
        tuple(entries),
        tuple(notes),
    )
