"""Quality checks for generated models (``python -m cubegen check``).

* **Z-fighting**: two faces in the same plane, facing the same way, overlapping -
  they flicker in the game. Only reported when it can show: different materials,
  or different objects (scripts recolour, move or hide whole objects).
* **Triangles**: per model, against a budget per category.
* **Draw calls**: one per material per object (Unity sub-meshes).

All checks are pure Python and work on the assets as built (asset space).
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from .geometry import add_up, v_cross, v_dot, v_norm, v_sub

#: triangles per model and category (detail "normal") - low poly, but a room holds many models
TRIANGLE_BUDGET = {
    "props": 1500, "robots": 1500, "ruins": 1500, "tech": 2000, "environment": 2000, "industrial": 2000,
    "puzzle": 2500, "nature": 3000,
}
DEFAULT_TRIANGLE_BUDGET = 2500
DRAW_CALL_BUDGET = 16  # materials summed over all objects of a model (a warning: puzzles with tiles need more)

PLANE_TOL = 1e-4   # metres: faces closer than this to the same plane are coplanar
MIN_OVERLAP = 1e-4  # m^2 (1 cm^2): smaller overlaps don't show


def _poly_area(pts: Sequence[Tuple[float, float]]) -> float:
    return abs(add_up(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                      for i in range(len(pts)))) / 2.0


def _clip(subject: List[Tuple[float, float]], clip: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Sutherland-Hodgman: ``subject`` clipped by the convex polygon ``clip`` (counter-clockwise)."""
    output = subject
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        inp, output = output, []
        if not inp:
            break

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-12

        def cut(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]
            ex, ey = b[0] - a[0], b[1] - a[1]
            den = dx * ey - dy * ex
            t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den if abs(den) > 1e-15 else 0.0
            return (p[0] + t * dx, p[1] + t * dy)

        for j in range(len(inp)):
            cur, prev = inp[j], inp[j - 1]
            if inside(cur):
                if not inside(prev):
                    output.append(cut(prev, cur))
                output.append(cur)
            elif inside(prev):
                output.append(cut(prev, cur))
    return output


def _ccw(pts):
    signed = add_up(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                    for i in range(len(pts)))
    return pts if signed >= 0 else pts[::-1]


def z_fighting(asset, min_overlap: float = MIN_OVERLAP, pivot: str = "") -> List[Dict]:
    """Overlapping coplanar faces that would flicker: [{"a", "b", "area", "materials"}], biggest first.

    Faces nobody sees are skipped: undersides on the ground (z = 0) and, with ``pivot`` "wall",
    backs against the wall.
    """
    (_, _, z0), (_, y1, _) = asset.bbox()

    def hidden(n, pts):
        if abs(z0) < PLANE_TOL and n[2] < -0.999 and all(abs(p[2]) < PLANE_TOL for p in pts):
            return True
        return pivot == "wall" and n[1] > 0.999 and all(abs(p[1] - y1) < PLANE_TOL for p in pts)

    faces = []  # (object, part index, material, normal, offset, points)
    for obj in asset.meshes():
        mesh = obj.mesh
        part_of = {}
        for pi, part in enumerate(mesh.parts):
            for fi in part.face_indices():
                part_of[fi] = pi
        for fi, face in enumerate(mesh.faces):
            pts = [mesh.verts[i] for i in face]
            n = mesh.face_normal(fi)
            if v_dot(n, n) < 0.5 or hidden(n, pts):  # degenerate / never visible
                continue
            faces.append((obj.name, part_of.get(fi, -1), mesh.roles[fi], n, v_dot(n, pts[0]), pts))
    buckets: Dict[Tuple, List[int]] = {}
    for k, (_, _, _, n, d, _) in enumerate(faces):
        key = (round(n[0], 2), round(n[1], 2), round(n[2], 2), math.floor(d / (PLANE_TOL * 20)))
        buckets.setdefault(key, []).append(k)
    found = []
    seen = set()
    for key, members in buckets.items():
        near = members + buckets.get(key[:3] + (key[3] + 1,), [])
        for i in members:
            oa, pa, ma, na, da, pts_a = faces[i]
            for j in near:
                if j <= i and j in members or (min(i, j), max(i, j)) in seen:
                    continue
                ob, pb, mb, nb, db, pts_b = faces[j]
                if (oa, pa) == (ob, pb) or (ma == mb and oa == ob):
                    continue  # same primitive, or same material in the same object: renders identically
                if v_dot(na, nb) < 0.9999 or abs(da - db) > PLANE_TOL:
                    continue
                if any(abs(v_dot(na, v_sub(p, pts_a[0]))) > PLANE_TOL for p in pts_b):
                    continue
                seen.add((min(i, j), max(i, j)))
                u = v_norm(v_sub(pts_a[1], pts_a[0]))
                w = v_cross(na, u)
                a2 = _ccw([(v_dot(p, u), v_dot(p, w)) for p in pts_a])
                b2 = _ccw([(v_dot(p, u), v_dot(p, w)) for p in pts_b])
                inter = _clip(a2, b2)
                area = _poly_area(inter) if len(inter) >= 3 else 0.0
                if area >= min_overlap:
                    found.append({"a": oa, "b": ob, "area": round(area, 5), "materials": sorted({ma, mb})})
    found.sort(key=lambda f: -f["area"])
    return found


