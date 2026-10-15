#!/usr/bin/env python3
"""Atlas check: real baked runs of a fixed set (smooth, voxel, facet), then the atlas UVs measured numerically.

    python3 tools/atlas_check.py                     # generate (one heavy run under the shared lock) and measure
    python3 tools/atlas_check.py --dir DIR           # measure the GLB files of an earlier run (no Blender)
    python3 tools/atlas_check.py --keep --out DIR    # keep the run and write uv_<model>.png + overview.png

What is measured per model (the GLB export carries the atlas UVs = UV0 of the FBX):

- **occupancy:** share of the unit square the UV polygons cover (the manifest's ``atlas_occupancy``; they must agree);
- **range:** every UV inside 0..1;
- **overlap:** texels (at ``--size``, default 512 like the bake) covered by faces of two different islands - baked
  texels would be shared;
- **margin:** texels where two islands, each grown by half the bake margin (``MARGIN`` px, Cycles' 4 px), touch - the
  dilation of one island would run into the other (bleeding in the lowest mips is a separate matter).

Islands are the faces connected through shared UV vertices. Exit code 1 when a limit (``LIMITS``) is broken. Needs numpy;
without it the script runs again with Blender's Python. The bake itself waits for the machine-wide queue of heavy runs
(``tools/unity_check.HeavyLock``, AGENTS.md).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Sequence, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

MARGIN = 4  # px: Cycles' bake margin (bake._bake)
#: fixed set: (shape, types, seed) - small and large, round and boxy, one voxel and one facet run
SET = (
    ("smooth", "console,cargo_container,tank,locker", "7"),
    ("voxel", "crate,generator,tank", "7"),
    ("facet", "canister,generator,tank", "7"),
)
#: what a good atlas keeps: no out-of-range UV, (almost) no shared texel, occupancy as the manifest says
LIMITS = {"min_occupancy": 0.40, "overlap_share": 0.001, "margin_share": 0.02, "manifest_difference": 0.01}

Polygon = List[Tuple[float, float]]


def read_glb_uvs(path: str) -> List[Polygon]:
    """The UV triangles (TEXCOORD_0, v flipped back) of every primitive with the baked material ``MTA_*`` of a GLB - what the engine samples with: the
    export after the bake has the atlas as its only UV map (an OBJ of cubegen keeps the tiled UVs of the MT_ materials)."""
    import struct

    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"glTF":
        raise ValueError(f"{path}: not a GLB")
    pos, doc, blob = 12, None, b""
    while pos < len(data):
        length, kind = struct.unpack("<I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"JSON":
            doc = json.loads(body)
        elif kind == b"BIN\0":
            blob = body
        pos += 8 + length

    def accessor(index):
        import numpy as np

        acc = doc["accessors"][index]
        view = doc["bufferViews"][acc["bufferView"]]
        dtype = {5126: "<f4", 5123: "<u2", 5125: "<u4", 5121: "u1"}[acc["componentType"]]
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[acc["type"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride")
        count = acc["count"]
        if stride and stride != np.dtype(dtype).itemsize * width:
            raw = np.frombuffer(blob, np.uint8, count * stride, start).reshape(count, stride)
            return np.frombuffer(raw[:, :np.dtype(dtype).itemsize * width].tobytes(), dtype).reshape(count, width)
        return np.frombuffer(blob, dtype, count * width, start).reshape(count, width)

    polys = []
    for mesh in doc.get("meshes", []):
        for prim in mesh["primitives"]:
            if "TEXCOORD_0" not in prim["attributes"] or "indices" not in prim:
                continue
            material = doc.get("materials", [{}])[prim["material"]].get("name", "") if "material" in prim else ""
            if not material.startswith("MTA_"):  # glow, crystal and glass keep their M_ material and no atlas UVs
                continue
            uv = accessor(prim["attributes"]["TEXCOORD_0"])
            idx = accessor(prim["indices"]).reshape(-1)
            for a, b, c in idx.reshape(-1, 3):
                polys.append([(float(uv[k][0]), 1.0 - float(uv[k][1])) for k in (a, b, c)])
    return polys


def _islands(polys: Sequence[Polygon]) -> List[int]:
    """Island id per polygon: polygons sharing a UV vertex (rounded to 1e-5) are one island."""
    parent = list(range(len(polys)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner: Dict[Tuple[int, int], int] = {}
    for i, poly in enumerate(polys):
        for u, v in poly:
            key = (round(u * 1e5), round(v * 1e5))
            if key in owner:
                a, b = find(i), find(owner[key])
                if a != b:
                    parent[max(a, b)] = min(a, b)
            else:
                owner[key] = i
    roots = {}
    return [roots.setdefault(find(i), len(roots)) for i in range(len(polys))]


def _fill(mask, poly: Polygon, size: int) -> None:
    """Texels whose centre lies in the (convex or fan-triangulated) polygon."""
    import numpy as np

    for k in range(1, len(poly) - 1):
        pts = np.asarray([poly[0], poly[k], poly[k + 1]], np.float64) * size
        x0, y0 = np.floor(pts.min(axis=0)).astype(int)
        x1, y1 = np.ceil(pts.max(axis=0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = pts
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-12:
            continue
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / det
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / det
        mask[y0:y1 + 1, x0:x1 + 1] |= (w0 >= -1e-9) & (w1 >= -1e-9) & (1 - w0 - w1 >= -1e-9)


def _grow(mask, steps: int):
    out = mask.copy()
    for _ in range(steps):
        grown = out.copy()
        grown[1:, :] |= out[:-1, :]
        grown[:-1, :] |= out[1:, :]
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        out = grown
    return out


def area(poly: Polygon) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2.0


def analyse(polys: Sequence[Polygon], size: int = 512, margin: int = MARGIN) -> Dict:
    """Measurements of one atlas (see the module docstring); ``island_map`` (size x size, island id + 1, 0 = empty;
    the last writer wins in an overlap) is for drawing."""
    import numpy as np

    ids = _islands(polys)
    count = (max(ids) + 1) if ids else 0
    coverage = np.zeros((size, size), np.uint8)   # islands per texel
    reach = np.zeros((size, size), np.uint8)      # islands per texel after growing each by margin/2
    island_map = np.zeros((size, size), np.int32)
    for island in range(count):
        mask = np.zeros((size, size), bool)
        for poly, i in zip(polys, ids):
            if i == island:
                _fill(mask, poly, size)
        coverage += mask
        reach += _grow(mask, margin // 2)
        island_map[mask] = island + 1
    covered = int((coverage > 0).sum())
    flat = [c for poly in polys for p in poly for c in p]
    return {
        "faces": len(polys), "islands": count, "size": size,
        "occupancy": round(sum(area(p) for p in polys), 4),
        "in_range": bool(flat) and min(flat) >= -1e-4 and max(flat) <= 1 + 1e-4,
        "overlap_texels": int((coverage > 1).sum()),
        "overlap_share": round(float((coverage > 1).sum()) / max(covered, 1), 5),
        "margin_texels": int(((reach > 1) & (coverage <= 1)).sum()),
        "margin_share": round(float(((reach > 1) & (coverage <= 1)).sum()) / max(covered, 1), 5),
        "island_map": island_map,
    }


def problems(name: str, stats: Dict, manifest_occupancy=None) -> List[str]:
    found = []
    if not stats["in_range"]:
        found.append(f"{name}: UVs outside 0..1")
    if stats["occupancy"] < LIMITS["min_occupancy"]:
        found.append(f"{name}: occupancy {stats['occupancy']:.2f} < {LIMITS['min_occupancy']}")
    if stats["overlap_share"] > LIMITS["overlap_share"]:
        found.append(f"{name}: {stats['overlap_share']:.2%} of the texels shared by two islands")
    if stats["margin_share"] > LIMITS["margin_share"]:
        found.append(f"{name}: {stats['margin_share']:.2%} of the texels where the margins of two islands meet")
    if manifest_occupancy is not None and abs(manifest_occupancy - stats["occupancy"]) > LIMITS["manifest_difference"]:
        found.append(f"{name}: occupancy {stats['occupancy']:.3f} differs from the manifest's {manifest_occupancy}")
    return found


def draw(stats: Dict, path: str) -> str:
    """``uv_<model>.png``: islands in colours (hue by id), shared texels red."""
    import numpy as np

    from cubegen.neutral import write_png

    ids = stats["island_map"]
    rng = np.random.RandomState(3)
    palette = np.vstack([[18, 18, 24], rng.randint(70, 230, (int(ids.max()) + 1, 3))]).astype(np.uint8)
    image = palette[ids]
    return write_png(path, image)


def generate(out: str, quiet: bool = True) -> List[str]:
    """The fixed runs (one per shape) into ``out/<shape>``, under the shared lock; returns their folders."""
    from unity_check import HeavyLock

    folders = []
    with HeavyLock("Cubegen tools/atlas_check.py") as lock:
        lock.acquire()
        for shape, types, seed in SET:
            folder = os.path.join(out, shape)
            cmd = [sys.executable, "-m", "cubegen", "generate", "--seed", seed, "--types", types, "--count", "1",
                   "--shape", shape, "--textures", "baked", "--texture-size", "512", "--formats", "glb", "--no-render",
                   "--no-blend", "--out", folder]
            subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL if quiet else None,
                           env=dict(os.environ, CE_HEAVY_HELD="1"))
            folders.append(folder)
    return folders


def measure(folder: str, size: int = 512) -> Dict[str, Dict]:
    """``{model: stats}`` of every OBJ under ``folder/models`` (manifest occupancy attached)."""
    manifest = {}
    path = os.path.join(folder, "manifest.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            manifest = {m["name"]: m.get("atlas_occupancy") for m in json.load(fh).get("models", [])}
    result = {}
    for obj in sorted(glob.glob(os.path.join(folder, "models", "*.glb"))):
        name = os.path.splitext(os.path.basename(obj))[0]
        stats = analyse(read_glb_uvs(obj), size)
        stats["manifest_occupancy"] = manifest.get(name)
        result[name] = stats
    return result


def _ensure_numpy() -> None:
    try:
        import numpy  # noqa: F401
    except ImportError:
        pythons = sorted(glob.glob("/Applications/Blender.app/Contents/Resources/*/python/bin/python3*"))
        if pythons and os.environ.get("CUBEGEN_ATLAS_REEXEC") != "1":
            sys.exit(subprocess.call([pythons[-1], *sys.argv], env=dict(os.environ, CUBEGEN_ATLAS_REEXEC="1")))
        sys.exit("atlas_check needs numpy (Blender's Python has it)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="atlas check: occupancy, overlap and margins of baked atlas UVs")
    ap.add_argument("--dir", metavar="DIR", action="append", help="measure the GLB files of an earlier run (repeatable)")
    ap.add_argument("--out", help="working folder (default: a temporary one; with --keep it stays)")
    ap.add_argument("--keep", action="store_true", help="keep the run and write uv_<model>.png and overview.png")
    ap.add_argument("--size", type=int, default=512)
    args = ap.parse_args(argv)
    _ensure_numpy()
    work = args.out or tempfile.mkdtemp(prefix="cubegen_atlas_")
    folders = args.dir or generate(work, quiet=True)
    found, rows, pictures = [], [], []
    for folder in folders:
        for name, stats in measure(folder, args.size).items():
            shape = os.path.basename(folder.rstrip("/"))
            rows.append((shape, name, stats))
            found += problems(f"{shape}/{name}", stats, stats["manifest_occupancy"])
            if args.keep:
                os.makedirs(work, exist_ok=True)
                pictures.append(draw(stats, os.path.join(work, f"uv_{shape}_{name}.png")))
    print(f"{'shape':7} {'model':22} {'faces':>5} {'isl':>4} {'occ':>6} {'manif':>6} {'overlap':>8} {'margin':>7}")
    for shape, name, s in rows:
        manifest = "-" if s["manifest_occupancy"] is None else f"{s['manifest_occupancy']:.3f}"
        print(f"{shape:7} {name:22} {s['faces']:5d} {s['islands']:4d} {s['occupancy']:6.3f} {manifest:>6} "
              f"{s['overlap_share']:8.3%} {s['margin_share']:7.3%}")
    if pictures:
        magick = shutil.which("magick")
        if magick:
            sheet = os.path.join(work, "overview.png")
            subprocess.run([magick, "montage", *pictures, "-tile", "5x", "-geometry", "220x220+3+3", "-background",
                            "#101014", sheet], check=False)
            print(f"overview: {sheet}")
    for line in found:
        print("PROBLEM", line)
    print("atlas check: " + ("FAILED" if found else "ok") + f" ({len(rows)} models)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
