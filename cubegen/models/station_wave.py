"""First asset wave from IDEEN.md (cubegen 0.11.2): station architecture, machines, technology and props.

Eleven candidates that no existing type, variant or kit covered. They reuse the geometry of the experimental
prototypes (``test_pipe_rack``, ``test_relay_box``, ``test_coolant_loop``, ``test_warning_beacon``) and the
helpers of the neighbouring families (pipe radii and connectors of ``pipe``, tank domes, pump fins).

Every type is a **static model** by default: no behaviour, so generation 3 gives each part an exact mesh collider
(openings, gaps under pipe runs and the inside of loops stay free). Gameplay scripts are an explicit option where a
later release needs them (``machine`` on turbine and compressor, ``signal`` on the warning beacon); the model and its
gameplay release are separate steps.

Conventions as everywhere: front -Y, floor pieces stand on z = 0, wall pieces (pivot ``wall``) have their back at
y = +0.1 and their pivot on the floor below, ceiling pieces hang at their mount height above a floor pivot.
"""

from __future__ import annotations

import math

from ..geometry import pipe_section, sphere
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, stripes, strut, valve_wheel
from .details import pole_tower
from .lettering import add_text, text_width
from .registry import model

STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}
PIPE_RADII = (0.09, 0.18)  # the radii of ``pipe`` / ``pipe_bend`` that fit a rack or a loop


def _status_param():
    return Param("status", "choice", "Glow-Startzustand", choices=("off", "on"), default="off",
                 description="Status-Glow beim Export: off = M_GlowRed, on = M_GlowCyan (Unity schaltet ihn um)")


def _flange(mesh, r, x, z, sides=10):
    """A dark flange ring around a pipe along X."""
    cyl(mesh, r * 1.25, 0.08, (x, 0, z), "M_RobotDark", sides=sides, rot=ALONG_X)


def _dome(mesh, r, center, direction, material, sides=12):
    """A low-poly dished head on a vessel: two cone rings, pointing along ``direction`` (+x, -x or +z, -z)."""
    cx, cy, cz = center
    axis, sign = direction[1], 1 if direction[0] == "+" else -1
    rot = {"x": (0.0, sign * math.pi / 2, 0.0), "z": (0.0 if sign > 0 else math.pi, 0.0, 0.0)}[axis]
    h1, h2 = r * 0.28, r * 0.16

    def at(d):
        return (cx + sign * d, cy, cz) if axis == "x" else (cx, cy, cz + sign * d)

    cyl(mesh, r, h1, at(h1 / 2), material, sides=sides, radius_top=r * 0.7, rot=rot)
    cyl(mesh, r * 0.7, h2, at(h1 + h2 / 2), material, sides=sides, radius_top=r * 0.3, rot=rot)
    return h1 + h2


# --------------------------------------------------------------------------
# architecture
# --------------------------------------------------------------------------

AIRLOCK_STATES = ("closed", "outer_open", "inner_open", "open")


@model("airlock_chamber", "AirlockChamber", "environment", "Walk-through airlock chamber: tube with two framed "
       "double doors (Panel_Outer at the front, Panel_Inner at the back), warning stripes, gauge and lights",
       params=[
           Param("length", "float", "Kammerlänge (m)", lo=2.0, hi=6.0, size=True),
           Param("width", "float", "Innenbreite (m)", lo=1.4, hi=3.0, size=True),
           Param("height", "float", "Innenhöhe (m)", lo=2.2, hi=3.4, size=True),
           Param("window", "bool", "Fenster in den Türen"),
           Param("stripes", "bool", "Warnstreifen an den Schwellen"),
           Param("state", "choice", "Türstellung", choices=AIRLOCK_STATES, default="closed", quiet=True,
                 description="Statisches Modell: geschlossen, äußere / innere Tür offen oder beide offen"),
       ])
def airlock_chamber(rng, a):
    p = a.p
    length = p.float("length", 2.6, 3.6)
    width = p.float("width", 1.8, 2.4)
    height = p.float("height", 2.4, 3.0)
    shell = p.material(["M_Wall", "M_RobotDark", "M_Wall"])
    glow = p.glow(weights=(0.8, 0.1, 0.1))
    window = p.bool("window", 0.6)
    stripe = p.bool("stripes", 0.7, warning=True)
    vents = rng.randint(1, 3)
    state = p.option("state")
    t, fd, floor = 0.25, 0.36, 0.1
    dw, dh = round(width * 0.7, 3), round(height - 0.3, 3)  # clear door opening
    a.meta.update({"inner_m": [round(width, 3), round(length, 3), round(height, 3)], "opening_m": [dw, dh],
                   "state": state, "floor_height_m": floor})
    body, lights = a.part("Body"), a.part("Glow")

    # tube between the two frames: walls, roof, floor (walkable top at z = floor)
    tube = length - fd
    for sx in (-1, 1):
        cube(body, (t, tube, height + 0.1), (sx * (width / 2 + t / 2), 0, (height + 0.1) / 2), shell, bevel=0.02)
        for k in range(vents):  # vent grilles on the inside
            y = -tube / 2 + tube * (k + 1) / (vents + 1)
            cube(body, (0.03, 0.5, 0.35), (sx * (width / 2 - 0.015), y, height * 0.72), "M_RobotDark")
    cube(body, (width + 2 * t, tube, 0.2), (0, 0, height + 0.2), shell, bevel=0.02)
    cube(body, (width, tube, floor), (0, 0, floor / 2), "M_Platform")
    cube(lights, (width * 0.5, tube * 0.8, 0.03), (0, 0, height + 0.085), glow)  # light strip under the roof

    def frame(y0, name):
        """A flanged door frame at y0: pocket plates, outer posts, header, threshold, two sliding leaves."""
        s = 1 if y0 > 0 else -1
        for sx in (-1, 1):
            for dy in (-0.14, 0.14):  # pocket: the leaf slides between two plates
                cube(body, (dw / 2, 0.08, dh), (sx * 3 * dw / 4, y0 + dy, dh / 2), shell, bevel=0.01)
            cube(body, (0.12, fd, dh), (sx * (dw + 0.06), y0, dh / 2), "M_RobotDark", bevel=0.01)
        header = height + 0.45 - dh
        cube(body, (2 * dw + 0.24, fd, header), (0, y0, dh + header / 2), "M_RobotDark", bevel=0.02)
        cube(body, (dw, fd, floor), (0, y0, floor / 2), "M_Metal")
        if stripe:
            stripes(body, dw * 0.9, (0, y0, floor + 0.006), count=6, width=fd * 0.6)
        cube(a.part(f"StatusLight_{name}"), (min(1.0, dw * 0.6), 0.02, 0.1), (0, y0 + s * (fd / 2 + 0.01), dh + 0.2),
             "M_GlowCyan" if state in ("open", name.lower() + "_open") else "M_GlowRed")
        is_open = state == "open" or state == name.lower() + "_open"
        for side, sx in (("", -1), ("_B", 1)):
            cx = sx * (3 * dw / 4 if is_open else dw / 4)  # closed: the two leaves meet with a 6 mm seal gap
            leaf = a.part(f"Panel_{name}{side}", pivot=(cx, y0, floor + dh / 2))
            cube(leaf, (dw / 2 - 0.006, 0.12, dh - floor - 0.02), (cx, y0, floor + (dh - floor) / 2), "M_Metal", bevel=0.015)
            cube(leaf, (dw / 2 - 0.12, 0.13, 0.06), (cx, y0, floor + (dh - floor) * 0.35), "M_RobotDark")
            if window:
                cube(leaf, (dw * 0.22, 0.13, dh * 0.22), (cx, y0, floor + (dh - floor) * 0.7), "M_Glass")

    frame(-length / 2, "Outer")
    frame(length / 2, "Inner")
    # pressure gauge and cycle button beside the inner door, on the inside wall
    gx = -(width / 2 - 0.04)
    cyl(body, 0.12, 0.05, (gx, length / 2 - fd - 0.35, 1.5), "M_Metal", sides=10, rot=(0, math.pi / 2, 0))
    cyl(lights, 0.09, 0.02, (gx + 0.03, length / 2 - fd - 0.35, 1.5), glow, sides=10, rot=(0, math.pi / 2, 0))
    cube(body, (0.05, 0.16, 0.22), (gx + 0.01, length / 2 - fd - 0.7, 1.25), "M_Warning")


