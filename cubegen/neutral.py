"""Neutral maps for a recolouring shader (0.24.0 "Primer", Cube Escape ROADMAP ToDo 27, contract version 3).

``--paint`` bakes every model once, neutrally (``stylebake.bake_masks``: weights, AO, edge, up, height, the tile
textures' diffuse and normal), and composes a scheme from those maps (``paint.compose``). This module packs the inputs
of ``compose`` into five textures a shader reads (``MTN_<Model>_<map>.png`` next to the ``MTP_`` maps):

=========  ======================================================================================================
``W0``     RGB: weights of ``weight_layout[0]`` (one painted game material per channel); A: noise 0..1
``W1``     RGB: weights of ``weight_layout[1]`` (black without a second group); A: detail, ``DETAIL_RANGE`` linear
``W2``     RGB: weights of ``weight_layout[2]``; A: 1 (reserved) - only when the layout has a third group
``Fields`` R: ambient occlusion, G: edge, B: up (world normal Z), A: height (0 at the model's foot, 1 at its top)
``Normal`` tangent-space normal of the tile textures (the same pixels as ``MTP_<Model>_<scheme>_Normal.png``)
=========  ======================================================================================================

All of them are linear data (no sRGB), 8 bit. The noise used to be drawn at compose time from a numpy seed; it is a
channel now, so a shader computes exactly the reference image instead of a look-alike: ``compose`` reads its inputs
from the *packed* (8-bit) values (``unpack``), never from floats a shader cannot see. ``compose`` itself stays the
reference formula (Cube Escape MATERIALS.md, decision 2: two recipes, no shared formula).

Arrays here are bottom-up like Blender's pixels and UV space (row 0 = v 0); ``write_png``/``read_png`` flip to the
top-down rows of a PNG. Pure numpy - no Blender needed to pack, read or compose (``tools/paint_reference.py``).
"""

from __future__ import annotations

import struct
import zlib
from typing import Dict, Sequence, Tuple

#: the maps of ``textures.neutral`` in the sidecar (contract ``neutral_maps``), in this order
NEUTRAL_KEYS = ("W0", "W1", "W2", "Fields", "Normal")
#: always written with --paint (W2 only for a third weight group)
NEUTRAL_REQUIRED = ("W0", "W1", "Fields", "Normal")
#: the detail factor's range (``paint.detail_map`` clamps to it): W1.a = (detail - lo) / (hi - lo)
DETAIL_RANGE = (0.35, 1.8)
#: the noise: weight x bilinear upscaled random grid of ``cells`` cells, seeds ``seed + offset`` (as compose drew it
#: since 0.17.0)
NOISE_OCTAVES = ((0.6, 32, 0), (0.4, 160, 1))
#: file names: MTN_<model>_<map>.png in the textures folder (MTP_ = composed scheme, MTA_ = material)
PREFIX = "MTN_"
#: channel meaning per map - the same as contract.json › neutral_maps › channels (a test keeps them equal)
CHANNELS = {
    "W0": {"rgb": "weights of weight_layout[0]", "a": "noise"},
    "W1": {"rgb": "weights of weight_layout[1] (black without a second group)", "a": "detail"},
    "W2": {"rgb": "weights of weight_layout[2]", "a": "reserved (1)"},
    "Fields": {"r": "ambient occlusion", "g": "edge", "b": "up", "a": "height"},
    "Normal": {"rgb": "tangent-space normal (OpenGL, +Y up)"},
}


def file_name(model: str, key: str) -> str:
    return f"{PREFIX}{model}_{key}.png"


def noise(size: int, seed: int):
    """The paint noise 0..1 of a ``size`` x ``size`` map (float32): the two octaves of ``NOISE_OCTAVES``."""
    out = None
    for weight, cells, offset in NOISE_OCTAVES:
        layer = weight * _grid_noise(size, seed + offset, cells)
        out = layer if out is None else out + layer
    return out


def _grid_noise(size, seed, cells):
    """Deterministic noise 0..1 (bilinear upscaled random grid) - the formula of 0.17.0 (``stylebake._noise``)."""
    import numpy as np

    grid = np.random.RandomState(seed % 2**31).rand(cells + 1, cells + 1).astype(np.float32)
    x = np.linspace(0, cells, size, dtype=np.float32)
    i = np.minimum(x.astype(np.int32), cells - 1)
    f = x - i
    rows = grid[i] * (1 - f)[:, None] + grid[i + 1] * f[:, None]
    return rows[:, i] * (1 - f)[None, :] + rows[:, i + 1] * f[None, :]


