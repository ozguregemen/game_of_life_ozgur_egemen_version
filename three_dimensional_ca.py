"""UI-independent data model and neighborhood tools for 3D automata."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import prod
from numbers import Integral
from types import MappingProxyType
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

VolumeShape: TypeAlias = tuple[int, int, int]
Position3D: TypeAlias = tuple[int, int, int]
Offset3D: TypeAlias = tuple[int, int, int]
StateVolume: TypeAlias = NDArray[np.uint8]

AXIS_Z = "z"
AXIS_Y = "y"
AXIS_X = "x"
SLICE_AXES = (AXIS_Z, AXIS_Y, AXIS_X)

BOUNDARY_FIXED = "fixed"
BOUNDARY_WRAP = "wrap"
BOUNDARY_REFLECT = "reflect"
BOUNDARY_MODES = (BOUNDARY_FIXED, BOUNDARY_WRAP, BOUNDARY_REFLECT)

MAX_UINT8_STATES = 256
DEFAULT_MAX_AXIS_LENGTH = 256
DEFAULT_MAX_CELLS = 256**3
DEFAULT_MAX_VOLUME_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_WORKING_BYTES = 128 * 1024 * 1024


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer.")
    normalized = int(value)
    if normalized < 1:
        raise ValueError(f"{name} must be positive.")
    return normalized


def normalize_volume_shape(shape: Sequence[int]) -> VolumeShape:
    """Validate a ``(depth, rows, columns)`` volume shape."""
    try:
        dimensions = tuple(shape)
    except TypeError as exc:
        raise TypeError("Volume shape must contain depth, rows, and columns.") from exc
    if len(dimensions) != 3:
        raise ValueError("Volume shape must contain depth, rows, and columns.")
    depth, rows, columns = (
        _positive_integer(value, name)
        for value, name in zip(
            dimensions,
            ("depth", "rows", "columns"),
            strict=True,
        )
    )
    return depth, rows, columns


def _validate_state_count(state_count: int) -> int:
    count = _positive_integer(state_count, "state_count")
    if not 2 <= count <= MAX_UINT8_STATES:
        raise ValueError(
            f"state_count must be between 2 and {MAX_UINT8_STATES}."
        )
    return count


def _validate_state(value: object, state_count: int, name: str = "state") -> int:
    if isinstance(value, bool):
        normalized = int(value)
    elif isinstance(value, Integral):
        normalized = int(value)
    else:
        raise TypeError(f"{name} must be an integer.")
    if not 0 <= normalized < state_count:
        raise ValueError(f"{name} must be between 0 and {state_count - 1}.")
    return normalized


def _validate_boundary(boundary: str) -> str:
    if boundary not in BOUNDARY_MODES:
        raise ValueError(f"Unknown 3D boundary mode: {boundary}")
    return boundary


def _reflected_index(index: int, length: int) -> int:
    """Mirror an arbitrary coordinate like NumPy's ``reflect`` pad mode."""
    if length == 1:
        return 0
    period = 2 * (length - 1)
    reflected = index % period
    return reflected if reflected < length else period - reflected


def _normalize_position(position: Sequence[int]) -> Position3D:
    try:
        values = tuple(position)
    except TypeError as exc:
        raise TypeError("Position must contain z, y, and x coordinates.") from exc
    if len(values) != 3:
        raise ValueError("Position must contain z, y, and x coordinates.")
    normalized: list[int] = []
    for value, name in zip(values, ("z", "y", "x"), strict=True):
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise TypeError(f"{name} coordinate must be an integer.")
        normalized.append(int(value))
    return normalized[0], normalized[1], normalized[2]


