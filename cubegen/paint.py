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


#: paint schemes - colours as sRGB hex (as painted), amounts 0..1. The six wall concepts of the user's concept sheet
#: "Cube Escape - Umgebungs Konzepte" (01 Industrial ... 06 Organic). Keys: see ``SCHEME_KEYS``.
PAINTS: Dict[str, Dict] = {
    # orange-accented steel, heavy wear, grime, a little dust
    "industrial": {
        "label": "Industrial",
        "colors": {"M_Ground": "#3a3d42", "M_Wall": "#3a3e45", "M_Platform": "#7d828b", "M_HazardOrange": "#e8862a",
                   "M_RobotBody": "#b8bcc3", "M_RobotDark": "#2a2d33", "M_Metal": "#8a9099", "M_Warning": "#f0a030",
                   "M_PortalPanel": "#9aa0a8"},
        "glow": "orange", "edge_light": 0.2, "wear": 0.75, "wear_color": "#d5d9df", "grime": 0.55,
        "grime_color": "#1a1712", "rising_grime": 0.5, "dust": 0.25, "dust_color": "#6f6553", "moss": 0.0,
        "moss_color": "#000000", "edge_glow": 0.0, "edge_glow_color": "#000000", "roughness": 0.62, "metal": 1.0,
    },
    # white lab panels, light grey frames, blue light: clean, glossy, hardly worn
    "clean": {
        "label": "Clean",
        "colors": {"M_Ground": "#d8dde4", "M_Wall": "#c9ced6", "M_Platform": "#e4e8ee", "M_HazardOrange": "#3d8ee0",
                   "M_RobotBody": "#f0f2f5", "M_RobotDark": "#8d949e", "M_Metal": "#e2e6ec", "M_Warning": "#7cc4f5",
                   "M_PortalPanel": "#eef1f5"},
        "glow": "cyan", "edge_light": 0.15, "wear": 0.08, "wear_color": "#ffffff", "grime": 0.18,
        "grime_color": "#4a5260", "rising_grime": 0.1, "dust": 0.0, "dust_color": "#000000", "moss": 0.0,
        "moss_color": "#000000", "edge_glow": 0.0, "edge_glow_color": "#000000", "roughness": 0.32, "metal": 0.3,
    },
    # worn brown and rust, chipped to bare metal, rust in the crevices
    "ruin": {
        "label": "Ruin",
        "colors": {"M_Ground": "#5a4b3c", "M_Wall": "#5a4d40", "M_Platform": "#6e6255", "M_HazardOrange": "#a0612c",
                   "M_RobotBody": "#8a7f70", "M_RobotDark": "#2e2822", "M_Metal": "#7d6a55", "M_Warning": "#b8892f",
                   "M_PortalPanel": "#8a8070"},
        "glow": "orange", "edge_light": 0.1, "wear": 0.9, "wear_color": "#a8a39a", "grime": 0.7,
        "grime_color": "#5a2e14", "rising_grime": 0.65, "dust": 0.35, "dust_color": "#7a6a52", "moss": 0.0,
        "moss_color": "#000000", "edge_glow": 0.0, "edge_glow_color": "#000000", "roughness": 0.85, "metal": 0.6,
    },
    # cold slate and steel blue, little wear, edges glowing faintly in the crystal light
    "crystal": {
        "label": "Crystal",
        "colors": {"M_Ground": "#1f2530", "M_Wall": "#2b3442", "M_Platform": "#56677f", "M_HazardOrange": "#2f7fd8",
                   "M_RobotBody": "#a7b6c9", "M_RobotDark": "#181d27", "M_Metal": "#46546a", "M_Warning": "#4fc3ff",
                   "M_PortalPanel": "#8fa4bd"},
        "glow": "cyan", "edge_light": 0.1, "wear": 0.25, "wear_color": "#9fd8ff", "grime": 0.3,
        "grime_color": "#0b1018", "rising_grime": 0.15, "dust": 0.0, "dust_color": "#000000", "moss": 0.0,
        "moss_color": "#000000", "edge_glow": 0.35, "edge_glow_color": "#4fc3ff", "roughness": 0.4, "metal": 1.0,
    },
    # near black, red light, a red seam glowing along the edges - secret / danger
    "dark": {
        "label": "Dark",
        "colors": {"M_Ground": "#16161b", "M_Wall": "#1c1c22", "M_Platform": "#2c2c33", "M_HazardOrange": "#8e1b22",
                   "M_RobotBody": "#3a3a42", "M_RobotDark": "#101014", "M_Metal": "#2e2e36", "M_Warning": "#c0282e",
                   "M_PortalPanel": "#33333b"},
        "glow": "red", "edge_light": 0.08, "wear": 0.2, "wear_color": "#5a5a66", "grime": 0.4,
        "grime_color": "#050507", "rising_grime": 0.3, "dust": 0.0, "dust_color": "#000000", "moss": 0.0,
        "moss_color": "#000000", "edge_glow": 0.06, "edge_glow_color": "#ff2a35", "roughness": 0.5, "metal": 0.8,
    },
    # mossy stone grey, overgrown from the top and from the floor, damp and dirty
    "organic": {
        "label": "Organic",
        "colors": {"M_Ground": "#4f5a46", "M_Wall": "#5d625c", "M_Platform": "#6c7068", "M_HazardOrange": "#6f7a3a",
                   "M_RobotBody": "#80857c", "M_RobotDark": "#2d302b", "M_Metal": "#6a6e66", "M_Warning": "#8a8f3c",
                   "M_PortalPanel": "#787d74"},
        "glow": "cyan", "edge_light": 0.1, "wear": 0.35, "wear_color": "#8c9088", "grime": 0.6,
        "grime_color": "#1d2414", "rising_grime": 0.5, "dust": 0.0, "dust_color": "#000000", "moss": 1.0,
        "moss_color": "#4f7a25", "edge_glow": 0.0, "edge_glow_color": "#000000", "roughness": 0.8, "metal": 0.3,
    },
    # concept sheets II/III (07 Sand, 08 Space, Ice, Toxic, Void): sandstone, dust everywhere, sand rising from the floor
    "sand": {
        "label": "Sand",
        "colors": {"M_Ground": "#c49a62", "M_Wall": "#b8925e", "M_Platform": "#d2b48a", "M_HazardOrange": "#c47a2c",
                   "M_RobotBody": "#d8c4a0", "M_RobotDark": "#6e5638", "M_Metal": "#a88a62", "M_Warning": "#d89a3a",
                   "M_PortalPanel": "#cdb48e"},
        "glow": "orange", "edge_light": 0.25, "wear": 0.7, "wear_color": "#e8d8b8", "grime": 0.35,
        "grime_color": "#6a4a28", "rising_grime": 0.0, "dust": 0.7, "dust_color": "#e0c48e", "moss": 0.6,
        "moss_color": "#d8b880", "edge_glow": 0.0, "edge_glow_color": "#000000", "roughness": 0.9, "metal": 0.2,
    },
    # dark navy-grey hull plating, orange trims, blue light: clean and glossy
    "space": {
        "label": "Space",
        "colors": {"M_Ground": "#2a3140", "M_Wall": "#2a3140", "M_Platform": "#4a5568", "M_HazardOrange": "#e8862a",
                   "M_RobotBody": "#8c97a8", "M_RobotDark": "#1a1f2a", "M_Metal": "#5a6578", "M_Warning": "#f0a030",
                   "M_PortalPanel": "#6e7a8e"},
        "glow": "cyan", "edge_light": 0.18, "wear": 0.2, "wear_color": "#c8d0dc", "grime": 0.25,
        "grime_color": "#0a0d14", "rising_grime": 0.1, "dust": 0.0, "dust_color": "#000000", "moss": 0.0,
        "moss_color": "#000000", "edge_glow": 0.04, "edge_glow_color": "#4fc3ff", "roughness": 0.35, "metal": 1.0,
    },
    # pale ice blue and white, snow on top surfaces, faint frost at the edges
    "ice": {
        "label": "Ice",
        "colors": {"M_Ground": "#c8dcea", "M_Wall": "#b8d6e8", "M_Platform": "#dcecf6", "M_HazardOrange": "#4aa8e0",
                   "M_RobotBody": "#e8f2f8", "M_RobotDark": "#5a7a92", "M_Metal": "#a8c4d8", "M_Warning": "#8fd4ff",
                   "M_PortalPanel": "#d0e4f0"},
        "glow": "cyan", "edge_light": 0.3, "wear": 0.15, "wear_color": "#ffffff", "grime": 0.2,
        "grime_color": "#3a5a72", "rising_grime": 0.0, "dust": 0.8, "dust_color": "#f4f8fc", "moss": 0.5,
        "moss_color": "#eef6fc", "edge_glow": 0.1, "edge_glow_color": "#bfe8ff", "roughness": 0.25, "metal": 0.3,
    },
    # dark grey, poison green slime rising from the floor, green glowing seams
    "toxic": {
        "label": "Toxic",
        "colors": {"M_Ground": "#2c3128", "M_Wall": "#33382e", "M_Platform": "#4a5044", "M_HazardOrange": "#6aa82a",
                   "M_RobotBody": "#6a7062", "M_RobotDark": "#1c2018", "M_Metal": "#4e5548", "M_Warning": "#b8e030",
                   "M_PortalPanel": "#5a6052"},
        "glow": "orange", "edge_light": 0.08, "wear": 0.4, "wear_color": "#8a9280", "grime": 0.6,
        "grime_color": "#1a2a08", "rising_grime": 0.6, "dust": 0.0, "dust_color": "#000000", "moss": 0.35,
        "moss_color": "#2f6a18", "edge_glow": 0.12, "edge_glow_color": "#5cff3a", "roughness": 0.55, "metal": 0.6,
    },
    # black violet, violet light in the seams - a place outside the station
    "void": {
        "label": "Void",
        "colors": {"M_Ground": "#1a1424", "M_Wall": "#1e1828", "M_Platform": "#2c2438", "M_HazardOrange": "#7a3ac8",
                   "M_RobotBody": "#3c3448", "M_RobotDark": "#100c16", "M_Metal": "#2a2236", "M_Warning": "#a35cff",
                   "M_PortalPanel": "#342c40"},
        "glow": "cyan", "edge_light": 0.06, "wear": 0.15, "wear_color": "#5a4a70", "grime": 0.35,
        "grime_color": "#050308", "rising_grime": 0.3, "dust": 0.0, "dust_color": "#000000", "moss": 0.0,
        "moss_color": "#000000", "edge_glow": 0.1, "edge_glow_color": "#a35cff", "roughness": 0.45, "metal": 0.8,
    },
}

