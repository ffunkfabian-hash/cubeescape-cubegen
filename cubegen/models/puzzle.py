"""Puzzle pieces: receivers for the inventory items, valves, levers, pipe fittings, lasers, plates, keypads.

Everything here is wired to the game's existing scripts (``Rotatable``,
``SignalIndicator``, ``SignalLight``, ``ItemPickup``). Empties named
``Slot`` / ``Slot_<n>`` mark where an inserted item sits (Unity: snap the
item's transform there).

Moving parts have their pivot on the axis: ``Wheel`` (valve wheel), ``Lever``
(handle / knob), ``Fitting`` (rotating pipe piece), ``Mirror``, ``Plate``
(pressure plate), ``Panel`` (hinged fuse box lid).
"""

from __future__ import annotations

import math

from ..geometry import lathe
from ..params import Param
from .common import ALONG_X, ALONG_Y, add_vec, cube, cyl, deg, item_pickup, pickup_params, prerotate, rotated, \
    stripes, sweep_param, sweep_rotator, valve_wheel
from .details import pillar_front, round_base, wall_mount
from .registry import model

STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}


def _status_param():
    return Param("status", "choice", "Glow-Startzustand", choices=("off", "on"), default="off",
                 description="Status-Glow beim Export: off = M_GlowRed, on = M_GlowCyan (Unity schaltet ihn um)")


def _indicator(a, off="M_GlowRed", on="M_GlowCyan", note=""):
    a.behaviour("SignalIndicator", {"renderers": ["Glow"]}, {"offMaterial": off, "onMaterial": on}, note=note)


# --------------------------------------------------------------------------
# receivers for the inventory items
# --------------------------------------------------------------------------

@model("socket", "Socket", "puzzle", "Socket / charging station for an energy cell or battery, status glow, item slot",
       params=[
           Param("kind", "choice", "Für", choices=("energy_cell", "battery")),
           Param("height", "float", "Sockelhöhe (m)", lo=0.3, hi=1.6, size=True),
           Param("cables", "bool", "Kabel zum Boden"),
           Param("stripes", "bool", "Warnstreifen"),
           _status_param(),
       ])
def socket(rng, a):
    p = a.p
    kind = p.choice("kind", ["energy_cell", "battery"])
    h = p.float("height", 0.7, 1.1)
    w = rng.uniform(0.45, 0.7)
    body, lights = a.part("Body"), a.part("Glow")
    status = STATUS[p.option("status")]
    mat = p.material(["M_Wall", "M_RobotDark", "M_Metal"])
    a.meta["kind"] = kind

    cube(body, (w + 0.15, w + 0.15, 0.12), (0, 0, 0.06), "M_RobotDark", bevel=0.02)
    cube(body, (w, w * 0.8, h), (0, 0, 0.12 + h / 2), mat, bevel=0.03)
    top = 0.12 + h
    if kind == "energy_cell":  # upright cradle: ring with a hole look, cell stands in it
        cyl(body, w * 0.32, 0.12, (0, 0, top + 0.06), "M_RobotDark", sides=8, bevel=0.015)
        cyl(body, w * 0.22, 0.02, (0, 0, top + 0.13), "M_Metal", sides=8)
        for i in range(3):  # claws that hold the cell
            ang = 2 * math.pi * i / 3 + math.pi / 6
            cube(body, (0.04, 0.04, 0.22), (math.cos(ang) * w * 0.3, math.sin(ang) * w * 0.3, top + 0.2), "M_Metal")
        cyl(lights, w * 0.33, 0.03, (0, 0, top + 0.015), status, sides=8)
        a.empty("Slot", (0.0, 0.0, top + 0.32))
    else:  # battery tray: a box with an open top
        tw, td = w * 0.85, w * 0.6
        cube(body, (tw, td, 0.06), (0, 0, top + 0.03), "M_RobotDark")
        for s in (-1, 1):
            cube(body, (0.05, td, 0.18), (s * (tw / 2 - 0.025), 0, top + 0.12), "M_RobotDark")
            cube(body, (tw, 0.05, 0.18), (0, s * (td / 2 - 0.025), top + 0.12), "M_RobotDark")
        for x in (-tw * 0.2, tw * 0.2):
            cyl(body, 0.025, 0.04, (x, 0, top + 0.08), "M_HazardOrange", sides=6)
        cube(lights, (tw * 0.6, 0.02, 0.04), (0, -td / 2 - 0.01, top + 0.15), status)
        a.empty("Slot", (0.0, 0.0, top + 0.2))
    cube(lights, (w * 0.4, 0.02, 0.08), (0, -w * 0.4 - 0.01, 0.12 + h * 0.7), status)
    if p.bool("cables", 0.5):
        for x in (-w * 0.3, w * 0.3):
            cyl(body, 0.03, h * 0.8, (x, w * 0.4 + 0.04, 0.12 + h * 0.4), "M_HazardOrange", sides=6)
    if p.bool("stripes", 0.4, warning=True):
        stripes(body, w * 0.8, (0, -w * 0.4 - 0.005, 0.25), count=4, width=0.02, height=0.1)
    _indicator(a, note="Slot marks where the inserted item sits; Glow turns cyan when powered")


@model("fuse_box", "FuseBox", "puzzle", "Wall fuse box: hinged lid (Panel), fuse slots, status glow", pivot="wall",
       params=[
           Param("slots", "int", "Sicherungen", lo=1, hi=6),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.5, hi=2.5),
           Param("lid_angle", "float", "Deckel-Winkel offen (°)", lo=30, hi=180, unity=True, default=110),
           Param("warning", "bool", "Warnschild"),
           _status_param(),
       ])