def to_byte(values):
    """0..1 -> uint8 as Blender stores a float in a byte image (float32: floor(255 x + 0.5), clamped) - the one
    quantisation every packed channel and every ``MTP_`` map goes through."""
    import numpy as np

    v = np.asarray(values, dtype=np.float32)
    return np.clip(np.floor(v * np.float32(255.0) + np.float32(0.5)), 0, 255).astype(np.uint8)


def from_byte(values):
    import numpy as np

    return np.asarray(values, dtype=np.float32) / np.float32(255.0)


def encode_detail(detail):
    import numpy as np

    lo, hi = DETAIL_RANGE
    return to_byte((np.clip(detail, lo, hi) - lo) / (hi - lo))


def decode_detail(byte):
    import numpy as np

    lo, hi = DETAIL_RANGE
    return (np.float32(lo) + from_byte(byte) * np.float32(hi - lo)).astype(np.float32)


def pack(weights: Sequence, layout: Sequence[Sequence[str]], ao, edge, up, height, noise_map, detail=None) -> Dict:
    """The packed maps (uint8 arrays, bottom-up) from ``compose``'s float inputs: ``{"W0", "W1"[, "W2"], "Fields"}``
    (the normal is a file of its own). ``height`` None: 0; ``detail`` None: 1 (plain)."""
    import numpy as np

    if not layout or len(layout) != len(weights) or len(layout) > 3:
        raise ValueError(f"weight layout of 1-3 groups expected, got {len(layout)} for {len(weights)} weight maps")
    shape = np.asarray(ao).shape
    out = {}
    for k in range(max(2, len(layout))):
        rgb = to_byte(np.asarray(weights[k])[..., :3]) if k < len(layout) else np.zeros(shape + (3,), np.uint8)
        if k == 0:
            alpha = to_byte(noise_map)
        elif k == 1:
            alpha = encode_detail(np.ones(shape, np.float32) if detail is None else detail)
        else:
            alpha = np.full(shape, 255, np.uint8)
        out[f"W{k}"] = np.concatenate([rgb, alpha[..., None]], axis=2)
    out["Fields"] = np.stack([to_byte(ao), to_byte(edge), to_byte(up),
                              to_byte(np.zeros(shape, np.float32) if height is None else height)], axis=2)
    return out


def unpack(packed: Dict, layout: Sequence[Sequence[str]]) -> Dict:
    """``compose``'s inputs from the packed maps - exactly the values a shader samples (8 bit / 255)."""
    fields = from_byte(packed["Fields"])
    return {
        "weights": [from_byte(packed[f"W{k}"][..., :3]) for k in range(len(layout))],
        "noise": from_byte(packed["W0"][..., 3]),
        "detail": decode_detail(packed["W1"][..., 3]),
        "ao": fields[..., 0], "edge": fields[..., 1], "up": fields[..., 2], "height": fields[..., 3],
    }


def compose_packed(packed: Dict, layout: Sequence[Sequence[str]], paint: str) -> Dict:
    """``paint.compose`` from the packed maps: the reference a shader reproduces."""
    from .paint import compose

    m = unpack(packed, layout)
    return compose(m["weights"], [tuple(g) for g in layout], m["ao"], m["edge"], m["up"], m["noise"], paint,
                   m["detail"], m["height"])


def to_srgb(linear):
    import numpy as np

    linear = np.asarray(linear, dtype=np.float32)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - 0.055)


def final_maps(result: Dict) -> Dict[str, object]:
    """``compose``'s result as the uint8 arrays of the ``MTP_`` files (bottom-up): Albedo and Emission sRGB (RGB),
    Roughness grey (RGB), MetallicSmoothness (RGBA: R metallic, A smoothness = 1 - roughness). The same values
    ``stylebake.compose_paint`` hands Blender to save."""
    import numpy as np

    rough = result["roughness"]
    grey = np.repeat(result["metallic"][..., None], 3, axis=2)
    return {"Albedo": to_byte(to_srgb(result["albedo"])), "Emission": to_byte(to_srgb(result["emission"])),
            "Roughness": to_byte(np.repeat(rough[..., None], 3, axis=2)),
            "MetallicSmoothness": np.concatenate([to_byte(grey), to_byte(1.0 - rough)[..., None]], axis=2)}


# ---------------------------------------------------------------------------
# PNG without Blender or ImageMagick (8 bit; written with filter 0, deterministic, no date chunks)
# ---------------------------------------------------------------------------