@model("ceiling_beam", "CeilingBeam", "environment", "Ceiling beam spanning along X under the ceiling (top at "
       "mount height): I-beam, truss or box girder with bearing plates, optional cable tray and lamps",
       pivot="wall", view="below", params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0, 6.0)),
           Param("profile", "choice", "Profil", choices=("i_beam", "truss", "box")),
           Param("depth", "float", "Trägerhöhe (m)", lo=0.2, hi=0.8, size=True),
           Param("tray", "bool", "Kabeltrasse darunter"),
           Param("lamps", "bool", "Lampen darunter"),
           Param("mount_height", "float", "Oberkante über Boden (m)", lo=2.2, hi=8.0, default=3.0, quiet=True),
       ])
def ceiling_beam(rng, a):
    p = a.p
    ln = p.choice("length", [2.0, 4.0, 4.0, 6.0])
    profile = p.choice("profile", ["i_beam", "i_beam", "truss", "box"])
    h = p.float("depth", 0.3, 0.55)
    mat = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    tray = p.bool("tray", 0.4)
    lamps = p.bool("lamps", 0.5)
    glow = p.glow()
    top = p.option("mount_height")
    body = a.part("Girder")  # "Beam" is the moving balance beam of balance_scale
    a.meta.update({"length_m": ln, "profile": profile, "depth_m": round(h, 3), "top_m": top})
    zc, w = top - h / 2, max(0.18, h * 0.6)
    if profile == "i_beam":
        for dz in (h / 2 - 0.025, -h / 2 + 0.025):
            cube(body, (ln, w, 0.05), (0, 0, zc + dz), mat)
        cube(body, (ln, 0.05, h - 0.1), (0, 0, zc), mat)
        for k in range(int(ln / 1.0) + 1):  # web stiffeners every metre
            cube(body, (0.03, w * 0.8, h - 0.1), (-ln / 2 + 0.05 + k * (ln - 0.1) / max(1, int(ln / 1.0)), 0, zc), mat)
    elif profile == "truss":
        for dz in (h / 2 - 0.05, -h / 2 + 0.05):
            for dy in (-w / 2 + 0.04, w / 2 - 0.04):
                cube(body, (ln, 0.08, 0.1), (0, dy, zc + dz), mat)
        bays = max(2, int(round(ln / 0.5)))
        for k in range(bays):
            x0 = -ln / 2 + ln * k / bays
            x1 = x0 + ln / bays
            for dy in (-w / 2 + 0.04, w / 2 - 0.04):
                lo, hi = (x0, x1) if k % 2 == 0 else (x1, x0)
                strut(body, (lo, dy, zc - h / 2 + 0.1), (hi, dy, zc + h / 2 - 0.1), 0.025, "M_Metal")
                cube(body, (0.05, 0.05, h - 0.2), (x0, dy, zc), "M_Metal")
        for dy in (-w / 2 + 0.04, w / 2 - 0.04):
            cube(body, (0.05, 0.05, h - 0.2), (ln / 2, dy, zc), "M_Metal")
    else:
        for dz in (h / 2 - 0.03, -h / 2 + 0.03):
            cube(body, (ln, w, 0.06), (0, 0, zc + dz), mat)
        for dy in (w / 2 - 0.025, -w / 2 + 0.025):
            cube(body, (ln, 0.05, h - 0.12), (0, dy, zc), mat)
    for sx in (-1, 1):  # bearing plates at both ends
        cube(body, (0.06, w + 0.12, h + 0.08), (sx * (ln / 2 - 0.03), 0, zc), "M_RobotDark", bevel=0.01)
    if tray:  # cable tray on two hanger rods
        tz = zc - h / 2 - 0.35
        cube(body, (ln * 0.9, 0.3, 0.03), (0, 0, tz), "M_Metal")
        for dy in (-0.15, 0.15):
            cube(body, (ln * 0.9, 0.02, 0.08), (0, dy, tz + 0.04), "M_Metal")
        for sx in (-1, 1):
            cyl(body, 0.012, 0.35, (sx * ln * 0.35, 0, tz + 0.175), "M_Metal", sides=6)
        cyl(body, 0.045, ln * 0.85, (0, -0.05, tz + 0.06), "M_HazardOrange", sides=6, rot=ALONG_X)
    if lamps:
        lights = a.part("Glow")
        for k in range(max(1, int(ln / 2))):
            x = -ln / 2 + ln * (k + 0.5) / max(1, int(ln / 2))
            cube(body, (0.5, 0.18, 0.08), (x, 0, zc - h / 2 - 0.04), "M_RobotDark", bevel=0.01)
            cube(lights, (0.44, 0.12, 0.02), (x, 0, zc - h / 2 - 0.085), glow)


# --------------------------------------------------------------------------
# machines and pipes
# --------------------------------------------------------------------------

