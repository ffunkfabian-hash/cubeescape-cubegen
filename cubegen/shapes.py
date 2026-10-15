"""Shape variants derived from a finished model (0.30.0, ``--shape``; TECHNIK.md 4 / Robogen 15, 17).

Three forms (``SHAPES``), all derived from the finished smooth model, all *inside* it (nothing protrudes, so the colliders
of the smooth model stay valid), all on the model's own parts, names, pivots and materials:

* ``voxel`` - cubes on one grid, faces merged (below);
* ``facet`` - every round solid part (a closed convex part with 12 or more vertices) becomes the convex hull of a
  farthest-point subset of its vertices (a third of them, at least 8): fewer, larger faces, a cut-stone look (discs and
  plates stay: a handful of their vertices makes shards);
* ``holes`` - flat plates (closed convex, thin along a world axis, large across) get a regular grid of square holes of
  one cell (at most 0.15 m: nothing passes through, a collider box over the plate stays right) with a solid rim.

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

Pure Python, deterministic (grid anchored at the asset origin, sorted iteration).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .asset import DECORATIVE_PARTS
from .geometry import Part, v_cross, v_dot, v_norm, v_sub

SHAPES = ("smooth", "voxel", "facet", "holes")
MIN_CELLS = 4          # a part thinner than this on any axis stays smooth
MAX_CELLS = 6000       # a part with more candidate cells stays smooth (cost)
CELL_RANGE = (0.06, 0.2)
GRID_DIVISIONS = 16    # the cell is the model's longest side / this, clamped to CELL_RANGE
EPS = 1e-6
META_KEY = "derived_shape"  # asset.meta: what was derived (models use "shape" for their own things)
FACET_MIN_VERTS = 12   # a part with fewer vertices is faceted enough (a box has 8)
FACET_KEEP = 3         # one vertex in three stays (at least FACET_FLOOR)
FACET_FLOOR = 8
FACET_FLAT = 0.35      # thinnest side over the middle one: below this the part is a disc or plate and stays
HOLE_MAX = 0.15        # m: the largest hole - nothing (a player capsule, a robot) passes, a collider over the plate holds
HOLE_MIN = 0.06
HOLE_THIN = 0.12       # m: a plate is at most this thick ...
HOLE_RATIO = 4.0       # ... and its other two sides at least this many times its thickness, and 8 holes wide
LID_FACTOR = 3        # a top slab may cost this many triangles per face of its part
TOP_STEP = 0.05        # m: the top of a part is matched to this (voxel caps in fine layers, facet vertices added)
HOLE_LAYER = 0.8       # the single layer of cells is this share of the thickness (bevelled edges stay outside the cells)

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


def _cells(planes, lo: Vec, hi: Vec, cell: Vec, origin: Vec = (0.0, 0.0, 0.0), max_cells: int = MAX_CELLS) -> Optional[Set[Tuple[int, int, int]]]:
    """Cells (a grid of ``cell`` sized boxes, index i = centre ``origin + (i + 0.5) * cell``) lying wholly inside the
    convex part: the box's reach along a plane normal n is ``sum(|n_i| * half_i)``, the exact support of a box."""
    half = tuple(c / 2 for c in cell)
    first = [math.ceil((lo[i] + half[i] - origin[i]) / cell[i] - 0.5 - EPS) for i in range(3)]
    last = [math.floor((hi[i] - half[i] - origin[i]) / cell[i] - 0.5 + EPS) for i in range(3)]
    count = 1
    for i in range(3):
        count *= max(0, last[i] - first[i] + 1)
    if count == 0 or count > max_cells:
        return None
    reach = [sum(abs(n[i]) * half[i] for i in range(3)) for n, _, _, _ in planes]
    found = set()
    for ix in range(first[0], last[0] + 1):
        for iy in range(first[1], last[1] + 1):
            for iz in range(first[2], last[2] + 1):
                p = (origin[0] + (ix + 0.5) * cell[0], origin[1] + (iy + 0.5) * cell[1],
                     origin[2] + (iz + 0.5) * cell[2])
                if all(v_dot(n, p) - d + r <= EPS for (n, d, _, _), r in zip(planes, reach)):
                    found.add((ix, iy, iz))
    return found or None