SCHEME_KEYS = ("label", "colors", "glow", "edge_light", "wear", "wear_color", "grime", "grime_color", "rising_grime",
               "dust", "dust_color", "moss", "moss_color", "edge_glow", "edge_glow_color", "roughness", "metal")


BUILTIN_PAINTS = tuple(PAINTS)
GLOW_COLORS = ("cyan", "red", "orange")  # the --glow colours of the glow parts
AMOUNT_KEYS = ("edge_light", "wear", "grime", "rising_grime", "dust", "moss", "edge_glow", "roughness", "metal")
COLOR_KEYS = ("wear_color", "grime_color", "dust_color", "moss_color", "edge_glow_color")


def _check_hex(value, where):
    if not (isinstance(value, str) and len(value) == 7 and value[0] == "#"
            and all(c in "0123456789abcdefABCDEF" for c in value[1:])):
        raise ValueError(f"{where}: colour must be '#rrggbb', got {value!r}")


def check_scheme(scheme: Dict, where: str = "paint scheme") -> Dict:
    """Validate a complete scheme (all ``SCHEME_KEYS``); returns it."""
    missing = [k for k in SCHEME_KEYS if k not in scheme]
    unknown = [k for k in scheme if k not in SCHEME_KEYS]
    if missing or unknown:
        raise ValueError(f"{where}: missing keys {missing}, unknown keys {unknown}")
    if not isinstance(scheme["label"], str) or not scheme["label"].strip():
        raise ValueError(f"{where}: label must be a text")
    if scheme["glow"] not in GLOW_COLORS:
        raise ValueError(f"{where}: glow must be one of {', '.join(GLOW_COLORS)}")
    for k in AMOUNT_KEYS:
        if not isinstance(scheme[k], (int, float)) or isinstance(scheme[k], bool) or not 0.0 <= scheme[k] <= 1.0:
            raise ValueError(f"{where}: {k} must be a number from 0 to 1")
    for k in COLOR_KEYS:
        _check_hex(scheme[k], f"{where}: {k}")
    if not isinstance(scheme["colors"], dict):
        raise ValueError(f"{where}: colors must be an object {{material: '#rrggbb'}}")
    if set(scheme["colors"]) - set(PAINTED):
        raise ValueError(f"{where}: colors only for {', '.join(PAINTED)}")
    for name, value in scheme["colors"].items():
        _check_hex(value, f"{where}: colors.{name}")
    return scheme