@model("pipe_rack", "PipeRack", "industrial", "Pipe rack: frames of I-profile uprights every 2 m along X, cross "
       "beams on 1-3 levels carrying hollow pipe runs (ends fit ``pipe``), clamps, optional cable tray on top",
       params=[
           Param("length", "choice", "Länge (m)", choices=(2.0, 4.0, 6.0)),
           Param("levels", "int", "Ebenen", lo=1, hi=3),
           Param("pipes", "int", "Rohre je Ebene", lo=1, hi=3),
           Param("radius", "choice", "Rohr-Radius (m)", choices=PIPE_RADII),
           Param("height", "float", "Höhe (m)", lo=1.4, hi=4.0, size=True),
           Param("tray", "bool", "Kabeltrasse oben"),
       ])
def pipe_rack(rng, a):
    p = a.p
    ln = p.choice("length", [2.0, 4.0, 4.0, 6.0])
    levels = p.int("levels", 1, 3)
    per = p.int("pipes", 1, 3)
    r = p.choice("radius", list(PIPE_RADII))
    h = p.float("height", 1.8, 2.8)
    frame_mat = p.material(["M_RobotDark", "M_Metal"])
    pipe_mat = p.material(["M_Metal", "M_Wall"])
    glow = p.glow()
    tray = p.bool("tray", 0.4)
    depth = max(0.7, per * (2 * r + 0.2) + 0.2)
    body, lights = a.part("Frame"), a.part("Glow")
    # level heights: the lowest leaves at least 1 m clear underneath
    zs = [round(h * (0.45 + 0.5 * k / max(1, levels)) if levels > 1 else h * 0.75, 3) for k in range(levels)]
    frames = int(round(ln / 2)) + 1
    xs = [-ln / 2 + 0.1 + (ln - 0.2) * i / (frames - 1) for i in range(frames)]
    for x in xs:
        for dy in (-depth / 2, depth / 2):
            # I-profile upright: two flanges and a web
            for fx in (-0.07, 0.07):
                cube(body, (0.02, 0.16, h), (x + fx, dy, h / 2), frame_mat)
            cube(body, (0.12, 0.02, h), (x, dy, h / 2), frame_mat)
            cube(body, (0.3, 0.3, 0.03), (x, dy, 0.015), "M_RobotDark")  # base plate
        for z in zs:
            cube(body, (0.12, depth + 0.16, 0.12), (x, 0, z - r - 0.06), frame_mat)  # the pipes rest on it
        cube(body, (0.12, depth + 0.16, 0.12), (x, 0, h - 0.06), frame_mat)
    for dy in (-depth / 2, depth / 2):  # longitudinal top beams
        cube(body, (ln, 0.12, 0.12), (0, dy, h - 0.06), frame_mat)
    runs = a.part("Pipes")
    ends = []
    for k, z in enumerate(zs):
        for j in range(per):
            y = -depth / 2 + 0.2 + r + j * (2 * r + 0.2) if per > 1 else 0.0
            runs.add(pipe_section(r, ln, min(0.03, r * 0.3), 8, pipe_mat), loc=(0, y, z), rot=ALONG_X)
            for x in (-ln / 2 + 0.06, ln / 2 - 0.06):
                cyl(runs, r * 1.25, 0.12, (x, y, z), "M_RobotDark", sides=8, rot=ALONG_X)
            if (k + j) % 2 == 0:
                cyl(lights, r * 1.06, 0.06, (0, y, z), glow, sides=8, rot=ALONG_X)
            ends.append([round(y, 4), z])
    if tray:
        cube(body, (ln, depth * 0.8, 0.03), (0, 0, h + 0.015), "M_Metal")
        for dy in (-depth * 0.4, depth * 0.4):
            cube(body, (ln, 0.02, 0.1), (0, dy, h + 0.05), "M_Metal")
    a.meta.update({"length_m": ln, "radius": r, "pipe_axes": ends, "levels_m": zs, "depth_m": round(depth, 3)})


@model("coolant_loop", "CoolantLoop", "industrial", "Coolant loop: supply and return risers, top and bottom runs "
       "with rounded elbows, inline heat exchanger, optional pump and service valve; the loop stays open inside",
       params=[
           Param("width", "float", "Breite (m)", lo=1.2, hi=4.0, size=True),
           Param("height", "float", "Höhe (m)", lo=1.0, hi=3.0, size=True),
           Param("radius", "choice", "Rohr-Radius (m)", choices=PIPE_RADII),
           Param("state", "choice", "Kühlmittel", choices=("cold", "hot")),
           Param("pump", "bool", "Umwälzpumpe"),
           Param("valve", "bool", "Serviceventil"),
       ])
def coolant_loop(rng, a):
    p = a.p
    w = p.float("width", 1.6, 2.6)
    h = p.float("height", 1.4, 2.2)
    r = p.choice("radius", list(PIPE_RADII))
    state = p.choice("state", ["cold", "cold", "hot"])
    pump = p.bool("pump", 0.6)
    valve = p.bool("valve", 0.5)
    mat = p.material(["M_Metal", "M_Wall"])
    glow = {"cold": "M_GlowCyan", "hot": "M_GlowOrange"}[state]
    body, lights = a.part("Pipe"), a.part("Glow")
    z0 = r + 0.3
    z1 = z0 + h - 2 * r
    for x in (-w / 2, w / 2):  # risers
        cyl(body, r, z1 - z0, (x, 0, (z0 + z1) / 2), mat, sides=10)
        for z in (z0, z1):
            body.add(sphere(r * 1.04, 10, 4, mat), loc=(x, 0, z))  # rounded elbow knuckles
    for z in (z0, z1):  # top and bottom runs
        cyl(body, r, w, (0, 0, z), mat, sides=10, rot=ALONG_X)
    for sx in (-1, 1):  # feet and connection stubs
        cube(body, (0.2, 0.3, z0 - r * 0.5), (sx * w * 0.3, 0, (z0 - r * 0.5) / 2), "M_RobotDark", bevel=0.02)
        cyl(body, r, 0.4, (sx * (w / 2 + 0.2), 0, z0), mat, sides=10, rot=ALONG_X)
        _flange(body, r, sx * (w / 2 + 0.36), z0)
    # heat exchanger on the supply riser: finned block around the pipe
    ez, eh = (z0 + z1) / 2, min(0.9, (z1 - z0) * 0.6)
    cube(body, (r * 4, r * 4, eh), (-w / 2, 0, ez), "M_RobotDark", bevel=0.02)
    for k in range(5):
        cube(body, (r * 4.6, r * 4.6, 0.02), (-w / 2, 0, ez - eh / 2 + 0.08 + k * (eh - 0.16) / 4), "M_Metal")
    for z in (ez - eh / 2 - 0.1, ez + eh / 2 + 0.1):
        cyl(lights, r * 1.08, 0.05, (-w / 2, 0, z), glow, sides=10)
    cyl(lights, r * 1.06, 0.06, (0, 0, z1), glow, sides=10, rot=ALONG_X)
    if pump:  # inline pump on the return riser
        pz = z0 + (z1 - z0) * 0.35
        cyl(body, r * 2.0, r * 2.4, (w / 2, 0, pz), p.material(["M_HazardOrange", "M_Wall"]), sides=10, bevel=0.02)
        cyl(body, r * 1.2, r * 2.2, (w / 2, -r * 2.0, pz), "M_RobotDark", sides=8, rot=ALONG_Y)
    if valve:  # service valve on the bottom run, wheel to the front
        cube(body, (r * 3, r * 2.6, r * 3), (w * 0.15, 0, z0), "M_RobotDark", bevel=0.02)
        cyl(body, 0.03, 0.18, (w * 0.15, -r * 1.3 - 0.09, z0), "M_Metal", sides=6, rot=ALONG_Y)
        valve_wheel(body, (w * 0.15, -r * 1.3 - 0.2, z0), radius=max(0.14, r * 1.4))
    a.meta.update({"width_m": round(w, 3), "radius": r, "state": state, "axis_height": round(z0, 3),
                   "ends_x": [round(-(w / 2 + 0.4), 3), round(w / 2 + 0.4, 3)]})


