"""Palette mode (``--textures palette``): one material per model, so a static model is one draw call.

All ``M_*`` colours of the game sit as cells in one small palette texture
(``MP_Palette``). A face keeps its look, its UVs point at the centre of its
material's cell (no filtering across cells: point sampling, every cell is
16 x 16 px). Maps, like the tiled textures (Unity Standard / URP Lit):

* ``MP_Palette_Albedo.png``             base colour (sRGB)
* ``MP_Palette_MetallicSmoothness.png`` R = metallic, A = smoothness
* ``MP_Palette_Emission.png``           glow colours (x ``emission`` from the JSON), black elsewhere

Kept as their own material (the game needs them separate):

* parts the scripts recolour: ``SignalIndicator.renderers``, ``Machine.glow``,
  ``SignalLight.glow``, ``Rotatable.glow``, ``Door.statusLights`` - they swap
  ``renderer.sharedMaterial``, which would recolour the whole palette model
* ``M_Glass`` - transparent, it can't share an opaque material

So a static model needs 1 draw call (2 with glass), a scripted one 1 per moving
part plus its status lights. Pure Python (PNG writer below), no ImageMagick.
"""

from __future__ import annotations

import json
import math
import os
import struct
import zlib
from typing import Dict, Iterable, List, Optional, Tuple

from .materials import MATERIALS

PALETTE_MATERIAL = "MP_Palette"
KEEP = ("M_Glass",)
#: behaviour roles whose parts change material at runtime
SWAPPED_ROLES = {"SignalIndicator": ("renderers",), "Machine": ("glow",), "SignalLight": ("glow",),
                 "Rotatable": ("glow",), "Door": ("statusLights",)}
COLUMNS = 4
CELL = 16  # px per cell
ORDER = list(MATERIALS)  # cell index = position in the game's material table (new materials go at the end)


def cell(material: str) -> Tuple[int, int]:
    """(column, row from the top) of a material's cell."""
    i = ORDER.index(material)
    return i % COLUMNS, i // COLUMNS


def rows() -> int:
    return math.ceil(len(ORDER) / COLUMNS)


def uv(material: str) -> Tuple[float, float]:
    """UV of the centre of a material's cell (v = 0 at the bottom of the image)."""
    col, row = cell(material)
    return ((col + 0.5) / COLUMNS, 1.0 - (row + 0.5) / rows())


def max_emission() -> float:
    return max(e for _, _, _, e in MATERIALS.values() if e)


class PaletteMap:
    """Material of every face in palette mode: ``map(part, role)``; ``uv(role)`` for palette faces."""

    def __init__(self, keep_parts: Iterable[str] = ()):
        self.keep_parts = set(keep_parts)

    def __call__(self, part: str, role: str) -> str:
        if part in self.keep_parts or role in KEEP:
            return role
        return PALETTE_MATERIAL

    @staticmethod
    def uv(role: str) -> Tuple[float, float]:
        return uv(role)

    def to_dict(self) -> Dict[str, object]:
        return {"material": PALETTE_MATERIAL, "keep_parts": sorted(self.keep_parts), "keep": list(KEEP)}


def material_map(asset) -> PaletteMap:
    """The palette map of an asset: everything into ``MP_Palette`` except parts its scripts recolour and glass."""
    keep: List[str] = []
    for b in asset.behaviours:
        for role in SWAPPED_ROLES.get(b["script"], ()):
            value = b["parts"].get(role)
            keep += value if isinstance(value, list) else ([value] if value else [])
    return PaletteMap(keep)


def resolve(material_map, part: str, role: str) -> str:
    """Material of a face: a ``PaletteMap`` (per part) or a plain ``{"M_Metal": "MT_Metal"}`` dict (or None)."""
    if callable(material_map):
        return material_map(part, role)
    return (material_map or {}).get(role, role)


# ---------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------

def write_png(path: str, width: int, height: int, pixels: List[Tuple[int, int, int, int]]) -> None:
    """Minimal RGBA PNG writer (8 bit, no filtering) - deterministic, no dependencies."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(bytes(pixels[y * width + x]))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def _image(value) -> Tuple[int, int, List[Tuple[int, int, int, int]]]:
    width, height = COLUMNS * CELL, rows() * CELL
    pixels = []
    for y in range(height):
        for x in range(width):
            index = (y // CELL) * COLUMNS + x // CELL
            pixels.append(value(ORDER[index]) if index < len(ORDER) else (0, 0, 0, 255))
    return width, height, pixels


def _byte(v: float) -> int:
    return max(0, min(255, int(round(v * 255))))


def write_palette(out_dir: str, log=print) -> Dict[str, object]:
    """The palette maps + ``CubeEscape_Palette.json`` in ``out_dir``; returns the info (with absolute paths)."""
    os.makedirs(out_dir, exist_ok=True)
    peak = max_emission()
    maps = {
        "Albedo": lambda m: tuple(_byte(c) for c in MATERIALS[m][0]) + (255,),
        "MetallicSmoothness": lambda m: (_byte(MATERIALS[m][2]),) * 3 + (_byte(MATERIALS[m][1]),),
        "Emission": lambda m: tuple(_byte(c * (MATERIALS[m][3] or 0) / peak) for c in MATERIALS[m][0]) + (255,),
    }
    paths = {}
    for kind, value in maps.items():
        path = os.path.join(out_dir, f"{PALETTE_MATERIAL}_{kind}.png")
        write_png(path, *_image(value))
        paths[kind] = path
    info = {
        "name": PALETTE_MATERIAL,
        "size": [COLUMNS * CELL, rows() * CELL],
        "cell_px": CELL,
        "emission": peak,
        "filter": "point",
        "note": "Unity: one material MP_Palette (Albedo -> base map, MetallicSmoothness -> metallic map with "
                "smoothness from alpha, Emission -> emission map x emission), textures with Filter Mode Point, "
                "no mipmaps (or Clamp), sRGB only for Albedo and Emission.",
        "cells": {m: {"uv": list(uv(m)), "cell": list(cell(m))} for m in ORDER},
        "keep": list(KEEP) + [f"parts recoloured by scripts ({', '.join(sorted(SWAPPED_ROLES))})"],
        "maps": {k: os.path.basename(v) for k, v in paths.items()},
    }
    with open(os.path.join(out_dir, "CubeEscape_Palette.json"), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)
    log(f"palette ({len(ORDER)} materials, {info['size'][0]}x{info['size'][1]} px) -> {out_dir}")
    return dict(info, paths=paths)


def draw_calls(asset, palette: Optional[PaletteMap] = None) -> int:
    """Draw calls of an asset in palette mode (see ``quality.draw_calls``)."""
    palette = palette or material_map(asset)
    if not asset.behaviours:
        return len({palette(o.name, r) for o in asset.meshes() for r in o.mesh.roles})
    return sum(len({palette(o.name, r) for r in o.mesh.roles}) for o in asset.meshes())


__all__ = ["PALETTE_MATERIAL", "PaletteMap", "material_map", "resolve", "uv", "write_palette", "write_png",
           "draw_calls"]
