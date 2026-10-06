"""An asset = one exported file: several named objects, each with its own pivot.

Builders write all geometry in *asset space* (the coordinates the finished
asset has, origin = asset pivot). An object's pivot only decides where its
origin sits - the Blender worker subtracts it from the vertices, so moving
parts (``Rotor``, ``Wheel``, ``Panel`` ...) turn around the right point.

Objects only ever get a location - rotation and scale stay 0 / 1, all shaping
is baked into the mesh (clean FBX import in Unity).
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Dict, List, Optional, Tuple

from .geometry import Mesh, Vec3, add_up, euler_matrix, v_add, v_scale, v_sub
from .seeds import StableRandom, sub_rng


class AssetObject:
    def __init__(self, name: str, pivot: Vec3, parent: Optional[str], mesh: Optional[Mesh]):
        self.name = name
        self.pivot = tuple(pivot)
        self.parent = parent
        self.mesh = mesh  # None = empty (e.g. a hinge like "LeverPivot")

    @property
    def is_empty(self) -> bool:
        return self.mesh is None

    def local_verts(self) -> List[Vec3]:
        return [v_sub(v, self.pivot) for v in self.mesh.verts] if self.mesh else []


# Blender (Z up, front -Y) -> Unity (Y up, front +Z), as produced by the FBX export
# with axis_forward="-Z", axis_up="Y", bake_space_transform=True.
def to_unity(v: Vec3) -> Tuple[float, float, float]:
    return (round(-v[0], 4) + 0.0, round(v[2], 4) + 0.0, round(-v[1], 4) + 0.0)


#: Blender -> Unity as a matrix (``to_unity`` without rounding); a rotation R becomes M R M^-1
_TO_UNITY = ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))


def _quaternion(m) -> Tuple[float, float, float, float]:
    """(x, y, z, w) of a rotation matrix - the order of Unity's ``new Quaternion(x, y, z, w)``."""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)
    if q[3] < 0:  # same rotation, canonical sign
        q = tuple(-c for c in q)
    return tuple(round(c, 6) + 0.0 for c in q)  # type: ignore[return-value]