@model("pressure_tank", "PressureTank", "industrial", "Pressure vessel: lying on two saddles or standing on a skirt, "
       "dished heads, nozzles, relief valve, gauge window (Glow), warning band; outlet fits ``pipe``",
       params=[
           Param("orientation", "choice", "Lage", choices=("horizontal", "vertical")),
           Param("radius", "float", "Radius (m)", lo=0.3, hi=1.4, size=True, snap_factor=2),
           Param("length", "float", "Mantellänge (m)", lo=1.0, hi=5.0, size=True),
           Param("relief_valve", "bool", "Sicherheitsventil"),
           Param("warning_band", "bool", "Warnband"),
           _status_param(),
       ])
def pressure_tank(rng, a):
    p = a.p
    orient = p.choice("orientation", ["horizontal", "horizontal", "vertical"])
    r = p.float("radius", 0.45, 0.9)
    ln = p.float("length", 1.6, 3.0)
    mat = p.material(["M_Wall", "M_Metal", "M_Platform"])
    relief = p.bool("relief_valve", 0.7)
    band = p.bool("warning_band", 0.5, warning=True)
    status = STATUS[p.option("status")]
    body, lights = a.part("Body"), a.part("Glow")
    sides = 12
    a.meta.update({"orientation": orient, "radius": round(r, 3), "length_m": round(ln, 3)})
    if orient == "horizontal":
        z = r + 0.3
        cyl(body, r, ln, (0, 0, z), mat, sides=sides, rot=ALONG_X)
        head = 0.0
        for sx in (-1, 1):
            head = _dome(body, r, (sx * ln / 2, 0, z), ("+" if sx > 0 else "-") + "x", mat)
            cyl(body, r * 1.02, 0.05, (sx * (ln / 2 - 0.05), 0, z), "M_RobotDark", sides=sides, rot=ALONG_X)  # seam
            sx_pos = sx * ln * 0.3
            cube(body, (0.25, r * 1.6, z - r * 0.4), (sx_pos, 0, (z - r * 0.4) / 2), "M_RobotDark", bevel=0.02)
            cube(body, (0.4, r * 1.9, 0.05), (sx_pos, 0, 0.025), "M_Metal")
        if band:
            cyl(body, r * 1.01, 0.12, (0, 0, z), "M_Warning", sides=sides, rot=ALONG_X)
        top = (ln * 0.15, 0, z + r)
        out_x = -(ln / 2 + head + 0.3)
        cyl(body, 0.09, 0.3 + head * 0.4, (-(ln / 2 + head * 0.8) - 0.15, 0, z), "M_Metal", sides=8, rot=ALONG_X)
        _flange(body, 0.09, out_x + 0.04, z, sides=8)
        a.meta["outlet"] = [round(out_x, 4), 0.0, round(z, 4)]
        gauge = (-ln * 0.25, -r * 0.98, z + r * 0.15)
    else:
        z0 = 0.35
        cyl(body, r * 0.92, z0, (0, 0, z0 / 2), "M_RobotDark", sides=sides)  # skirt
        _dome(body, r, (0, 0, z0 + 0.0), "-z", mat)
        cyl(body, r, ln, (0, 0, z0 + ln / 2), mat, sides=sides)
        head = _dome(body, r, (0, 0, z0 + ln), "+z", mat)
        if band:
            cyl(body, r * 1.01, 0.12, (0, 0, z0 + ln * 0.7), "M_Warning", sides=sides)
        top = (0, 0, z0 + ln + head)
        oz = z0 + 0.45
        cyl(body, 0.09, 0.45, (r + 0.15, 0, oz), "M_Metal", sides=8, rot=ALONG_X)
        _flange(body, 0.09, r + 0.33, oz, sides=8)
        a.meta["outlet"] = [round(r + 0.37, 4), 0.0, round(oz, 4)]
        gauge = (0, -r * 0.98, z0 + ln * 0.45)
    # top nozzle with blind flange, relief valve, gauge window
    tx, ty, tz = top
    cyl(body, r * 0.14, 0.22, (tx, ty, tz + 0.08), "M_Metal", sides=8)
    cyl(body, r * 0.2, 0.05, (tx, ty, tz + 0.2), "M_RobotDark", sides=8)
    if relief:
        cyl(body, 0.05, 0.18, (tx + r * 0.35, ty, tz + 0.03), "M_Metal", sides=6)
        cyl(body, 0.08, 0.1, (tx + r * 0.35, ty, tz + 0.15), "M_HazardOrange", sides=8)
    gx, gy, gz = gauge
    cyl(body, 0.11, 0.06, (gx, gy - 0.02, gz), "M_RobotDark", sides=10, rot=ALONG_Y)
    cyl(lights, 0.08, 0.02, (gx, gy - 0.055, gz), status, sides=10, rot=ALONG_Y)


