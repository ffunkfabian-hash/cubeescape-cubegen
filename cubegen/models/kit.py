"""Modular building kit: stairs, ladders, catwalks, floor tiles, ceiling panels, wall corners, window walls,
cable trays, lifts, conveyors and jump / teleporter pads.

Sizes follow the wall module (3 m high, 0.5 m thick, 2 / 4 m long) and the
1 m floor grid. Walkable pieces (``catwalk``, ``floor_tile``) have their top at
z = 0 like the platforms.
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, fan, rail, stripes
from .dressing import dress_catwalk, dress_floor, dressing_param
from .registry import model

# turns a (y, z) polygon into a prism extruded along X (local x -> world y, local y -> world z, local z -> world x)
YZ_TO_X = ((0, 0, 1), (1, 0, 0), (0, 1, 0))
STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}


def slope_colliders(a, width, run, rise, center_x=0.0, layer=0.5, center_y=0.0, base_z=0.0, direction=1, part=None):
    """Colliders of a solid ramp climbing towards +Y (foot at y = center_y - run/2, z = base_z; top at
    y = center_y + run/2, z = base_z + rise); ``direction`` -1 climbs towards -Y.

    A thin box lies on the slope (smooth walking); stacked boxes below it fill the
    wedge, each one ending under the slope, so nothing sticks out of the ramp. Layers
    of at most 0.2 m leave no gap under the 0.1 m slope box (0.5 m: as up to generation 2).
    """
    slope, ln = math.atan2(rise, run), math.hypot(run, rise)
    t = 0.1
    # box top on the slope plane, shifted along the slope normal (0, -sin, cos) by t/2
    a.collider((width, ln, t), (center_x, center_y + direction * math.sin(slope) * t / 2,
                                base_z + rise / 2 - math.cos(slope) * t / 2),
               rot=(direction * slope, 0.0, 0.0), part=part)
    layers = max(1, int(math.ceil(rise / layer - 1e-9)))
    for i in range(layers):
        z0, z1 = rise * i / layers, rise * (i + 1) / layers
        y0 = -run / 2 + run * z1 / rise  # where the slope reaches the top of this layer
        if run / 2 - y0 > 0.02:
            a.collider((width, run / 2 - y0, z1 - z0),
                       (center_x, center_y + direction * (y0 + run / 2) / 2, base_z + (z0 + z1) / 2), part=part)


STAIR_LAYOUTS = ("straight", "landing", "quarter", "switchback")
STEP_RISE, STEP_RUN, SWITCHBACK_GAP = 0.2, 0.3, 0.1


def stair_flights(layout, w, rise):
    """Geometry of a stair layout: flights [(axis, sign, x, y, z0, steps)] (start of the first step,
    climbing along axis*sign), landing (x0, x1, y0, y1, z), bottom and top connector ((x, y, z), direction)."""
    steps = max(2, int(round(rise / STEP_RISE)))
    sh = rise / steps
    n1 = steps // 2
    n2 = steps - n1
    zl = n1 * sh
    run1 = n1 * STEP_RUN
    if layout == "landing":
        y0 = -(steps * STEP_RUN + w) / 2
        flights = [("y", 1, 0.0, y0, 0.0, n1), ("y", 1, 0.0, y0 + run1 + w, zl, n2)]
        landing = (-w / 2, w / 2, y0 + run1, y0 + run1 + w, zl)
        top = ((0.0, y0 + run1 + w + n2 * STEP_RUN, rise), (0, 1))
        bottom = ((0.0, y0, 0.0), (0, -1))
    elif layout == "quarter":
        y0 = -(run1 + w) / 2
        ya = y0 + run1
        flights = [("y", 1, 0.0, y0, 0.0, n1), ("x", 1, w / 2, ya + w / 2, zl, n2)]
        landing = (-w / 2, w / 2, ya, ya + w, zl)
        top = ((w / 2 + n2 * STEP_RUN, ya + w / 2, rise), (1, 0))
        bottom = ((0.0, y0, 0.0), (0, -1))
    else:  # switchback: up along +Y on the left, turn on the landing, up along -Y on the right
        xo = (w + SWITCHBACK_GAP) / 2
        y0 = -(run1 + w) / 2
        ya = y0 + run1
        flights = [("y", 1, -xo, y0, 0.0, n1), ("y", -1, xo, ya, zl, n2)]
        landing = (-xo - w / 2, xo + w / 2, ya, ya + w, zl)
        top = ((xo, ya - n2 * STEP_RUN, rise), (0, -1))
        bottom = ((-xo, y0, 0.0), (0, -1))
    return {"steps": steps, "step_rise": sh, "flights": flights, "landing": landing, "top": top, "bottom": bottom}


def _stairs_layout(rng, a, p, layout, w, rise, mat, glow):
    """Stairs with a landing, a quarter turn or a switchback (solid steps, like the straight flight)."""
    body = a.part("Body")
    geo = stair_flights(layout, w, rise)
    sh = geo["step_rise"]
    a.meta.update({"style": "stairs", "layout": layout, "steps": geo["steps"], "step_rise_m": round(sh, 4)})
    edges = p.bool("glow_edges", 0.4)
    lights = a.part("Glow") if edges else None
    k = 0
    for axis, sign, x, y, z0, n in geo["flights"]:
        for i in range(n):
            h = z0 + sh * (i + 1)
            d = (i + 0.5) * STEP_RUN * sign
            cx, cy = (x + d, y) if axis == "x" else (x, y + d)
            size = (STEP_RUN, w, h) if axis == "x" else (w, STEP_RUN, h)
            cube(body, size, (cx, cy, h / 2), "M_RobotDark" if k % 2 else mat)
            a.collider(size, (cx, cy, h / 2))
            nose = (-STEP_RUN * 0.375 * sign)
            nsize = (STEP_RUN * 0.25, w + 0.02, 0.02) if axis == "x" else (w + 0.02, STEP_RUN * 0.25, 0.02)
            cube(body, nsize, (cx + nose, cy, h + 0.01) if axis == "x" else (cx, cy + nose, h + 0.01), "M_Metal")
            if edges:
                e = -STEP_RUN / 2 * sign - 0.01 * sign
                esize = (0.02, w * 0.8, 0.02) if axis == "x" else (w * 0.8, 0.02, 0.02)
                cube(lights, esize, (cx + e, cy, h - 0.03) if axis == "x" else (cx, cy + e, h - 0.03), glow)
            k += 1
    lx0, lx1, ly0, ly1, zl = geo["landing"]
    cube(body, (lx1 - lx0, ly1 - ly0, zl), ((lx0 + lx1) / 2, (ly0 + ly1) / 2, zl / 2), mat)
    a.collider((lx1 - lx0, ly1 - ly0, zl), ((lx0 + lx1) / 2, (ly0 + ly1) / 2, zl / 2))
    cube(body, (lx1 - lx0 - 0.1, ly1 - ly0 - 0.1, 0.02), ((lx0 + lx1) / 2, (ly0 + ly1) / 2, zl + 0.01), "M_Metal")
    rails = p.choice("rails", ["none", "left", "both"])
    if rails != "none":
        for axis, sign, x, y, z0, n in geo["flights"]:
            run = n * STEP_RUN
            sides = (-1, 1) if rails == "both" else ((-1,) if axis == "y" and x <= 0 else (1,))
            for s in sides:
                _flight_rail(body, a, axis, sign, x, y, z0, run, n * sh, w, s)
        _landing_rails(body, a, layout, geo["landing"], w)
    if p.bool("stripes", 0.3, warning=True):
        (bx, by, _), _ = geo["bottom"]
        stripes(body, w * 0.9, (bx, by - 0.005, 0.06), count=max(3, int(w * 3)), width=0.01, height=0.1)


def _flight_rail(body, a, axis, sign, x, y, z0, run, rise, w, side):
    """Sloped railing on one side of a flight (posts, top and middle bar) with its fence collider."""
    slope = math.atan2(rise, run)
    ln = math.hypot(run, rise)
    if axis == "y":
        rx, mid = x + side * (w / 2 + 0.05), (x + side * (w / 2 + 0.05), y + sign * run / 2, z0 + rise / 2)
    else:
        rx, mid = None, (x + sign * run / 2, y + side * (w / 2 + 0.05), z0 + rise / 2)
    for t in (0.05, 0.5, 0.95):
        d = run * t * sign
        px, py = (rx, y + d) if axis == "y" else (x + d, mid[1])
        cube(body, (0.05, 0.05, 1.0), (px, py, z0 + rise * t + 0.5), "M_Metal")
    rot = (slope * sign, 0, 0) if axis == "y" else (0, -slope * sign, 0)
    for zoff, th in ((1.0, 0.06), (0.5, 0.04)):
        size = (th, ln, th) if axis == "y" else (ln, th, th)
        cube(body, size, (mid[0], mid[1], mid[2] + zoff), "M_Metal", rot=rot)
    fence = max(0.2, (run - math.sin(slope)) / math.cos(slope))
    a.collider((0.08, fence, 1.0) if axis == "y" else (fence, 0.08, 1.0), (mid[0], mid[1], mid[2] + 0.5), rot=rot)


def _landing_rails(body, a, layout, landing, w):
    """Flat railing on the open edges of a landing (the flights' ends stay open)."""
    x0, x1, y0, y1, z = landing
    o = 0.05
    if layout == "landing":
        runs = [((x0 - o, y0), (x0 - o, y1)), ((x1 + o, y0), (x1 + o, y1))]
    elif layout == "quarter":
        runs = [((x0 - o, y0), (x0 - o, y1 + o)), ((x0 - o, y1 + o), (x1, y1 + o))]
    else:
        runs = [((x0 - o, y0), (x0 - o, y1 + o)), ((x0 - o, y1 + o), (x1 + o, y1 + o)),
                ((x1 + o, y0), (x1 + o, y1 + o))]
    for start, end in runs:
        size, center = rail_run(body, start, end, 1.0, z0=z)
        a.collider(size, center)


def _wall_trims(m, length, along_x=True, dh=0.0, dt=0.0):
    """Base and top trims of the wall module (same sizes as ``wall``; ``dh`` / ``dt``: height / thickness - 3 / 0.5)."""
    for size, z in (((length, 0.56 + dt, 0.25), 0.125), ((length, 0.60 + dt, 0.15), 2.95 + dh)):
        cube(m, size if along_x else (size[1], size[0], size[2]), (0, 0, z), "M_RobotDark", bevel=0.01)


@model("stairs", "Stairs", "environment", "Stairs or ramp climbing towards the back (+Y), optional rails and glow edges",
       params=[
           Param("style", "choice", "Bauform", choices=("stairs", "ramp")),
           Param("width", "float", "Breite (m)", lo=0.6, hi=4.0, size=True),
           Param("rise", "float", "Höhe (m)", lo=0.4, hi=3.0, size=True),
           Param("rails", "choice", "Geländer", choices=("none", "left", "both")),
           Param("glow_edges", "bool", "Glow-Kanten"),
           Param("stripes", "bool", "Warnstreifen unten"),
           Param("layout", "choice", "Lauf", choices=STAIR_LAYOUTS, default="straight", quiet=True,
                 description="gerade, mit Zwischenpodest (landing), mit Vierteldrehung (quarter) oder "
                             "gegenläufig mit Wendepodest (switchback); Podeste immer Treppenbreite tief"),
       ], set_faces=("x-", "x+", "y+", "z-", "z+"), set_pins=("style", "rails", "layout"))  # front: stripes vary
def stairs(rng, a):
    p = a.p
    style = p.choice("style", ["stairs", "stairs", "ramp"])
    w = p.float("width", 1.0, 2.0)
    rise = p.float("rise", 1.0, 3.0)
    mat = p.material(["M_Metal", "M_Wall", "M_Platform"])
    glow = p.glow()
    layout = p.option("layout")
    if layout != "straight":
        _stairs_layout(rng, a, p, layout, w, rise, mat, glow)
        return
    body = a.part("Body")
    steps = max(2, int(round(rise / 0.2)))
    run = steps * 0.3 if style == "stairs" else rise * 2.2
    a.meta.update({"style": style, "run_m": round(run, 3), "steps": steps if style == "stairs" else 0})
    edges = p.bool("glow_edges", 0.4)
    lights = a.part("Glow") if edges else None
    if style == "stairs":
        sh, sd = rise / steps, run / steps
        for i in range(steps):
            h = sh * (i + 1)
            y = -run / 2 + sd * (i + 0.5)
            cube(body, (w, sd, h), (0, y, h / 2), "M_RobotDark" if i % 2 else mat)
            a.collider((w, sd, h), (0, y, h / 2))  # solid steps (step height ~0.2 m: CharacterController steps up)
            cube(body, (w + 0.02, sd * 0.25, 0.02), (0, y - sd * 0.375, h + 0.01), "M_Metal")  # nosing
            if edges:
                cube(lights, (w * 0.8, 0.02, 0.02), (0, y - sd / 2 - 0.01, h - 0.03), glow)
    else:
        body.add(prism([(-run / 2, 0.0), (run / 2, 0.0), (run / 2, rise)], w, mat), basis=YZ_TO_X)
        slope_colliders(a, w, run, rise, layer=0.2 if p.style.generation >= 3 else 0.5)
        slope = math.atan2(rise, run)
        for i in range(int(run / 0.4)):  # anti-slip bars on the slope
            t = (i + 0.5) * 0.4 / run
            cube(body, (w * 0.9, 0.05, 0.03), (0, -run / 2 + run * t, rise * t + 0.01), "M_RobotDark",
                 rot=(slope, 0, 0))
        if edges:
            for s in (-1, 1):
                ln = math.hypot(run, rise)
                cube(lights, (0.03, ln * 0.9, 0.02), (s * (w / 2 - 0.05), 0, rise / 2 + 0.012), glow, rot=(slope, 0, 0))
    rails = p.choice("rails", ["none", "left", "both"])
    if rails != "none":
        slope = math.atan2(rise, run)
        ln = math.hypot(run, rise)
        for s in ((-1,) if rails == "left" else (-1, 1)):
            x = s * (w / 2 + 0.05)
            for t in (0.05, 0.5, 0.95):
                y, z = -run / 2 + run * t, rise * t
                cube(body, (0.05, 0.05, 1.0), (x, y, z + 0.5), "M_Metal")
            cube(body, (0.06, ln, 0.06), (x, 0, rise / 2 + 1.0), "M_Metal", rot=(slope, 0, 0))
            cube(body, (0.04, ln, 0.04), (x, 0, rise / 2 + 0.5), "M_Metal", rot=(slope, 0, 0))
            # railing as a fence; shortened so the tilted box ends where the rails end
            fence = max(0.2, (run - math.sin(slope)) / math.cos(slope))
            a.collider((0.08, fence, 1.0), (x, 0, rise / 2 + 0.5), rot=(slope, 0, 0))
    if p.bool("stripes", 0.3, warning=True):
        stripes(body, w * 0.9, (0, -run / 2 - 0.005, 0.06), count=max(3, int(w * 3)), width=0.01, height=0.1)


@model("ladder", "Ladder", "environment", "Ladder with wall brackets at the back (+Y), optional safety cage",
       params=[
           Param("height", "float", "Höhe (m)", lo=1.0, hi=6.0, size=True),
           Param("width", "float", "Breite (m)", lo=0.3, hi=1.0),
           Param("cage", "bool", "Rückenschutz"),
           Param("hoops", "bool", "Haltebügel oben"),
       ])
def ladder(rng, a):
    p = a.p
    h = p.float("height", 2.0, 4.0)
    w = p.float("width", 0.45, 0.6)
    mat = p.material(["M_Metal", "M_Metal", "M_HazardOrange", "M_Warning"])
    body = a.part("Body")
    for x in (-w / 2, w / 2):
        cube(body, (0.05, 0.06, h), (x, 0, h / 2), mat)
        cube(body, (0.12, 0.06, 0.04), (x, 0, 0.02), "M_RobotDark")  # foot
    n = max(2, int((h - 0.2) / 0.3))
    for i in range(n):
        cyl(body, 0.02, w, (0, 0, 0.3 + i * (h - 0.3) / n), "M_Metal", sides=6, rot=ALONG_X)
    for z in [0.5 + k * 1.5 for k in range(int((h - 0.3) / 1.5) + 1)]:  # wall brackets
        for x in (-w / 2, w / 2):
            cube(body, (0.04, 0.2, 0.04), (x, 0.13, min(z, h - 0.1)), "M_RobotDark")
    if p.bool("hoops", 0.5):  # grab bars sticking up over the top
        for x in (-w / 2, w / 2):
            cube(body, (0.05, 0.06, 0.9), (x, 0, h + 0.45), mat)
        cube(body, (w + 0.05, 0.06, 0.05), (0, 0, h + 0.9), mat)
    cage = p.bool("cage", 0.4, enabled=h > 2.4)
    if cage:
        r = w / 2 + 0.25
        for z in [2.2 + k * 0.9 for k in range(int((h - 2.2) / 0.9) + 1)]:
            for i in range(7):  # half hoop (front half), made of short segments
                ang = math.pi + math.pi * i / 6
                ang2 = math.pi + math.pi * (i + 1) / 6
                mx, my = (math.cos(ang) + math.cos(ang2)) / 2 * r, (math.sin(ang) + math.sin(ang2)) / 2 * r
                if i < 6:
                    cube(body, (math.pi * r / 6 * 1.05, 0.04, 0.04), (mx, my - 0.05, z), mat,
                         rot=(0, 0, (ang + ang2) / 2 + math.pi / 2))
        for i in range(5):  # vertical bars of the cage
            ang = math.pi + math.pi * (i + 1) / 6
            cube(body, (0.03, 0.03, h - 2.2), (math.cos(ang) * r, math.sin(ang) * r - 0.05, 2.2 + (h - 2.2) / 2), mat)
    a.meta.update({"rungs": n, "cage": cage})


CATWALK_SHAPES = ("straight", "corner", "tee", "cross", "landing", "end")
# arms of the shapes: directions in which the walkway leaves the centre (connectors at +-length/2)
CATWALK_ARMS = {"straight": ((-1, 0), (1, 0)), "corner": ((-1, 0), (0, 1)), "tee": ((-1, 0), (1, 0), (0, 1)),
                "cross": ((-1, 0), (1, 0), (0, 1), (0, -1)), "landing": ((-1, 0), (1, 0)), "end": ((-1, 0),)}


@model("catwalk", "Catwalk", "environment", "Catwalk / bridge segment (walkable top at z = 0): grating, rails, "
       "glow edges, optional supports; L, T, cross, landing and end pieces", pivot="top", params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("width", "choice", "Breite (m)", choices=(1.0, 2.0)),
           Param("rails", "choice", "Geländer", choices=("both", "one", "none")),
           Param("supports", "float", "Stützen-Länge (m, 0 = keine)", lo=0.0, hi=4.0),
           Param("glow", "bool", "Glow-Kanten"),
           Param("shape", "choice", "Form", choices=CATWALK_SHAPES, default="straight", quiet=True,
                 description="L-Stück (corner), T-Stück, Kreuz, Podest (landing) oder Endstück mit "
                             "Abschlussgeländer; Anschlüsse immer bei +-Länge/2"),
           Param("rail_height", "float", "Geländerhöhe (m)", lo=0.8, hi=1.4, default=1.0, quiet=True),
           dressing_param("ruin: durchhängende und abgerissene Kabel unter dem Steg; organic: Ranken über die "
                          "Kanten, Moos"),
       ], set_faces=("x-", "x+", "z+"), set_pins=("rails", "shape"))  # joins at the ends; supports below vary