def fuse_box(rng, a):
    p = a.p
    n = p.int("slots", 2, 4)
    w = max(0.4, 0.14 * n + 0.2)
    h = rng.uniform(0.5, 0.7)
    d = 0.18
    z = p.value("mount_height", rng.uniform(1.1, 1.5))
    z = max(z, h / 2 + 0.05)
    body, lights = a.part("Body"), a.part("Glow")
    status = STATUS[p.option("status")]
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.styled("M_Wall", ["M_Wall", "M_Metal", "M_RobotDark"]), bevel=0.02)
    yf = 0.1 - d
    cube(body, (w - 0.08, 0.02, h - 0.12), (0, yf - 0.005, z), "M_RobotDark")
    for i in range(n):  # fuse holders, the fuse lies across like the item (along X)
        x = -w / 2 + 0.1 + i * (w - 0.2) / max(1, n - 1) if n > 1 else 0.0
        for dz in (-0.08, 0.08):
            cube(body, (0.06, 0.04, 0.03), (x, yf - 0.03, z + dz - 0.03), "M_Metal")
        a.empty(f"Slot_{i + 1}", (x, yf - 0.06, z - 0.03))
        cube(lights, (0.05, 0.02, 0.03), (x, yf - 0.025, z + h / 2 - 0.12), status)
    # lid hinged on the left edge (rotates around Unity up)
    for s in (-1, 1):  # rim around the fuse bay, carries the lid
        cube(body, (0.03, 0.06, h), (s * (w / 2 - 0.015), yf - 0.03, z), "M_RobotDark")
        cube(body, (w, 0.06, 0.03), (0, yf - 0.03, z + s * (h / 2 - 0.015)), "M_RobotDark")
    hinge = (-w / 2, yf - 0.065, z)
    lid = a.part("Panel", pivot=hinge)
    cube(lid, (w, 0.03, h), (0, yf - 0.075, z), p.material(["M_Wall", "M_Metal", "M_Platform"]), bevel=0.01)
    cube(lid, (0.04, 0.03, 0.12), (w / 2 - 0.06, yf - 0.1, z), "M_RobotDark")
    for dz in (-h * 0.35, h * 0.35):
        cyl(body, 0.015, 0.06, (-w / 2, yf - 0.065, z + dz), "M_Metal", sides=6)
    if p.bool("warning", 0.6, warning=True):  # lightning triangle sign on the lid
        cube(lid, (0.16, 0.01, 0.14), (0, yf - 0.095, z + h * 0.15), "M_Warning", rot=(0, deg(45), 0))
        cube(lid, (0.03, 0.012, 0.09), (0, yf - 0.098, z + h * 0.15), "M_RobotDark", rot=(0, deg(25), 0))
    a.meta["slots"] = n
    a.behaviour("Rotatable", {"target": "Panel", "glow": "Glow"},
                {"axis": "up", "step": p.option("lid_angle"), "speed": 180, "target": 1, "interactive": True},
                note="lid swings open around its hinge (Unity up); Slot_<n> = fuse positions")
    _indicator(a)


@model("chip_reader", "ChipReader", "puzzle", "Wall data chip reader: slot, small screen, status glow", pivot="wall",
       params=[
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.5, hi=2.5),
           Param("screen", "bool", "Bildschirm"),
           Param("keys", "bool", "Tasten"),
           _status_param(),
       ])
def chip_reader(rng, a):
    p = a.p
    w, h, d = rng.uniform(0.3, 0.45), rng.uniform(0.4, 0.6), rng.uniform(0.12, 0.18)
    z = p.value("mount_height", rng.uniform(1.1, 1.4))
    z = max(z, h / 2 + 0.05)
    body, lights = a.part("Body"), a.part("Glow")
    status = STATUS[p.option("status")]
    glow = p.glow(weights=(0.85, 0.05, 0.1))
    yf = 0.1 - d
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_RobotDark", "M_Wall"]), bevel=0.02)
    # chip slot: a dark bezel with a thin opening (the chip goes in upright)
    cube(body, (w * 0.7, 0.05, 0.08), (0, yf - 0.02, z - h * 0.15), "M_Metal", bevel=0.01)
    cube(body, (w * 0.5, 0.02, 0.02), (0, yf - 0.05, z - h * 0.15), "M_Ground")
    a.empty("Slot", (0.0, yf - 0.06, z - h * 0.15))
    if p.bool("screen", 0.7):
        cube(a.part("Screen"), (w * 0.75, 0.02, h * 0.28), (0, yf - 0.01, z + h * 0.22), glow)
    if p.bool("keys", 0.5):
        for i in range(3):
            cube(body, (0.05, 0.03, 0.04), (-0.07 + i * 0.07, yf - 0.015, z - h * 0.36), "M_Platform")
    cube(lights, (0.06, 0.02, 0.06), (w * 0.35, yf - 0.01, z - h * 0.15), status)
    _indicator(a, note="Slot marks where the inserted data chip sits")


@model("battery_bank", "BatteryBank", "puzzle", "Rack with battery bays, LED pattern and status glow", params=[
    Param("bays", "int", "Fächer", lo=1, hi=8),
    Param("height", "float", "Höhe (m)", lo=0.6, hi=3.0, size=True),
    Param("filled", "int", "Belegte Fächer (Deko)", lo=0, hi=8),
    _status_param(),
])
def battery_bank(rng, a):
    p = a.p
    n = p.int("bays", 2, 5)
    h = p.float("height", 1.2, 2.0)
    bay_w = rng.uniform(0.32, 0.42)
    w = n * bay_w + 0.1
    d = rng.uniform(0.4, 0.6)
    body, lights, glow = a.part("Body"), a.part("Lights"), a.part("Glow")
    status = STATUS[p.option("status")]
    cube(body, (w, d, h), (0, 0, h / 2), p.styled("M_RobotDark", ["M_RobotDark", "M_Metal", "M_Wall"]), bevel=0.03)
    for z in (0.05, h - 0.05):
        cube(body, (w + 0.04, d + 0.04, 0.1), (0, 0, z), "M_Wall", bevel=0.02)
    bz = h * 0.45
    filled = p.int("filled", 0, n)
    for i in range(n):
        x = -w / 2 + 0.05 + bay_w * (i + 0.5)
        cube(body, (bay_w - 0.06, 0.04, 0.36), (x, -d / 2 - 0.01, bz), "M_Ground")  # bay opening
        a.empty(f"Slot_{i + 1}", (x, -d / 2 + 0.05, bz))
        if i < filled:  # a battery already sits in the bay
            cube(body, (bay_w - 0.12, 0.08, 0.26), (x, -d / 2 - 0.03, bz), "M_Wall", bevel=0.01)
            cube(body, (0.04, 0.09, 0.27), (x - (bay_w - 0.12) / 2, -d / 2 - 0.03, bz), "M_HazardOrange")
        cube(glow, (bay_w - 0.12, 0.02, 0.03), (x, -d / 2 - 0.02, bz + 0.24), status)
        for k in range(rng.randint(1, 3)):
            mat = "M_GlowRed" if rng.random() < 0.2 else "M_GlowCyan"
            cube(lights, (0.04, 0.02, 0.03), (x - bay_w * 0.3 + k * 0.06, -d / 2 - 0.02, bz - 0.25), mat)
    a.meta.update({"bays": n, "filled": min(filled, n)})
    _indicator(a, note="Slot_<n> = battery bays")