@model("turbine", "Turbine", "industrial", "Turbine on a skid: intake bell with a rotor (Rotor), ribbed casing, "
       "exhaust duct up or back, gearbox and control box; option ``machine`` adds Machine + Rotator",
       params=[
           Param("radius", "float", "Gehäuse-Radius (m)", lo=0.3, hi=1.2, size=True, snap_factor=2),
           Param("length", "float", "Gehäuselänge (m)", lo=1.2, hi=4.0, size=True),
           Param("exhaust", "choice", "Abgas", choices=("up", "back")),
           Param("guard", "bool", "Ansauggitter"),
           _status_param(),
           Param("machine", "bool", "Machine-Script (Status, Rotor dreht im Betrieb)", default=False, quiet=True,
                 description="Gameplay-Export; ohne bleibt die Turbine ein statisches Modell mit genauer Kollision"),
           Param("rotor_speed", "float", "Rotor-Tempo (°/s)", lo=0, hi=3000, unity=True, default=900, quiet=True,
                 description="Nur mit machine"),
       ])
def turbine(rng, a):
    p = a.p
    r = p.float("radius", 0.45, 0.8)
    ln = p.float("length", 1.8, 2.8)
    exhaust = p.choice("exhaust", ["up", "back"])
    guard = p.bool("guard", 0.6)
    mat = p.material(["M_Wall", "M_Metal", "M_HazardOrange"])
    blades = rng.choice([6, 8, 10])
    status = STATUS[p.option("status")]
    body, lights = a.part("Body"), a.part("Glow")
    z = r * 1.25 + 0.35
    x0 = -ln / 2
    total = ln + r * 1.4
    cube(body, (total + 0.4, r * 2.6, 0.15), (r * 0.4, 0, 0.075), "M_RobotDark", bevel=0.02)  # skid
    for sx in (-0.3, 0.3):  # pedestals
        cube(body, (0.3, r * 1.4, z - r * 0.7), (sx * ln, 0, 0.15 + (z - r * 0.7 - 0.15) / 2), "M_RobotDark")
    cyl(body, r, ln, (0, 0, z), mat, sides=12, rot=ALONG_X)
    for k in range(4):  # ribs
        cyl(body, r * 1.06, 0.06, (x0 + ln * (k + 0.5) / 4, 0, z), "M_RobotDark", sides=12, rot=ALONG_X)
    cube(body, (ln, r * 2.14, 0.05), (0, 0, z), "M_RobotDark")  # horizontal split flange
    # intake bell at the front end (-X), opening towards -X
    cyl(body, r, r * 0.5, (x0 - r * 0.25, 0, z), "M_RobotDark", sides=12, radius_top=r * 1.25, rot=(0, -math.pi / 2, 0))
    center = (x0 - r * 0.45, 0.0, z)
    rotor = a.part("Rotor", pivot=center)
    cyl(rotor, r * 0.25, r * 0.3, center, "M_Metal", sides=8, rot=ALONG_X)
    for i in range(blades):
        ang = 2 * math.pi * i / blades
        cube(rotor, (0.03, r * 0.75, r * 0.18), (center[0], math.cos(ang) * r * 0.55, z + math.sin(ang) * r * 0.55),
             "M_Platform", rot=(ang + deg(20), 0, 0))
    if guard:
        for k in range(-2, 3):
            half = math.sqrt(max(0.0, (r * 1.2) ** 2 - (k * r * 0.45) ** 2))
            cube(body, (0.02, 0.02, 2 * half), (x0 - r * 0.62, k * r * 0.45, z), "M_Metal")
    # exhaust at the back end (+X)
    x1 = ln / 2
    cyl(body, r, r * 0.6, (x1 + r * 0.3, 0, z), mat, sides=12, radius_top=r * 0.7, rot=(0, math.pi / 2, 0))
    if exhaust == "up":
        body.add(sphere(r * 0.72, 12, 4, "M_RobotDark"), loc=(x1 + r * 0.75, 0, z))
        cyl(body, r * 0.7, r * 1.6, (x1 + r * 0.75, 0, z + r * 0.8), "M_RobotDark", sides=12)
        cyl(body, r * 0.8, 0.08, (x1 + r * 0.75, 0, z + r * 1.6), "M_Metal", sides=12)
    else:
        cyl(body, r * 0.7, r * 0.9, (x1 + r * 1.05, 0, z), "M_RobotDark", sides=12, rot=ALONG_X)
        cyl(body, r * 0.8, 0.08, (x1 + r * 1.5, 0, z), "M_Metal", sides=12, rot=ALONG_X)
    # control box on the front side
    cube(body, (0.5, 0.25, 0.6), (0, -r * 1.35, 0.15 + 0.3 + 0.05), "M_RobotDark", bevel=0.02)
    cube(lights, (0.3, 0.02, 0.1), (0, -r * 1.35 - 0.13, 0.15 + 0.6), status)
    a.meta.update({"radius": round(r, 3), "length_m": round(ln, 3), "exhaust": exhaust, "axis_height": round(z, 3)})
    if p.option("machine"):
        a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "right", "speed": p.option("rotor_speed")},
                    note="enabled by Machine while it runs")
        a.behaviour("Machine", {"body": "Body", "glow": "Glow", "rotor": "Rotor"}, {"needsPower": False},
                    note="Glow: M_GlowRed off / M_GlowCyan running / M_GlowOrange broken")


@model("compressor", "Compressor", "industrial", "Air compressor on a skid: finned motor, belt guard, crankcase "
       "with 1-3 finned cylinder heads, intake filters, optional air receiver; option ``machine`` adds Machine",
       params=[
           Param("size", "float", "Größe (Motor-Radius, m)", lo=0.12, hi=0.45, size=True),
           Param("heads", "int", "Zylinderköpfe", lo=1, hi=3),
           Param("receiver", "bool", "Druckluftbehälter"),
           _status_param(),
           Param("machine", "bool", "Machine-Script (Status)", default=False, quiet=True,
                 description="Gameplay-Export; ohne bleibt der Kompressor ein statisches Modell mit genauer Kollision"),
       ])