def catwalk(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0, 4.0])
    width = p.choice("width", [1.0, 1.0, 2.0])
    deck = a.part("Deck")
    frame = p.material(["M_RobotDark", "M_Metal", "M_HazardOrange"])
    a.meta.update({"length_m": length, "width_m": width})
    shape, rail_h = p.option("shape"), p.option("rail_height")
    if shape != "straight" or rail_h != 1.0:
        _catwalk_shape(rng, a, p, shape, length, width, frame, rail_h)
        if shape in ("straight", "end"):
            dress_catwalk(a, deck, length, width, p.option("dressing"))
        return
    for s in (-1, 1):  # side beams
        cube(deck, (length, 0.08, 0.2), (0, s * (width / 2 - 0.04), -0.1), frame, bevel=0.01)
    for x in (-length / 2 + 0.04, length / 2 - 0.04):
        cube(deck, (0.08, width - 0.16, 0.16), (x, 0, -0.08), frame)
    n = int(length / 0.12)
    for i in range(n):  # grating bars across
        cube(deck, (0.04, width - 0.16, 0.04), (-length / 2 + 0.1 + i * (length - 0.2) / (n - 1), 0, -0.03),
             "M_Metal")
    for y in (-width / 4, width / 4):
        cube(deck, (length - 0.16, 0.03, 0.08), (0, y, -0.1), "M_Metal")
    a.collider((length, width, 0.2), (0, 0, -0.1), part="Deck")  # deck only - no hull over rails and supports
    if p.bool("glow", 0.5):
        glow = p.glow()
        lights = a.part("Glow")
        for s in (-1, 1):
            cube(lights, (length * 0.9, 0.02, 0.04), (0, s * (width / 2 + 0.01), -0.08), glow)
    rails = p.choice("rails", ["both", "both", "one", "none"])
    if rails != "none":
        r = a.part("Rail")
        for s in ((-1, 1) if rails == "both" else (1,)):
            rail(r, length - 0.1, True, s * (width / 2 - 0.04))
            a.collider((length - 0.1, 0.08, 1.03), (0, s * (width / 2 - 0.04), 0.515), part="Rail")
    sup = p.value("supports", rng.choice([0.0, 0.0, rng.uniform(1.0, 3.0)]))
    if sup > 0.05:
        for x in (-length / 2 + 0.3, length / 2 - 0.3):
            for s in (-1, 1):
                cube(deck, (0.1, 0.1, sup), (x, s * (width / 2 - 0.1), -0.2 - sup / 2), "M_RobotDark")
                a.collider((0.1, 0.1, sup), (x, s * (width / 2 - 0.1), -0.2 - sup / 2), part="Deck")
            cube(deck, (0.08, width - 0.2, 0.08), (x, 0, -0.2 - sup * 0.6), "M_RobotDark")
        a.meta["supports_m"] = round(sup, 3)
    dress_catwalk(a, deck, length, width, p.option("dressing"))


