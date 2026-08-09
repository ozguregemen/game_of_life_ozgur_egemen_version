"""Camera, voxel picking, and ModernGL rendering for 3D automata."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians, sin, tan
from numbers import Real
from typing import Any, Sequence, TypeAlias

import numpy as np
from numpy.typing import NDArray

from three_dimensional_ca import Position3D, Volume3D, VolumeShape

try:
    import moderngl
except ImportError:  # pragma: no cover - exercised by the runtime fallback
    moderngl = None  # type: ignore[assignment]


FloatVector: TypeAlias = NDArray[np.float32]
FloatMatrix: TypeAlias = NDArray[np.float32]
Viewport: TypeAlias = tuple[int, int, int, int]
RGBColor: TypeAlias = tuple[int, int, int]
FILTER_MODES = ("all", "clip", "layer")
FILTER_AXES = ("x", "y", "z")
COLOR_SCHEMES = (
    "state",
    "xyz",
    "layer",
    "radial",
    "density",
    "theme",
    "white",
)
LIGHTING_MODES = ("studio", "soft", "flat")
PROJECTION_ORTHOGRAPHIC = "orthographic"
PROJECTION_PERSPECTIVE = "perspective"
PROJECTION_MODES = (PROJECTION_ORTHOGRAPHIC, PROJECTION_PERSPECTIVE)
TRANSPARENT_SORT_DIRECTION_STEPS = 50.0
CAMERA_FACE_DIRECTIONS = {
    "front": (0.0, 0.0, 1.0),
    "back": (0.0, 0.0, -1.0),
    "right": (1.0, 0.0, 0.0),
    "left": (-1.0, 0.0, 0.0),
    "top": (0.0, 1.0, 0.0),
    "bottom": (0.0, -1.0, 0.0),
}
CAMERA_FACE_LABELS = {
    "front": "FRONT",
    "back": "BACK",
    "right": "RIGHT",
    "left": "LEFT",
    "top": "TOP",
    "bottom": "BOTTOM",
}
_ORIENTATION_FACE_VERTICES = {
    "front": ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),
    "back": ((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)),
    "right": ((1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)),
    "left": ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)),
    "top": ((-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)),
    "bottom": ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),
}


@dataclass(frozen=True)
class VoxelRenderSettings:
    """GPU appearance and view filters that do not mutate the simulation."""

    mode: str = "all"
    axis: str = "z"
    layer: int = 0
    keep_lower: bool = True
    opacity: float = 1.0
    color_scheme: str = "state"
    lighting: str = "studio"
    outline: float = 0.055
    voxel_scale: float = 0.80
    occlusion: float = 0.65

    def __post_init__(self) -> None:
        if self.mode not in FILTER_MODES:
            raise ValueError(f"Unknown 3D filter mode: {self.mode!r}.")
        if self.axis not in FILTER_AXES:
            raise ValueError(f"Unknown 3D filter axis: {self.axis!r}.")
        if isinstance(self.layer, bool) or not isinstance(self.layer, int):
            raise TypeError("3D filter layer must be an integer.")
        if not isinstance(self.keep_lower, bool):
            raise TypeError("3D clipping direction must be boolean.")
        if isinstance(self.opacity, bool) or not isinstance(self.opacity, Real):
            raise TypeError("Voxel opacity must be a number.")
        if not 0.05 <= self.opacity <= 1.0:
            raise ValueError("Voxel opacity must be between 0.05 and 1.0.")
        if self.color_scheme not in COLOR_SCHEMES:
            raise ValueError(f"Unknown 3D color scheme: {self.color_scheme!r}.")
        if self.lighting not in LIGHTING_MODES:
            raise ValueError(f"Unknown 3D lighting mode: {self.lighting!r}.")
        for name, value, minimum, maximum in (
            ("outline", self.outline, 0.0, 0.20),
            ("voxel_scale", self.voxel_scale, 0.50, 0.98),
            ("occlusion", self.occlusion, 0.0, 1.0),
        ):
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"Voxel {name} must be a number.")
            if not minimum <= value <= maximum:
                raise ValueError(
                    f"Voxel {name} must be between {minimum} and {maximum}."
                )


def _vector3(value: Any, label: str) -> FloatVector:
    try:
        vector = np.asarray(value, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain three finite numbers.") from exc
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{label} must contain three finite numbers.")
    return vector.copy()


def _normalized(value: FloatVector, label: str = "vector") -> FloatVector:
    length = float(np.linalg.norm(value))
    if length <= 1e-8:
        raise ValueError(f"{label} cannot have zero length.")
    return (value / length).astype(np.float32, copy=False)


def perspective_matrix(
    fov_y_degrees: float,
    aspect: float,
    near: float,
    far: float,
) -> FloatMatrix:
    """Return an OpenGL perspective matrix for column vectors."""
    if not 1.0 <= fov_y_degrees < 179.0:
        raise ValueError("Vertical field of view must be between 1 and 179 degrees.")
    if aspect <= 0.0 or near <= 0.0 or far <= near:
        raise ValueError("Perspective aspect and clipping distances are invalid.")
    focal = 1.0 / tan(radians(fov_y_degrees) / 2.0)
    matrix = np.zeros((4, 4), dtype=np.float32)
    matrix[0, 0] = focal / aspect
    matrix[1, 1] = focal
    matrix[2, 2] = (far + near) / (near - far)
    matrix[2, 3] = 2.0 * far * near / (near - far)
    matrix[3, 2] = -1.0
    return matrix


def orthographic_matrix(
    vertical_size: float,
    aspect: float,
    near: float,
    far: float,
) -> FloatMatrix:
    """Return a centered OpenGL orthographic matrix for column vectors."""

    if vertical_size <= 0.0 or aspect <= 0.0 or near <= 0.0 or far <= near:
        raise ValueError("Orthographic size, aspect, and clipping distances are invalid.")
    half_height = vertical_size / 2.0
    half_width = half_height * aspect
    matrix = np.identity(4, dtype=np.float32)
    matrix[0, 0] = 1.0 / half_width
    matrix[1, 1] = 1.0 / half_height
    matrix[2, 2] = -2.0 / (far - near)
    matrix[2, 3] = -(far + near) / (far - near)
    return matrix


def look_at_matrix(
    eye: FloatVector,
    target: FloatVector,
    up_hint: FloatVector | None = None,
) -> FloatMatrix:
    """Return a right-handed OpenGL view matrix for column vectors."""
    eye = _vector3(eye, "eye")
    target = _vector3(target, "target")
    forward = _normalized(target - eye, "view direction")
    up = _vector3((0.0, 1.0, 0.0) if up_hint is None else up_hint, "up")
    right = np.cross(forward, up)
    if float(np.linalg.norm(right)) <= 1e-6:
        up = _vector3((0.0, 0.0, 1.0), "fallback up")
        right = np.cross(forward, up)
    right = _normalized(right, "camera right")
    camera_up = _normalized(np.cross(right, forward), "camera up")

    matrix = np.identity(4, dtype=np.float32)
    matrix[0, :3] = right
    matrix[1, :3] = camera_up
    matrix[2, :3] = -forward
    matrix[0, 3] = -float(np.dot(right, eye))
    matrix[1, 3] = -float(np.dot(camera_up, eye))
    matrix[2, 3] = float(np.dot(forward, eye))
    return matrix


def matrix_bytes(matrix: FloatMatrix) -> bytes:
    """Encode a row-major NumPy matrix for OpenGL's column-major uniforms."""
    value = np.asarray(matrix, dtype=np.float32)
    if value.shape != (4, 4):
        raise ValueError("OpenGL matrix must be 4x4.")
    return value.T.copy(order="C").tobytes()


