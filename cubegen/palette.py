"""Palette mode (``--textures palette``): one material per model, so a static model is one draw call.

All ``M_*`` colours of the game sit as cells in one small palette texture
(``MP_Palette``). A face keeps its look, its UVs point at the centre of its
material's cell (no filtering across cells: point sampling, every cell is
16 x 16 px). Maps, like the tiled textures (Unity Standard / URP Lit):

Colour palettes (``--palette``, ``COLOR_PALETTES``) recolour the cells: ``MP_Palette_<Name>`` with its own maps
and manifest; the models (UVs) stay the same.

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

PALETTE_MATERIAL = "MP_Palette"  # the standard palette (the game's colours); other palettes: MP_Palette_<Name>
DEFAULT_PALETTE = "standard"
KEEP = ("M_Glass",)
#: behaviour roles whose parts change material at runtime
SWAPPED_ROLES = {"SignalIndicator": ("renderers",), "Machine": ("glow",), "SignalLight": ("glow",),
                 "Rotatable": ("glow",), "Door": ("statusLights",)}
COLUMNS = 4
CELL = 16  # px per cell
ORDER = list(MATERIALS)  # cell index = position in the game's material table (new materials go at the end)


# ---------------------------------------------------------------------------
# colour palettes
# ---------------------------------------------------------------------------

#: Colour palettes for palette mode (``--palette``): sRGB colours that replace the game's ``M_*`` colours in the
#: palette texture. Every palette has the same cells, so a model looks different only by its material
#: (``MP_Palette_<Name>``) - one export per palette, or swap the material in Unity. Glass and the parts the
#: scripts recolour keep their ``M_*`` material (see the module docstring), so their colours stay the game's.
#: ``emission`` scales the glow; ``family`` is the model family the palette was made for.
COLOR_PALETTES: Dict[str, Dict[str, object]] = {
    "rust": {
        "title": "Rost", "family": "foundry", "emission": 1.0,
        "description": "Gießerei: warme Brauntöne, oxidiertes Metall, Bernstein-Glow",
        "colors": {
            "M_Ground": (0.20, 0.15, 0.12), "M_Wall": (0.36, 0.26, 0.20), "M_Platform": (0.62, 0.55, 0.46),
            "M_HazardOrange": (0.85, 0.38, 0.12), "M_RobotBody": (0.78, 0.70, 0.58),
            "M_RobotDark": (0.16, 0.12, 0.10), "M_GlowCyan": (1.00, 0.62, 0.18), "M_GlowRed": (1.00, 0.18, 0.08),
            "M_GlowOrange": (1.00, 0.40, 0.05), "M_Crystal": (1.00, 0.55, 0.20), "M_Metal": (0.50, 0.38, 0.28),
            "M_Warning": (0.90, 0.62, 0.12), "M_PortalPanel": (0.66, 0.58, 0.48),
        },
    },
    "frost": {
        "title": "Frost", "family": "lab", "emission": 1.0,
        "description": "Kryo: Eisblau und Weiß, kühles Licht",
        "colors": {
            "M_Ground": (0.70, 0.76, 0.82), "M_Wall": (0.55, 0.64, 0.74), "M_Platform": (0.92, 0.95, 0.98),
            "M_HazardOrange": (1.00, 0.52, 0.20), "M_RobotBody": (0.95, 0.97, 1.00),
            "M_RobotDark": (0.20, 0.26, 0.34), "M_GlowCyan": (0.55, 0.90, 1.00), "M_GlowRed": (1.00, 0.25, 0.30),
            "M_GlowOrange": (1.00, 0.45, 0.15), "M_Crystal": (0.70, 0.95, 1.00), "M_Metal": (0.62, 0.70, 0.78),
            "M_Warning": (0.98, 0.80, 0.25), "M_PortalPanel": (0.85, 0.90, 0.95),
        },
    },
    "toxic": {
        "title": "Gift", "family": "reactor", "emission": 1.2,
        "description": "Reaktor / Störfall: dunkles Grüngrau, Säuregrün",
        "colors": {
            "M_Ground": (0.12, 0.15, 0.11), "M_Wall": (0.22, 0.27, 0.20), "M_Platform": (0.62, 0.68, 0.55),
            "M_HazardOrange": (0.95, 0.55, 0.08), "M_RobotBody": (0.76, 0.80, 0.68),
            "M_RobotDark": (0.10, 0.12, 0.09), "M_GlowCyan": (0.55, 1.00, 0.15), "M_GlowRed": (1.00, 0.20, 0.10),
            "M_GlowOrange": (1.00, 0.35, 0.05), "M_Crystal": (0.45, 1.00, 0.35), "M_Metal": (0.38, 0.44, 0.36),
            "M_Warning": (0.85, 0.90, 0.10), "M_PortalPanel": (0.60, 0.66, 0.55),
        },
    },
    "medical": {
        "title": "Medizin", "family": "medbay", "emission": 0.8,
        "description": "Krankenstation: Weiß, Mint, sanftes Türkis",
        "colors": {
            "M_Ground": (0.62, 0.68, 0.70), "M_Wall": (0.86, 0.90, 0.90), "M_Platform": (0.96, 0.97, 0.97),
            "M_HazardOrange": (0.95, 0.45, 0.25), "M_RobotBody": (0.98, 0.99, 1.00),
            "M_RobotDark": (0.30, 0.38, 0.40), "M_GlowCyan": (0.30, 0.95, 0.80), "M_GlowRed": (1.00, 0.25, 0.25),
            "M_GlowOrange": (1.00, 0.50, 0.15), "M_Crystal": (0.55, 1.00, 0.90), "M_Metal": (0.70, 0.76, 0.78),
            "M_Warning": (0.95, 0.78, 0.30), "M_PortalPanel": (0.80, 0.92, 0.90),
        },
    },
    "derelict": {
        "title": "Wrack", "family": "derelict", "emission": 0.4,
        "description": "Verlassenes Wrack: ausgeblichen, staubig, schwaches Licht",
        "colors": {
            "M_Ground": (0.17, 0.17, 0.16), "M_Wall": (0.30, 0.30, 0.29), "M_Platform": (0.55, 0.54, 0.50),
            "M_HazardOrange": (0.62, 0.36, 0.18), "M_RobotBody": (0.62, 0.61, 0.57),
            "M_RobotDark": (0.13, 0.13, 0.12), "M_GlowCyan": (0.35, 0.55, 0.55), "M_GlowRed": (0.70, 0.18, 0.12),
            "M_GlowOrange": (0.70, 0.30, 0.10), "M_Crystal": (0.40, 0.60, 0.62), "M_Metal": (0.40, 0.40, 0.38),
            "M_Warning": (0.62, 0.52, 0.22), "M_PortalPanel": (0.52, 0.52, 0.50),
        },
    },
    "greenhouse": {
        "title": "Gewächshaus", "family": "greenhouse", "emission": 0.9,
        "description": "Gewächshaus: Moosgrün, Erde, Holz, warmes Licht",
        "colors": {
            "M_Ground": (0.22, 0.17, 0.11), "M_Wall": (0.30, 0.38, 0.26), "M_Platform": (0.70, 0.62, 0.45),
            "M_HazardOrange": (0.95, 0.50, 0.12), "M_RobotBody": (0.88, 0.88, 0.80),
            "M_RobotDark": (0.16, 0.18, 0.12), "M_GlowCyan": (0.95, 0.85, 0.45), "M_GlowRed": (1.00, 0.22, 0.12),
            "M_GlowOrange": (1.00, 0.48, 0.10), "M_Crystal": (0.60, 0.95, 0.55), "M_Metal": (0.45, 0.48, 0.40),
            "M_Warning": (0.92, 0.78, 0.20), "M_PortalPanel": (0.78, 0.80, 0.68),
        },
    },
    "neon": {
        "title": "Neon", "family": None, "emission": 1.3,
        "description": "Nachtschicht: tiefes Violett, Magenta- und Cyan-Licht",
        "colors": {
            "M_Ground": (0.08, 0.06, 0.12), "M_Wall": (0.16, 0.12, 0.24), "M_Platform": (0.40, 0.36, 0.52),
            "M_HazardOrange": (1.00, 0.30, 0.55), "M_RobotBody": (0.70, 0.66, 0.85),
            "M_RobotDark": (0.07, 0.05, 0.10), "M_GlowCyan": (1.00, 0.20, 0.85), "M_GlowRed": (1.00, 0.12, 0.30),
            "M_GlowOrange": (1.00, 0.45, 0.10), "M_Crystal": (0.65, 0.35, 1.00), "M_Metal": (0.32, 0.30, 0.42),
            "M_Warning": (0.20, 0.95, 1.00), "M_PortalPanel": (0.50, 0.45, 0.65),
        },
    },
}


def palette_names() -> List[str]:
    return [DEFAULT_PALETTE] + list(COLOR_PALETTES)


def check_palette(name: Optional[str]) -> str:
    """A palette name (``None`` / empty = the standard palette); unknown names raise ``ValueError``."""
    name = (name or DEFAULT_PALETTE).strip().lower()
    if name not in palette_names():
        raise ValueError(f"unknown colour palette {name!r}; available: {', '.join(palette_names())}")
    return name


def palette_material(name: Optional[str] = None) -> str:
    """Material name of a palette: ``MP_Palette`` for the standard one, else ``MP_Palette_<Name>``."""
    name = check_palette(name)
    return PALETTE_MATERIAL if name == DEFAULT_PALETTE else f"{PALETTE_MATERIAL}_{name.capitalize()}"


def is_palette_material(material: str) -> bool:
    return material == PALETTE_MATERIAL or material.startswith(PALETTE_MATERIAL + "_")


def palette_colors(name: Optional[str] = None) -> Dict[str, Tuple[Tuple[float, float, float], float, float,
                                                                     Optional[float]]]:
    """The material table of a palette, like ``materials.MATERIALS``: (sRGB, smoothness, metallic, emission)."""
    name = check_palette(name)
    if name == DEFAULT_PALETTE:
        return dict(MATERIALS)
    entry = COLOR_PALETTES[name]
    colors, scale = entry["colors"], float(entry.get("emission") or 1.0)
    return {m: (tuple(colors.get(m, rgb)), smooth, metal, emission * scale if emission else emission)
            for m, (rgb, smooth, metal, emission) in MATERIALS.items()}


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


def max_emission(table=None) -> float:
    return max(e for _, _, _, e in (table or MATERIALS).values() if e)


class PaletteMap:
    """Material of every face in palette mode: ``map(part, role)``; ``uv(role)`` for palette faces."""

    def __init__(self, keep_parts: Iterable[str] = (), material: str = PALETTE_MATERIAL):
        self.keep_parts = set(keep_parts)
        self.material = material

    def __call__(self, part: str, role: str) -> str:
        if part in self.keep_parts or role in KEEP:
            return role
        return self.material

    @staticmethod
    def uv(role: str) -> Tuple[float, float]:
        return uv(role)

    def to_dict(self) -> Dict[str, object]:
        return {"material": self.material, "keep_parts": sorted(self.keep_parts), "keep": list(KEEP)}


def material_map(asset, palette: Optional[str] = None) -> PaletteMap:
    """The palette map of an asset: everything into the palette material (``MP_Palette`` or
    ``MP_Palette_<Name>``) except parts its scripts recolour and glass."""
    keep: List[str] = []
    for b in asset.behaviours + asset.meta.get("deferred_behaviours", []):
        for role in SWAPPED_ROLES.get(b["script"], ()):
            value = b["parts"].get(role)
            keep += value if isinstance(value, list) else ([value] if value else [])
    return PaletteMap(keep, palette_material(palette))


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


def palette_manifest_name(name: Optional[str] = None) -> str:
    """``CubeEscape_Palette.json`` (standard) or ``CubeEscape_Palette_<Name>.json`` - several palettes can share
    one textures folder."""
    material = palette_material(name)
    return f"CubeEscape{material[len('MP'):]}.json"


def write_palette(out_dir: str, log=print, name: Optional[str] = None) -> Dict[str, object]:
    """The maps of a colour palette + its manifest (``palette_manifest_name``) in ``out_dir``; returns the info
    (with absolute paths)."""
    name = check_palette(name)
    material = palette_material(name)
    table = palette_colors(name)
    os.makedirs(out_dir, exist_ok=True)
    peak = max_emission(table)
    maps = {
        "Albedo": lambda m: tuple(_byte(c) for c in table[m][0]) + (255,),
        "MetallicSmoothness": lambda m: (_byte(table[m][2]),) * 3 + (_byte(table[m][1]),),
        "Emission": lambda m: tuple(_byte(c * (table[m][3] or 0) / peak) for c in table[m][0]) + (255,),
    }
    paths = {}
    for kind, value in maps.items():
        path = os.path.join(out_dir, f"{material}_{kind}.png")
        write_png(path, *_image(value))
        paths[kind] = path
    info = {
        "name": material,
        "palette": name,
        "size": [COLUMNS * CELL, rows() * CELL],
        "cell_px": CELL,
        "emission": peak,
        "filter": "point",
        "note": f"Unity: one material {material} (Albedo -> base map, MetallicSmoothness -> metallic map with "
                "smoothness from alpha, Emission -> emission map x emission), textures with Filter Mode Point, "
                "no mipmaps (or Clamp), sRGB only for Albedo and Emission. All palettes share the cells: another "
                "palette = another material, same models.",
        "cells": {m: {"uv": list(uv(m)), "cell": list(cell(m))} for m in ORDER},
        "keep": list(KEEP) + [f"parts recoloured by scripts ({', '.join(sorted(SWAPPED_ROLES))})"],
        "maps": {k: os.path.basename(v) for k, v in paths.items()},
    }
    if name != DEFAULT_PALETTE:
        info["description"] = COLOR_PALETTES[name]["description"]
    with open(os.path.join(out_dir, palette_manifest_name(name)), "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)
    log(f"palette {name} ({material}, {len(ORDER)} materials, {info['size'][0]}x{info['size'][1]} px) -> {out_dir}")
    return dict(info, paths=paths)


def write_swatches(path: str, names: Optional[Iterable[str]] = None, cell_px: int = 24) -> str:
    """One row per palette, one square per material (the order of the palette texture) - to compare palettes."""
    names = [check_palette(n) for n in (names or palette_names())]
    width, height = len(ORDER) * cell_px, len(names) * cell_px
    pixels = []
    for row in range(height):
        table = palette_colors(names[row // cell_px])
        for x in range(width):
            edge = row % cell_px in (0, cell_px - 1) or x % cell_px in (0, cell_px - 1)
            rgb = table[ORDER[x // cell_px]][0]
            pixels.append((20, 20, 24, 255) if edge else tuple(_byte(c) for c in rgb) + (255,))
    write_png(path, width, height, pixels)
    return path


def draw_calls(asset, palette: Optional[PaletteMap] = None) -> int:
    """Draw calls of an asset in palette mode (see ``quality.draw_calls``)."""
    palette = palette or material_map(asset)
    if not asset.behaviours:
        return len({palette(o.name, r) for o in asset.meshes() for r in o.mesh.roles})
    return sum(len({palette(o.name, r) for r in o.mesh.roles}) for o in asset.meshes())


__all__ = ["PALETTE_MATERIAL", "DEFAULT_PALETTE", "COLOR_PALETTES", "PaletteMap", "material_map", "resolve", "uv",
           "write_palette", "write_png", "write_swatches", "draw_calls", "palette_names", "check_palette",
           "palette_material", "palette_colors", "palette_manifest_name", "is_palette_material"]