def _catwalk_segments(shape, length, width):
    """Deck rectangles (x0, x1, y0, y1) of a catwalk shape, the hub first."""
    hw, hl = width / 2, length / 2
    if shape == "landing":
        return [(-hl, hl, -hl, hl)]
    if shape in ("straight", "end"):
        return [(-hl, hl, -hw, hw)]
    rects = [(-hw, hw, -hw, hw)]
    for dx, dy in CATWALK_ARMS[shape]:
        if hl - hw < 1e-6:
            continue
        if dx:
            rects.append((-hl, -hw, -hw, hw) if dx < 0 else (hw, hl, -hw, hw))
        else:
            rects.append((-hw, hw, -hl, -hw) if dy < 0 else (-hw, hw, hw, hl))
    return rects


def _catwalk_rail_lines(shape, length, width):
    """Rail runs ((x0, y0), (x1, y1)) along the outer edges, leaving every connector open."""
    hw, hl, inset = width / 2, length / 2, 0.04
    if shape == "landing":  # square: closed at front/back, gaps of the walkway width on the sides
        lines = [((-hl, -hl + inset), (hl, -hl + inset)), ((-hl, hl - inset), (hl, hl - inset))]
        for x in (-hl + inset, hl - inset):
            lines += [((x, -hl), (x, -hw)), ((x, hw), (x, hl))]
        return [ln for ln in lines if abs(ln[1][0] - ln[0][0]) + abs(ln[1][1] - ln[0][1]) > 0.05]
    if shape in ("straight", "end"):
        lines = [((-hl + 0.05, s * (hw - inset)), (hl - 0.05, s * (hw - inset))) for s in (-1, 1)]
        if shape == "end":  # closing rail across the far end
            lines.append(((hl - inset, -hw + 0.05), (hl - inset, hw - 0.05)))
        return lines
    arms = set(CATWALK_ARMS[shape])
    lines = []
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        if (dx, dy) in arms:  # both sides of the arm, from the hub to the connector
            if dx:
                xa, xb = (-hl + 0.05, -hw) if dx < 0 else (hw, hl - 0.05)
                lines += [((xa, s * (hw - inset)), (xb, s * (hw - inset))) for s in (-1, 1)]
            else:
                ya, yb = (-hl + 0.05, -hw) if dy < 0 else (hw, hl - 0.05)
                lines += [((s * (hw - inset), ya), (s * (hw - inset), yb)) for s in (-1, 1)]
        else:  # closed side of the hub
            if dx:
                lines.append(((dx * (hw - inset), -hw), (dx * (hw - inset), hw)))
            else:
                lines.append(((-hw, dy * (hw - inset)), (hw, dy * (hw - inset))))
    return [ln for ln in lines if abs(ln[1][0] - ln[0][0]) + abs(ln[1][1] - ln[0][1]) > 0.05]


