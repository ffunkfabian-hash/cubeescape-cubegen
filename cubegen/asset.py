"""An asset = one exported file: several named objects, each with its own pivot.

Builders write all geometry in *asset space* (the coordinates the finished
asset has, origin = asset pivot). An object's pivot only decides where its
origin sits - the Blender worker subtracts it from the vertices, so moving
parts (``Rotor``, ``Wheel``, ``Panel`` ...) turn around the right point.

Objects only ever get a location - rotation and scale stay 0 / 1, all shaping
is baked into the mesh (clean FBX import in Unity).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .geometry import Mesh, Vec3, v_add, v_scale, v_sub


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


class Asset:
    def __init__(self, name: str):
        self.name = name
        self.objects: List[AssetObject] = []
        self.meta: Dict[str, object] = {}

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

    def scale(self, factor: float) -> None:
        for obj in self.objects:
            obj.pivot = v_scale(obj.pivot, factor)
            if obj.mesh:
                obj.mesh.scale(factor)

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

    def stats(self) -> Dict[str, object]:
        lo, hi = self.bbox()
        meshes = self.meshes()
        return {
            "objects": [o.name for o in self.objects],
            "vertices": sum(len(o.mesh.verts) for o in meshes),
            "triangles": sum(o.mesh.triangle_count() for o in meshes),
            "dimensions_m": [round(hi[i] - lo[i], 4) for i in range(3)],
            "materials": sorted({r for o in meshes for r in o.mesh.roles}),
        }