@dataclass(frozen=True)
class VolumeLimits:
    """Hard allocation limits for one dense uint8 volume and its work arrays."""

    max_axis_length: int = DEFAULT_MAX_AXIS_LENGTH
    max_cells: int = DEFAULT_MAX_CELLS
    max_volume_bytes: int = DEFAULT_MAX_VOLUME_BYTES
    max_working_bytes: int = DEFAULT_MAX_WORKING_BYTES

    def __post_init__(self) -> None:
        for field_name in (
            "max_axis_length",
            "max_cells",
            "max_volume_bytes",
            "max_working_bytes",
        ):
            object.__setattr__(
                self,
                field_name,
                _positive_integer(getattr(self, field_name), field_name),
            )

    def validate_shape(
        self,
        shape: Sequence[int],
        *,
        bytes_per_cell: int = 1,
    ) -> VolumeShape:
        """Return a normalized shape if its dense allocation fits the budget."""
        normalized = normalize_volume_shape(shape)
        if any(length > self.max_axis_length for length in normalized):
            raise MemoryError(
                "Volume axis exceeds the configured maximum of "
                f"{self.max_axis_length} cells."
            )
        cell_count = prod(normalized)
        if cell_count > self.max_cells:
            raise MemoryError(
                f"Volume requires {cell_count:,} cells; limit is "
                f"{self.max_cells:,}."
            )
        item_size = _positive_integer(bytes_per_cell, "bytes_per_cell")
        required_bytes = cell_count * item_size
        if required_bytes > self.max_volume_bytes:
            raise MemoryError(
                f"Volume requires {required_bytes:,} bytes; limit is "
                f"{self.max_volume_bytes:,}."
            )
        return normalized

    def validate_working_bytes(self, required_bytes: int) -> int:
        """Reject a temporary operation that would exceed the work budget."""
        required = _positive_integer(required_bytes, "required_bytes")
        if required > self.max_working_bytes:
            raise MemoryError(
                f"Operation needs about {required:,} working bytes; limit is "
                f"{self.max_working_bytes:,}."
            )
        return required


DEFAULT_VOLUME_LIMITS = VolumeLimits()


