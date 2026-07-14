"""Checkpoint and delta based history for cellular-automata workspaces."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypeAlias


PathPart: TypeAlias = str | int
StatePath: TypeAlias = tuple[PathPart, ...]
OperationKind: TypeAlias = Literal["set", "append", "truncate"]


@dataclass(frozen=True)
class DeltaOperation:
    """One mutation needed to transform a history state into the next state."""

    kind: OperationKind
    path: StatePath
    value: Any


@dataclass
class TimelineFrame:
    """A generation-labelled checkpoint or a delta from the previous frame."""

    generation: int
    checkpoint: Any | None = None
    delta: list[DeltaOperation] | None = None

    @property
    def is_checkpoint(self) -> bool:
        return self.checkpoint is not None


@dataclass(frozen=True)
class TimelineStatus:
    """Read-only timeline information used by workspaces and the UI."""

    cursor: int
    frame_count: int
    generation: int
    generations: tuple[int, ...]
    checkpoints: tuple[int, ...]
    can_step_back: bool
    can_step_forward: bool
    checkpoint_count: int
    delta_frame_count: int
    delta_operation_count: int


def diff_states(previous: Any, current: Any) -> list[DeltaOperation]:
    """Return compact operations that transform ``previous`` into ``current``."""

    operations: list[DeltaOperation] = []
    _diff_value(previous, current, (), operations)
    return operations


def _diff_value(
    previous: Any,
    current: Any,
    path: StatePath,
    operations: list[DeltaOperation],
) -> None:
    if type(previous) is not type(current):
        operations.append(DeltaOperation("set", path, deepcopy(current)))
        return

    if isinstance(previous, dict):
        if previous.keys() != current.keys():
            operations.append(DeltaOperation("set", path, deepcopy(current)))
            return
        for key in previous:
            _diff_value(previous[key], current[key], path + (key,), operations)
        return

    if isinstance(previous, list):
        shared_length = min(len(previous), len(current))
        for index in range(shared_length):
            _diff_value(
                previous[index],
                current[index],
                path + (index,),
                operations,
            )
        if len(current) < len(previous):
            operations.append(DeltaOperation("truncate", path, len(current)))
        elif len(current) > len(previous):
            for value in current[len(previous) :]:
                operations.append(DeltaOperation("append", path, deepcopy(value)))
        return

    if previous != current:
        operations.append(DeltaOperation("set", path, deepcopy(current)))


def apply_delta(state: Any, operations: list[DeltaOperation]) -> Any:
    """Apply delta operations to a copied state and return the new state."""

    result = deepcopy(state)
    for operation in operations:
        if operation.kind == "set":
            if not operation.path:
                result = deepcopy(operation.value)
            else:
                parent, key = _resolve_parent(result, operation.path)
                parent[key] = deepcopy(operation.value)
        elif operation.kind == "append":
            target = _resolve_value(result, operation.path)
            if not isinstance(target, list):
                raise TypeError("append operation target must be a list")
            target.append(deepcopy(operation.value))
        elif operation.kind == "truncate":
            target = _resolve_value(result, operation.path)
            if not isinstance(target, list):
                raise TypeError("truncate operation target must be a list")
            del target[int(operation.value) :]
    return result


def _resolve_parent(state: Any, path: StatePath) -> tuple[Any, PathPart]:
    parent = state
    for part in path[:-1]:
        parent = parent[part]
    return parent, path[-1]


def _resolve_value(state: Any, path: StatePath) -> Any:
    value = state
    for part in path:
        value = value[part]
    return value


class TimelineHistory:
    """Bounded history using periodic snapshots and intervening deltas."""

    def __init__(
        self,
        *,
        checkpoint_interval: int = 20,
        max_frames: int = 2000,
        checkpoint_delta_threshold: int = 1500,
    ) -> None:
        if checkpoint_interval < 1:
            raise ValueError("checkpoint_interval must be positive")
        if max_frames < 2:
            raise ValueError("max_frames must be at least two")
        self.checkpoint_interval = checkpoint_interval
        self.max_frames = max_frames
        self.checkpoint_delta_threshold = checkpoint_delta_threshold
        self.frames: list[TimelineFrame] = []
        self.cursor = -1
        self._cursor_state: Any | None = None

    def reset(self, state: Any, generation: int) -> None:
        """Discard history and create its initial checkpoint."""

        snapshot = deepcopy(state)
        self.frames = [TimelineFrame(int(generation), checkpoint=snapshot)]
        self.cursor = 0
        self._cursor_state = deepcopy(snapshot)

    def record(self, state: Any, generation: int) -> bool:
        """Append a changed state, branching if the cursor is in the past."""

        if not self.frames:
            self.reset(state, generation)
            return True

        previous = self.current_state()
        delta = diff_states(previous, state)
        generation = int(generation)
        if not delta and generation == self.frames[self.cursor].generation:
            return False

        if self.cursor < len(self.frames) - 1:
            del self.frames[self.cursor + 1 :]

        new_index = self.cursor + 1
        use_checkpoint = (
            new_index % self.checkpoint_interval == 0
            or len(delta) >= self.checkpoint_delta_threshold
        )
        if use_checkpoint:
            frame = TimelineFrame(generation, checkpoint=deepcopy(state))
        else:
            frame = TimelineFrame(generation, delta=delta)
        self.frames.append(frame)
        self.cursor = new_index
        self._cursor_state = deepcopy(state)
        self._prune_if_needed()
        return True

    def current_state(self) -> Any:
        """Return a copy of the state at the cursor."""

        if self.cursor < 0:
            raise IndexError("timeline is empty")
        if self._cursor_state is None:
            self._cursor_state = self.reconstruct(self.cursor)
        return deepcopy(self._cursor_state)

    def reconstruct(self, index: int) -> Any:
        """Rebuild a frame from the nearest preceding checkpoint."""

        if not 0 <= index < len(self.frames):
            raise IndexError("timeline frame index out of range")
        checkpoint_index = index
        while not self.frames[checkpoint_index].is_checkpoint:
            checkpoint_index -= 1
        state = deepcopy(self.frames[checkpoint_index].checkpoint)
        for frame in self.frames[checkpoint_index + 1 : index + 1]:
            if frame.is_checkpoint:
                state = deepcopy(frame.checkpoint)
            else:
                state = apply_delta(state, frame.delta or [])
        return state

    def seek(self, index: int) -> Any:
        """Move to a chronological frame and return its reconstructed state."""

        state = self.reconstruct(index)
        self.cursor = index
        self._cursor_state = deepcopy(state)
        return state

    def step(self, amount: int) -> Any | None:
        """Move one or more frames, returning ``None`` if movement is impossible."""

        if not self.frames or amount == 0:
            return None
        target = max(0, min(len(self.frames) - 1, self.cursor + amount))
        if target == self.cursor:
            return None
        return self.seek(target)

    def seek_generation(self, generation: int) -> Any | None:
        """Seek the most recent frame carrying an exact generation label."""

        matches = [
            index
            for index, frame in enumerate(self.frames)
            if frame.generation == generation
        ]
        if not matches:
            return None
        return self.seek(matches[-1])

    def status(self) -> TimelineStatus:
        """Return display and diagnostics data without exposing mutable frames."""

        generations = tuple(frame.generation for frame in self.frames)
        checkpoints = tuple(
            index for index, frame in enumerate(self.frames) if frame.is_checkpoint
        )
        current_generation = (
            self.frames[self.cursor].generation if self.cursor >= 0 else 0
        )
        delta_frames = [frame for frame in self.frames if frame.delta is not None]
        return TimelineStatus(
            cursor=self.cursor,
            frame_count=len(self.frames),
            generation=current_generation,
            generations=generations,
            checkpoints=checkpoints,
            can_step_back=self.cursor > 0,
            can_step_forward=0 <= self.cursor < len(self.frames) - 1,
            checkpoint_count=len(checkpoints),
            delta_frame_count=len(delta_frames),
            delta_operation_count=sum(len(frame.delta or []) for frame in delta_frames),
        )

    def _prune_if_needed(self) -> None:
        overflow = len(self.frames) - self.max_frames
        if overflow <= 0:
            return
        prune_chunk = max(
            1,
            min(self.checkpoint_interval, self.max_frames // 10),
        )
        remove_count = max(overflow, prune_chunk)
        first_state = self.reconstruct(remove_count)
        remaining = self.frames[remove_count:]
        remaining[0] = TimelineFrame(
            remaining[0].generation,
            checkpoint=first_state,
        )
        self.frames = remaining
        self.cursor -= remove_count


class TimelineBinding:
    """Connect a timeline to workspace-specific capture and restore callbacks."""

    def __init__(
        self,
        capture: Callable[[], Any],
        restore: Callable[[Any], None],
        get_generation: Callable[[], int],
        *,
        checkpoint_interval: int = 20,
        max_frames: int = 2000,
    ) -> None:
        self.capture = capture
        self.restore = restore
        self.get_generation = get_generation
        self.timeline = TimelineHistory(
            checkpoint_interval=checkpoint_interval,
            max_frames=max_frames,
        )
        self._workspace_clean = True
        self.reset()

    def reset(self) -> None:
        """Start a new timeline at the workspace's current state."""

        self.timeline.reset(self.capture(), self.get_generation())
        self._workspace_clean = True

    def prepare_change(self) -> None:
        """Mark a logical mutation boundary.

        UI mutations are committed explicitly when complete. Keeping this hook
        capture-free avoids scanning a large grid both before and after every
        generation while preserving the controller command contract.
        """
        self._workspace_clean = False

    def sync(self) -> bool:
        """Record the workspace when it differs from the current history frame."""

        recorded = self.timeline.record(self.capture(), self.get_generation())
        self._workspace_clean = True
        return recorded

    def step(self, amount: int) -> bool:
        """Move relatively through existing history and restore the workspace."""

        if not self._workspace_clean:
            self.sync()
        state = self.timeline.step(amount)
        if state is None:
            return False
        self.restore(state)
        self._workspace_clean = True
        return True

    def seek(self, index: int) -> bool:
        """Restore a chronological frame by its timeline index."""

        if not self._workspace_clean:
            self.sync()
        try:
            state = self.timeline.seek(index)
        except IndexError:
            return False
        self.restore(state)
        self._workspace_clean = True
        return True

    def seek_generation(self, generation: int) -> bool:
        """Restore the most recent frame for an exact generation number."""

        if not self._workspace_clean:
            self.sync()
        state = self.timeline.seek_generation(generation)
        if state is None:
            return False
        self.restore(state)
        self._workspace_clean = True
        return True

    def status(self) -> TimelineStatus:
        """Return timeline status without recapturing the workspace state."""
        return self.timeline.status()
