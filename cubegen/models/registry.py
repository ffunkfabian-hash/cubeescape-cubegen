"""Registry of model types.

A model type is a function ``build(rng, asset)`` that adds named objects to
``asset``. Tunable values are read through ``asset.p`` (a
:class:`~cubegen.params.ParamReader`), which rolls them from ``rng`` and
applies parameter overrides and the global style. Register it with
:func:`model` and it is available on the command line and in the add-on.

Changing a builder later: never add, remove or reorder rolls from ``rng``,
existing seeds would look different (``tests/test_golden.py`` catches it).
Roll new details from their own stream: ``asset.sub("detail_name")``.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..asset import Asset
from ..materials import check_material
from ..params import DETAIL, Param, ParamReader, Style
from ..quality import fix_z_fighting
from ..seeds import StableRandom
from .anchors import add_anchors
from .destruction import damage_asset
from .wear import apply_wear

BuildFn = Callable[[random.Random, Asset], None]

#: faces of the bounding box (axis and side) a variant set compares - the faces where neighbours join
SET_FACES = ("x-", "x+", "y-", "y+", "z-", "z+")
#: default: a wall-like piece joins left/right, stands on the floor, reaches the same top and keeps its back; parts
#: may stick out to the front (-y) differently - that is the point of a set
WALL_FACES = ("x-", "x+", "z-", "z+", "y+")


class ModelType:
    def __init__(self, name: str, title: str, category: str, pivot: str, description: str, build: BuildFn,
                 params: Sequence[Param], view: str = "above", set_faces: Sequence[str] = WALL_FACES,
                 set_pins: Sequence[str] = ()):
        self.name = name          # CLI name, e.g. "server_rack"
        self.title = title        # asset name prefix in Unity, e.g. "ServerRack"
        self.category = category
        self.pivot = pivot        # floor | top | center | wall
        self.description = description
        self.build = build
        self.params = list(params)
        self.view = view          # above | below: preview / icon camera (below for ceiling pieces)
        self.set_faces = tuple(set_faces)  # --set: the bounding-box faces every member must share (SET_FACES)
        self.set_pins = tuple(set_pins)    # --set: parameters pinned besides the outline ones (e.g. a corner's style)

    def param(self, name: str) -> Param:
        for p in self.params:
            if p.name == name:
                return p
        raise KeyError(f"{self.name} has no parameter {name!r}; available: {', '.join(p.name for p in self.params)}")


REGISTRY: Dict[str, ModelType] = {}


def model(name: str, title: str, category: str, description: str, pivot: str = "floor",
          params: Sequence[Param] = (), view: str = "above", set_faces: Sequence[str] = WALL_FACES,
          set_pins: Sequence[str] = ()):
    """Decorator that registers a builder function as model type ``name``."""

    def deco(fn: BuildFn) -> BuildFn:
        if name in REGISTRY:
            raise ValueError(f"model type {name!r} registered twice")
        if view not in ("above", "below"):
            raise ValueError(f"model type {name!r}: view must be 'above' or 'below'")
        unknown = [f for f in set_faces if f not in SET_FACES]
        if unknown or not set_faces:
            raise ValueError(f"model type {name!r}: set_faces from {', '.join(SET_FACES)}, got {list(set_faces)}")
        missing = [k for k in set_pins if k not in {p.name for p in params}]
        if missing:
            raise ValueError(f"model type {name!r}: set_pins {missing} are no parameters")
        REGISTRY[name] = ModelType(name, title, category, pivot, description, fn, params, view, set_faces, set_pins)
        return fn

    return deco


def model_types() -> List[str]:
    return sorted(REGISTRY)


def asset_name(model_type: str, index: int, prefix: str = "") -> str:
    return f"{prefix}{REGISTRY[model_type].title}_{index:03d}"


def generate_asset(model_type: str, seed: int, name: str = "", scale: float = 1.0,
                   params: Optional[Dict[str, Any]] = None, style: Optional[Style] = None) -> Asset:
    """Build one asset deterministically from its seed (+ optional parameter overrides and style)."""
    try:
        entry = REGISTRY[model_type]
    except KeyError as exc:
        raise KeyError(f"unknown model type {model_type!r}; available: {', '.join(model_types())}") from exc
    style = style or Style()
    style.validate()
    style = style.resolved()
    rng = StableRandom(seed)
    asset = Asset(name or f"{entry.title}_{seed}")
    asset.p = ParamReader(rng, entry.params, params, style)
    asset.seed = seed
    token = DETAIL.set(style.detail)
    try:
        entry.build(rng, asset)
    finally:
        DETAIL.reset(token)
    asset.prune()
    for b in asset.behaviours:  # a part without geometry is gone: no script may point at it
        for role, value in b["parts"].items():
            for name in value if isinstance(value, list) else [value]:
                if asset.get(name) is None:
                    raise ValueError(f"{model_type}: {b['script']}.{role} names {name!r}, which has no geometry")
    for c in asset.colliders:
        if c.part is not None and asset.get(c.part) is None:
            raise ValueError(f"{model_type}: collider on {c.part!r}, but that part has no geometry")
    for obj in asset.meshes():
        for role in set(obj.mesh.roles):
            check_material(role)
    asset.normalize(entry.pivot)
    if style.damage != "intact":
        damage_asset(asset, seed, style.damage, entry.pivot, style.generation)
        if style.damage == "destroyed":  # old generation ruins used a static envelope
            asset.colliders = []
    if style.shape != "smooth":  # a derived form of the finished model (shapes.py): before the flush-detail pass
        from ..shapes import apply_shape

        apply_shape(asset, style.shape)
    if style.generation >= 2:
        # flush details would flicker in the game: lift them 2 mm (fragments: split faces need more passes)
        fix_z_fighting(asset, entry.pivot, passes=8 if style.damage == "fractured" else 3,
                       whole_primitives=style.generation >= 3 and style.damage == "fractured")
    if style.wear != "none" and entry.pivot == "floor":
        apply_wear(asset, seed, style.wear)
        if style.generation >= 2:
            fix_z_fighting(asset, entry.pivot, only=("Wear",))  # wear never changes the model itself
    if style.clutter != "none":
        from ..clutter import apply_clutter

        apply_clutter(asset, style.clutter)
    else:
        asset.meta.pop("clutter_surfaces", None)
    if style.generation >= 3:
        from ..collision import complete_gameplay_collision, complete_static_collision
        complete_gameplay_collision(asset)
        complete_static_collision(asset)
        add_anchors(asset, model_type, style.damage)  # empties for sound and effects (Audio_*, FX_*)
    if scale != 1.0:
        asset.scale(scale)
    asset.meta.setdefault("type", model_type)
    asset.meta.setdefault("seed", seed)
    asset.meta["params"] = dict(asset.p.used)
    asset.validate_contract(model_type)
    return asset
