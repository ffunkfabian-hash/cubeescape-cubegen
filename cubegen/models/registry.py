"""Registry of model types.

A model type is a function ``build(rng, asset)`` that adds named objects to
``asset`` using only the given ``random.Random``. Register it with
:func:`model` and it is available on the command line.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, List

from ..asset import Asset
from ..materials import check_material

BuildFn = Callable[[random.Random, Asset], None]


class ModelType:
    def __init__(self, name: str, title: str, category: str, pivot: str, description: str, build: BuildFn):
        self.name = name          # CLI name, e.g. "server_rack"
        self.title = title        # asset name prefix in Unity, e.g. "ServerRack"
        self.category = category
        self.pivot = pivot        # floor | top | center
        self.description = description
        self.build = build


REGISTRY: Dict[str, ModelType] = {}


def model(name: str, title: str, category: str, description: str, pivot: str = "floor"):
    """Decorator that registers a builder function as model type ``name``."""

    def deco(fn: BuildFn) -> BuildFn:
        if name in REGISTRY:
            raise ValueError(f"model type {name!r} registered twice")
        REGISTRY[name] = ModelType(name, title, category, pivot, description, fn)
        return fn

    return deco


def model_types() -> List[str]:
    return sorted(REGISTRY)


def asset_name(model_type: str, index: int, prefix: str = "") -> str:
    return f"{prefix}{REGISTRY[model_type].title}_{index:03d}"


def generate_asset(model_type: str, seed: int, name: str = "", scale: float = 1.0) -> Asset:
    """Build one asset deterministically from its seed."""
    try:
        entry = REGISTRY[model_type]
    except KeyError as exc:
        raise KeyError(f"unknown model type {model_type!r}; available: {', '.join(model_types())}") from exc
    asset = Asset(name or f"{entry.title}_{seed}")
    entry.build(random.Random(seed), asset)
    asset.objects = [o for o in asset.objects if o.mesh is None or o.mesh.faces]
    for obj in asset.meshes():
        for role in set(obj.mesh.roles):
            check_material(role)
    asset.normalize(entry.pivot)
    if scale != 1.0:
        asset.scale(scale)
    asset.meta.setdefault("type", model_type)
    asset.meta.setdefault("seed", seed)
    return asset