def rail_run(m, start, end, height=1.0, material="M_Metal", z0=0.0, bevel=0.01):
    """Railing between two points at floor height z0 (axis-aligned): posts about every metre, top and
    middle bar. Returns size and centre of its fence collider."""
    (x0, y0), (x1, y1) = start, end
    along_x = abs(x1 - x0) >= abs(y1 - y0)
    ln = abs(x1 - x0) if along_x else abs(y1 - y0)
    posts = max(2, int(round(ln)) + 1)
    for i in range(posts):
        t = i / (posts - 1)
        cube(m, (0.07, 0.07, height), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + height / 2), material,
             bevel=bevel)
    for z in (height, height * 0.5):
        size = (ln, 0.06, 0.06) if along_x else (0.06, ln, 0.06)
        cube(m, size, ((x0 + x1) / 2, (y0 + y1) / 2, z0 + z), material, bevel=bevel)
    return ((ln, 0.08, height + 0.03) if along_x else (0.08, ln, height + 0.03)), \
        ((x0 + x1) / 2, (y0 + y1) / 2, z0 + (height + 0.03) / 2)


def _catwalk_shape(rng, a, p, shape, length, width, frame, rail_h):
    """Catwalk shapes beyond the straight segment (same rolls as the straight one, so materials match)."""
    deck = a.part("Deck")
    rects = _catwalk_segments(shape, length, width)
    for x0, x1, y0, y1 in rects:
        sx, sy = x1 - x0, y1 - y0
        along_x = sx >= sy
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for s in (-1, 1):  # edge beams along the long sides
            if along_x:
                cube(deck, (sx, 0.08, 0.2), (cx, cy + s * (sy / 2 - 0.04), -0.1), frame, bevel=0.01)
            else:
                cube(deck, (0.08, sy, 0.2), (cx + s * (sx / 2 - 0.04), cy, -0.1), frame, bevel=0.01)
        n = max(2, int((sx if along_x else sy) / 0.12))
        for i in range(n):  # grating bars across
            f = -0.5 + (i + 0.5) / n
            if along_x:
                cube(deck, (0.04, sy - 0.16, 0.04), (cx + f * (sx - 0.1), cy, -0.03), "M_Metal")
            else:
                cube(deck, (sx - 0.16, 0.04, 0.04), (cx, cy + f * (sy - 0.1), -0.03), "M_Metal")
        a.collider((sx, sy, 0.2), (cx, cy, -0.1), part="Deck")
    a.meta["shape"] = shape
    if p.bool("glow", 0.5):
        glow = p.glow()
        lights = a.part("Glow")
        for (x0, y0), (x1, y1) in _catwalk_rail_lines(shape, length, width):
            along_x = abs(x1 - x0) >= abs(y1 - y0)
            size = (abs(x1 - x0) * 0.9, 0.02, 0.04) if along_x else (0.02, abs(y1 - y0) * 0.9, 0.04)
            off = (0, 0.05 if y0 > 0 else -0.05) if along_x else (0.05 if x0 > 0 else -0.05, 0)
            cube(lights, size, ((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], -0.08), glow)
    rails = p.choice("rails", ["both", "both", "one", "none"])
    if rails != "none":  # shapes: rails on every open edge ("one" counts as both)
        r = a.part("Rail")
        for start, end in _catwalk_rail_lines(shape, length, width):
            size, center = rail_run(r, start, end, rail_h, bevel=0 if p.style.generation >= 3 else .01)
            a.collider(size, center, part="Rail")
    sup = p.value("supports", rng.choice([0.0, 0.0, rng.uniform(1.0, 3.0)]))
    if sup > 0.05:
        x0, x1, y0, y1 = rects[0]
        for x in (x0 + 0.3, x1 - 0.3):
            for y in (y0 + 0.1, y1 - 0.1):
                cube(deck, (0.1, 0.1, sup), (x, y, -0.2 - sup / 2), "M_RobotDark")
                a.collider((0.1, 0.1, sup), (x, y, -0.2 - sup / 2), part="Deck")
        a.meta["supports_m"] = round(sup, 3)


