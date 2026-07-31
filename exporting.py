"""Safe, deterministic export helpers for cellular-automata experiments."""

from __future__ import annotations

import csv
import json
import os
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from uuid import uuid4

import numpy as np
from PIL import Image

from app_paths import APPLICATION_PATHS
from scientific_analysis import AnalysisSample
from session_storage import safe_storage_filename

Color = tuple[int, int, int]
Palette = Mapping[int, Color]

EXPORT_DIRECTORY = APPLICATION_PATHS.exports
MAX_ANIMATION_FRAMES = 120


class ExportError(RuntimeError):
    """Raised when an export cannot be encoded or written safely."""


@dataclass(frozen=True)
class RasterFrame:
    """One generation represented as a rectangular or center-aligned grid."""

    generation: int
    rows: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("Frame generation cannot be negative.")
        if not self.rows or not any(self.rows):
            raise ValueError("Raster frames must contain at least one cell.")


@dataclass(frozen=True)
class RGBFrame:
    """One immutable, top-to-bottom RGB viewport frame."""

    generation: int
    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("Frame generation cannot be negative.")
        if self.width < 1 or self.height < 1:
            raise ValueError("RGB frame dimensions must be positive.")
        if len(self.pixels) != self.width * self.height * 3:
            raise ValueError("RGB frame byte count does not match its dimensions.")

    @classmethod
    def from_array(cls, generation: int, pixels: np.ndarray) -> "RGBFrame":
        """Freeze one uint8 ``height x width x RGB`` array for background work."""

        array = np.asarray(pixels)
        if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 3:
            raise TypeError("RGB frame arrays must have uint8 shape (height, width, 3).")
        contiguous = np.ascontiguousarray(array)
        return cls(
            generation=int(generation),
            width=int(contiguous.shape[1]),
            height=int(contiguous.shape[0]),
            pixels=contiguous.tobytes(order="C"),
        )

    def as_array(self, *, even_dimensions: bool = False) -> np.ndarray:
        """Return an array view, optionally padded for YUV420 video encoders."""

        source = np.frombuffer(self.pixels, dtype=np.uint8).reshape(
            self.height,
            self.width,
            3,
        )
        if not even_dimensions or not (self.height % 2 or self.width % 2):
            return source
        height = self.height + self.height % 2
        width = self.width + self.width % 2
        padded = np.zeros((height, width, 3), dtype=np.uint8)
        padded[: self.height, : self.width] = source
        return padded


@dataclass(frozen=True)
class ExportOutcome:
    """Completed background export result consumed by the Pygame thread."""

    label: str
    path: Path | None = None
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return self.path is not None and not self.error


def sampled_indices(frame_count: int, maximum: int = MAX_ANIMATION_FRAMES) -> tuple[int, ...]:
    """Return evenly distributed indices while always preserving both ends."""

    if frame_count < 0:
        raise ValueError("frame_count cannot be negative")
    if maximum < 2:
        raise ValueError("maximum must be at least two")
    if frame_count <= maximum:
        return tuple(range(frame_count))
    return tuple(
        round(index * (frame_count - 1) / (maximum - 1))
        for index in range(maximum)
    )


def export_path(
    stem: str,
    suffix: str,
    *,
    directory: Path | None = None,
    timestamp: datetime | None = None,
) -> Path:
    """Create a unique, timestamped path without touching the filesystem."""

    normalized_suffix = suffix.lower()
    if not normalized_suffix.startswith(".") or len(normalized_suffix) < 2:
        raise ValueError("suffix must include a file extension")
    safe_stem = safe_storage_filename(stem)
    moment = timestamp or datetime.now(timezone.utc)
    timestamp_text = moment.strftime("%Y%m%d-%H%M%S")
    target_directory = directory or EXPORT_DIRECTORY
    candidate = target_directory / f"{safe_stem}-{timestamp_text}{normalized_suffix}"
    number = 2
    while candidate.exists():
        candidate = target_directory / (
            f"{safe_stem}-{timestamp_text}-{number}{normalized_suffix}"
        )
        number += 1
    return candidate


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.stem}-{uuid4().hex}.tmp{path.suffix}")


def _prepare_target(path: Path, *, overwrite: bool) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Export already exists: {path.name}")
    return path


def _replace_temporary(temporary: Path, target: Path) -> Path:
    try:
        os.replace(temporary, target)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ExportError(f"Could not finalize '{target.name}': {exc}") from exc
    return target


def _canvas_shape(frames: Sequence[RasterFrame]) -> tuple[int, int]:
    if not frames:
        raise ValueError("At least one frame is required")
    height = max(len(frame.rows) for frame in frames)
    width = max(len(row) for frame in frames for row in frame.rows)
    return height, width


