"""Environment modules: doors, floating platforms, walls and pillars.

Same part names as the hand-made assets in the game, so the existing Unity
scripts work with generated variants:

* doors: ``Frame_Left``, ``Frame_Right``, ``Frame_Top`` (colliders),
  ``StatusLight_Front`` / ``StatusLight_Back``, ``Panel`` (+ ``Panel_B`` for
  split doors, pivot in the leaf centre)
* platforms: square, walkable top at z = 0, ``Deck`` + ``Glow``
* walls: 3 m high, 0.5 m thick, ``Wall`` + ``Glow``
"""

from __future__ import annotations

import math

from ..params import Param
from ..geometry import prism, ring
from .common import ALONG_X, cube, cyl, deg, frustum, stripes
from .dressing import dress_pillar, dressing_param
from .lettering import add_text, check_text, text_width
from .registry import model

UPRIGHT = ((1, 0, 0), (0, 0, -1), (0, 1, 0))  # (x, z) polygon facing the front, extruded towards -y

DOOR_STYLES = {
    #            width       height      post  depth frame          panel          split  stripes      accent        top
    "sliding":  ((1.6, 2.4), (2.4, 2.8), 0.4, 0.6, "M_Wall",      "M_Platform", None, None,         "M_GlowCyan", None),
    "heavy":    ((2.6, 3.4), (2.8, 3.2), 0.6, 0.9, "M_RobotDark", "M_Metal",    None, "M_Warning",  None,         0.6),
    "security": ((1.6, 2.2), (2.4, 2.8), 0.5, 0.7, "M_RobotDark", "M_Wall",     None, None,         "M_GlowRed",  None),
    "elevator": ((2.0, 2.6), (2.6, 3.0), 0.45, 0.6, "M_Wall",     "M_Metal",    "x",  None,         "M_Warning",  None),
    "airlock":  ((2.0, 2.6), (2.6, 3.0), 0.6, 1.0, "M_RobotDark", "M_Wall",     "z",  "M_Warning",  None,         0.6),
    "blast":    ((3.4, 4.4), (3.0, 3.6), 0.8, 1.2, "M_RobotDark", "M_Metal",    None, "M_HazardOrange", None,     0.8),
}


# How the game's Door recipes move the leaves (ModularBlocks.cs): direction, speed (m/s).
# The distance follows the generated size the same way: leaf width + 0.05 sideways,
# leaf height + 0.1 for single vertical leaves, leaf height + 0.05 for split vertical leaves.
DOOR_MOTION = {
    "sliding":  ("side", 3.0),     # Door_Sliding 2.05 for a 2.0 m opening
    "heavy":    ("down", 0.9),     # Door_Heavy -3.1 for 3.0 m
    "security": ("down", 4.0),     # Door_Security -2.7 for 2.6 m
    "elevator": ("side", 1.8),     # Door_Elevator 1.25 per leaf for 2.4 m, split
    "airlock":  ("vertical", 1.2),  # Door_Airlock 1.45 per leaf for 2.8 m, split
    "blast":    ("up", 0.6),       # Door_Blast 3.5 for 3.4 m
}


DOOR_VARIANTS = ("standard", "iris")