@model("floor_tile", "FloorTile", "environment", "Floor tile on the 1 m grid (top at z = 0): grating, plate, "
       "hatch or vent, optional glow", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 4.0)),
           Param("style", "choice", "Art", choices=("grate", "plate", "hatch", "vent")),
           Param("glow", "bool", "Glow-Linien"),
           Param("stripes", "bool", "Warnstreifen"),
           Param("depth", "float", "Stärke (m)", lo=0.05, hi=0.4),
           dressing_param("ruin: Schutt und eine lose Platte; organic: Moospolster, Steine, Büsche"),
       ], set_faces=("x-", "x+", "y-", "y+", "z-"))  # joins on four sides; details may stand on top
def floor_tile(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 2.0, 2.0, 4.0])
    style = p.choice("style", ["grate", "plate", "hatch", "vent"])
    m = a.part("Deck")
    mat = p.material(["M_Platform", "M_Metal", "M_Ground"])
    a.meta.update({"size_m": size, "style": style})
    depth = p.value("depth", 0.1 + rng.uniform(0.0, 0.1))
    a.collider((size, size, depth), (0, 0, -depth / 2), part="Deck")
    if style == "hatch" and p.style.generation >= 3:
        cube(m, (size, size, depth), (0, 0, -depth / 2), mat, bevel=.02)
        hatch = min(1.1, size - .2)
        # Centre the access cover. Surrounding panels show the scale of large tiles.
        span = (size - hatch - .12) / 2
        if span > .08:
            for side in (-1, 1):
                cube(m, (span, size - .08, .01), (side * (hatch / 2 + .04 + span / 2), 0, .005), "M_Wall")
                cube(m, (hatch + .08, span, .01), (0, side * (hatch / 2 + .04 + span / 2), .005), "M_Wall")
        cube(m, (hatch + .08, hatch + .08, .02), (0, 0, .01), "M_RobotDark")
        cube(m, (hatch, hatch, .02), (0, 0, .025), mat, bevel=.01)
        for side in (-1, 1):
            cube(m, (.12, .04, .035), (side * hatch * .35, hatch * .43, .04), "M_Metal")
        cube(m, (.24, .045, .025), (0, -hatch * .32, .0475), "M_RobotDark")
        a.meta["hatch_center"] = [0, 0]
    elif style == "grate":
        for s in (-1, 1):
            cube(m, (size, 0.06, depth), (0, s * (size / 2 - 0.03), -depth / 2), "M_RobotDark")
            cube(m, (0.06, size - 0.12, depth), (s * (size / 2 - 0.03), 0, -depth / 2), "M_RobotDark")
        n = int(size / 0.1)
        for i in range(n - 1):
            cube(m, (0.03, size - 0.12, depth * 0.8), (-size / 2 + (i + 1) * size / n, 0, -depth * 0.4), "M_Metal")
        cube(m, (size - 0.12, size - 0.12, 0.02), (0, 0, -depth + 0.01), "M_Ground")  # dark pit below
    else:
        cube(m, (size, size, depth), (0, 0, -depth / 2), mat, bevel=0.02)
        for i in range(int(size)):  # panel seams every metre
            for j in range(int(size)):
                cx, cy = -size / 2 + 0.5 + i, -size / 2 + 0.5 + j
                if style == "plate":
                    cube(m, (0.9, 0.9, 0.01), (cx, cy, 0.0), "M_Wall" if mat != "M_Wall" else "M_Metal")
                elif style == "hatch" and i == 0 and j == 0:
                    cube(m, (0.8, 0.8, 0.02), (cx, cy, 0.0), "M_HazardOrange", bevel=0.005)
                    cube(m, (0.3, 0.06, 0.04), (cx, cy - 0.25, 0.02), "M_RobotDark")
                elif style == "vent":
                    for k in range(5):
                        cube(m, (0.7, 0.05, 0.02), (cx, cy - 0.3 + k * 0.15, 0.0), "M_RobotDark")
    if p.bool("glow", 0.35):
        glow = p.glow()
        lights = a.part("Glow")
        for s in (-1, 1):
            cube(lights, (size * 0.9, 0.03, 0.02), (0, s * (size / 2 - 0.02), 0.0), glow)
    if p.bool("stripes", 0.25, warning=True):
        stripes(m, size * 0.9, (0, -size / 2 + 0.1, 0.006), count=int(size * 3), width=0.1)
    dress_floor(a, m, size, p.option("dressing"))


@model("ceiling_panel", "CeilingPanel", "environment", "Ceiling panel (hangs at mount height): light panel, "
       "fan (Rotor) or plain plate", pivot="wall", view="below", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 4.0)),
           Param("style", "choice", "Art", choices=("light", "fan", "plain")),
           Param("mount_height", "float", "Deckenhöhe (m)", lo=2.0, hi=6.0, default=3.0),
           Param("fan_speed", "float", "Lüfter-Tempo (°/s)", lo=0, hi=2000, unity=True, default=200,
                 description="Nur mit Lüfter"),
           Param("thickness", "float", "Stärke (m)", lo=0.04, hi=0.3),
       ], set_faces=("x-", "x+", "y-", "y+", "z+"))  # joins on four sides at the ceiling; lights hang below