def load_scheme(path: str):
    """A custom paint scheme from a JSON file: ``{"name", "base", ...}`` - every key not given comes from the built-in
    scheme ``base`` (default industrial; ``colors`` are merged per material). Returns ``(name, scheme)``."""
    import json
    import os

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: a paint scheme is a JSON object")
    name = str(data.pop("name", os.path.splitext(os.path.basename(path))[0])).strip().lower()
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"{path}: name: letters, digits and _ only")
    if name in BUILTIN_PAINTS:
        raise ValueError(f"{path}: {name!r} is a built-in scheme - give the custom one its own name")
    base = data.pop("base", "industrial")
    if base not in BUILTIN_PAINTS:
        raise ValueError(f"{path}: base must be a built-in scheme ({', '.join(BUILTIN_PAINTS)})")
    scheme = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PAINTS[base].items()}
    scheme["label"] = name.capitalize()
    for key, value in data.items():
        if key == "colors" and isinstance(value, dict):
            scheme["colors"].update(value)
        else:
            scheme[key] = value
    return name, check_scheme(scheme, path)


def register_scheme(name: str, scheme: Dict) -> None:
    """Make a custom scheme known in this process (the Blender worker gets it with the job)."""
    if name in BUILTIN_PAINTS:
        raise ValueError(f"{name!r} is a built-in scheme")
    PAINTS[name] = check_scheme(scheme, name)