def choose_scale(
    shape: tuple[int, int],
    *,
    maximum_pixels: int,
    maximum_scale: int = 8,
) -> int:
    """Choose nearest-neighbor scale while keeping both axes bounded."""

    height, width = shape
    if height <= 0 or width <= 0:
        raise ValueError("shape must be positive")
    if maximum_pixels < 1 or maximum_scale < 1:
        raise ValueError("scale limits must be positive")
    return max(1, min(maximum_scale, maximum_pixels // max(height, width)))


def render_frame_array(
    frame: RasterFrame,
    palette: Palette,
    *,
    canvas_shape: tuple[int, int] | None = None,
    scale: int = 1,
    center_rows: bool = True,
    even_dimensions: bool = False,
) -> np.ndarray:
    """Render one grid to an RGB array using exact state colors."""

    if scale < 1:
        raise ValueError("scale must be positive")
    height, width = canvas_shape or _canvas_shape((frame,))
    if len(frame.rows) > height or any(len(row) > width for row in frame.rows):
        raise ValueError("canvas_shape is smaller than the frame")
    if 0 not in palette:
        raise ValueError("palette must define state 0")

    canvas = np.empty((height, width, 3), dtype=np.uint8)
    canvas[:, :] = palette[0]
    for row_index, row in enumerate(frame.rows):
        left = (width - len(row)) // 2 if center_rows else 0
        for column, state in enumerate(row):
            try:
                canvas[row_index, left + column] = palette[state]
            except KeyError as exc:
                raise ValueError(f"palette has no color for state {state}") from exc

    if scale > 1:
        canvas = np.repeat(np.repeat(canvas, scale, axis=0), scale, axis=1)
    if even_dimensions:
        pad_height = canvas.shape[0] % 2
        pad_width = canvas.shape[1] % 2
        if pad_height or pad_width:
            padded = np.empty(
                (
                    canvas.shape[0] + pad_height,
                    canvas.shape[1] + pad_width,
                    3,
                ),
                dtype=np.uint8,
            )
            padded[:, :] = palette[0]
            padded[: canvas.shape[0], : canvas.shape[1]] = canvas
            canvas = padded
    return canvas


def save_png(
    frame: RasterFrame,
    palette: Palette,
    path: Path,
    *,
    scale: int | None = None,
    overwrite: bool = False,
) -> Path:
    """Atomically save a lossless nearest-neighbor diagram or grid PNG."""

    target = _prepare_target(path, overwrite=overwrite)
    shape = _canvas_shape((frame,))
    render_scale = scale or choose_scale(shape, maximum_pixels=2048)
    image = Image.fromarray(
        render_frame_array(frame, palette, scale=render_scale),
    )
    temporary = _temporary_path(target)
    try:
        image.save(temporary, format="PNG", optimize=True)
        return _replace_temporary(temporary, target)
    except (OSError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write PNG '{target.name}': {exc}") from exc


def save_rgb_png(
    frame: RGBFrame,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Atomically save an already-rendered RGB viewport as lossless PNG."""

    target = _prepare_target(path, overwrite=overwrite)
    temporary = _temporary_path(target)
    try:
        Image.fromarray(frame.as_array()).save(
            temporary,
            format="PNG",
            optimize=True,
        )
        return _replace_temporary(temporary, target)
    except (OSError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write PNG '{target.name}': {exc}") from exc


def save_gif(
    frames: Sequence[RasterFrame],
    palette: Palette,
    path: Path,
    *,
    duration_ms: int = 100,
    loop: int = 0,
    scale: int | None = None,
    overwrite: bool = False,
) -> Path:
    """Atomically save timeline frames as an animated GIF."""

    if duration_ms < 10:
        raise ValueError("duration_ms must be at least 10")
    target = _prepare_target(path, overwrite=overwrite)
    shape = _canvas_shape(frames)
    render_scale = scale or choose_scale(shape, maximum_pixels=960)
    images = [
        Image.fromarray(
            render_frame_array(
                frame,
                palette,
                canvas_shape=shape,
                scale=render_scale,
            ),
        )
        for frame in frames
    ]
    temporary = _temporary_path(target)
    try:
        images[0].save(
            temporary,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=loop,
            optimize=False,
            disposal=2,
        )
        return _replace_temporary(temporary, target)
    except (OSError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write GIF '{target.name}': {exc}") from exc


def _validate_rgb_animation(frames: Sequence[RGBFrame]) -> None:
    if not frames:
        raise ValueError("At least one RGB frame is required")
    size = (frames[0].width, frames[0].height)
    if any((frame.width, frame.height) != size for frame in frames):
        raise ValueError("All RGB animation frames must have the same dimensions")


def save_rgb_gif(
    frames: Sequence[RGBFrame],
    path: Path,
    *,
    duration_ms: int = 100,
    loop: int = 0,
    overwrite: bool = False,
) -> Path:
    """Atomically encode pre-rendered viewport frames as an animated GIF."""

    if duration_ms < 10:
        raise ValueError("duration_ms must be at least 10")
    _validate_rgb_animation(frames)
    target = _prepare_target(path, overwrite=overwrite)
    images = [Image.fromarray(frame.as_array()) for frame in frames]
    temporary = _temporary_path(target)
    try:
        images[0].save(
            temporary,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=loop,
            optimize=False,
            disposal=2,
        )
        return _replace_temporary(temporary, target)
    except (OSError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write GIF '{target.name}': {exc}") from exc


def save_mp4(
    frames: Sequence[RasterFrame],
    palette: Palette,
    path: Path,
    *,
    fps: int = 20,
    scale: int | None = None,
    overwrite: bool = False,
) -> Path:
    """Stream timeline frames to an H.264 MP4 using imageio-ffmpeg."""

    if fps < 1 or fps > 120:
        raise ValueError("fps must be between 1 and 120")
    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover - guarded by requirements.txt
        raise ExportError(
            "MP4 export requires imageio and imageio-ffmpeg."
        ) from exc

    target = _prepare_target(path, overwrite=overwrite)
    shape = _canvas_shape(frames)
    render_scale = scale or choose_scale(shape, maximum_pixels=960)
    temporary = _temporary_path(target)
    writer = None
    try:
        writer = imageio.get_writer(
            temporary,
            fps=fps,
            codec="libx264",
            format="FFMPEG",
            macro_block_size=1,
            pixelformat="yuv420p",
        )
        for frame in frames:
            writer.append_data(
                render_frame_array(
                    frame,
                    palette,
                    canvas_shape=shape,
                    scale=render_scale,
                    even_dimensions=True,
                )
            )
        writer.close()
        writer = None
        return _replace_temporary(temporary, target)
    except Exception as exc:
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write MP4 '{target.name}': {exc}") from exc


def save_rgb_mp4(
    frames: Sequence[RGBFrame],
    path: Path,
    *,
    fps: int = 20,
    overwrite: bool = False,
) -> Path:
    """Stream pre-rendered RGB viewport frames to an H.264 MP4."""

    if fps < 1 or fps > 120:
        raise ValueError("fps must be between 1 and 120")
    _validate_rgb_animation(frames)
    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover - guarded by requirements.txt
        raise ExportError(
            "MP4 export requires imageio and imageio-ffmpeg."
        ) from exc

    target = _prepare_target(path, overwrite=overwrite)
    temporary = _temporary_path(target)
    writer = None
    try:
        writer = imageio.get_writer(
            temporary,
            fps=fps,
            codec="libx264",
            format="FFMPEG",
            macro_block_size=1,
            pixelformat="yuv420p",
        )
        for frame in frames:
            writer.append_data(frame.as_array(even_dimensions=True))
        writer.close()
        writer = None
        return _replace_temporary(temporary, target)
    except Exception as exc:
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write MP4 '{target.name}': {exc}") from exc


def save_analysis_csv(
    samples: Iterable[AnalysisSample],
    path: Path,
    *,
    period: int | None,
    stabilization_generation: int | None,
    overwrite: bool = False,
) -> Path:
    """Atomically write generation measurements in spreadsheet-friendly CSV."""

    target = _prepare_target(path, overwrite=overwrite)
    temporary = _temporary_path(target)
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                (
                    "generation",
                    "population",
                    "density_percent",
                    "normalized_entropy",
                    "normalized_block_entropy",
                    "change_rate_percent",
                    "neighbor_agreement_percent",
                    "population_growth_percent_of_lattice",
                    "state_utilization_percent",
                    "detected_period",
                    "stabilization_generation",
                )
            )
            for sample in samples:
                writer.writerow(
                    (
                        sample.generation,
                        sample.population,
                        f"{sample.density:.8f}",
                        f"{sample.entropy:.8f}",
                        f"{sample.block_entropy:.8f}",
                        f"{sample.change_rate:.8f}",
                        f"{sample.neighbor_agreement:.8f}",
                        f"{sample.growth_rate:.8f}",
                        f"{sample.state_utilization:.8f}",
                        "" if period is None else period,
                        (
                            ""
                            if stabilization_generation is None
                            else stabilization_generation
                        ),
                    )
                )
        return _replace_temporary(temporary, target)
    except (OSError, TypeError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write CSV '{target.name}': {exc}") from exc


def save_experiment_json(
    document: Mapping[str, Any],
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Atomically save a UTF-8, human-readable experiment document."""

    target = _prepare_target(path, overwrite=overwrite)
    temporary = _temporary_path(target)
    try:
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return _replace_temporary(temporary, target)
    except (OSError, TypeError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        raise ExportError(f"Could not write JSON '{target.name}': {exc}") from exc


class ExportRunner:
    """Serialize one potentially expensive export away from the event thread."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="ca-export",
        )
        self._future: Future[Path] | None = None
        self._label = ""

    @property
    def busy(self) -> bool:
        return self._future is not None and not self._future.done()

    @property
    def label(self) -> str:
        return self._label

    def submit(self, label: str, work: Callable[[], Path]) -> bool:
        if self._future is not None:
            return False
        self._label = label
        self._future = self._executor.submit(work)
        return True

    def poll(self) -> ExportOutcome | None:
        if self._future is None or not self._future.done():
            return None
        future = self._future
        label = self._label
        self._future = None
        self._label = ""
        try:
            return ExportOutcome(label=label, path=future.result())
        except Exception as exc:
            return ExportOutcome(label=label, error=str(exc))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