def ceiling_panel(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 2.0, 2.0, 4.0])
    style = p.choice("style", ["light", "light", "fan", "plain"])
    z = p.value("mount_height", 3.0)
    t = p.value("thickness", rng.uniform(0.08, 0.14))
    body = a.part("Body")
    a.meta.update({"size_m": size, "style": style})
    cube(body, (size, size, t), (0, 0, z - t / 2), p.styled("M_Wall", ["M_Wall", "M_Metal", "M_Platform"]), bevel=0.02)
    if style == "light":
        glow = p.glow(weights=(0.8, 0.05, 0.15))
        lights = a.part("Glow")
        n = 1 if size < 2 else int(size)
        for i in range(n):
            x = -size / 2 + size * (i + 0.5) / n
            cube(body, (size / n * 0.7, size * 0.7, 0.04), (x, 0, z - t - 0.02), "M_RobotDark")
            cube(lights, (size / n * 0.6, size * 0.6, 0.02), (x, 0, z - t - 0.05), glow)
        a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Steady"})
    elif style == "fan":
        r = size * 0.38
        cyl(body, r * 1.1, 0.08, (0, 0, z - t - 0.04), "M_RobotDark", sides=12)
        for i in range(4):
            cube(body, (r * 2.2, 0.03, 0.03), (0, 0, z - t - 0.1), "M_Metal", rot=(0, 0, math.pi / 4 * i))
        center = (0.0, 0.0, z - t - 0.16)
        fan(a.part("Rotor", pivot=center), center, r, rng.choice([3, 4, 5]), "M_Metal")
        a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": p.option("fan_speed")})
    else:
        for i in range(int(size)):
            for j in range(int(size)):
                cube(body, (0.85, 0.85, 0.02), (-size / 2 + 0.5 + i, -size / 2 + 0.5 + j, z - t - 0.01), "M_Ground")


@model("wall_corner", "WallCorner", "environment", "Corner, end or T piece for the wall module (3 m high, 0.5 m "
       "thick unless set)", params=[
           Param("style", "choice", "Art", choices=("corner", "end", "tee")),
           Param("pipe", "bool", "Rohr an der Ecke"),
           Param("guard", "bool", "Kantenschutz (Warnfarbe)"),
           Param("glow", "bool", "Glow-Linie"),
           Param("height", "float", "Wandhöhe (m)", lo=2.0, hi=6.0, default=3.0, quiet=True),
           Param("thickness", "float", "Wandstärke (m)", lo=0.2, hi=1.0, default=0.5, quiet=True),
       ], set_faces=("x+", "y+", "z-", "z+"), set_pins=("style",))  # walls join right/back; pipe, guard outside
def wall_corner(rng, a):
    p = a.p
    style = p.choice("style", ["corner", "end", "tee"])
    dh, dt = p.option("height") - 3.0, p.option("thickness") - 0.5  # 0.0 for the standard module: bit for bit
    m = a.part("Wall")
    cube(m, (0.5 + dt, 0.5 + dt, 3.0 + dh), (0, 0, 1.5 + dh / 2), p.styled("M_Wall", ["M_Wall", "M_Metal"]),
         bevel=0.03)
    cube(m, (0.56 + dt, 0.56 + dt, 0.25), (0, 0, 0.125), "M_RobotDark", bevel=0.01)
    cube(m, (0.6 + dt, 0.6 + dt, 0.15), (0, 0, 2.95 + dh), "M_RobotDark", bevel=0.01)
    # exposed faces: corner -> front (-Y) and left (-X); end -> front, back, left; tee -> front
    faces = {"corner": ("front", "left"), "end": ("front", "back", "left"), "tee": ("front",)}[style]
    a.meta["style"] = style
    out = 0.285 + dt / 2  # glow strips just proud of the faces
    if p.bool("glow", 0.7):
        glow = p.glow()
        lights = a.part("Glow")
        for f in faces:
            if f in ("front", "back"):
                cube(lights, (0.5 + dt, 0.02, 0.05), (0, (-1 if f == "front" else 1) * out, 2.45 + dh), glow)
            else:
                cube(lights, (0.02, 0.5 + dt, 0.05), (-out, 0, 2.45 + dh), glow)
    edge = -0.25 - dt / 2
    if p.bool("guard", 0.4, warning=True) and style != "tee":
        cube(m, (0.08, 0.08, 2.6 + dh), (edge, edge, 1.55 + dh / 2), "M_Warning", rot=(0, 0, math.pi / 4))
    if p.bool("pipe", 0.4):
        x = -0.36 - dt / 2 if style != "tee" else 0.0
        cyl(m, 0.06, 2.75 + dh, (x, -0.36 - dt / 2, 1.5 + dh / 2), "M_Metal", sides=8)
        for z in (0.6, 2.4 + dh):
            cube(m, (0.1, 0.14, 0.06), (x, -0.3 - dt / 2, z), "M_RobotDark")
        a.meta["pipe"] = True


@model("window_wall", "WindowWall", "environment", "Wall module 2 or 4 m with windows (Glass): single, split or band",
       params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("windows", "choice", "Fenster", choices=("single", "split", "band")),
           Param("sill", "float", "Brüstung (m)", lo=0.2, hi=2.0),
           Param("glow", "bool", "Glow-Linie"),
           Param("height", "float", "Wandhöhe (m)", lo=2.0, hi=6.0, default=3.0, quiet=True),
           Param("thickness", "float", "Wandstärke (m)", lo=0.2, hi=1.0, default=0.5, quiet=True),
       ])
