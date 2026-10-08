"""Pure-Python low-poly mesh construction.

Everything in here runs both in a normal Python interpreter (for tests, stats
and the OBJ fallback exporter) and inside Blender's bundled Python. No bpy,
no numpy.

Conventions
-----------
* Z is up, units are metres (Blender default). The glTF/FBX exporters convert
  to Y-up for the game engine.
* Faces are lists of vertex indices, counter-clockwise when seen from outside,
  so normals point outwards.
* Every face carries a material name (e.g. ``"M_RobotDark"``), matching the
  Unity materials of Cube Escape. One mesh may use several materials.
* The FRONT of an asset looks towards -Y (Blender "Front" view, Unity +Z).
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Vec2 = Tuple[float, float]


# --------------------------------------------------------------------------
# small vector / matrix helpers
# --------------------------------------------------------------------------

def add_up(values) -> float:
    """Sum of floats, strictly left to right.

    Use this instead of ``sum()`` for geometry: Python 3.12 made ``sum()`` of
    floats more precise (compensated), so 3.11 (Blender) and 3.12+ (CLI) would
    differ in the last bit - enough to change a face's start vertex.
    """
    total = 0.0
    for v in values:
        total += v
    return total


def v_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_scale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def v_cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_len(a: Vec3) -> float:
    return math.sqrt(v_dot(a, a))


def v_norm(a: Vec3) -> Vec3:
    length = v_len(a)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / length, a[1] / length, a[2] / length)


Mat3 = Tuple[Vec3, Vec3, Vec3]  # rows


def euler_matrix(rx: float, ry: float, rz: float) -> Mat3:
    """Rotation matrix for XYZ euler angles (radians), same order as Blender."""
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    # R = Rz * Ry * Rx
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def basis_matrix(x_axis: Vec3, y_axis: Vec3, z_axis: Vec3) -> Mat3:
    """Matrix that maps local x/y/z onto the given world axes."""
    return (
        (x_axis[0], y_axis[0], z_axis[0]),
        (x_axis[1], y_axis[1], z_axis[1]),
        (x_axis[2], y_axis[2], z_axis[2]),
    )


def mat_mul_vec(m: Mat3, v: Vec3) -> Vec3:
    return (v_dot(m[0], v), v_dot(m[1], v), v_dot(m[2], v))


def transform_points(
    points: Iterable[Vec3],
    scale: Sequence[float] = (1.0, 1.0, 1.0),
    rot: Sequence[float] = (0.0, 0.0, 0.0),
    loc: Sequence[float] = (0.0, 0.0, 0.0),
    basis: Optional[Mat3] = None,
) -> List[Vec3]:
    """Scale, then orient (basis), then rotate (euler XYZ), then translate."""
    rmat = euler_matrix(*rot) if any(rot) else None
    out = []
    for p in points:
        q = (p[0] * scale[0], p[1] * scale[1], p[2] * scale[2])
        if basis is not None:
            q = mat_mul_vec(basis, q)
        if rmat is not None:
            q = mat_mul_vec(rmat, q)
        out.append((q[0] + loc[0], q[1] + loc[1], q[2] + loc[2]))
    return out


# --------------------------------------------------------------------------
# primitives (local space, return verts/faces/roles)
# --------------------------------------------------------------------------

class Prim:
    """A primitive in local space: vertices, faces and one role per face."""

    __slots__ = ("verts", "faces", "roles", "closed", "convex_faces")

    def __init__(self, verts, faces, roles, closed=True, convex_faces=None):
        self.verts: List[Vec3] = list(verts)
        self.faces: List[Tuple[int, ...]] = [tuple(f) for f in faces]
        self.roles: List[str] = list(roles)
        self.closed = closed
        # Optional exact decomposition recipe over the existing vertex indices.
        # Used only by current fractured exports; normal/historical meshes stay intact.
        self.convex_faces = convex_faces


def box(
    sx: float,
    sy: float,
    sz: float,
    role: str,
    top_role: Optional[str] = None,
    bottom_role: Optional[str] = None,
    top_scale: Sequence[float] = (1.0, 1.0),
    top_offset: Sequence[float] = (0.0, 0.0),
    loc: Sequence[float] = (0.0, 0.0, 0.0),
) -> Prim:
    """Axis aligned box centred on the origin.

    ``top_scale`` tapers the top face (frustum), ``top_offset`` shears it.
    ``loc`` shifts the box after construction for composing compound profiles.
    """
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    tx, ty = x * top_scale[0], y * top_scale[1]
    ox, oy = top_offset
    verts = [
        (-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
        (-tx + ox, -ty + oy, z), (tx + ox, -ty + oy, z), (tx + ox, ty + oy, z), (-tx + ox, ty + oy, z),
    ]
    if any(loc):
        verts = [v_add(v, loc) for v in verts]
    faces = [
        (0, 3, 2, 1),  # bottom
        (4, 5, 6, 7),  # top
        (0, 1, 5, 4),  # front (-y)
        (1, 2, 6, 5),  # right (+x)
        (2, 3, 7, 6),  # back (+y)
        (3, 0, 4, 7),  # left (-x)
    ]
    roles = [bottom_role or role, top_role or role, role, role, role, role]
    return Prim(verts, faces, roles)


def lathe(
    profile: Sequence[Vec2],
    sides: int,
    role,
    cap_bottom: bool = True,
    cap_top: bool = True,
    cap_bottom_role: Optional[str] = None,
    cap_top_role: Optional[str] = None,
    angle_offset: float = 0.0,
) -> Prim:
    """Surface of revolution around Z.

    ``profile`` is a list of ``(radius, z)`` from bottom to top along the
    *outside* of the shape. A radius of 0 creates a pole. ``role`` is either a
    single role or one role per profile segment.
    """
    if sides < 3:
        raise ValueError("lathe needs at least 3 sides")
    seg_roles = [role] * (len(profile) - 1) if isinstance(role, str) else list(role)
    if len(seg_roles) != len(profile) - 1:
        raise ValueError("need one role per profile segment")

    verts: List[Vec3] = []
    faces: List[Tuple[int, ...]] = []
    roles: List[str] = []
    rings: List[List[int]] = []
    for r, z in profile:
        if r <= 1e-9:
            rings.append([len(verts)])
            verts.append((0.0, 0.0, z))
        else:
            ring = []
            for j in range(sides):
                a = angle_offset + 2.0 * math.pi * j / sides
                ring.append(len(verts))
                verts.append((r * math.cos(a), r * math.sin(a), z))
            rings.append(ring)

    for i in range(len(rings) - 1):
        a_ring, b_ring = rings[i], rings[i + 1]
        if len(a_ring) == 1 and len(b_ring) == 1:
            continue
        for j in range(sides):
            j2 = (j + 1) % sides
            if len(a_ring) == 1:
                faces.append((a_ring[0], b_ring[j2], b_ring[j]))
            elif len(b_ring) == 1:
                faces.append((a_ring[j], a_ring[j2], b_ring[0]))
            else:
                faces.append((a_ring[j], a_ring[j2], b_ring[j2], b_ring[j]))
            roles.append(seg_roles[i])

    closed = True
    first, last = rings[0], rings[-1]
    if len(first) > 1:
        if cap_bottom:
            faces.append(tuple(reversed(first)))
            roles.append(cap_bottom_role or seg_roles[0])
        else:
            closed = False
    if len(last) > 1:
        if cap_top:
            faces.append(tuple(last))
            roles.append(cap_top_role or seg_roles[-1])
        else:
            closed = False
    recipe = _lathe_convex_faces(profile, rings, sides, seg_roles, cap_bottom, cap_top,
                                 cap_bottom_role, cap_top_role) if closed else None
    return Prim(verts, faces, roles, closed, recipe)


def _lathe_convex_faces(profile, rings, sides, seg_roles, cap_bottom, cap_top,
                        cap_bottom_role, cap_top_role):
    """Exact recipes for bounded axial solids and closed radial cross-sections.

    Only original ring vertices are used. Monotone axial bands are frusta;
    folded profiles with axis endpoints use convex radial polygon sectors.
    Validation after all model transformations rejects warped or invalid pieces.
    """
    if not 2 <= len(profile) <= 128 or sides > 128:
        return None
    if any(not math.isfinite(v) for point in profile for v in point) or any(r < 0 for r, _ in profile):
        return None
    def band(a, b):
        result = []
        for j in range(sides):
            j2 = (j + 1) % sides
            face = tuple(dict.fromkeys((rings[a][j if len(rings[a]) > 1 else 0],
                                        rings[a][j2 if len(rings[a]) > 1 else 0],
                                        rings[b][j2 if len(rings[b]) > 1 else 0],
                                        rings[b][j if len(rings[b]) > 1 else 0])))
            if len(face) >= 3: result.append((face, seg_roles[a]))
        return result
    lo, hi = 0, len(profile) - 1
    # A terminal pole on the same plane is an existing flat cap, not a zero-volume band.
    if len(rings[lo]) == 1 and profile[lo][1] == profile[lo + 1][1]: lo += 1
    if len(rings[hi]) == 1 and profile[hi][1] == profile[hi - 1][1]: hi -= 1
    if hi > lo and all(profile[i + 1][1] > profile[i][1] + 1e-9 for i in range(lo, hi)):
        pieces = []
        for i in range(lo, hi):
            if len(rings[i]) == len(rings[i + 1]) == 1:
                return None
            faces = band(i, i + 1)
            if len(rings[i]) > 1:
                bottom = seg_roles[0] if lo > 0 else cap_bottom_role or seg_roles[0]
                faces.append((tuple(reversed(rings[i])), bottom if i == lo else seg_roles[i]))
            if len(rings[i + 1]) > 1:
                top = seg_roles[-1] if hi < len(profile) - 1 else cap_top_role or seg_roles[-1]
                faces.append((tuple(rings[i + 1]), top if i == hi - 1 else seg_roles[i]))
            pieces.append(faces)
        return pieces
    if len(rings[0]) != 1 or len(rings[-1]) != 1:
        return None
    polygon = list(profile)
    indices = list(range(len(profile)))
    if _polygon_area(polygon) < 0:
        polygon.reverse(); indices.reverse()
    parts = _convex_polygon_parts(polygon, keep_convex=True)
    if not parts:
        return None
    pieces = []
    for j in range(sides):
        j2 = (j + 1) % sides
        for part in parts:
            original = [indices[v] for v in part]
            def vertex(i, angle): return rings[i][angle if len(rings[i]) > 1 else 0]
            faces = [(tuple(vertex(i, j) for i in original), seg_roles[0]),
                     (tuple(vertex(i, j2) for i in reversed(original)), seg_roles[0])]
            for a, b in zip(original, original[1:] + original[:1]):
                face = tuple(dict.fromkeys((vertex(a, j), vertex(a, j2), vertex(b, j2), vertex(b, j))))
                if len(face) >= 3:
                    role = seg_roles[min(a, b)] if abs(a - b) == 1 else seg_roles[0]
                    faces.append((face, role))
            pieces.append(faces)
    return pieces


def flat_front_offset(sides: int) -> float:
    """Angle offset that turns an n-sided prism so a flat side faces -Y (the front)."""
    return -math.pi / 2 + math.pi / sides


def cylinder(
    radius: float,
    depth: float,
    sides: int,
    role: str,
    radius_top: Optional[float] = None,
    cap_top_role: Optional[str] = None,
    cap_bottom_role: Optional[str] = None,
    bevel: float = 0.0,
    align_flat: bool = True,
) -> Prim:
    """Cylinder / frustum / cone along Z, centred on the origin.

    ``bevel`` chamfers both rims, ``align_flat`` turns a flat side to the front (-Y).
    """
    rt = radius if radius_top is None else radius_top
    h = depth / 2.0
    offset = flat_front_offset(sides) if align_flat else 0.0
    b = min(bevel, depth * 0.45, radius * 0.45, rt * 0.45 if rt > 0 else bevel)
    if b > 0 and rt > 0:
        profile = [(radius - b, -h), (radius, -h + b), (rt, h - b), (rt - b, h)]
    else:
        profile = [(radius, -h), (rt, h)]
    return lathe(profile, sides, role, cap_top_role=cap_top_role, cap_bottom_role=cap_bottom_role,
                 angle_offset=offset)


def chamfer_box(sx: float, sy: float, sz: float, role: str, bevel: float, top_role: Optional[str] = None) -> Prim:
    """Box with chamfered edges and corners (like a 1-segment bevel), centred on the origin."""
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    b = min(bevel, x * 0.45, y * 0.45, z * 0.45)
    if b <= 1e-6:
        return box(sx, sy, sz, role, top_role=top_role)
    verts: List[Vec3] = []
    idx: Dict[Tuple[int, int, int, int], int] = {}
    signs = (-1, 1)
    for cx in signs:
        for cy in signs:
            for cz in signs:
                idx[(cx, cy, cz, 0)] = len(verts)
                verts.append((cx * x, cy * (y - b), cz * (z - b)))
                idx[(cx, cy, cz, 1)] = len(verts)
                verts.append((cx * (x - b), cy * y, cz * (z - b)))
                idx[(cx, cy, cz, 2)] = len(verts)
                verts.append((cx * (x - b), cy * (y - b), cz * z))

    def corner(axis_values, kind):
        return idx[(axis_values[0], axis_values[1], axis_values[2], kind)]

    raw: List[Tuple[List[int], str]] = []
    for axis in range(3):  # the six main faces
        for s in signs:
            face = []
            for a in signs:
                for c in signs:
                    vals = [0, 0, 0]
                    vals[axis] = s
                    others = [k for k in range(3) if k != axis]
                    vals[others[0]], vals[others[1]] = a, c
                    face.append(corner(vals, axis))
            raw.append((face, top_role if (axis == 2 and s == 1 and top_role) else role))
    for axis in range(3):  # twelve edge faces, running along ``axis``
        i, j = [k for k in range(3) if k != axis]
        for si in signs:
            for sj in signs:
                face = []
                for s in signs:
                    vals = [0, 0, 0]
                    vals[i], vals[j], vals[axis] = si, sj, s
                    face += [corner(vals, i), corner(vals, j)]
                raw.append((face, role))
    for cx in signs:  # eight corner triangles
        for cy in signs:
            for cz in signs:
                raw.append(([idx[(cx, cy, cz, k)] for k in range(3)], role))

    faces, roles = [], []
    for face, r in raw:
        faces.append(_order_convex_face(verts, face))
        roles.append(r)
    return Prim(verts, faces, roles)


def _order_convex_face(verts: Sequence[Vec3], face: Sequence[int]) -> Tuple[int, ...]:
    """Counter-clockwise order (seen from outside) for a face of a convex body around the origin."""
    pts = [verts[i] for i in face]
    c = v_scale((add_up(p[0] for p in pts), add_up(p[1] for p in pts), add_up(p[2] for p in pts)), 1.0 / len(pts))
    n = v_norm(c)
    u = v_norm(v_sub(pts[0], c))
    w = v_cross(n, u)
    angles = [math.atan2(v_dot(v_sub(p, c), w), v_dot(v_sub(p, c), u)) for p in pts]
    ordered = [i for _, i in sorted(zip(angles, face))]
    if v_dot(face_normal([verts[i] for i in ordered]), c) < 0:
        ordered.reverse()
    return tuple(ordered)


def ring(r_in: float, r_out: float, depth: float, sides: int, role: str) -> Prim:
    """Flat band (hoop) around Z without the inner wall - meant to sit on a body."""
    h = depth / 2.0
    p = lathe(
        [(r_in, -h), (r_out, -h), (r_out, h), (r_in, h)],
        sides,
        role,
        cap_bottom=False,
        cap_top=False,
    )
    if 0 < r_in < r_out and depth > 0:
        p.convex_faces = _annular_sectors(sides, role)
    return p


def _annular_sectors(sides: int, role: str):
    """Closed angular wall sectors for four rings tracing an annular cross-section."""
    pieces = []
    for j in range(sides):
        next_j = (j + 1) % sides
        faces = [(tuple(k * sides + v for k, v in ((i, j), (i, next_j),
                   ((i + 1) % 4, next_j), ((i + 1) % 4, j))), role) for i in range(4)]
        faces.append((tuple(i * sides + j for i in range(4)), role))
        faces.append((tuple(i * sides + next_j for i in range(4)), role))
        pieces.append(faces)
    return pieces


def torus(major: float, minor: float, sides_major: int, sides_minor: int, role: str) -> Prim:
    """Torus lying in the XY plane."""
    verts: List[Vec3] = []
    faces: List[Tuple[int, ...]] = []
    for i in range(sides_major):
        u = 2.0 * math.pi * i / sides_major
        for j in range(sides_minor):
            v = 2.0 * math.pi * j / sides_minor
            rr = major + minor * math.cos(v)
            verts.append((rr * math.cos(u), rr * math.sin(u), minor * math.sin(v)))
    for i in range(sides_major):
        i2 = (i + 1) % sides_major
        for j in range(sides_minor):
            j2 = (j + 1) % sides_minor
            faces.append((
                i * sides_minor + j,
                i2 * sides_minor + j,
                i2 * sides_minor + j2,
                i * sides_minor + j2,
            ))
    recipe = None
    if major > minor > 0 and sides_major >= 3 and sides_minor >= 3:
        recipe = []
        for i in range(sides_major):
            next_i = (i + 1) % sides_major
            sector = [(faces[i * sides_minor + j], role) for j in range(sides_minor)]
            sector.append((tuple(i * sides_minor + j for j in range(sides_minor)), role))
            sector.append((tuple(next_i * sides_minor + j for j in range(sides_minor)), role))
            recipe.append(sector)
    return Prim(verts, faces, [role] * len(faces), convex_faces=recipe)


def _convex_polygon_parts(polygon: Sequence[Vec2], keep_convex=False):
    """Exact deterministic partition of a simple concave profile, bounded to 128 points.

    Ear clipping uses only existing vertices; adjacent triangles are greedily merged
    when their union is convex. Invalid/self-touching profiles receive no recipe.
    Convex profiles keep the original mesh instead of creating unnecessary shards.
    """
    n = len(polygon)
    if n < 3 or n > 128:
        return None
    span = max(max(p[k] for p in polygon) - min(p[k] for p in polygon) for k in (0, 1))
    if span <= 0:
        return None
    eps, distance_eps = span * span * 1e-12, span * 1e-12
    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    def on_segment(p, a, b):
        return abs(cross(a, b, p)) <= eps and all(min(a[k], b[k]) - distance_eps <= p[k] <= max(a[k], b[k]) + distance_eps for k in (0, 1))
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % n]
        if max(abs(a[k] - b[k]) for k in (0, 1)) <= distance_eps:
            return None
        for j in range(i + 1, n):
            if j == (i + 1) % n or (j + 1) % n == i:
                continue
            c, d = polygon[j], polygon[(j + 1) % n]
            ab = cross(a, b, c) * cross(a, b, d)
            cd = cross(c, d, a) * cross(c, d, b)
            if (ab < -eps * eps and cd < -eps * eps) or any((on_segment(c, a, b), on_segment(d, a, b), on_segment(a, c, d), on_segment(b, c, d))):
                return None
    if _polygon_area(polygon) <= eps:
        return None
    if all(cross(polygon[i - 1], polygon[i], polygon[(i + 1) % n]) >= -eps for i in range(n)):
        return [list(range(n))] if keep_convex else None
    remaining, pieces = list(range(n)), []
    while len(remaining) > 3:
        for i, b in enumerate(remaining):
            a, c = remaining[i - 1], remaining[(i + 1) % len(remaining)]
            if cross(polygon[a], polygon[b], polygon[c]) <= eps:
                continue
            if any(all(cross(polygon[u], polygon[v], polygon[p]) >= -eps for u, v in ((a, b), (b, c), (c, a)))
                   for p in remaining if p not in (a, b, c)):
                continue
            pieces.append([a, b, c]); remaining.pop(i)
            break
        else:
            return None
    if cross(*(polygon[i] for i in remaining)) <= eps:
        return None
    pieces.append(remaining)
    merged = True
    while merged:
        merged = False
        for i, first in enumerate(pieces):
            for j in range(i + 1, len(pieces)):
                second = pieces[j]
                shared = [(a, b) for a in range(len(first)) for b in range(len(second))
                          if first[a] == second[(b + 1) % len(second)] and first[(a + 1) % len(first)] == second[b]]
                if len(shared) != 1:
                    continue
                a, b = shared[0]
                path_a = [first[(a + 1 + k) % len(first)] for k in range(len(first))]
                path_b = [second[(b + 1 + k) % len(second)] for k in range(len(second))]
                union = path_a + path_b[1:-1]
                if len(set(union)) != len(union) or any(cross(polygon[union[k - 1]], polygon[union[k]], polygon[union[(k + 1) % len(union)]]) < -eps for k in range(len(union))):
                    continue
                pieces[i] = union; pieces.pop(j); merged = True
                break
            if merged:
                break
    return pieces


def prism(polygon: Sequence[Vec2], depth: float, role: str, cap_role: Optional[str] = None) -> Prim:
    """Extrude a 2D polygon (XY, counter-clockwise) along Z, centred on origin."""
    n = len(polygon)
    if n < 3:
        raise ValueError("prism needs a polygon with at least 3 points")
    if _polygon_area(polygon) < 0:
        polygon = list(reversed(polygon))
    h = depth / 2.0
    verts = [(x, y, -h) for x, y in polygon] + [(x, y, h) for x, y in polygon]
    faces: List[Tuple[int, ...]] = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    roles = [cap_role or role, cap_role or role]
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((i, i2, n + i2, n + i))
        roles.append(role)
    parts = _convex_polygon_parts(polygon) if depth > 0 else None
    recipe = None
    if parts:
        recipe = []
        for part in parts:
            sector = [(tuple(reversed(part)), cap_role or role), (tuple(i + n for i in part), cap_role or role)]
            for i, a in enumerate(part):
                b = part[(i + 1) % len(part)]
                sector.append(((a, b, n + b, n + a), role))
            recipe.append(sector)
    return Prim(verts, faces, roles, convex_faces=recipe)


def sphere(radius: float, segments: int, rings: int, role: str) -> Prim:
    """Low-poly UV sphere (poles on Z)."""
    profile = []
    for k in range(rings + 1):
        t = math.pi * k / rings - math.pi / 2.0
        profile.append((radius * math.cos(t) if 0 < k < rings else 0.0, radius * math.sin(t)))
    return lathe(profile, segments, role)


def _merge_prims(*parts: Prim) -> Prim:
    """Fuse multiple prims by concatenating their vertices/faces, suitable for modular profiles."""
    verts: List[Vec3] = []
    faces: List[Tuple[int, ...]] = []
    roles: List[str] = []
    offset = 0
    for part in parts:
        for v in part.verts:
            verts.append(v)
        for face in part.faces:
            faces.append(tuple(i + offset for i in face))
        roles.extend(part.roles)
        offset += len(part.verts)
    return Prim(verts, faces, roles)


def pipe_section(radius: float, depth: float, wall: float, sides: int = 10, role: str = "M_Metal") -> Prim:
    """Hollow cylindrical section / pipe segment."""
    if radius <= wall:
        raise ValueError("pipe wall must be smaller than the radius")
    h = depth / 2.0
    primitive = lathe(
        [(radius, -h), (radius, h), (radius - wall, h), (radius - wall, -h)],
        sides,
        role,
        cap_bottom=False,
        cap_top=False,
    )
    if radius > wall > 0 and depth > 0:
        primitive.convex_faces = _annular_sectors(sides, role)
    return primitive


def u_channel(width: float, height: float, depth: float, wall: float, role: str = "M_Metal") -> Prim:
    """Simple U-channel / C-channel structural section for walls, frames and rails."""
    if wall <= 0 or width <= wall * 2 or height <= wall * 2:
        raise ValueError("invalid U-channel dimensions")
    return _merge_prims(
        box(width, wall, depth, role, loc=(0.0, -height / 2.0 + wall / 2.0, 0.0)),
        box(wall, height, depth, role, loc=(-width / 2.0 + wall / 2.0, 0.0, 0.0)),
        box(wall, height, depth, role, loc=(width / 2.0 - wall / 2.0, 0.0, 0.0)),
    )


def angle_profile(width: float, height: float, depth: float, thickness: float, role: str = "M_Metal") -> Prim:
    """L-profile / angle bracket."""
    if width <= thickness or height <= thickness:
        raise ValueError("invalid L-profile dimensions")
    return _merge_prims(
        box(width, thickness, depth, role, loc=(0.0, -(height - thickness) / 2.0, 0.0)),
        box(thickness, height, depth, role, loc=(-width / 2.0 + thickness / 2.0, 0.0, 0.0)),
    )


def tee_profile(width: float, height: float, depth: float, web: float, role: str = "M_Metal") -> Prim:
    """T-profile / tee beam."""
    if width <= web or height <= web:
        raise ValueError("invalid T-profile dimensions")
    return _merge_prims(
        box(width, web, depth, role, loc=(0.0, height / 2.0 - web / 2.0, 0.0)),
        box(web, height, depth, role, loc=(0.0, 0.0, 0.0)),
    )


def i_beam(width: float, height: float, depth: float, web: float, flange: float, role: str = "M_Metal") -> Prim:
    """I-beam as a symmetric web plus two flanges."""
    if width <= 0 or height <= 0 or web <= 0 or flange <= 0:
        raise ValueError("invalid I-beam dimensions")
    return _merge_prims(
        box(width, flange, depth, role, loc=(0.0, -height / 2.0 + flange / 2.0, 0.0)),
        box(width, flange, depth, role, loc=(0.0, height / 2.0 - flange / 2.0, 0.0)),
        box(web, height - 2.0 * flange, depth, role, loc=(0.0, 0.0, 0.0)),
    )


def wedge(width: float, height: float, depth: float, role: str = "M_Wall") -> Prim:
    """Right-triangle wedge / ramp segment."""
    if width <= 0 or height <= 0 or depth <= 0:
        raise ValueError("invalid wedge dimensions")
    poly = [(-width / 2.0, 0.0), (width / 2.0, 0.0), (width / 2.0, height)]
    return prism(poly, depth, role)


def grate(width: float, length: float, depth: float, bar: float, gap: float, role: str = "M_Metal") -> Prim:
    """Simple modular grate made from intersecting bars, suitable for drains and access plates."""
    if width <= 0 or length <= 0 or depth <= 0 or bar <= 0 or gap <= 0:
        raise ValueError("invalid grate dimensions")
    pieces = []
    steps_x = max(1, int(width / (bar + gap)))
    steps_y = max(1, int(length / (bar + gap)))
    for i in range(steps_x):
        x = -width / 2.0 + (i + 0.5) * (width / steps_x)
        pieces.append(box(bar, length, depth, role, loc=(x, 0.0, 0.0)))
    for j in range(steps_y):
        y = -length / 2.0 + (j + 0.5) * (length / steps_y)
        pieces.append(box(width, bar, depth, role, loc=(0.0, y, 0.0)))
    return _merge_prims(*pieces)


def rounded_box(sx: float, sy: float, sz: float, role: str, radius: float = 0.05) -> Prim:
    """Rounded rectangle / capsule-like box; a robust low-poly alternative to sharp corners."""
    return chamfer_box(sx, sy, sz, role, min(radius, sx / 4.0, sy / 4.0, sz / 4.0))


def _polygon_area(poly: Sequence[Vec2]) -> float:
    area = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def face_normal(points: Sequence[Vec3]) -> Vec3:
    """Newell's method - robust for quads and n-gons."""
    nx = ny = nz = 0.0
    for i in range(len(points)):
        x1, y1, z1 = points[i]
        x2, y2, z2 = points[(i + 1) % len(points)]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return v_norm((nx, ny, nz))


