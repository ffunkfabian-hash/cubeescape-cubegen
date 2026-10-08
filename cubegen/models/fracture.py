"""Fractured variant of any model (global style ``damage`` = ``fractured``).

The model looks intact but consists of fragments ``Fragment_<nn>``: Voronoi cells
around a few seeded points cut every convex closed primitive (boxes, chamfered
boxes, cylinders ...) into pieces, the cut faces get the fracture material.
Other primitives (open shells, concave shapes) go whole to the cell of their
centre. Generation 1/2 retain their historical fragment meshes and convex hulls.
Generation 3 uses a Fragment parent per region, with one Shard mesh/collider per
primitive, so hulls never join disconnected geometry. Non-convex shards keep exact
fixed mesh collision and require decomposition before a dynamic release. Unity
authors one rigid body per approved compound parent. Until explicitly released
the model is decoration (no scripts); its random stream is separate from the model.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Dict, List, Tuple

from ..geometry import Mesh, Prim, add_up, box, face_normal, v_cross, v_dot, v_norm, v_sub
from ..seeds import StableRandom

FRACTURE = "M_Ground"
EPS = 1e-7
_BOX_FACES = box(1, 1, 1, "").faces

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


def _box_topology(points, faces):
    return len(points) == 8 and faces == _BOX_FACES


def _planar_faces(points, faces):
    if any(not math.isfinite(c) for p in points for c in p):
        return False
    for face in faces:
        normal = face_normal([points[i] for i in face])
        if any(abs(v_dot(normal, v_sub(points[j], points[face[0]]))) > 1e-6 for j in face):
            return False
    return True


def _deformed_box_parts(prim: Prim):
    """Bounded exact partition of a warped box using the existing face fan.

    Twelve oriented boundary triangles cone to a proven interior point. Only
    adjacent tetrahedra whose unchanged boundary is convex may be merged. Render
    meshes are explicit triangles, so convex cooking cannot flatten a warped quad.
    Unsupported topology, inverted triangles or a missing kernel stay fixed.
    """
    if not prim.closed or not _box_topology(prim.verts, prim.faces):
        return None
    if _planar_faces(prim.verts, prim.faces) and _convex(prim.verts, prim.faces):
        return None
    if any(not math.isfinite(c) for p in prim.verts for c in p):
        return None
    triangles = [(tuple((face[0], face[i], face[i + 1])), role)
                 for face, role in zip(prim.faces, prim.roles) for i in (1, 2)]
    return _star_partition(prim, triangles)


def _star_partition(prim: Prim, triangles, search_kernel=False):
    """Reuse the bounded exact volume partition for connected genus-zero surfaces.

    No hull fitting: boundary triangles remain unchanged. A proven strict kernel
    and a single spherical winding prevent a partition across holes/overlaps.
    """
    if not prim.closed or not 4 <= len(prim.verts) <= 64 or not 4 <= len(triangles) <= 128:
        return None
    if any(not math.isfinite(c) for p in prim.verts for c in p):
        return None
    used, edges, adjacent = set(), {}, [set() for _ in prim.verts]
    for face, _ in triangles:
        if len(set(face)) != 3 or any(not 0 <= v < len(prim.verts) for v in face):
            return None
        used.update(face)
        for a, b in zip(face, face[1:] + face[:1]):
            edges.setdefault(tuple(sorted((a, b))), []).append((a, b))
            adjacent[a].add(b); adjacent[b].add(a)
    if len(used) != len(prim.verts) or len(used) - len(edges) + len(triangles) != 2:
        return None
    if any(len(pair) != 2 or pair[0] != tuple(reversed(pair[1])) for pair in edges.values()):
        return None
    visited, pending = set(), [0]
    while pending:
        v = pending.pop()
        if v not in visited:
            visited.add(v); pending.extend(adjacent[v] - visited)
    if len(visited) != len(used):
        return None
    center = tuple(add_up(p[k] for p in prim.verts) / len(prim.verts) for k in range(3))
    if search_kernel:
        planes = [(face_normal([prim.verts[v] for v in face]), prim.verts[face[0]]) for face, _ in triangles]
        if any(v_dot(n, n) < .5 for n, _ in planes):
            return None
        span = max(max(p[k] for p in prim.verts) - min(p[k] for p in prim.verts) for k in range(3))
        min_area = min(math.sqrt(v_dot(cross, cross)) for face, _ in triangles
                       for cross in [v_cross(v_sub(prim.verts[face[1]], prim.verts[face[0]]),
                                             v_sub(prim.verts[face[2]], prim.verts[face[0]]))])
        margin = max(1e-7, span * 1e-6, 1.1e-8 / min_area)
        origin, active = center, []
        for _ in range(128):
            index = max(range(len(planes)), key=lambda i: v_dot(planes[i][0], v_sub(center, planes[i][1])))
            normal, point = planes[index]
            if index not in active: active.append(index)
            outside = v_dot(normal, v_sub(center, point)) + margin
            if outside <= 1e-12:
                break
            center = tuple(center[k] - outside * normal[k] for k in range(3))
        def strict(candidate):
            return all(v_dot(v_sub(prim.verts[a], candidate), v_cross(v_sub(prim.verts[b], candidate),
                       v_sub(prim.verts[c], candidate))) > 1e-8 for (a, b, c), _ in triangles)
        if not strict(center):
            # Nearly opposing constraints converge slowly. Solve their two-plane
            # projection directly, bounded to 16 active planes; all faces still verify it.
            for i, j in combinations(active[:16], 2):
                n, a = planes[i]; m, b = planes[j]
                rho = v_dot(n, m); divisor = 1 - rho * rho
                if divisor <= 1e-12: continue
                first = v_dot(n, v_sub(origin, a)) + margin
                second = v_dot(m, v_sub(origin, b)) + margin
                alpha = (first - rho * second) / divisor
                beta = (second - rho * first) / divisor
                candidate = tuple(origin[k] - alpha * n[k] - beta * m[k] for k in range(3))
                if strict(candidate):
                    center = candidate; break
    center_index = len(prim.verts)
    points = prim.verts + [center]
    cells, volume, winding = [], 0.0, 0.0
    for (a, b, c), role in triangles:
        u, v, w = (v_sub(points[i], center) for i in (a, b, c))
        determinant = v_dot(u, v_cross(v, w))
        if determinant <= 1e-8:
            return None
        volume += determinant / 6
        lengths = [math.sqrt(v_dot(p, p)) for p in (u, v, w)]
        denominator = lengths[0] * lengths[1] * lengths[2] + v_dot(u, v) * lengths[2] + v_dot(v, w) * lengths[0] + v_dot(w, u) * lengths[1]
        winding += 2 * math.atan2(determinant, denominator)
        cells.append([((a, b, c), role), ((a, center_index, b), FRACTURE), ((b, center_index, c), FRACTURE), ((c, center_index, a), FRACTURE)])
    if abs(winding - 4 * math.pi) > 1e-6:
        return None
    # A warped quad may still triangulate to a convex solid: keep one exact shape.
    if _convex(prim.verts, [face for face, _ in triangles]):
        return [Prim(prim.verts, [face for face, _ in triangles], [role for _, role in triangles])]
    merged = True
    while merged:
        merged = False
        for i, first in enumerate(cells):
            first_keys = {tuple(sorted(face)) for face, _ in first}
            for j in range(i + 1, len(cells)):
                second = cells[j]
                shared = first_keys & {tuple(sorted(face)) for face, _ in second}
                if not shared:
                    continue
                union = [(face, role) for face, role in first + second if tuple(sorted(face)) not in shared]
                vertices = sorted({v for face, _ in union for v in face})
                index = {old: new for new, old in enumerate(vertices)}
                if not _convex([points[v] for v in vertices], [tuple(index[v] for v in face) for face, _ in union]):
                    continue
                cells[i] = union; cells.pop(j); merged = True
                break
            if merged:
                break
    result = []
    for cell in cells:
        vertices = sorted({v for face, _ in cell for v in face})
        index = {old: new for new, old in enumerate(vertices)}
        piece = Prim([points[v] for v in vertices], [tuple(index[v] for v in face) for face, _ in cell], [role for _, role in cell])
        edges = {}
        for face in piece.faces:
            for a, b in zip(face, face[1:] + face[:1]):
                edge = tuple(sorted((a, b))); edges[edge] = edges.get(edge, 0) + 1
        if any(count != 2 for count in edges.values()) or not _convex(piece.verts, piece.faces):
            return None
        result.append(piece)
    mesh = Mesh()
    for piece in result: mesh.add(piece)
    if abs(sum(mesh.part_volume(p) for p in mesh.parts) - volume) > max(1e-9, volume * 1e-7):
        return None
    return result


def _radial_parts(prim: Prim):
    if not prim.closed or len(prim.verts) > 64:
        return None
    triangles = [(tuple((face[0], face[i], face[i + 1])), role)
                 for face, role in zip(prim.faces, prim.roles) for i in range(1, len(face) - 1)]
    return _star_partition(prim, triangles, search_kernel=True)


def _convex_recipe_parts(prim: Prim):
    """Validate exact procedural wall sectors after all model transforms.

    New faces close each sector, never the central opening. Invalid or deformed
    recipes fall back to the original exact fixed mesh; no approximate hulls.
    """
    if not prim.convex_faces:
        return None
    pieces = []
    for recipe in prim.convex_faces:
        vertices = sorted({v for face, _ in recipe for v in face})
        index = {old: new for new, old in enumerate(vertices)}
        points = [prim.verts[i] for i in vertices]
        center = tuple(add_up(p[k] for p in points) / len(points) for k in range(3))
        faces, roles = [], []
        for original, role in recipe:
            face = tuple(index[v] for v in original)
            normal = face_normal([points[v] for v in face])
            # Convex cooking must not replace a warped quad by a different surface.
            if any(abs(v_dot(normal, v_sub(points[v], points[face[0]]))) > 1e-6 for v in face):
                return None
            if v_dot(normal, v_sub(center, points[face[0]])) > 0:
                face = tuple(reversed(face))
            faces.append(face)
            roles.append(role)
        edges = {}
        for face in faces:
            for a, b in zip(face, face[1:] + face[:1]):
                edge = (min(a, b), max(a, b))
                edges[edge] = edges.get(edge, 0) + 1
        if not edges or any(count != 2 for count in edges.values()) or not _convex(points, faces):
            return None
        piece = Prim(points, faces, roles, closed=True)
        mesh = Mesh()
        if mesh.part_volume(mesh.add(piece)) <= 1e-8:
            return None
        pieces.append(piece)
    return pieces


def _convex_components(prim: Prim) -> List[Prim]:
    """Use validated round-wall recipes or recover existing convex structural parts.

    Connectivity uses original vertex indices, never welded positions: touching or
    overlapping profile boxes remain independent exact shapes. Unsupported shells
    and genuinely concave connected meshes are returned unchanged. No hull fitting,
    new surfaces in structural recovery or runtime decomposition is involved.
    Round-wall recipes add the cap faces needed to close each exact wall sector.
    """
    box_parts = _deformed_box_parts(prim)
    if box_parts is not None:
        return box_parts
    if _box_topology(prim.verts, prim.faces) and not _planar_faces(prim.verts, prim.faces):
        return [prim]
    if prim.closed and _planar_faces(prim.verts, prim.faces) and _convex(prim.verts, prim.faces):
        return [prim]
    recipe = _convex_recipe_parts(prim)
    if recipe is not None:
        return recipe
    radial = _radial_parts(prim)
    if radial is not None:
        return radial
    if not prim.closed:
        return [prim]
    adjacent = [set() for _ in prim.verts]
    used = set()
    for face in prim.faces:
        used.update(face)
        for a, b in zip(face, face[1:] + face[:1]):
            adjacent[a].add(b)
            adjacent[b].add(a)
    groups = []
    while used:
        pending = [min(used)]
        group = set()
        while pending:
            vertex = pending.pop()
            if vertex in group:
                continue
            group.add(vertex)
            pending.extend(adjacent[vertex] - group)
        used.difference_update(group)
        groups.append(group)
    if len(groups) < 2:
        return [prim]
    pieces = []
    for group in groups:
        vertices = sorted(group)
        index = {old: new for new, old in enumerate(vertices)}
        selected = [i for i, face in enumerate(prim.faces) if face[0] in group]
        faces = [tuple(index[v] for v in prim.faces[i]) for i in selected]
        points = [prim.verts[i] for i in vertices]
        edges = {}
        for face in faces:
            for a, b in zip(face, face[1:] + face[:1]):
                edge = (min(a, b), max(a, b))
                edges[edge] = edges.get(edge, 0) + 1
        if not edges or any(count != 2 for count in edges.values()) or not _convex(points, faces):
            return [prim]
        piece = Prim(points, faces, [prim.roles[i] for i in selected], closed=True)
        mesh = Mesh()
        if mesh.part_volume(mesh.add(piece)) <= 1e-8:
            return [prim]
        pieces.append(piece)
    return pieces


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


def fracture_asset(asset, seed: int, pivot: str, pieces: int = 0, generation: int = 1) -> int:
    """Replace the model's parts by ``Fragment_<nn>`` parts (compound colliders in generation 3); returns the fragment count."""
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
            warped_box = generation >= 3 and not _planar_faces(pts, faces)
            if extent < big or not part.closed or not _convex(pts, faces) or warped_box:  # small or not cuttable: whole
                prim = Prim(pts, faces, roles, part.closed, part.convex_faces)
                pieces = _convex_components(prim) if generation >= 3 else [prim]
                fragments[_cell(centre, sites)].extend(pieces)
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
        centre = ((a0 + a1) / 2, (b0 + b1) / 2, (c0 + c1) / 2)
        if generation < 3:
            mesh = asset.part(name, pivot=centre)
            for prim in prims:
                mesh.add(prim, name="fragment")
            asset.mesh_collider(name, convex=True)
        else:
            # A Voronoi region can contain disconnected bars or an open shell.
            # Their combined convex hull would seal gaps. Keep a compound body:
            # one mesh/shape per original convex piece, under one fragment pivot.
            # Match the sidecar grid before Blender stores Empty locations as float32.
            # Half-grid pivots otherwise round differently in the FBX and sidecar.
            centre = tuple(round(v, 4) for v in centre)
            asset.empty(name, centre)
            for index, prim in enumerate(prims, 1):
                child = f"Shard_{count:02d}_{index:03d}"
                mesh = asset.part(child, pivot=centre, parent=name)
                mesh.add(prim, name="fragment")
                planar_box = _planar_faces(prim.verts, prim.faces)
                asset.mesh_collider(child, convex=prim.closed and planar_box and _convex(prim.verts, prim.faces))
    asset.meta["damage"] = "fractured"
    asset.meta["fragments"] = count
    return count


__all__ = ["fracture_asset"]