def _top_z(planes, x: float, y: float) -> Optional[float]:
    """Height of the upper surface of a convex part (outward ``planes``) at (x, y), or None when the part has no
    surface there (Cyrus-Beck on the vertical line)."""
    top, bottom = math.inf, -math.inf
    for n, d, _, _ in planes:
        rest = d - n[0] * x - n[1] * y
        if abs(n[2]) < 1e-9:
            if rest < -EPS:
                return None
        elif n[2] > 0:
            top = min(top, rest / n[2])
        else:
            bottom = max(bottom, rest / n[2])
    if top == math.inf or top < bottom - EPS:
        return None
    return top


def _cap_layers(cells, planes, cell: float, layers: int, side: Optional[float] = None):
    """Fine layers above the top cell of each column: the cells are ``layers`` fine layers high (``cell / layers`` <=
    ``TOP_STEP``), and above the top cell of a column as many whole fine layers are added as stay inside the part at
    every corner of the column. The top of the voxel form then lies at most one fine layer (or the slope across one
    column) under the smooth part instead of up to a whole cell."""
    fine = cell / layers
    side = side or cell
    columns: Dict[Tuple[int, int], int] = {}
    for ix, iy, iz in cells:
        if columns.get((ix, iy), iz - 1) < iz:
            columns[(ix, iy)] = iz
    out = set()
    for (ix, iy), iz in columns.items():
        corners = [_top_z(planes, (ix + a) * side, (iy + b) * side) for a in (0, 1) for b in (0, 1)]
        if any(c is None for c in corners):
            continue
        room = min(corners) - (iz + 1) * cell
        for k in range(max(0, int(math.floor(room / fine + EPS)))):
            out.add((ix, iy, (iz + 1) * layers + k))
    return out


def _merged_faces(cells: Set[Tuple[int, int, int]], roles: Dict[Tuple[int, int], str], cell,
                  origin: Vec = (0.0, 0.0, 0.0)):
    """Quads ``(corners, role)`` of the surface of ``cells``: faces towards air only, neighbours of one direction and
    slice merged into rectangles (greedy: along u first, then along v). ``cell``: a number or a size per axis."""
    if not isinstance(cell, (tuple, list)):
        cell = (cell, cell, cell)
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
                    plane = origin[axis] + (layer + (1 if sign > 0 else 0)) * cell[axis]
                    corners = []
                    for du, dv in ((0, 0), (w, 0), (w, h), (0, h)):
                        point = [0.0, 0.0, 0.0]
                        point[axis] = plane
                        point[u_axis] = origin[u_axis] + (u + du) * cell[u_axis]
                        point[v_axis] = origin[v_axis] + (v + dv) * cell[v_axis]
                        corners.append(tuple(point))
                    if sign < 0:
                        corners.reverse()
                    quads.append((corners, roles[(axis, sign)]))
    return quads