def compressor(rng, a):
    p = a.p
    r = p.float("size", 0.18, 0.3)
    heads = p.int("heads", 1, 3)
    receiver = p.bool("receiver", 0.7)
    mat = p.material(["M_HazardOrange", "M_Wall", "M_RobotBody"])
    status = STATUS[p.option("status")]
    body, lights = a.part("Body"), a.part("Glow")
    ml = r * 2.6
    cw = max(0.45, heads * r * 1.6 + 0.2)
    length = ml + 0.35 + cw
    depth = r * 3.0 + (r * 3.2 if receiver else 0.0)
    yb = r * 1.6 if receiver else 0.0  # machine row moves to the front when a receiver stands behind
    z = r + 0.2
    cube(body, (length + 0.2, depth + 0.2, 0.12), (0, yb / 2 - (r * 0.8 if receiver else 0), 0.06), "M_RobotDark",
         bevel=0.02)
    yf = -yb / 2
    xm = -length / 2 + ml / 2
    cyl(body, r, ml, (xm, yf, z + 0.06), mat, sides=10, bevel=0.02, rot=ALONG_X)
    for i in range(int(ml / 0.07)):
        cyl(body, r * 1.12, 0.015, (xm - ml / 2 + 0.05 + i * 0.07, yf, z + 0.06), mat, sides=10, rot=ALONG_X)
    cube(body, (0.12, r * 2.2, r * 2.8), (xm + ml / 2 + 0.1, yf, z + 0.2), "M_Warning", bevel=0.02)  # belt guard
    xc = xm + ml / 2 + 0.2 + cw / 2
    ch = r * 1.8
    cube(body, (cw, r * 2.2, ch), (xc, yf, 0.12 + ch / 2), "M_RobotDark", bevel=0.03)  # crankcase
    for i in range(heads):
        hx = xc - cw / 2 + 0.1 + r * 0.8 + i * r * 1.6
        hz = 0.12 + ch
        cyl(body, r * 0.6, r * 1.2, (hx, yf, hz + r * 0.6), "M_Metal", sides=8)
        for k in range(4):  # cooling fins
            cyl(body, r * 0.78, 0.02, (hx, yf, hz + 0.08 + k * r * 0.28), "M_Metal", sides=8)
        cube(body, (r * 1.1, r * 1.1, 0.08), (hx, yf, hz + r * 1.24), "M_RobotDark")
        cyl(body, r * 0.35, r * 0.4, (hx, yf - r * 0.2, hz + r * 1.48), "M_RobotDark", sides=8)  # intake filter
    cube(lights, (0.12, 0.02, 0.05), (xc + cw * 0.3, yf - r * 1.1 - 0.01, 0.12 + ch * 0.7), status)
    if receiver:
        rr, rl = r * 1.3, length * 0.75
        rz = rr + 0.25
        yr = yf + r * 1.1 + 0.15 + rr
        cyl(body, rr, rl, (0, yr, rz), p.material(["M_Wall", "M_Metal"]), sides=10, rot=ALONG_X)
        for sx in (-1, 1):
            _dome(body, rr, (sx * rl / 2, yr, rz), ("+" if sx > 0 else "-") + "x", "M_Wall", sides=10)
            cube(body, (0.15, rr * 1.4, rz - rr * 0.5), (sx * rl * 0.3, yr, 0.12 + (rz - rr * 0.5 - 0.12) / 2),
                 "M_RobotDark")
        # discharge line from the heads into the receiver
        strut(body, (xc, yf, 0.12 + ch + r * 0.4), (xc, yr - rr * 0.5, rz + rr * 0.6), 0.03, "M_Metal")
        cyl(body, 0.09, 0.3, (rl / 2 + rr * 0.44 + 0.15, yr, rz), "M_Metal", sides=8, rot=ALONG_X)
        _flange(body, 0.09, rl / 2 + rr * 0.44 + 0.27, rz, sides=8)
        a.meta["outlet"] = [round(rl / 2 + rr * 0.44 + 0.31, 4), round(yr, 4), round(rz, 4)]
        cyl(body, 0.08, 0.05, (-rl * 0.2, yr - rr - 0.02, rz + rr * 0.3), "M_RobotDark", sides=10, rot=ALONG_Y)
        cyl(lights, 0.06, 0.02, (-rl * 0.2, yr - rr - 0.05, rz + rr * 0.3), status, sides=10, rot=ALONG_Y)
    a.meta.update({"heads": heads, "receiver": receiver})
    if p.option("machine"):
        a.behaviour("Machine", {"body": "Body", "glow": "Glow"}, {"needsPower": True},
                    note="Glow: M_GlowRed off / M_GlowCyan running / M_GlowOrange broken")


# --------------------------------------------------------------------------
# technology and electrics
# --------------------------------------------------------------------------

@model("relay_box", "RelayBox", "industrial", "Wall relay / breaker box (back at y = +0.1): relay rows with status "
       "LEDs (Glow), breaker toggles, main switch, louvres, cable conduits up to the ceiling", pivot="wall",
       params=[
           Param("style", "choice", "Bauform", choices=("box", "tall")),
           Param("rows", "int", "Relaisreihen", lo=1, hi=4),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.8, hi=2.2),
           Param("conduits", "bool", "Kabelrohre nach oben"),
           Param("warning", "bool", "Warnschild"),
           _status_param(),
       ])
def relay_box(rng, a):
    p = a.p
    style = p.choice("style", ["box", "box", "tall"])
    rows = p.int("rows", 2, 3)
    w, d = rng.uniform(0.7, 1.0), rng.uniform(0.22, 0.3)
    h = max(0.6, rows * 0.22 + 0.3) if style == "box" else max(1.1, rows * 0.3 + 0.4)
    z = p.value("mount_height", rng.uniform(1.2, 1.5))
    z = max(z, h / 2 + 0.15)  # wall-hung: never on the floor
    conduits = p.bool("conduits", 0.7)
    warn = p.bool("warning", 0.6, warning=True)
    status = STATUS[p.option("status")]
    body, glow, lights = a.part("Body"), a.part("Glow"), a.part("Lights")
    mat = p.material(["M_Wall", "M_RobotDark", "M_Metal"])
    yf = 0.1 - d
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), mat, bevel=0.03)
    cube(body, (w - 0.1, 0.02, h - 0.14), (0, yf - 0.005, z), "M_RobotDark")  # front panel
    top = z + h / 2 - 0.12
    for k in range(rows):
        rz = top - 0.14 - k * ((h - 0.4) / max(1, rows))
        n = max(3, int((w - 0.3) / 0.11))
        for i in range(n):
            x = -w / 2 + 0.15 + i * (w - 0.3) / (n - 1)
            cube(body, (0.08, 0.05, 0.12), (x, yf - 0.035, rz), "M_Platform", bevel=0.005)  # relay module
            cube(glow if i % 2 == 0 else lights, (0.03, 0.02, 0.02), (x, yf - 0.065, rz + 0.04),
                 status if i % 2 == 0 else "M_GlowOrange")
            cube(body, (0.02, 0.04, 0.035), (x, yf - 0.06, rz - 0.03), "M_Metal")  # toggle
        cube(body, (w - 0.2, 0.03, 0.025), (0, yf - 0.02, rz - 0.085), "M_Metal")  # DIN rail
    # main switch on the right, louvres on top
    cyl(body, 0.07, 0.05, (w / 2 - 0.12, yf - 0.03, z - h / 2 + 0.16), "M_RobotDark", sides=8, rot=ALONG_Y)
    cube(body, (0.05, 0.04, 0.16), (w / 2 - 0.12, yf - 0.065, z - h / 2 + 0.16), "M_HazardOrange")
    for k in range(3):
        cube(body, (w * 0.5, 0.03, 0.02), (-w * 0.1, yf - 0.015, z + h / 2 - 0.05 - k * 0.035), "M_RobotDark")
    if warn:
        cube(body, (0.14, 0.012, 0.12), (-w / 2 + 0.14, yf - 0.012, z - h / 2 + 0.14), "M_Warning", rot=(0, deg(45), 0))
    if conduits:  # up the wall to the ceiling (3 m wall height)
        run = max(0.3, 3.0 - (z + h / 2))
        for x in (-w * 0.3, 0.0, w * 0.3):
            cyl(body, 0.035, run, (x, 0.02, z + h / 2 + run / 2), "M_Metal", sides=6)
    a.meta.update({"style": style, "rows": rows})


