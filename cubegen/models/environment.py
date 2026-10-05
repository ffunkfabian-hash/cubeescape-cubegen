"""Environment modules: doors, floating platforms, walls and pillars.

Same part names as the hand-made assets in the game, so the existing Unity
scripts work with generated variants:

* doors: ``Frame_Left``, ``Frame_Right``, ``Frame_Top`` (colliders),
  ``StatusLight_Front`` / ``StatusLight_Back``, ``Panel`` (+ ``Panel_B`` for
  split doors, pivot in the leaf centre)
* platforms: walkable top at z = 0, ``Deck`` + ``Glow``
* walls: 3 m high, 0.5 m thick, ``Wall`` + ``Glow``
"""

from __future__ import annotations

import math

from .common import ALONG_X, cube, cyl, deg, frustum, glow_material, rail, stripes
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


@model("door", "Door", "environment", "Door with frame, status lights and one or two moving leaves (6 styles)")
def door(rng, a):
    style = rng.choice(sorted(DOOR_STYLES))
    (w0, w1), (h0, h1), post, depth, frame_mat, panel_mat, split, stripe_mat, accent, top = DOOR_STYLES[style]
    width = round(rng.uniform(w0, w1) * 5) / 5   # snap to 0.2 m so doors fit wall openings
    height = round(rng.uniform(h0, h1) * 5) / 5
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
                {"openOffset": _door_offset(style, width, height, split), "speed": DOOR_MOTION[style][1]},
                note="openOffset in Unity units relative to the leaf's rest position; split leaves move by the "
                     "sign of their localPosition")


@model("platform", "Platform", "environment", "Floating platform (walkable top at z = 0): square or octagonal, "
       "tapered underside or crystal keel", pivot="top")
def platform(rng, a):
    size = rng.choice([1.0, 2.0, 2.0, 3.0, 4.0])
    shape = rng.choice(["square", "square", "octagon"])
    deck_mat = rng.choice(["M_Platform", "M_Platform", "M_Metal"])
    glow = glow_material(rng)
    deck, lights = a.part("Deck"), a.part("Glow")
    under = rng.choice(["frustum", "frustum", "keel"])
    a.meta.update({"size_m": size, "shape": shape, "underside": under})

    if shape == "square":
        cube(deck, (size, size, 0.25), (0, 0, -0.125), deck_mat, bevel=0.04)
        cube(lights, (size - 0.1, size - 0.1, 0.06), (0, 0, -0.28), glow)
    else:
        r = size / 2 / math.cos(math.pi / 8)  # apothem = size / 2
        cyl(deck, r, 0.25, (0, 0, -0.125), deck_mat, sides=8, bevel=0.03)
        cyl(lights, r * 0.96, 0.06, (0, 0, -0.28), glow, sides=8)
    depth = 0.35 + size * 0.3
    if under == "frustum":
        u = size * rng.uniform(0.3, 0.45)
        if shape == "square":
            frustum(deck, (u, u), (size - 0.2, size - 0.2), -0.31 - depth, -0.31, "M_RobotDark")
        else:
            cyl(deck, u / 2, depth, (0, 0, -0.31 - depth / 2), "M_RobotDark", sides=8, radius_top=size / 2 * 0.9)
    else:
        kr = size * 0.18
        cyl(deck, kr, depth * 0.5, (0, 0, -0.31 - depth * 0.25), "M_Crystal", sides=6, radius_top=kr * 1.4)
        cyl(deck, kr, depth * 0.6, (0, 0, -0.31 - depth * 0.5 - depth * 0.3), "M_Crystal", sides=6, radius_top=0.0,
            rot=(math.pi, 0, 0))
    if size >= 2 and rng.random() < 0.3:
        rail(a.part("Rail"), size - 0.2, True, size / 2 - 0.1)
        a.meta["rail"] = True
    if rng.random() < 0.3:
        stripes(deck, size * 0.8, (0, -size / 2 + 0.12, 0.006), count=6, width=0.12)


@model("wall", "Wall", "environment", "Wall module 2 or 4 m long, 3 m high, 0.5 m thick: panel layouts, glow lines, pipes")
def wall(rng, a):
    length = rng.choice([2.0, 4.0, 4.0])
    m, lights = a.part("Wall"), a.part("Glow")
    glow = glow_material(rng)
    cube(m, (length, 0.5, 3.0), (0, 0, 1.5), "M_Wall", bevel=0.03)
    cube(m, (length, 0.56, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.01)
    cube(m, (length, 0.60, 0.15), (0, 0, 2.95), "M_RobotDark", bevel=0.01)
    layout = rng.choice(["tall", "split", "grid", "vent"])
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
    lines = rng.choice(["top", "both", "vertical"])
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
    if rng.random() < 0.3:  # pipe along the front
        z = rng.uniform(0.5, 2.2)
        cyl(m, 0.07, length, (0, -0.4, z), "M_Metal", rot=ALONG_X)
        for x in (-length / 2 + 0.4, length / 2 - 0.4):
            cube(m, (0.08, 0.16, 0.08), (x, -0.32, z), "M_RobotDark")
        a.meta["pipe"] = True
    if rng.random() < 0.2:
        stripes(m, length * 0.9, (0, -0.29, 0.125), count=int(length * 2), width=0.02, height=0.2)


@model("pillar", "Pillar", "environment", "Square or octagonal pillar with base, cap, glow strips and warning band")
def pillar(rng, a):
    w = rng.uniform(0.4, 1.2)
    h = rng.choice([3.0, 3.0, 4.0])
    shape = rng.choice(["square", "octagon"])
    mat = rng.choice(["M_Wall", "M_Metal"])
    glow = glow_material(rng)
    body, lights = a.part("Body"), a.part("Glow")
    a.meta.update({"shape": shape, "height_m": h})
    if shape == "square":
        cube(body, (w, w, h), (0, 0, h / 2), mat, bevel=0.04)
        for z, zh in ((0.125, 0.25), (h - 0.09, 0.2)):  # cap 1 cm above the body: no z-fighting
            cube(body, (w + 0.15, w + 0.15, zh), (0, 0, z), "M_RobotDark", bevel=0.02)
        for x in (-1, 1):
            for y in (-1, 1):
                cube(lights, (0.04, 0.04, h * 0.72), (x * (w / 2 + 0.005), y * (w / 2 + 0.005), h / 2), glow)
    else:
        r = w / 2 / math.cos(math.pi / 8)
        cyl(body, r, h, (0, 0, h / 2), mat, sides=8, bevel=0.03)
        for z, zh in ((0.125, 0.25), (h - 0.09, 0.2)):
            cyl(body, r + 0.08, zh, (0, 0, z), "M_RobotDark", sides=8, bevel=0.02)
        for i in range(4):
            ang = math.pi / 2 * i - math.pi / 2
            ap = w / 2 + 0.005
            cube(lights, (0.06 if i % 2 == 0 else 0.02, 0.02 if i % 2 == 0 else 0.06, h * 0.72),
                 (math.cos(ang) * ap, math.sin(ang) * ap, h / 2), glow)
    if rng.random() < 0.35:
        cube(body, (w + 0.04, w + 0.04, 0.2), (0, 0, 0.5), "M_Warning")