@dataclass(frozen=True)
class Neighborhood3D:
    """A named, deterministic set of ``(dz, dy, dx)`` neighbor offsets."""

    key: str
    label: str
    offsets: tuple[Offset3D, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("Neighborhood key cannot be empty.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("Neighborhood label cannot be empty.")
        normalized: list[Offset3D] = []
        for offset in self.offsets:
            values = _normalize_position(offset)
            if values == (0, 0, 0):
                raise ValueError("A neighborhood cannot include its center cell.")
            normalized.append(values)
        if not normalized:
            raise ValueError("A neighborhood must contain at least one offset.")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Neighborhood offsets must be unique.")
        object.__setattr__(self, "key", self.key.strip())
        object.__setattr__(self, "label", self.label.strip())
        object.__setattr__(self, "offsets", tuple(normalized))

    @property
    def size(self) -> int:
        """Return the number of neighboring positions."""
        return len(self.offsets)

    @property
    def radius(self) -> int:
        """Return the largest absolute axis displacement."""
        return max(abs(component) for offset in self.offsets for component in offset)


def moore_neighborhood(radius: int = 1) -> Neighborhood3D:
    """Create a cubic Moore neighborhood; radius one contains 26 cells."""
    normalized_radius = _positive_integer(radius, "radius")
    offsets = tuple(
        (dz, dy, dx)
        for dz in range(-normalized_radius, normalized_radius + 1)
        for dy in range(-normalized_radius, normalized_radius + 1)
        for dx in range(-normalized_radius, normalized_radius + 1)
        if (dz, dy, dx) != (0, 0, 0)
    )
    return Neighborhood3D(
        key=f"moore_r{normalized_radius}",
        label=f"Moore radius {normalized_radius}",
        offsets=offsets,
    )


def von_neumann_neighborhood(radius: int = 1) -> Neighborhood3D:
    """Create a Manhattan-distance neighborhood; radius one has six faces."""
    normalized_radius = _positive_integer(radius, "radius")
    offsets = tuple(
        (dz, dy, dx)
        for dz in range(-normalized_radius, normalized_radius + 1)
        for dy in range(-normalized_radius, normalized_radius + 1)
        for dx in range(-normalized_radius, normalized_radius + 1)
        if 0 < abs(dz) + abs(dy) + abs(dx) <= normalized_radius
    )
    return Neighborhood3D(
        key=f"von_neumann_r{normalized_radius}",
        label=f"Von Neumann radius {normalized_radius}",
        offsets=offsets,
    )


MOORE_NEIGHBORHOOD = moore_neighborhood()
VON_NEUMANN_NEIGHBORHOOD = von_neumann_neighborhood()
NEIGHBORHOODS_3D = MappingProxyType(
    {
        "moore": MOORE_NEIGHBORHOOD,
        "von_neumann": VON_NEUMANN_NEIGHBORHOOD,
    }
)


def _count_dtype(neighbor_count: int) -> np.dtype[np.unsignedinteger]:
    if neighbor_count <= np.iinfo(np.uint8).max:
        return np.dtype(np.uint8)
    if neighbor_count <= np.iinfo(np.uint16).max:
        return np.dtype(np.uint16)
    if neighbor_count <= np.iinfo(np.uint32).max:
        return np.dtype(np.uint32)
    return np.dtype(np.uint64)


class Volume3D:
    """Own a bounded, C-contiguous ``uint8`` state volume.

    The canonical axis order is ``(z, y, x)`` or equivalently
    ``(depth, rows, columns)``. Public NumPy views are read-only; mutations go
    through validated cell, fill, replacement, and slice-writing methods.
    """

    def __init__(
        self,
        cells: np.ndarray | Sequence[Sequence[Sequence[int]]],
        *,
        state_count: int = 2,
        boundary: str = BOUNDARY_FIXED,
        outside_state: int = 0,
        neighborhood: Neighborhood3D = MOORE_NEIGHBORHOOD,
        limits: VolumeLimits = DEFAULT_VOLUME_LIMITS,
    ) -> None:
        if not isinstance(limits, VolumeLimits):
            raise TypeError("limits must be a VolumeLimits instance.")
        self._limits = limits
        self._state_count = _validate_state_count(state_count)
        self._cells = self._validated_cells(cells)
        self._boundary = _validate_boundary(boundary)
        self._outside_state = _validate_state(
            outside_state,
            self.state_count,
            "outside_state",
        )
        self._neighborhood = self._validate_neighborhood(neighborhood)

    @classmethod
    def empty(
        cls,
        shape: Sequence[int],
        *,
        fill_state: int = 0,
        state_count: int = 2,
        boundary: str = BOUNDARY_FIXED,
        outside_state: int = 0,
        neighborhood: Neighborhood3D = MOORE_NEIGHBORHOOD,
        limits: VolumeLimits = DEFAULT_VOLUME_LIMITS,
    ) -> Volume3D:
        """Create a uniformly filled volume after checking allocation limits."""
        if not isinstance(limits, VolumeLimits):
            raise TypeError("limits must be a VolumeLimits instance.")
        normalized_state_count = _validate_state_count(state_count)
        normalized_fill = _validate_state(
            fill_state,
            normalized_state_count,
            "fill_state",
        )
        normalized_shape = limits.validate_shape(shape)
        cells = np.full(normalized_shape, normalized_fill, dtype=np.uint8)
        return cls(
            cells,
            state_count=normalized_state_count,
            boundary=boundary,
            outside_state=outside_state,
            neighborhood=neighborhood,
            limits=limits,
        )

    def _validated_cells(
        self,
        cells: np.ndarray | Sequence[Sequence[Sequence[int]]],
    ) -> StateVolume:
        try:
            raw = np.asarray(cells)
        except (TypeError, ValueError) as exc:
            raise ValueError("3D cells must form a rectangular volume.") from exc
        if raw.ndim != 3 or 0 in raw.shape:
            raise ValueError("3D cells must form a non-empty rectangular volume.")
        if raw.dtype.kind not in "biu":
            raise TypeError("3D cell states must be integers.")
        self.limits.validate_shape(raw.shape, bytes_per_cell=np.dtype(np.uint8).itemsize)
        if np.any(raw < 0) or np.any(raw >= self.state_count):
            raise ValueError(
                f"3D cell states must be between 0 and {self.state_count - 1}."
            )
        return np.array(raw, dtype=np.uint8, order="C", copy=True)

    @staticmethod
    def _validate_neighborhood(neighborhood: Neighborhood3D) -> Neighborhood3D:
        if not isinstance(neighborhood, Neighborhood3D):
            raise TypeError("neighborhood must be a Neighborhood3D instance.")
        return neighborhood

    @property
    def limits(self) -> VolumeLimits:
        return self._limits

    @property
    def state_count(self) -> int:
        return self._state_count

    @property
    def shape(self) -> VolumeShape:
        return self._cells.shape

    @property
    def depth(self) -> int:
        return self.shape[0]

    @property
    def rows(self) -> int:
        return self.shape[1]

    @property
    def columns(self) -> int:
        return self.shape[2]

    @property
    def cell_count(self) -> int:
        return self._cells.size

    @property
    def nbytes(self) -> int:
        return self._cells.nbytes

    @property
    def boundary(self) -> str:
        return self._boundary

    @boundary.setter
    def boundary(self, value: str) -> None:
        self._boundary = _validate_boundary(value)

    @property
    def outside_state(self) -> int:
        return self._outside_state

    @outside_state.setter
    def outside_state(self, value: int) -> None:
        self._outside_state = _validate_state(
            value,
            self.state_count,
            "outside_state",
        )

    @property
    def neighborhood(self) -> Neighborhood3D:
        return self._neighborhood

    @neighborhood.setter
    def neighborhood(self, value: Neighborhood3D) -> None:
        self._neighborhood = self._validate_neighborhood(value)

    @property
    def cells(self) -> StateVolume:
        """Return a read-only view of the owned state volume."""
        view = self._cells.view()
        view.flags.writeable = False
        return view

    def to_numpy(self, *, copy: bool = True) -> StateVolume:
        """Return a writable copy or a zero-copy read-only volume view."""
        if copy:
            return self._cells.copy()
        return self.cells

    def copy(self) -> Volume3D:
        """Return an independent volume with identical configuration."""
        return Volume3D(
            self._cells,
            state_count=self.state_count,
            boundary=self.boundary,
            outside_state=self.outside_state,
            neighborhood=self.neighborhood,
            limits=self.limits,
        )

    def _require_inside(self, position: Sequence[int]) -> Position3D:
        z, y, x = _normalize_position(position)
        if not (0 <= z < self.depth and 0 <= y < self.rows and 0 <= x < self.columns):
            raise IndexError(f"3D position is outside volume shape {self.shape}.")
        return z, y, x

    def get_cell(self, position: Sequence[int]) -> int:
        """Return one in-bounds cell state."""
        return int(self._cells[self._require_inside(position)])

    def set_cell(self, position: Sequence[int], state: int) -> None:
        """Set one in-bounds cell after validating its state."""
        self._cells[self._require_inside(position)] = _validate_state(
            state,
            self.state_count,
        )

    def fill(self, state: int = 0) -> None:
        """Set every cell to one valid state."""
        self._cells.fill(_validate_state(state, self.state_count))

    def replace_cells(
        self,
        cells: np.ndarray | Sequence[Sequence[Sequence[int]]],
    ) -> None:
        """Replace all cells without allowing an implicit shape change."""
        replacement = self._validated_cells(cells)
        if replacement.shape != self.shape:
            raise ValueError(
                f"Replacement shape {replacement.shape} does not match {self.shape}."
            )
        self._cells = replacement

    @staticmethod
    def _axis_dimension(axis: str) -> int:
        try:
            return {AXIS_Z: 0, AXIS_Y: 1, AXIS_X: 2}[axis]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Slice axis must be one of {SLICE_AXES}.") from exc

    def slice_shape(self, axis: str) -> tuple[int, int]:
        """Return the renderer-facing row/column shape for one slice axis."""
        dimension = self._axis_dimension(axis)
        return tuple(
            length for index, length in enumerate(self.shape) if index != dimension
        )

    def _slice_view(self, axis: str, index: int) -> NDArray[np.uint8]:
        dimension = self._axis_dimension(axis)
        if isinstance(index, bool) or not isinstance(index, Integral):
            raise TypeError("slice index must be an integer.")
        normalized_index = int(index)
        if not 0 <= normalized_index < self.shape[dimension]:
            raise IndexError(
                f"Slice index {normalized_index} is outside axis {axis!r}."
            )
        if axis == AXIS_Z:
            return self._cells[normalized_index, :, :]
        if axis == AXIS_Y:
            return self._cells[:, normalized_index, :]
        return self._cells[:, :, normalized_index]

    def extract_slice(
        self,
        axis: str,
        index: int,
        *,
        copy: bool = True,
    ) -> NDArray[np.uint8]:
        """Extract a 2D state plane suitable for ``StateGridRasterizer``.

        A Z slice is ``(rows, columns)``, a Y slice is ``(depth, columns)``,
        and an X slice is ``(depth, rows)``. Zero-copy slices are read-only.
        """
        plane = self._slice_view(axis, index)
        if copy:
            return plane.copy()
        view = plane.view()
        view.flags.writeable = False
        return view

    def write_slice(
        self,
        axis: str,
        index: int,
        values: np.ndarray | Sequence[Sequence[int]],
    ) -> None:
        """Replace one axis-aligned plane after shape and state validation."""
        target = self._slice_view(axis, index)
        try:
            plane = np.asarray(values)
        except (TypeError, ValueError) as exc:
            raise ValueError("Slice values must form a rectangular 2D array.") from exc
        if plane.ndim != 2 or plane.shape != target.shape:
            raise ValueError(
                f"Slice shape {plane.shape} does not match expected {target.shape}."
            )
        if plane.dtype.kind not in "biu":
            raise TypeError("Slice states must be integers.")
        if np.any(plane < 0) or np.any(plane >= self.state_count):
            raise ValueError(
                f"Slice states must be between 0 and {self.state_count - 1}."
            )
        target[:] = plane.astype(np.uint8, copy=False)

    def sample(
        self,
        position: Sequence[int],
        *,
        boundary: str | None = None,
        outside_state: int | None = None,
    ) -> int:
        """Sample an in- or out-of-bounds position under a boundary policy."""
        z, y, x = _normalize_position(position)
        mode = self.boundary if boundary is None else _validate_boundary(boundary)
        outside = (
            self.outside_state
            if outside_state is None
            else _validate_state(outside_state, self.state_count, "outside_state")
        )
        if 0 <= z < self.depth and 0 <= y < self.rows and 0 <= x < self.columns:
            return int(self._cells[z, y, x])
        if mode == BOUNDARY_WRAP:
            return int(
                self._cells[z % self.depth, y % self.rows, x % self.columns]
            )
        if mode == BOUNDARY_REFLECT:
            return int(
                self._cells[
                    _reflected_index(z, self.depth),
                    _reflected_index(y, self.rows),
                    _reflected_index(x, self.columns),
                ]
            )
        return outside

    def neighbor_values(
        self,
        position: Sequence[int],
        *,
        neighborhood: Neighborhood3D | None = None,
        boundary: str | None = None,
        outside_state: int | None = None,
    ) -> StateVolume:
        """Return neighboring states in the definition's deterministic order."""
        z, y, x = self._require_inside(position)
        definition = (
            self.neighborhood
            if neighborhood is None
            else self._validate_neighborhood(neighborhood)
        )
        return np.fromiter(
            (
                self.sample(
                    (z + dz, y + dy, x + dx),
                    boundary=boundary,
                    outside_state=outside_state,
                )
                for dz, dy, dx in definition.offsets
            ),
            dtype=np.uint8,
            count=definition.size,
        )

    def _normalized_active_states(
        self,
        active_states: Iterable[int] | None,
    ) -> tuple[int, ...]:
        values = (
            tuple(range(1, self.state_count))
            if active_states is None
            else tuple(active_states)
        )
        return tuple(
            sorted(
                {
                    _validate_state(value, self.state_count, "active state")
                    for value in values
                }
            )
        )

    def estimated_neighbor_working_bytes(
        self,
        neighborhood: Neighborhood3D | None = None,
    ) -> int:
        """Estimate peak temporary bytes for vectorized neighbor counting."""
        definition = (
            self.neighborhood
            if neighborhood is None
            else self._validate_neighborhood(neighborhood)
        )
        radius = definition.radius
        padded_cells = prod(length + 2 * radius for length in self.shape)
        count_bytes = self.cell_count * _count_dtype(definition.size).itemsize
        return 2 * self.cell_count + padded_cells + count_bytes

    def neighbor_counts(
        self,
        *,
        active_states: Iterable[int] | None = None,
        neighborhood: Neighborhood3D | None = None,
        boundary: str | None = None,
        outside_state: int | None = None,
    ) -> NDArray[np.unsignedinteger]:
        """Count selected neighboring states for every cell in one batch."""
        definition = (
            self.neighborhood
            if neighborhood is None
            else self._validate_neighborhood(neighborhood)
        )
        mode = self.boundary if boundary is None else _validate_boundary(boundary)
        outside = (
            self.outside_state
            if outside_state is None
            else _validate_state(outside_state, self.state_count, "outside_state")
        )
        selected_states = self._normalized_active_states(active_states)
        self.limits.validate_working_bytes(
            self.estimated_neighbor_working_bytes(definition)
        )

        active = np.zeros(self.shape, dtype=np.bool_)
        for state in selected_states:
            np.logical_or(active, self._cells == state, out=active)

        radius = definition.radius
        padding = ((radius, radius),) * 3
        if mode == BOUNDARY_WRAP:
            padded = np.pad(active, padding, mode="wrap")
        elif mode == BOUNDARY_REFLECT:
            padded = np.pad(active, padding, mode="reflect")
        else:
            padded = np.pad(
                active,
                padding,
                mode="constant",
                constant_values=outside in selected_states,
            )

        counts = np.zeros(self.shape, dtype=_count_dtype(definition.size))
        for dz, dy, dx in definition.offsets:
            counts += padded[
                radius + dz : radius + dz + self.depth,
                radius + dy : radius + dy + self.rows,
                radius + dx : radius + dx + self.columns,
            ]
        return counts

    def memory_report(
        self,
        neighborhood: Neighborhood3D | None = None,
    ) -> dict[str, int | VolumeShape]:
        """Return allocation figures for UI diagnostics and future history caps."""
        return {
            "shape": self.shape,
            "cell_count": self.cell_count,
            "volume_bytes": self.nbytes,
            "neighbor_working_bytes": self.estimated_neighbor_working_bytes(
                neighborhood
            ),
            "max_volume_bytes": self.limits.max_volume_bytes,
            "max_working_bytes": self.limits.max_working_bytes,
        }
