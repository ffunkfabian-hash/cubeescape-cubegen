"""Tileable material textures made with ImageMagick (optional: ``--textures tiled``).

Every textured material gets its own name (``MT_Metal`` ...) so the game's
importer, which remaps ``M_*`` materials by name, keeps the plain materials of
hand-made assets untouched. Status / glow materials (``M_Glow*``), crystal and
glass are never textured - the game's scripts swap them at runtime.

Textures tile seamlessly: all noise, blur and patterns wrap around the edges
(``-virtual-pixel tile`` and periodic patterns). The models are UV mapped with
a box projection in metres, so one texture tile = 1 m x 1 m on every face.

Maps per material (Unity URP / Standard friendly):

* ``<Name>_Albedo.png``            base colour (sRGB)
* ``<Name>_Normal.png``            tangent-space normal map (OpenGL / Unity convention, Y+)
* ``<Name>_Roughness.png``         roughness (Blender)
* ``<Name>_MetallicSmoothness.png`` R = metallic, A = smoothness (Unity)
"""

from __future__ import annotations

import json
import math
import os
import random
import tempfile
from typing import Dict, List, Optional

from .imagemagick import ImageMagick
from .materials import MATERIALS, to_hex
from .seeds import StableRandom

#: plain material -> texture recipe
RECIPES = {
    "M_Metal": "brushed",
    "M_Wall": "panels",
    "M_RobotDark": "coated",
    "M_Platform": "plating",
    "M_Ground": "diamond",
    "M_RobotBody": "painted",
    "M_Warning": "chipped",
    "M_HazardOrange": "chipped",
}
TEXTURE_MODES = ("none", "tiled", "baked")
BARE_METAL = "#4a4e55"


def textured_name(material: str, texture_set: str = "") -> str:
    base = material[2:] if material.startswith("M_") else material
    return f"MT_{texture_set}_{base}" if texture_set else f"MT_{base}"


def material_map(texture_set: str = "") -> Dict[str, str]:
    """``{"M_Metal": "MT_Metal", ...}`` for every material that gets a texture."""
    return {m: textured_name(m, texture_set) for m in RECIPES}


