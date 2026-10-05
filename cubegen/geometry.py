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

    __slots__ = ("verts", "faces", "roles", "closed")

    def __init__(self, verts, faces, roles, closed=True):
        self.verts: List[Vec3] = list(verts)
        self.faces: List[Tuple[int, ...]] = [tuple(f) for f in faces]
        self.roles: List[str] = list(roles)
        self.closed = closed


def box(
    sx: float,
    sy: float,
    sz: float,
    role: str,
    top_role: Optional[str] = None,
    bottom_role: Optional[str] = None,
    top_scale: Sequence[float] = (1.0, 1.0),
    top_offset: Sequence[float] = (0.0, 0.0),
) -> Prim:
    """Axis aligned box centred on the origin.

    ``top_scale`` tapers the top face (frustum), ``top_offset`` shears it.
    """
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    tx, ty = x * top_scale[0], y * top_scale[1]
    ox, oy = top_offset
    verts = [
        (-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
        (-tx + ox, -ty + oy, z), (tx + ox, -ty + oy, z), (tx + ox, ty + oy, z), (-tx + ox, ty + oy, z),
    ]
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
    return Prim(verts, faces, roles, closed)


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
    c = v_scale((sum(p[0] for p in pts), sum(p[1] for p in pts), sum(p[2] for p in pts)), 1.0 / len(pts))
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
    return p


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
    return Prim(verts, faces, [role] * len(faces))


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
    return Prim(verts, faces, roles)


def sphere(radius: float, segments: int, rings: int, role: str) -> Prim:
    """Low-poly UV sphere (poles on Z)."""
    profile = []
    for k in range(rings + 1):
        t = math.pi * k / rings - math.pi / 2.0
        profile.append((radius * math.cos(t) if 0 < k < rings else 0.0, radius * math.sin(t)))
    return lathe(profile, segments, role)


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

    __slots__ = ("mesh", "name", "v0", "v1", "f0", "f1", "closed")

    def __init__(self, mesh, name, v0, v1, f0, f1, closed):
        self.mesh, self.name = mesh, name
        self.v0, self.v1, self.f0, self.f1 = v0, v1, f0, f1
        self.closed = closed

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
        part = Part(self, name, v0, len(self.verts), f0, len(self.faces), prim.closed)
        self.parts.append(part)
        return part

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