def unity_rotation(rot: Vec3) -> Tuple[float, float, float, float]:
    """Unity quaternion (x, y, z, w) of a Blender XYZ euler rotation (radians, as used by ``cube``)."""
    r = euler_matrix(*rot)
    m = _TO_UNITY
    mr = [[add_up(m[i][k] * r[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    # M is orthogonal: M^-1 = M^T
    return _quaternion([[add_up(mr[i][k] * m[j][k] for k in range(3)) for j in range(3)] for i in range(3)])


class Collider:
    """Collision shape hint for the Unity import (the FBX carries no colliders).

    ``box``  - centre / size / XYZ euler rotation in asset space (like ``cube``)
    ``mesh`` - MeshCollider on the part's own mesh (``convex`` for rigid / moving parts)

    ``part`` is the object the collider belongs to: it moves with that part
    (lid, deck, field ...); ``None`` = the model root.
    """

    def __init__(self, kind: str, part: Optional[str], center: Vec3 = (0.0, 0.0, 0.0),
                 size: Vec3 = (0.0, 0.0, 0.0), rot: Vec3 = (0.0, 0.0, 0.0), convex: bool = False):
        self.kind = kind
        self.part = part
        self.center = tuple(center)
        self.size = tuple(size)
        self.rot = tuple(rot)
        self.convex = convex


#: rotation axes in the names the game's scripts use (Vector3.right / up / forward)
UNITY_AXES = {"right": (1, 0, 0), "up": (0, 1, 0), "forward": (0, 0, 1)}


class Asset:
    def __init__(self, name: str):
        self.name = name
        self.objects: List[AssetObject] = []
        self.meta: Dict[str, object] = {}
        #: which existing Unity scripts drive which parts, with field values in Unity units
        self.behaviours: List[Dict[str, object]] = []
        #: explicit collision shapes; empty = the importer's default (box hull)
        self.colliders: List[Collider] = []
        #: parameter reader of the build (set by generate_asset): rolls values, applies overrides / style
        self.p = None
        #: the asset seed (set by generate_asset)
        self.seed = 0

    def sub(self, key: str) -> StableRandom:
        """An own random stream for one aspect of the model, e.g. ``a.sub("antenna")``.

        Every roll from the builder's ``rng`` shifts all rolls after it. New
        details should roll from their own stream instead: then adding them
        leaves everything the seed made so far exactly as it was. Same seed +
        key = same stream.
        """
        return sub_rng(self.seed, key)

    def behaviour(self, script: str, parts: Dict[str, object], fields: Optional[Dict[str, object]] = None,
                  note: str = "") -> None:
        """Describe how a game script should be wired to this asset (written to <Name>.cubegen.json).

        ``parts`` maps the script's reference fields to part names, ``fields``
        holds the script parameters (Unity units: m, m/s, deg/s, axes by name).
        """
        for value in parts.values():
            for name in value if isinstance(value, list) else [value]:
                if self.get(name) is None:
                    raise ValueError(f"behaviour {script}: part {name!r} does not exist")
        entry: Dict[str, object] = {"script": script, "parts": parts, "fields": fields or {}}
        if note:
            entry["note"] = note
        self.behaviours.append(entry)

    def collider(self, size: Vec3, center: Vec3, rot: Vec3 = (0.0, 0.0, 0.0), part: Optional[str] = None) -> None:
        """Box collider in asset space (same arguments as ``cube``), attached to ``part`` or the root."""
        self._check_collider_part(part)
        if min(size) <= 0:
            raise ValueError(f"collider size must be > 0, got {size}")
        self.colliders.append(Collider("box", part, center, size, rot))

    def mesh_collider(self, part: str, convex: bool = True) -> None:
        """MeshCollider on the mesh of ``part`` (convex: Unity builds the hull, needed on moving parts)."""
        self._check_collider_part(part)
        if self.get(part).is_empty:
            raise ValueError(f"mesh collider: {part!r} is an empty")
        self.colliders.append(Collider("mesh", part, convex=convex))

    def _check_collider_part(self, part: Optional[str]) -> None:
        if part is not None and self.get(part) is None:
            raise ValueError(f"collider: part {part!r} does not exist")

    # -- building -------------------------------------------------------------
    def part(self, name: str, pivot: Vec3 = (0.0, 0.0, 0.0), parent: Optional[str] = None) -> Mesh:
        """Mesh of object ``name`` (created on first use, later calls return the same mesh)."""
        for obj in self.objects:
            if obj.name == name:
                if obj.mesh is None:
                    raise ValueError(f"{name!r} is an empty, not a mesh")
                return obj.mesh
        self._check_parent(parent)
        mesh = Mesh(name)
        self.objects.append(AssetObject(name, pivot, parent, mesh))
        return mesh

    def empty(self, name: str, pivot: Vec3, parent: Optional[str] = None) -> None:
        self._check_parent(parent)
        if self.get(name):
            raise ValueError(f"object {name!r} exists already")
        self.objects.append(AssetObject(name, pivot, parent, None))

    def _check_parent(self, parent: Optional[str]) -> None:
        if parent is not None and self.get(parent) is None:
            raise ValueError(f"parent {parent!r} must be created before its children")

    def get(self, name: str) -> Optional[AssetObject]:
        return next((o for o in self.objects if o.name == name), None)

    # -- transforms -----------------------------------------------------------
    def translate(self, offset: Vec3) -> None:
        for obj in self.objects:
            obj.pivot = v_add(obj.pivot, offset)
            if obj.mesh:
                obj.mesh.translate(offset)
        for c in self.colliders:
            c.center = v_add(c.center, offset)

    def scale(self, factor: float) -> None:
        for entry in self.behaviours:  # distances scale with the model, speeds/angles don't
            fields = entry["fields"]
            for key in ("openOffset", "distance", "travel"):
                if key in fields:
                    value = fields[key]
                    fields[key] = [round(c * factor, 4) for c in value] if isinstance(value, list) \
                        else round(value * factor, 4)
        for obj in self.objects:
            obj.pivot = v_scale(obj.pivot, factor)
            if obj.mesh:
                obj.mesh.scale(factor)
        for c in self.colliders:
            c.center, c.size = v_scale(c.center, factor), v_scale(c.size, factor)

    def normalize(self, pivot_mode: str) -> None:
        """Apply the pivot convention of the asset type.

        ``floor``  - standing assets: lowest point at z = 0 (x/y as built, i.e. centred)
        ``top``    - walkable pieces: built with the top surface at z = 0, left as is
        ``wall``   - wall-mounted pieces: pivot on the floor below, geometry at its height, left as is
        ``center`` - floating items: bounding box centred on the origin
        """
        (x0, y0, z0), (x1, y1, z1) = self.bbox()
        if pivot_mode == "floor":
            self.translate((0.0, 0.0, -z0))
        elif pivot_mode == "center":
            self.translate((-(x0 + x1) / 2, -(y0 + y1) / 2, -(z0 + z1) / 2))
        elif pivot_mode not in ("top", "wall"):
            raise ValueError(f"unknown pivot mode {pivot_mode!r}")

    # -- queries --------------------------------------------------------------
    def meshes(self) -> List[AssetObject]:
        return [o for o in self.objects if o.mesh is not None]

    def bbox(self) -> Tuple[Vec3, Vec3]:
        boxes = [o.mesh.bbox() for o in self.meshes() if o.mesh.verts]
        if not boxes:
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
        lo = tuple(min(b[0][i] for b in boxes) for i in range(3))
        hi = tuple(max(b[1][i] for b in boxes) for i in range(3))
        return lo, hi  # type: ignore[return-value]

    def collider_data(self) -> List[Dict[str, object]]:
        """Colliders in Unity coordinates, relative to the pivot of their part (or the model root).

        A box with a rotation needs its own child GameObject (``BoxCollider`` itself
        cannot rotate): localPosition = center, localRotation = rotation.
        """
        out: List[Dict[str, object]] = []
        for c in self.colliders:
            if c.kind == "mesh":
                out.append({"type": "mesh", "part": c.part, "convex": c.convex})
                continue
            origin = self.get(c.part).pivot if c.part else (0.0, 0.0, 0.0)
            sx, sy, sz = c.size
            out.append({"type": "box", "part": c.part,
                        "center": list(to_unity(v_sub(c.center, origin))),
                        "size": [round(sx, 4), round(sz, 4), round(sy, 4)],  # Blender x/y/z -> Unity x/z/y
                        "rotation": list(unity_rotation(c.rot))})
        return out

    def digest(self) -> str:
        """SHA-256 fingerprint of everything that ends up in the files: geometry, pivots, materials, colliders,
        script wiring and meta data. Floats are rounded to 1e-6 so last-bit differences between platforms
        don't count."""

        def num(x: float) -> str:
            return repr(round(float(x), 6) + 0.0)

        def vec(v) -> str:
            return ",".join(num(c) for c in v)

        def rounded(value):
            if isinstance(value, float):
                return round(value, 6) + 0.0
            if isinstance(value, dict):
                return {str(k): rounded(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [rounded(v) for v in value]
            return value

        h = hashlib.sha256()
        for o in self.objects:
            h.update(f"O|{o.name}|{o.parent}|{vec(o.pivot)}\n".encode())
            if o.mesh is not None:
                h.update(";".join(vec(v) for v in o.mesh.verts).encode())
                h.update(repr(o.mesh.faces).encode())
                h.update("|".join(o.mesh.roles).encode())
        for c in self.colliders:
            h.update(f"C|{c.kind}|{c.part}|{vec(c.center)}|{vec(c.size)}|{vec(c.rot)}|{c.convex}\n".encode())
        h.update(json.dumps(rounded(self.behaviours), sort_keys=True, default=str).encode())
        h.update(json.dumps(rounded(self.meta), sort_keys=True, default=str).encode())
        return h.hexdigest()

    def stats(self) -> Dict[str, object]:
        lo, hi = self.bbox()
        meshes = self.meshes()
        return {
            "objects": [o.name for o in self.objects],
            "vertices": sum(len(o.mesh.verts) for o in meshes),
            "triangles": sum(o.mesh.triangle_count() for o in meshes),
            "dimensions_m": [round(hi[i] - lo[i], 4) for i in range(3)],
            "materials": sorted({r for o in meshes for r in o.mesh.roles}),
            "colliders": len(self.colliders),
        }
