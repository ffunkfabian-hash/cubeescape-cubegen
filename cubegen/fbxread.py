"""Minimal reader for binary FBX files: model hierarchy and local transforms (pure Python).

:func:`unity_locals` returns every model's local position / euler rotation in
Unity coordinates, the way Unity's importer converts a Y-up FBX (x mirrored,
units -> metres). :func:`check_asset` compares an exported FBX with the asset
it was built from - the Blender worker runs it after every FBX export, so an
FBX never disagrees with its ``<Name>.cubegen.json``.
"""

import struct
import zlib

_ARRAY = {"f": ("f", 4), "d": ("d", 8), "l": ("q", 8), "i": ("i", 4), "b": ("?", 1)}
_SCALAR = {"Y": ("h", 2), "C": ("?", 1), "I": ("i", 4), "F": ("f", 4), "D": ("d", 8), "L": ("q", 8)}


class Node:
    def __init__(self, name, props, children):
        self.name, self.props, self.children = name, props, children

    def find(self, name):
        return next((c for c in self.children if c.name == name), None)

    def find_all(self, name):
        return [c for c in self.children if c.name == name]


def _read_props(data, pos, count):
    props = []
    for _ in range(count):
        code = chr(data[pos])
        pos += 1
        if code in _SCALAR:
            fmt, size = _SCALAR[code]
            props.append(struct.unpack_from("<" + fmt, data, pos)[0])
            pos += size
        elif code in _ARRAY:
            length, encoding, clen = struct.unpack_from("<III", data, pos)
            pos += 12
            raw = data[pos:pos + clen]
            pos += clen
            if encoding == 1:
                raw = zlib.decompress(raw)
            fmt, size = _ARRAY[code]
            props.append(list(struct.unpack_from(f"<{length}{fmt}", raw, 0)))
        elif code in "SR":
            (length,) = struct.unpack_from("<I", data, pos)
            pos += 4
            raw = data[pos:pos + length]
            pos += length
            props.append(raw.decode("utf-8", "replace") if code == "S" else raw)
        else:
            raise ValueError(f"unknown FBX property type {code!r}")
    return props, pos


def _read_node(data, pos, wide):
    if wide:
        end, count, _plen = struct.unpack_from("<QQQ", data, pos)
        pos += 24
    else:
        end, count, _plen = struct.unpack_from("<III", data, pos)
        pos += 12
    name_len = data[pos]
    pos += 1
    if end == 0:
        return None, pos
    name = data[pos:pos + name_len].decode("ascii")
    pos += name_len
    props, pos = _read_props(data, pos, count)
    children = []
    while pos < end:
        child, pos = _read_node(data, pos, wide)
        if child is None:
            break
        children.append(child)
    return Node(name, props, children), end


def read(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if not data.startswith(b"Kaydara FBX Binary"):
        raise ValueError(f"{path}: not a binary FBX")
    (version,) = struct.unpack_from("<I", data, 23)
    wide = version >= 7500
    pos, nodes = 27, []
    while pos < len(data):
        node, pos = _read_node(data, pos, wide)
        if node is None:
            break
        nodes.append(node)
    return Node("root", [], nodes)


def _p70(node):
    values = {}
    props = node.find("Properties70")
    for p in props.find_all("P") if props else []:
        values[p.props[0]] = p.props[4:]
    return values


def models(path):
    """{name: {"parent": name or None, "translation": (x, y, z), "rotation": (x, y, z), "type": ...}} in FBX units."""
    root = read(path)
    by_id = {}
    for m in root.find("Objects").find_all("Model"):
        name = m.props[1].split("\x00")[0]
        values = _p70(m)
        by_id[m.props[0]] = {"name": name, "type": m.props[2], "parent": None,
                             "translation": tuple(values.get("Lcl Translation", (0.0, 0.0, 0.0))),
                             "rotation": tuple(values.get("Lcl Rotation", (0.0, 0.0, 0.0))),
                             "scaling": tuple(values.get("Lcl Scaling", (1.0, 1.0, 1.0)))}
    geometry = {g.props[0]: g.find("Vertices").props[0] for g in root.find("Objects").find_all("Geometry")
                if g.find("Vertices") is not None}
    for c in root.find("Connections").find_all("C"):
        if c.props[0] == "OO" and c.props[1] in by_id and c.props[2] in by_id:
            by_id[c.props[1]]["parent"] = by_id[c.props[2]]["name"]
        elif c.props[0] == "OO" and c.props[1] in geometry and c.props[2] in by_id:
            flat = geometry[c.props[1]]
            by_id[c.props[2]]["vertices"] = [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]
    settings = _p70(root.find("GlobalSettings"))
    unit = settings.get("UnitScaleFactor", (1.0,))[0]
    return {m["name"]: dict(m, unit=unit) for m in by_id.values()}


def unity_locals(path):
    """Local position (metres), euler rotation (degrees) and mesh vertices (metres, local) per model,
    as Unity imports a Y-up FBX."""
    result = {}
    for name, m in models(path).items():
        k = m["unit"] / 100.0  # FBX unit = cm * UnitScaleFactor
        x, y, z = m["translation"]
        rx, ry, rz = m["rotation"]
        result[name] = {"parent": m["parent"], "position": (round(-x * k, 4) + 0.0, round(y * k, 4) + 0.0,
                                                            round(z * k, 4) + 0.0),
                        "vertices": [(-vx * k, vy * k, vz * k) for vx, vy, vz in m.get("vertices", [])],
                        "rotation": (round(rx, 3) + 0.0, round(-ry, 3) + 0.0, round(-rz, 3) + 0.0),
                        "scale": tuple(round(s, 4) for s in m["scaling"])}
    return result


def check_asset(path, asset, tolerance=1e-4):
    """Differences between the FBX at ``path`` and ``asset`` (parents, local pivots, rotation 0, scale 1).

    Empty list = consistent.
    """
    from .asset import to_unity

    found = unity_locals(path)
    problems = []
    for o in asset.objects:
        info = found.get(o.name)
        if info is None:
            problems.append(f"{o.name}: missing in the FBX")
            continue
        parent = asset.get(o.parent) if o.parent else None
        expected = to_unity(tuple(o.pivot[i] - (parent.pivot[i] if parent else 0.0) for i in range(3)))
        if info["parent"] != o.parent:
            problems.append(f"{o.name}: parent {info['parent']!r} in the FBX, expected {o.parent!r}")
        if any(abs(a - b) > tolerance for a, b in zip(info["position"], expected)):
            problems.append(f"{o.name}: local position {info['position']} in the FBX, expected {expected}")
        if any(abs(r) > 1e-3 for r in info["rotation"]):
            problems.append(f"{o.name}: rotation {info['rotation']} in the FBX, expected 0")
        if any(abs(s - 1.0) > 1e-4 for s in info["scale"]):
            problems.append(f"{o.name}: scale {info['scale']} in the FBX, expected 1")
        if not o.is_empty:  # the exporter may drop unused vertices: every FBX vertex must be one of the mesh's
            wanted = {tuple(round(c, 3) + 0.0 for c in to_unity(v)) for v in o.local_verts()}
            off = [v for v in info["vertices"] if tuple(round(c, 3) + 0.0 for c in v) not in wanted
                   and min(max(abs(a - b) for a, b in zip(v, w)) for w in wanted) > max(tolerance, 2e-3)]
            if not info["vertices"]:
                problems.append(f"{o.name}: no mesh in the FBX")
            elif off:
                problems.append(f"{o.name}: {len(off)} vertices away from the mesh, e.g. {off[0]}")
    return problems
