"""Shape variants derived from a finished model (0.30.0, ``--shape``; TECHNIK.md 4 / Robogen 15, 17).

``voxel`` rebuilds the solid parts of a model as a union of cubes on one grid: the same parts, names, pivots, materials,
colliders and sidecar, a different silhouette - so it needs no new textures (the atlas is made from whatever geometry
the model has) and passes the same checks. Rules, all measured or derived in Robogen:

* **Only what is solid and safe:** a part becomes voxels when it is closed and convex (the cube test is then exact), at
  least ``MIN_CELLS`` cells thick on every axis, in a mesh object that only carries looks (``DECORATIVE_PARTS``), in a
  model without a pick-up behaviour. Thin parts, joints and everything that moves stay smooth.
* **A cube only where it fits:** its centre lies at least half a cell inside the part, so the cube lies wholly inside and
  nothing sticks out of the original - the colliders of the smooth model stay valid (AGENTS.md: collision per model).
* **Faces are merged (Robogen 17):** only the faces that border air are kept, and neighbours with the same material in
  a plane become one rectangle (greedy, per direction and slice). A part keeps the role of the original face that
  pointed the same way (a crate keeps its top role).

Pure Python, deterministic (grid anchored at the asset origin, sorted iteration). The other Robogen forms are not
derived here: the faceted form is what ``--detail low`` and ``crystal_cut`` already give, a perforated form is open.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .asset import DECORATIVE_PARTS
from .geometry import Part, v_cross, v_dot, v_norm, v_sub

SHAPES = ("smooth", "voxel")
MIN_CELLS = 4          # a part thinner than this on any axis stays smooth
MAX_CELLS = 6000       # a part with more candidate cells stays smooth (cost)
CELL_RANGE = (0.06, 0.2)
GRID_DIVISIONS = 16    # the cell is the model's longest side / this, clamped to CELL_RANGE
EPS = 1e-6

Vec = Tuple[float, float, float]
AXES = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def cell_size(asset) -> float:
    """The grid cell of a model: its longest side over ``GRID_DIVISIONS`` (rounded to mm), within ``CELL_RANGE``."""
    lo, hi = asset.bbox()
    longest = max(hi[i] - lo[i] for i in range(3))
    return round(min(CELL_RANGE[1], max(CELL_RANGE[0], longest / GRID_DIVISIONS)), 3)


def _planes(mesh, part: Part) -> Optional[List[Tuple[Vec, float, float, str]]]:
    """Outward planes ``(normal, offset, area, role)`` of a closed part, or None when it is not convex."""
    verts = mesh.verts[part.v0:part.v1]
    centre = tuple(sum(v[i] for v in verts) / len(verts) for i in range(3))
    planes = []
    for fi in part.face_indices():
        face = mesh.faces[fi]
        pts = [mesh.verts[i] for i in face]
        n = (0.0, 0.0, 0.0)
        for k in range(1, len(pts) - 1):
            c = v_cross(v_sub(pts[k], pts[0]), v_sub(pts[k + 1], pts[0]))
            n = (n[0] + c[0], n[1] + c[1], n[2] + c[2])
        area = math.sqrt(v_dot(n, n)) / 2
        if area < 1e-9:
            continue
        normal = v_norm(n)
        offset = v_dot(normal, pts[0])
        if v_dot(normal, centre) - offset > 0:  # winding differs from "outward": use the outward side
            normal, offset = (-normal[0], -normal[1], -normal[2]), -offset
        planes.append((normal, offset, area, mesh.roles[fi]))
    for normal, offset, _, _ in planes:
        if any(v_dot(normal, v) - offset > 1e-5 for v in verts):
            return None
    return planes


def _direction_roles(planes, fallback: str) -> Dict[Tuple[int, int], str]:
    """The role of the face (largest area) that points along each of the six axis directions."""
    roles = {}
    for axis in range(3):
        for sign in (1, -1):
            best = None
            for normal, _, area, role in planes:
                if normal[axis] * sign > 0.5 and (best is None or area > best[0]):
                    best = (area, role)
            roles[(axis, sign)] = best[1] if best else fallback
    return roles


def _cells(planes, lo: Vec, hi: Vec, cell: float) -> Optional[Set[Tuple[int, int, int]]]:
    """Cube cells (grid anchored at the origin) lying at least half a cell inside the convex part."""
    half = cell / 2
    first = [math.ceil((lo[i] + half) / cell - 0.5 - EPS) for i in range(3)]
    last = [math.floor((hi[i] - half) / cell - 0.5 + EPS) for i in range(3)]
    count = 1
    for i in range(3):
        count *= max(0, last[i] - first[i] + 1)
    if count == 0 or count > MAX_CELLS:
        return None
    found = set()
    for ix in range(first[0], last[0] + 1):
        for iy in range(first[1], last[1] + 1):
            for iz in range(first[2], last[2] + 1):
                p = ((ix + 0.5) * cell, (iy + 0.5) * cell, (iz + 0.5) * cell)
                # the whole cube is inside when its centre is half a cell inside along each plane normal: the cube's
                # reach along a normal n is half * (|nx| + |ny| + |nz|), the exact support of an axis-aligned cube
                if all(v_dot(n, p) - d + half * (abs(n[0]) + abs(n[1]) + abs(n[2])) <= EPS for n, d, _, _ in planes):
                    found.add((ix, iy, iz))
    return found or None


def _merged_faces(cells: Set[Tuple[int, int, int]], roles: Dict[Tuple[int, int], str], cell: float):
    """Quads ``(corners, role)`` of the surface of ``cells``: faces towards air only, neighbours of one direction and
    slice merged into rectangles (greedy: along u first, then along v)."""
    quads = []
    for axis in range(3):
        u_axis, v_axis = (axis + 1) % 3, (axis + 2) % 3
        for sign in (1, -1):
            slices: Dict[int, Set[Tuple[int, int]]] = {}
            for c in cells:
                n = list(c)
                n[axis] += sign
                if tuple(n) not in cells:
                    slices.setdefault(c[axis], set()).add((c[u_axis], c[v_axis]))
            for layer in sorted(slices):
                todo = slices[layer]
                for (u, v) in sorted(todo, key=lambda uv: (uv[1], uv[0])):
                    if (u, v) not in todo:
                        continue
                    w = 1
                    while (u + w, v) in todo:
                        w += 1
                    h = 1
                    while all((u + k, v + h) in todo for k in range(w)):
                        h += 1
                    for k in range(w):
                        for j in range(h):
                            todo.discard((u + k, v + j))
                    plane = (layer + (1 if sign > 0 else 0)) * cell
                    corners = []
                    for du, dv in ((0, 0), (w, 0), (w, h), (0, h)):
                        point = [0.0, 0.0, 0.0]
                        point[axis], point[u_axis], point[v_axis] = plane, (u + du) * cell, (v + dv) * cell
                        corners.append(tuple(point))
                    if sign < 0:
                        corners.reverse()
                    quads.append((corners, roles[(axis, sign)]))
    return quads


def voxelize_part(mesh, part: Part, cell: float):
    """Quads of the voxel form of one closed part, or None when it must stay smooth."""
    if not part.closed or part.v1 - part.v0 < 4:
        return None
    verts = mesh.verts[part.v0:part.v1]
    lo = tuple(min(v[i] for v in verts) for i in range(3))
    hi = tuple(max(v[i] for v in verts) for i in range(3))
    if any(hi[i] - lo[i] < MIN_CELLS * cell for i in range(3)):
        return None
    planes = _planes(mesh, part)
    if not planes:
        return None
    cells = _cells(planes, lo, hi, cell)
    if not cells:
        return None
    fallback = Counter(mesh.roles[fi] for fi in part.face_indices()).most_common(1)[0][0]
    return _merged_faces(cells, _direction_roles(planes, fallback), cell)


def _replace(mesh, replaced: Sequence[Tuple[Part, list]]) -> None:
    """Swap the parts for their quads: the rest keeps its order, the new geometry follows as parts named ``voxel``."""
    mesh.remove_parts([part for part, _ in replaced])
    for _, quads in replaced:
        v0, f0 = len(mesh.verts), len(mesh.faces)
        index: Dict[Vec, int] = {}
        for corners, role in quads:
            face = []
            for p in corners:
                p = tuple(round(c, 6) + 0.0 for c in p)
                if p not in index:
                    index[p] = len(mesh.verts)
                    mesh.verts.append(p)
                face.append(index[p])
            mesh.faces.append(tuple(face))
            mesh.roles.append(role)
        mesh.parts.append(Part(mesh, "voxel", v0, len(mesh.verts), f0, len(mesh.faces), True, None))


def voxelize(asset, cell: Optional[float] = None) -> Dict[str, object]:
    """Derive the voxel form in place; returns ``{"cell", "parts", "triangles_before", "triangles_after"}`` (kept in
    ``asset.meta['shape']`` when a part changed). A model with a pick-up behaviour and objects outside ``DECORATIVE_PARTS`` are left alone."""
    cell = cell or cell_size(asset)
    before = asset.stats()["triangles"]
    converted = 0
    if not any(b["script"] == "ItemPickup" for b in asset.behaviours):
        for obj in asset.meshes():
            if obj.name not in DECORATIVE_PARTS:
                continue
            replaced = []
            for part in obj.mesh.parts:
                quads = voxelize_part(obj.mesh, part, cell)
                if quads:
                    replaced.append((part, quads))
            if replaced:
                _replace(obj.mesh, replaced)
                converted += len(replaced)
    info = {"form": "voxel", "cell": cell, "parts": converted, "triangles_before": before,
            "triangles_after": asset.stats()["triangles"]}
    if converted:  # a model nothing was derived from stays exactly the smooth model
        asset.meta["shape"] = info
    return info


def apply_shape(asset, shape: str) -> Optional[Dict[str, object]]:
    if shape == "voxel":
        return voxelize(asset)
    return None