class _Layers:
    """Grayscale building blocks (all tileable), written to a work directory."""

    def __init__(self, im: ImageMagick, work: str, size: int, rng: random.Random):
        self.im, self.work, self.n, self.rng = im, work, size, rng
        self.count = 0

    def path(self, name: str) -> str:
        self.count += 1
        return os.path.join(self.work, f"{self.count:02d}_{name}.png")

    def _seed(self) -> str:
        return str(self.rng.randint(1, 2**30))

    def noise(self, blur: float) -> str:
        """Soft cloudy noise, ``blur`` relative to a 512 px tile."""
        out = self.path("noise")
        self.im.run(["-size", f"{self.n}x{self.n}", "xc:gray50", "-seed", self._seed(), "+noise", "Random",
                     "-channel", "G", "-separate", "+channel", "-virtual-pixel", "tile",
                     "-blur", f"0x{blur * self.n / 512:.2f}", "-auto-level", f"PNG8:{out}"])
        return out

    def brushed(self) -> str:
        out = self.path("brushed")
        self.im.run(["-size", f"{self.n}x{self.n}", "xc:gray50", "-seed", self._seed(), "+noise", "Random",
                     "-channel", "G", "-separate", "+channel", "-virtual-pixel", "tile",
                     "-motion-blur", f"0x{self.n * 0.08:.1f}+0", "-auto-level", "-level", "25%,75%", f"PNG8:{out}"])
        return out

    def scratches(self, count: int, length: float, angle_spread: float = 180.0) -> str:
        """White hairline scratches on black; every line is also drawn shifted by the tile size (wraps)."""
        out = self.path("scratches")
        n = self.n
        draws: List[str] = []
        base_angle = self.rng.uniform(0, 180)
        for _ in range(count):
            x, y = self.rng.uniform(0, n), self.rng.uniform(0, n)
            a = math.radians(base_angle + self.rng.uniform(-angle_spread / 2, angle_spread / 2))
            ln = n * length * self.rng.uniform(0.4, 1.0)
            x2, y2 = x + math.cos(a) * ln, y + math.sin(a) * ln
            for dx in (-n, 0, n):
                for dy in (-n, 0, n):
                    draws.append(f"line {x + dx:.1f},{y + dy:.1f} {x2 + dx:.1f},{y2 + dy:.1f}")
        self.im.run(["-size", f"{n}x{n}", "xc:black", "-stroke", "white", "-strokewidth", f"{max(1, n // 512)}",
                     "-draw", " ".join(draws), "-virtual-pixel", "tile", "-blur", "0x0.6", f"PNG8:{out}"])
        return out

    def combine(self, name: str, dst: str, src: str, a: float, b: float, c: float, d: float) -> str:
        """Per pixel ``a*src*dst + b*src + c*dst + d`` (fast replacement for -fx)."""
        out = self.path(name)
        self.im.run([dst, src, "-compose", "Mathematics", "-define", f"compose:args={a},{b},{c},{d}",
                     "-composite", "-colorspace", "gray", f"PNG8:{out}"])
        return out

    def grooves(self, period: int, width: float) -> str:
        """1 inside panels, 0 in the grooves between them (periodic, so it tiles)."""
        n, g = self.n, max(1, int(round(width)))
        rects = []
        for k in range(0, n // period + 1):
            c = k * period
            rects.append(f"rectangle {c - g},0 {c + g - 1},{n}")
            rects.append(f"rectangle 0,{c - g} {n},{c + g - 1}")
        out = self.path("grooves")
        self.im.run(["-size", f"{n}x{n}", "xc:white", "-fill", "black", "-draw", " ".join(rects), f"PNG8:{out}"])
        return out

    def rivets(self, period: int, inset: float, radius: float) -> str:
        """Domed rivets near every panel corner."""
        n = self.n
        circles = []
        for k in range(n // period):
            for m in range(n // period):
                for cx in (k * period + inset, (k + 1) * period - inset):
                    for cy in (m * period + inset, (m + 1) * period - inset):
                        circles.append(f"circle {cx:.1f},{cy:.1f} {cx + radius:.1f},{cy:.1f}")
        out = self.path("rivets")
        self.im.run(["-size", f"{n}x{n}", "xc:black", "-fill", "white", "-draw", " ".join(circles),
                     "-virtual-pixel", "tile", "-blur", f"0x{radius * 0.45:.2f}", "-auto-level", f"PNG8:{out}"])
        return out

    def diamond(self, cell: int) -> str:
        """Checker plate: elongated bumps alternating +-45 degrees, one per cell."""
        n = self.n
        shapes = []
        for k in range(n // cell):
            for m in range(n // cell):
                angle = 45 if (k + m) % 2 == 0 else -45
                cx, cy = (k + 0.5) * cell, (m + 0.5) * cell
                shapes.append(f"push graphic-context translate {cx:.1f},{cy:.1f} rotate {angle} "
                              f"ellipse 0,0 {cell * 0.33:.1f},{cell * 0.08:.1f} 0,360 pop graphic-context")
        out = self.path("diamond")
        self.im.run(["-size", f"{n}x{n}", "xc:black", "-fill", "white", "-draw", " ".join(shapes),
                     "-virtual-pixel", "tile", "-blur", f"0x{cell * 0.04:.2f}", "-auto-level", f"PNG8:{out}"])
        return out

    def threshold(self, src: str, percent: float) -> str:
        out = self.path("mask")
        self.im.run([src, "-threshold", f"{percent:.1f}%", f"PNG8:{out}"])
        return out


def _normal_from_height(im: ImageMagick, height: str, out: str, strength: float) -> None:
    """Sobel derivatives of the (tileable) height map -> tangent-space normal map (Y+ = up, Unity/OpenGL)."""
    scale = f"{50.0 * strength:.0f}%!"
    im.run([height, "-colorspace", "gray", "-virtual-pixel", "tile",
            "(", "-clone", "0", "-define", f"convolve:scale={scale}", "-bias", "50%", "-morphology", "Convolve",
            "Sobel:0", "-negate", ")",
            "(", "-clone", "0", "-define", f"convolve:scale={scale}", "-bias", "50%", "-morphology", "Convolve",
            "Sobel:90", ")",
            "(", "-clone", "0", "-fill", "white", "-colorize", "100", ")",
            "-delete", "0", "-set", "colorspace", "sRGB", "-combine", "-depth", "8", f"PNG24:{out}"])


def build_material_texture(im: ImageMagick, material: str, out_dir: str, name: str, size: int, seed: int) -> Dict:
    """Generate all maps of one textured material."""
    recipe = RECIPES[material]
    color, smoothness, metallic, _ = MATERIALS[material]
    rough = 1.0 - smoothness
    rng = StableRandom(f"{seed}:{material}")
    n = size
    paths = {k: os.path.join(out_dir, f"{name}_{k}.png") for k in ("Albedo", "Normal", "Roughness",
                                                                      "MetallicSmoothness")}
    with tempfile.TemporaryDirectory(prefix="cubegen_tex_") as work:
        L = _Layers(im, work, n, rng)
        grime = L.noise(blur=rng.uniform(14, 22))
        fine = L.noise(blur=1.2)
        light_mask = dark_mask = None
        strength = 2.0
        if recipe == "brushed":
            base = L.brushed()
            scr = L.scratches(rng.randint(10, 22), 0.25, angle_spread=60)
            height = L.combine("h", base, scr, 0, -0.4, 0.25, 0.375)
            shade = L.combine("s", base, grime, 0, 0.06, 0.22, 0.74)
            light_mask, strength = scr, 1.0
        elif recipe in ("panels", "plating", "coated", "painted"):
            period = {"panels": rng.choice([n // 2, n]), "plating": n, "coated": n, "painted": n}[recipe]
            groove = L.grooves(period, max(1.5, n / (170 if recipe == "panels" else 260)))
            if recipe == "panels":
                riv = L.rivets(period, period * 0.07, n / 90)
                height = L.combine("h", L.combine("h0", groove, riv, 0, 0.35, 0.45, 0.06), fine, 0, 0.04, 1, 0)
            else:
                height = L.combine("h", groove, fine, 0, 0.04, 0.45, 0.08)
            if recipe == "panels":
                shade = L.combine("s", groove, grime, 0.07, 0.13, 0.273, 0.507)
            else:  # light / painted surfaces: less cloudy grime
                shade = L.combine("s", groove, grime, 0.04, 0.07, 0.26, 0.65)
            if recipe in ("coated", "painted"):
                light_mask = L.scratches(rng.randint(6, 14), 0.12)
            strength = 2.5
        elif recipe == "diamond":
            plate = L.diamond(n // 8)
            height = L.combine("h", plate, fine, 0, 0.04, 0.5, 0.38)
            shade = L.combine("s", plate, grime, 0.06, 0.16, 0.24, 0.64)
            strength = 3.0
        else:  # chipped paint
            chips = L.threshold(L.noise(blur=rng.uniform(5.0, 8.0)), rng.uniform(74, 82))
            height = L.combine("h", chips, fine, 0, 0.04, -0.25, 0.53)
            shade = L.combine("s", grime, grime, 0, 0, 0.12, 0.86)
            dark_mask = chips
            strength = 1.5

        # albedo = colour x shade (+ bare metal in chips, + bright scratches)
        args = ["-size", f"{n}x{n}", f"xc:{to_hex(material)}", shade, "-compose", "Multiply", "-composite"]
        if dark_mask:
            args += ["(", "-size", f"{n}x{n}", f"xc:{BARE_METAL}", ")", dark_mask, "-compose", "Over", "-composite"]
        if light_mask:
            args += ["(", "-size", f"{n}x{n}", "xc:#c9ced6", light_mask, "-alpha", "off", "-compose", "CopyOpacity",
                     "-composite", ")", "-compose", "Over", "-composite"]
        im.run(args + ["-depth", "8", f"PNG24:{paths['Albedo']}"])

        _normal_from_height(im, height, paths["Normal"], strength)

        # roughness: base value, rougher where grimy, smoother on scratches
        r_lo, r_hi = max(0.0, rough - 0.12), min(1.0, rough + 0.12)
        rough_map = L.combine("r", grime, grime, 0, 0, r_hi - r_lo, r_lo)
        if light_mask:
            rough_map = L.combine("r2", rough_map, light_mask, -0.5, 0, 1, 0)
        im.run([rough_map, "-colorspace", "gray", f"PNG8:{paths['Roughness']}"])

        # Unity: R = metallic, A = smoothness
        im.run(["-size", f"{n}x{n}", f"xc:gray({metallic * 100:.0f}%)", "(", paths["Roughness"], "-negate", ")",
                "-alpha", "off", "-compose", "CopyOpacity", "-composite", f"PNG32:{paths['MetallicSmoothness']}"])

    return {
        "name": name,
        "base": material,
        "recipe": recipe,
        "color": list(color),
        "metallic": metallic,
        "smoothness": smoothness,
        "tile_m": 1.0,
        "maps": {k: os.path.basename(v) for k, v in paths.items()},
        "paths": paths,
    }


def build_texture_set(im: ImageMagick, out_dir: str, size: int = 512, texture_set: str = "",
                      seed: Optional[int] = None, log=print) -> Dict[str, Dict]:
    """All textured materials -> ``{plain material: info}`` + ``CubeEscape_Textures.json`` in ``out_dir``."""
    from .seeds import parse_seed

    os.makedirs(out_dir, exist_ok=True)
    seed = parse_seed(texture_set or "default") if seed is None else seed
    result = {}
    for material in RECIPES:
        name = textured_name(material, texture_set)
        result[material] = build_material_texture(im, material, out_dir, name, size, seed)
    manifest = {
        "textureSet": texture_set or "default",
        "seed": seed,
        "size": size,
        "uv": "box projection, 1 UV unit = 1 m, one tile per metre",
        "note": "Unity: create a material per entry (Albedo -> base map, Normal -> normal map, "
                "MetallicSmoothness -> metallic map with smoothness from alpha), tiling 1/1.",
        "materials": [{k: v for k, v in info.items() if k != "paths"} for info in result.values()],
    }
    with open(os.path.join(out_dir, "CubeEscape_Textures.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"textures ({len(result)} materials, {size}px) -> {out_dir}")
    return result
