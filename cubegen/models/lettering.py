"""Text on models: room numbers, labels, counters (``sign.text=B-12``, ``door.label``, ``countdown``).

A low-poly block font: every glyph is a few straight strokes on a 4 x 6 grid,
each stroke one box. Text stands upright in the XZ plane and faces the front
(-Y), like the symbols on ``sign``. Letters A-Z (also Ä Ö Ü), digits and
``- . : / + # _ ' !`` are known; lower case is shown as upper case.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from ..geometry import Mesh
from .common import cube

Stroke = Tuple[float, float, float, float]

GRID_W, GRID_H = 4.0, 6.0
ADVANCE = 5.5          # grid units from one character to the next (glyph + gap)
STROKE = 0.9           # stroke thickness in grid units

_L, _R, _T, _B, _M = (0, 0, 0, 6), (4, 0, 4, 6), (0, 6, 4, 6), (0, 0, 4, 0), (0, 3, 4, 3)

GLYPHS: Dict[str, Tuple[Stroke, ...]] = {
    "A": (_L, _R, _T, _M),
    "B": (_L, (0, 6, 3, 6), (3, 6, 3, 3), _M, (4, 3, 4, 0), _B),
    "C": (_L, _T, _B),
    "D": (_L, (0, 6, 3, 6), (3, 6, 4, 5), (4, 5, 4, 1), (4, 1, 3, 0), (3, 0, 0, 0)),
    "E": (_L, _T, (0, 3, 3, 3), _B),
    "F": (_L, _T, (0, 3, 3, 3)),
    "G": (_L, _T, _B, (4, 0, 4, 3), (2, 3, 4, 3)),
    "H": (_L, _R, _M),
    "I": ((2, 0, 2, 6), (1, 6, 3, 6), (1, 0, 3, 0)),
    "J": ((4, 6, 4, 0), _B, (0, 0, 0, 2)),
    "K": (_L, (0, 3, 4, 6), (0, 3, 4, 0)),
    "L": (_L, _B),
    "M": (_L, _R, (0, 6, 2, 3), (2, 3, 4, 6)),
    "N": (_L, _R, (0, 6, 4, 0)),
    "O": (_L, _R, _T, _B),
    "P": (_L, _T, (4, 6, 4, 3), _M),
    "Q": (_L, _R, _T, _B, (2, 2, 4, 0)),
    "R": (_L, _T, (4, 6, 4, 3), _M, (1, 3, 4, 0)),
    "S": (_T, (0, 6, 0, 3), _M, (4, 3, 4, 0), _B),
    "T": (_T, (2, 6, 2, 0)),
    "U": (_L, _R, _B),
    "V": ((0, 6, 2, 0), (2, 0, 4, 6)),
    "W": (_L, _R, (0, 0, 2, 3), (2, 3, 4, 0)),
    "X": ((0, 0, 4, 6), (0, 6, 4, 0)),
    "Y": ((0, 6, 2, 3), (4, 6, 2, 3), (2, 3, 2, 0)),
    "Z": (_T, (4, 6, 0, 0), _B),
    "0": (_L, _R, _T, _B, (1, 1.5, 3, 4.5)),
    "1": ((2, 0, 2, 6), (2, 6, 0.8, 4.8), (1, 0, 3, 0)),
    "2": (_T, (4, 6, 4, 3), _M, (0, 3, 0, 0), _B),
    "3": (_T, _R, (1, 3, 4, 3), _B),
    "4": ((0, 6, 0, 3), _M, (3, 6, 3, 0)),
    "5": (_T, (0, 6, 0, 3), _M, (4, 3, 4, 0), _B),
    "6": (_T, _L, _B, (4, 3, 4, 0), _M),
    "7": (_T, (4, 6, 1.5, 0)),
    "8": (_L, _R, _T, _B, _M),
    "9": (_T, _R, _M, (0, 6, 0, 3), _B),
    "-": ((1, 3, 3, 3),),
    "+": ((0.8, 3, 3.2, 3), (2, 1.8, 2, 4.2)),
    ".": ((2, 0, 2, 0.5),),
    ":": ((2, 1, 2, 1.5), (2, 4, 2, 4.5)),
    "/": ((0, 0, 4, 6),),
    "_": (_B,),
    "'": ((2, 6, 2, 4.5),),
    "!": ((2, 6, 2, 2), (2, 0, 2, 0.5)),
    "#": ((1.3, 0, 1.3, 6), (2.7, 0, 2.7, 6), (0, 2, 4, 2), (0, 4, 4, 4)),
    " ": (),
}
UMLAUTS = {"Ä": "A", "Ö": "O", "Ü": "U"}
DOTS = ((1, 7, 1, 7.5), (3, 7, 3, 7.5))
CHARSET = "".join(GLYPHS) + "".join(UMLAUTS)


def check_text(text: str, max_len: int = 24) -> str:
    """Upper case text the font can draw (ValueError names the characters it can't)."""
    text = str(text).strip().upper()
    if not text or len(text) > max_len:
        raise ValueError(f"text: 1-{max_len} characters, got {text!r}")
    bad = sorted({c for c in text if c not in CHARSET})
    if bad:
        raise ValueError(f"text {text!r}: no glyph for {' '.join(repr(c) for c in bad)}; known: A-Z Ä Ö Ü 0-9 "
                         "and - + . : / _ ' ! # space")
    return text


def glyph(char: str) -> Tuple[Stroke, ...]:
    if char in UMLAUTS:
        return GLYPHS[UMLAUTS[char]] + DOTS
    return GLYPHS[char]


def text_width(text: str, height: float) -> float:
    """Width of ``text`` in metres at cap height ``height``."""
    s = height / GRID_H
    return (len(text) * ADVANCE - (ADVANCE - GRID_W)) * s + STROKE * s


def strokes(text: str) -> List[Stroke]:
    """All strokes of a line of text, in grid units, starting at x = 0."""
    out: List[Stroke] = []
    for i, char in enumerate(text):
        dx = i * ADVANCE
        out += [(x1 + dx, y1, x2 + dx, y2) for x1, y1, x2, y2 in glyph(char)]
    return out


def add_text(mesh: Mesh, text: str, center: Sequence[float], height: float, depth: float, material: str) -> float:
    """Raised letters centred on ``center`` (x, y = front face of the plate behind it, z), facing -Y.

    The strokes stand ``depth`` proud of the plate. Returns the text width in metres.
    """
    text = check_text(text, max_len=len(text) or 1)
    s = height / GRID_H
    t = STROKE * s
    width = text_width(text, height)
    x0 = center[0] - width / 2 + t / 2
    z0 = center[2] - height / 2
    y = center[1] - depth / 2
    for x1, z1, x2, z2 in strokes(text):
        dx, dz = (x2 - x1) * s, (z2 - z1) * s
        length = math.hypot(dx, dz)
        mid = (x0 + (x1 + x2) / 2 * s, y, z0 + (z1 + z2) / 2 * s)
        angle = math.atan2(dz, dx)
        cube(mesh, (length + t, depth, t), mid, material, rot=(0.0, -angle, 0.0))
    return width


__all__ = ["add_text", "check_text", "text_width", "strokes", "CHARSET", "GLYPHS"]
