"""Deterministic seed derivation.

A single *master seed* drives a whole batch. Every model gets its own seed
derived from ``(master, model type, index)`` via SHA-256, so

* the same command always produces the same files,
* adding a new model type or changing ``--count`` never changes the models
  that already existed,
* a single model can be rebuilt from the seed stored in ``manifest.json``.
"""

from __future__ import annotations

import hashlib
import random

MAX_SEED = 2**31 - 1  # fits signed 32-bit ints (Blender props, C#, GDScript)


def derive_seed(master: int, *keys: object) -> int:
    text = ":".join([str(int(master))] + [str(k) for k in keys])
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & MAX_SEED


def model_seed(master: int, model_type: str, index: int) -> int:
    return derive_seed(master, "model", model_type, index)


def random_master_seed() -> int:
    return random.SystemRandom().randint(0, 999_999)


def parse_seed(value) -> int:
    """Accept ints and arbitrary strings ("level-3") as seeds."""
    if value is None:
        return random_master_seed()
    if isinstance(value, int):
        return value
    text = str(value).strip()
    try:
        return int(text)
    except ValueError:
        return derive_seed(0, "text", text)