def _lid(mesh, part: Part, planes, top: float, cell: float, fallback: str):
    """``(split height, quads)`` of a lid: the exact top slab of a closed convex part, from the last grid layer under
    ``top - TOP_STEP`` up to the top - the part's own vertices above that height plus where its edges cross it, as a
    convex hull (so round rims, bevels and domes stay as smooth as the smooth model, inside it by construction).
    The slab's bottom face is left out (the cubes end there). None when the part is too low or the slab costs more
    than ``LID_FACTOR`` triangles per face of the part."""
    split = math.floor((top - TOP_STEP) / cell + EPS) * cell
    if split <= cell:
        return None
    points = set()
    for fi in part.face_indices():
        pts = [mesh.verts[i] for i in mesh.faces[fi]]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            for q in (a, b):
                if q[2] >= split - 1e-6:
                    points.add(tuple(round(c, 6) + 0.0 for c in (q[0], q[1], max(q[2], split))))
            if (a[2] - split) * (b[2] - split) < -1e-12:
                t = (split - a[2]) / (b[2] - a[2])
                points.add(tuple(round(a[i] + (b[i] - a[i]) * t, 6) + 0.0 for i in range(2)) + (split,))
    points = sorted(points)
    triangles = _hull(points)
    if not triangles or len(triangles) > LID_FACTOR * len(part.face_indices()):
        return None
    quads = []
    for tri in triangles:
        corners = [points[i] for i in tri]
        if all(abs(c[2] - split) < 1e-6 for c in corners):
            continue  # the bottom of the slab: under it the cubes end
        nrm = v_norm(v_cross(v_sub(corners[1], corners[0]), v_sub(corners[2], corners[0])))
        best = max(planes, key=lambda pl: (v_dot(pl[0], nrm), pl[2]))
        quads.append((corners, best[3] if best else fallback))
    return split, quads


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
    cells = _cells(planes, lo, hi, (cell, cell, cell))
    if not cells:
        return None
    fallback = Counter(mesh.roles[fi] for fi in part.face_indices()).most_common(1)[0][0]
    roles = _direction_roles(planes, fallback)
    layers = max(1, math.ceil(cell / TOP_STEP - EPS))
    lid = _lid(mesh, part, planes, hi[2], cell, fallback)
    if lid:  # the exact top slab of the part; the cubes end under it
        split, lid_quads = lid
        cells = {c for c in cells if (c[2] + 1) * cell <= split + EPS}
        caps = set()
    else:
        lid_quads = []
        caps = _cap_layers(cells, planes, cell, layers)
    if not cells:
        return None
    fine = {(ix, iy, iz * layers + k) for ix, iy, iz in cells for k in range(layers)} | caps
    return _merged_faces(fine, roles, (cell, cell, cell / layers)) + lid_quads


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


def _hull(points: Sequence[Vec]) -> Optional[List[Tuple[int, int, int]]]:
    """Triangles (index triples, outward winding) of the convex hull of ``points`` - incremental, O(n^2), for the few
    dozen vertices of a part. None when the points are flat. Coplanar points do not extend the hull."""
    n = len(points)
    tol = 1e-9

    def normal(a, b, c):
        return v_cross(v_sub(points[b], points[a]), v_sub(points[c], points[a]))

    def side(face, p):
        a, b, c = face
        return v_dot(normal(a, b, c), v_sub(points[p], points[a]))

    base = None
    for a in range(n):
        for b in range(a + 1, n):
            if v_dot(v_sub(points[b], points[a]), v_sub(points[b], points[a])) < 1e-12:
                continue
            for c in range(b + 1, n):
                if v_dot(normal(a, b, c), normal(a, b, c)) < 1e-12:
                    continue
                for d in range(c + 1, n):
                    if abs(side((a, b, c), d)) > 1e-9:
                        base = (a, b, c, d)
                        break
                if base:
                    break
            if base:
                break
        if base:
            break
    if base is None:
        return None
    a, b, c, d = base
    faces = [(a, b, c), (a, c, d), (a, d, b), (b, d, c)]
    centre = tuple(sum(points[i][k] for i in base) / 4 for k in range(3))
    def oriented(face):
        a, b, c = face
        nrm = normal(a, b, c)
        return face if v_dot(nrm, v_sub(centre, points[a])) < 0 else (a, c, b)

    faces = [oriented(f) for f in faces]
    for p in range(n):
        if p in base:
            continue
        visible = [f for f in faces if side(f, p) > tol]
        if not visible:
            continue
        edges = Counter()
        for f in visible:
            for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                edges[e] += 1
        keep = [f for f in faces if f not in visible]
        for (u, v) in sorted(edges):
            if (v, u) not in edges:  # a horizon edge: its other side stays
                keep.append((u, v, p))
        faces = keep
    return faces