@model("keycard", "Keycard", "props", "Inventory item: key card, key fob or mechanical key (pivot in the centre)",
       pivot="center", params=[
           Param("kind", "choice", "Art", choices=("card", "fob", "key")),
           *pickup_params(),
       ])
def keycard(rng, a):
    p = a.p
    kind = p.choice("kind", ["card", "card", "fob", "key"])
    glow = p.glow(weights=(0.6, 0.25, 0.15))
    body, lights = a.part("Body"), a.part("Glow")
    a.meta["kind"] = kind
    if kind == "card":
        w, h = rng.uniform(0.3, 0.38), rng.uniform(0.19, 0.24)
        cube(body, (w, 0.02, h), (0, 0, 0), p.material(["M_Platform", "M_RobotBody", "M_Wall"]), bevel=0.008)
        cube(body, (w, 0.024, h * 0.22), (0, 0, h * 0.28), rng.choice(["M_HazardOrange", "M_Warning", "M_RobotDark"]))
        cube(body, (w * 0.18, 0.026, h * 0.22), (-w * 0.3, 0, -h * 0.12), "M_Metal")  # chip
        cube(lights, (w * 0.4, 0.026, 0.02), (w * 0.12, 0, -h * 0.3), glow)
    elif kind == "fob":
        r = rng.uniform(0.06, 0.09)
        cube(body, (r * 2.2, 0.06, r * 3.2), (0, 0, 0), p.material(["M_RobotDark", "M_Wall"]), bevel=0.02)
        cyl(lights, r * 0.6, 0.065, (0, 0, -r * 0.3), glow, sides=8, rot=ALONG_Y)
        cyl(body, r * 0.5, 0.03, (0, 0, r * 1.9), "M_Metal", sides=8, rot=ALONG_Y)  # ring
    else:
        r = rng.uniform(0.06, 0.08)
        length = rng.uniform(0.25, 0.35)
        cyl(body, r, 0.03, (-length / 2 + r, 0, 0), "M_Metal", sides=8, bevel=0.008, rot=ALONG_Y)
        cube(body, (length - r, 0.025, r * 0.35), (r / 2, 0, 0), "M_Metal")
        for i in range(rng.randint(2, 4)):  # teeth
            cube(body, (0.025, 0.025, r * 0.4), (length / 2 - 0.03 - i * 0.04, 0, -r * 0.3), "M_Metal")
        cyl(lights, r * 0.45, 0.034, (-length / 2 + r, 0, 0), glow, sides=8, rot=ALONG_Y)
    item_pickup(a, ["Body", "Glow"])


# --------------------------------------------------------------------------
# things you turn, pull and push
# --------------------------------------------------------------------------

@model("valve", "Valve", "puzzle", "Wall valve: plate, pipe stub and a valve wheel (Wheel, Rotatable)", pivot="wall",
       params=[
           Param("radius", "float", "Rad-Radius (m)", lo=0.12, hi=0.6, size=True),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.4, hi=2.5),
           Param("pipes", "bool", "Rohre hoch / runter"),
           Param("steps", "int", "Ziel (Anzahl 90°-Schritte)", lo=1, hi=8, unity=True, default=2),
           Param("speed", "float", "Tempo (°/s)", lo=10, hi=1000, unity=True, default=180),
       ])
def valve(rng, a):
    p = a.p
    r = p.float("radius", 0.18, 0.35)
    z = p.value("mount_height", rng.uniform(0.9, 1.4))
    plate = r * 2.4
    z = max(z, plate / 2 + 0.15)
    body, lights = a.part("Body"), a.part("Glow")
    glow = p.glow()
    cube(body, (plate, 0.06, plate), (0, 0.07, z), "M_RobotDark", bevel=0.02)
    for x in (-1, 1):
        for zz in (-1, 1):
            cyl(body, 0.02, 0.02, (x * plate * 0.4, 0.035, z + zz * plate * 0.4), "M_Metal", sides=6, rot=ALONG_Y)
    cyl(body, r * 0.35, 0.16, (0, -0.04, z), p.material(["M_Metal", "M_Wall"]), sides=8, rot=ALONG_Y)
    cyl(body, 0.04, 0.14, (0, -0.18, z), "M_Metal", sides=6, rot=ALONG_Y)
    cyl(lights, r * 0.38, 0.03, (0, -0.02, z), glow, sides=8, rot=ALONG_Y)
    if p.bool("pipes", 0.5):
        pr = max(0.05, r * 0.3)
        for s in (-1, 1):
            ln = max(0.05, z - plate / 2 - 0.02) if s < 0 else rng.uniform(0.4, 1.0)
            cyl(body, pr, ln, (plate * 0.3, 0.0, z + s * (plate / 2 + ln / 2)), "M_Metal", sides=8)
            cyl(body, pr * 1.3, 0.06, (plate * 0.3, 0.0, z + s * (plate / 2 + 0.03)), "M_RobotDark", sides=8)
    center = (0.0, -0.26, z)
    valve_wheel(a.part("Wheel", pivot=center), center, radius=r)
    a.behaviour("Rotatable", {"target": "Wheel", "glow": "Glow"},
                {"axis": "forward", "step": 90, "speed": p.option("speed"), "target": p.option("steps"),
                 "interactive": True}, note="like the game's Valve: 90 degree steps around Unity forward")