@model("diagnostics_port", "DiagnosticsPort", "tech", "Wall diagnostics port (back at y = +0.1): recessed plate, "
       "round multi-pin socket (Slot), data port, small screen (Screen), LED bar (Glow), hinged cover (Cover), "
       "optional service cable on a hook", pivot="wall",
       params=[
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.3, hi=2.0),
           Param("cover", "choice", "Klappe", choices=("open", "closed", "none")),
           Param("screen", "bool", "Bildschirm"),
           Param("cable", "bool", "Servicekabel am Haken"),
           _status_param(),
       ])
def diagnostics_port(rng, a):
    p = a.p
    w, h = rng.uniform(0.34, 0.48), rng.uniform(0.3, 0.42)
    z = p.value("mount_height", rng.uniform(0.6, 1.1))
    z = max(z, h / 2 + 0.05)
    cover = p.choice("cover", ["open", "open", "closed", "none"])
    screen = p.bool("screen", 0.6)
    cable = p.bool("cable", 0.5)
    status = STATUS[p.option("status")]
    glow = p.glow(weights=(0.85, 0.05, 0.1))
    body, lights, extra = a.part("Body"), a.part("Glow"), a.part("Lights")
    d = 0.07
    yf = 0.1 - d
    cube(body, (w + 0.08, d, h + 0.08), (0, 0.1 - d / 2, z), p.material(["M_RobotDark", "M_Wall", "M_Metal"]),
         bevel=0.015)
    cube(body, (w - 0.02, 0.02, h - 0.02), (0, yf - 0.005, z), "M_Ground")  # recess
    sx, sz = -w * 0.18, z - h * 0.05
    cyl(body, 0.075, 0.05, (sx, yf - 0.03, sz), "M_Metal", sides=10, rot=ALONG_Y)  # socket collar
    cyl(body, 0.055, 0.02, (sx, yf - 0.06, sz), "M_RobotDark", sides=10, rot=ALONG_Y)
    for k in range(5):  # pins
        ang = 2 * math.pi * k / 5
        cube(body, (0.012, 0.02, 0.012), (sx + math.cos(ang) * 0.03, yf - 0.07, sz + math.sin(ang) * 0.03), "M_Platform")
    a.empty("Slot", (sx, yf - 0.08, sz))
    cube(body, (0.1, 0.03, 0.04), (w * 0.22, yf - 0.02, sz - 0.04), "M_Metal")  # data port
    cube(body, (0.07, 0.01, 0.015), (w * 0.22, yf - 0.036, sz - 0.04), "M_RobotDark")
    if screen:
        cube(a.part("Screen"), (w * 0.4, 0.015, h * 0.2), (w * 0.15, yf - 0.01, z + h * 0.28), glow)
    for k in range(4):
        cube(lights if k < 2 else extra, (0.03, 0.015, 0.015), (-w / 2 + 0.06 + k * 0.045, yf - 0.01, z + h * 0.32),
             status if k < 2 else "M_GlowOrange")
    if cover != "none":
        hinge = (0.0, yf - 0.065, z + h / 2 + 0.02)
        lid = a.part("Cover", pivot=hinge)
        open_ang = deg(-105) if cover == "open" else 0.0

        def turned(v):
            c, s = math.cos(open_ang), math.sin(open_ang)
            dy, dz = v[1] - hinge[1], v[2] - hinge[2]
            return (v[0], hinge[1] + dy * c - dz * s, hinge[2] + dy * s + dz * c)

        cube(lid, (w + 0.06, 0.025, h + 0.04), turned((0, yf - 0.065, z + 0.01)), "M_Metal", bevel=0.008,
             rot=(open_ang, 0, 0))
        cube(lid, (0.1, 0.02, 0.03), turned((0, yf - 0.085, z - h / 2 + 0.03)), "M_RobotDark", rot=(open_ang, 0, 0))
        for x in (-w * 0.3, w * 0.3):
            cyl(body, 0.012, 0.06, (x, yf - 0.065, z + h / 2 + 0.02), "M_Metal", sides=6, rot=ALONG_X)
    if cable:  # service cable hanging from a hook beside the port
        hx = w / 2 + 0.14
        cube(body, (0.04, 0.12, 0.04), (hx, 0.04, z + 0.05), "M_Metal")
        top = (hx, -0.03, z + 0.05)
        last = top
        for k in range(1, 4):
            pt = (hx + (0.05 if k % 2 else -0.05), -0.04, z + 0.05 - k * 0.12)
            strut(body, last, pt, 0.012, "M_HazardOrange")
            last = pt
        cube(body, (0.05, 0.05, 0.09), (last[0], last[1], last[2] - 0.05), "M_RobotDark")
    a.meta.update({"cover": cover})


@model("warning_beacon", "WarningBeacon", "tech", "Warning beacon / signal tower on a pole or a heavy base: stacked "
       "light tiers, the top one is the signal (Glow), optional horn; option ``signal`` adds SignalLight",
       params=[
           Param("mount", "choice", "Montage", choices=("pole", "base")),
           Param("tiers", "int", "Leuchtstufen", lo=1, hi=4),
           Param("height", "float", "Höhe (m)", lo=0.4, hi=3.0, size=True),
           Param("horn", "bool", "Signalhorn"),
           Param("signal", "bool", "SignalLight-Script", default=False, quiet=True,
                 description="Gameplay-Export; ohne bleibt die Leuchte ein statisches Modell"),
           Param("mode", "choice", "Modus", choices=("Steady", "Blink", "Pulse"), unity=True, default="Blink", quiet=True,
                 description="Nur mit signal"),
       ])
