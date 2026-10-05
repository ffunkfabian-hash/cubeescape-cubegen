"""Registry of model types.

A model type is a function ``build(rng, asset)`` that adds named objects to
``asset``. Tunable values are read through ``asset.p`` (a
:class:`~cubegen.params.ParamReader`), which rolls them from ``rng`` and
applies parameter overrides and the global style. Register it with
:func:`model` and it is available on the command line and in the add-on.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..asset import Asset
from ..materials import check_material
from ..params import DETAIL, Param, ParamReader, Style
from .wear import apply_wear

BuildFn = Callable[[random.Random, Asset], None]


class ModelType:
    def __init__(self, name: str, title: str, category: str, pivot: str, description: str, build: BuildFn,
                 params: Sequence[Param]):
        self.name = name          # CLI name, e.g. "server_rack"
        self.title = title        # asset name prefix in Unity, e.g. "ServerRack"
        self.category = category
        self.pivot = pivot        # floor | top | center | wall
        self.description = description
        self.build = build
        self.params = list(params)

    def param(self, name: str) -> Param:
        for p in self.params:
            if p.name == name:
                return p
        raise KeyError(f"{self.name} has no parameter {name!r}; available: {', '.join(p.name for p in self.params)}")


REGISTRY: Dict[str, ModelType] = {}


def model(name: str, title: str, category: str, description: str, pivot: str = "floor",
          params: Sequence[Param] = ()):
    """Decorator that registers a builder function as model type ``name``."""

    def deco(fn: BuildFn) -> BuildFn:
        if name in REGISTRY:
            raise ValueError(f"model type {name!r} registered twice")
        REGISTRY[name] = ModelType(name, title, category, pivot, description, fn, params)
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
    rng = random.Random(seed)
    asset = Asset(name or f"{entry.title}_{seed}")
    asset.p = ParamReader(rng, entry.params, params, style)
    token = DETAIL.set(style.detail)
    try:
        entry.build(rng, asset)
    finally:
        DETAIL.reset(token)
    asset.objects = [o for o in asset.objects if o.mesh is None or o.mesh.faces]
    for obj in asset.meshes():
        for role in set(obj.mesh.roles):
            check_material(role)
    asset.normalize(entry.pivot)
    if style.wear != "none" and entry.pivot == "floor":
        apply_wear(asset, seed, style.wear)
    if scale != 1.0:
        asset.scale(scale)
    asset.meta.setdefault("type", model_type)
    asset.meta.setdefault("seed", seed)
    asset.meta["params"] = dict(asset.p.used)
    return asset