@model("lever", "Lever", "puzzle", "Wall lever (pull handle) or rotary dial with step marks (Lever, Rotatable)",
       pivot="wall", params=[
           Param("style", "choice", "Bauform", choices=("lever", "dial")),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.4, hi=2.5),
           Param("positions", "int", "Stellungen", lo=2, hi=8),
           Param("speed", "float", "Tempo (°/s)", lo=10, hi=1000, unity=True, default=120),
       ])
def lever(rng, a):
    p = a.p
    style = p.choice("style", ["lever", "lever", "dial"])
    z = p.value("mount_height", rng.uniform(1.0, 1.4))
    positions = p.int("positions", 2, 4)
    body, lights = a.part("Body"), a.part("Glow")
    glow = p.glow()
    a.meta.update({"style": style, "positions": positions})
    if style == "lever":
        pw, ph = rng.uniform(0.25, 0.35), rng.uniform(0.5, 0.7)
        z = max(z, ph / 2 + 0.05)
        cube(body, (pw, 0.08, ph), (0, 0.06, z), p.material(["M_RobotDark", "M_Wall"]), bevel=0.02)
        cube(body, (0.06, 0.04, ph * 0.8), (0, 0.0, z), "M_Ground")  # the slot it moves in
        swing = 90.0
        step = swing / (positions - 1)
        for i in range(positions):  # marks next to the slot, along the arc
            ang = deg(-swing / 2 + i * step)
            cube(lights if i == positions - 1 else body, (0.05, 0.02, 0.02),
                 (pw * 0.35, -0.03, z + math.sin(ang) * ph * 0.38), glow if i == positions - 1 else "M_Metal")
        hinge = (0.0, -0.04, z)
        handle = a.part("Lever", pivot=hinge)
        cyl(handle, 0.05, 0.12, (0, -0.04, z), "M_Metal", sides=8, rot=ALONG_X)
        length = ph * rng.uniform(0.55, 0.7)
        tilt = (deg(-swing / 2), 0.0, 0.0)  # rest position: handle tilted down (rotate around Unity right)
        cube(handle, (0.05, 0.05, length), add_vec(hinge, rotated(tilt, (0, -0.06, length / 2))), "M_Metal",
             rot=tilt)
        cube(handle, (0.16, 0.08, 0.08), add_vec(hinge, rotated(tilt, (0, -0.06, length))),
             p.material(["M_HazardOrange", "M_RobotDark", "M_Warning"]), bevel=0.02, rot=tilt)
        axis = "right"
    else:
        r = rng.uniform(0.12, 0.2)
        z = max(z, r * 1.6 + 0.05)
        cube(body, (r * 3, 0.06, r * 3), (0, 0.07, z), p.material(["M_RobotDark", "M_Wall"]), bevel=0.02)
        step = 360.0 / positions
        for i in range(positions):
            ang = math.pi / 2 - deg(i * step)
            cube(lights if i == 0 else body, (0.03, 0.02, 0.05),
                 (math.cos(ang) * r * 1.25, 0.03, z + math.sin(ang) * r * 1.25),
                 glow if i == 0 else "M_Metal", rot=(0, math.pi / 2 - ang, 0))
        center = (0.0, -0.02, z)
        knob = a.part("Lever", pivot=center)
        cyl(knob, r, 0.08, center, "M_RobotDark", sides=10, bevel=0.015, rot=ALONG_Y)
        cube(knob, (0.04, 0.05, r * 0.9), (0, -0.07, z + r * 0.4), "M_HazardOrange")  # pointer
        axis = "forward"
    a.behaviour("Rotatable", {"target": "Lever", "glow": "Glow"},
                {"axis": axis, "step": round(step, 3), "speed": p.option("speed"), "target": positions - 1,
                 "interactive": True}, note="lever: around Unity right; dial: around Unity forward")


PIPE_ARMS = {  # which tile edges a fitting connects: -Y (front), +X, +Y, -X
    "straight": (0, 2),
    "elbow": (0, 1),
    "tee": (0, 1, 3),
    "cross": (0, 1, 2, 3),
    "end": (0,),
}


@model("pipe_fitting", "PipeFitting", "puzzle", "1 m pipe puzzle tile: straight, elbow, tee, cross or end piece "
       "that turns in 90° steps (Fitting, Rotatable)", params=[
           Param("kind", "choice", "Stück", choices=tuple(PIPE_ARMS)),
           Param("tile", "float", "Kachel (m)", lo=0.5, hi=3.0, size=True),
           Param("radius", "float", "Rohr-Radius (m)", lo=0.05, hi=0.3),
           Param("base", "bool", "Bodenplatte"),
           Param("target", "int", "Ziel-Stellung (0-3)", lo=0, hi=3, unity=True, default=0),
           Param("speed", "float", "Tempo (°/s)", lo=10, hi=1000, unity=True, default=240),
       ])
