"""Pygame scientific dashboard for live metrics and reproducible summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from scientific_analysis import (
    AnalysisSample,
    AnalysisSeries,
    ElementaryComparisonRunner,
    ElementaryRuleComparison,
)


@dataclass(frozen=True)
class AnalysisPanelServices:
    """Drawing resources and application callbacks for the analysis panel."""

    screen: Callable[[], pygame.Surface]
    window_size: Callable[[], tuple[int, int]]
    content_width: Callable[[], int]
    theme: Callable[[], dict[str, tuple[int, int, int]]]
    large_font: Callable[[], pygame.font.Font]
    small_font: Callable[[], pygame.font.Font]
    tiny_font: Callable[[], pygame.font.Font]
    live_series: Callable[[], AnalysisSeries]
    current_generation: Callable[[], int]
    comparison_rules: Callable[[], tuple[int, ...]]
    current_rule: Callable[[], int]
    set_status: Callable[[str, float], None]


class ScientificAnalysisPanel:
    """Display live scientific time series and reproducible 1D comparisons."""

    def __init__(
        self,
        services: AnalysisPanelServices,
        comparison_runner: ElementaryComparisonRunner,
    ) -> None:
        self.services = services
        self.comparison_runner = comparison_runner
        self.active = False
        self.tab = "live"
        self.comparison_results: list[ElementaryRuleComparison] | None = None
        self.comparison_error = ""

    def toggle(self) -> None:
        self.active = not self.active
        if self.active and self.tab == "comparison":
            self.request_comparison()

    def close(self) -> None:
        self.active = False

    def request_comparison(self) -> None:
        rules = self.services.comparison_rules()
        if self.comparison_runner.request(rules, generations=160):
            self.comparison_results = None
            self.comparison_error = ""

    def update(self) -> None:
        """Collect a completed background comparison without blocking Pygame."""
        try:
            results = self.comparison_runner.poll()
        except Exception as exc:  # The dashboard must not stop the simulation.
            self.comparison_error = str(exc)
            self.services.set_status(f"Rule comparison failed: {exc}", 4.0)
            return
        if results is not None:
            self.comparison_results = results

    def geometry(
        self,
    ) -> tuple[
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
        pygame.Rect,
    ]:
        width, height = self.services.window_size()
        content_width = self.services.content_width()
        modal = pygame.Rect(
            0,
            0,
            max(320, min(1120, content_width - 30)),
            max(360, min(760, height - 40)),
        )
        modal.center = (content_width // 2, height // 2)
        tab_width = min(170, (modal.width - 120) // 4)
        live_tab = pygame.Rect(modal.x + 18, modal.y + 47, tab_width, 28)
        summary_tab = pygame.Rect(live_tab.right + 8, live_tab.y, tab_width, 28)
        methods_tab = pygame.Rect(summary_tab.right + 8, live_tab.y, tab_width, 28)
        comparison_tab = pygame.Rect(methods_tab.right + 8, live_tab.y, tab_width, 28)
        close_button = pygame.Rect(modal.right - 42, modal.y + 12, 28, 25)
        return modal, live_tab, summary_tab, methods_tab, comparison_tab, close_button

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_i):
                self.close()
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            (
                modal,
                live_tab,
                summary_tab,
                methods_tab,
                comparison_tab,
                close_button,
            ) = self.geometry()
            if close_button.collidepoint(event.pos) or not modal.collidepoint(event.pos):
                self.close()
            elif live_tab.collidepoint(event.pos):
                self.tab = "live"
            elif summary_tab.collidepoint(event.pos):
                self.tab = "summary"
            elif methods_tab.collidepoint(event.pos):
                self.tab = "methods"
            elif comparison_tab.collidepoint(event.pos):
                self.tab = "comparison"
                self.request_comparison()
            return True
        return event.type in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEWHEEL,
        )

    def draw(self) -> None:
        if not self.active:
            return
        self.update()
        (
            modal,
            live_tab,
            summary_tab,
            methods_tab,
            comparison_tab,
            close_button,
        ) = self.geometry()
        screen = self.services.screen()
        theme = self.services.theme()

        shadow = pygame.Surface((modal.width + 12, modal.height + 12), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 100))
        screen.blit(shadow, (modal.x + 5, modal.y + 5))
        pygame.draw.rect(screen, theme["info_bar"], modal, border_radius=10)
        pygame.draw.rect(screen, theme["text"], modal, 2, border_radius=10)
        title = self.services.large_font().render(
            "Scientific Analysis",
            True,
            theme["text"],
        )
        screen.blit(title, (modal.x + 18, modal.y + 12))

        self._draw_tab(live_tab, "Live Metrics", self.tab == "live")
        self._draw_tab(summary_tab, "Statistical Summary", self.tab == "summary")
        self._draw_tab(methods_tab, "Methods", self.tab == "methods")
        self._draw_tab(
            comparison_tab,
            "1D Rule Comparison",
            self.tab == "comparison",
        )
        pygame.draw.rect(screen, theme["button"], close_button, border_radius=4)
        pygame.draw.rect(screen, theme["text"], close_button, 1, border_radius=4)
        close_text = self.services.small_font().render("×", True, theme["text"])
        screen.blit(close_text, close_text.get_rect(center=close_button.center))

        content = pygame.Rect(
            modal.x + 16,
            live_tab.bottom + 9,
            modal.width - 32,
            modal.bottom - live_tab.bottom - 23,
        )
        if self.tab == "comparison":
            self._draw_comparison(content)
        elif self.tab == "methods":
            self._draw_methods(content)
        elif self.tab == "summary":
            self._draw_summary(content)
        else:
            self._draw_live(content)

    @staticmethod
    def _fit_text(font: pygame.font.Font, value: str, width: int) -> str:
        if font.size(value)[0] <= width:
            return value
        suffix = "…"
        shortened = value
        while shortened and font.size(shortened + suffix)[0] > width:
            shortened = shortened[:-1]
        return shortened.rstrip() + suffix

    def _draw_tab(self, rect: pygame.Rect, label: str, active: bool) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        color = theme["button_hover"] if active else theme["button"]
        pygame.draw.rect(screen, color, rect, border_radius=4)
        border = (70, 170, 255) if active else theme["grid"]
        pygame.draw.rect(screen, border, rect, 2 if active else 1, border_radius=4)
        font = self.services.tiny_font()
        text = font.render(
            self._fit_text(font, label, rect.width - 8),
            True,
            theme["button_text"],
        )
        screen.blit(text, text.get_rect(center=rect.center))

    def _displayed_samples(self, series: AnalysisSeries) -> list[AnalysisSample]:
        current_generation = self.services.current_generation()
        matching_indices = [
            index
            for index, sample in enumerate(series.samples)
            if sample.generation == current_generation
        ]
        return (
            series.samples[: matching_indices[-1] + 1]
            if matching_indices
            else series.samples
        )

    def _draw_live(self, content: pygame.Rect) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        series = self.services.live_series()
        displayed_samples = self._displayed_samples(series)
        latest = displayed_samples[-1] if displayed_samples else None
        if latest is None:
            message = self.services.small_font().render(
                "No measurements are available yet.", True, theme["text"]
            )
            screen.blit(message, message.get_rect(center=content.center))
            return

        summary_height = 66
        summary_rect = pygame.Rect(content.x, content.y, content.width, summary_height)
        pygame.draw.rect(screen, theme["stats_bar"], summary_rect, border_radius=6)
        heading = (
            f"{series.title}  ·  Generation {latest.generation}  ·  "
            f"Samples {len(displayed_samples)}/{len(series.samples)}"
        )
        screen.blit(
            self.services.small_font().render(heading, True, theme["text"]),
            (summary_rect.x + 10, summary_rect.y + 6),
        )
        if series.period is None:
            behavior = "Period: not detected  ·  Stabilization: not detected"
        else:
            behavior = (
                f"Period: {series.period}"
                f"{' (stable)' if series.period == 1 else ''}  ·  "
                f"Stabilization generation: {series.stabilization_generation}"
            )
        screen.blit(
            self.services.tiny_font().render(behavior, True, theme["text"]),
            (summary_rect.x + 10, summary_rect.y + 29),
        )
        regime = f"Heuristic regime: {series.heuristic_regime()}"
        screen.blit(
            self.services.tiny_font().render(regime, True, theme["text"]),
            (summary_rect.x + 10, summary_rect.y + 47),
        )

        graph_area = pygame.Rect(
            content.x,
            summary_rect.bottom + 8,
            content.width,
            content.bottom - summary_rect.bottom - 8,
        )
        gap = 8
        chart_width = (graph_area.width - gap) // 2
        chart_height = (graph_area.height - 2 * gap) // 3
        charts = (
            (
                pygame.Rect(graph_area.x, graph_area.y, chart_width, chart_height),
                series.population_label,
                "population",
                (80, 195, 255),
                None,
            ),
            (
                pygame.Rect(
                    graph_area.x + chart_width + gap,
                    graph_area.y,
                    chart_width,
                    chart_height,
                ),
                "Density (%)",
                "density",
                (90, 220, 130),
                100.0,
            ),
            (
                pygame.Rect(
                    graph_area.x,
                    graph_area.y + chart_height + gap,
                    chart_width,
                    chart_height,
                ),
                "Normalized entropy",
                "entropy",
                (225, 175, 65),
                1.0,
            ),
            (
                pygame.Rect(
                    graph_area.x + chart_width + gap,
                    graph_area.y + chart_height + gap,
                    chart_width,
                    chart_height,
                ),
                "Block entropy",
                "block_entropy",
                (180, 125, 240),
                1.0,
            ),
            (
                pygame.Rect(
                    graph_area.x,
                    graph_area.y + 2 * (chart_height + gap),
                    chart_width,
                    chart_height,
                ),
                "Change rate (%)",
                "change_rate",
                (235, 100, 145),
                100.0,
            ),
            (
                pygame.Rect(
                    graph_area.x + chart_width + gap,
                    graph_area.y + 2 * (chart_height + gap),
                    chart_width,
                    chart_height,
                ),
                "Neighbor agreement (%)",
                "neighbor_agreement",
                (70, 205, 195),
                100.0,
            ),
        )
        for rect, label, attribute, color, fixed_max in charts:
            self._draw_graph(
                rect,
                label,
                displayed_samples,
                attribute,
                color,
                fixed_max,
            )

    def _draw_graph(
        self,
        rect: pygame.Rect,
        label: str,
        samples: list[AnalysisSample],
        attribute: str,
        color: tuple[int, int, int],
        fixed_max: float | None,
    ) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        pygame.draw.rect(screen, theme["stats_bar"], rect, border_radius=6)
        pygame.draw.rect(screen, theme["grid"], rect, 1, border_radius=6)
        latest_value = float(getattr(samples[-1], attribute))
        display_value = (
            f"{latest_value:.0f}"
            if attribute == "population"
            else f"{latest_value:.3f}"
            if attribute in ("entropy", "block_entropy")
            else f"{latest_value:.2f}"
        )
        heading = self.services.tiny_font().render(
            f"{label}: {display_value}",
            True,
            theme["text"],
        )
        screen.blit(heading, (rect.x + 7, rect.y + 5))
        plot = pygame.Rect(rect.x + 32, rect.y + 24, rect.width - 40, rect.height - 42)
        if plot.width < 2 or plot.height < 2:
            return
        for division in range(3):
            y = plot.y + round(division * plot.height / 2)
            pygame.draw.line(screen, theme["grid"], (plot.x, y), (plot.right, y), 1)

        values = [float(getattr(sample, attribute)) for sample in samples]
        maximum = fixed_max if fixed_max is not None else max(1.0, max(values) * 1.08)
        point_count = min(len(samples), max(2, plot.width))
        if len(samples) == 1:
            indices = [0]
        else:
            indices = [
                round(index * (len(samples) - 1) / (point_count - 1))
                for index in range(point_count)
            ]
        points = [
            (
                plot.x
                + round(position * plot.width / max(1, len(indices) - 1)),
                plot.bottom
                - round(min(maximum, values[index]) * plot.height / maximum),
            )
            for position, index in enumerate(indices)
        ]
        if len(points) > 1:
            pygame.draw.lines(screen, color, False, points, 2)
        else:
            pygame.draw.circle(screen, color, points[0], 3)
        first_generation = samples[0].generation
        last_generation = samples[-1].generation
        axis = self.services.tiny_font()
        screen.blit(
            axis.render(str(first_generation), True, theme["text"]),
            (plot.x, plot.bottom + 2),
        )
        last_text = axis.render(str(last_generation), True, theme["text"])
        screen.blit(last_text, (plot.right - last_text.get_width(), plot.bottom + 2))

    def _draw_summary(self, content: pygame.Rect) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        series = self.services.live_series()
        displayed = self._displayed_samples(series)
        if not displayed:
            message = self.services.small_font().render(
                "No measurements are available yet.", True, theme["text"]
            )
            screen.blit(message, message.get_rect(center=content.center))
            return

        window = min(100, len(displayed))
        selected = displayed[-window:]
        statistics = {
            attribute: self._statistics(selected, attribute)
            for attribute in (
                "population",
                "density",
                "entropy",
                "block_entropy",
                "change_rate",
                "neighbor_agreement",
                "growth_rate",
                "state_utilization",
            )
        }
        shape = "×".join(str(length) for length in series.lattice_shape)
        header = pygame.Rect(content.x, content.y, content.width, 72)
        pygame.draw.rect(screen, theme["stats_bar"], header, border_radius=6)
        heading = (
            f"{series.title}  ·  {len(series.lattice_shape)}D lattice {shape}  ·  "
            f"states {series.state_count}"
        )
        font = self.services.small_font()
        screen.blit(
            font.render(self._fit_text(font, heading, header.width - 20), True, theme["text"]),
            (header.x + 10, header.y + 7),
        )
        detail = (
            f"Window: generations {selected[0].generation}–{selected[-1].generation} "
            f"(n={window})  ·  Heuristic regime: {series.heuristic_regime()}"
        )
        screen.blit(
            self.services.tiny_font().render(
                self._fit_text(self.services.tiny_font(), detail, header.width - 20),
                True,
                theme["text"],
            ),
            (header.x + 10, header.y + 33),
        )
        caveat = (
            "Descriptive statistics; slope is per generation. Regime labels are heuristic, not proofs."
        )
        screen.blit(
            self.services.tiny_font().render(
                self._fit_text(self.services.tiny_font(), caveat, header.width - 20),
                True,
                theme["text"],
            ),
            (header.x + 10, header.y + 51),
        )

        table = pygame.Rect(
            content.x,
            header.bottom + 8,
            content.width,
            content.bottom - header.bottom - 8,
        )
        columns = (
            ("Metric", 0.25),
            ("Current", 0.125),
            ("Mean", 0.125),
            ("SD", 0.125),
            ("Min", 0.105),
            ("Max", 0.105),
            ("Slope/gen", 0.165),
        )
        positions: list[tuple[int, int]] = []
        cursor = table.x
        for _, fraction in columns:
            width = round(table.width * fraction)
            positions.append((cursor, width))
            cursor += width
        header_height = 27
        pygame.draw.rect(
            screen,
            theme["button"],
            (table.x, table.y, table.width, header_height),
            border_radius=4,
        )
        tiny = self.services.tiny_font()
        for (label, _), (x, width) in zip(columns, positions, strict=True):
            text = tiny.render(label, True, theme["text"])
            screen.blit(text, text.get_rect(center=(x + width // 2, table.y + 13)))

        metrics = (
            (series.population_label, "population", 1),
            ("Density (%)", "density", 2),
            ("State entropy [0,1]", "entropy", 3),
            ("Block entropy [0,1]", "block_entropy", 3),
            ("Change / Hamming (%)", "change_rate", 2),
            ("Neighbor agreement (%)", "neighbor_agreement", 2),
            ("Population growth (% lattice)", "growth_rate", 2),
            ("State utilization (%)", "state_utilization", 2),
        )
        row_height = max(25, (table.height - header_height) // len(metrics))
        for index, (label, key, precision) in enumerate(metrics):
            y = table.y + header_height + index * row_height
            row = pygame.Rect(table.x, y, table.width, row_height - 2)
            pygame.draw.rect(
                screen,
                theme["stats_bar"] if index % 2 else theme["button"],
                row,
                border_radius=3,
            )
            stats = statistics[key]
            values = (
                label,
                f"{stats[0]:.{precision}f}",
                f"{stats[1]:.{precision}f}",
                f"{stats[2]:.{precision}f}",
                f"{stats[3]:.{precision}f}",
                f"{stats[4]:.{precision}f}",
                f"{stats[5]:+.{precision}f}",
            )
            for value, (x, width) in zip(values, positions, strict=True):
                fitted = self._fit_text(tiny, value, width - 6)
                rendered = tiny.render(fitted, True, theme["text"])
                screen.blit(rendered, rendered.get_rect(center=(x + width // 2, row.centery)))

    @staticmethod
    def _statistics(
        samples: list[AnalysisSample],
        attribute: str,
    ) -> tuple[float, float, float, float, float, float]:
        values = [float(getattr(sample, attribute)) for sample in samples]
        generations = [float(sample.generation) for sample in samples]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        generation_mean = sum(generations) / len(generations)
        denominator = sum(
            (generation - generation_mean) ** 2 for generation in generations
        )
        slope = (
            sum(
                (generation - generation_mean) * (value - mean)
                for generation, value in zip(generations, values, strict=True)
            )
            / denominator
            if denominator
            else 0.0
        )
        return values[-1], mean, variance**0.5, min(values), max(values), slope

    @staticmethod
    def _wrap_text(
        font: pygame.font.Font,
        value: str,
        width: int,
    ) -> list[str]:
        words = value.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def _draw_methods(self, content: pygame.Rect) -> None:
        """Explain the panel's estimators and their interpretation limits."""

        screen = self.services.screen()
        theme = self.services.theme()
        series = self.services.live_series()
        dimension = len(series.lattice_shape)
        block = {1: "3", 2: "2x2", 3: "2x2x2"}[dimension]
        heading = (
            f"Measurement protocol · {dimension}D · lattice "
            f"{'×'.join(str(length) for length in series.lattice_shape)} · "
            f"{series.state_count} states"
        )
        font = self.services.small_font()
        screen.blit(
            font.render(
                self._fit_text(font, heading, content.width - 8),
                True,
                theme["text"],
            ),
            (content.x + 4, content.y + 2),
        )
        methods = (
            (
                "Normalized state entropy H1",
                "-sum p(s) log2 p(s) / log2(k)",
                "Uncertainty of the current single-cell state distribution; 0 is uniform and 1 is maximally balanced.",
            ),
            (
                f"Normalized block entropy HB ({block})",
                "-sum p(block) log2 p(block) / block capacity",
                "Non-overlapping local patterns; incomplete edge blocks are excluded instead of padded.",
            ),
            (
                "Temporal Hamming change",
                "100 x changed positions / compared positions",
                "Compares consecutive generations. Expanding 1D rows are center-aligned; 2D and 3D shapes are fixed.",
            ),
            (
                "Orthogonal neighbor agreement",
                "100 x equal adjacent pairs / interior adjacent pairs",
                "Uses axis-aligned interior pairs. Wrap/reflect edge pairs are intentionally excluded for comparability.",
            ),
            (
                "Population growth and utilization",
                "growth = 100 x delta population / lattice cells",
                "State utilization is observed state count divided by the rule's available state count.",
            ),
            (
                "Cycles and heuristic regime",
                "period = generation gap between identical full-state hashes",
                "Exact repeats establish periods. Other regime labels summarize a recent window and are not formal proofs.",
            ),
        )
        area = pygame.Rect(
            content.x,
            content.y + 29,
            content.width,
            content.height - 51,
        )
        gap = 8
        card_width = (area.width - gap) // 2
        card_height = (area.height - 2 * gap) // 3
        tiny = self.services.tiny_font()
        accents = (
            (225, 175, 65),
            (180, 125, 240),
            (235, 100, 145),
            (70, 205, 195),
            (90, 220, 130),
            (80, 195, 255),
        )
        for index, ((title, formula, description), accent) in enumerate(
            zip(methods, accents, strict=True)
        ):
            column = index % 2
            row = index // 2
            card = pygame.Rect(
                area.x + column * (card_width + gap),
                area.y + row * (card_height + gap),
                card_width,
                card_height,
            )
            pygame.draw.rect(screen, theme["stats_bar"], card, border_radius=6)
            pygame.draw.rect(screen, accent, card, 2, border_radius=6)
            screen.blit(
                tiny.render(
                    self._fit_text(tiny, title, card.width - 16),
                    True,
                    theme["text"],
                ),
                (card.x + 8, card.y + 7),
            )
            screen.blit(
                tiny.render(
                    self._fit_text(tiny, formula, card.width - 16),
                    True,
                    accent,
                ),
                (card.x + 8, card.y + 27),
            )
            line_y = card.y + 48
            for line in self._wrap_text(tiny, description, card.width - 16):
                if line_y + tiny.get_height() > card.bottom - 5:
                    break
                screen.blit(tiny.render(line, True, theme["text"]), (card.x + 8, line_y))
                line_y += tiny.get_height() + 2
        reference = (
            "Methods: Zenil 2013 · Helvik et al. 2006 · Alfaro & Sanjuan 2024; full citations in README."
        )
        screen.blit(
            tiny.render(
                self._fit_text(tiny, reference, content.width - 8),
                True,
                theme["text"],
            ),
            (content.x + 4, content.bottom - 17),
        )

    def _draw_comparison(self, content: pygame.Rect) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        note = (
            "Canonical single-center seed · 160 generations · "
            "equal 321-cell infinite-background window"
        )
        screen.blit(
            self.services.tiny_font().render(note, True, theme["text"]),
            (content.x + 4, content.y + 2),
        )
        if self.comparison_error:
            error = self.services.small_font().render(
                f"Comparison failed: {self.comparison_error}",
                True,
                (245, 95, 95),
            )
            screen.blit(error, error.get_rect(center=content.center))
            return
        if self.comparison_results is None:
            dots = "." * ((pygame.time.get_ticks() // 350) % 4)
            loading = self.services.small_font().render(
                f"Computing comparable rule experiments{dots}",
                True,
                theme["text"],
            )
            screen.blit(loading, loading.get_rect(center=content.center))
            return

        table = pygame.Rect(content.x, content.y + 27, content.width, content.height - 27)
        columns = (
            ("Rule", 0.09),
            ("Avg density", 0.15),
            ("State H", 0.14),
            ("Block H", 0.14),
            ("Change", 0.14),
            ("Neighbor", 0.16),
            ("Period @ gen", 0.18),
        )
        positions: list[tuple[int, int]] = []
        cursor = table.x
        for _, fraction in columns:
            width = round(table.width * fraction)
            positions.append((cursor, width))
            cursor += width
        header_height = 29
        pygame.draw.rect(
            screen,
            theme["button"],
            (table.x, table.y, table.width, header_height),
            border_radius=5,
        )
        for (label, _), (x, width) in zip(columns, positions):
            rendered = self.services.tiny_font().render(label, True, theme["text"])
            screen.blit(rendered, rendered.get_rect(center=(x + width // 2, table.y + 14)))

        row_height = max(34, min(58, (table.height - header_height) // max(1, len(self.comparison_results))))
        current_rule = self.services.current_rule()
        max_density = max(
            1.0,
            max(result.mean_density for result in self.comparison_results),
        )
        for index, result in enumerate(self.comparison_results):
            y = table.y + header_height + index * row_height
            row = pygame.Rect(table.x, y, table.width, row_height - 2)
            background = theme["button"] if index % 2 == 0 else theme["stats_bar"]
            pygame.draw.rect(screen, background, row, border_radius=3)
            if result.rule == current_rule:
                pygame.draw.rect(screen, (225, 175, 65), row, 2, border_radius=3)
            density_column_x, density_column_width = positions[1]
            bar = pygame.Rect(
                density_column_x + 4,
                row.centery + 7,
                round((density_column_width - 8) * result.mean_density / max_density),
                4,
            )
            pygame.draw.rect(screen, (90, 220, 130), bar, border_radius=2)
            period_label = (
                "—"
                if result.period is None
                else f"{result.period} @ {result.stabilization_generation}"
            )
            values = (
                str(result.rule),
                f"{result.mean_density:.2f}%",
                f"{result.mean_entropy:.3f}",
                f"{result.mean_block_entropy:.3f}",
                f"{result.mean_change_rate:.2f}%",
                f"{result.mean_neighbor_agreement:.2f}%",
                period_label,
            )
            for value, (x, width) in zip(values, positions):
                rendered = self.services.tiny_font().render(value, True, theme["text"])
                screen.blit(rendered, rendered.get_rect(center=(x + width // 2, row.centery - 4)))
