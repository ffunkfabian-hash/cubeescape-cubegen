"""More puzzle mechanics: buttons, gear trains, a laser splitter, force fields, cable plugs, scanners and safes.

Like :mod:`puzzle`, everything is wired to the game's existing scripts. New
moving parts (pivot on their axis / hinge):

* ``Button`` / ``Button_<n>`` - pushed about 1.5 cm towards the wall
* ``Gear_<n>`` - gears of a gear train (``Rotator``, ratios follow the radii)
* ``Prism`` - turning beam splitter with the empties ``Beam_A`` / ``Beam_B``
* ``Field`` - the barrier of a force field (``Door`` retracts it into the floor)
* ``Plug`` - loose cable with its plug, ``Slot_<n>`` = the sockets
* ``Scan`` - scanner surface (``SignalLight``)
* safe: ``Panel`` (door) with the dial ``Wheel`` as its child
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import ALONG_Y, add_vec, cube, cyl, deg, gear, rotated, stripes, strut
from .registry import model

STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}


def _status_param():
    return Param("status", "choice", "Glow-Startzustand", choices=("off", "on"), default="off",
                 description="Status-Glow beim Export: off = M_GlowRed, on = M_GlowCyan (Unity schaltet ihn um)")


def _indicator(a, note=""):
    a.behaviour("SignalIndicator", {"renderers": ["Glow"]}, {"offMaterial": "M_GlowRed", "onMaterial": "M_GlowCyan"},
                note=note)


def _mount(p, rng, lo, hi, half_height):
    """Mount height of a wall piece: rolled, overridable, never below the floor."""
    return max(p.value("mount_height", rng.uniform(lo, hi)), half_height + 0.05)


# --------------------------------------------------------------------------
# buttons
# --------------------------------------------------------------------------

@model("button", "Button", "puzzle", "Wall push button: big button, emergency stop or a row of buttons "
       "(Button / Button_<n> move in), status glow", pivot="wall", params=[
           Param("style", "choice", "Bauform", choices=("push", "emergency", "row")),
           Param("count", "int", "Knöpfe (Reihe)", lo=2, hi=6),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.5, hi=2.5),
           Param("guard", "bool", "Schutzbügel"),
           Param("stripes", "bool", "Warnrahmen"),
           _status_param(),
       ])
def button(rng, a):
    p = a.p
    style = p.choice("style", ["push", "push", "emergency", "row"])
    body, glow = a.part("Body"), a.part("Glow")
    status = STATUS[p.option("status")]
    mat = p.material(["M_RobotDark", "M_Wall", "M_Metal"])
    a.meta["style"] = style
    d = 0.06
    yf = 0.1 - d
    if style == "row":
        n = p.int("count", 2, 4)
        bw = rng.uniform(0.08, 0.12)
        gap = bw * 0.6
        w, h = n * (bw + gap) + gap, bw * 2.8
        z = _mount(p, rng, 1.0, 1.4, h / 2)
        cube(body, (w, d, h), (0, 0.1 - d / 2, z), mat, bevel=0.012)
        caps = ["M_Platform", "M_Warning", "M_HazardOrange", "M_RobotBody"]
        for i in range(n):
            x = -w / 2 + gap + bw / 2 + i * (bw + gap)
            cube(body, (bw + 0.02, 0.02, bw + 0.02), (x, yf - 0.01, z - h * 0.12), "M_RobotDark")
            center = (x, yf - 0.035, z - h * 0.12)
            cube(a.part(f"Button_{i + 1}", pivot=center), (bw, 0.04, bw), center, rng.choice(caps), bevel=0.008)
            cube(a.part("Lights"), (bw * 0.5, 0.02, 0.03), (x, yf - 0.01, z + h * 0.3),
                 rng.choice(["M_GlowCyan", "M_GlowOrange", "M_GlowRed"]))
        cube(glow, (w * 0.7, 0.02, 0.03), (0, yf - 0.01, z - h * 0.42), status)
        a.meta["buttons"] = n
        note = "Button_<n> move ~1.5 cm towards the wall (Unity -Z) when pressed"
    else:
        s = rng.uniform(0.22, 0.34)
        w = h = s
        z = _mount(p, rng, 1.0, 1.4, h / 2)
        if style == "push":
            cube(body, (w, d, h), (0, 0.1 - d / 2, z), mat, bevel=0.015)
            cube(body, (s * 0.72, 0.03, s * 0.72), (0, yf - 0.012, z), "M_RobotDark", bevel=0.008)
            center = (0.0, yf - 0.04, z)
            cube(a.part("Button", pivot=center), (s * 0.55, 0.05, s * 0.55), center,
                 rng.choice(["M_HazardOrange", "M_Platform", "M_Warning"]), bevel=0.012)
            for sx in (-1, 1):  # status glow frame around the button
                cube(glow, (0.02, 0.02, s * 0.66), (sx * s * 0.33, yf - 0.03, z), status)
                cube(glow, (s * 0.66, 0.02, 0.02), (0, yf - 0.03, z + sx * s * 0.33), status)
        else:  # emergency stop: yellow plate, collar, red mushroom
            cube(body, (w, d, h), (0, 0.1 - d / 2, z), "M_Warning", bevel=0.015)
            cyl(body, s * 0.3, 0.05, (0, yf - 0.02, z), "M_RobotDark", sides=10, rot=ALONG_Y)
            center = (0.0, yf - 0.07, z)
            knob = a.part("Button", pivot=center)
            cyl(knob, s * 0.12, 0.06, (0, yf - 0.05, z), "M_RobotDark", sides=8, rot=ALONG_Y)
            cyl(knob, s * 0.26, 0.05, (0, yf - 0.1, z), "M_GlowRed", sides=10, bevel=0.012, rot=ALONG_Y)
            cube(glow, (0.04, 0.02, 0.04), (s * 0.38, yf - 0.01, z + s * 0.38), status)
        if p.bool("guard", 0.4):  # U-shaped guard in front against accidental pushes
            for sx in (-1, 1):
                cube(body, (0.025, 0.14, 0.025), (sx * s * 0.42, yf - 0.07, z + s * 0.4), "M_Metal")
            cube(body, (s * 0.86, 0.025, 0.025), (0, yf - 0.14, z + s * 0.4), "M_Metal")
        note = "Button moves ~1.5 cm towards the wall (Unity -Z) when pressed"
    if p.bool("stripes", 0.35, warning=True):
        stripes(body, w * 0.9, (0, yf - 0.005, z - h / 2 + 0.025), count=max(3, int(w * 12)), width=0.01,
                height=0.03)
    _indicator(a, note=note)


# --------------------------------------------------------------------------
# gear train
# --------------------------------------------------------------------------

@model("gear_puzzle", "GearPuzzle", "puzzle", "Wall gear train: 2-5 meshing gears (Gear_<n>, Rotator), "
       "optionally one missing (Slot)", pivot="wall", params=[
           Param("gears", "int", "Zahnräder", lo=2, hi=5),
           Param("missing", "bool", "Ein Zahnrad fehlt (Slot)"),
           Param("crank", "bool", "Kurbel am ersten Rad"),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.6, hi=2.5),
           Param("speed", "float", "Tempo erstes Rad (°/s)", lo=0, hi=720, unity=True, default=60),
           _status_param(),
       ])
def gear_puzzle(rng, a):
    p = a.p
    n = p.int("gears", 3, 4)
    radii = [rng.uniform(0.1, 0.24) for _ in range(n)]
    tooth = [min(0.05, r * 0.25) for r in radii]
    centers = [(0.0, 0.0)]
    for i in range(1, n):  # chain: each gear meshes with the previous one
        dist = radii[i - 1] + radii[i] + (tooth[i - 1] + tooth[i]) * 0.3
        ang = deg(rng.uniform(-35, 35))
        px, pz = centers[-1]
        centers.append((px + math.cos(ang) * dist, pz + math.sin(ang) * dist))
    xs = [c[0] for c in centers]
    zs = [c[1] for c in centers]
    margin = max(radii) + 0.12
    x_mid, z_mid = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    w = max(xs) - min(xs) + 2 * margin
    h = max(zs) - min(zs) + 2 * margin + 0.12
    z = _mount(p, rng, 1.1, 1.5, h / 2)
    body, glow = a.part("Body"), a.part("Glow")
    status = STATUS[p.option("status")]
    cube(body, (w, 0.06, h), (0, 0.07, z), p.material(["M_RobotDark", "M_Wall", "M_Metal"]), bevel=0.02)
    for sx in (-1, 1):
        for sz in (-1, 1):
            cyl(body, 0.02, 0.02, (sx * (w / 2 - 0.05), 0.035, z + sz * (h / 2 - 0.05)), "M_Metal", sides=6,
                rot=ALONG_Y)
    missing = p.bool("missing", 0.6) and n > 2
    gap = rng.randint(1, n - 2) if missing else -1
    mats = ["M_Metal", "M_HazardOrange", "M_Warning", "M_Platform"]
    base = p.option("speed")
    phase = 0.0
    for i, ((cx, cz), r) in enumerate(zip(centers, radii)):
        center = (cx - x_mid, -0.01, z + cz - z_mid)
        cyl(body, 0.03, 0.1, add_vec(center, (0, 0.04, 0)), "M_RobotDark", sides=8, rot=ALONG_Y)  # axle
        if i == gap:  # empty axle: the spare gear goes here
            cyl(body, r * 0.32, 0.02, add_vec(center, (0, 0.035, 0)), "M_Ground", sides=10, rot=ALONG_Y)
            a.empty("Slot", center)
            a.meta["missing_gear"] = {"index": i + 1, "radius": round(r, 3)}
            continue
        part = a.part(f"Gear_{i + 1}", pivot=center)
        teeth = gear(part, center, r, 0.05, rng.choice(mats), phase=phase)
        phase = math.pi / teeth  # next gear half a tooth on, so the teeth interlock
        if i == 0 and p.bool("crank", 0.4):
            arm = (center[0] + r * 0.7, center[1] - 0.05, center[2])
            cube(part, (r * 0.75, 0.03, 0.05), (center[0] + r * 0.35, center[1] - 0.05, center[2]), "M_RobotDark")
            cyl(part, 0.025, 0.12, add_vec(arm, (0, -0.06, 0)), "M_HazardOrange", sides=6, rot=ALONG_Y)
        speed = round(base * radii[0] / r * (1 if i % 2 == 0 else -1), 2)
        a.behaviour("Rotator", {"target": f"Gear_{i + 1}"}, {"axis": "forward", "speed": speed},
                    note="disabled until the gear train is complete; speeds follow the gear ratios")
    cube(glow, (0.12, 0.02, 0.04), (w / 2 - 0.12, 0.035, z + h / 2 - 0.06), status)
    a.meta["gears"] = n
    _indicator(a, note="Slot = axle of the missing gear (spare_part kind gear with about this radius)" if missing
               else "")


# --------------------------------------------------------------------------
# laser splitter
# --------------------------------------------------------------------------

@model("laser_splitter", "LaserSplitter", "puzzle", "Turnable crystal prism that splits a laser beam in two "
       "(Prism, Rotatable; Beam_A / Beam_B)", params=[
           Param("height", "float", "Prismenmitte (m)", lo=0.3, hi=2.0, size=True),
           Param("step", "choice", "Schritt (°)", choices=(45, 90), unity=True),
           Param("target", "int", "Ziel-Stellung", lo=0, hi=7, unity=True, default=0),
       ])
def laser_splitter(rng, a):
    p = a.p
    h = p.float("height", 0.8, 1.2)
    body, glow = a.part("Body"), a.part("Glow")
    light = p.glow()
    cyl(body, 0.3, 0.1, (0, 0, 0.05), "M_RobotDark", sides=8, bevel=0.02)
    cyl(glow, 0.31, 0.02, (0, 0, 0.09), light, sides=8)
    center = (0.0, 0.0, 0.1)
    turn = a.part("Prism", pivot=center)
    cyl(turn, 0.22, 0.06, (0, 0, 0.13), "M_Metal", sides=8)
    cyl(turn, 0.04, h - 0.3, (0, 0, 0.16 + (h - 0.3) / 2), "M_RobotDark", sides=6)
    size = rng.uniform(0.16, 0.24)
    ph = size * rng.uniform(1.4, 2.0)
    tri = [(math.cos(deg(90 + 120 * k)) * size, math.sin(deg(90 + 120 * k)) * size) for k in range(3)]
    turn.add(prism(tri, ph, "M_Crystal"), loc=(0, 0, h))
    for dz in (-ph / 2 - 0.02, ph / 2 + 0.02):  # metal caps holding the crystal
        cyl(turn, size * 0.75, 0.04, (0, 0, h + dz), "M_Metal", sides=6)
    cube(turn, (0.04, 0.04, 0.06), (0, -size * 0.6, h - ph / 2 - 0.06), "M_Warning")  # orientation mark
    a.empty("Beam_A", (0.0, -size - 0.05, h), parent="Prism")
    a.empty("Beam_B", (-size - 0.05, 0.0, h), parent="Prism")
    a.behaviour("Rotatable", {"target": "Prism", "glow": "Glow"},
                {"axis": "up", "step": p.choice("step", [45, 90]), "speed": 180, "target": p.option("target"),
                 "interactive": True},
                note="rest: Beam_A continues to Unity forward, Beam_B splits off to Unity right; both turn with "
                     "the prism")


# --------------------------------------------------------------------------
# force field
# --------------------------------------------------------------------------

@model("force_field", "ForceField", "puzzle", "Energy barrier between two emitter posts: field or laser fence "
       "(Field, Door retracts it into the floor)", params=[
           Param("style", "choice", "Art", choices=("field", "lasers")),
           Param("width", "float", "Öffnung Breite (m)", lo=0.8, hi=5.0, size=True),
           Param("height", "float", "Öffnung Höhe (m)", lo=1.2, hi=4.0, size=True),
           Param("speed", "float", "Tempo (m/s)", lo=0.1, hi=20.0, unity=True, default=6.0),
       ])
def force_field(rng, a):
    p = a.p
    style = p.choice("style", ["field", "field", "lasers"])
    width = round(p.float("width", 1.6, 3.0) * 5) / 5
    height = round(p.float("height", 2.2, 3.0) * 5) / 5
    post, depth = rng.uniform(0.3, 0.45), rng.uniform(0.4, 0.6)
    frame = p.material(["M_RobotDark", "M_Wall", "M_Metal"])
    light = p.glow_from(["M_GlowCyan", "M_GlowCyan", "M_GlowRed"]) if style == "field" else "M_GlowRed"
    a.meta.update({"style": style, "opening_m": [width, height]})
    for side, x in (("Left", -(width + post) / 2), ("Right", (width + post) / 2)):
        m = a.part(f"Frame_{side}")
        cube(m, (post, depth, height + 0.3), (x, 0, (height + 0.3) / 2), frame, bevel=0.03)
        cube(m, (post + 0.08, depth + 0.08, 0.2), (x, 0, 0.1), "M_RobotDark", bevel=0.01)
        inner = x - math.copysign(post / 2, x)
        cube(m, (0.04, depth * 0.4, height * 0.9), (inner, 0, height * 0.48), light)  # emitter strip
        for k in range(3):
            cube(m, (0.03, depth + 0.02, 0.06), (x, 0, height * (0.25 + 0.25 * k)), "M_Warning")
    top = a.part("Frame_Top")
    cube(top, (width, depth * 0.8, 0.3), (0, 0, height + 0.15), frame, bevel=0.03)
    for side, y in (("Front", -(depth * 0.4 + 0.01)), ("Back", depth * 0.4 + 0.01)):
        cube(a.part(f"StatusLight_{side}"), (min(1.0, width * 0.5), 0.02, 0.08), (0, y, height + 0.15), "M_GlowRed")
    sill = rng.random() < 0.6
    if sill:
        cube(a.part("Base"), (width, depth * 0.6, 0.06), (0, 0, 0.03), "M_RobotDark")
    center = (0.0, 0.0, height / 2)
    field = a.part("Field", pivot=center)
    if style == "field":
        cube(field, (width, 0.04, height - 0.04), center, "M_Crystal")
    else:
        n = max(3, int(height / 0.35))
        for i in range(n):
            cyl(field, 0.018, width, (0, 0, 0.25 + i * (height - 0.4) / (n - 1)), "M_GlowRed", sides=6,
                rot=(0, math.pi / 2, 0))
    a.behaviour("Door", {"panels": ["Field"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "upperFrame": ["Frame_Top"], "colliders": ["Frame_Left", "Frame_Right", "Frame_Top"]},
                {"openOffset": [0.0, -round(height + 0.1, 4), 0.0], "speed": p.option("speed")},
                note="'open' = the field drops into the floor; give Field a BoxCollider from its bounds")


# --------------------------------------------------------------------------
# cable plug board
# --------------------------------------------------------------------------

PLUG_COLOURS = ["M_GlowCyan", "M_GlowRed", "M_GlowOrange", "M_Warning", "M_Platform", "M_HazardOrange"]


@model("cable_plug", "CablePlug", "puzzle", "Wall plug board: coloured sockets (Slot_<n>) and a loose cable with "
       "a plug (Plug)", pivot="wall", params=[
           Param("sockets", "int", "Buchsen", lo=1, hi=6),
           Param("cable_length", "float", "Kabellänge (m)", lo=0.2, hi=1.5),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.8, hi=2.5),
           _status_param(),
       ])
def cable_plug(rng, a):
    p = a.p
    n = p.int("sockets", 2, 4)
    w = max(0.4, n * 0.16 + 0.12)
    h = rng.uniform(0.45, 0.6)
    d = 0.1
    length = p.float("cable_length", 0.4, 0.9)
    z = _mount(p, rng, 1.2, 1.5, h / 2)
    z = max(z, h / 2 + length + 0.2)  # the hanging plug stays above the floor
    yf = 0.1 - d
    body, lights, glow = a.part("Body"), a.part("Lights"), a.part("Glow")
    status = STATUS[p.option("status")]
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_Wall", "M_RobotDark", "M_Metal"]), bevel=0.02)
    cube(body, (w - 0.06, 0.02, h * 0.45), (0, yf - 0.005, z + h * 0.08), "M_RobotDark")
    colours = rng.sample(PLUG_COLOURS, n)
    for i, colour in enumerate(colours):
        x = -w / 2 + 0.08 + 0.08 + i * (w - 0.32) / max(1, n - 1) if n > 1 else 0.0
        zc = z + h * 0.08
        cyl(lights, 0.05, 0.02, (x, yf - 0.02, zc), colour, sides=8, rot=ALONG_Y)
        cyl(body, 0.03, 0.03, (x, yf - 0.025, zc), "M_Ground", sides=8, rot=ALONG_Y)
        a.empty(f"Slot_{i + 1}", (x, yf - 0.06, zc))
    cube(glow, (w * 0.4, 0.02, 0.03), (0, yf - 0.01, z + h / 2 - 0.05), status)
    # cable outlet bottom left, the cable sags down to the plug
    ox = -w / 2 + 0.1
    cyl(body, 0.045, 0.06, (ox, yf - 0.02, z - h / 2 + 0.06), "M_RobotDark", sides=8, rot=ALONG_Y)
    start = (ox, yf - 0.05, z - h / 2 + 0.06)
    sway = rng.uniform(-0.15, 0.15)
    steps = 6
    pts = [start]
    for k in range(1, steps + 1):
        t = k / steps
        pts.append((ox + sway * math.sin(t * math.pi * 0.8), yf - 0.05 - 0.04 * math.sin(t * math.pi),
                    start[2] - length * t))
    end = pts[-1]
    plug = a.part("Plug", pivot=end)
    target = rng.randrange(n)
    for q0, q1 in zip(pts, pts[1:]):
        strut(plug, q0, q1, 0.018, "M_RobotDark")
    head = (end[0], end[1], end[2] - 0.07)
    strut(plug, end, head, 0.035, "M_RobotDark", sides=8)
    cyl(plug, 0.04, 0.03, (end[0], end[1], end[2] - 0.075), colours[target], sides=8)  # colour band
    for dx in (-0.012, 0.012):
        cube(plug, (0.008, 0.008, 0.04), (end[0] + dx, end[1], end[2] - 0.11), "M_Metal")
    a.meta.update({"sockets": n, "plug_colour": colours[target], "target_slot": target + 1})
    _indicator(a, note="Plug = loose cable end; target_slot (meta) has the matching colour")


# --------------------------------------------------------------------------
# scanner
# --------------------------------------------------------------------------

@model("scanner", "Scanner", "puzzle", "Wall scanner: hand, retina or card swipe (Scan, SignalLight), status glow",
       pivot="wall", params=[
           Param("kind", "choice", "Art", choices=("hand", "retina", "card")),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.6, hi=2.5),
           Param("screen", "bool", "Bildschirm"),
           Param("mode", "choice", "Scan-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Pulse"),
           _status_param(),
       ])
def scanner(rng, a):
    p = a.p
    kind = p.choice("kind", ["hand", "retina", "card"])
    w, h, d = rng.uniform(0.3, 0.42), rng.uniform(0.45, 0.65), rng.uniform(0.08, 0.14)
    z = _mount(p, rng, 1.2, 1.5, h / 2)
    yf = 0.1 - d
    body, glow, scan = a.part("Body"), a.part("Glow"), a.part("Scan")
    status = STATUS[p.option("status")]
    light = p.glow(weights=(0.75, 0.1, 0.15))
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_RobotDark", "M_Wall", "M_Metal"]), bevel=0.02)
    a.meta["kind"] = kind
    if kind == "hand":  # tilted palm pad with a scan grid
        tilt = (deg(-25), 0.0, 0.0)
        pc = (0.0, yf - 0.05, z - h * 0.12)
        cube(body, (w * 0.85, 0.12, h * 0.5), pc, "M_RobotDark", bevel=0.015, rot=tilt)
        for i in range(4):
            cube(scan, (w * 0.7, 0.012, 0.012), add_vec(pc, rotated(tilt, (0, -0.062, -h * 0.18 + i * h * 0.12))),
                 light, rot=tilt)
        for i in range(5):  # finger guides
            guide = add_vec(pc, rotated(tilt, (-w * 0.28 + i * w * 0.14, -0.064, h * 0.1)))
            cube(body, (0.015, 0.014, h * 0.2), guide, "M_Metal", rot=tilt)
    elif kind == "retina":  # eyepiece with a rubber hood
        ec = (0.0, yf, z - h * 0.05)
        cyl(body, 0.08, 0.14, add_vec(ec, (0, -0.06, 0)), "M_RobotDark", sides=10, rot=ALONG_Y)
        cyl(body, 0.095, 0.05, add_vec(ec, (0, -0.14, 0)), "M_Ground", sides=10, rot=ALONG_Y)
        cyl(scan, 0.05, 0.02, add_vec(ec, (0, -0.172, 0)), light, sides=10, rot=ALONG_Y)
    else:  # card swipe: slot rail and a scan strip
        cube(body, (0.08, 0.06, h * 0.5), (w * 0.2, yf - 0.03, z - h * 0.05), "M_Metal", bevel=0.01)
        cube(body, (0.015, 0.065, h * 0.46), (w * 0.2, yf - 0.035, z - h * 0.05), "M_Ground")
        cube(scan, (0.02, 0.02, h * 0.4), (w * 0.2 - 0.055, yf - 0.01, z - h * 0.05), light)
    if p.bool("screen", 0.5):
        cube(a.part("Screen"), (w * 0.7, 0.02, h * 0.16), (0, yf - 0.01, z + h * 0.32), light)
    cube(glow, (0.05, 0.02, 0.05), (-w * 0.35, yf - 0.01, z + h * 0.42), status)
    a.behaviour("SignalLight", {"glow": "Scan"}, {"mode": p.option("mode")}, note="scan surface")
    _indicator(a)


# --------------------------------------------------------------------------
# safe
# --------------------------------------------------------------------------

@model("safe", "Safe", "puzzle", "Floor safe: hinged door (Panel) with a dial (Wheel, child of Panel) or keypad, "
       "item slot inside", params=[
           Param("lock", "choice", "Schloss", choices=("dial", "keypad")),
           Param("height", "float", "Höhe (m)", lo=0.4, hi=1.8, size=True),
           Param("door_angle", "float", "Tür-Winkel offen (°)", lo=30, hi=180, unity=True, default=100),
           Param("code", "int", "Ziel-Ziffer am Rad (0-9)", lo=0, hi=9, unity=True, default=7),
           _status_param(),
       ])
def safe(rng, a):
    p = a.p
    lock = p.choice("lock", ["dial", "dial", "keypad"])
    h = p.float("height", 0.6, 1.2)
    w = rng.uniform(0.5, 0.9)
    d = rng.uniform(0.5, 0.75)
    t = 0.08
    feet = 0.06
    mat = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    status = STATUS[p.option("status")]
    body = a.part("Body")
    z0, z1 = feet, feet + h
    zc = (z0 + z1) / 2
    a.meta["lock"] = lock
    for x in (-w / 2 + 0.06, w / 2 - 0.06):
        for y in (-d / 2 + 0.06, d / 2 - 0.06):
            cube(body, (0.08, 0.08, feet), (x, y, feet / 2), "M_Ground")
    yb = -d / 2 + 0.1  # front of the box body (the door sits in front of it)
    depth = d / 2 - yb
    cube(body, (w, t, h), (0, d / 2 - t / 2, zc), mat, bevel=0.02)                   # back
    for sx in (-1, 1):
        cube(body, (t, depth, h), (sx * (w / 2 - t / 2), (yb + d / 2) / 2, zc), mat, bevel=0.02)
    for zz in (z0 + t / 2, z1 - t / 2):
        cube(body, (w, depth, t), (0, (yb + d / 2) / 2, zz), mat, bevel=0.02)
    cube(body, (w - 2 * t, 0.02, h - 2 * t), (0, d / 2 - t - 0.01, zc), "M_Ground")  # dark inside
    cube(body, (w - 2 * t - 0.02, depth - t - 0.04, 0.03), (0, (yb + d / 2 - t) / 2, zc - h * 0.1), "M_Metal")  # shelf
    a.empty("Slot", (0.0, (yb + d / 2 - t) / 2, zc - h * 0.1 + 0.06))
    hinge = (-w / 2, yb - 0.05, zc)
    door = a.part("Panel", pivot=hinge)
    cube(door, (w, 0.1, h), (0, yb - 0.05, zc), mat, bevel=0.025)
    cube(door, (w * 0.8, 0.02, h * 0.8), (0, yb - 0.105, zc), "M_RobotDark" if mat != "M_RobotDark" else "M_Wall")
    for dz in (-h * 0.32, h * 0.32):
        cyl(body, 0.03, 0.12, (-w / 2 - 0.02, yb - 0.05, zc + dz), "M_Metal", sides=6)
    yf = yb - 0.115
    handle_c = (w * 0.18, yf - 0.02, zc - h * 0.12)
    cyl(door, 0.04, 0.05, handle_c, "M_Metal", sides=8, rot=ALONG_Y)
    for k in range(3):  # three-spoke handle
        ang = deg(90 + 120 * k)
        cube(door, (0.025, 0.025, 0.14), add_vec(handle_c, (math.cos(ang) * 0.07, -0.02, math.sin(ang) * 0.07)),
             "M_Metal", rot=(0, math.pi / 2 - ang, 0))
    cube(a.part("Glow", parent="Panel"), (0.04, 0.02, 0.04), (w * 0.38, yf, zc + h * 0.38), status)
    if lock == "dial":
        r = min(0.12, w * 0.16)
        dc = (-w * 0.12, yf - 0.03, zc + h * 0.15)
        cyl(door, r * 1.25, 0.02, add_vec(dc, (0, 0.02, 0)), "M_Metal", sides=10, rot=ALONG_Y)
        for k in range(10):  # tick ring around the dial (digits 0-9)
            ang = math.pi / 2 - 2 * math.pi * k / 10
            cube(door, (0.012, 0.012, 0.03), add_vec(dc, (math.cos(ang) * r * 1.15, 0.005, math.sin(ang) * r * 1.15)),
                 "M_Warning" if k == 0 else "M_RobotDark", rot=(0, math.pi / 2 - ang, 0))
        dial = a.part("Wheel", pivot=dc, parent="Panel")
        cyl(dial, r, 0.04, dc, "M_RobotDark", sides=10, bevel=0.01, rot=ALONG_Y)
        cyl(dial, r * 0.3, 0.05, add_vec(dc, (0, -0.03, 0)), "M_Metal", sides=8, rot=ALONG_Y)
        cube(dial, (0.015, 0.02, r * 0.5), add_vec(dc, (0, -0.025, r * 0.65)), "M_HazardOrange")
        a.behaviour("Rotatable", {"target": "Wheel", "glow": "Glow"},
                    {"axis": "forward", "step": 36, "speed": 180, "target": p.option("code"), "interactive": True},
                    note="dial: 10 positions (36 degrees), target = code digit")
    else:
        cube(a.part("Screen", parent="Panel"), (w * 0.3, 0.02, 0.06), (-w * 0.12, yf, zc + h * 0.3),
             p.glow(weights=(0.8, 0.1, 0.1)))
        for row in range(3):
            for col in range(3):
                cube(door, (0.04, 0.02, 0.03), (-w * 0.12 + (col - 1) * 0.055, yf, zc + h * 0.18 - row * 0.045),
                     "M_Platform")
        _indicator(a)
    a.behaviour("Rotatable", {"target": "Panel", "glow": "Glow"},
                {"axis": "up", "step": p.option("door_angle"), "speed": 90, "target": 1, "interactive": False},
                note="door swings open around its hinge (left, Unity up) once the lock is solved; Slot = loot")