def pipe_fitting(rng, a):
    p = a.p
    kind = p.choice("kind", list(PIPE_ARMS))
    tile = p.value("tile", rng.choice([1.0, 1.0, 1.0, 2.0]))
    r = p.float("radius", 0.1, 0.16)
    r = min(r, tile * 0.2)
    has_base = p.bool("base", 0.7)
    mat = p.material(["M_Metal", "M_Wall"])
    glow = p.glow()
    body, lights = a.part("Body"), a.part("Glow")
    a.meta.update({"kind": kind, "tile_m": tile})
    zc = r + 0.12
    if has_base:
        cube(body, (tile, tile, 0.08), (0, 0, 0.04), "M_RobotDark", bevel=0.02)
        for s in (-1, 1):  # glow edge on the tile, shows "flow" (does not turn)
            cube(lights, (tile * 0.8, 0.03, 0.02), (0, s * (tile / 2 - 0.05), 0.09), glow)
        cyl(body, tile * 0.18, 0.06, (0, 0, 0.11), "M_Metal", sides=8)  # turntable
    else:
        cyl(body, tile * 0.18, 0.08, (0, 0, 0.04), "M_RobotDark", sides=8)
        cyl(lights, tile * 0.19, 0.02, (0, 0, 0.07), glow, sides=8)
    center = (0.0, 0.0, zc)
    fit = a.part("Fitting", pivot=center)
    sides = 8
    arms = PIPE_ARMS[kind]
    cyl(fit, r * 1.3, r * 2.6, center, "M_RobotDark", sides=sides, bevel=0.02)  # hub
    half = tile / 2 - 0.02
    for k in arms:
        ang = -math.pi / 2 + k * math.pi / 2
        dx, dy = math.cos(ang), math.sin(ang)
        mid = (dx * half / 2, dy * half / 2, zc)
        cyl(fit, r, half, mid, mat, sides=sides, rot=(math.pi / 2, 0, ang + math.pi / 2))
        cyl(fit, r * 1.25, 0.06, (dx * (half - 0.04), dy * (half - 0.04), zc), "M_RobotDark", sides=sides,
            rot=(math.pi / 2, 0, ang + math.pi / 2))
    if kind == "end":
        cyl(fit, r * 1.35, 0.1, (0, 0, zc + r * 1.35), "M_HazardOrange", sides=sides)  # cap on the hub
    cube(fit, (0.04, tile * 0.25, 0.02), (0, 0, zc + r * 1.31), "M_Warning")  # orientation mark
    a.behaviour("Rotatable", {"target": "Fitting", "glow": "Glow"},
                {"axis": "up", "step": 90, "speed": p.option("speed"), "target": p.option("target"),
                 "interactive": True}, note="arms (rest): " + ", ".join(("front", "right", "back", "left")[k]
                                                                         for k in arms))


@model("laser_emitter", "LaserEmitter", "puzzle", "Laser emitter on a stand: housing, lens, beam start (SignalLight)",
       params=[
           Param("height", "float", "Strahlhöhe (m)", lo=0.3, hi=2.0, size=True),
           Param("style", "choice", "Bauform", choices=("stand", "box")),
           Param("mode", "choice", "SignalLight-Modus", choices=("Steady", "Blink", "Pulse"), unity=True,
                 default="Steady"),
       ])
def laser_emitter(rng, a):
    p = a.p
    h = p.float("height", 0.8, 1.2)
    style = p.choice("style", ["stand", "box"])
    glow = p.glow_from(["M_GlowRed", "M_GlowCyan", "M_GlowOrange"])
    body, lights = a.part("Body"), a.part("Glow")
    a.meta["style"] = style
    if style == "stand":
        cyl(body, 0.25, 0.08, (0, 0, 0.04), "M_RobotDark", sides=8, bevel=0.02)
        cyl(body, 0.05, h - 0.2, (0, 0, 0.08 + (h - 0.2) / 2), "M_Metal", sides=6)
        cube(body, (0.2, 0.4, 0.2), (0, 0.05, h), p.material(["M_Wall", "M_RobotDark"]), bevel=0.03)
    else:  # pedestal with a wide emitter housing and cooling fins
        cube(body, (0.45, 0.45, 0.08), (0, 0, 0.04), "M_RobotDark", bevel=0.02)
        cube(body, (0.25, 0.25, h - 0.2), (0, 0.05, 0.08 + (h - 0.2) / 2), p.material(["M_Wall", "M_Metal"]),
             bevel=0.02)
        cube(body, (0.36, 0.5, 0.28), (0, 0.05, h), "M_RobotDark", bevel=0.03)
        for i in range(4):
            cube(body, (0.38, 0.03, 0.22), (0, 0.12 + i * 0.05, h), "M_Metal")
    cyl(body, 0.1, 0.12, (0, -0.24, h), "M_Metal", sides=8, rot=ALONG_Y)
    cyl(lights, 0.065, 0.03, (0, -0.31, h), glow, sides=8, rot=ALONG_Y)
    a.empty("Beam", (0.0, -0.33, h))
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="Beam = start point of the laser ray, pointing to Unity forward")


@model("laser_mirror", "LaserMirror", "puzzle", "Turnable mirror on a base: redirects the laser in 45° steps "
       "(Mirror, Rotatable)", params=[
           Param("height", "float", "Spiegelmitte (m)", lo=0.3, hi=2.0, size=True),
           Param("step", "choice", "Schritt (°)", choices=(45, 90), unity=True),
           Param("target", "int", "Ziel-Stellung", lo=0, hi=7, unity=True, default=1),
       ])
def laser_mirror(rng, a):
    p = a.p
    h = p.float("height", 0.8, 1.2)
    body, lights = a.part("Body"), a.part("Glow")
    glow = p.glow()
    cyl(body, 0.3, 0.1, (0, 0, 0.05), "M_RobotDark", sides=8, bevel=0.02)
    cyl(lights, 0.31, 0.02, (0, 0, 0.09), glow, sides=8)
    round_base(a, body, 0.3, 0.1, "M")  # variety details (own stream)
    mw, mh = rng.uniform(0.35, 0.5), rng.uniform(0.35, 0.55)
    center = (0.0, 0.0, 0.1)
    mirror = a.part("Mirror", pivot=center)
    cyl(mirror, 0.2, 0.06, (0, 0, 0.13), "M_Metal", sides=8)
    for x in (-mw / 2 - 0.03, mw / 2 + 0.03):
        cube(mirror, (0.04, 0.06, h - 0.1), (x, 0, 0.16 + (h - 0.16) / 2), "M_Metal")
    yaw = (0.0, 0.0, deg(45))  # rest: 45 degrees, reflects front -> side
    cube(mirror, (mw, 0.05, mh), (0, 0, h), "M_RobotDark", bevel=0.01, rot=yaw)
    cube(mirror, (mw - 0.06, 0.01, mh - 0.06), add_vec((0, 0, h), rotated(yaw, (0, -0.03, 0))), "M_Glass", rot=yaw)
    cube(mirror, (mw, 0.04, 0.04), (0, 0, h - mh / 2 - 0.03), "M_Metal")
    a.behaviour("Rotatable", {"target": "Mirror", "glow": "Glow"},
                {"axis": "up", "step": p.choice("step", [45, 45, 90]), "speed": 180, "target": p.option("target"),
                 "interactive": True}, note="mirror rests at 45 degrees around Unity up")