def _top_deficit(points, triangles, candidates) -> Optional[Vec]:
    """The candidate vertex that sticks out most above (or beside) the hull ``triangles`` of ``points`` by more than
    ``TOP_STEP``, or None."""
    planes = []
    for a, b, c in triangles:
        nrm = v_cross(v_sub(points[b], points[a]), v_sub(points[c], points[a]))
        length = math.sqrt(v_dot(nrm, nrm))
        if length < 1e-12:
            continue
        nrm = (nrm[0] / length, nrm[1] / length, nrm[2] / length)
        planes.append((nrm, v_dot(nrm, points[a]), 0.0, ""))
    worst, best = None, TOP_STEP
    have = set(points)
    for p in candidates:
        if p in have:
            continue
        top = _top_z(planes, p[0], p[1])
        gap = math.inf if top is None else p[2] - top
        if gap > best:
            worst, best = p, gap
    return worst


def facet_part(mesh, part: Part):
    """Quads of the faceted form of one closed convex part (the hull of a farthest-point subset of its vertices), or
    None when the part stays as it is."""
    if not part.closed or part.v1 - part.v0 < FACET_MIN_VERTS:
        return None
    verts = mesh.verts[part.v0:part.v1]
    ext = sorted(max(v[i] for v in verts) - min(v[i] for v in verts) for i in range(3))
    if ext[0] < FACET_FLAT * ext[1]:
        return None  # a disc or a plate: a few of its vertices make shards, not facets
    planes = _planes(mesh, part)
    if not planes:
        return None
    unique = sorted({tuple(round(c, 6) + 0.0 for c in v) for v in mesh.verts[part.v0:part.v1]})
    if len(unique) < FACET_MIN_VERTS:
        return None
    target = max(FACET_FLOOR, len(unique) // FACET_KEEP)
    chosen = [min(range(len(unique)), key=lambda i: (unique[i][2], unique[i][1], unique[i][0]))]
    far = [math.inf] * len(unique)
    while len(chosen) < target:
        last = unique[chosen[-1]]
        for i, p in enumerate(unique):
            d = v_dot(v_sub(p, last), v_sub(p, last))
            far[i] = min(far[i], d)
        chosen.append(max((i for i in range(len(unique)) if i not in chosen), key=lambda i: (far[i], -i)))
    points = [unique[i] for i in sorted(chosen)]
    triangles = _hull(points)
    # Keep the top: add original vertices while one lies more than TOP_STEP above the hull (round tops and rims
    # must not sink; the hull is inside the part, so only a missing vertex can lower the walkable surface).
    while triangles:
        worst = _top_deficit(points, triangles, unique)
        if worst is None:
            break
        points = sorted(set(points) | {worst})
        triangles = _hull(points)
    if not triangles or len(triangles) >= len(part.face_indices()) * 2:
        return None  # no gain: the part is faceted enough
    fallback = Counter(mesh.roles[fi] for fi in part.face_indices()).most_common(1)[0][0]
    quads = []
    for tri in triangles:
        corners = [points[i] for i in tri]
        nrm = v_norm(v_cross(v_sub(corners[1], corners[0]), v_sub(corners[2], corners[0])))
        best = max(planes, key=lambda pl: (v_dot(pl[0], nrm), pl[2]))
        quads.append((corners, best[3] if best else fallback))
    return quads


def holes_part(mesh, part: Part):
    """Quads of the perforated form of one closed convex plate, or None when it is no plate or too small."""
    if not part.closed:
        return None
    verts = mesh.verts[part.v0:part.v1]
    lo = tuple(min(v[i] for v in verts) for i in range(3))
    hi = tuple(max(v[i] for v in verts) for i in range(3))
    ext = [hi[i] - lo[i] for i in range(3)]
    thin = min(range(3), key=lambda i: ext[i])
    others = [i for i in range(3) if i != thin]
    if ext[thin] > HOLE_THIN or any(ext[i] < HOLE_RATIO * ext[thin] for i in others):
        return None
    cell_plane = min(HOLE_MAX, max(HOLE_MIN, min(ext[i] for i in others) / 8))
    if any(ext[i] < 8 * cell_plane for i in others):
        return None
    planes = _planes(mesh, part)
    if not planes:
        return None
    for sign in (1, -1):  # a true slab: both big faces face along the thin axis
        if not any(pl[0][thin] * sign > 0.999 for pl in planes):
            return None
    cell = [cell_plane] * 3
    cell[thin] = ext[thin] * HOLE_LAYER
    origin = [0.0, 0.0, 0.0]
    for i in others:  # cells counted from the plate's corner: a regular grid with an even rim
        n = int(ext[i] // cell_plane)
        origin[i] = lo[i] + (ext[i] - n * cell_plane) / 2
    origin[thin] = (lo[thin] + hi[thin]) / 2 - cell[thin] / 2 - 0.0
    cells = _cells(planes, lo, hi, tuple(cell), tuple(origin))
    if not cells:
        return None
    iu = [c[others[0]] for c in cells]
    iv = [c[others[1]] for c in cells]
    u0, u1, v0, v1 = min(iu), max(iu), min(iv), max(iv)
    kept = {c for c in cells
            if not (u0 < c[others[0]] < u1 and v0 < c[others[1]] < v1 and (c[others[0]] - u0) % 2 == 1
                    and (c[others[1]] - v0) % 2 == 1)}
    if len(kept) == len(cells):
        return None
    fallback = Counter(mesh.roles[fi] for fi in part.face_indices()).most_common(1)[0][0]
    return _merged_faces(kept, _direction_roles(planes, fallback), tuple(cell), tuple(origin))


def _tris(quads) -> int:
    return sum(len(corners) - 2 for corners, _ in quads)


def _derive(asset, form: str, make, skip_names=(), budget: Optional[int] = None) -> Dict[str, object]:
    """Replace, in place, every part ``make(mesh, part)`` gives quads for - in decorative objects of a model without a
    pick-up behaviour; with ``budget`` a part is only taken while the model's triangles stay within it. Returns the summary (also kept in ``asset.meta['derived_shape']`` when a part changed)."""
    before = asset.stats()["triangles"]
    running = before
    converted = 0
    if not any(b["script"] == "ItemPickup" for b in asset.behaviours):
        for obj in asset.meshes():
            if obj.name not in DECORATIVE_PARTS or obj.name in skip_names:
                continue
            replaced = []
            for part in obj.mesh.parts:
                quads = make(obj.mesh, part)
                if not quads:
                    continue
                grown = _tris(quads) - sum(len(obj.mesh.faces[fi]) - 2 for fi in part.face_indices())
                if budget is not None and grown > 0 and running + grown > budget:
                    continue
                running += grown
                replaced.append((part, quads))
            if replaced:
                _replace(obj.mesh, replaced)
                converted += len(replaced)
    info = {"form": form, "parts": converted, "triangles_before": before, "triangles_after": asset.stats()["triangles"]}
    if converted:  # a model nothing was derived from stays exactly the smooth model
        asset.meta[META_KEY] = info
    return info


def voxelize(asset, cell: Optional[float] = None) -> Dict[str, object]:
    """The voxel form (see the module docstring); ``info['cell']`` is the grid cell."""
    cell = cell or cell_size(asset)
    info = _derive(asset, "voxel", lambda mesh, part: voxelize_part(mesh, part, cell))
    info["cell"] = cell
    if META_KEY in asset.meta:
        asset.meta[META_KEY]["cell"] = cell
    return info


def facet(asset) -> Dict[str, object]:
    return _derive(asset, "facet", facet_part)


def perforate(asset, pivot: str = "", budget: Optional[int] = None) -> Dict[str, object]:
    """The perforated form; a walking surface (pivot ``top``) keeps its plates, and plates are only perforated while
    the model stays within the triangle ``budget`` (holes cost triangles)."""
    if pivot == "top":
        return _derive(asset, "holes", lambda mesh, part: None)
    return _derive(asset, "holes", holes_part, budget=budget)


def apply_shape(asset, shape: str, pivot: str = "", budget: Optional[int] = None) -> Optional[Dict[str, object]]:
    if shape == "voxel":
        return voxelize(asset)
    if shape == "facet":
        return facet(asset)
    if shape == "holes":
        return perforate(asset, pivot, budget)
    return None