def warning_beacon(rng, a):
    p = a.p
    mount = p.choice("mount", ["pole", "pole", "base"])
    tiers = p.int("tiers", 2, 3)
    height = p.float("height", 1.4, 2.2)
    horn = p.bool("horn", 0.4)
    body, glow, lights = a.part("Body"), a.part("Glow"), a.part("Lights")
    r = 0.075 if mount == "pole" else 0.11
    if mount == "pole":
        cyl(body, 0.22, 0.06, (0, 0, 0.03), "M_RobotDark", sides=8, bevel=0.01)
        cyl(body, 0.035, height, (0, 0, 0.06 + height / 2), "M_Metal", sides=6)
        z0 = 0.06 + height
    else:
        height = min(height, 0.6)
        cube(body, (0.5, 0.5, 0.15), (0, 0, 0.075), "M_RobotDark", bevel=0.03)
        cyl(body, 0.06, height, (0, 0, 0.15 + height / 2), "M_Metal", sides=6)
        stripes(body, 0.45, (0, -0.25, 0.08), count=4, width=0.02, height=0.1)
        z0 = 0.15 + height
    cyl(body, r * 1.15, 0.05, (0, 0, z0 + 0.025), "M_RobotDark", sides=10)
    z = z0 + 0.05
    colors = ["M_GlowCyan", "M_GlowOrange", "M_GlowCyan"][:tiers - 1] + ["M_GlowRed"]
    for k, mat in enumerate(colors):  # lower tiers are fixed colours, the top tier is the signal
        cyl(glow if k == len(colors) - 1 else lights, r, 0.1, (0, 0, z + 0.05), mat, sides=10)
        z += 0.1
        cyl(body, r * 1.08, 0.015, (0, 0, z + 0.0075), "M_RobotDark", sides=10)
        z += 0.015
    cyl(body, r * 0.9, 0.04, (0, 0, z + 0.02), "M_RobotDark", sides=10, radius_top=r * 0.5)
    pole_tower(a, body, r, z0 + 0.05, z, 0.035 if mount == "pole" else 0.06, mount)  # variety details (own stream)
    if horn:
        cyl(body, 0.045, 0.12, (r + 0.04, 0, z0 + 0.1), "M_RobotDark", sides=8, radius_top=0.09,
            rot=(0, math.pi / 2, 0))
    a.meta.update({"mount": mount, "tiers": tiers, "lamp_top_m": round(z + 0.04, 3)})
    if p.option("signal"):
        a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})


# --------------------------------------------------------------------------
# station props
# --------------------------------------------------------------------------

@model("emergency_case", "EmergencyCase", "props", "Wall emergency case (back at y = +0.1): red frame, glass door "
       "(Glass), extinguisher, axe or first aid inside, break-glass hammer and sign", pivot="wall",
       params=[
           Param("content", "choice", "Inhalt", choices=("extinguisher", "axe", "first_aid")),
           Param("mount_height", "float", "Unterkante über Boden (m)", lo=0.1, hi=1.6),
           Param("hammer", "bool", "Nothammer"),
           Param("label", "bool", "Schild NOTFALL"),
       ])
def emergency_case(rng, a):
    p = a.p
    content = p.choice("content", ["extinguisher", "extinguisher", "axe", "first_aid"])
    w, h, d = rng.uniform(0.45, 0.6), rng.uniform(0.75, 1.0), rng.uniform(0.22, 0.3)
    z0 = p.value("mount_height", rng.uniform(0.5, 0.9))
    hammer = p.bool("hammer", 0.6)
    label = p.bool("label", 0.6)
    frame = rng.choice(["M_HazardOrange", "M_HazardOrange", "M_Warning"])  # painted frame, never a light
    body = a.part("Body")
    zc = z0 + h / 2
    yb, yf = 0.1, 0.1 - d
    cube(body, (w, 0.03, h), (0, yb - 0.015, zc), "M_RobotDark")  # back
    for sx in (-1, 1):
        cube(body, (0.04, d, h), (sx * (w / 2 - 0.02), 0.1 - d / 2, zc), frame, bevel=0.008)
    for sz in (-1, 1):
        cube(body, (w, d, 0.04), (0, 0.1 - d / 2, zc + sz * (h / 2 - 0.02)), frame, bevel=0.008)
    cube(a.part("Glass"), (w - 0.08, 0.012, h - 0.08), (0, yf + 0.01, zc), "M_Glass")
    cube(body, (0.03, 0.03, 0.12), (w / 2 - 0.06, yf - 0.005, zc), "M_Metal")  # latch
    inner = a.part("Content")
    yi = 0.1 - d / 2 + 0.01
    if content == "extinguisher":
        cyl(inner, 0.08, h * 0.55, (0, yi, z0 + 0.06 + h * 0.275), "M_HazardOrange", sides=8)
        cyl(inner, 0.04, 0.08, (0, yi, z0 + 0.06 + h * 0.59), "M_RobotDark", sides=6)
        strut(inner, (0.03, yi, z0 + 0.06 + h * 0.6), (0.1, yi - 0.03, z0 + 0.06 + h * 0.3), 0.012, "M_RobotDark")
    elif content == "axe":
        cube(inner, (0.04, 0.03, h * 0.7), (0, yi, zc), "M_Wall")
        cube(inner, (0.2, 0.025, 0.12), (0.06, yi, zc + h * 0.3), "M_Metal")
    else:
        cube(inner, (w * 0.6, 0.1, h * 0.3), (0, yi, zc), "M_Platform", bevel=0.01)
        cube(inner, (0.12, 0.105, 0.04), (0, yi, zc), "M_GlowRed")
        cube(inner, (0.04, 0.106, 0.12), (0, yi, zc), "M_GlowRed")
    if hammer:  # small break-glass hammer on a chain beside the case
        cube(body, (0.03, 0.06, 0.03), (w / 2 + 0.06, 0.07, zc + 0.1), "M_Metal")
        cube(body, (0.025, 0.025, 0.16), (w / 2 + 0.06, 0.03, zc - 0.0), "M_HazardOrange")
        cube(body, (0.08, 0.04, 0.035), (w / 2 + 0.06, 0.03, zc - 0.09), "M_Metal")
    if label:
        text = "NOTFALL"
        th = min(0.07, (w - 0.08) / max(1.0, text_width(text, 1.0)))
        cube(body, (w, 0.02, th + 0.06), (0, yb - 0.01, z0 + h + th / 2 + 0.06), "M_Platform")
        add_text(body, text, (0, yb - 0.025, z0 + h + th / 2 + 0.06), th, 0.01, "M_HazardOrange")
    a.meta.update({"content": content})