def draw_calls(asset) -> int:
    return sum(len(set(o.mesh.roles)) for o in asset.meshes())


def check(asset, category: str, pivot: str = "", budget_scale: float = 1.0) -> Dict:
    """Metrics and problems of one asset (``budget_scale``: 1.5 for detail "high")."""
    stats = asset.stats()
    budget = int(TRIANGLE_BUDGET.get(category, DEFAULT_TRIANGLE_BUDGET) * budget_scale)
    fights = z_fighting(asset, pivot=pivot)
    calls = draw_calls(asset)
    errors, warnings = [], []
    if stats["triangles"] > budget:
        errors.append(f"{stats['triangles']} triangles > budget {budget}")
    if calls > DRAW_CALL_BUDGET:
        warnings.append(f"{calls} draw calls > {DRAW_CALL_BUDGET}")
    if fights:
        top = fights[0]
        warnings.append(f"z-fighting: {len(fights)} face pair(s), e.g. {top['a']}/{top['b']} "
                        f"{top['area'] * 1e4:.0f} cm2 ({' vs '.join(top['materials'])})")
    return {"triangles": stats["triangles"], "budget": budget, "draw_calls": calls, "z_fighting": fights,
            "errors": errors, "warnings": warnings}


def report(model_types: Sequence[str], build, registry, seeds: int = 10, budget_scale: float = 1.0) -> Dict[str, Dict]:
    """Per type over ``seeds`` variants: max triangles, max draw calls, z-fighting, distinct variants.

    ``build(type, index)`` returns the asset of a variant.
    """
    from .variety import pick_unique

    result = {}
    for t in model_types:
        entry = registry[t]
        rows = [check(build(t, i), entry.category, entry.pivot, budget_scale) for i in range(seeds)]
        fights = [len(r["z_fighting"]) for r in rows]
        result[t] = {
            "category": entry.category,
            "triangles": max(r["triangles"] for r in rows),
            "budget": rows[0]["budget"],
            "draw_calls": max(r["draw_calls"] for r in rows),
            "z_fighting_pairs": max(fights),
            "z_fighting_variants": sum(1 for f in fights if f),
            "z_fighting_example": next((r["z_fighting"][0] for r in rows if r["z_fighting"]), None),
            "distinct_variants": len(pick_unique(seeds, lambda i, t=t: build(t, i), max_tries=seeds)[0]),
            "errors": sorted({e for r in rows for e in r["errors"]}),
        }
    return result


__all__ = ["check", "report", "z_fighting", "draw_calls", "TRIANGLE_BUDGET", "DRAW_CALL_BUDGET"]
