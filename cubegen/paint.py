"""Paint schemes (experimental, 0.17.0 "Prism"): the robot generator's skin principle for environment models.

A model is baked once, neutrally (``stylebake.bake_masks``): weight maps for its game materials (three per RGB image -
anti-aliased edges mix the weights, so every material boundary stays exact), ambient occlusion, an edge mask and an
"up" mask. A paint scheme is data only - a colour per game material, wear, grime, dust and edge glow - and is composed
from those maps without baking again (``compose``): colour = sum(weight x scheme colour), darkened in crevices, lighter
on worn edges. Any number of schemes costs one bake.

The game materials (``M_*``) keep their meaning; glow and status parts are separate objects with their own material
(the game's scripts switch them) and take the scheme's ``glow`` style colour instead.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .materials import MATERIALS

RGB = Tuple[float, float, float]

#: materials the weight maps cover: everything a scheme recolours (not glow/status, crystal or glass - they keep
#: their own plain material, like ``--textures baked``)
PAINTED = ("M_Ground", "M_Wall", "M_Platform", "M_HazardOrange", "M_RobotBody", "M_RobotDark", "M_Metal",
           "M_Warning", "M_PortalPanel")


def hex_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


#: paint schemes - colours as sRGB hex (as painted), the rest 0..1
PAINTS: Dict[str, Dict] = {
    # orange-accented steel (insets orange like the concept's industrial wall), heavy wear: bright scratched edges, grime in the crevices, a little dust on top
    "industrial": {
        "label": "Industrial",
        "colors": {"M_Ground": "#c8731f", "M_Wall": "#474c55", "M_Platform": "#7d828b", "M_HazardOrange": "#e8862a",
                   "M_RobotBody": "#b8bcc3", "M_RobotDark": "#23262c", "M_Metal": "#62676f", "M_Warning": "#f0a030",
                   "M_PortalPanel": "#9aa0a8"},
        "glow": "orange", "wear": 0.65, "wear_color": "#d5d9df", "grime": 0.55, "dust": 0.25,
        "dust_color": "#6f6553", "edge_glow": 0.0, "edge_glow_color": "#000000", "roughness": 0.62,
    },
    # cold slate and steel blue, little wear, edges glowing faintly in the crystal light
    "crystal": {
        "label": "Crystal",
        "colors": {"M_Ground": "#1f2530", "M_Wall": "#2b3442", "M_Platform": "#56677f", "M_HazardOrange": "#2f7fd8",
                   "M_RobotBody": "#a7b6c9", "M_RobotDark": "#181d27", "M_Metal": "#46546a", "M_Warning": "#4fc3ff",
                   "M_PortalPanel": "#8fa4bd"},
        "glow": "cyan", "wear": 0.25, "wear_color": "#9fd8ff", "grime": 0.3, "dust": 0.0,
        "dust_color": "#000000", "edge_glow": 0.35, "edge_glow_color": "#4fc3ff", "roughness": 0.4,
    },
}


def paint_names() -> List[str]:
    return sorted(PAINTS)


def check_paint(name: str) -> str:
    if name not in PAINTS:
        raise ValueError(f"unknown paint scheme {name!r} (known: {', '.join(paint_names())})")
    return name


def weight_layout(materials: Sequence[str]) -> List[Tuple[str, ...]]:
    """The painted materials of a model in groups of three: one RGB weight image per group (R, G, B)."""
    used = [m for m in PAINTED if m in materials]
    return [tuple(used[i:i + 3]) for i in range(0, len(used), 3)]


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_colors(paint: str) -> Dict[str, RGB]:
    """Scheme colours in linear space (composition and Unity work in linear); unknown materials keep the game's."""
    scheme = PAINTS[check_paint(paint)]
    out = {}
    for name in PAINTED:
        rgb = hex_rgb(scheme["colors"][name]) if name in scheme["colors"] else MATERIALS[name][0]
        out[name] = tuple(srgb_to_linear(c) for c in rgb)  # type: ignore[assignment]
    return out


def detail_map(weights: Sequence, layout: Sequence[Tuple[str, ...]], diffuse):
    """Surface detail independent of any scheme: the tile textures' brightness (grooves, rivets, scratches) relative
    to the flat game colour under the same weights - 1 = plain, < 1 darker, > 1 lighter."""
    import numpy as np

    def lum(rgb):
        return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]

    flat = np.zeros(diffuse.shape[:2], dtype=np.float32)
    for image, group in zip(weights, layout):
        for channel, name in enumerate(group):
            color = np.asarray([srgb_to_linear(c) for c in MATERIALS[name][0]], dtype=np.float32)
            flat += image[..., channel] * float(lum(color))
    return np.clip(lum(diffuse) / np.maximum(flat, 1e-3), 0.35, 1.8)


def compose(weights: Sequence, layout: Sequence[Tuple[str, ...]], ao, edge, up, noise, paint: str, detail=None):
    """Albedo (linear RGB) and emission (linear RGB) of one paint scheme from the neutral maps (numpy arrays,
    H x W x 3 for weights, H x W for the masks, the 0..1 noise and the optional ``detail_map``). Pure arithmetic: the
    same maps and scheme give the same pixels on every machine."""
    import numpy as np

    scheme = PAINTS[check_paint(paint)]
    colors = linear_colors(paint)
    albedo = np.zeros(ao.shape + (3,), dtype=np.float32)
    covered = np.zeros(ao.shape, dtype=np.float32)
    for image, group in zip(weights, layout):
        for channel, name in enumerate(group):
            w = image[..., channel]
            albedo += w[..., None] * np.asarray(colors[name], dtype=np.float32)
            covered += w
    albedo /= np.maximum(covered, 1e-4)[..., None]  # weights may not sum to exactly 1 after 8-bit rounding
    if detail is not None:
        albedo *= detail[..., None]

    # grime: crevices darker, broken up by low-frequency noise
    crevice = np.clip(1.0 - ao, 0.0, 1.0)
    grime = 1.0 - scheme["grime"] * np.clip(crevice * 1.6 + (noise - 0.5) * 0.2, 0.0, 1.0)
    albedo *= grime[..., None]
    # dust on surfaces facing up
    dust = scheme["dust"] * np.clip(up * 1.3 - 0.3, 0.0, 1.0) * np.clip(noise * 1.4 - 0.2, 0.0, 1.0)
    dust_rgb = np.asarray([srgb_to_linear(c) for c in hex_rgb(scheme["dust_color"])], dtype=np.float32)
    albedo = albedo * (1.0 - dust[..., None]) + dust_rgb * dust[..., None]
    # worn edges: paint chipped off where the edge mask is strong and the noise allows it
    wear = scheme["wear"] * np.clip(edge * 1.8 - 0.15, 0.0, 1.0) * np.clip(noise * 1.6 - 0.25, 0.0, 1.0)
    wear_rgb = np.asarray([srgb_to_linear(c) for c in hex_rgb(scheme["wear_color"])], dtype=np.float32)
    albedo = albedo * (1.0 - wear[..., None]) + wear_rgb * wear[..., None]
    # faint glowing edges (crystal energy)
    glow_rgb = np.asarray([srgb_to_linear(c) for c in hex_rgb(scheme["edge_glow_color"])], dtype=np.float32)
    emission = (scheme["edge_glow"] * np.clip(edge * 2.0 - 0.2, 0.0, 1.0) * np.clip(covered, 0.0, 1.0))[..., None] \
        * glow_rgb
    return np.clip(albedo, 0.0, 1.0), np.clip(emission, 0.0, 1.0)