@model("laser_receiver", "LaserReceiver", "puzzle", "Laser target: housing with a crystal lens that lights up "
       "(SignalIndicator)", params=[
           Param("height", "float", "Zielhöhe (m)", lo=0.3, hi=2.5, size=True),
           Param("mount", "choice", "Montage", choices=("stand", "pillar")),
           _status_param(),
       ])
def laser_receiver(rng, a):
    p = a.p
    h = p.float("height", 0.8, 1.2)
    mount = p.choice("mount", ["stand", "pillar"])
    body, lights = a.part("Body"), a.part("Glow")
    status = STATUS[p.option("status")]
    a.meta["mount"] = mount
    if mount == "stand":
        cyl(body, 0.25, 0.08, (0, 0, 0.04), "M_RobotDark", sides=8, bevel=0.02)
        cyl(body, 0.05, h - 0.2, (0, 0, 0.08 + (h - 0.2) / 2), "M_Metal", sides=6)
    else:
        cube(body, (0.35, 0.35, h - 0.15), (0, 0.05, (h - 0.15) / 2), p.material(["M_Wall", "M_Metal"]), bevel=0.03)
    r = rng.uniform(0.18, 0.26)
    if mount == "stand":  # variety details (own stream), below the housing
        round_base(a, body, 0.25, 0.08, "R")
    else:
        pillar_front(a, body, -0.125, 0.0, h - 0.15 - r - 0.05, 0.35, "R")
    cyl(body, r, 0.18, (0, 0.03, h), "M_RobotDark", sides=8, bevel=0.02, rot=ALONG_Y)
    cyl(body, r * 0.75, 0.06, (0, -0.08, h), "M_Metal", sides=8, rot=ALONG_Y)
    cyl(a.part("Lens"), r * 0.5, 0.08, (0, -0.1, h), "M_Optic", sides=6, rot=ALONG_Y)
    for i in range(4):
        ang = math.pi / 4 + i * math.pi / 2
        cube(lights, (0.04, 0.02, 0.04), (math.cos(ang) * r * 0.9, -0.07, h + math.sin(ang) * r * 0.9), status)
    _indicator(a, note="lights up when the laser hits the Lens")


@model("pressure_plate", "PressurePlate", "puzzle", "Floor pressure plate: frame, sinking plate (Plate), glow edge",
       params=[
           Param("size", "float", "Größe (m)", lo=0.4, hi=3.0, size=True),
           Param("shape", "choice", "Form", choices=("square", "round")),
           Param("stripes", "bool", "Warnstreifen"),
           _status_param(),
       ])
def pressure_plate(rng, a):
    p = a.p
    s = p.float("size", 0.8, 1.4)
    shape = p.choice("shape", ["square", "square", "round"])
    body, lights = a.part("Body"), a.part("Glow")
    status = STATUS[p.option("status")]
    plate_mat = p.material(["M_Metal", "M_Platform", "M_RobotBody"])
    a.meta["shape"] = shape
    center = (0.0, 0.0, 0.1)
    plate = a.part("Plate", pivot=center)
    if shape == "square":
        cube(body, (s + 0.2, s + 0.2, 0.08), (0, 0, 0.04), "M_RobotDark", bevel=0.02)
        cube(lights, (s + 0.04, s + 0.04, 0.02), (0, 0, 0.085), status)
        cube(plate, (s - 0.04, s - 0.04, 0.06), (0, 0, 0.11), plate_mat, bevel=0.015)
        for i in range(3):
            cube(plate, (s * 0.7, 0.04, 0.01), (0, -s * 0.25 + i * s * 0.25, 0.145), "M_RobotDark")
        if p.bool("stripes", 0.4, warning=True):
            stripes(body, s, (0, -s / 2 - 0.06, 0.081), count=5, width=0.06, height=0.01)
    else:
        r = s / 2 / math.cos(math.pi / 10)
        cyl(body, r + 0.1, 0.08, (0, 0, 0.04), "M_RobotDark", sides=10, bevel=0.02)
        cyl(lights, r + 0.02, 0.02, (0, 0, 0.085), status, sides=10)
        cyl(plate, r - 0.02, 0.06, (0, 0, 0.11), plate_mat, sides=10, bevel=0.015)
        cyl(plate, r * 0.4, 0.01, (0, 0, 0.145), "M_RobotDark", sides=10)
        if p.bool("stripes", 0.4, warning=True):
            stripes(body, s, (0, -r - 0.06, 0.081), count=5, width=0.04, height=0.01)
    if p.style.generation >= 3:
        a.mesh_collider("Body", convex=True)
        a.mesh_collider("Plate", convex=True)
    _indicator(a, note="Plate sinks by ~4 cm when pressed (pivot at its centre)")


@model("keypad", "Keypad", "puzzle", "Wall keypad / button panel with a display (Screen) and status glow",
       pivot="wall", params=[
           Param("layout", "choice", "Tasten", choices=("numpad", "buttons", "big_button")),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.5, hi=2.5),
           _status_param(),
           Param("variant", "choice", "Variante", choices=("standard", "access"), default="standard", quiet=True,
                 description="access: Zugangspanel mit Kartenleser-Modul (Slot), Schutzhaube und Statusleiste; "
                             "Script und Anzeigen wie standard"),
       ])