def window_wall(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0, 4.0])
    kind = p.choice("windows", ["single", "split", "band"])
    sill = p.float("sill", 0.7, 1.1)
    h, t = p.option("height"), p.option("thickness")
    dh, dt = h - 3.0, t - 0.5  # 0.0 for the standard module: bit for bit
    if sill > h - 0.8:
        raise ValueError(f"window_wall: sill {sill} m leaves no window in a {h} m wall (at most {h - 0.8:.2f} m)")
    top = min(max(rng.uniform(2.2, 2.5) + dh, sill + 0.4), h - 0.3)  # window top follows the wall height
    m, glass = a.part("Wall"), a.part("Glass")
    mat = p.styled("M_Wall", ["M_Wall", "M_Metal"])
    a.meta.update({"length_m": length, "windows": kind})
    cube(m, (length, t, sill), (0, 0, sill / 2), mat, bevel=0.03)
    cube(m, (length, t, h - top), (0, 0, top + (h - top) / 2), mat, bevel=0.03)
    _wall_trims(m, length, dh=dh, dt=dt)
    if kind == "band":
        openings = [(-length / 2 + 0.2, length / 2 - 0.2)]
    else:
        openings = [(-length / 2 + i * 2 + 0.3, -length / 2 + i * 2 + 1.7) for i in range(int(length // 2))]
    edges = [-length / 2] + [e for o in openings for e in o] + [length / 2]
    for x0, x1 in zip(edges[0::2], edges[1::2]):  # solid posts between the openings
        if x1 - x0 > 1e-6:
            cube(m, (x1 - x0, t, top - sill), ((x0 + x1) / 2, 0, (sill + top) / 2), mat)
    oh = top - sill
    face = t / 2
    for x0, x1 in openings:
        cx, ow = (x0 + x1) / 2, x1 - x0
        for s in (-1, 1):  # dark frame around the opening, front and back
            cube(m, (ow + 0.1, 0.06, 0.06), (cx, s * face, sill), "M_RobotDark")
            cube(m, (ow + 0.1, 0.06, 0.06), (cx, s * face, top), "M_RobotDark")
            for x in (x0, x1):
                cube(m, (0.06, 0.06, oh), (x, s * face, (sill + top) / 2), "M_RobotDark")
        cube(m, (ow + 0.1, 0.34, 0.06), (cx, -0.08 - dt / 2, sill + 0.03), "M_Metal")  # sill
        cube(glass, (ow, 0.04, oh), (cx, 0, (sill + top) / 2), "M_Glass")
        mullions = 1 if kind == "split" else (int(ow / 1.0) if kind == "band" else 0)
        for k in range(mullions):
            x = x0 + ow * (k + 1) / (mullions + 1)
            cube(m, (0.06, 0.1, oh), (x, 0, (sill + top) / 2), "M_RobotDark")
    if p.bool("glow", 0.5):
        glow = p.glow()
        lights = a.part("Glow")
        for y in (-0.285 - dt / 2, 0.285 + dt / 2):
            cube(lights, (length - 0.4, 0.02, 0.05), (0, y, min(top + 0.2, h - 0.2)), glow)


@model("cable_tray", "CableTray", "environment", "Wall cable tray / conduit (2 or 4 m along X) with cable bundle",
       pivot="wall", params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0)),
           Param("mount_height", "float", "Höhe über Boden (m)", lo=0.3, hi=3.0),
           Param("style", "choice", "Art", choices=("tray", "conduit")),
           Param("cables", "int", "Kabel", lo=1, hi=10),
       ])
def cable_tray(rng, a):
    p = a.p
    length = p.choice("length", [2.0, 4.0])
    z = p.value("mount_height", rng.uniform(1.8, 2.7))
    style = p.choice("style", ["tray", "tray", "conduit"])
    n = p.int("cables", 3, 6)
    m = a.part("Body")
    w = rng.uniform(0.2, 0.35)
    z = max(z, 0.15)
    yc = 0.1 - 0.05 - w / 2
    a.meta.update({"length_m": length, "style": style})
    for x in [-length / 2 + 0.25 + i * 1.0 for i in range(int(length))]:  # wall brackets
        cube(m, (0.04, w + 0.08, 0.04), (x, 0.06 - (w + 0.08) / 2, z - 0.06), "M_RobotDark")
        cube(m, (0.04, 0.03, 0.18), (x, 0.085, z - 0.0), "M_RobotDark")
    if style == "tray":  # open U channel
        cube(m, (length, w, 0.02), (0, yc, z - 0.03), "M_Metal")
        for s in (-1, 1):
            cube(m, (length, 0.02, 0.1), (0, yc + s * w / 2, z + 0.01), "M_Metal")
        mats = ["M_RobotDark", "M_RobotDark", "M_HazardOrange", "M_Warning", "M_Wall"]
        for i in range(n):  # cables lying in the tray
            r = rng.uniform(0.015, 0.03)
            col, row = i % 4, i // 4
            cyl(m, r, length, (0, yc - w / 2 + 0.04 + col * (w - 0.08) / 3, z - 0.02 + r + row * 0.05),
                rng.choice(mats), sides=6, rot=ALONG_X)
    else:  # closed conduits
        for i in range(min(n, 4)):
            r = rng.uniform(0.03, 0.05)
            y = 0.1 - r - 0.02 - i * (w / 4)
            cyl(m, r, length, (0, y, z), "M_Metal" if i % 2 == 0 else "M_Wall", sides=8, rot=ALONG_X)
            for x in (-length / 2 + 0.1, length / 2 - 0.1):
                cyl(m, r * 1.3, 0.06, (x, y, z), "M_RobotDark", sides=8, rot=ALONG_X)


@model("lift", "Lift", "environment", "Lift platform: moving Deck between two columns "
       "(Door script moves it up)", params=[
           Param("size", "float", "Plattform (m)", lo=1.0, hi=3.0, size=True),
           Param("travel", "float", "Hub (m)", lo=0.5, hi=4.0, unity=True),
           Param("speed", "float", "Tempo (m/s)", lo=0.1, hi=5.0, unity=True, default=1.0),
           Param("rail", "bool", "Geländer auf der Plattform"),
       ])