# --------------------------------------------------------------------------
# mesh
# --------------------------------------------------------------------------

class Part:
    """Slice of a :class:`Mesh` created by one ``add`` call."""

    __slots__ = ("mesh", "name", "v0", "v1", "f0", "f1", "closed", "convex_faces")

    def __init__(self, mesh, name, v0, v1, f0, f1, closed, convex_faces=None):
        self.mesh, self.name = mesh, name
        self.v0, self.v1, self.f0, self.f1 = v0, v1, f0, f1
        self.closed = closed
        self.convex_faces = convex_faces

    def vertex_indices(self) -> range:
        return range(self.v0, self.v1)

    def face_indices(self) -> range:
        return range(self.f0, self.f1)


class Mesh:
    """Collection of flat-shaded parts that becomes one game object."""

    def __init__(self, name: str = "model"):
        self.name = name
        self.verts: List[Vec3] = []
        self.faces: List[Tuple[int, ...]] = []
        self.roles: List[str] = []
        self.parts: List[Part] = []

    # -- building -----------------------------------------------------------
    def add(
        self,
        prim: Prim,
        loc: Sequence[float] = (0.0, 0.0, 0.0),
        rot: Sequence[float] = (0.0, 0.0, 0.0),
        scale: Sequence[float] = (1.0, 1.0, 1.0),
        basis: Optional[Mat3] = None,
        name: str = "part",
    ) -> Part:
        v0, f0 = len(self.verts), len(self.faces)
        self.verts.extend(transform_points(prim.verts, scale, rot, loc, basis))
        self.faces.extend(tuple(i + v0 for i in f) for f in prim.faces)
        self.roles.extend(prim.roles)
        part = Part(self, name, v0, len(self.verts), f0, len(self.faces), prim.closed, prim.convex_faces)
        self.parts.append(part)
        return part

    def remove_parts(self, remove: Sequence[Part]) -> None:
        """Delete whole parts (vertices, faces, roles) and re-index the remaining ones."""
        gone = {id(p) for p in remove}
        verts: List[Vec3] = []
        faces: List[Tuple[int, ...]] = []
        roles: List[str] = []
        parts: List[Part] = []
        for part in self.parts:
            if id(part) in gone:
                continue
            v0, f0 = len(verts), len(faces)
            shift = v0 - part.v0
            verts.extend(self.verts[part.v0:part.v1])
            for fi in part.face_indices():
                faces.append(tuple(i + shift for i in self.faces[fi]))
                roles.append(self.roles[fi])
            part.v0, part.v1, part.f0, part.f1 = v0, len(verts), f0, len(faces)
            parts.append(part)
        self.verts, self.faces, self.roles, self.parts = verts, faces, roles, parts

    def part_bbox(self, part: Part) -> Tuple[Vec3, Vec3]:
        pts = self.verts[part.v0:part.v1]
        return (tuple(min(p[i] for p in pts) for i in range(3)),  # type: ignore[return-value]
                tuple(max(p[i] for p in pts) for i in range(3)))

    def translate(self, offset: Vec3) -> None:
        self.verts = [v_add(v, offset) for v in self.verts]

    def scale(self, factor: float) -> None:
        self.verts = [v_scale(v, factor) for v in self.verts]

    # -- queries ------------------------------------------------------------
    def face_points(self, fi: int) -> List[Vec3]:
        return [self.verts[i] for i in self.faces[fi]]

    def face_normal(self, fi: int) -> Vec3:
        return face_normal(self.face_points(fi))

    def bbox(self) -> Tuple[Vec3, Vec3]:
        if not self.verts:
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
        xs = [v[0] for v in self.verts]
        ys = [v[1] for v in self.verts]
        zs = [v[2] for v in self.verts]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def dimensions(self) -> Vec3:
        lo, hi = self.bbox()
        return v_sub(hi, lo)

    def triangle_count(self) -> int:
        return sum(len(f) - 2 for f in self.faces)

    def part_volume(self, part: Part) -> float:
        """Signed volume of a part (positive for outward facing normals)."""
        vol = 0.0
        for fi in part.face_indices():
            pts = self.face_points(fi)
            for k in range(1, len(pts) - 1):
                vol += v_dot(pts[0], v_cross(pts[k], pts[k + 1])) / 6.0
        return vol


def box_uvs(points: Sequence[Vec3], normal: Vec3) -> List[Vec2]:
    """Box projection in metres (1 UV unit = 1 m) - handy for trim sheets / triplanar looks."""
    ax = max(range(3), key=lambda i: abs(normal[i]))
    a, b = [(1, 2), (0, 2), (0, 1)][ax]
    flip = -1.0 if normal[ax] < 0 else 1.0
    if ax == 1:
        flip = -flip
    return [(p[a] * flip, p[b]) for p in points]
