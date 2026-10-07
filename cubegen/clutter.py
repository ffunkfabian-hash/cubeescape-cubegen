"""Seeded placement of separate small props on explicitly declared surfaces."""

from __future__ import annotations

import copy
import math
from typing import Dict, List, Tuple

from .asset import Asset, AssetObject
from .geometry import Vec3
from .models.registry import generate_asset
from .params import Style
from .seeds import StableRandom, derive_seed

DENSITIES = {"clean": 1.5, "lived-in": 5.0, "chaotic": 9.0}
PROP_TYPES = ("tool", "spare_part", "keycard")


def _surface_bounds(surface: Dict[str, object], asset_name: str) -> Tuple[float, float, float, float, float]:
    try:
        x0, x1 = surface["x"]
        y0, y1 = surface["y"]
        z = surface["z"]
        values = tuple(float(value) for value in (x0, x1, y0, y1, z))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{asset_name}: invalid clutter surface {surface!r}") from exc
    x0, x1, y0, y1, z = values
    if not all(math.isfinite(value) for value in values) or x0 >= x1 or y0 >= y1:
        raise ValueError(f"{asset_name}: invalid clutter surface bounds {surface!r}")
    return values


def _prop_spec(prop_type: str, rng: StableRandom) -> Tuple[Dict[str, object], float]:
    if prop_type == "tool":
        return {"kind": rng.choice(("wrench", "pliers", "screwdriver")), "length": rng.uniform(0.24, 0.38)}, \
            rng.uniform(0.25, 0.34)
    if prop_type == "spare_part":
        return {"kind": rng.choice(("gear", "lens", "valve_wheel")), "size": rng.uniform(0.12, 0.2)}, \
            rng.uniform(0.25, 0.34)
    return {}, rng.uniform(0.22, 0.3)


def _horizontal_bounds(prop: Asset, scale: float, yaw: float) -> Tuple[float, float, float, float, float]:
    c, s = math.cos(yaw), math.sin(yaw)
    points = []
    for obj in prop.meshes():
        for x, y, z in obj.mesh.verts:
            # Inventory props are modeled upright in XZ; lay them on the table.
            x, y, z = x, -z, y
            points.append((scale * (c * x - s * y), scale * (s * x + c * y), scale * z))
    if not points:
        raise ValueError(f"clutter prop {prop.name!r} has no mesh vertices")
    return (min(p[0] for p in points), max(p[0] for p in points),
            min(p[1] for p in points), max(p[1] for p in points), min(p[2] for p in points))


def _append_prop(host: Asset, prop: Asset, prefix: str, scale: float, yaw: float,
                 location: Tuple[float, float], bottom: float) -> None:
    c, s = math.cos(yaw), math.sin(yaw)
    _, _, _, _, z0 = _horizontal_bounds(prop, scale, yaw)
    offset = (location[0], location[1], bottom - z0)

    for obj in prop.objects:
        if obj.mesh is None:
            continue
        name = f"{prefix}_{obj.name}"
        if host.get(name) is not None:
            raise ValueError(f"asset {host.name!r}: clutter object name {name!r} already exists")

        pivot_x, pivot_y, pivot_z = obj.pivot
        pivot_x, pivot_y, pivot_z = pivot_x, -pivot_z, pivot_y
        pivot = (scale * (c * pivot_x - s * pivot_y) + offset[0],
                 scale * (s * pivot_x + c * pivot_y) + offset[1],
                 scale * pivot_z + offset[2])
        mesh = copy.deepcopy(obj.mesh)
        mesh.verts = [
            (scale * (c * x + s * z) + offset[0],
             scale * (s * x - c * z) + offset[1],
             scale * y + offset[2])
            for x, y, z in mesh.verts
        ]
        host.objects.append(AssetObject(name, pivot, None, mesh))


def apply_clutter(asset: Asset, density: str) -> None:
    """Place small, independently named props on an asset's declared top surfaces."""
    surfaces = asset.meta.pop("clutter_surfaces", [])
    if density == "none" or not surfaces:
        return
    if density not in DENSITIES:
        raise ValueError(f"unknown clutter density {density!r}; choose none, {', '.join(DENSITIES)}")

    placed = []
    skipped = 0
    surface_records = []
    style = asset.p.style
    prop_style = Style(glow=style.glow, material=style.material, warning=style.warning,
                       detail=style.detail, generation=style.generation, clutter="none")
    for surface_index, surface in enumerate(surfaces):
        x0, x1, y0, y1, z = _surface_bounds(surface, asset.name)
        area = (x1 - x0) * (y1 - y0)
        target = min(8, max(1, int(area * DENSITIES[density] + 0.5)))
        key = str(surface.get("key", surface_index))
        surface_records.append({"key": key, "bounds": [round(value, 4) for value in (x0, x1, y0, y1, z)]})
        occupied: List[Tuple[float, float, float, float]] = []

        for item_index in range(target):
            rng = StableRandom(derive_seed(asset.seed, "clutter", key, item_index))
            prop_type = rng.choice(PROP_TYPES)
            params, target_size = _prop_spec(prop_type, rng)
            prop = generate_asset(
                prop_type,
                derive_seed(asset.seed, "clutter-prop", key, item_index, prop_type),
                params=params,
                style=prop_style,
            )
            lo, hi = prop.bbox()
            largest = max(hi[0] - lo[0], hi[2] - lo[2])
            scale = target_size / largest if largest > 1e-9 else 1.0
            yaw = rng.uniform(-math.pi, math.pi)
            bx0, bx1, by0, by1, _ = _horizontal_bounds(prop, scale, yaw)
            half_x, half_y = (bx1 - bx0) / 2, (by1 - by0) / 2
            if x1 - x0 < 2 * half_x or y1 - y0 < 2 * half_y:
                skipped += 1
                continue

            accepted = None
            for _ in range(64):
                px = rng.uniform(x0 + half_x, x1 - half_x)
                py = rng.uniform(y0 + half_y, y1 - half_y)
                bounds = (px - half_x, px + half_x, py - half_y, py + half_y)
                if all(bounds[1] + 0.025 <= other[0] or other[1] + 0.025 <= bounds[0] or
                       bounds[3] + 0.025 <= other[2] or other[3] + 0.025 <= bounds[2]
                       for other in occupied):
                    accepted = (px, py, bounds)
                    break
            if accepted is None:
                skipped += 1
                continue

            px, py, bounds = accepted
            occupied.append(bounds)
            prefix = f"Clutter_{len(placed):03d}"
            _append_prop(asset, prop, prefix, scale, yaw, (px, py), z)
            placed.append({"type": prop_type, "surface": key, "position": [round(px, 4), round(py, 4), round(z, 4)]})

    if placed or skipped:
        asset.meta["clutter_pass"] = {
            "density": density, "surfaces": surface_records, "placed": placed, "skipped": skipped,
        }
