"""Effect materials as data (0.30.0, TECHNIK.md 7 / Robogen 11).

Glass, hologram, liquid, glow and the other materials that keep their own ``M_`` material in baked, paint and
palette mode (``materials.KEEP_OWN``) get a description that the manifest carries per model (``effects``): the kind of
effect, the values Cubegen gives the plain material (colour, smoothness, emission) and what the material is meant for.
Since 0.30.0 (contract version 4) the description is also the sidecar's ``effects`` block. The base values (colour,
smoothness, metallic, emission) are exactly those of ``materials.MATERIALS``; ``params`` are Cubegen's *proposed*
parameters for the runtime effect (``KIND_PARAMS``: a flat set of numbers, flags and 2-vectors per kind) - Cube Escape
implements the effect (Fresnel, alpha, scrolling, pulsing, ...) and may restyle any value; what it must not do is read a
key the contract does not list (``contract.json`` section ``effects``).
"""

from __future__ import annotations

from typing import Dict, List

from .materials import CRYSTAL_SPLIT, GLOW_MATERIALS, KEEP_OWN, MATERIALS

EFFECT_FORMAT = 1

#: allowed parameter keys per kind and their type: "number", "bool" or "vec2" (the contract's section ``effects``)
KIND_PARAMS = {
    "glow": {"emissionIntensity": "number", "pulseAmount": "number", "pulseSpeed": "number"},
    "crystal": {"fresnelPower": "number", "alpha": "number", "emissionIntensity": "number", "sparkle": "number"},
    "glass": {"alpha": "number", "fresnelPower": "number", "doubleSided": "bool", "refraction": "number"},
    "liquid": {"alpha": "number", "scrollSpeed": "vec2", "waveAmplitude": "number", "waveFrequency": "number",
               "fresnelPower": "number"},
    "hologram": {"alpha": "number", "additive": "bool", "fresnelPower": "number", "scanlineFrequency": "number",
                 "scanlineSpeed": "number", "scanlineStrength": "number", "flicker": "number",
                 "emissionIntensity": "number"},
    "emitter": {"emissionIntensity": "number", "bloom": "bool", "pulseAmount": "number"},
    "optic": {"alpha": "number", "fresnelPower": "number", "refraction": "number", "dispersion": "number"},
    "foliage": {"translucency": "number", "swayAmplitude": "number", "swayFrequency": "number"},
}
#: the proposed values per kind; ``emissionIntensity`` follows ``MATERIALS`` (the glow materials differ), a material
#: may override single keys in ``MATERIAL_PARAMS``
KIND_DEFAULTS = {
    "glow": {"pulseAmount": 0.0, "pulseSpeed": 1.0},
    "crystal": {"fresnelPower": 3.0, "alpha": 0.9, "sparkle": 0.3},
    "glass": {"alpha": 0.3, "fresnelPower": 2.5, "doubleSided": True, "refraction": 0.0},
    "liquid": {"alpha": 0.75, "scrollSpeed": [0.03, 0.015], "waveAmplitude": 0.004, "waveFrequency": 3.0,
               "fresnelPower": 2.0},
    "hologram": {"alpha": 0.55, "additive": True, "fresnelPower": 3.0, "scanlineFrequency": 90.0,
                 "scanlineSpeed": 0.6, "scanlineStrength": 0.25, "flicker": 0.05},
    "emitter": {"bloom": True, "pulseAmount": 0.0},
    "optic": {"alpha": 0.6, "fresnelPower": 2.0, "refraction": 0.05, "dispersion": 0.02},
    "foliage": {"translucency": 0.25, "swayAmplitude": 0.01, "swayFrequency": 1.2},
}
MATERIAL_PARAMS = {"M_Biolume": {"pulseAmount": 0.2}}

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
            "emission": emission, "params": params_of(name)}


def params_of(name: str) -> Dict:
    """The proposed runtime parameters of an effect material (keys of ``KIND_PARAMS[kind]`` only)."""
    kind = KINDS[name]
    params = {k: (list(v) if isinstance(v, list) else v) for k, v in KIND_DEFAULTS[kind].items()}
    params.update(MATERIAL_PARAMS.get(name, {}))
    emission = MATERIALS[name][3]
    if "emissionIntensity" in KIND_PARAMS[kind] and emission is not None:
        params["emissionIntensity"] = emission
    return {k: params[k] for k in KIND_PARAMS[kind] if k in params}


def effects_table() -> List[Dict]:
    """Every effect material in ``KEEP_OWN`` order of ``MATERIALS``."""
    return [effect_of(name) for name in MATERIALS if name in KEEP_OWN]


def effects_of(asset) -> List[Dict]:
    """The effect materials the faces of ``asset`` use (empty for a model without any)."""
    used = {r for o in asset.meshes() for r in o.mesh.roles}
    return [effect_of(name) for name in MATERIALS if name in KEEP_OWN and name in used]
