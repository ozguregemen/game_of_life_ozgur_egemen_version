"""Independent Pygame laboratory for reproducible multi-factor CA sweeps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Hashable

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
class ExperimentLabServices:
    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    content_width: Callable[[], int]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    context: Callable[[], ExperimentContext]
    master_seed: Callable[[], int]
    set_status: Callable[[str, float], None]
    pause: Callable[[], None]


class ExperimentLabPanel:
    """Full-size advanced tool kept separate from live Scientific Analysis."""

    def __init__(self, services: ExperimentLabServices, runner: ExperimentRunner) -> None:
        self.services = services
        self.runner = runner
        self.active = False
        self.tab = "design"
        self.view = ExperimentLabView(services, runner)

    def toggle(self) -> None:
        self.active = not self.active
        if self.active:
            self.services.pause()
            self.view.sync_context()

    def close(self) -> None:
        self.active = False

    def geometry(
        self,
    ) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
        width, height = self.services.window_size()
        content_width = self.services.content_width()
        modal = pygame.Rect(
            0,
            0,
            max(480, min(1320, content_width - 24)),
            max(420, min(860, height - 28)),
        )
        modal.center = (content_width // 2, height // 2)
        tab_width = min(210, (modal.width - 90) // 2)
        design_tab = pygame.Rect(modal.x + 20, modal.y + 53, tab_width, 31)
        results_tab = pygame.Rect(design_tab.right + 8, design_tab.y, tab_width, 31)
        close_button = pygame.Rect(modal.right - 43, modal.y + 13, 29, 27)
        content = pygame.Rect(
            modal.x + 18,
            design_tab.bottom + 9,
            modal.width - 36,
            modal.bottom - design_tab.bottom - 25,
        )
        return modal, design_tab, results_tab, close_button, content

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            modifiers = getattr(event, "mod", pygame.key.get_mods())
            if event.key == pygame.K_ESCAPE or (
                event.key == pygame.K_i and modifiers & pygame.KMOD_SHIFT
            ):
                self.close()
            elif event.key == pygame.K_RETURN and self.tab == "design":
                if self.view.request():
                    self.tab = "results"
            return True
        modal, design_tab, results_tab, close_button, content = self.geometry()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if close_button.collidepoint(event.pos) or not modal.collidepoint(event.pos):
                self.close()
            elif design_tab.collidepoint(event.pos):
                self.tab = "design"
            elif results_tab.collidepoint(event.pos):
                self.tab = "results"
            elif self.view.handle_event(event, content, self.tab):
                if self.view.runner.running:
                    self.tab = "results"
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.view.handle_event(event, content, self.tab)
            return True
        return event.type in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONUP,
        )

    def draw(self) -> None:
        if not self.active:
            return
        self.view.update()
        modal, design_tab, results_tab, close_button, content = self.geometry()
        screen = self.services.screen()
        theme = self.services.theme()
        shadow = pygame.Surface((modal.width + 12, modal.height + 12), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 120))
        screen.blit(shadow, (modal.x + 5, modal.y + 5))
        pygame.draw.rect(screen, theme["info_bar"], modal, border_radius=10)
        pygame.draw.rect(screen, theme["text"], modal, 2, border_radius=10)
        title = self.services.large_font().render(
            "Experiment Lab · Multi-factor CA Research",
            True,
            theme["text"],
        )
        screen.blit(title, (modal.x + 20, modal.y + 13))
        self._tab(design_tab, "Design Experiment", self.tab == "design")
        self._tab(results_tab, "Results & Export", self.tab == "results")
        pygame.draw.rect(screen, theme["button"], close_button, border_radius=4)
        pygame.draw.rect(screen, theme["text"], close_button, 1, border_radius=4)
        close_text = self.services.small_font().render("×", True, theme["text"])
        screen.blit(close_text, close_text.get_rect(center=close_button.center))
        if self.tab == "results":
            self.view.draw_results(content)
        else:
            self.view.draw_design(content)

    def _tab(self, rect: pygame.Rect, label: str, active: bool) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        pygame.draw.rect(
            screen,
            theme["button_hover"] if active else theme["button"],
            rect,
            border_radius=5,
        )
        pygame.draw.rect(
            screen,
            (90, 220, 130) if active else theme["grid"],
            rect,
            2 if active else 1,
            border_radius=5,
        )
        rendered = self.services.tiny_font().render(label, True, theme["button_text"])
        screen.blit(rendered, rendered.get_rect(center=rect.center))


class ExperimentLabView:
    """Selection state, validation, execution progress, and result rendering."""

    GENERATION_OPTIONS = {
        "1d": (80, 160, 320),
        "2d": (50, 100, 200),
        "3d": (20, 40, 80),
    }
    REPETITION_OPTIONS = (1, 3, 5)
    DENSITY_OPTIONS = (0.10, 0.20, 0.35)

    def __init__(self, services: ExperimentLabServices, runner: ExperimentRunner) -> None:
        self.services = services
        self.runner = runner
        self.report: ExperimentReport | None = None
        self.error = ""
        self.cancelled = False
        self.result_scroll = 0
        self._context_signature: tuple[object, ...] = ()
        self.context: ExperimentContext | None = None
        self.selected_rules: set[str] = set()
        self.selected_boundaries: set[str] = set()
        self.selected_sizes: set[int] = set()
        self.selected_generations: set[int] = set()
        self.selected_seed_kinds: set[str] = set()
        self.selected_densities: set[float] = set()
        self.repetition_index = 1

    @staticmethod
    def _fit(font: pygame.font.Font, value: str, width: int) -> str:
        if font.size(value)[0] <= width:
            return value
        suffix = "..."
        while value and font.size(value + suffix)[0] > width:
            value = value[:-1]
        return value.rstrip() + suffix

    def sync_context(self) -> ExperimentContext:
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
                    "Workspace changed; the previous experiment was cancelled.",
                    3.0,
                )
            self._context_signature = signature
            self.context = context
            self.selected_rules = {context.rules[0].key}
            self.selected_boundaries = {context.boundaries[0]}
            self.selected_sizes = {context.size_options[min(1, len(context.size_options) - 1)]}
            options = self.GENERATION_OPTIONS[context.dimension]
            self.selected_generations = {options[min(1, len(options) - 1)]}
            default_seed = SEED_RANDOM if SEED_RANDOM in context.seed_kinds else context.seed_kinds[0]
            self.selected_seed_kinds = {default_seed}
            closest_density = min(
                self.DENSITY_OPTIONS,
                key=lambda density: abs(density - context.default_seed_density),
            )
            self.selected_densities = {closest_density}
            self.repetition_index = 1
            self.report = None
            self.error = ""
            self.cancelled = False
            self.result_scroll = 0
        return context

    def plan(self) -> ExperimentPlan:
        context = self.sync_context()
        rule_by_key = {rule.key: rule for rule in context.rules}
        rules = tuple(
            rule for rule in context.rules if rule.key in self.selected_rules
        )
        if len(rules) != len(self.selected_rules) or any(
            key not in rule_by_key for key in self.selected_rules
        ):
            raise ValueError("A selected rule is no longer available in this workspace.")
        return ExperimentPlan(
            dimension=context.dimension,
            mode_label=context.mode_label,
            rules=rules,
            boundaries=tuple(
                boundary
                for boundary in context.boundaries
                if boundary in self.selected_boundaries
            ),
            sizes=tuple(size for size in context.size_options if size in self.selected_sizes),
            generation_counts=tuple(
                generations
                for generations in self.GENERATION_OPTIONS[context.dimension]
                if generations in self.selected_generations
            ),
            repetitions=self.REPETITION_OPTIONS[self.repetition_index],
            seed_kinds=tuple(
                kind for kind in context.seed_kinds if kind in self.selected_seed_kinds
            ),
            seed_densities=tuple(
                density
                for density in self.DENSITY_OPTIONS
                if density in self.selected_densities
            ),
            master_seed=self.services.master_seed(),
        )

    def request(self) -> bool:
        try:
            plan = self.plan()
        except (TypeError, ValueError) as exc:
            self.error = str(exc)
            self.services.set_status(f"Experiment rejected: {exc}", 4.0)
            return False
        if not self.runner.request(plan):
            return False
        self.report = None
        self.error = ""
        self.cancelled = False
        self.result_scroll = 0
        self.services.set_status(
            f"Experiment started: {plan.run_count} background runs.",
            3.0,
        )
        return True

    def update(self) -> None:
        try:
            report = self.runner.poll()
        except ExperimentCancelled:
            self.cancelled = True
            self.services.set_status("Experiment cancelled safely.", 2.5)
            return
        except Exception as exc:
            self.error = str(exc)
            self.services.set_status(f"Experiment failed: {exc}", 4.0)
            return
        if report is not None:
            self.report = report
            self.services.set_status(
                f"Experiment complete: {len(report.runs)} runs in {report.elapsed_seconds:.2f} s.",
                4.0,
            )

    def _design_geometry(
        self,
        content: pygame.Rect,
    ) -> tuple[
        pygame.Rect,
        tuple[tuple[str, Hashable, pygame.Rect], ...],
        pygame.Rect,
        pygame.Rect,
    ]:
        context = self.sync_context()
        intro = pygame.Rect(content.x, content.y, content.width, 54)
        rows: tuple[tuple[str, tuple[tuple[Hashable, str], ...]], ...] = (
            ("rules", tuple((rule.key, rule.name) for rule in context.rules)),
            ("boundaries", tuple((value, value.title()) for value in context.boundaries)),
            ("sizes", tuple((value, str(value)) for value in context.size_options)),
            (
                "generations",
                tuple((value, str(value)) for value in self.GENERATION_OPTIONS[context.dimension]),
            ),
            (
                "seed_kinds",
                tuple((value, value.replace("_", " ").title()) for value in context.seed_kinds),
            ),
            (
                "densities",
                tuple((value, f"{value * 100:.0f}%") for value in self.DENSITY_OPTIONS),
            ),
        )
        footer_height = 43
        gap = 6
        rule_lines = max(1, (len(rows[0][1]) + 3) // 4)
        row_units = rule_lines + len(rows) - 1
        available = content.bottom - intro.bottom - footer_height - gap * (len(rows) + 1)
        unit_height = max(32, available // row_units)
        label_width = max(112, min(165, content.width // 6))
        chips: list[tuple[str, Hashable, pygame.Rect]] = []
        y = intro.bottom + gap
        for group, values in rows:
            chip_area_x = content.x + label_width
            chip_gap = 5
            columns = min(4, len(values)) if group == "rules" else len(values)
            lines = max(1, (len(values) + columns - 1) // columns)
            row_height = unit_height * lines
            chip_width = max(
                44,
                (content.right - chip_area_x - chip_gap * (columns - 1)) // columns,
            )
            chip_height = max(24, (row_height - 6 - chip_gap * (lines - 1)) // lines)
            for index, (value, _label) in enumerate(values):
                line = index // columns
                column = index % columns
                chips.append(
                    (
                        group,
                        value,
                        pygame.Rect(
                            chip_area_x + column * (chip_width + chip_gap),
                            y + 3 + line * (chip_height + chip_gap),
                            chip_width,
                            chip_height,
                        ),
                    )
                )
            y += row_height + gap
        footer = pygame.Rect(content.x, content.bottom - footer_height, content.width, footer_height)
        repetitions = pygame.Rect(footer.x + 7, footer.y + 6, min(190, footer.width // 4), footer.height - 12)
        run = pygame.Rect(footer.right - min(210, footer.width // 4) - 7, footer.y + 6, min(210, footer.width // 4), footer.height - 12)
        return intro, tuple(chips), repetitions, run

    def _selected_set(self, group: str) -> set[Hashable]:
        return {
            "rules": self.selected_rules,
            "boundaries": self.selected_boundaries,
            "sizes": self.selected_sizes,
            "generations": self.selected_generations,
            "seed_kinds": self.selected_seed_kinds,
            "densities": self.selected_densities,
        }[group]

    def _toggle(self, group: str, value: Hashable) -> None:
        selected = self._selected_set(group)
        if value in selected:
            if len(selected) == 1:
                self.services.set_status("Each experiment factor needs at least one value.", 2.5)
                return
            selected.remove(value)
        else:
            selected.add(value)
        self.error = ""

    def handle_event(self, event: pygame.event.Event, content: pygame.Rect, tab: str) -> bool:
        if tab == "design":
            _intro, chips, repetitions, run = self._design_geometry(content)
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                return False
            for group, value, rect in chips:
                if rect.collidepoint(event.pos):
                    if group == "densities" and SEED_RANDOM not in self.selected_seed_kinds:
                        self.services.set_status(
                            "Random density applies only when Random seed is selected.",
                            2.5,
                        )
                        return True
                    self._toggle(group, value)
                    return True
            if repetitions.collidepoint(event.pos):
                self.repetition_index = (
                    self.repetition_index + 1
                ) % len(self.REPETITION_OPTIONS)
                return True
            if run.collidepoint(event.pos):
                if self.runner.running:
                    self.runner.cancel()
                    return True
                return self.request()
            return False

        csv_button, json_button, table = self._results_geometry(content)
        if event.type == pygame.MOUSEWHEEL and table.collidepoint(pygame.mouse.get_pos()):
            self.result_scroll = max(0, self.result_scroll - event.y)
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.runner.running and table.collidepoint(event.pos):
            self.runner.cancel()
            return True
        if csv_button.collidepoint(event.pos) and self.report is not None:
            self._export("csv")
            return True
        if json_button.collidepoint(event.pos) and self.report is not None:
            self._export("json")
            return True
        return False

    def _export(self, kind: str) -> None:
        if self.report is None:
            return
        try:
            path = (
                export_experiment_csv(self.report)
                if kind == "csv"
                else export_experiment_json(self.report)
            )
        except OSError as exc:
            self.services.set_status(f"{kind.upper()} export failed: {exc}", 4.0)
        else:
            self.services.set_status(f"Experiment {kind.upper()} saved: {path}", 5.0)

    def draw_design(self, content: pygame.Rect) -> None:
        context = self.sync_context()
        screen = self.services.screen()
        theme = self.services.theme()
        intro, chips, repetitions, run = self._design_geometry(content)
        pygame.draw.rect(screen, theme["stats_bar"], intro, border_radius=6)
        heading = (
            f"{context.dimension.upper()} · {context.mode_label} · master seed "
            f"{self.services.master_seed()}"
        )
        screen.blit(
            self.services.small_font().render(heading, True, theme["text"]),
            (intro.x + 10, intro.y + 6),
        )
        note = (
            "Select one or more values in every row. The lab evaluates their full Cartesian product."
        )
        screen.blit(
            self.services.tiny_font().render(
                self._fit(self.services.tiny_font(), note, intro.width - 20),
                True,
                theme["text"],
            ),
            (intro.x + 10, intro.y + 31),
        )
        labels = {
            "rules": "Rules",
            "boundaries": "Boundaries",
            "sizes": "Size / axis",
            "generations": "Generations",
            "seed_kinds": "Seed type",
            "densities": "Random density",
        }
        value_labels: dict[tuple[str, Hashable], str] = {}
        for rule in context.rules:
            value_labels[("rules", rule.key)] = rule.name
        for value in context.boundaries:
            value_labels[("boundaries", value)] = value.title()
        for value in context.size_options:
            value_labels[("sizes", value)] = str(value)
        for value in self.GENERATION_OPTIONS[context.dimension]:
            value_labels[("generations", value)] = str(value)
        for value in context.seed_kinds:
            value_labels[("seed_kinds", value)] = value.replace("_", " ").title()
        for value in self.DENSITY_OPTIONS:
            value_labels[("densities", value)] = f"{value * 100:.0f}%"
        row_bounds: dict[str, list[int]] = {}
        for group, value, rect in chips:
            bounds = row_bounds.setdefault(group, [rect.top, rect.bottom])
            bounds[0] = min(bounds[0], rect.top)
            bounds[1] = max(bounds[1], rect.bottom)
            enabled = not (group == "densities" and SEED_RANDOM not in self.selected_seed_kinds)
            self._chip(
                rect,
                value_labels[(group, value)],
                value in self._selected_set(group),
                enabled,
            )
        label_x = content.x + 8
        for group, (top, bottom) in row_bounds.items():
            center_y = (top + bottom) // 2
            rendered = self.services.tiny_font().render(labels[group], True, theme["text"])
            screen.blit(rendered, (label_x, center_y - rendered.get_height() // 2))
        pygame.draw.rect(screen, theme["stats_bar"], (content.x, repetitions.y - 6, content.width, repetitions.height + 12), border_radius=6)
        self._button(
            repetitions,
            f"Random repetitions: {self.REPETITION_OPTIONS[self.repetition_index]}",
        )
        try:
            plan = self.plan()
        except (TypeError, ValueError) as exc:
            plan_label = f"Cannot run: {exc}"
            plan_color = (245, 110, 95)
            can_run = False
        else:
            plan_label = f"Planned independent runs: {plan.run_count}"
            plan_color = (90, 220, 130)
            can_run = True
        rendered = self.services.tiny_font().render(
            self._fit(
                self.services.tiny_font(),
                plan_label,
                run.x - repetitions.right - 22,
            ),
            True,
            plan_color,
        )
        screen.blit(
            rendered,
            rendered.get_rect(
                center=((repetitions.right + run.x) // 2, repetitions.centery)
            ),
        )
        self._button(
            run,
            "Cancel safely" if self.runner.running else "Run Experiment (Enter)",
            enabled=can_run or self.runner.running,
            accent=(235, 100, 145) if self.runner.running else (90, 220, 130),
        )

    def _results_geometry(self, content: pygame.Rect) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        button_width = min(190, (content.width - 10) // 3)
        csv_button = pygame.Rect(content.right - 2 * button_width - 7, content.y + 4, button_width, 31)
        json_button = pygame.Rect(content.right - button_width, content.y + 4, button_width, 31)
        table = pygame.Rect(content.x, content.y + 44, content.width, content.height - 44)
        return csv_button, json_button, table

    def draw_results(self, content: pygame.Rect) -> None:
        self.sync_context()
        csv_button, json_button, table = self._results_geometry(content)
        theme = self.services.theme()
        screen = self.services.screen()
        if self.runner.running:
            progress = self.runner.progress
            heading = f"Running {progress.completed_runs}/{progress.total_runs} · {progress.rule_name} · {progress.boundary}"
        elif self.report is not None:
            heading = f"Completed {len(self.report.runs)} runs in {self.report.elapsed_seconds:.2f} s"
        elif self.error:
            heading = f"Experiment failed: {self.error}"
        elif self.cancelled:
            heading = "Experiment cancelled; partial results were discarded."
        else:
            heading = "No completed experiment yet. Configure one in Design Experiment."
        rendered = self.services.small_font().render(
            self._fit(self.services.small_font(), heading, csv_button.x - content.x - 14),
            True,
            theme["text"],
        )
        screen.blit(rendered, (content.x + 4, content.y + 9))
        self._button(csv_button, "Export analysis CSV", enabled=self.report is not None)
        self._button(json_button, "Export reproducible JSON", enabled=self.report is not None)
        if self.runner.running:
            progress = self.runner.progress
            self._message(table, "Click the result area to cancel safely.", (80, 195, 255), progress.fraction)
        elif self.report is not None:
            self._draw_table(table, self.report)
        elif self.error:
            self._message(table, self.error, (245, 95, 95))
        elif self.cancelled:
            self._message(table, "Cancelled safely. Return to Design to adjust the sweep.", (225, 175, 65))
        else:
            self._message(table, "Results, uncertainty and export actions will appear here.", (90, 220, 130))

    def _chip(self, rect: pygame.Rect, label: str, selected: bool, enabled: bool) -> None:
        theme = self.services.theme()
        screen = self.services.screen()
        fill = theme["button_hover"] if selected else theme["button"]
        if not enabled:
            fill = theme["stats_bar"]
        border = (90, 220, 130) if selected else theme["grid"]
        pygame.draw.rect(screen, fill, rect, border_radius=4)
        pygame.draw.rect(screen, border, rect, 2 if selected else 1, border_radius=4)
        font = self.services.tiny_font()
        prefix = "[x] " if selected else ""
        color = theme["button_text"] if enabled else theme["grid"]
        rendered = font.render(self._fit(font, prefix + label, rect.width - 8), True, color)
        screen.blit(rendered, rendered.get_rect(center=rect.center))

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
        pygame.draw.rect(screen, theme["button"] if enabled else theme["stats_bar"], rect, border_radius=4)
        pygame.draw.rect(screen, accent or theme["grid"], rect, 2 if accent else 1, border_radius=4)
        color = theme["button_text"] if enabled else theme["grid"]
        font = self.services.tiny_font()
        rendered = font.render(self._fit(font, label, rect.width - 10), True, color)
        screen.blit(rendered, rendered.get_rect(center=rect.center))

    def _message(
        self,
        rect: pygame.Rect,
        text: str,
        color: tuple[int, int, int],
        progress: float | None = None,
    ) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        pygame.draw.rect(screen, theme["stats_bar"], rect, border_radius=6)
        rendered = self.services.small_font().render(
            self._fit(self.services.small_font(), text, rect.width - 30), True, color
        )
        screen.blit(rendered, rendered.get_rect(center=rect.center))
        if progress is not None:
            track = pygame.Rect(rect.x + 40, rect.centery + 30, rect.width - 80, 8)
            pygame.draw.rect(screen, theme["grid"], track, border_radius=4)
            fill = track.copy()
            fill.width = round(track.width * max(0.0, min(1.0, progress)))
            pygame.draw.rect(screen, color, fill, border_radius=4)

    def _draw_table(self, rect: pygame.Rect, report: ExperimentReport) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        pygame.draw.rect(screen, theme["stats_bar"], rect, border_radius=6)
        columns = (
            ("Rule", 0.18),
            ("Boundary", 0.08),
            ("Size", 0.06),
            ("Gen", 0.06),
            ("Seed", 0.09),
            ("Density", 0.08),
            ("n", 0.04),
            ("Final density", 0.15),
            ("Entropy", 0.12),
            ("Change", 0.07),
            ("Period", 0.07),
        )
        positions: list[tuple[int, int]] = []
        cursor = rect.x
        for _label, fraction in columns:
            width = round(rect.width * fraction)
            positions.append((cursor, width))
            cursor += width
        header_height = 27
        pygame.draw.rect(screen, theme["button"], (rect.x, rect.y, rect.width, header_height), border_radius=4)
        tiny = self.services.tiny_font()
        for (label, _), (x, width) in zip(columns, positions, strict=True):
            rendered = tiny.render(self._fit(tiny, label, width - 4), True, theme["text"])
            screen.blit(rendered, rendered.get_rect(center=(x + width // 2, rect.y + 13)))
        row_height = 27
        visible = max(1, (rect.height - header_height - 4) // row_height)
        maximum_scroll = max(0, len(report.aggregates) - visible)
        self.result_scroll = min(self.result_scroll, maximum_scroll)
        selected = report.aggregates[self.result_scroll : self.result_scroll + visible]
        for index, aggregate in enumerate(selected):
            y = rect.y + header_height + index * row_height
            row = pygame.Rect(rect.x, y, rect.width, row_height - 1)
            pygame.draw.rect(screen, theme["button"] if index % 2 == 0 else theme["stats_bar"], row)
            period = (
                "--"
                if aggregate.mean_detected_period is None
                else f"{aggregate.mean_detected_period:.1f}"
            )
            values = (
                aggregate.rule_name,
                aggregate.boundary,
                str(aggregate.size),
                str(aggregate.generations),
                aggregate.seed_kind.replace("_", " "),
                "--" if aggregate.seed_density is None else f"{100 * aggregate.seed_density:.0f}%",
                str(aggregate.repetitions),
                f"{aggregate.mean_final_density:.2f}±{aggregate.sd_final_density:.2f}%",
                f"{aggregate.mean_entropy:.3f}±{aggregate.sd_entropy:.3f}",
                f"{aggregate.mean_change_rate:.2f}%",
                period,
            )
            for value, (x, width) in zip(values, positions, strict=True):
                rendered = tiny.render(self._fit(tiny, value, width - 5), True, theme["text"])
                screen.blit(rendered, rendered.get_rect(center=(x + width // 2, row.centery)))
        if maximum_scroll:
            note = f"{self.result_scroll + 1}-{self.result_scroll + len(selected)} / {len(report.aggregates)} · wheel scrolls"
            rendered = tiny.render(note, True, theme["text"])
            screen.blit(rendered, (rect.right - rendered.get_width() - 5, rect.bottom - rendered.get_height() - 3))