def transparent_order_key(
    camera: "OrbitCamera3D",
    revision: int,
) -> tuple[Any, ...]:
    """Return a stable view bucket for approximate transparent voxel sorting.

    Back-to-front order depends on view direction, not zoom distance or camera
    panning. Quantizing that direction avoids sorting and re-uploading a dense
    instance buffer for every single mouse-motion event.
    """

    direction = camera.forward
    bucket = tuple(
        round(float(value) * TRANSPARENT_SORT_DIRECTION_STEPS)
        / TRANSPARENT_SORT_DIRECTION_STEPS
        for value in direction
    )
    return "transparent", int(revision), bucket


@dataclass
class OrbitCamera3D:
    """Orbit camera whose target and parameters are session serializable."""

    target: FloatVector = field(
        default_factory=lambda: np.zeros(3, dtype=np.float32)
    )
    yaw: float = radians(45.0)
    pitch: float = radians(28.0)
    distance: float = 58.0
    fov_y: float = 45.0
    near: float = 0.1
    far: float = 500.0
    projection: str = PROJECTION_ORTHOGRAPHIC

    def __post_init__(self) -> None:
        self.target = _vector3(self.target, "camera target")
        for label in ("yaw", "pitch", "distance", "fov_y", "near", "far"):
            value = getattr(self, label)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"Camera {label} must be a number.")
            setattr(self, label, float(value))
        self.pitch = max(radians(-90.0), min(radians(90.0), self.pitch))
        self.distance = max(1.0, self.distance)
        if not 1.0 <= self.fov_y < 179.0:
            raise ValueError("Camera field of view must be between 1 and 179 degrees.")
        if self.near <= 0.0 or self.far <= self.near:
            raise ValueError("Camera clipping distances are invalid.")
        if self.projection not in PROJECTION_MODES:
            raise ValueError(f"Unknown camera projection: {self.projection!r}.")

    @property
    def eye(self) -> FloatVector:
        horizontal = self.distance * cos(self.pitch)
        return self.target + np.asarray(
            (
                horizontal * cos(self.yaw),
                self.distance * sin(self.pitch),
                horizontal * sin(self.yaw),
            ),
            dtype=np.float32,
        )

    @property
    def forward(self) -> FloatVector:
        return _normalized(self.target - self.eye, "camera forward")

    @property
    def right(self) -> FloatVector:
        right = np.cross(
            self.forward,
            np.asarray((0.0, 1.0, 0.0), dtype=np.float32),
        )
        if float(np.linalg.norm(right)) <= 1e-6:
            right = np.cross(
                self.forward,
                np.asarray((0.0, 0.0, 1.0), dtype=np.float32),
            )
        return _normalized(right, "camera right")

    @property
    def up(self) -> FloatVector:
        return _normalized(np.cross(self.right, self.forward), "camera up")

    def reset_for_shape(self, shape: VolumeShape) -> None:
        """Center the volume and select a distance that shows its full diagonal."""
        diagonal = float(np.linalg.norm(np.asarray(shape, dtype=np.float32)))
        self.target[:] = 0.0
        self.yaw = radians(45.0)
        self.pitch = radians(28.0)
        self.distance = max(8.0, diagonal * 1.35)
        self.far = max(500.0, self.distance + diagonal * 4.0)

    def orbit(self, delta_x: float, delta_y: float) -> None:
        self.yaw -= float(delta_x) * 0.008
        self.pitch -= float(delta_y) * 0.008
        self.pitch = max(radians(-90.0), min(radians(90.0), self.pitch))

    def snap_to_face(self, face: str) -> None:
        """Align the selected world-space volume face toward the viewer."""

        if face not in CAMERA_FACE_DIRECTIONS:
            raise ValueError(f"Unknown camera face: {face!r}.")
        if face == "front":
            self.yaw, self.pitch = radians(90.0), 0.0
        elif face == "back":
            self.yaw, self.pitch = radians(-90.0), 0.0
        elif face == "right":
            self.yaw, self.pitch = 0.0, 0.0
        elif face == "left":
            self.yaw, self.pitch = radians(180.0), 0.0
        elif face == "top":
            self.yaw, self.pitch = 0.0, radians(90.0)
        else:
            self.yaw, self.pitch = 0.0, radians(-90.0)

    def pan(self, delta_x: float, delta_y: float, viewport_height: int) -> None:
        scale = (
            2.0
            * self.distance
            * tan(radians(self.fov_y) / 2.0)
            / max(1, viewport_height)
        )
        self.target += (
            -float(delta_x) * self.right + float(delta_y) * self.up
        ) * scale

    def zoom(self, factor: float) -> None:
        if factor <= 0.0:
            raise ValueError("Camera zoom factor must be positive.")
        self.distance = max(2.0, min(self.far * 0.75, self.distance / factor))

    def view_matrix(self) -> FloatMatrix:
        return look_at_matrix(self.eye, self.target)

    def projection_matrix(self, aspect: float) -> FloatMatrix:
        if self.projection == PROJECTION_ORTHOGRAPHIC:
            vertical_size = 2.0 * self.distance * tan(radians(self.fov_y) / 2.0)
            return orthographic_matrix(
                vertical_size,
                aspect,
                self.near,
                self.far,
            )
        return perspective_matrix(self.fov_y, aspect, self.near, self.far)

    def view_projection(self, aspect: float) -> FloatMatrix:
        return self.projection_matrix(aspect) @ self.view_matrix()

    def screen_ray(
        self,
        position: tuple[int, int],
        viewport: Viewport,
    ) -> tuple[FloatVector, FloatVector]:
        """Return a world-space ray through one Pygame screen coordinate."""
        viewport_x, viewport_y, width, height = viewport
        if width < 1 or height < 1:
            raise ValueError("Camera viewport must be non-empty.")
        normalized_x = 2.0 * (position[0] - viewport_x) / width - 1.0
        normalized_y = 1.0 - 2.0 * (position[1] - viewport_y) / height
        inverse = np.linalg.inv(self.view_projection(width / height))
        near_clip = np.asarray((normalized_x, normalized_y, -1.0, 1.0))
        far_clip = np.asarray((normalized_x, normalized_y, 1.0, 1.0))
        near_world = inverse @ near_clip
        far_world = inverse @ far_clip
        near_world /= near_world[3]
        far_world /= far_world[3]
        direction = _normalized(
            (far_world[:3] - near_world[:3]).astype(np.float32),
            "screen ray",
        )
        origin = (
            near_world[:3].astype(np.float32, copy=True)
            if self.projection == PROJECTION_ORTHOGRAPHIC
            else self.eye.copy()
        )
        return origin, direction

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": [float(value) for value in self.target],
            "yaw": self.yaw,
            "pitch": self.pitch,
            "distance": self.distance,
            "fov_y": self.fov_y,
            "projection": self.projection,
        }

    @classmethod
    def from_mapping(cls, value: Any) -> OrbitCamera3D:
        if not isinstance(value, dict):
            raise TypeError("3D camera state must be an object.")
        return cls(
            target=value["target"],
            yaw=value["yaw"],
            pitch=value["pitch"],
            distance=value["distance"],
            fov_y=value.get("fov_y", 45.0),
            projection=value.get("projection", PROJECTION_ORTHOGRAPHIC),
        )


