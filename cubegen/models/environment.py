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
from .common import ALONG_X, cube, cyl, deg, frustum, stripes
from .registry import model

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


def _door_offset(style: str, width: float, height: float, split) -> list:
    direction, _ = DOOR_MOTION[style]
    if direction == "side":
        leaf = width / 2 if split == "x" else width
        return [round(leaf + 0.05, 4), 0.0, 0.0]
    if direction == "vertical":  # split up/down - each leaf moves away from the centre (sign of its position)
        return [0.0, round(height / 2 + 0.05, 4), 0.0]
    return [0.0, round((height + 0.1) * (-1 if direction == "down" else 1), 4), 0.0]


@model("door", "Door", "environment", "Door with frame, status lights and one or two moving leaves (6 styles)",
       params=[
           Param("style", "choice", "Stil", choices=tuple(sorted(DOOR_STYLES))),
           Param("width", "float", "Öffnung Breite (m)", lo=0.6, hi=8.0, size=True),
           Param("height", "float", "Öffnung Höhe (m)", lo=1.2, hi=8.0, size=True),
           Param("speed", "float", "Öffnungstempo (m/s)", lo=0.05, hi=20.0, unity=True),
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

    if split == "x":
        leaf("Panel", width / 2, height, (-width / 4, 0, height / 2))
        leaf("Panel_B", width / 2, height, (width / 4, 0, height / 2))
    elif split == "z":
        leaf("Panel", width, height / 2, (0, 0, height / 4))
        leaf("Panel_B", width, height / 2, (0, 0, height * 3 / 4))
    else:
        leaf("Panel", width, height, (0, 0, height / 2))

    panels = ["Panel", "Panel_B"] if split else ["Panel"]
    a.behaviour("Door", {"panels": panels, "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Frame_Top"]},
                {"openOffset": _door_offset(style, width, height, split),
                 "speed": p.value("speed", DOOR_MOTION[style][1])},
                note="openOffset in Unity units relative to the leaf's rest position; split leaves move by the "
                     "sign of their localPosition")


@model("platform", "Platform", "environment", "Square floating platform (walkable top at z = 0), "
       "tapered underside or crystal keel", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 3.0, 4.0)),
           Param("underside", "choice", "Unterseite", choices=("frustum", "keel")),
           Param("stripes", "bool", "Warnstreifen vorne"),
       ])
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


@model("wall", "Wall", "environment", "Wall module 2 or 4 m long, 3 m high, 0.5 m thick: panel layouts, glow lines, pipes",
       params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("layout", "choice", "Panel-Layout", choices=("tall", "split", "grid", "vent")),
           Param("lines", "choice", "Glow-Linien", choices=("top", "both", "vertical")),
           Param("pipe", "bool", "Rohr vorne"),
           Param("pipe_height", "float", "Rohr-Höhe (m)", lo=0.2, hi=2.8, description="Nur mit Rohr"),
           Param("stripes", "bool", "Warnstreifen unten"),
       ])
def wall(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0, 4.0])
    m, lights = a.part("Wall"), a.part("Glow")
    glow = p.glow()
    cube(m, (length, 0.5, 3.0), (0, 0, 1.5), p.styled("M_Wall", ["M_Wall", "M_Metal"]), bevel=0.03)
    cube(m, (length, 0.56, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.01)
    cube(m, (length, 0.60, 0.15), (0, 0, 2.95), "M_RobotDark", bevel=0.01)
    layout = p.choice("layout", ["tall", "split", "grid", "vent"])
    a.meta.update({"length_m": length, "layout": layout})
    for i in range(int(length // 2)):
        x = -length / 2 + 1 + i * 2
        for y in (-0.26, 0.26):
            if layout == "tall":
                cube(m, (1.7, 0.04, 1.8), (x, y, 1.35), "M_Ground", bevel=0.01)
            elif layout == "split":
                cube(m, (1.7, 0.04, 1.1), (x, y, 1.0), "M_Ground", bevel=0.01)
                cube(m, (1.7, 0.04, 0.5), (x, y, 2.0), "M_Ground", bevel=0.01)
            elif layout == "grid":
                for dx in (-0.45, 0.45):
                    for z in (0.85, 1.85):
                        cube(m, (0.8, 0.04, 0.85), (x + dx, y, z), "M_Ground", bevel=0.01)
            else:
                cube(m, (1.7, 0.04, 1.8), (x, y, 1.35), "M_Ground", bevel=0.01)
                if y < 0:  # vent grille on the front only
                    for k in range(6):
                        cube(m, (1.2, 0.05, 0.04), (x, y - 0.02, 0.8 + k * 0.12), "M_RobotDark", rot=(deg(30), 0, 0))
    lines = p.choice("lines", ["top", "both", "vertical"])
    for y in (-0.285, 0.285):
        if lines in ("top", "both"):
            cube(lights, (length - 0.4, 0.02, 0.05), (0, y, 2.45), glow)
        if lines == "both":
            cube(lights, (length - 0.4, 0.02, 0.04), (0, y, 0.32), glow)
        if lines == "vertical":
            for i in range(int(length // 2) + 1):
                x = -length / 2 + i * 2
                x = max(-length / 2 + 0.1, min(length / 2 - 0.1, x))
                cube(lights, (0.04, 0.02, 2.2), (x, y, 1.45), glow)
    if p.bool("pipe", 0.3):  # pipe along the front
        z = p.value("pipe_height", rng.uniform(0.5, 2.2))
        cyl(m, 0.07, length, (0, -0.4, z), "M_Metal", rot=ALONG_X)
        for x in (-length / 2 + 0.4, length / 2 - 0.4):
            cube(m, (0.08, 0.16, 0.08), (x, -0.32, z), "M_RobotDark")
        a.meta["pipe"] = True
    if p.bool("stripes", 0.2, warning=True):
        stripes(m, length * 0.9, (0, -0.29, 0.125), count=int(length * 2), width=0.02, height=0.2)


@model("pillar", "Pillar", "environment", "Square pillar with base, cap, glow strips and warning band",
       params=[
           Param("width", "float", "Breite (m)", lo=0.2, hi=3.0, size=True),
           Param("height", "choice", "Höhe (m)", choices=(3.0, 4.0)),
           Param("warning_band", "bool", "Warnband"),
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