def lift(rng, a):
    p = a.p
    s = p.float("size", 1.4, 2.4)
    travel = p.value("travel", round(rng.uniform(1.5, 3.0) * 2) / 2)
    frame_mat = p.material(["M_RobotDark", "M_Metal", "M_HazardOrange"])
    col_h = travel + 0.6
    cube(a.part("Base"), (s + 0.2, s + 0.2, 0.12), (0, 0, 0.06), "M_RobotDark", bevel=0.02)
    a.collider((s + 0.2, s + 0.2, 0.12), (0, 0, 0.06), part="Base")
    for side, x in (("Left", -(s / 2 + 0.15)), ("Right", s / 2 + 0.15)):
        f = a.part(f"Frame_{side}")
        cube(f, (0.25, 0.3, col_h), (x, s * 0.3, col_h / 2), frame_mat, bevel=0.02)
        a.collider((0.25, 0.3, col_h), (x, s * 0.3, col_h / 2), part=f"Frame_{side}")
        cube(f, (0.06, 0.32, col_h - 0.4), (x - math.copysign(0.12, x), s * 0.3, col_h / 2), "M_Warning")
    top = a.part("Frame_Top")
    cube(top, (s + 0.55, 0.3, 0.2), (0, s * 0.3, col_h + 0.1), frame_mat, bevel=0.02)
    a.collider((s + 0.55, 0.3, 0.2), (0, s * 0.3, col_h + 0.1), part="Frame_Top")
    for side, y in (("Front", s * 0.3 - 0.16), ("Back", s * 0.3 + 0.16)):
        cube(a.part(f"StatusLight_{side}"), (0.4, 0.02, 0.08), (0, y, col_h + 0.1), "M_GlowRed")
    center = (0.0, 0.0, 0.2)
    deck = a.part("Deck", pivot=center)
    cube(deck, (s, s, 0.14), (0, 0, 0.19), p.material(["M_Platform", "M_Metal"]), bevel=0.02)
    a.collider((s, s, 0.14), (0, 0, 0.19), part="Deck")  # moves with the deck
    stripes(deck, s * 0.9, (0, -s / 2 + 0.08, 0.265), count=6, width=0.1)
    for x in (-s / 2 - 0.02, s / 2 + 0.02):  # guide shoes running in the columns
        cube(deck, (0.08, 0.2, 0.1), (x, s * 0.3, 0.19), "M_RobotDark")
    if p.bool("rail", 0.5):
        for x in (-s / 2 + 0.04, s / 2 - 0.04):
            for y in (-s / 2 + 0.04, s / 2 - 0.3):
                cube(deck, (0.05, 0.05, 0.9), (x, y, 0.26 + 0.45), "M_Metal")
            cube(deck, (0.05, s - 0.3, 0.05), (x, -0.13, 0.26 + 0.9), "M_Metal")
            a.collider((0.06, s - 0.25, 0.92), (x, -0.13, 0.26 + 0.46), part="Deck")
    a.meta["travel_m"] = travel
    a.behaviour("Door", {"panels": ["Deck"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Base"]},
                {"openOffset": [0.0, round(travel, 4), 0.0], "speed": p.option("speed")},
                note="lift: 'open' = Deck up by travel (Unity Y); same mover as a vertical door")


@model("conveyor", "Conveyor", "industrial", "Conveyor along X: roller track or belt with end drums "
       "(Roller_<n>, Rotator)", params=[
           Param("style", "choice", "Art", choices=("rollers", "belt")),
           Param("length", "float", "Länge (m)", lo=0.8, hi=4.0, size=True),
           Param("width", "float", "Breite (m)", lo=0.4, hi=1.5, size=True),
           Param("height", "float", "Höhe (m)", lo=0.3, hi=1.2),
           Param("speed", "float", "Rollen-Tempo (°/s)", lo=0, hi=1000, unity=True, default=180),
       ])
def conveyor(rng, a):
    p = a.p
    style = p.choice("style", ["rollers", "belt"])
    length = p.float("length", 1.5, 3.0)
    w = p.float("width", 0.6, 1.0)
    h = p.float("height", 0.6, 0.9)
    frame = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    body = a.part("Body")
    a.meta["style"] = style
    for s in (-1, 1):
        cube(body, (length, 0.06, 0.16), (0, s * (w / 2 + 0.03), h - 0.02), frame, bevel=0.01)
    for x in (-length / 2 + 0.1, length / 2 - 0.1) + ((0.0,) if length > 2.5 else ()):
        for s in (-1, 1):
            cube(body, (0.06, 0.06, h - 0.1), (x, s * (w / 2 + 0.03), (h - 0.1) / 2), "M_RobotDark")
        cube(body, (0.05, w, 0.05), (x, 0, h * 0.3), "M_RobotDark")
    stripes(body, length * 0.9, (0, -w / 2 - 0.065, h - 0.02), count=int(length * 3), width=0.01, height=0.08)
    r = 0.045 if style == "rollers" else 0.08
    if style == "rollers":
        n = max(3, int(length / 0.18))
        xs = [-length / 2 + 0.1 + i * (length - 0.2) / (n - 1) for i in range(n)]
    else:
        xs = [-length / 2 + r + 0.02, length / 2 - r - 0.02]
        belt = a.part("Belt")
        cube(belt, (length - 0.04, w - 0.04, 0.02), (0, 0, h + 0.01), "M_Ground")
        cube(belt, (length - 2 * r - 0.04, w - 0.04, 0.02), (0, 0, h - 2 * r + 0.01), "M_Ground")
    for i, x in enumerate(xs):
        center = (x, 0.0, h - r + 0.01) if style == "belt" else (x, 0.0, h - 0.01)
        roller = a.part(f"Roller_{i + 1}", pivot=center)
        cyl(roller, r, w - 0.02 if style == "rollers" else w - 0.06, center, "M_Metal", sides=8, rot=ALONG_Y)
        cube(roller, (r * 0.5, w * 0.6, r * 2.05), center, "M_RobotDark")  # makes the turning visible
        a.behaviour("Rotator", {"target": f"Roller_{i + 1}"}, {"axis": "forward", "speed": p.option("speed")})
    a.meta["rollers"] = len(xs)


@model("pad", "Pad", "environment", "Jump pad (arrows, glow) or teleporter pad (floating ring, Rotor)", params=[
    Param("kind", "choice", "Art", choices=("jump", "teleport")),
    Param("radius", "float", "Radius (m)", lo=0.4, hi=2.0, size=True, snap_factor=2),
    Param("mode", "choice", "SignalLight-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Pulse"),
    Param("speed", "float", "Ring-Tempo (°/s)", lo=0, hi=720, unity=True, default=90,
          description="Nur Teleporter"),
])
def pad(rng, a):
    p = a.p
    kind = p.choice("kind", ["jump", "teleport"])
    r = p.float("radius", 0.6, 1.2)
    glow = p.glow(weights=(0.7, 0.05, 0.25))
    body, lights = a.part("Body"), a.part("Glow")
    sides = 10
    a.meta["kind"] = kind
    cyl(body, r * 1.15, 0.12, (0, 0, 0.06), "M_RobotDark", sides=sides, bevel=0.02)
    cyl(body, r, 0.06, (0, 0, 0.15), p.material(["M_Platform", "M_Metal", "M_Wall"]), sides=sides, bevel=0.01)
    cyl(lights, r * 1.05, 0.04, (0, 0, 0.12), glow, sides=sides)
    if kind == "jump":
        cyl(lights, r * 0.35, 0.03, (0, 0, 0.19), glow, sides=sides)
        for i in range(4):  # chevrons pointing outwards
            ang = math.pi / 2 * i
            for k in (0.55, 0.75):
                for s in (-1, 1):
                    cube(body, (r * 0.18, 0.04, 0.02), (math.cos(ang) * r * k - math.sin(ang) * s * r * 0.06,
                                                        math.sin(ang) * r * k + math.cos(ang) * s * r * 0.06, 0.185),
                         "M_Warning", rot=(0, 0, ang - s * deg(40)))  # V pointing outwards
        a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})
    else:
        for i in range(3):  # pylons that carry the ring
            ang = 2 * math.pi * i / 3 + math.pi / 2
            cube(body, (0.12, 0.12, 1.4), (math.cos(ang) * r * 1.05, math.sin(ang) * r * 1.05, 0.7 + 0.1),
                 "M_RobotDark", bevel=0.02)
        center = (0.0, 0.0, 1.6)
        ring = a.part("Rotor", pivot=center)
        n = 12
        for i in range(n):
            ang = 2 * math.pi * i / n
            mat = "M_Accent" if i % 3 == 0 else "M_Metal"
            cube(ring, (2 * math.pi * r * 0.95 / n * 1.05, 0.08, 0.08),
                 (math.cos(ang) * r * 0.95, math.sin(ang) * r * 0.95, 1.6), mat, rot=(0, 0, ang + math.pi / 2))
        a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})
        a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": p.option("speed")})