@dataclass(frozen=True)
class OrientationCubeFace:
    """One visible clickable face in the viewport orientation cube."""

    key: str
    label: str
    polygon: tuple[tuple[int, int], ...]
    depth: float


def orientation_cube_faces(
    camera: OrbitCamera3D,
    rect: tuple[int, int, int, int],
) -> tuple[OrientationCubeFace, ...]:
    """Project visible orientation-cube faces from farthest to nearest."""

    x, y, width, height = rect
    if width < 8 or height < 8:
        return ()
    center = np.asarray((x + width / 2.0, y + height / 2.0))
    scale = min(width, height) * 0.27
    view_rotation = camera.view_matrix()[:3, :3]
    eye_direction = _normalized(camera.eye - camera.target, "camera eye direction")
    faces: list[OrientationCubeFace] = []
    for key, vertices in _ORIENTATION_FACE_VERTICES.items():
        normal = np.asarray(CAMERA_FACE_DIRECTIONS[key], dtype=np.float32)
        if float(np.dot(normal, eye_direction)) <= 1e-5:
            continue
        transformed = (view_rotation @ np.asarray(vertices, dtype=np.float32).T).T
        polygon = tuple(
            (
                round(center[0] + vertex[0] * scale),
                round(center[1] - vertex[1] * scale),
            )
            for vertex in transformed
        )
        faces.append(
            OrientationCubeFace(
                key=key,
                label=CAMERA_FACE_LABELS[key],
                polygon=polygon,
                depth=float(np.mean(transformed[:, 2])),
            )
        )
    return tuple(sorted(faces, key=lambda face: face.depth))


