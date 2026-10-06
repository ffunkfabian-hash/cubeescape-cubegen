"""Deterministic seed derivation.

A single *master seed* drives a whole batch. Every model gets its own seed
derived from ``(master, model type, index)`` via SHA-256, so

* the same command always produces the same files,
* adding a new model type or changing ``--count`` never changes the models
  that already existed,
* a single model can be rebuilt from the seed stored in ``manifest.json``.

All rolls go through :class:`StableRandom`, whose methods are frozen copies of
CPython's algorithms, so a new Python version can't change the models.
"""

from __future__ import annotations

import hashlib
import math
import random
from bisect import bisect
from itertools import accumulate
from typing import List, Optional, Sequence

MAX_SEED = 2**31 - 1  # fits signed 32-bit ints (Blender props, C#, GDScript)


def derive_seed(master: int, *keys: object) -> int:
    text = ":".join([str(int(master))] + [str(k) for k in keys])
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & MAX_SEED


def model_seed(master: int, model_type: str, index: int) -> int:
    return derive_seed(master, "model", model_type, index)


class StableRandom(random.Random):
    """``random.Random`` with its sampling methods frozen.

    Python only promises that ``random()`` keeps its sequence for a seed; the
    other methods may change between versions. These are copies of CPython
    3.9 - 3.13 (identical there), built on the Mersenne Twister core
    (``random()`` / ``getrandbits()``), so the generator gives the same models
    in Blender's Python and in any newer CLI Python.
    """

    def _randbelow(self, n: int) -> int:  # type: ignore[override]
        k = n.bit_length()
        r = self.getrandbits(k)
        while r >= n:
            r = self.getrandbits(k)
        return r

    def randrange(self, start: int, stop: Optional[int] = None, step: int = 1) -> int:  # type: ignore[override]
        if stop is None:
            if step != 1:
                raise TypeError("Missing a non-None stop argument")
            if start > 0:
                return self._randbelow(start)
            raise ValueError("empty range for randrange()")
        width = stop - start
        if step == 1:
            if width > 0:
                return start + self._randbelow(width)
            raise ValueError(f"empty range in randrange({start}, {stop})")
        if step > 0:
            n = (width + step - 1) // step
        elif step < 0:
            n = (width + step + 1) // step
        else:
            raise ValueError("zero step for randrange()")
        if n <= 0:
            raise ValueError(f"empty range in randrange({start}, {stop}, {step})")
        return start + step * self._randbelow(n)

    def randint(self, a: int, b: int) -> int:  # type: ignore[override]
        return self.randrange(a, b + 1)

    def choice(self, seq):  # type: ignore[override]
        if not len(seq):
            raise IndexError("Cannot choose from an empty sequence")
        return seq[self._randbelow(len(seq))]

    def uniform(self, a: float, b: float) -> float:  # type: ignore[override]
        return a + (b - a) * self.random()

    def shuffle(self, x: List) -> None:  # type: ignore[override]
        for i in reversed(range(1, len(x))):
            j = self._randbelow(i + 1)
            x[i], x[j] = x[j], x[i]

    def sample(self, population: Sequence, k: int) -> List:  # type: ignore[override]
        n = len(population)
        if not 0 <= k <= n:
            raise ValueError("Sample larger than population or is negative")
        result: List = [None] * k
        setsize = 21
        if k > 5:
            setsize += 4 ** math.ceil(math.log(k * 3, 4))
        if n <= setsize:
            pool = list(population)
            for i in range(k):
                j = self._randbelow(n - i)
                result[i] = pool[j]
                pool[j] = pool[n - i - 1]
        else:
            selected = set()
            for i in range(k):
                j = self._randbelow(n)
                while j in selected:
                    j = self._randbelow(n)
                selected.add(j)
                result[i] = population[j]
        return result

    def choices(self, population: Sequence, weights: Optional[Sequence[float]] = None, *,  # type: ignore[override]
                cum_weights: Optional[Sequence[float]] = None, k: int = 1) -> List:
        n = len(population)
        if cum_weights is None:
            if weights is None:
                return [population[math.floor(self.random() * n)] for _ in range(k)]
            cum_weights = list(accumulate(weights))
        elif weights is not None:
            raise TypeError("Cannot specify both weights and cumulative weights")
        if len(cum_weights) != n:
            raise ValueError("The number of weights does not match the population")
        total = cum_weights[-1] + 0.0
        if total <= 0.0:
            raise ValueError("Total of weights must be greater than zero")
        return [population[bisect(cum_weights, self.random() * total, 0, n - 1)] for _ in range(k)]


def sub_rng(seed: int, *keys: object) -> StableRandom:
    """Independent random stream for one aspect of a model (see ``Asset.sub``)."""
    return StableRandom(derive_seed(seed, "sub", *keys))


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