def keypad(rng, a):
    p = a.p
    layout = p.choice("layout", ["numpad", "buttons", "big_button"])
    w, h = rng.uniform(0.3, 0.42), rng.uniform(0.45, 0.6)
    d = 0.08
    z = p.value("mount_height", rng.uniform(1.1, 1.4))
    z = max(z, h / 2 + 0.05)
    body, lights, glow = a.part("Body"), a.part("Lights"), a.part("Glow")
    status = STATUS[p.option("status")]
    yf = 0.1 - d
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_RobotDark", "M_Wall", "M_Metal"]), bevel=0.015)
    cube(a.part("Screen"), (w * 0.75, 0.02, h * 0.18), (0, yf - 0.005, z + h * 0.33), p.glow(weights=(0.8, 0.1, 0.1)))
    a.meta["layout"] = layout
    if layout == "numpad":
        for row in range(4):
            for col in range(3):
                cube(body, (w * 0.2, 0.03, h * 0.1), (-w * 0.25 + col * w * 0.25, yf - 0.01, z + h * 0.1 - row * h * 0.14),
                     "M_Platform", bevel=0.005)
    elif layout == "buttons":
        n = rng.randint(2, 4)
        for i in range(n):
            mat = rng.choice(["M_GlowCyan", "M_GlowRed", "M_GlowOrange"])
            cyl(lights, w * 0.09, 0.04, (-w * 0.3 + i * w * 0.6 / max(1, n - 1), yf - 0.015, z - h * 0.05), mat,
                sides=8, rot=ALONG_Y)
    else:
        cyl(body, w * 0.32, 0.03, (0, yf - 0.01, z - h * 0.1), "M_Warning", sides=10, rot=ALONG_Y)
        cyl(lights, w * 0.24, 0.06, (0, yf - 0.03, z - h * 0.1), "M_GlowRed", sides=10, rot=ALONG_Y)
    cube(glow, (w * 0.15, 0.02, 0.03), (w * 0.3, yf - 0.005, z - h * 0.42), status)
    if p.option("variant") == "access":  # access panel: card reader module beside it, hood, status bar
        cx = w / 2 + 0.11
        cube(body, (0.18, d + 0.02, h * 0.7), (cx, 0.1 - (d + 0.02) / 2, z - h * 0.05), "M_RobotDark", bevel=0.012)
        cube(body, (0.12, 0.05, 0.03), (cx, yf - 0.035, z + h * 0.05), "M_Metal")  # card slot bezel
        cube(body, (0.09, 0.012, 0.008), (cx, yf - 0.061, z + h * 0.05), "M_Ground")
        a.empty("Slot", (cx, yf - 0.07, z + h * 0.05))
        cube(glow, (0.03, 0.02, 0.03), (cx, yf - 0.03, z - h * 0.25), status)
        cube(body, (w + 0.3, 0.12, 0.03), (0.11, 0.1 - 0.06, z + h / 2 + 0.035), "M_Metal")  # hood
        cube(lights, (w + 0.22, 0.015, 0.025), (0.11, yf - 0.015, z - h / 2 - 0.04), "M_GlowCyan")  # status bar
        a.meta["variant"] = "access"
    _indicator(a)


# --------------------------------------------------------------------------
# watching and listening: cameras and antennas (turning heads)
# --------------------------------------------------------------------------

@model("camera", "Camera", "tech", "Security camera on a wall arm: turning head (Rotor), blinking LED", pivot="wall",
       params=[
           Param("mount_height", "float", "Höhe über Boden (m)", lo=1.0, hi=4.0),
           Param("style", "choice", "Bauform", choices=("box", "dome")),
           Param("speed", "float", "Dreh-Tempo (°/s, 0 = steht)", lo=-180, hi=180, unity=True, default=0,
                 description="Rotator dreht endlos; 0, bis es ein Schwenk-Script gibt"),
           Param("mode", "choice", "LED-Modus", choices=("Steady", "Blink", "Pulse"), unity=True, default="Blink"),
           sweep_param(),
       ])
def camera(rng, a):
    p = a.p
    z = p.value("mount_height", rng.uniform(2.2, 2.8))
    style = p.choice("style", ["box", "box", "dome"])
    body, lights = a.part("Body"), a.part("Glow")
    a.meta["style"] = style
    cube(body, (0.18, 0.06, 0.25), (0, 0.07, z), "M_RobotDark", bevel=0.01)
    arm = rng.uniform(0.25, 0.4)
    cube(body, (0.06, arm, 0.06), (0, 0.04 - arm / 2, z), "M_Metal")
    center = (0.0, 0.04 - arm, z - 0.05)
    head = a.part("Rotor", pivot=center)
    cx, cy, cz = center
    cyl(head, 0.04, 0.1, (cx, cy, cz), "M_Metal", sides=6)
    if style == "box":
        pitch = rng.uniform(15, 30)
        # The front is -Y: positive Blender X pitch points the lens down.
        tilt = (deg(pitch if p.style.generation >= 3 else -pitch), 0.0, 0.0)
        cube(head, (0.18, 0.4, 0.16), add_vec(center, rotated(tilt, (0, -0.12, -0.1))), p.material(["M_Platform", "M_RobotBody", "M_Wall"]),
             bevel=0.02, rot=tilt)
        cube(head, (0.22, 0.3, 0.02), add_vec(center, rotated(tilt, (0, -0.1, -0.01))), "M_RobotDark", rot=tilt)
        cyl(head, 0.055, 0.04, add_vec(center, rotated(tilt, (0, -0.33, -0.1))), "M_Glass", sides=8,
            rot=(tilt[0] + math.pi / 2, 0, 0))
        cube(lights, (0.03, 0.02, 0.03), add_vec(center, rotated(tilt, (0.06, -0.325, -0.04))), "M_GlowRed", rot=tilt)
    else:
        cyl(head, 0.14, 0.06, (cx, cy, cz - 0.07), "M_RobotDark", sides=10)
        cyl(head, 0.13, 0.12, (cx, cy, cz - 0.16), "M_Glass", sides=10, radius_top=0.13 * 0.98)
        cyl(head, 0.13 * 0.98, 0.05, (cx, cy, cz - 0.245), "M_Glass", sides=10, radius_top=0.06)
        cube(lights, (0.03, 0.03, 0.02), (cx, cy - 0.1, cz - 0.05), "M_GlowRed")
    wall_mount(a, body, z, 0.1, "C")  # variety details (own stream): conduit, plate or junction box on the wall
    sweep = p.option("sweep")
    if sweep:  # the LED sits on the head: it turns with it
        prerotate(a, "Rotor", 0.0, adopt=("Glow",))
    sweep_rotator(a, "Rotor", p.option("speed"), sweep,
                  "head turns around Unity up; speed 0 = still (a Rotator spins endlessly, not a sweep)")
    if p.style.generation >= 3:
        a.mesh_collider("Body", convex=True)
        a.mesh_collider("Rotor", convex=True)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})