def _point_in_convex_polygon(
    point: tuple[int, int],
    polygon: Sequence[tuple[int, int]],
) -> bool:
    signs: list[bool] = []
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        cross = (end[0] - start[0]) * (point[1] - start[1]) - (
            end[1] - start[1]
        ) * (point[0] - start[0])
        if cross:
            signs.append(cross > 0)
    return not signs or all(sign == signs[0] for sign in signs)


def orientation_cube_face_at(
    camera: OrbitCamera3D,
    rect: tuple[int, int, int, int],
    point: tuple[int, int],
) -> str | None:
    """Return the nearest visible orientation face under a screen point."""

    for face in reversed(orientation_cube_faces(camera, rect)):
        if _point_in_convex_polygon(point, face.polygon):
            return face.key
    return None


def volume_position_to_world(
    position: Position3D,
    shape: VolumeShape,
) -> FloatVector:
    """Map canonical ``(z, y, x)`` coordinates to centered world space."""
    z, y, x = position
    depth, rows, columns = shape
    return np.asarray(
        (
            x - (columns - 1) / 2.0,
            (rows - 1) / 2.0 - y,
            z - (depth - 1) / 2.0,
        ),
        dtype=np.float32,
    )


def voxel_instance_data(volume: Volume3D) -> NDArray[np.float32]:
    """Return ``x, y, z, state`` rows for every non-empty voxel."""
    active = np.argwhere(volume.cells != 0)
    if not len(active):
        return np.empty((0, 4), dtype=np.float32)
    depth, rows, columns = volume.shape
    data = np.empty((len(active), 4), dtype=np.float32)
    data[:, 0] = active[:, 2] - (columns - 1) / 2.0
    data[:, 1] = (rows - 1) / 2.0 - active[:, 1]
    data[:, 2] = active[:, 0] - (depth - 1) / 2.0
    data[:, 3] = volume.cells[tuple(active.T)]
    return data


def voxel_render_instance_data(volume: Volume3D) -> NDArray[np.float32]:
    """Return position/state rows plus normalized local occupancy for shading."""
    base = voxel_instance_data(volume)
    if not len(base):
        return np.empty((0, 5), dtype=np.float32)
    occupied = np.argwhere(volume.cells != 0)
    occupied_states = tuple(range(1, volume.state_count))
    counts = volume.neighbor_counts(active_states=occupied_states)
    data = np.empty((len(base), 5), dtype=np.float32)
    data[:, :4] = base
    data[:, 4] = (
        counts[tuple(occupied.T)].astype(np.float32) + 1.0
    ) / float(volume.neighborhood.size + 1)
    return data


@dataclass(frozen=True)
class VoxelPick:
    """First occupied voxel hit by a ray and its preceding empty neighbor."""

    hit: Position3D
    adjacent: Position3D | None
    distance: float


