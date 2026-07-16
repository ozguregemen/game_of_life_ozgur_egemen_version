"""Application-facing coordinator for contextual experiment exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

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
from three_dimensional_modes import ALL_RULES_3D, MODE_LABELS_3D
from themes import (
    COLORBLIND_CYCLIC_PALETTE,
    COLORBLIND_BLUE,
    COLORBLIND_MAGENTA,
    COLORBLIND_SKY,
    COLORBLIND_YELLOW,
    CYCLIC_PALETTE,
    LIGHT_MODE_BLUE,
    LIGHT_MODE_ORANGE,
    LIGHT_MODE_PURPLE,
    LIGHT_MODE_TEAL,
    THEMES,
    one_d_state_color,
)
from timeline_history import TimelineStatus
from wireworld import CONDUCTOR, ELECTRON_HEAD, ELECTRON_TAIL, EMPTY as WIRE_EMPTY


THREE_D_ATLAS_SEPARATOR = 255


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
    three_d_snapshot: Callable[[], Mapping[str, Any]]
    three_d_context: Callable[[], Mapping[str, Any]]
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
        if dimension == "3d":
            context = self.services.three_d_context()
            mode_key = str(context["mode"])
            rule_key = str(context["rule"])
            shape = tuple(int(value) for value in context["shape"])
            rule = ALL_RULES_3D[rule_key]
            return (
                f"3D {MODE_LABELS_3D[mode_key]} | {rule.name} {rule.notation} | "
                f"Volume {shape[2]}x{shape[1]}x{shape[0]} | "
                f"Generation {generation}"
            )
        mode = self.services.active_mode()
        return f"2D {MODE_BY_KEY[mode].name} | Generation {generation}"

    def _stem(self, category: str) -> str:
        generation = self.services.current_generation()
        if self.services.active_dimension() == "1d":
            rule = self.services.elementary_rule()
            return f"1d-rule-{rule}-generation-{generation}-{category}"
        if self.services.active_dimension() == "3d":
            context = self.services.three_d_context()
            return (
                f"3d-{context['mode']}-{context['rule']}-"
                f"generation-{generation}-{category}"
            )
        return (
            f"2d-{self.services.active_mode()}-generation-{generation}-{category}"
        )

    @staticmethod
    def _from_1d_snapshot(snapshot: Mapping[str, Any]) -> RasterFrame:
        primary_source = tuple(
            tuple(int(cell) for cell in row) for row in snapshot["rows"]
        )

        def align_outside_states(
            rows: tuple[tuple[int, ...], ...],
            raw_backgrounds: Any,
            fallback: int,
        ) -> tuple[tuple[int, ...], ...]:
            """Center rows and materialize each generation's infinite background."""
            if not rows:
                return ()
            backgrounds = (
                tuple(int(value) for value in raw_backgrounds)
                if isinstance(raw_backgrounds, Sequence)
                else ()
            )
            if len(backgrounds) != len(rows):
                backgrounds = (0,) * max(0, len(rows) - 1) + (fallback,)
            width = max(len(row) for row in rows)
            aligned: list[tuple[int, ...]] = []
            for row, outside in zip(rows, backgrounds):
                missing = width - len(row)
                left = missing // 2
                aligned.append(
                    (outside,) * left
                    + row
                    + (outside,) * (missing - left)
                )
            return tuple(aligned)

        primary_rows = align_outside_states(
            primary_source,
            snapshot.get("row_backgrounds"),
            int(snapshot.get("background", 0)),
        )
        raw_spec = snapshot.get("rule_spec")
        state_count = (
            int(raw_spec.get("states", 2))
            if isinstance(raw_spec, Mapping)
            else 2
        )
        secondary_offset = max(1, state_count - 1)
        comparison = snapshot.get("comparison")
        if isinstance(comparison, Mapping) and bool(comparison.get("enabled")):
            secondary_source = tuple(
                tuple(int(cell) for cell in row)
                for row in comparison.get("rows", ())
            )
            secondary_rows = align_outside_states(
                secondary_source,
                comparison.get("row_backgrounds"),
                int(comparison.get("background", 0)),
            )
            secondary_rows = tuple(
                tuple(
                    0 if int(cell) == 0 else int(cell) + secondary_offset
                    for cell in row
                )
                for row in secondary_rows
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
                0 <= row < len(rows)
                and 0 <= column < len(rows[0])
            ):
                rows[row][column] = 2 if bool(ant["active"]) else 3
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

    @staticmethod
    def _from_3d_snapshot(snapshot: Mapping[str, Any]) -> RasterFrame:
        """Create a deterministic XY/XZ/YZ atlas from one 3D volume snapshot."""

        shape = tuple(int(value) for value in snapshot["shape"])
        if len(shape) != 3 or any(length < 1 for length in shape):
            raise ValueError("3D export shape must contain three positive axes")
        raw_cells = snapshot["cells"]
        if isinstance(raw_cells, (bytes, bytearray, memoryview)):
            cells = np.frombuffer(raw_cells, dtype=np.uint8)
            if cells.size != int(np.prod(shape)):
                raise ValueError("3D export cell bytes do not match the volume shape")
            cells = cells.reshape(shape)
        else:
            cells = np.asarray(raw_cells, dtype=np.uint8)
            if cells.shape != shape:
                raise ValueError("3D export cells do not match the volume shape")

        state_count = int(snapshot["state_count"])
        if state_count < 2 or np.any(cells >= state_count):
            raise ValueError("3D export contains a state outside its rule range")

        slice_state = snapshot.get("slice", {})
        axis = str(snapshot.get("slice_axis", slice_state.get("axis", "z")))
        selected_index = int(
            snapshot.get("slice_index", slice_state.get("index", shape[0] // 2))
        )
        if axis not in ("z", "y", "x"):
            raise ValueError("3D export slice axis must be x, y, or z")
        axis_lengths = {"z": shape[0], "y": shape[1], "x": shape[2]}
        if not 0 <= selected_index < axis_lengths[axis]:
            raise ValueError("3D export slice index is outside the volume")

        z_index = selected_index if axis == "z" else shape[0] // 2
        y_index = selected_index if axis == "y" else shape[1] // 2
        x_index = selected_index if axis == "x" else shape[2] // 2
        xy = cells[z_index, :, :]
        xz = cells[:, y_index, :]
        yz = cells[:, :, x_index].T

        depth, rows, columns = shape
        atlas = np.full(
            (rows + 1 + depth, columns + 1 + depth),
            THREE_D_ATLAS_SEPARATOR,
            dtype=np.uint8,
        )
        atlas[:rows, :columns] = xy
        atlas[:rows, columns + 1 :] = yz
        atlas[rows + 1 :, :columns] = xz
        atlas[rows + 1 :, columns + 1 :] = 0
        return RasterFrame(
            generation=int(snapshot["generation"]),
            rows=tuple(tuple(int(cell) for cell in row) for row in atlas),
        )

    def palette(self) -> dict[int, tuple[int, int, int]]:
        theme_name = self.services.theme_name()
        theme = THEMES[theme_name]
        background = theme["background"]
        if self.services.active_dimension() == "1d":
            spec = self._one_d_spec()
            palette = {0: background}
            secondary_offset = max(1, spec.states - 1)
            for state in range(1, spec.states):
                palette[state] = one_d_state_color(
                    state,
                    spec.states,
                    theme_name,
                )
                palette[state + secondary_offset] = one_d_state_color(
                    state,
                    spec.states,
                    theme_name,
                    secondary=True,
                )
            return palette
        if self.services.active_dimension() == "3d":
            context = self.services.three_d_context()
            state_count = int(context["state_count"])
            active = (
                COLORBLIND_YELLOW
                if theme_name == "colorblind"
                else theme["cell"]
            )
            decay = (
                COLORBLIND_MAGENTA
                if theme_name == "colorblind"
                else (255, 42, 10)
            )
            palette = {
                0: background,
                1: active,
                THREE_D_ATLAS_SEPARATOR: theme["grid"],
            }
            for state in range(2, state_count):
                amount = (state - 1) / max(1, state_count - 2)
                palette[state] = tuple(
                    round(source + (target - source) * amount)
                    for source, target in zip(active, decay, strict=True)
                )
            return palette
        mode = self.services.active_mode()
        if mode == "life":
            return {0: background, 1: theme["cell"]}
        if mode == "immigration":
            if theme_name == "colorblind":
                return {
                    0: background,
                    1: COLORBLIND_BLUE,
                    2: COLORBLIND_YELLOW,
                }
            if theme_name in ("pastel", "paper"):
                return {0: background, 1: LIGHT_MODE_BLUE, 2: LIGHT_MODE_ORANGE}
            return {0: background, 1: (40, 180, 255), 2: (255, 135, 35)}
        if mode == "brians_brain":
            if theme_name == "colorblind":
                return {
                    0: background,
                    1: COLORBLIND_YELLOW,
                    2: COLORBLIND_SKY,
                }
            if theme_name in ("pastel", "paper"):
                return {0: background, 1: LIGHT_MODE_TEAL, 2: LIGHT_MODE_PURPLE}
            if theme_name == "midnight":
                return {0: background, 1: (80, 235, 255), 2: (170, 120, 230)}
            return {0: background, 1: (80, 235, 255), 2: (75, 55, 155)}
        if mode == "langtons_ant":
            ant = COLORBLIND_BLUE if theme_name == "colorblind" else (230, 35, 45)
            stopped = (
                COLORBLIND_MAGENTA
                if theme_name == "colorblind"
                else (125, 35, 40)
            )
            return {
                0: (235, 235, 225),
                1: (24, 25, 30),
                2: ant,
                3: stopped,
            }
        if mode == "wireworld":
            if theme_name == "colorblind":
                return {
                    WIRE_EMPTY: (16, 24, 32),
                    ELECTRON_HEAD: COLORBLIND_SKY,
                    ELECTRON_TAIL: COLORBLIND_MAGENTA,
                    CONDUCTOR: COLORBLIND_YELLOW,
                }
            return {
                WIRE_EMPTY: (10, 12, 18),
                ELECTRON_HEAD: (65, 170, 255),
                ELECTRON_TAIL: (235, 65, 55),
                CONDUCTOR: (245, 190, 35),
            }
        if mode == "cyclic_automaton":
            cyclic = (
                COLORBLIND_CYCLIC_PALETTE
                if theme_name == "colorblind"
                else CYCLIC_PALETTE
            )
            return dict(enumerate(cyclic))
        raise ValueError(f"Unknown export mode: {mode}")

    def capture_current_raster(self) -> RasterFrame:
        if self.services.active_dimension() == "1d":
            return self._from_1d_snapshot(self.services.elementary_snapshot())
        if self.services.active_dimension() == "3d":
            return self._from_3d_snapshot(self.services.three_d_snapshot())
        mode = self.services.active_mode()
        return self._from_2d_snapshot(mode, self.services.two_d_snapshot(mode))

    def capture_timeline_rasters(self) -> tuple[RasterFrame, ...]:
        snapshots = self.services.timeline_snapshots()
        if self.services.active_dimension() == "1d":
            return tuple(self._from_1d_snapshot(snapshot) for snapshot in snapshots)
        if self.services.active_dimension() == "3d":
            return tuple(self._from_3d_snapshot(snapshot) for snapshot in snapshots)
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
            export_mode = "one_dimensional_ca"
        elif dimension == "3d":
            context = self.services.three_d_context()
            rule = ALL_RULES_3D[str(context["rule"])]
            export_mode = str(context["mode"])
            name = (
                f"{MODE_LABELS_3D[export_mode]} {rule.name} "
                f"generation {generation}"
            )
        else:
            name = f"{MODE_BY_KEY[mode].name} generation {generation}"
            export_mode = mode
        document = self.services.session_document(name)
        series = self.services.analysis_series()
        history = self.services.history_status()
        window = series.window_summary(window=100)
        document["experiment_export"] = {
            "schema": "cellular-automata-lab/experiment-export",
            "version": 2,
            "dimension": dimension,
            "mode": export_mode,
            "generation": generation,
            "timeline": {
                "frame_count": history.frame_count,
                "cursor": history.cursor,
                "generations": list(history.generations),
            },
            "analysis": {
                "title": series.title,
                "population_label": series.population_label,
                "lattice_shape": list(series.lattice_shape),
                "lattice_dimension": len(series.lattice_shape),
                "state_count": series.state_count,
                "period": series.period,
                "stabilization_generation": series.stabilization_generation,
                "heuristic_regime": series.heuristic_regime(),
                "window_summary": {
                    "sample_count": window.sample_count,
                    "start_generation": window.start_generation,
                    "end_generation": window.end_generation,
                    "metrics": {
                        key: {
                            "current": value.current,
                            "mean": value.mean,
                            "standard_deviation": value.standard_deviation,
                            "minimum": value.minimum,
                            "maximum": value.maximum,
                            "slope_per_generation": value.slope_per_generation,
                        }
                        for key, value in window.metrics.items()
                    },
                },
                "methodology": {
                    "state_entropy": "Shannon entropy normalized by log2(state_count)",
                    "block_entropy": (
                        "Non-overlapping length-3 (1D), 2x2 (2D), or 2x2x2 (3D) "
                        "Shannon block entropy normalized by block capacity"
                    ),
                    "change_rate": "Hamming distance from the preceding generation",
                    "neighbor_agreement": (
                        "Equal-state share of interior orthogonal adjacent pairs"
                    ),
                    "regime": "Heuristic descriptor; not a formal dynamical proof",
                },
                "samples": [
                    {
                        "generation": sample.generation,
                        "population": sample.population,
                        "density_percent": sample.density,
                        "normalized_entropy": sample.entropy,
                        "normalized_block_entropy": sample.block_entropy,
                        "change_rate_percent": sample.change_rate,
                        "neighbor_agreement_percent": sample.neighbor_agreement,
                        "population_growth_percent_of_lattice": sample.growth_rate,
                        "state_utilization_percent": sample.state_utilization,
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