def _iris(a, width: float, height: float, opened: float) -> None:
    """A round iris diaphragm filling the door opening: corner plates (Iris_Frame) around a round hole, a trim ring
    and six layered blades (Iris). ``opened`` 0..1 pulls the blade tips from the centre to the rim."""
    r = min(width, height) * 0.475
    zc = height / 2
    plate = a.part("Iris_Frame")
    arc = 6
    for qx in (-1, 1):
        for qz in (-1, 1):
            pts = [(qx * width / 2, 0.0), (qx * width / 2, qz * height / 2), (0.0, qz * height / 2)]
            pts += [(qx * r * math.sin(math.pi / 2 * k / arc), qz * r * math.cos(math.pi / 2 * k / arc))
                    for k in range(arc + 1)]
            plate.add(prism(pts, 0.2, "M_RobotDark"), loc=(0, 0, zc), basis=UPRIGHT)
    trim = a.part("Iris_Trim")
    trim.add(ring(r - 0.02, r + 0.1, 0.26, 24, "M_Metal"), loc=(0, 0, zc), rot=(math.pi / 2, 0, 0))
    blades = a.part("Iris")
    n, step = 6, 2 * math.pi / 6
    tip = opened * 0.9  # blade tip radius as a share of r: 0 = the six tips meet in the centre
    for i in range(n):
        t0 = step * i
        pts = [(r * math.cos(t0), r * math.sin(t0)), (r * math.cos(t0 + step * 1.35), r * math.sin(t0 + step * 1.35)),
               (r * tip * math.cos(t0 + step * 0.9), r * tip * math.sin(t0 + step * 0.9))]
        y = -0.03 + i * 0.012  # layered: every blade in its own plane, no flickering overlaps
        blades.add(prism(pts, 0.01, "M_Metal" if i % 2 else "M_Wall"), loc=(0, y + 0.005, zc), basis=UPRIGHT)
    a.meta["iris"] = {"radius_m": round(r, 4), "open": round(opened, 3), "clear_radius_m": round(r * tip, 4)}


def _door_offset(style: str, width: float, height: float, split) -> list:
    direction, _ = DOOR_MOTION[style]
    if direction == "side":
        leaf = width / 2 if split == "x" else width
        return [round(leaf + 0.05, 4), 0.0, 0.0]
    if direction == "vertical":  # split up/down: the first leaf (the upper one) rises, the second sinks
        return [0.0, round(height / 2 + 0.05, 4), 0.0]
    return [0.0, round((height + 0.1) * (-1 if direction == "down" else 1), 4), 0.0]


@model("door", "Door", "environment", "Door with frame, status lights and one or two moving leaves (6 styles)",
       params=[
           Param("style", "choice", "Stil", choices=tuple(sorted(DOOR_STYLES))),
           Param("width", "float", "Öffnung Breite (m)", lo=0.6, hi=8.0, size=True),
           Param("height", "float", "Öffnung Höhe (m)", lo=1.2, hi=8.0, size=True),
           Param("speed", "float", "Öffnungstempo (m/s)", lo=0.05, hi=20.0, unity=True),
           Param("label", "text", "Raumnummer / Beschriftung", quiet=True,
                 description="Schild über der Tür, z. B. B-12 (bis 12 Zeichen); eigenes statisches Teil Label"),
           Param("variant", "choice", "Variante", choices=DOOR_VARIANTS, default="standard", quiet=True,
                 description="iris: runde Irisblende (Iris) im Rahmen - statisches Modell ohne Door-Script, "
                             "die Lamellen öffnen nicht linear"),
           Param("iris_open", "float", "Irisblende offen (0-1)", lo=0.0, hi=1.0, default=0.0, quiet=True,
                 description="Nur Variante iris: 0 = geschlossen, 1 = offen (freier Durchgang in der Mitte)"),
       ])
