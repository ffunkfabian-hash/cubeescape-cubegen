"""Fractured variant of any model (global style ``damage`` = ``fractured``).

The model looks intact but consists of fragments ``Fragment_<nn>``: Voronoi cells
around a few seeded points cut every convex closed primitive (boxes, chamfered
boxes, cylinders ...) into pieces, the cut faces get the fracture material.
Other primitives (open shells, concave shapes) go whole to the cell of their
centre. Every fragment is its own part with the pivot in its middle and a
convex mesh collider - Unity gives them rigid bodies when the object is
destroyed and lets them fall. Until then the model is static decoration (no
scripts); its own random stream keeps it the fractured version of the same seed.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from ..geometry import Mesh, Prim, add_up, face_normal, v_cross, v_dot, v_norm, v_sub
from ..seeds import StableRandom

FRACTURE = "M_Ground"
EPS = 1e-7

Poly = Tuple[List[Tuple[float, float, float]], str]  # face points, role


def _convex(points, faces) -> bool:
    for face in faces:
        pts = [points[i] for i in face]
        n = face_normal(pts)
        if v_dot(n, n) < 0.5:
            return False
        d = v_dot(n, pts[0])
        if any(v_dot(n, p) - d > 1e-6 for p in points):
            return False
    return True


def _clip_poly(pts, n, d):
    """Part of a planar polygon with dot(n, x) <= d, plus the points it gained on the plane."""
    out, cut = [], []
    for i, cur in enumerate(pts):
        prev = pts[i - 1]
        dc, dp = v_dot(n, cur) - d, v_dot(n, prev) - d
        if dc <= EPS:
            if dp > EPS:
                t = dp / (dp - dc)
                q = tuple(prev[k] + (cur[k] - prev[k]) * t for k in range(3))
                out.append(q)
                cut.append(q)
            out.append(cur)
            if abs(dc) <= EPS:
                cut.append(cur)
        elif dp <= EPS:
            t = dp / (dp - dc)
            q = tuple(prev[k] + (cur[k] - prev[k]) * t for k in range(3))
            out.append(q)
            cut.append(q)
    return out, cut


def _dedupe(pts, tol=1e-6):
    out = []
    for p in pts:
        if all(max(abs(p[k] - q[k]) for k in range(3)) > tol for q in out):
            out.append(p)
    return out


def _clip_body(polys: List[Poly], n, d, cap_role: str) -> List[Poly]:
    """Convex body (list of faces) cut by the half space dot(n, x) <= d, the hole closed with a cap face."""
    if all(v_dot(n, p) - d <= EPS for pts, _ in polys for p in pts):
        return polys
    result, ring = [], []
    for pts, role in polys:
        kept, cut = _clip_poly(pts, n, d)
        ring += cut
        kept = _dedupe(kept)
        if len(kept) >= 3:
            result.append((kept, role))
    ring = _dedupe(ring)
    if len(ring) >= 3 and result:
        c = tuple(add_up(p[k] for p in ring) / len(ring) for k in range(3))
        u = v_norm(v_sub(ring[0], c))
        w = v_cross(n, u)
        ring.sort(key=lambda p: math.atan2(v_dot(v_sub(p, c), w), v_dot(v_sub(p, c), u)))
        if v_dot(face_normal(ring), n) < 0:
            ring.reverse()
        result.append((ring, cap_role))
    return result if len(result) >= 4 else []


def _prim_from(polys: List[Poly]) -> Prim:
    verts, faces, roles = [], [], []
    index: Dict[Tuple[float, float, float], int] = {}
    for pts, role in polys:
        face = []
        for p in pts:
            key = (round(p[0], 7), round(p[1], 7), round(p[2], 7))
            if key not in index:
                index[key] = len(verts)
                verts.append(p)
            if index[key] not in face:
                face.append(index[key])
        if len(face) >= 3:
            faces.append(tuple(face))
            roles.append(role)
    return Prim(verts, faces, roles, closed=True)


def _cell(point, sites) -> int:
    return min(range(len(sites)), key=lambda i: add_up((point[k] - sites[i][k]) ** 2 for k in range(3)))


def fracture_asset(asset, seed: int, pivot: str, pieces: int = 0) -> int:
    """Replace the model's parts by ``Fragment_<nn>`` parts (convex mesh colliders); returns the fragment count."""
    rng = StableRandom(seed ^ 0xF4AC)
    (x0, y0, z0), (x1, y1, z1) = asset.bbox()
    size = (max(x1 - x0, 0.05), max(y1 - y0, 0.05), max(z1 - z0, 0.05))
    if not pieces:
        pieces = max(4, min(12, int(round((size[0] * size[1] * size[2]) ** (1 / 3) * 4)) + rng.randint(0, 2)))
    lo = (x0 + size[0] * 0.15, y0 + size[1] * 0.15, z0 + size[2] * 0.15)
    sites = [tuple(rng.uniform(lo[k], lo[k] + size[k] * 0.7) for k in range(3)) for _ in range(pieces)]

    fragments: List[List[Prim]] = [[] for _ in sites]
    big = max(size) * 0.2  # only primitives at least this long are cut, smaller ones stay whole
    for obj in asset.meshes():
        mesh = obj.mesh
        for part in mesh.parts:
            pts = mesh.verts[part.v0:part.v1]
            faces = [tuple(i - part.v0 for i in mesh.faces[fi]) for fi in part.face_indices()]
            roles = [mesh.roles[fi] for fi in part.face_indices()]
            if not faces:
                continue
            centre = tuple(add_up(p[k] for p in pts) / len(pts) for k in range(3))
            extent = max(max(p[k] for p in pts) - min(p[k] for p in pts) for k in range(3))
            if extent < big or not part.closed or not _convex(pts, faces):  # small or not cuttable: whole
                fragments[_cell(centre, sites)].append(Prim(pts, faces, roles, part.closed))
                continue
            body = [([pts[i] for i in f], r) for f, r in zip(faces, roles)]
            for i in range(len(sites)):
                piece = body
                for j, other in enumerate(sites):
                    if j == i or not piece:
                        continue
                    n = v_sub(other, sites[i])
                    d = (v_dot(other, other) - v_dot(sites[i], sites[i])) / 2
                    length = math.sqrt(v_dot(n, n))
                    piece = _clip_body(piece, tuple(c / length for c in n), d / length, FRACTURE)
                if piece:
                    prim = _prim_from(piece)
                    m = Mesh()
                    if m.part_volume(m.add(prim)) > 1e-8:
                        fragments[i].append(prim)

    asset.objects = []
    asset.behaviours = []
    asset.colliders = []
    count = 0
    for prims in fragments:
        if not prims:
            continue
        count += 1
        name = f"Fragment_{count:02d}"
        tmp = Mesh(name)
        for prim in prims:
            tmp.add(prim)
        (a0, b0, c0), (a1, b1, c1) = tmp.bbox()
        mesh = asset.part(name, pivot=((a0 + a1) / 2, (b0 + b1) / 2, (c0 + c1) / 2))
        for prim in prims:
            mesh.add(prim, name="fragment")
        asset.mesh_collider(name, convex=True)
    asset.meta["damage"] = "fractured"
    asset.meta["fragments"] = count
    return count


__all__ = ["fracture_asset"]
