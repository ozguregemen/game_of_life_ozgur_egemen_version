"""Saved experiment browser and visual comparison workspace."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pygame
from PIL import Image

from app_paths import APPLICATION_PATHS
from experiment_lab import ExperimentReport
from experiment_report_library import (
    COMPARISON_METRICS,
    MAX_SAVED_REPORTS,
    ExperimentReportLibrary,
    ReportComparison,
    SavedExperimentSummary,
    compare_reports,
)

COMPARISON_EXPORT_DIRECTORY = APPLICATION_PATHS.exports / "experiment_comparisons"
METRIC_COLORS = {
    "final_density": (82, 190, 235),
    "entropy": (242, 184, 72),
    "block_entropy": (177, 126, 235),
    "change_rate": (238, 100, 150),
}


@dataclass(frozen=True)
class HistoryGeometry:
    save_button: pygame.Rect
    refresh_button: pygame.Rect
    list_panel: pygame.Rect
    list_area: pygame.Rect
    open_button: pygame.Rect
    delete_button: pygame.Rect
    compare_panel: pygame.Rect
    metric_buttons: tuple[tuple[str, pygame.Rect], ...]
    export_png_button: pygame.Rect
    export_pdf_button: pygame.Rect


class ExperimentHistoryView:
    """Own history selection, deletion confirmation, comparison, and export."""

    def __init__(
        self,
        services: Any,
        library: ExperimentReportLibrary,
        current_report: Callable[[], ExperimentReport | None],
        open_report: Callable[[ExperimentReport], None],
    ) -> None:
        self.services = services
        self.library = library
        self.current_report = current_report
        self.open_report = open_report
        self.selected_paths: set[Path] = set()
        self.metric_key = "entropy"
        self.scroll = 0
        self.delete_confirmation: Path | None = None
        self.comparison: ReportComparison | None = None
        self.export_directory = COMPARISON_EXPORT_DIRECTORY
        self.refresh()

    @staticmethod
    def _fit(font: pygame.font.Font, value: str, width: int) -> str:
        if font.size(value)[0] <= width:
            return value
        suffix = "..."
        while value and font.size(value + suffix)[0] > width:
            value = value[:-1]
        return value.rstrip() + suffix

    def refresh(self) -> None:
        self.library.refresh()
        valid_paths = {entry.path for entry in self.library.entries}
        self.selected_paths.intersection_update(valid_paths)
        self.delete_confirmation = None
        self._refresh_comparison()

    def _selected_entries(self) -> tuple[SavedExperimentSummary, ...]:
        return tuple(
            entry
            for entry in self.library.entries
            if entry.path in self.selected_paths
        )

    def _refresh_comparison(self) -> None:
        entries = self._selected_entries()
        if len(entries) < 2:
            self.comparison = None
            return
        try:
            reports = tuple((entry, self.library.load(entry)) for entry in entries)
            self.comparison = compare_reports(reports, self.metric_key)
        except (OSError, TypeError, ValueError) as exc:
            self.comparison = None
            self.services.set_status(f"Comparison failed: {exc}", 4.0)

    def geometry(self, content: pygame.Rect) -> HistoryGeometry:
        toolbar_height = 36
        action_width = min(165, max(105, content.width // 6))
        save_button = pygame.Rect(
            content.right - action_width * 2 - 7,
            content.y + 2,
            action_width,
            31,
        )
        refresh_button = pygame.Rect(
            content.right - action_width,
            content.y + 2,
            action_width,
            31,
        )
        body = pygame.Rect(
            content.x,
            content.y + toolbar_height + 5,
            content.width,
            content.height - toolbar_height - 5,
        )
        if content.width >= 760:
            list_width = max(300, round(body.width * 0.38))
            list_panel = pygame.Rect(body.x, body.y, list_width, body.height)
            compare_panel = pygame.Rect(
                list_panel.right + 7,
                body.y,
                body.right - list_panel.right - 7,
                body.height,
            )
        else:
            list_height = max(155, round(body.height * 0.43))
            list_panel = pygame.Rect(body.x, body.y, body.width, list_height)
            compare_panel = pygame.Rect(
                body.x,
                list_panel.bottom + 7,
                body.width,
                body.bottom - list_panel.bottom - 7,
            )
        button_gap = 6
        footer_height = 31
        half = (list_panel.width - 18 - button_gap) // 2
        open_button = pygame.Rect(
            list_panel.x + 6,
            list_panel.bottom - footer_height - 5,
            half,
            footer_height,
        )
        delete_button = pygame.Rect(
            open_button.right + button_gap,
            open_button.y,
            list_panel.right - open_button.right - button_gap - 6,
            footer_height,
        )
        list_area = pygame.Rect(
            list_panel.x + 6,
            list_panel.y + 29,
            list_panel.width - 12,
            open_button.y - list_panel.y - 35,
        )
        metric_gap = 5
        metric_width = (
            compare_panel.width - 12 - metric_gap * (len(COMPARISON_METRICS) - 1)
        ) // len(COMPARISON_METRICS)
        metric_buttons = tuple(
            (
                key,
                pygame.Rect(
                    compare_panel.x + 6 + index * (metric_width + metric_gap),
                    compare_panel.y + 6,
                    metric_width,
                    27,
                ),
            )
            for index, key in enumerate(COMPARISON_METRICS)
        )
        export_width = min(130, (compare_panel.width - 17) // 2)
        export_pdf_button = pygame.Rect(
            compare_panel.right - export_width - 6,
            compare_panel.bottom - 34,
            export_width,
            28,
        )
        export_png_button = pygame.Rect(
            export_pdf_button.x - export_width - 5,
            export_pdf_button.y,
            export_width,
            28,
        )
        return HistoryGeometry(
            save_button,
            refresh_button,
            list_panel,
            list_area,
            open_button,
            delete_button,
            compare_panel,
            metric_buttons,
            export_png_button,
            export_pdf_button,
        )

    def _row_rects(
        self,
        geometry: HistoryGeometry,
    ) -> tuple[tuple[SavedExperimentSummary, pygame.Rect], ...]:
        row_height = 49
        visible = max(1, geometry.list_area.height // row_height)
        maximum = max(0, len(self.library.entries) - visible)
        self.scroll = min(self.scroll, maximum)
        entries = self.library.entries[self.scroll : self.scroll + visible]
        return tuple(
            (
                entry,
                pygame.Rect(
                    geometry.list_area.x,
                    geometry.list_area.y + index * row_height,
                    geometry.list_area.width,
                    row_height - 3,
                ),
            )
            for index, entry in enumerate(entries)
        )

    def handle_event(
        self,
        event: pygame.event.Event,
        content: pygame.Rect,
    ) -> str | None:
        geometry = self.geometry(content)
        if event.type == pygame.MOUSEWHEEL and geometry.list_area.collidepoint(
            pygame.mouse.get_pos()
        ):
            self.scroll = max(0, self.scroll - event.y)
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if geometry.save_button.collidepoint(event.pos):
            self._save_current()
            return None
        if geometry.refresh_button.collidepoint(event.pos):
            self.refresh()
            self.services.set_status("Experiment history refreshed.", 2.0)
            return None
        for metric_key, rect in geometry.metric_buttons:
            if rect.collidepoint(event.pos):
                self.metric_key = metric_key
                self._refresh_comparison()
                return None
        for entry, rect in self._row_rects(geometry):
            if not rect.collidepoint(event.pos):
                continue
            if entry.path in self.selected_paths:
                self.selected_paths.remove(entry.path)
            elif len(self.selected_paths) < 3:
                self.selected_paths.add(entry.path)
            else:
                self.services.set_status(
                    "Select at most three reports for a readable comparison.", 2.5
                )
            self.delete_confirmation = None
            self._refresh_comparison()
            return None
        selected = self._selected_entries()
        if geometry.open_button.collidepoint(event.pos):
            if len(selected) != 1:
                self.services.set_status("Select exactly one report to open.", 2.5)
                return None
            try:
                self.open_report(self.library.load(selected[0]))
            except (OSError, TypeError, ValueError) as exc:
                self.services.set_status(f"Could not open report: {exc}", 4.0)
                return None
            self.services.set_status(f"Opened saved report: {selected[0].name}", 3.0)
            return "results"
        if geometry.delete_button.collidepoint(event.pos):
            if len(selected) != 1:
                self.services.set_status("Select exactly one report to delete.", 2.5)
                return None
            entry = selected[0]
            if self.delete_confirmation != entry.path:
                self.delete_confirmation = entry.path
                self.services.set_status(
                    "Click Confirm Delete again to remove the selected report.", 3.0
                )
                return None
            try:
                self.library.delete(entry)
            except (OSError, ValueError) as exc:
                self.services.set_status(f"Delete failed: {exc}", 4.0)
            else:
                self.selected_paths.discard(entry.path)
                self.refresh()
                self.services.set_status("Saved experiment deleted.", 2.5)
            return None
        if geometry.export_png_button.collidepoint(event.pos):
            self._export_comparison(geometry.compare_panel, "png")
            return None
        if geometry.export_pdf_button.collidepoint(event.pos):
            self._export_comparison(geometry.compare_panel, "pdf")
            return None
        return None

    def _save_current(self) -> None:
        report = self.current_report()
        if report is None:
            self.services.set_status("Run or open an experiment before saving it.", 2.5)
            return
        existing = next(
            (
                entry
                for entry in self.library.entries
                if entry.completed_at == report.completed_at
                and entry.run_count == len(report.runs)
            ),
            None,
        )
        if existing is not None:
            self.selected_paths = {existing.path}
            self.services.set_status("This experiment is already in history.", 2.5)
            return
        try:
            entry = self.library.save(report)
        except (OSError, TypeError, ValueError) as exc:
            self.services.set_status(f"Could not save experiment: {exc}", 4.0)
            return
        self.selected_paths = {entry.path}
        self.scroll = 0
        self._refresh_comparison()
        self.services.set_status(f"Saved experiment: {entry.name}", 3.5)

    def _export_comparison(self, rect: pygame.Rect, kind: str) -> None:
        if self.comparison is None:
            self.services.set_status("Select two or three reports before exporting.", 2.5)
            return
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.export_directory.mkdir(parents=True, exist_ok=True)
        path = self.export_directory / f"experiment-comparison-{timestamp}.{kind}"
        surface = self.services.screen().subsurface(rect).copy()
        try:
            if kind == "png":
                pygame.image.save(surface, path)
            else:
                pixels = pygame.image.tobytes(surface, "RGB")
                image = Image.frombytes("RGB", surface.get_size(), pixels)
                image.save(path, "PDF", resolution=144.0)
        except (OSError, ValueError, pygame.error) as exc:
            self.services.set_status(f"Comparison export failed: {exc}", 4.0)
        else:
            self.services.set_status(f"Comparison {kind.upper()} saved: {path}", 5.0)

    def draw(self, content: pygame.Rect) -> None:
        geometry = self.geometry(content)
        screen = self.services.screen()
        theme = self.services.theme()
        tiny = self.services.tiny_font()
        heading = (
            "Saved reports stay in the app library; select 2-3 to compare equal-weight "
            "configuration means."
        )
        rendered = tiny.render(
            self._fit(tiny, heading, geometry.save_button.x - content.x - 12),
            True,
            theme["text"],
        )
        screen.blit(rendered, (content.x + 4, content.y + 10))
        self._button(
            geometry.save_button,
            "Save Current Result",
            enabled=self.current_report() is not None,
            accent=(90, 220, 130),
        )
        self._button(geometry.refresh_button, "Refresh Library")
        self._draw_library(geometry)
        self._draw_comparison(geometry)

    def _draw_library(self, geometry: HistoryGeometry) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        tiny = self.services.tiny_font()
        pygame.draw.rect(screen, theme["stats_bar"], geometry.list_panel, border_radius=6)
        pygame.draw.rect(screen, theme["grid"], geometry.list_panel, 1, border_radius=6)
        title = (
            f"SAVED EXPERIMENTS · {len(self.library.entries)}/{MAX_SAVED_REPORTS} · "
            f"SELECTED {len(self.selected_paths)}/3"
        )
        if self.library.errors:
            title += f" · {len(self.library.errors)} unreadable ignored"
        screen.blit(
            tiny.render(
                self._fit(tiny, title, geometry.list_panel.width - 14),
                True,
                (90, 220, 130),
            ),
            (geometry.list_panel.x + 7, geometry.list_panel.y + 7),
        )
        rows = self._row_rects(geometry)
        if not rows:
            message = tiny.render(
                "No saved reports yet. Save the current result above.",
                True,
                theme["button_text"],
            )
            screen.blit(message, message.get_rect(center=geometry.list_area.center))
        for index, (entry, rect) in enumerate(rows):
            selected = entry.path in self.selected_paths
            pygame.draw.rect(
                screen,
                theme["button_hover"] if selected else theme["button"],
                rect,
                border_radius=4,
            )
            pygame.draw.rect(
                screen,
                (90, 220, 130) if selected else theme["grid"],
                rect,
                2 if selected else 1,
                border_radius=4,
            )
            check = pygame.Rect(rect.x + 7, rect.centery - 7, 14, 14)
            pygame.draw.rect(screen, theme["stats_bar"], check, border_radius=2)
            pygame.draw.rect(
                screen,
                (90, 220, 130) if selected else theme["grid"],
                check,
                2,
                border_radius=2,
            )
            if selected:
                pygame.draw.line(
                    screen,
                    (90, 220, 130),
                    (check.x + 3, check.centery),
                    (check.centerx - 1, check.bottom - 3),
                    2,
                )
                pygame.draw.line(
                    screen,
                    (90, 220, 130),
                    (check.centerx - 1, check.bottom - 3),
                    (check.right - 2, check.y + 3),
                    2,
                )
            name = tiny.render(
                self._fit(tiny, entry.name, rect.width - 38),
                True,
                theme["text"],
            )
            details = (
                f"{entry.dimension.upper()} · {entry.mode_label} · "
                f"{entry.run_count} runs · {entry.configuration_count} configs"
            )
            detail_surface = tiny.render(
                self._fit(tiny, details, rect.width - 38),
                True,
                theme["button_text"],
            )
            screen.blit(name, (rect.x + 29, rect.y + 7))
            screen.blit(detail_surface, (rect.x + 29, rect.y + 25))
        selected = self._selected_entries()
        self._button(
            geometry.open_button,
            "Open Selected in Results",
            enabled=len(selected) == 1,
        )
        delete_label = (
            "Confirm Delete"
            if len(selected) == 1
            and self.delete_confirmation == selected[0].path
            else "Delete Selected"
        )
        self._button(
            geometry.delete_button,
            delete_label,
            enabled=len(selected) == 1,
            accent=(238, 100, 100) if delete_label == "Confirm Delete" else None,
        )

    def _draw_comparison(self, geometry: HistoryGeometry) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        panel = geometry.compare_panel
        pygame.draw.rect(screen, theme["stats_bar"], panel, border_radius=6)
        pygame.draw.rect(screen, theme["grid"], panel, 1, border_radius=6)
        for metric_key, rect in geometry.metric_buttons:
            label = COMPARISON_METRICS[metric_key][0]
            self._button(
                rect,
                label,
                accent=METRIC_COLORS[metric_key]
                if metric_key == self.metric_key
                else None,
            )
        content = pygame.Rect(
            panel.x + 7,
            panel.y + 40,
            panel.width - 14,
            geometry.export_png_button.y - panel.y - 47,
        )
        if self.comparison is None:
            selected = len(self.selected_paths)
            message = (
                f"{selected}/2 minimum selected. Choose two or three saved reports "
                "from the library."
            )
            rendered = self.services.small_font().render(
                self._fit(self.services.small_font(), message, content.width - 20),
                True,
                theme["button_text"],
            )
            screen.blit(rendered, rendered.get_rect(center=content.center))
        else:
            self._draw_comparison_chart(content, self.comparison)
        self._button(
            geometry.export_png_button,
            "Export PNG",
            enabled=self.comparison is not None,
        )
        self._button(
            geometry.export_pdf_button,
            "Export PDF",
            enabled=self.comparison is not None,
        )

    def _draw_comparison_chart(
        self,
        rect: pygame.Rect,
        comparison: ReportComparison,
    ) -> None:
        screen = self.services.screen()
        theme = self.services.theme()
        tiny = self.services.tiny_font()
        accent = METRIC_COLORS[comparison.metric_key]
        title = (
            f"{comparison.metric_label.upper()} · BAR = EXPERIMENT MEAN · "
            "WHISKER = CONFIGURATION RANGE"
        )
        screen.blit(
            tiny.render(self._fit(tiny, title, rect.width), True, accent),
            (rect.x, rect.y),
        )
        chart_height = min(205, max(58, rect.height - 82))
        chart = pygame.Rect(rect.x, rect.y + 22, rect.width, chart_height)
        maximum = max(entry.maximum for entry in comparison.entries) * 1.05
        maximum = max(maximum, 1e-9)
        label_width = min(230, max(105, round(chart.width * 0.32)))
        value_width = 62
        plot_left = chart.x + label_width
        plot_width = max(30, chart.width - label_width - value_width)
        row_height = chart.height // len(comparison.entries)
        palette = ((82, 190, 235), (242, 184, 72), (177, 126, 235))
        for index, entry in enumerate(comparison.entries):
            center_y = chart.y + index * row_height + row_height // 2
            name = tiny.render(
                self._fit(tiny, entry.summary.name, label_width - 10),
                True,
                theme["text"],
            )
            screen.blit(name, (chart.x, center_y - name.get_height() // 2))
            track = pygame.Rect(plot_left, center_y - 7, plot_width, 14)
            pygame.draw.rect(screen, theme["button"], track, border_radius=5)
            fill = track.copy()
            fill.width = max(1, round(plot_width * entry.mean / maximum))
            pygame.draw.rect(screen, palette[index], fill, border_radius=5)
            low_x = plot_left + round(plot_width * entry.minimum / maximum)
            high_x = plot_left + round(plot_width * entry.maximum / maximum)
            pygame.draw.line(screen, theme["text"], (low_x, center_y), (high_x, center_y), 2)
            pygame.draw.line(screen, theme["text"], (low_x, center_y - 6), (low_x, center_y + 6), 1)
            pygame.draw.line(screen, theme["text"], (high_x, center_y - 6), (high_x, center_y + 6), 1)
            value = tiny.render(
                f"{entry.mean:.3f}{comparison.unit}", True, theme["text"]
            )
            screen.blit(value, value.get_rect(midleft=(track.right + 7, center_y)))
        insight_y = chart.bottom + 7
        low = min(comparison.entries, key=lambda entry: entry.mean)
        best = comparison.best
        difference = best.mean - low.mean
        percent = difference / abs(low.mean) * 100 if low.mean else None
        difference_label = f"{difference:.3f}{comparison.unit}"
        if percent is not None:
            difference_label += f" ({percent:.1f}% relative)"
        summary = (
            f"Highest experiment mean: {best.summary.name}. Difference from lowest: "
            f"{difference_label}."
        )
        lines = (summary, *comparison.notes)
        for index, line in enumerate(lines[:3]):
            surface = tiny.render(
                self._fit(tiny, line, rect.width),
                True,
                accent if index == 0 else theme["button_text"],
            )
            screen.blit(surface, (rect.x, insight_y + index * 15))
        details_y = insight_y + min(3, len(lines)) * 15 + 8
        available = rect.bottom - details_y
        detail_height = 42
        if available >= detail_height + 20:
            heading = tiny.render("EXPERIMENT DESIGNS", True, theme["text"])
            screen.blit(heading, (rect.x, details_y))
            details_y += 18
            visible = min(
                len(comparison.entries),
                max(1, (rect.bottom - details_y) // detail_height),
            )
            for index, entry in enumerate(comparison.entries[:visible]):
                card = pygame.Rect(
                    rect.x,
                    details_y + index * detail_height,
                    rect.width,
                    detail_height - 4,
                )
                pygame.draw.rect(screen, theme["button"], card, border_radius=4)
                pygame.draw.rect(screen, theme["grid"], card, 1, border_radius=4)
                label = (
                    f"{entry.summary.name} · best: {entry.best_configuration}"
                )
                screen.blit(
                    tiny.render(
                        self._fit(tiny, label, card.width - 12),
                        True,
                        palette[index],
                    ),
                    (card.x + 6, card.y + 5),
                )
                screen.blit(
                    tiny.render(
                        self._fit(tiny, entry.design_summary, card.width - 12),
                        True,
                        theme["button_text"],
                    ),
                    (card.x + 6, card.y + 21),
                )

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
        pygame.draw.rect(
            screen,
            theme["button"] if enabled else theme["stats_bar"],
            rect,
            border_radius=4,
        )
        pygame.draw.rect(
            screen,
            accent or theme["grid"],
            rect,
            2 if accent else 1,
            border_radius=4,
        )
        font = self.services.tiny_font()
        color = theme["button_text"] if enabled else theme["grid"]
        text = font.render(self._fit(font, label, rect.width - 8), True, color)
        screen.blit(text, text.get_rect(center=rect.center))
