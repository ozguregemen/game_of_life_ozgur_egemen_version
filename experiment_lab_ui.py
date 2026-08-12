"""Pygame presentation for bounded, reproducible CA parameter sweeps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from experiment_lab import (
    ExperimentCancelled,
    ExperimentContext,
    ExperimentPlan,
    ExperimentReport,
    ExperimentRunner,
    SEED_RANDOM,
    export_experiment_csv,
    export_experiment_json,
)


@dataclass(frozen=True)
class ExperimentLabViewServices:
    screen: Callable[[], pygame.Surface]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    context: Callable[[], ExperimentContext]
    master_seed: Callable[[], int]
    set_status: Callable[[str, float], None]


class ExperimentLabView:
    """Own controls and results while the numerical worker stays UI-independent."""

    GENERATION_OPTIONS = {
        "1d": (80, 160, 320),
        "2d": (50, 100, 200),
        "3d": (20, 40, 80),
    }
    REPETITION_OPTIONS = (1, 3, 5)
    DENSITY_OPTIONS = (0.10, 0.20, 0.35)

    def __init__(
        self,
        services: ExperimentLabViewServices,
        runner: ExperimentRunner,
    ) -> None:
        self.services = services
        self.runner = runner
        self.report: ExperimentReport | None = None
        self.error = ""
        self.cancelled = False
        self.result_scroll = 0
        self._context_signature: tuple[object, ...] = ()
        self._context: ExperimentContext | None = None
        self.rule_count = 1
        self.boundary_sweep = False
        self.size_index = 0
        self.generation_index = 1
        self.repetition_index = 1
        self.seed_index = 0
        self.density_index = 1

    @staticmethod
    def _fit(font: pygame.font.Font, value: str, width: int) -> str:
        if font.size(value)[0] <= width:
            return value
        suffix = "..."
        while value and font.size(value + suffix)[0] > width:
            value = value[:-1]
        return value.rstrip() + suffix

    def _sync_context(self) -> ExperimentContext:
        context = self.services.context()
        signature = (
            context.dimension,
            context.mode_label,
            tuple(rule.key for rule in context.rules),
            context.boundaries,
            context.size_options,
            context.seed_kinds,
        )
        if signature != self._context_signature:
            if self._context_signature and self.runner.running:
                self.runner.cancel()
                self.services.set_status(
                    "Workspace changed; the previous background experiment was cancelled.",
                    3.0,
                )
            self._context_signature = signature
            self._context = context
            self.rule_count = min(3, len(context.rules))
            self.boundary_sweep = False
            self.size_index = min(1, len(context.size_options) - 1)
            self.generation_index = 1
            self.repetition_index = 1
            self.seed_index = (
                context.seed_kinds.index(SEED_RANDOM)
                if SEED_RANDOM in context.seed_kinds
                else 0
            )
            self.density_index = min(
                range(len(self.DENSITY_OPTIONS)),
                key=lambda index: abs(
                    self.DENSITY_OPTIONS[index] - context.default_seed_density
                ),
            )
            self.report = None
            self.error = ""
            self.result_scroll = 0
        return context

    def _plan(self) -> ExperimentPlan:
        context = self._sync_context()
        seed_kind = context.seed_kinds[self.seed_index]
        repetitions = self.REPETITION_OPTIONS[self.repetition_index]
        if seed_kind != SEED_RANDOM:
            repetitions = 1
        return ExperimentPlan(
            dimension=context.dimension,
            mode_label=context.mode_label,
            rules=context.rules[: self.rule_count],
            boundaries=(
                context.boundaries if self.boundary_sweep else context.boundaries[:1]
            ),
            size=context.size_options[self.size_index],
            generations=self.GENERATION_OPTIONS[context.dimension][
                self.generation_index
            ],
            repetitions=repetitions,
            seed_kind=seed_kind,
            seed_density=self.DENSITY_OPTIONS[self.density_index],
            master_seed=self.services.master_seed(),
        )

    def request(self) -> None:
        try:
            plan = self._plan()
        except (TypeError, ValueError) as exc:
            self.error = str(exc)
            self.services.set_status(f"Experiment rejected: {exc}", 4.0)
            return
        if self.runner.request(plan):
            self.report = None
            self.error = ""
            self.cancelled = False
            self.result_scroll = 0
            self.services.set_status(
                f"Experiment started: {plan.run_count} bounded runs in background.",
                3.0,
            )

    def update(self) -> None:
        try:
            report = self.runner.poll()
        except ExperimentCancelled:
            self.cancelled = True
            self.services.set_status("Experiment cancelled safely.", 2.5)
            return
        except Exception as exc:  # A failed sweep must not stop the application.
            self.error = str(exc)
            self.services.set_status(f"Experiment failed: {exc}", 4.0)
            return
        if report is not None:
            self.report = report
            self.services.set_status(
                f"Experiment complete: {len(report.runs)} runs in "
                f"{report.elapsed_seconds:.2f} s.",
                4.0,
            )

    def geometry(self, content: pygame.Rect) -> dict[str, pygame.Rect]:
        gap = 7
        header = pygame.Rect(content.x, content.y, content.width, 57)
        controls_top = header.bottom + gap
        control_height = 30
        control_width = (content.width - 3 * gap) // 4
        rects: dict[str, pygame.Rect] = {"header": header}
        first = ("rules", "boundaries", "size", "generations")
        second = ("repetitions", "seed", "density", "run")
        for row, names in enumerate((first, second)):
            y = controls_top + row * (control_height + gap)
            for column, name in enumerate(names):
                rects[name] = pygame.Rect(
                    content.x + column * (control_width + gap),
                    y,
                    control_width,
                    control_height,
                )
        action_y = rects["repetitions"].bottom + gap
        export_width = min(150, (content.width - gap) // 2)
        rects["csv"] = pygame.Rect(content.right - 2 * export_width - gap, action_y, export_width, 28)
        rects["json"] = pygame.Rect(content.right - export_width, action_y, export_width, 28)
        rects["table"] = pygame.Rect(
            content.x,
            action_y + 35,
            content.width,
            max(1, content.bottom - action_y - 35),
        )
        return rects

    def handle_event(self, event: pygame.event.Event, content: pygame.Rect) -> bool:
        context = self._sync_context()
        rects = self.geometry(content)
        if event.type == pygame.MOUSEWHEEL and rects["table"].collidepoint(
            pygame.mouse.get_pos()
        ):
            self.result_scroll = max(0, self.result_scroll - event.y)
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        position = event.pos
        if rects["rules"].collidepoint(position):
            self.rule_count = self.rule_count % len(context.rules) + 1
        elif rects["boundaries"].collidepoint(position):
            if len(context.boundaries) > 1:
                self.boundary_sweep = not self.boundary_sweep
        elif rects["size"].collidepoint(position):
            self.size_index = (self.size_index + 1) % len(context.size_options)
        elif rects["generations"].collidepoint(position):
            options = self.GENERATION_OPTIONS[context.dimension]
            self.generation_index = (self.generation_index + 1) % len(options)
        elif rects["repetitions"].collidepoint(position):
            self.repetition_index = (
                self.repetition_index + 1
            ) % len(self.REPETITION_OPTIONS)
        elif rects["seed"].collidepoint(position):
            self.seed_index = (self.seed_index + 1) % len(context.seed_kinds)
        elif rects["density"].collidepoint(position):
            self.density_index = (
                self.density_index + 1
            ) % len(self.DENSITY_OPTIONS)
        elif rects["run"].collidepoint(position):
            if self.runner.running:
                self.runner.cancel()
            else:
                self.request()
        elif rects["csv"].collidepoint(position) and self.report is not None:
            try:
                path = export_experiment_csv(self.report)
            except OSError as exc:
                self.services.set_status(f"CSV export failed: {exc}", 4.0)
            else:
                self.services.set_status(f"Experiment CSV saved: {path}", 5.0)
        elif rects["json"].collidepoint(position) and self.report is not None:
            try:
                path = export_experiment_json(self.report)
            except OSError as exc:
                self.services.set_status(f"JSON export failed: {exc}", 4.0)
            else:
                self.services.set_status(f"Experiment JSON saved: {path}", 5.0)
        else:
            return False
        return True

    def _button(
        self,
        rect: pygame.Rect,
        label: str,
        *,
        enabled: bool = True,
        accent: tuple[int, int, int] | None = None,
    ) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        fill = theme["button_hover"] if enabled else theme["stats_bar"]
        pygame.draw.rect(screen, fill, rect, border_radius=4)
        pygame.draw.rect(screen, accent or theme["grid"], rect, 2 if accent else 1, border_radius=4)
        color = theme["button_text"] if enabled else theme["grid"]
        font = self.services.tiny_font()
        rendered = font.render(self._fit(font, label, rect.width - 10), True, color)
        screen.blit(rendered, rendered.get_rect(center=rect.center))

    def draw(self, content: pygame.Rect) -> None:
        self.update()
        context = self._sync_context()
        rects = self.geometry(content)
        screen = self.services.screen()
        theme = self.services.theme()
        pygame.draw.rect(screen, theme["stats_bar"], rects["header"], border_radius=6)
        plan_note = (
            f"{context.dimension.upper()} / {context.mode_label}  |  deterministic seed "
            f"{self.services.master_seed()}  |  bounded background worker"
        )
        font = self.services.small_font()
        screen.blit(
            font.render(self._fit(font, plan_note, rects["header"].width - 18), True, theme["text"]),
            (rects["header"].x + 9, rects["header"].y + 7),
        )
        detail = (
            "Sweep rules and boundaries with repeated seeds; report mean, population SD, "
            "entropy, density, change, period and stabilization."
        )
        tiny = self.services.tiny_font()
        screen.blit(
            tiny.render(self._fit(tiny, detail, rects["header"].width - 18), True, theme["text"]),
            (rects["header"].x + 9, rects["header"].y + 32),
        )

        selected_names = ", ".join(rule.name for rule in context.rules[: self.rule_count])
        boundary_label = (
            "All: " + ", ".join(context.boundaries)
            if self.boundary_sweep
            else context.boundaries[0]
        )
        seed_kind = context.seed_kinds[self.seed_index]
        repetitions = (
            1
            if seed_kind != SEED_RANDOM
            else self.REPETITION_OPTIONS[self.repetition_index]
        )
        self._button(rects["rules"], f"Rules ({self.rule_count}): {selected_names}")
        self._button(rects["boundaries"], f"Boundary: {boundary_label}")
        self._button(rects["size"], f"Size per axis: {context.size_options[self.size_index]}")
        self._button(
            rects["generations"],
            f"Generations: {self.GENERATION_OPTIONS[context.dimension][self.generation_index]}",
        )
        self._button(rects["repetitions"], f"Repetitions: {repetitions}")
        self._button(rects["seed"], f"Seed: {seed_kind.replace('_', ' ').title()}")
        self._button(
            rects["density"],
            f"Random density: {100 * self.DENSITY_OPTIONS[self.density_index]:.0f}%",
            enabled=seed_kind == SEED_RANDOM,
        )
        self._button(
            rects["run"],
            "Cancel safely" if self.runner.running else "Run experiment",
            accent=(235, 100, 145) if self.runner.running else (90, 220, 130),
        )
        self._button(rects["csv"], "Export analysis CSV", enabled=self.report is not None)
        self._button(rects["json"], "Export reproducible JSON", enabled=self.report is not None)

        if self.runner.running:
            progress = self.runner.progress
            label = (
                f"Running {progress.completed_runs}/{progress.total_runs}"
                f"  {progress.rule_name} / {progress.boundary}"
            )
            self._draw_message(rects["table"], label, (80, 195, 255), progress.fraction)
        elif self.error:
            self._draw_message(rects["table"], f"Experiment failed: {self.error}", (245, 95, 95))
        elif self.cancelled and self.report is None:
            self._draw_message(rects["table"], "Experiment cancelled; no partial result was exported.", (225, 175, 65))
        elif self.report is None:
            try:
                estimated = self._plan().run_count
            except (TypeError, ValueError) as exc:
                self._draw_message(
                    rects["table"],
                    f"Adjust this plan: {exc}",
                    (225, 175, 65),
                )
            else:
                self._draw_message(
                    rects["table"],
                    f"Ready. Current plan contains {estimated} independent run(s).",
                    (90, 220, 130),
                )
        else:
            self._draw_results(rects["table"], self.report)

    def _draw_message(
        self,
        rect: pygame.Rect,
        message: str,
        color: tuple[int, int, int],
        progress: float | None = None,
    ) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        pygame.draw.rect(screen, theme["stats_bar"], rect, border_radius=6)
        rendered = self.services.small_font().render(
            self._fit(self.services.small_font(), message, rect.width - 30),
            True,
            color,
        )
        screen.blit(rendered, rendered.get_rect(center=rect.center))
        if progress is not None:
            track = pygame.Rect(rect.x + 40, rect.centery + 28, rect.width - 80, 8)
            pygame.draw.rect(screen, theme["grid"], track, border_radius=4)
            fill = track.copy()
            fill.width = round(track.width * max(0.0, min(1.0, progress)))
            pygame.draw.rect(screen, color, fill, border_radius=4)

    def _draw_results(self, rect: pygame.Rect, report: ExperimentReport) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        pygame.draw.rect(screen, theme["stats_bar"], rect, border_radius=6)
        summary = (
            f"{len(report.runs)} runs / {len(report.aggregates)} groups / "
            f"{report.elapsed_seconds:.2f} s  |  mean +/- population SD"
        )
        tiny = self.services.tiny_font()
        screen.blit(tiny.render(self._fit(tiny, summary, rect.width - 12), True, theme["text"]), (rect.x + 6, rect.y + 5))
        columns = (
            ("Rule", 0.23),
            ("Boundary", 0.10),
            ("n", 0.05),
            ("Final density", 0.17),
            ("Entropy", 0.11),
            ("Change", 0.11),
            ("Period", 0.10),
            ("Stabilize", 0.13),
        )
        header_y = rect.y + 27
        positions: list[tuple[int, int]] = []
        cursor = rect.x
        for _, fraction in columns:
            width = round(rect.width * fraction)
            positions.append((cursor, width))
            cursor += width
        pygame.draw.rect(screen, theme["button"], (rect.x, header_y, rect.width, 24))
        for (label, _), (x, width) in zip(columns, positions, strict=True):
            rendered = tiny.render(self._fit(tiny, label, width - 4), True, theme["text"])
            screen.blit(rendered, rendered.get_rect(center=(x + width // 2, header_y + 12)))
        row_height = 25
        visible = max(1, (rect.bottom - header_y - 25) // row_height)
        maximum_scroll = max(0, len(report.aggregates) - visible)
        self.result_scroll = min(self.result_scroll, maximum_scroll)
        selected = report.aggregates[
            self.result_scroll : self.result_scroll + visible
        ]
        for index, aggregate in enumerate(selected):
            y = header_y + 25 + index * row_height
            row = pygame.Rect(rect.x, y, rect.width, row_height - 1)
            pygame.draw.rect(screen, theme["button"] if index % 2 == 0 else theme["stats_bar"], row)
            stabilization = (
                "--"
                if aggregate.mean_stabilization_generation is None
                else f"{aggregate.mean_stabilization_generation:.1f}"
            )
            values = (
                aggregate.rule_name,
                aggregate.boundary,
                str(aggregate.repetitions),
                f"{aggregate.mean_final_density:.2f} +/- {aggregate.sd_final_density:.2f}%",
                f"{aggregate.mean_entropy:.3f} +/- {aggregate.sd_entropy:.3f}",
                f"{aggregate.mean_change_rate:.2f}%",
                (
                    f"{aggregate.mean_detected_period:.1f} ({aggregate.period_detection_rate:.0f}%)"
                    if aggregate.mean_detected_period is not None
                    else "-- (0%)"
                ),
                stabilization,
            )
            for value, (x, width) in zip(values, positions, strict=True):
                rendered = tiny.render(self._fit(tiny, value, width - 5), True, theme["text"])
                screen.blit(rendered, rendered.get_rect(center=(x + width // 2, row.centery)))
        if maximum_scroll:
            note = f"Rows {self.result_scroll + 1}-{self.result_scroll + len(selected)} of {len(report.aggregates)} (wheel to scroll)"
            rendered = tiny.render(note, True, theme["text"])
            screen.blit(rendered, (rect.right - rendered.get_width() - 5, rect.bottom - rendered.get_height() - 3))
