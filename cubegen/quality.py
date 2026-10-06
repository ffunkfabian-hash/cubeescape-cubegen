"""Quality checks for generated models (``python -m cubegen check``).

* **Z-fighting**: two faces in the same plane, facing the same way, overlapping -
  they flicker in the game. Only reported when it can show: different materials,
  or different objects (scripts recolour, move or hide whole objects).
* **Triangles**: per model, against a budget per category.
* **Draw calls**: one per material per object (Unity sub-meshes); static models: one per material.
* **Colliders**: solid pieces of the model that no collision shape covers (the player walks into them).

All checks are pure Python and work on the assets as built (asset space).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from .geometry import add_up, v_cross, v_dot, v_norm, v_sub

#: triangles per model and category (detail "normal") - low poly, but a room holds many models
TRIANGLE_BUDGET = {
    "props": 1500, "robots": 1500, "ruins": 1500, "tech": 2000, "environment": 2000, "industrial": 2000,
    "puzzle": 2500, "nature": 3000,
}
DEFAULT_TRIANGLE_BUDGET = 2500
DRAW_CALL_BUDGET = 16  # materials summed over all objects of a model ...
DRAW_CALLS_PER_OBJECT = 2  # ... or 2 per object: every object is its own renderer in Unity (moving parts can't merge)

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


def _fighting_faces(asset, min_overlap: float = MIN_OVERLAP, pivot: str = "") -> List[Tuple]:
    """Overlapping coplanar face pairs that would flicker: [(area, (obj, face index, face area), (...same))]."""
    (_, _, z0), (_, y1, _) = asset.bbox()
    if pivot == "floor":  # the floor is at z = 0, even when wear or rubble sinks a little into it
        z0 = 0.0

    def hidden(n, pts):
        if abs(z0) < PLANE_TOL and n[2] < -0.999 and all(abs(p[2]) < PLANE_TOL for p in pts):
            return True
        return pivot == "wall" and n[1] > 0.999 and all(abs(p[1] - y1) < PLANE_TOL for p in pts)

    faces = []  # (object, part index, material, normal, offset, points, face index)
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
            faces.append((obj, part_of.get(fi, -1), mesh.roles[fi], n, v_dot(n, pts[0]), pts, fi))
    buckets: Dict[Tuple, List[int]] = {}
    for k, (_, _, _, n, d, _, _) in enumerate(faces):
        key = (round(n[0], 2), round(n[1], 2), round(n[2], 2), math.floor(d / (PLANE_TOL * 20)))
        buckets.setdefault(key, []).append(k)
    found = []
    seen = set()
    for key, members in buckets.items():
        near = members + buckets.get(key[:3] + (key[3] + 1,), [])
        for i in members:
            oa, pa, ma, na, da, pts_a, fa = faces[i]
            for j in near:
                if j <= i and j in members or (min(i, j), max(i, j)) in seen:
                    continue
                ob, pb, mb, nb, db, pts_b, fb = faces[j]
                if (oa is ob and pa == pb) or (ma == mb and oa is ob):
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
                    found.append((area, (oa, fa, _poly_area(a2), ma), (ob, fb, _poly_area(b2), mb)))
    found.sort(key=lambda f: -f[0])
    return found


def z_fighting(asset, min_overlap: float = MIN_OVERLAP, pivot: str = "") -> List[Dict]:
    """Overlapping coplanar faces that would flicker: [{"a", "b", "area", "materials"}], biggest first.

    Faces nobody sees are skipped: undersides on the ground (z = 0) and, with ``pivot`` "wall",
    backs against the wall.
    """
    return [{"a": a[0].name, "b": b[0].name, "area": round(area, 5), "materials": sorted({a[3], b[3]})}
            for area, a, b in _fighting_faces(asset, min_overlap, pivot)]


DECAL_OFFSET = 0.002  # metres a flush detail face is lifted off the face under it (Unity's depth buffer resolves it)


def fix_z_fighting(asset, pivot: str = "", offset: float = DECAL_OFFSET, passes: int = 3,
                   only: Optional[Sequence[str]] = None) -> int:
    """Lift the smaller face of every flickering pair ``offset`` along its normal: a stripe, a glow strip or a
    panel flush with the body now sits on it. Moves only that face's vertices (its primitive grows by
    ``offset``). With ``only``, just faces of these objects move (wear never changes the model itself).
    Returns the number of faces moved; deterministic."""
    order = {id(o): k for k, o in enumerate(asset.meshes())}
    moved = 0
    for _ in range(passes):
        lift = {}
        for _, a, b in _fighting_faces(asset, pivot=pivot):
            # the smaller face is the detail; on a tie the later object / face
            candidates = [f for f in (a, b) if only is None or f[0].name in only]
            if not candidates:
                continue
            key = lambda f: (round(f[2], 6), -order[id(f[0])], -f[1])  # noqa: E731
            obj, fi = min(candidates, key=key)[:2]
            lift[(id(obj), fi)] = (obj, fi)
        if not lift:
            break
        for (_, fi), (obj, _) in sorted(lift.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
            mesh = obj.mesh
            n = mesh.face_normal(fi)
            for vi in mesh.faces[fi]:
                v = mesh.verts[vi]
                mesh.verts[vi] = (v[0] + n[0] * offset, v[1] + n[1] * offset, v[2] + n[2] * offset)
            moved += 1
    return moved


def draw_calls(asset) -> int:
    """One per material per object (Unity sub-meshes). A static model (no scripts) is batched by Unity's static
    batching (Library prefabs marked Static): one per material."""
    if not asset.behaviours:
        return len({r for o in asset.meshes() for r in o.mesh.roles})
    return sum(len(set(o.mesh.roles)) for o in asset.meshes())


def draw_call_budget(asset) -> int:
    """16 per model - or, for models of many objects (tiles, legs, rollers that move on their own and can't be
    merged), 2 per object plus 2 for the body. Optional wear (``--wear``) comes on top."""
    objects = [o for o in asset.meshes() if o.name != "Wear"]
    wear = sum(len(set(o.mesh.roles)) for o in asset.meshes() if o.name == "Wear")
    return max(DRAW_CALL_BUDGET, DRAW_CALLS_PER_OBJECT * len(objects) + 2) + wear


# --------------------------------------------------------------------------
# colliders against the geometry
# --------------------------------------------------------------------------

SOLID_MIN_VOLUME = 0.05  # m^3: smaller pieces (rails, struts, bolts, crystals' tips) need no collider of their own
SOLID_MIN_SIZE = 0.15    # m: ... nor do thin plates
COLLIDER_TOL = 0.05      # m: geometry this close to a collider counts as covered (bevels, lifted details)
SAMPLES = 3              # sample points per axis in a part's bounding box


def _solid_volume(verts, faces) -> float:
    total = 0.0
    for f in faces:
        a = verts[f[0]]
        for i in range(1, len(f) - 1):
            b, c = verts[f[i]], verts[f[i + 1]]
            total += v_dot(a, v_cross(b, c)) / 6.0
    return abs(total)


def _inside_solid(p, verts, faces) -> bool:
    """Point in a closed mesh: ray towards +x, odd number of crossings (faces may be concave n-gons)."""
    px, py, pz = p
    crossings = 0
    for f in faces:
        pts = [verts[i] for i in f]
        nx = add_up((a[1] - b[1]) * (a[2] + b[2]) for a, b in zip(pts, pts[1:] + pts[:1]))
        if abs(nx) < 1e-12:  # face parallel to the ray
            continue
        ny = add_up((a[2] - b[2]) * (a[0] + b[0]) for a, b in zip(pts, pts[1:] + pts[:1]))
        nz = add_up((a[0] - b[0]) * (a[1] + b[1]) for a, b in zip(pts, pts[1:] + pts[:1]))
        x = (nx * pts[0][0] + ny * (pts[0][1] - py) + nz * (pts[0][2] - pz)) / nx
        if x <= px:
            continue
        inside = False
        for (_, y1, z1), (_, y2, z2) in zip(pts, pts[1:] + pts[:1]):
            if (z1 > pz) != (z2 > pz) and py < y1 + (pz - z1) * (y2 - y1) / (z2 - z1):
                inside = not inside
        crossings += inside
    return crossings % 2 == 1


def needs_collider(mesh, part) -> bool:
    """A closed piece big enough to walk into: ``SOLID_MIN_VOLUME`` and ``SOLID_MIN_SIZE`` thick."""
    if not part.closed:
        return False
    verts = mesh.verts[part.v0:part.v1]
    if min(max(v[i] for v in verts) - min(v[i] for v in verts) for i in range(3)) < SOLID_MIN_SIZE:
        return False
    faces = [tuple(i - part.v0 for i in mesh.faces[fi]) for fi in range(part.f0, part.f1)]
    return _solid_volume(verts, faces) >= SOLID_MIN_VOLUME


def uncovered_geometry(asset, pivot: str = "") -> List[Dict]:
    """Solid pieces the Unity collision shapes (``families.collision_boxes``) don't cover - the player walks into
    them. Per closed piece of at least ``SOLID_MIN_VOLUME`` (and ``SOLID_MIN_SIZE`` thick): points on a grid inside
    the piece that lie outside every collider (``COLLIDER_TOL``).

    Not counted: ``Damage`` (only shows while a machine is broken), the leaves of a ``Door`` without colliders of its
    own (the game's door setup gives them theirs) and, for platforms (pivot ``top``), what lies under the floor."""
    from .families import collision_boxes  # families needs nothing from here, but keep the import lazy

    boxes = collision_boxes(asset, "")
    skip = {"Damage"}
    if not asset.colliders:
        for b in asset.behaviours:
            if b["script"] == "Door":
                skip.update(b["parts"].get("panels") or [])
    found = []
    for obj in asset.meshes():
        if obj.name in skip:
            continue
        mesh = obj.mesh
        for part in mesh.parts:
            if not needs_collider(mesh, part):
                continue
            verts = mesh.verts[part.v0:part.v1]
            lo = [min(v[i] for v in verts) for i in range(3)]
            hi = [max(v[i] for v in verts) for i in range(3)]
            faces = [tuple(i - part.v0 for i in mesh.faces[fi]) for fi in range(part.f0, part.f1)]
            points = []
            for gx in range(SAMPLES):
                for gy in range(SAMPLES):
                    for gz in range(SAMPLES):
                        p = tuple(lo[i] + (hi[i] - lo[i]) * (g + 0.5) / SAMPLES for i, g in enumerate((gx, gy, gz)))
                        if pivot == "top" and p[2] < -COLLIDER_TOL:  # platforms: under the floor
                            continue
                        if _inside_solid(p, verts, faces):
                            points.append(p)
            if not points:
                continue
            free = [p for p in points if not any(b.contains(p, margin=-COLLIDER_TOL) for b in boxes)]
            if free:
                found.append({"object": obj.name, "uncovered": round(len(free) / len(points), 3),
                              "min": [round(c, 3) for c in lo], "max": [round(c, 3) for c in hi]})
    return found


def check(asset, category: str, pivot: str = "", budget_scale: float = 1.0, palette: bool = False) -> Dict:
    """Metrics and problems of one asset (``budget_scale``: 1.5 for detail "high"; ``palette``: draw calls with
    ``--textures palette``)."""
    stats = asset.stats()
    budget = int(TRIANGLE_BUDGET.get(category, DEFAULT_TRIANGLE_BUDGET) * budget_scale)
    fights = z_fighting(asset, pivot=pivot)
    if palette:
        from .palette import draw_calls as palette_draw_calls

        calls = palette_draw_calls(asset)
    else:
        calls = draw_calls(asset)
    call_budget = draw_call_budget(asset)
    errors, warnings = [], []
    if stats["triangles"] > budget:
        errors.append(f"{stats['triangles']} triangles > budget {budget}")
    if calls > call_budget:
        warnings.append(f"{calls} draw calls > {call_budget}")
    uncovered = uncovered_geometry(asset, pivot)
    if uncovered:
        top = uncovered[0]
        warnings.append(f"no collider: {len(uncovered)} solid piece(s), e.g. {top['object']} "
                        f"{top['uncovered']:.0%} uncovered")
    if fights:
        top = fights[0]
        warnings.append(f"z-fighting: {len(fights)} face pair(s), e.g. {top['a']}/{top['b']} "
                        f"{top['area'] * 1e4:.0f} cm2 ({' vs '.join(top['materials'])})")
    return {"triangles": stats["triangles"], "budget": budget, "draw_calls": calls, "draw_call_budget": call_budget,
            "z_fighting": fights, "uncovered": uncovered,
            "errors": errors, "warnings": warnings}


def report(model_types: Sequence[str], build, registry, seeds: int = 10, budget_scale: float = 1.0,
           palette: bool = False) -> Dict[str, Dict]:
    """Per type over ``seeds`` variants: max triangles, max draw calls, z-fighting, solid geometry without a
    collider, distinct variants.

    ``build(type, index)`` returns the asset of a variant.
    """
    from .variety import pick_unique

    result = {}
    for t in model_types:
        entry = registry[t]
        rows = [check(build(t, i), entry.category, entry.pivot, budget_scale, palette) for i in range(seeds)]
        fights = [len(r["z_fighting"]) for r in rows]
        result[t] = {
            "category": entry.category,
            "triangles": max(r["triangles"] for r in rows),
            "budget": rows[0]["budget"],
            "draw_calls": max(r["draw_calls"] for r in rows),
            "draw_calls_over": sum(1 for r in rows if r["draw_calls"] > r["draw_call_budget"]),
            "z_fighting_pairs": max(fights),
            "z_fighting_variants": sum(1 for f in fights if f),
            "z_fighting_example": next((r["z_fighting"][0] for r in rows if r["z_fighting"]), None),
            "uncovered_variants": sum(1 for r in rows if r["uncovered"]),
            "uncovered_example": next((r["uncovered"][0] for r in rows if r["uncovered"]), None),
            "distinct_variants": len(pick_unique(seeds, lambda i, t=t: build(t, i), max_tries=seeds)[0]),
            "errors": sorted({e for r in rows for e in r["errors"]}),
        }
    return result


__all__ = ["check", "report", "z_fighting", "uncovered_geometry", "needs_collider", "fix_z_fighting", "draw_calls",
           "TRIANGLE_BUDGET", "DRAW_CALL_BUDGET",
           "draw_call_budget"]
