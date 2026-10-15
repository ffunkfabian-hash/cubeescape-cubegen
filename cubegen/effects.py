"""Effect materials as data (0.30.0, TECHNIK.md 7 / Robogen 11).

Glass, hologram, liquid, glow and the other materials that keep their own ``M_`` material in baked, paint and
palette mode (``materials.KEEP_OWN``) get a description that the manifest carries per model (``effects``): the kind of
effect, the values Cubegen gives the plain material (colour, smoothness, emission) and what the material is meant for.
It is a *description only*: the runtime effect (Fresnel, alpha, scrolling, pulsing) lives in Cube Escape; the numbers
here are exactly those of ``materials.MATERIALS``, so a viewer and the game can read the same values. Nothing is
invented that the game does not have; the sidecar and the contract are untouched (the effect block of the sidecar is
ROADMAP ToDo 28, together with Cube Escape).
"""

from __future__ import annotations

from typing import Dict, List

from .materials import CRYSTAL_SPLIT, GLOW_MATERIALS, KEEP_OWN, MATERIALS

EFFECT_FORMAT = 1

#: kind per material; everything in ``KEEP_OWN`` needs an entry (a test keeps the two in step)
KINDS = {
    **{name: "glow" for name in GLOW_MATERIALS},
    "M_Crystal": "crystal",
    "M_Glass": "glass",
    "M_Liquid": "liquid",
    "M_Hologram": "hologram",
    "M_Lamp": "emitter",
    "M_Leaf": "foliage",
    "M_Biolume": "emitter",
    "M_Signal": "emitter",
    "M_Accent": "emitter",
    "M_Optic": "optic",
}
#: what the material is for (the scripts of the game swap glow materials at runtime)
ROLES = {
    **{name: "status colour; the game's scripts swap it at runtime" for name in GLOW_MATERIALS},
    "M_Crystal": "real crystal only",
    "M_Glass": "transparent panes",
    **CRYSTAL_SPLIT,
}


def effect_of(name: str) -> Dict:
    """The description of one effect material (colour in sRGB 0..1)."""
    colour, smoothness, metallic, emission = MATERIALS[name]
    return {"material": name, "kind": KINDS[name], "role": ROLES[name],
            "color": [round(c, 4) for c in colour], "smoothness": smoothness, "metallic": metallic,
            "emission": emission}


def effects_table() -> List[Dict]:
    """Every effect material in ``KEEP_OWN`` order of ``MATERIALS``."""
    return [effect_of(name) for name in MATERIALS if name in KEEP_OWN]


def effects_of(asset) -> List[Dict]:
    """The effect materials the faces of ``asset`` use (empty for a model without any)."""
    used = {r for o in asset.meshes() for r in o.mesh.roles}
    return [effect_of(name) for name in MATERIALS if name in KEEP_OWN and name in used]