def door(rng, a):
    p = a.p
    style = p.choice("style", sorted(DOOR_STYLES))
    (w0, w1), (h0, h1), post, depth, frame_mat, panel_mat, split, stripe_mat, accent, top = DOOR_STYLES[style]

    def opening(name, lo, hi):
        value = p.float(name, lo, hi)
        if name not in p.overrides and p.style.snap == 0:
            value = round(value * 5) / 5  # snap to 0.2 m so doors fit wall openings
        p.used[name] = value
        return value

    width = opening("width", w0, w1)
    height = opening("height", h0, h1)
    top = top if top is not None else post
    a.meta.update({"style": style, "opening_m": [width, height], "split": split})

    for side, x in (("Left", -(width + post) / 2), ("Right", (width + post) / 2)):
        m = a.part(f"Frame_{side}")
        cube(m, (post, depth, height + top), (x, 0, (height + top) / 2), frame_mat, bevel=0.03)
        cube(m, (post + 0.06, depth + 0.06, 0.25), (x, 0, 0.125), "M_RobotDark", bevel=0.01)
        if accent:
            cube(m, (0.06, depth + 0.02, height * 0.8), (x - math.copysign(post / 2, x), 0, height * 0.45), accent)
    t = a.part("Frame_Top")
    cube(t, (width, depth, top), (0, 0, height + top / 2), frame_mat, bevel=0.03)
    if accent:
        cube(t, (width, depth + 0.02, 0.1), (0, 0, height + 0.05), accent)
    for side, y in (("Front", -(depth / 2 + 0.01)), ("Back", depth / 2 + 0.01)):
        cube(a.part(f"StatusLight_{side}"), (min(1.2, width * 0.6), 0.02, 0.1), (0, y, height + top / 2), "M_GlowRed")

    def leaf(name, w, h, center):
        p = a.part(name, pivot=center)
        cx, cy, cz = center
        cube(p, (w, 0.25, h), center, panel_mat, bevel=0.02)
        bands = rng.choice([(0.2, -0.2), (0.3, 0.0, -0.3), (0.25,)])
        for f in bands:
            cube(p, (w - 0.1, 0.27, 0.05), (cx, cy, cz + h * f), "M_RobotDark")
        if stripe_mat:
            for i in range(max(1, int(w / 0.5))):
                cube(p, (0.12, 0.27, h * 0.25), (cx - w / 2 + 0.25 + i * 0.5, cy, cz - h * 0.35), stripe_mat,
                     rot=(0, deg(30), 0))

    variant = p.option("variant")
    if variant == "iris":
        _iris(a, width, height, p.option("iris_open"))
        a.meta["variant"] = "iris"
    elif split == "x":
        leaf("Panel", width / 2, height, (-width / 4, 0, height / 2))
        leaf("Panel_B", width / 2, height, (width / 4, 0, height / 2))
    elif split == "z":
        leaf("Panel", width, height / 2, (0, 0, height / 4))
        leaf("Panel_B", width, height / 2, (0, 0, height * 3 / 4))
    else:
        leaf("Panel", width, height, (0, 0, height / 2))

    label = p.option("label")
    if label:  # room number plate above the frame, proud of the wall face
        label = check_text(label, max_len=12)
        letters = 0.16
        lw = text_width(label, letters) + 0.16
        plate = a.part("Label")
        z = height + top + 0.06 + letters / 2 + 0.04
        cube(plate, (lw, 0.04, letters + 0.08), (0, -depth / 2 - 0.02, z), "M_RobotDark", bevel=0.01)
        add_text(plate, label, (0, -depth / 2 - 0.04, z), letters, 0.015, "M_Platform")
        a.meta["label"] = label

    if variant == "iris":
        return  # no linear leaves: a static model until an iris script exists (generation 3 gives exact meshes)
    # Unity moves the second leaf by -openOffset: first the leaf that moves along +openOffset
    panels = {"x": ["Panel", "Panel_B"], "z": ["Panel_B", "Panel"]}.get(split, ["Panel"])
    a.behaviour("Door", {"panels": panels, "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Frame_Top"]},
                {"openOffset": _door_offset(style, width, height, split),
                 "speed": p.value("speed", DOOR_MOTION[style][1])},
                note="openOffset in Unity units relative to the leaf's rest position; a second leaf moves by "
                     "-openOffset (Unity's default secondOffset), away from the first")


@model("platform", "Platform", "environment", "Square floating platform (walkable top at z = 0), "
       "tapered underside or crystal keel", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 3.0, 4.0)),
           Param("underside", "choice", "Unterseite", choices=("frustum", "keel")),
           Param("stripes", "bool", "Warnstreifen vorne"),
       ], set_faces=("x-", "x+", "y-", "y+"))  # decks join on four sides; stripes on top, the underside varies