def voxel_is_visible(
    position: Position3D,
    settings: VoxelRenderSettings,
) -> bool:
    """Return whether one canonical voxel passes the active layer filter."""
    if settings.mode == "all":
        return True
    coordinates = {"z": position[0], "y": position[1], "x": position[2]}
    coordinate = coordinates[settings.axis]
    if settings.mode == "layer":
        return coordinate == settings.layer
    if settings.keep_lower:
        return coordinate <= settings.layer
    return coordinate >= settings.layer


def pick_voxel(
    volume: Volume3D,
    ray_origin: Any,
    ray_direction: Any,
    settings: VoxelRenderSettings | None = None,
) -> VoxelPick | None:
    """Traverse a dense volume with an exact 3D DDA ray test."""
    origin_world = _vector3(ray_origin, "ray origin")
    direction_world = _normalized(_vector3(ray_direction, "ray direction"))
    depth, rows, columns = volume.shape
    origin = np.asarray(
        (
            origin_world[0] + columns / 2.0,
            rows / 2.0 - origin_world[1],
            origin_world[2] + depth / 2.0,
        ),
        dtype=np.float64,
    )
    direction = np.asarray(
        (direction_world[0], -direction_world[1], direction_world[2]),
        dtype=np.float64,
    )
    limits = np.asarray((columns, rows, depth), dtype=np.int64)

    entry = 0.0
    exit_distance = float("inf")
    for axis in range(3):
        if abs(direction[axis]) <= 1e-12:
            if origin[axis] < 0.0 or origin[axis] >= limits[axis]:
                return None
            continue
        first = (0.0 - origin[axis]) / direction[axis]
        second = (limits[axis] - origin[axis]) / direction[axis]
        near_axis, far_axis = sorted((first, second))
        entry = max(entry, near_axis)
        exit_distance = min(exit_distance, far_axis)
        if entry > exit_distance:
            return None
    if exit_distance < 0.0:
        return None

    entry = max(0.0, entry)
    point = origin + direction * (entry + 1e-7)
    point = np.minimum(np.maximum(point, 0.0), limits - 1e-7)
    voxel = np.floor(point).astype(np.int64)
    step = np.sign(direction).astype(np.int64)
    delta = np.full(3, float("inf"), dtype=np.float64)
    boundary_time = np.full(3, float("inf"), dtype=np.float64)
    for axis in range(3):
        if step[axis] == 0:
            continue
        delta[axis] = abs(1.0 / direction[axis])
        boundary = voxel[axis] + (1 if step[axis] > 0 else 0)
        boundary_time[axis] = entry + (boundary - point[axis]) / direction[axis]

    previous: Position3D | None = None
    while np.all(voxel >= 0) and np.all(voxel < limits):
        x, y, z = (int(value) for value in voxel)
        position = (z, y, x)
        cell_state = volume.get_cell(position)
        if cell_state != 0 and (
            settings is None or voxel_is_visible(position, settings)
        ):
            return VoxelPick(position, previous, entry)
        previous = position if cell_state == 0 else None
        axis = int(np.argmin(boundary_time))
        entry = float(boundary_time[axis])
        if entry > exit_distance + 1e-7:
            break
        voxel[axis] += step[axis]
        boundary_time[axis] += delta[axis]
    return None


def _cube_vertex_data() -> NDArray[np.float32]:
    faces = (
        ((0.0, 0.0, 1.0), ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))),
        ((0.0, 0.0, -1.0), ((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1))),
        ((1.0, 0.0, 0.0), ((1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1))),
        ((-1.0, 0.0, 0.0), ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1))),
        ((0.0, 1.0, 0.0), ((-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1))),
        ((0.0, -1.0, 0.0), ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1))),
    )
    rows: list[tuple[float, ...]] = []
    face_uv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    for normal, corners in faces:
        for index in (0, 1, 2, 0, 2, 3):
            position = tuple(float(value) * 0.5 for value in corners[index])
            rows.append((*position, *normal, *face_uv[index]))
    return np.asarray(rows, dtype=np.float32)


def _box_vertex_data(shape: VolumeShape) -> NDArray[np.float32]:
    depth, rows, columns = shape
    x0, x1 = -columns / 2.0, columns / 2.0
    y0, y1 = -rows / 2.0, rows / 2.0
    z0, z1 = -depth / 2.0, depth / 2.0
    corners = np.asarray(
        (
            (x0, y0, z0),
            (x1, y0, z0),
            (x1, y1, z0),
            (x0, y1, z0),
            (x0, y0, z1),
            (x1, y0, z1),
            (x1, y1, z1),
            (x0, y1, z1),
        ),
        dtype=np.float32,
    )
    edges = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )
    return np.asarray([corners[index] for edge in edges for index in edge], dtype=np.float32)