@model("antenna", "Antenna", "tech", "Antenna mast, radar or satellite dish on a base; turning head (Rotor)", params=[
    Param("style", "choice", "Bauform", choices=("mast", "radar", "dish")),
    Param("height", "float", "Höhe (m)", lo=0.8, hi=6.0, size=True),
    Param("speed", "float", "Dreh-Tempo (°/s)", lo=0, hi=360, unity=True),
])
def antenna(rng, a):
    p = a.p
    style = p.choice("style", ["mast", "radar", "dish"])
    h = p.float("height", 1.6, 3.0)
    body, lights = a.part("Body"), a.part("Glow")
    glow = p.glow_from(["M_GlowRed", "M_GlowRed", "M_GlowCyan"])
    a.meta["style"] = style
    base = rng.uniform(0.5, 0.8)
    cube(body, (base, base, 0.2), (0, 0, 0.1), "M_RobotDark", bevel=0.02)
    if style == "mast":  # lattice mast with a blinking tip, turning cross arms on top
        legs = 0.12 + h * 0.03
        for x in (-1, 1):
            for y in (-1, 1):
                cube(body, (0.04, 0.04, h), (x * legs, y * legs, 0.2 + h / 2), "M_Metal")
        for i in range(int(h / 0.5)):
            zz = 0.4 + i * 0.5
            for s in (-1, 1):
                cube(body, (legs * 2, 0.03, 0.03), (0, s * legs, zz), "M_Metal")
                cube(body, (0.03, legs * 2, 0.03), (s * legs, 0, zz), "M_Metal")
        top = 0.2 + h
        center = (0.0, 0.0, top)
        rotor = a.part("Rotor", pivot=center)
        cyl(rotor, 0.05, 0.1, (0, 0, top + 0.05), "M_RobotDark", sides=6)
        for k in range(2):
            cube(rotor, (0.8 if k == 0 else 0.03, 0.03 if k == 0 else 0.6, 0.03), (0, 0, top + 0.1 + k * 0.1), "M_Metal")
        cyl(body, 0.015, 0.5, (0, 0, top + 0.4), "M_Metal", sides=6)
        cube(lights, (0.06, 0.06, 0.06), (0, 0, top + 0.68), glow)
        speed = 30
    elif style == "radar":
        cyl(body, 0.12, h * 0.6, (0, 0, 0.2 + h * 0.3), "M_Wall", sides=8)
        top = 0.2 + h * 0.6
        cyl(body, 0.2, 0.12, (0, 0, top), "M_RobotDark", sides=8)
        center = (0.0, 0.0, top)
        rotor = a.part("Rotor", pivot=center)
        width = min(2.4, h * rng.uniform(0.5, 0.8))
        cube(rotor, (0.08, 0.08, 0.35), (0, 0, top + 0.2), "M_Metal")
        cube(rotor, (width, 0.08, 0.3), (0, -0.08, top + 0.4), p.material(["M_Platform", "M_Wall"]), bevel=0.02,
             rot=(deg(-15), 0, 0))
        for i in range(5):
            cube(rotor, (0.03, 0.05, 0.28), (-width / 2 + 0.1 + i * (width - 0.2) / 4, -0.13, top + 0.4), "M_RobotDark",
                 rot=(deg(-15), 0, 0))
        cube(lights, (0.12, 0.12, 0.05), (0, 0, top + 0.08), glow)
        speed = 60
    else:  # satellite dish, tilted up
        cyl(body, 0.1, h * 0.5, (0, 0, 0.2 + h * 0.25), "M_Wall", sides=8)
        top = 0.2 + h * 0.5
        center = (0.0, 0.0, top)
        rotor = a.part("Rotor", pivot=center)
        r = min(1.4, h * rng.uniform(0.3, 0.45))
        tilt = (deg(rng.uniform(30, 55)), 0.0, 0.0)
        cyl(rotor, 0.12, 0.2, (0, 0, top + 0.1), "M_RobotDark", sides=8)
        dish_c = (0, 0, top + 0.2 + r * 0.6)
        bowl = lathe([(0.0, -r * 0.08), (r * 0.35, -r * 0.05), (r, r * 0.22), (r * 0.94, r * 0.24),
                      (r * 0.3, r * 0.02), (0.0, 0.0)], 12,
                     [p.material(["M_Platform", "M_RobotBody"]), "M_Platform", "M_RobotDark", "M_Wall", "M_Wall"])
        rotor.add(bowl, loc=dish_c, rot=tilt)
        cube(rotor, (0.08, 0.08, r * 0.7), add_vec(dish_c, rotated(tilt, (0, 0, -r * 0.45))), "M_Metal", rot=tilt)
        cyl(rotor, 0.04, r * 0.9, add_vec(dish_c, rotated(tilt, (0, 0, -r * 0.5))), "M_Metal", sides=6, rot=tilt)
        cube(lights, (0.08, 0.08, 0.08), add_vec(dish_c, rotated(tilt, (0, 0, -r * 0.95))), glow, rot=tilt)
        speed = 10
    speed = p.value("speed", speed)
    a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": speed})
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Blink" if style == "mast" else "Pulse"})