def platform(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 2.0, 2.0, 3.0, 4.0])
    rng.choice(["square", "square", "octagon"])  # former shape roll - kept so other properties of seeds stay
    deck_mat = p.material(["M_Platform", "M_Platform", "M_Metal"])
    glow = p.glow()
    deck, lights = a.part("Deck"), a.part("Glow")
    under = p.choice("underside", ["frustum", "frustum", "keel"])
    a.meta.update({"size_m": size, "underside": under})

    cube(deck, (size, size, 0.25), (0, 0, -0.125), deck_mat, bevel=0.04)
    cube(lights, (size - 0.1, size - 0.1, 0.06), (0, 0, -0.28), glow)
    depth = 0.35 + size * 0.3
    if under == "frustum":
        u = size * rng.uniform(0.3, 0.45)
        frustum(deck, (u, u), (size - 0.2, size - 0.2), -0.31 - depth, -0.31, "M_RobotDark")
    else:
        kr = size * 0.18
        cyl(deck, kr, depth * 0.5, (0, 0, -0.31 - depth * 0.25), "M_Crystal", sides=6, radius_top=kr * 1.4)
        cyl(deck, kr, depth * 0.6, (0, 0, -0.31 - depth * 0.5 - depth * 0.3), "M_Crystal", sides=6, radius_top=0.0,
            rot=(math.pi, 0, 0))
    if size >= 2:
        rng.random()  # former railing roll - kept for seed stability, platforms have no railing any more
    if p.bool("stripes", 0.3, warning=True):
        stripes(deck, size * 0.8, (0, -size / 2 + 0.12, 0.006), count=6, width=0.12)
    a.mesh_collider("Deck")  # convex hull of slab + underside = the real shape, flat top


def door_frame_outer(style: str, width: float, height: float):
    """Outer size of a door's frame (= the wall opening a door of this style needs): width, height."""
    post, top = DOOR_STYLES[style][2], DOOR_STYLES[style][9]
    return width + 2 * post, height + (top if top is not None else post)


WALL_OPENINGS = ("none", "door", "window", "pipe")


@model("wall", "Wall", "environment", "Wall module 2 or 4 m long, 3 m high, 0.5 m thick: panel layouts, glow lines, "
       "pipes; optional opening for a door, a window or a pipe", params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("layout", "choice", "Panel-Layout", choices=("tall", "split", "grid", "vent")),
           Param("lines", "choice", "Glow-Linien", choices=("top", "both", "vertical")),
           Param("pipe", "bool", "Rohr vorne"),
           Param("pipe_height", "float", "Rohr-Höhe (m)", lo=0.2, hi=2.8, description="Nur mit Rohr"),
           Param("stripes", "bool", "Warnstreifen unten"),
           Param("height", "float", "Wandhöhe (m)", lo=2.0, hi=6.0, default=3.0, quiet=True),
           Param("thickness", "float", "Wandstärke (m)", lo=0.2, hi=1.0, default=0.5, quiet=True),
           Param("opening", "choice", "Öffnung", choices=WALL_OPENINGS, default="none", quiet=True,
                 description="Ausschnitt für eine Tür (Rahmenmaß der Tür), ein Fenster oder ein Rohr"),
           Param("opening_x", "float", "Öffnung Versatz (m)", lo=-4.0, hi=4.0, default=0.0, quiet=True),
           Param("door_style", "choice", "Tür-Stil", choices=tuple(sorted(DOOR_STYLES)), default="sliding",
                 quiet=True, description="Nur mit Türöffnung: bestimmt das Rahmenmaß"),
           Param("door_width", "float", "Tür Breite (m)", lo=0.6, hi=8.0, default=2.0, quiet=True),
           Param("door_height", "float", "Tür Höhe (m)", lo=1.2, hi=8.0, default=2.6, quiet=True),
           Param("window_width", "float", "Fenster Breite (m)", lo=0.4, hi=3.6, default=1.6, quiet=True),
           Param("window_height", "float", "Fenster Höhe (m)", lo=0.4, hi=2.5, default=1.2, quiet=True),
           Param("window_sill", "float", "Fenster Brüstung (m)", lo=0.2, hi=2.0, default=1.0, quiet=True),
           Param("duct_radius", "float", "Rohrdurchführung Radius (m)", lo=0.05, hi=0.5, default=0.18, quiet=True),
           Param("duct_height", "float", "Rohrdurchführung Achshöhe (m)", lo=0.2, hi=2.6, default=0.6, quiet=True),
       ])
