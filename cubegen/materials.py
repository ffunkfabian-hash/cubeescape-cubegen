"""Cube Escape materials.

Names and values mirror ``Blender/Scripts/generate_assets.py`` of the game and
the Unity materials in ``Assets/Art/Materials`` - Unity remaps imported FBX
materials by name, so generated assets pick up the real game materials.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# name: (sRGB colour, smoothness like in Unity, metallic, emission strength or None)
MATERIALS: Dict[str, Tuple[Tuple[float, float, float], float, float, Optional[float]]] = {
    "M_Ground":       ((0.16, 0.18, 0.23), 0.35, 0.0, None),
    "M_Wall":         ((0.24, 0.27, 0.34), 0.40, 0.0, None),
    "M_Platform":     ((0.85, 0.87, 0.92), 0.50, 0.0, None),
    "M_HazardOrange": ((1.00, 0.45, 0.10), 0.40, 0.0, None),
    "M_RobotBody":    ((0.92, 0.93, 0.96), 0.60, 0.1, None),
    "M_RobotDark":    ((0.12, 0.13, 0.16), 0.50, 0.3, None),
    "M_GlowCyan":     ((0.10, 0.85, 1.00), 0.80, 0.0, 4.0),
    "M_GlowRed":      ((1.00, 0.16, 0.10), 0.80, 0.0, 1.5),
    "M_GlowOrange":   ((1.00, 0.26, 0.03), 0.80, 0.0, 1.15),
    "M_Crystal":      ((0.30, 0.90, 1.00), 0.90, 0.0, 2.5),
    "M_Metal":        ((0.42, 0.46, 0.52), 0.55, 0.6, None),
    "M_Warning":      ((0.95, 0.74, 0.12), 0.35, 0.0, None),
    "M_PortalPanel":  ((0.78, 0.82, 0.86), 0.25, 0.0, None),
    "M_Glass":        ((0.45, 0.70, 0.85), 0.90, 0.0, None),
}

GLOW_MATERIALS = ("M_GlowCyan", "M_GlowRed", "M_GlowOrange")


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_hex(name: str) -> str:
    r, g, b = MATERIALS[name][0]
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def check_material(name: str) -> str:
    if name not in MATERIALS:
        raise KeyError(f"unknown material {name!r}; known: {', '.join(MATERIALS)}")
    return name