_COLOR_TYPES = {1: 0, 2: 4, 3: 2, 4: 6}  # channels -> PNG colour type (grey, grey+alpha, RGB, RGBA)


def write_png(path: str, array) -> str:
    """An H x W x C uint8 array (bottom-up rows, C = 1-4) as PNG."""
    import numpy as np

    data = np.asarray(array, dtype=np.uint8)
    if data.ndim == 2:
        data = data[..., None]
    h, w, c = data.shape
    rows = np.ascontiguousarray(data[::-1].reshape(h, w * c))
    raw = np.concatenate([np.zeros((h, 1), np.uint8), rows], axis=1).tobytes()

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, _COLOR_TYPES[c], 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return path


def read_png(path: str):
    """A PNG (8 bit, not interlaced, any filter - also Blender's and ImageMagick's) as H x W x C uint8, bottom-up.
    Palette images are expanded to RGB(A)."""
    import numpy as np

    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path}: not a PNG")
    pos, idat, palette, alpha = 8, [], None, None
    w = h = depth = ctype = interlace = 0
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            palette = np.frombuffer(body, np.uint8).reshape(-1, 3)
        elif kind == b"tRNS":
            alpha = np.frombuffer(body, np.uint8)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if depth != 8 or interlace:
        raise ValueError(f"{path}: only 8-bit, non-interlaced PNGs (depth {depth}, interlace {interlace})")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * channels
    raw = np.frombuffer(zlib.decompress(b"".join(idat)), np.uint8).reshape(h, stride + 1)
    out = np.zeros((h, stride), np.int32)
    prev = np.zeros(stride, np.int32)
    for y in range(h):
        kind, line = raw[y, 0], raw[y, 1:].astype(np.int32)
        if kind == 0:
            row = line
        elif kind == 2:
            row = (line + prev) & 0xFF
        elif kind in (1, 3, 4):
            row = _unfilter(kind, line, prev, channels)
        else:
            raise ValueError(f"{path}: unknown filter {kind}")
        out[y] = row
        prev = row
    image = out.astype(np.uint8).reshape(h, w, channels)
    if ctype == 3:
        rgb = palette[image[..., 0]]
        if alpha is not None:
            a = np.full(len(palette), 255, np.uint8)
            a[:len(alpha)] = alpha
            rgb = np.concatenate([rgb, a[image[..., 0]][..., None]], axis=2)
        image = rgb
    return image[::-1].copy()


def _unfilter(kind, line, prev, bpp):
    """Sub (1), Average (3), Paeth (4): sequential within a row, one pixel (``bpp`` bytes) at a time."""
    row = [0] * len(line)
    line, prev = line.tolist(), prev.tolist()
    for i in range(len(line)):
        a = row[i - bpp] if i >= bpp else 0
        if kind == 1:
            pred = a
        elif kind == 3:
            pred = (a + prev[i]) >> 1
        else:
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
        row[i] = (line[i] + pred) & 0xFF
    import numpy as np

    return np.asarray(row, np.int32)


def write_neutral(packed: Dict, model: str, out_dir: str) -> Dict[str, str]:
    """``MTN_<model>_<map>.png`` for every packed map; returns {map: path}."""
    import os

    return {key: write_png(os.path.join(out_dir, file_name(model, key)), packed[key])
            for key in NEUTRAL_KEYS if key in packed}


def read_neutral(paths: Dict[str, str]) -> Dict:
    """The packed maps back from their files (``Normal`` is not needed to compose and stays out)."""
    return {key: read_png(path) for key, path in paths.items() if key != "Normal"}


def max_difference(a, b) -> Tuple[int, float]:
    """Largest absolute difference (0..255) and the share of pixels that differ at all - for reference checks."""
    import numpy as np

    diff = np.abs(np.asarray(a, np.int16) - np.asarray(b, np.int16))
    return int(diff.max()) if diff.size else 0, float((diff.max(axis=-1) > 0).mean()) if diff.size else 0.0


__all__ = ["NEUTRAL_KEYS", "NEUTRAL_REQUIRED", "DETAIL_RANGE", "NOISE_OCTAVES", "PREFIX", "CHANNELS", "file_name",
           "noise", "pack", "unpack", "compose_packed", "final_maps", "write_png", "read_png", "write_neutral",
           "read_neutral", "encode_detail", "decode_detail", "to_byte", "from_byte", "to_srgb", "max_difference"]