def wall(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0, 4.0])
    h, t = p.option("height"), p.option("thickness")
    dh, dt = h - 3.0, t - 0.5   # 0.0 for the standard module: the classic wall, bit for bit
    hs = h / 3.0                # panel heights scale with the wall
    opening = p.option("opening")
    hole = _wall_hole(p, opening, length, h) if opening != "none" else None
    if hole is not None and hole["length"] != length:
        length = hole["length"]
        p.used["length"] = length
    m, lights = a.part("Wall"), a.part("Glow")
    glow = p.glow()
    mat = p.styled("M_Wall", ["M_Wall", "M_Metal"])
    if hole is None:
        cube(m, (length, 0.5 + dt, 3.0 + dh), (0, 0, 1.5 + dh / 2), mat, bevel=0.03)
        cube(m, (length, 0.56 + dt, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.01)
        cube(m, (length, 0.60 + dt, 0.15), (0, 0, 2.95 + dh), "M_RobotDark", bevel=0.01)
    else:
        _wall_with_hole(a, m, mat, length, h, t, hole)
    layout = p.choice("layout", ["tall", "split", "grid", "vent"])
    a.meta.update({"length_m": length, "layout": layout})
    clear = (lambda x0, x1, z0, z1: True) if hole is None else hole["clear"]
    for i in range(int(length // 2)):
        x = -length / 2 + 1 + i * 2
        if not clear(x - 0.9, x + 0.9, 0.0, h):
            continue
        for y in (-0.26 - dt / 2, 0.26 + dt / 2):
            if layout == "tall":
                cube(m, (1.7, 0.04, 1.8 * hs), (x, y, 1.35 * hs), "M_Ground", bevel=0.01)
            elif layout == "split":
                cube(m, (1.7, 0.04, 1.1 * hs), (x, y, 1.0 * hs), "M_Ground", bevel=0.01)
                cube(m, (1.7, 0.04, 0.5 * hs), (x, y, 2.0 * hs), "M_Ground", bevel=0.01)
            elif layout == "grid":
                for dx in (-0.45, 0.45):
                    for z in (0.85, 1.85):
                        cube(m, (0.8, 0.04, 0.85 * hs), (x + dx, y, z * hs), "M_Ground", bevel=0.01)
            else:
                cube(m, (1.7, 0.04, 1.8 * hs), (x, y, 1.35 * hs), "M_Ground", bevel=0.01)
                if y < 0:  # vent grille on the front only
                    for k in range(6):
                        cube(m, (1.2, 0.05, 0.04), (x, y - 0.02, 0.8 + k * 0.12), "M_RobotDark", rot=(deg(30), 0, 0))
    lines = p.choice("lines", ["top", "both", "vertical"])
    for y in (-0.285 - dt / 2, 0.285 + dt / 2):
        for z, th in (((2.45 + dh, 0.05),) if lines in ("top", "both") else ()) + \
                (((0.32, 0.04),) if lines == "both" else ()):
            for x0, x1 in _free_spans(-length / 2 + 0.2, length / 2 - 0.2, z - th, z + th, hole):
                cube(lights, (x1 - x0, 0.02, th), ((x0 + x1) / 2, y, z), glow)
        if lines == "vertical":
            for i in range(int(length // 2) + 1):
                x = -length / 2 + i * 2
                x = max(-length / 2 + 0.1, min(length / 2 - 0.1, x))
                if clear(x - 0.05, x + 0.05, 0.35, 2.55 + dh):
                    cube(lights, (0.04, 0.02, 2.2 + dh), (x, y, 1.45 + dh / 2), glow)
    if p.bool("pipe", 0.3):  # pipe along the front
        z = p.value("pipe_height", rng.uniform(0.5, 2.2))
        spans = _free_spans(-length / 2, length / 2, z - 0.1, z + 0.1, hole)
        for x0, x1 in spans:
            cyl(m, 0.07, x1 - x0, ((x0 + x1) / 2, -0.4 - dt / 2, z), "M_Metal", rot=ALONG_X)
        for x in (-length / 2 + 0.4, length / 2 - 0.4):
            if any(x0 <= x <= x1 for x0, x1 in spans):
                cube(m, (0.08, 0.16, 0.08), (x, -0.32 - dt / 2, z), "M_RobotDark")
        a.meta["pipe"] = True
    if p.bool("stripes", 0.2, warning=True) and (hole is None or hole["z0"] > 0.3):
        stripes(m, length * 0.9, (0, -0.29 - dt / 2, 0.125), count=int(length * 2), width=0.02, height=0.2)
    if hole is not None:
        a.meta["opening"] = {k: v for k, v in hole.items() if k not in ("clear", "length")}


def _free_spans(x0, x1, z0, z1, hole):
    """Parts of [x0, x1] a horizontal strip at z0..z1 can cover without crossing the opening (+10 cm)."""
    if hole is None or z1 <= hole["z0"] - 0.1 or z0 >= hole["z1"] + 0.1:
        return [(x0, x1)]
    spans = [(x0, min(x1, hole["x0"] - 0.1)), (max(x0, hole["x1"] + 0.1), x1)]
    return [(a, b) for a, b in spans if b - a > 0.15]


def _wall_hole(p, opening, length, h):
    """Rectangle of the opening (x0, x1, z0, z1) and the wall length it needs (the 2 m grid, at least)."""
    x = p.option("opening_x")
    if opening == "door":
        style = p.option("door_style")
        w, oh = door_frame_outer(style, p.option("door_width"), p.option("door_height"))
        z0, z1, extra = 0.0, oh, {"door_style": style, "door_width": p.option("door_width"),
                                  "door_height": p.option("door_height")}
    elif opening == "window":
        w = p.option("window_width")
        z0 = p.option("window_sill")
        z1, extra = z0 + p.option("window_height"), {}
    else:
        r = p.option("duct_radius")
        w = max(0.15, 2 * r * 1.4)  # room for the pipe and its flange
        zc = p.option("duct_height")
        z0, z1, extra = zc - w / 2, zc + w / 2, {"duct_radius": r, "duct_height": zc}
    z1 = min(z1, h - 0.3)  # keep the lintel and the top trim
    z0 = max(z0, 0.0 if opening == "door" else 0.3)
    need = w + 0.4
    full = max(length, 2.0 * math.ceil(need / 2.0 - 1e-9))
    x = max(-full / 2 + 0.2 + w / 2, min(full / 2 - 0.2 - w / 2, x))
    hole = {"kind": opening, "x0": x - w / 2, "x1": x + w / 2, "z0": z0, "z1": z1, "length": full,
            "center_x": x, "width": round(w, 4), "height": round(z1 - z0, 4), **extra}
    hole["clear"] = lambda a0, a1, b0, b1: a1 <= hole["x0"] - 0.1 or a0 >= hole["x1"] + 0.1 or \
        b1 <= hole["z0"] - 0.1 or b0 >= hole["z1"] + 0.1
    return hole


def _wall_with_hole(a, m, mat, length, h, t, hole):
    """Wall body around the opening: separate blocks, framed opening, own colliders (the opening stays free)."""
    x0, x1, z0, z1 = hole["x0"], hole["x1"], hole["z0"], hole["z1"]
    blocks = [(-length / 2, x0, 0.0, h), (x1, length / 2, 0.0, h), (x0, x1, 0.0, z0), (x0, x1, z1, h)]
    for bx0, bx1, bz0, bz1 in blocks:
        if bx1 - bx0 > 1e-6 and bz1 - bz0 > 1e-6:
            cube(m, (bx1 - bx0, t, bz1 - bz0), ((bx0 + bx1) / 2, 0, (bz0 + bz1) / 2), mat, bevel=0.03)
            a.collider((bx1 - bx0, t, bz1 - bz0), ((bx0 + bx1) / 2, 0, (bz0 + bz1) / 2))
    for tx0, tx1 in ((-length / 2, x0 - 0.03), (x1 + 0.03, length / 2)) if z0 < 0.25 else ((-length / 2, length / 2),):
        if tx1 - tx0 > 1e-6:  # base trim, interrupted by a door
            cube(m, (tx1 - tx0, t + 0.06, 0.25), ((tx0 + tx1) / 2, 0, 0.125), "M_RobotDark", bevel=0.01)
    cube(m, (length, t + 0.10, 0.15), (0, 0, h - 0.05), "M_RobotDark", bevel=0.01)
    w, oh, cx = x1 - x0, z1 - z0, (x0 + x1) / 2
    for s in (-1, 1):  # dark frame around the opening, front and back (outside the opening)
        if z0 > 0:
            cube(m, (w + 0.12, 0.06, 0.06), (cx, s * (t / 2 + 0.03), z0 - 0.03), "M_RobotDark")
        cube(m, (w + 0.12, 0.06, 0.06), (cx, s * (t / 2 + 0.03), z1 + 0.03), "M_RobotDark")
        for x in (x0 - 0.03, x1 + 0.03):
            cube(m, (0.06, 0.06, oh), (x, s * (t / 2 + 0.03), (z0 + z1) / 2), "M_RobotDark")
    if hole["kind"] == "window":
        glass = a.part("Glass")
        cube(glass, (w, 0.04, oh), (cx, 0, (z0 + z1) / 2), "M_Glass")
        cube(m, (w, 0.3, 0.05), (cx, -t / 2 - 0.04, z0 + 0.025), "M_Metal")  # sill board in front
        a.collider((w, 0.04, oh), (cx, 0, (z0 + z1) / 2), part="Glass")


@model("pillar", "Pillar", "environment", "Square pillar with base, cap, glow strips and warning band",
       params=[
           Param("width", "float", "Breite (m)", lo=0.2, hi=3.0, size=True),
           Param("height", "choice", "Höhe (m)", choices=(3.0, 4.0)),
           Param("warning_band", "bool", "Warnband"),
           dressing_param("ruin: Schutt am Fuß, Bewehrung, abgerissenes Kabel; organic: Ranken unter dem "
                          "Kopf, Steine und Büsche am Fuß"),
       ])
def pillar(rng, a):
    p = a.p
    w = p.float("width", 0.4, 1.2)
    h = p.choice("height", [3.0, 3.0, 4.0])
    rng.choice(["square", "octagon"])  # former shape roll - kept so other properties of seeds stay
    mat = p.material(["M_Wall", "M_Metal"])
    glow = p.glow()
    body, lights = a.part("Body"), a.part("Glow")
    a.meta.update({"height_m": h})
    cube(body, (w, w, h), (0, 0, h / 2), mat, bevel=0.04)
    for z, zh in ((0.125, 0.25), (h - 0.09, 0.2)):  # cap 1 cm above the body: no z-fighting
        cube(body, (w + 0.15, w + 0.15, zh), (0, 0, z), "M_RobotDark", bevel=0.02)
    for x in (-1, 1):
        for y in (-1, 1):
            cube(lights, (0.04, 0.04, h * 0.72), (x * (w / 2 + 0.005), y * (w / 2 + 0.005), h / 2), glow)
    if p.bool("warning_band", 0.35, warning=True):
        cube(body, (w + 0.04, w + 0.04, 0.2), (0, 0, 0.5), "M_Warning")
    dress_pillar(a, body, w, h, p.option("dressing"))