def paint_names() -> List[str]:
    return sorted(BUILTIN_PAINTS)


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


def _lin(hex_color: str):
    import numpy as np

    return np.asarray([srgb_to_linear(c) for c in hex_rgb(hex_color)], dtype=np.float32)


def compose(weights: Sequence, layout: Sequence[Tuple[str, ...]], ao, edge, up, noise, paint: str, detail=None,
            height=None) -> Dict:
    """One paint scheme from the neutral maps (numpy arrays: H x W x 3 weights, H x W masks, 0..1 noise, optional
    ``detail_map`` and height): ``{"albedo", "emission"}`` (linear RGB) and ``{"roughness", "metallic"}`` (0..1).
    Pure arithmetic: the same maps and scheme give the same pixels on every machine."""
    import numpy as np

    scheme = PAINTS[check_paint(paint)]
    colors = linear_colors(paint)
    albedo = np.zeros(ao.shape + (3,), dtype=np.float32)
    covered = np.zeros(ao.shape, dtype=np.float32)
    metallic = np.zeros(ao.shape, dtype=np.float32)
    for image, group in zip(weights, layout):
        for channel, name in enumerate(group):
            w = image[..., channel]
            albedo += w[..., None] * np.asarray(colors[name], dtype=np.float32)
            metallic += w * MATERIALS[name][2]
            covered += w
    albedo /= np.maximum(covered, 1e-4)[..., None]  # weights may not sum to exactly 1 after 8-bit rounding
    metallic = metallic / np.maximum(covered, 1e-4) * scheme["metal"]
    if detail is not None:
        albedo *= detail[..., None]
    roughness = np.full(ao.shape, scheme["roughness"], dtype=np.float32)

    def blend(amount, hex_color):
        nonlocal albedo
        albedo = albedo * (1.0 - amount[..., None]) + _lin(hex_color) * amount[..., None]

    # grime: crevices darker and tinted, broken up by noise; rougher there
    crevice = np.clip(1.0 - ao, 0.0, 1.0)
    grime = scheme["grime"] * np.clip(crevice * 1.6 + (noise - 0.5) * 0.2, 0.0, 1.0)
    blend(grime * 0.75, scheme["grime_color"])
    roughness += grime * 0.25
    if height is not None:  # dirt rising from the floor (0 at the model's foot, 1 at its top)
        rising = scheme["rising_grime"] * np.clip((0.45 - height) / 0.45, 0.0, 1.0) ** 1.5 \
            * np.clip(0.55 + noise * 0.7, 0.0, 1.0)
        blend(rising * 0.8, scheme["grime_color"])
    # dust on surfaces facing up
    # (in patches: a floor or a platform top must not vanish under one closed layer of dust, sand or snow)
    dust = scheme["dust"] * np.clip(up * 1.3 - 0.3, 0.0, 1.0) * np.clip(noise * 2.2 - 0.9, 0.0, 1.0)
    blend(dust, scheme["dust_color"])
    # moss: on top surfaces, creeping down from the top edge and up from the floor in noisy patches
    if scheme["moss"] > 0:
        top = np.clip((height - 0.7) / 0.3, 0.0, 1.0) if height is not None else 0.0
        foot = np.clip((0.25 - height) / 0.25, 0.0, 1.0) if height is not None else 0.0
        # hanging down from the top: the higher, the more; plus patches anywhere the noise is high
        hang = np.clip((height - 0.35) / 0.65, 0.0, 1.0) ** 1.5 if height is not None else 0.0
        patches = np.clip(noise * 2.0 - 0.55, 0.0, 1.0)  # top surfaces only in patches, never a closed carpet
        broken = 0.4 + 0.6 * patches  # the top band and the foot too: a box top must not turn into one green lid
        reach = np.clip(up * 1.4 * patches + (top * 0.9 + foot * 0.7 + hang * 0.55) * broken + crevice * 0.6
                        + (noise - 0.6) * 0.8, 0.0, 1.0)
        moss = scheme["moss"] * np.clip((reach * (0.45 + noise) - 0.42) * 3.0, 0.0, 1.0)
        blend(moss, scheme["moss_color"])
        roughness = roughness * (1.0 - moss) + moss * 0.95
        metallic *= 1.0 - moss
    # painted edge light: every edge a little lighter (the concept's drawn highlights), before the wear
    light = scheme["edge_light"] * np.clip(edge * 2.2 - 0.1, 0.0, 1.0)
    albedo = albedo + (1.0 - albedo) * light[..., None] * 0.6
    # worn edges: paint chipped off to bare material - smoother and more metallic there
    wear = scheme["wear"] * np.clip(edge * 1.8 - 0.15, 0.0, 1.0) * np.clip(noise * 1.6 - 0.25, 0.0, 1.0)
    blend(wear, scheme["wear_color"])
    roughness = roughness * (1.0 - wear * 0.5)
    metallic = metallic + (1.0 - metallic) * wear * 0.6 * scheme["metal"]
    # glowing edges (crystal energy, dark red seams)
    emission = (scheme["edge_glow"] * np.clip(edge * 2.0 - 0.2, 0.0, 1.0) * np.clip(covered, 0.0, 1.0))[..., None] \
        * _lin(scheme["edge_glow_color"])
    return {"albedo": np.clip(albedo, 0.0, 1.0), "emission": np.clip(emission, 0.0, 1.0),
            "roughness": np.clip(roughness, 0.03, 1.0), "metallic": np.clip(metallic, 0.0, 1.0)}