def _filter_plane_vertex_data(
    shape: VolumeShape,
    settings: VoxelRenderSettings,
) -> NDArray[np.float32]:
    """Return four line segments outlining the selected canonical layer."""
    depth, rows, columns = shape
    x0, x1 = -columns / 2.0, columns / 2.0
    y0, y1 = -rows / 2.0, rows / 2.0
    z0, z1 = -depth / 2.0, depth / 2.0
    if settings.axis == "x":
        x = settings.layer - (columns - 1) / 2.0
        corners = ((x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1))
    elif settings.axis == "y":
        y = (rows - 1) / 2.0 - settings.layer
        corners = ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))
    else:
        z = settings.layer - (depth - 1) / 2.0
        corners = ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))
    edges = ((0, 1), (1, 2), (2, 3), (3, 0))
    return np.asarray([corners[index] for edge in edges for index in edge], dtype=np.float32)


class ModernGLVoxelRenderer:
    """Draw non-empty volume cells as instanced, depth-tested cubes."""

    def __init__(self, context: Any) -> None:
        if moderngl is None:
            raise RuntimeError("ModernGL is required for the 3D renderer.")
        self.ctx = context
        self.program = self.ctx.program(
            vertex_shader="""
                #version 330
                uniform mat4 mvp;
                uniform vec3 volume_shape;
                uniform int filter_axis;
                uniform float voxel_scale;
                in vec3 in_position;
                in vec3 in_normal;
                in vec2 in_face_uv;
                in vec3 in_offset;
                in float in_state;
                in float in_density;
                out vec3 v_normal;
                out vec2 v_face_uv;
                out vec3 v_world_position;
                flat out vec3 v_offset;
                flat out float v_state;
                flat out float v_density;
                flat out float v_layer;
                void main() {
                    v_normal = in_normal;
                    v_face_uv = in_face_uv;
                    v_offset = in_offset;
                    v_state = in_state;
                    v_density = in_density;
                    if (filter_axis == 0) {
                        v_layer = in_offset.x + (volume_shape.x - 1.0) * 0.5;
                    } else if (filter_axis == 1) {
                        v_layer = (volume_shape.y - 1.0) * 0.5 - in_offset.y;
                    } else {
                        v_layer = in_offset.z + (volume_shape.z - 1.0) * 0.5;
                    }
                    v_world_position = in_position * voxel_scale + in_offset;
                    gl_Position = mvp * vec4(v_world_position, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                uniform vec3 alive_color;
                uniform vec3 decay_color;
                uniform vec3 border_color;
                uniform vec3 camera_position;
                uniform vec3 volume_shape;
                uniform int state_count;
                uniform int color_scheme;
                uniform int lighting_mode;
                uniform vec3 selected_world;
                uniform int selection_enabled;
                uniform int filter_mode;
                uniform int filter_layer;
                uniform int keep_lower;
                uniform float voxel_opacity;
                uniform float outline_thickness;
                uniform float occlusion_strength;
                in vec3 v_normal;
                in vec2 v_face_uv;
                in vec3 v_world_position;
                flat in vec3 v_offset;
                flat in float v_state;
                flat in float v_density;
                flat in float v_layer;
                out vec4 frag_color;

                vec3 spectrum(float amount) {
                    float t = clamp(amount, 0.0, 1.0);
                    vec3 blue = vec3(0.08, 0.36, 1.0);
                    vec3 cyan = vec3(0.08, 0.95, 0.82);
                    vec3 yellow = vec3(1.0, 0.86, 0.10);
                    vec3 magenta = vec3(1.0, 0.08, 0.42);
                    if (t < 0.33) return mix(blue, cyan, t / 0.33);
                    if (t < 0.66) return mix(cyan, yellow, (t - 0.33) / 0.33);
                    return mix(yellow, magenta, (t - 0.66) / 0.34);
                }

                vec3 voxel_color() {
                    vec3 normalized_position = clamp(
                        (v_offset + (volume_shape - vec3(1.0)) * 0.5) /
                        max(volume_shape - vec3(1.0), vec3(1.0)),
                        vec3(0.0),
                        vec3(1.0)
                    );
                    if (color_scheme == 1) return normalized_position;
                    if (color_scheme == 2) return spectrum(normalized_position.z);
                    if (color_scheme == 3) {
                        vec3 centered = v_offset / max(volume_shape * 0.5, vec3(1.0));
                        return spectrum(length(centered) / 1.7320508);
                    }
                    if (color_scheme == 4) return spectrum(v_density);
                    if (color_scheme == 5) return alive_color;
                    if (color_scheme == 6) return vec3(0.96);

                    vec3 base = vec3(1.0, 0.88, 0.08);
                    if (v_state > 1.5 && state_count > 2) {
                        float decay = clamp(
                            (v_state - 1.0) / float(state_count - 2),
                            0.0,
                            1.0
                        );
                        base = mix(base, decay_color, decay);
                    }
                    return base;
                }

                void main() {
                    if (filter_mode == 1) {
                        if (keep_lower == 1 && v_layer > float(filter_layer) + 0.1) discard;
                        if (keep_lower == 0 && v_layer < float(filter_layer) - 0.1) discard;
                    } else if (filter_mode == 2 && abs(v_layer - float(filter_layer)) > 0.1) {
                        discard;
                    }
                    vec3 base = voxel_color();
                    if (selection_enabled == 1 && distance(v_offset, selected_world) < 0.1) {
                        base = vec3(1.0, 0.78, 0.18);
                    }

                    float edge_distance = min(
                        min(v_face_uv.x, 1.0 - v_face_uv.x),
                        min(v_face_uv.y, 1.0 - v_face_uv.y)
                    );
                    if (outline_thickness > 0.0) {
                        float feather = max(fwidth(edge_distance) * 1.5, 0.001);
                        float edge = 1.0 - smoothstep(
                            outline_thickness,
                            outline_thickness + feather,
                            edge_distance
                        );
                        base = mix(base, border_color, edge);
                    }

                    vec3 normal = normalize(v_normal);
                    vec3 key_direction = normalize(vec3(0.48, 0.82, 0.32));
                    vec3 fill_direction = normalize(vec3(-0.62, 0.28, -0.72));
                    float key = max(dot(normal, key_direction), 0.0);
                    float fill = max(dot(normal, fill_direction), 0.0);
                    vec3 lit = base;
                    if (lighting_mode == 0) {
                        vec3 view_direction = normalize(camera_position - v_world_position);
                        vec3 half_direction = normalize(key_direction + view_direction);
                        float specular = pow(max(dot(normal, half_direction), 0.0), 32.0);
                        vec3 light = vec3(0.20)
                            + key * vec3(0.72, 0.66, 0.54)
                            + fill * vec3(0.16, 0.22, 0.34);
                        lit = base * light + specular * vec3(0.22, 0.20, 0.16);
                    } else if (lighting_mode == 1) {
                        lit = base * (0.48 + 0.42 * key + 0.10 * fill);
                    }
                    float occlusion = 1.0
                        - occlusion_strength * clamp(v_density, 0.0, 1.0) * 0.68;
                    frag_color = vec4(clamp(lit * occlusion, 0.0, 1.0), voxel_opacity);
                }
            """,
        )
        cube = _cube_vertex_data()
        self.cube_buffer = self.ctx.buffer(cube.tobytes())
        self.instance_buffer = self.ctx.buffer(reserve=20, dynamic=True)
        self.vao = self.ctx.vertex_array(
            self.program,
            (
                (
                    self.cube_buffer,
                    "3f 3f 2f",
                    "in_position",
                    "in_normal",
                    "in_face_uv",
                ),
                (
                    self.instance_buffer,
                    "3f 1f 1f /i",
                    "in_offset",
                    "in_state",
                    "in_density",
                ),
            ),
        )
        self.line_program = self.ctx.program(
            vertex_shader="""
                #version 330
                uniform mat4 mvp;
                in vec3 in_position;
                void main() { gl_Position = mvp * vec4(in_position, 1.0); }
            """,
            fragment_shader="""
                #version 330
                uniform vec3 line_color;
                out vec4 frag_color;
                void main() { frag_color = vec4(line_color, 1.0); }
            """,
        )
        self.box_buffer = self.ctx.buffer(reserve=24 * 3 * 4, dynamic=True)
        self.box_vao = self.ctx.vertex_array(
            self.line_program,
            ((self.box_buffer, "3f", "in_position"),),
        )
        self.filter_buffer = self.ctx.buffer(reserve=8 * 3 * 4, dynamic=True)
        self.filter_vao = self.ctx.vertex_array(
            self.line_program,
            ((self.filter_buffer, "3f", "in_position"),),
        )
        self.instance_count = 0
        self._instance_data = np.empty((0, 5), dtype=np.float32)
        self._buffer_order_key: tuple[Any, ...] | None = None
        self._revision: int | None = None
        self._shape: VolumeShape | None = None

    def update_volume(self, volume: Volume3D, revision: int) -> None:
        if self._revision == revision and self._shape == volume.shape:
            return
        data = voxel_render_instance_data(volume)
        byte_count = max(20, data.nbytes)
        if self.instance_buffer.size < byte_count:
            self.instance_buffer.orphan(byte_count)
        if data.nbytes:
            self.instance_buffer.write(data.tobytes())
        self._instance_data = data
        self._buffer_order_key = ("native", revision)
        self.instance_count = len(data)
        self._revision = revision
        if self._shape != volume.shape:
            box = _box_vertex_data(volume.shape)
            self.box_buffer.write(box.tobytes())
            self._shape = volume.shape

    def _order_transparent_instances(
        self,
        camera: OrbitCamera3D,
        revision: int,
    ) -> None:
        if not len(self._instance_data):
            return
        order_key = transparent_order_key(camera, revision)
        if self._buffer_order_key == order_key:
            return
        depths = self._instance_data[:, :3] @ camera.forward
        ordered = self._instance_data[np.argsort(depths)[::-1]]
        self.instance_buffer.write(ordered.tobytes())
        self._buffer_order_key = order_key

    def _restore_native_instance_order(self, revision: int) -> None:
        order_key = ("native", revision)
        if self._buffer_order_key == order_key:
            return
        if self._instance_data.nbytes:
            self.instance_buffer.write(self._instance_data.tobytes())
        self._buffer_order_key = order_key

    def render(
        self,
        volume: Volume3D,
        camera: OrbitCamera3D,
        viewport: Viewport,
        window_height: int,
        *,
        revision: int,
        alive_color: RGBColor,
        accent_color: RGBColor,
        selected: Position3D | None = None,
        settings: VoxelRenderSettings | None = None,
    ) -> None:
        settings = VoxelRenderSettings() if settings is None else settings
        self.update_volume(volume, revision)
        x, y, width, height = viewport
        if width < 1 or height < 1:
            return
        self.ctx.viewport = (x, window_height - y - height, width, height)
        self.ctx.scissor = self.ctx.viewport
        matrix = camera.view_projection(width / height)
        self.program["mvp"].write(matrix_bytes(matrix))
        self.program["alive_color"].value = tuple(channel / 255.0 for channel in alive_color)
        self.program["decay_color"].value = (1.0, 0.16, 0.04)
        self.program["border_color"].value = (0.012, 0.016, 0.022)
        self.program["camera_position"].value = tuple(
            float(value) for value in camera.eye
        )
        self.program["state_count"].value = volume.state_count
        self.program["color_scheme"].value = COLOR_SCHEMES.index(
            settings.color_scheme
        )
        self.program["lighting_mode"].value = LIGHTING_MODES.index(
            settings.lighting
        )
        self.program["voxel_scale"].value = settings.voxel_scale
        self.program["outline_thickness"].value = settings.outline
        self.program["occlusion_strength"].value = settings.occlusion
        axis_index = FILTER_AXES.index(settings.axis)
        axis_length = (volume.shape[2], volume.shape[1], volume.shape[0])[axis_index]
        layer = max(0, min(axis_length - 1, settings.layer))
        self.program["volume_shape"].value = (
            float(volume.shape[2]),
            float(volume.shape[1]),
            float(volume.shape[0]),
        )
        self.program["filter_axis"].value = axis_index
        self.program["filter_mode"].value = FILTER_MODES.index(settings.mode)
        self.program["filter_layer"].value = layer
        self.program["keep_lower"].value = int(settings.keep_lower)
        self.program["voxel_opacity"].value = settings.opacity
        if selected is None:
            self.program["selection_enabled"].value = 0
            self.program["selected_world"].value = (0.0, 0.0, 0.0)
        else:
            self.program["selection_enabled"].value = 1
            self.program["selected_world"].value = tuple(
                float(value) for value in volume_position_to_world(selected, volume.shape)
            )
        transparent = settings.opacity < 0.999
        if transparent:
            self._order_transparent_instances(camera, revision)
            self.ctx.enable_only(
                moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND
            )
            self.ctx.blend_func = (
                moderngl.SRC_ALPHA,
                moderngl.ONE_MINUS_SRC_ALPHA,
            )
            self.ctx.depth_mask = False
        else:
            self._restore_native_instance_order(revision)
            self.ctx.enable_only(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
            self.ctx.depth_mask = True
        if self.instance_count:
            self.vao.render(instances=self.instance_count)
        self.ctx.depth_mask = True

        self.line_program["mvp"].write(matrix_bytes(matrix))
        self.line_program["line_color"].value = tuple(
            channel / 255.0 for channel in accent_color
        )
        self.ctx.enable_only(moderngl.DEPTH_TEST)
        self.box_vao.render(mode=moderngl.LINES, vertices=24)
        if settings.mode != "all":
            plane_settings = VoxelRenderSettings(
                mode=settings.mode,
                axis=settings.axis,
                layer=layer,
                keep_lower=settings.keep_lower,
                opacity=settings.opacity,
            )
            self.filter_buffer.write(
                _filter_plane_vertex_data(volume.shape, plane_settings).tobytes()
            )
            self.ctx.disable(moderngl.DEPTH_TEST)
            self.filter_vao.render(mode=moderngl.LINES, vertices=8)
        self.ctx.scissor = None

    def release(self) -> None:
        for resource in (
            self.filter_vao,
            self.filter_buffer,
            self.box_vao,
            self.box_buffer,
            self.line_program,
            self.vao,
            self.instance_buffer,
            self.cube_buffer,
            self.program,
        ):
            resource.release()
