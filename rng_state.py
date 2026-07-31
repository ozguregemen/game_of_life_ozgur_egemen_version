"""JSON-safe persistence helpers for Python's deterministic random generator."""

from __future__ import annotations

import hashlib
import random
import secrets
from typing import Any, Mapping, Sequence

RNG_ENGINE = "python-mt19937"
MAX_SEED = (1 << 63) - 1


def new_experiment_seed() -> int:
    """Return a user-storable master seed for a new application process."""
    return secrets.randbelow(MAX_SEED + 1)


def derive_seed(master_seed: int, stream: str) -> int:
    """Derive stable independent streams without relying on salted ``hash``."""
    payload = f"{int(master_seed)}:{stream}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def seeded_random(master_seed: int, stream: str) -> random.Random:
    """Create one deterministic random stream from a master seed and label."""
    return random.Random(derive_seed(master_seed, stream))


def encode_random_state(generator: random.Random) -> dict[str, Any]:
    """Convert ``Random.getstate`` into an explicit JSON-compatible object."""
    version, internal, gaussian = generator.getstate()
    return {
        "engine": RNG_ENGINE,
        "version": version,
        "state": list(internal),
        "gaussian": gaussian,
    }


def decode_random_state(value: Mapping[str, Any]) -> tuple[int, tuple[int, ...], float | None]:
    """Validate and decode one serialized MT19937 state."""
    if value.get("engine") != RNG_ENGINE:
        raise ValueError(f"Unsupported random engine: {value.get('engine')!r}.")
    version = value.get("version")
    internal = value.get("state")
    gaussian = value.get("gaussian")
    if isinstance(version, bool) or not isinstance(version, int):
        raise TypeError("Random state version must be an integer.")
    if isinstance(internal, (str, bytes)) or not isinstance(internal, Sequence):
        raise TypeError("Random state must be an integer array.")
    if not internal or any(isinstance(item, bool) or not isinstance(item, int) for item in internal):
        raise TypeError("Random state must contain only integers.")
    if gaussian is not None and (
        isinstance(gaussian, bool) or not isinstance(gaussian, (int, float))
    ):
        raise TypeError("Random Gaussian cache must be a number or null.")
    decoded = (version, tuple(internal), None if gaussian is None else float(gaussian))
    probe = random.Random()
    probe.setstate(decoded)
    return decoded


def restore_random_state(generator: random.Random, value: Mapping[str, Any]) -> None:
    """Restore a generator only after its entire state has been validated."""
    generator.setstate(decode_random_state(value))
