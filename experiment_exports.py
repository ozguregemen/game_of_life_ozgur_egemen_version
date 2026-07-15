"""Application-facing coordinator for contextual experiment exports."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from cyclic_automaton import DEFAULT_STATE_COUNT as CYCLIC_STATE_COUNT
from exporting import (
    ExportError,
    ExportRunner,
    RasterFrame,
    export_path,
    save_analysis_csv,
    save_experiment_json,
    save_gif,
    save_mp4,
    save_png,
)
from mode_registry import MODE_BY_KEY
from one_dimensional_ca import FAMILY_ELEMENTARY, RULE_FAMILY_BY_KEY, RuleSpec
from scientific_analysis import AnalysisSeries
from themes import THEMES
from timeline_history import TimelineStatus
from wireworld import CONDUCTOR, ELECTRON_HEAD, ELECTRON_TAIL, EMPTY as WIRE_EMPTY


@dataclass(frozen=True)
class ExperimentExportServices:
    """State capture and application callbacks required by the coordinator."""

    active_dimension: Callable[[], str]
    active_mode: Callable[[], str]
    theme_name: Callable[[], str]
    current_generation: Callable[[], int]
    elementary_rule: Callable[[], int]
    elementary_boundary: Callable[[], str]
    elementary_snapshot: Callable[[], Mapping[str, Any]]
    two_d_snapshot: Callable[[str], Mapping[str, Any]]
    timeline_snapshots: Callable[[], Sequence[Mapping[str, Any]]]
    analysis_series: Callable[[], AnalysisSeries]
    history_status: Callable[[], TimelineStatus]
    session_document: Callable[[str], dict[str, Any]]
    set_status: Callable[[str, float], None]


class ExperimentExportCoordinator:
    """Normalize workspace state and queue safe export encoders."""

    def __init__(
        self,
        services: ExperimentExportServices,
        runner: ExportRunner,
    ) -> None:
        self.services = services
        self.runner = runner

    def _one_d_spec(self) -> RuleSpec:
        snapshot = self.services.elementary_snapshot()
        raw_spec = snapshot.get("rule_spec")
        if isinstance(raw_spec, Mapping):
            return RuleSpec.from_mapping(raw_spec)
        return RuleSpec(
            FAMILY_ELEMENTARY,
            int(snapshot.get("rule", self.services.elementary_rule())),
            2,
            1,
        )

    def context_label(self) -> str:
        dimension = self.services.active_dimension()
        generation = self.services.current_generation()
        if dimension == "1d":
            spec = self._one_d_spec()
            return (
                f"1D {spec.definition.name} Code {spec.code} | "
                f"States: {spec.states} | Radius: {spec.radius} | "
                f"Generation {generation} | "
                f"Boundary: {self.services.elementary_boundary()}"
            )
        mode = self.services.active_mode()
        return f"2D {MODE_BY_KEY[mode].name} | Generation {generation}"

    def _stem(self, category: str) -> str:
        generation = self.services.current_generation()
        if self.services.active_dimension() == "1d":
            rule = self.services.elementary_rule()
            return f"1d-rule-{rule}-generation-{generation}-{category}"
        return (
            f"2d-{self.services.active_mode()}-generation-{generation}-{category}"
        )

    @staticmethod
    def _from_1d_snapshot(snapshot: Mapping[str, Any]) -> RasterFrame:
        primary_rows = tuple(
            tuple(int(cell) for cell in row) for row in snapshot["rows"]
        )
        comparison = snapshot.get("comparison")
        if isinstance(comparison, Mapping) and bool(comparison.get("enabled")):
            secondary_rows = tuple(
                tuple(int(cell) for cell in row)
                for row in comparison.get("rows", ())
            )
            if len(secondary_rows) == len(primary_rows):
                primary_rows = tuple(
                    (*primary, 0, 0, 0, *secondary)
                    for primary, secondary in zip(primary_rows, secondary_rows)
                )
        return RasterFrame(
            generation=int(snapshot["generation"]),
            rows=primary_rows,
        )

    @staticmethod
    def _normalized_2d_rows(
        mode: str,
        snapshot: Mapping[str, Any],
    ) -> tuple[tuple[int, ...], ...]:
        source = snapshot["grid"]
        if mode == "life":
            rows = [[1 if int(cell) > 0 else 0 for cell in row] for row in source]
        elif mode == "immigration":
            rows = [
                [
                    1 if int(cell) > 0 else 2 if int(cell) < 0 else 0
                    for cell in row
                ]
                for row in source
            ]
        else:
            rows = [[int(cell) for cell in row] for row in source]

        if mode == "langtons_ant":
            ant = snapshot["ant"]
            row = int(ant["row"])
            column = int(ant["col"])
            if (
                bool(ant["active"])
                and 0 <= row < len(rows)
                and 0 <= column < len(rows[0])
            ):
                rows[row][column] = 2
        return tuple(tuple(row) for row in rows)

    @classmethod
    def _from_2d_snapshot(
        cls,
        mode: str,
        snapshot: Mapping[str, Any],
    ) -> RasterFrame:
        return RasterFrame(
            generation=int(snapshot["generation"]),
            rows=cls._normalized_2d_rows(mode, snapshot),
        )

    def palette(self) -> dict[int, tuple[int, int, int]]:
        theme = THEMES[self.services.theme_name()]
        background = theme["background"]
        if self.services.active_dimension() == "1d":
            spec = self._one_d_spec()
            palette = {0: background, 1: theme["cell"]}
            for state in range(2, spec.states):
                red, green, blue = colorsys.hsv_to_rgb(
                    ((state - 1) / max(1, spec.states - 1) + 0.52) % 1.0,
                    0.72,
                    0.96,
                )
                palette[state] = (
                    round(red * 255),
                    round(green * 255),
                    round(blue * 255),
                )
            return palette
        mode = self.services.active_mode()
        if mode == "life":
            return {0: background, 1: theme["cell"]}
        if mode == "immigration":
            return {0: background, 1: (40, 180, 255), 2: (255, 135, 35)}
        if mode == "brians_brain":
            return {0: background, 1: (75, 235, 255), 2: (45, 90, 155)}
        if mode == "langtons_ant":
            return {0: (245, 245, 240), 1: (25, 25, 25), 2: (235, 55, 60)}
        if mode == "wireworld":
            return {
                WIRE_EMPTY: (10, 10, 12),
                ELECTRON_HEAD: (70, 165, 255),
                ELECTRON_TAIL: (245, 65, 50),
                CONDUCTOR: (245, 195, 35),
            }
        if mode == "cyclic_automaton":
            palette: dict[int, tuple[int, int, int]] = {}
            for state in range(CYCLIC_STATE_COUNT):
                red, green, blue = colorsys.hsv_to_rgb(
                    state / CYCLIC_STATE_COUNT,
                    0.78,
                    0.96,
                )
                palette[state] = (
                    round(red * 255),
                    round(green * 255),
                    round(blue * 255),
                )
            return palette
        raise ValueError(f"Unknown export mode: {mode}")

    def capture_current_raster(self) -> RasterFrame:
        if self.services.active_dimension() == "1d":
            return self._from_1d_snapshot(self.services.elementary_snapshot())
        mode = self.services.active_mode()
        return self._from_2d_snapshot(mode, self.services.two_d_snapshot(mode))

    def capture_timeline_rasters(self) -> tuple[RasterFrame, ...]:
        snapshots = self.services.timeline_snapshots()
        if self.services.active_dimension() == "1d":
            return tuple(self._from_1d_snapshot(snapshot) for snapshot in snapshots)
        mode = self.services.active_mode()
        return tuple(self._from_2d_snapshot(mode, snapshot) for snapshot in snapshots)

    def _queue(self, label: str, work: Callable[[], Path]) -> bool:
        if not self.runner.submit(label, work):
            self.services.set_status(
                f"Export already running: {self.runner.label}",
                4.0,
            )
            return False
        self.services.set_status(f"Exporting {label} in the background...", 3.0)
        return True

    def export_png(self) -> bool:
        try:
            frame = self.capture_current_raster()
            palette = self.palette()
            path = export_path(self._stem("diagram"), ".png")
        except (OSError, TypeError, ValueError, ExportError) as exc:
            self.services.set_status(f"PNG export could not start: {exc}", 5.0)
            return False
        return self._queue("PNG diagram", lambda: save_png(frame, palette, path))

    def _export_animation(self, format_name: str) -> bool:
        try:
            frames = self.capture_timeline_rasters()
            palette = self.palette()
            suffix = ".gif" if format_name == "GIF" else ".mp4"
            path = export_path(self._stem("timeline"), suffix)
        except (OSError, TypeError, ValueError, ExportError) as exc:
            self.services.set_status(
                f"{format_name} export could not start: {exc}",
                5.0,
            )
            return False
        work = (
            (lambda: save_gif(frames, palette, path))
            if format_name == "GIF"
            else (lambda: save_mp4(frames, palette, path))
        )
        return self._queue(f"{format_name} timeline", work)

    def export_gif(self) -> bool:
        return self._export_animation("GIF")

    def export_mp4(self) -> bool:
        return self._export_animation("MP4")

    def export_csv(self) -> bool:
        series = self.services.analysis_series()
        samples = tuple(series.samples)
        period = series.period
        stabilization_generation = series.stabilization_generation
        try:
            path = export_path(self._stem("metrics"), ".csv")
        except (OSError, TypeError, ValueError) as exc:
            self.services.set_status(f"CSV export could not start: {exc}", 5.0)
            return False
        return self._queue(
            "generation metrics CSV",
            lambda: save_analysis_csv(
                samples,
                path,
                period=period,
                stabilization_generation=stabilization_generation,
            ),
        )

    def capture_shareable_document(self) -> dict[str, Any]:
        dimension = self.services.active_dimension()
        mode = self.services.active_mode()
        generation = self.services.current_generation()
        if dimension == "1d":
            spec = self._one_d_spec()
            name = (
                f"{RULE_FAMILY_BY_KEY[spec.family].name} Code {spec.code} "
                f"generation {generation}"
            )
        else:
            name = f"{MODE_BY_KEY[mode].name} generation {generation}"
        document = self.services.session_document(name)
        series = self.services.analysis_series()
        history = self.services.history_status()
        document["experiment_export"] = {
            "schema": "cellular-automata-lab/experiment-export",
            "version": 1,
            "dimension": dimension,
            "mode": "one_dimensional_ca" if dimension == "1d" else mode,
            "generation": generation,
            "timeline": {
                "frame_count": history.frame_count,
                "cursor": history.cursor,
                "generations": list(history.generations),
            },
            "analysis": {
                "title": series.title,
                "population_label": series.population_label,
                "period": series.period,
                "stabilization_generation": series.stabilization_generation,
                "samples": [
                    {
                        "generation": sample.generation,
                        "population": sample.population,
                        "density_percent": sample.density,
                        "normalized_entropy": sample.entropy,
                        "change_rate_percent": sample.change_rate,
                    }
                    for sample in series.samples
                ],
            },
        }
        return document

    def export_json(self) -> bool:
        try:
            document = self.capture_shareable_document()
            path = export_path(self._stem("experiment"), ".json")
        except (OSError, TypeError, ValueError, ExportError) as exc:
            self.services.set_status(f"JSON export could not start: {exc}", 5.0)
            return False
        return self._queue(
            "shareable experiment JSON",
            lambda: save_experiment_json(document, path),
        )
