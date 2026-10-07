"""Wear & tear: rubble, loose plates and torn cables around a finished model.

Uses its own random stream (derived from the asset seed), so adding wear never
changes the model itself. Goes into a separate static part ``Wear`` - the game's
scripts ignore unknown parts.
"""

from __future__ import annotations

import math

from ..seeds import StableRandom
from .common import cube, deg

LEVELS = {"light": (2, 3, 0, 1), "heavy": (5, 8, 1, 2)}  # chunks min/max, plates min/max


def apply_wear(asset, seed: int, level: str) -> None:
    rng = StableRandom(seed ^ 0x5EA7)
    (x0, y0, _), (x1, y1, z1) = asset.bbox()
    w, d = max(x1 - x0, 0.3), max(y1 - y0, 0.3)
    size = min(max(w, d), 3.0)
    cmin, cmax, pmin, pmax = LEVELS[level]
    m = asset.part("Wear")
    for _ in range(rng.randint(cmin, cmax)):
        s = size * rng.uniform(0.04, 0.1)
        side = rng.choice([-1, 1])
        if rng.random() < 0.5:   # along the front / back edge
            x, y = rng.uniform(x0, x1), (y0 if side < 0 else y1) + side * rng.uniform(0.0, s * 1.5)
        else:                    # along the left / right edge
            x, y = (x0 if side < 0 else x1) + side * rng.uniform(0.0, s * 1.5), rng.uniform(y0, y1)
        cube(m, (s, s * 0.8, s * 0.6), (x, y, s * 0.25), rng.choice(["M_Wall", "M_Ground", "M_RobotDark"]),
             rot=(deg(rng.uniform(-20, 20)), deg(rng.uniform(-20, 20)), rng.uniform(0, math.pi)))
    for _ in range(rng.randint(pmin, pmax)):  # a plate leaning against the front
        pw = min(w, 1.2) * rng.uniform(0.3, 0.5)
        cube(m, (pw, 0.03, pw * 0.7), (rng.uniform(x0 + pw / 2, max(x0 + pw / 2, x1 - pw / 2)), y0 - 0.12,
                                       pw * 0.3), "M_Metal", rot=(deg(-30), 0, deg(rng.uniform(-15, 15))))
    if level == "heavy" and z1 > 0.6:  # a torn cable hanging down the side
        cube(m, (0.04, 0.04, z1 * 0.5), (x1 + 0.03, rng.uniform(y0, y1), z1 * 0.3), "M_HazardOrange",
             rot=(deg(rng.uniform(-15, 15)), deg(rng.uniform(5, 20)), 0))
    asset.meta["wear"] = level
