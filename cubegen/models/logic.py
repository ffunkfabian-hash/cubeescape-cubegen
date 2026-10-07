"""More puzzle pieces: a block to push onto the pressure plate, tone / colour sequence panel, water level puzzle,
colour filter for the laser, symbol plates, crane with magnet and a countdown display.

Wired to the game's existing scripts where they fit (``Rotatable`` for valves,
plates, filter and crane jib, ``SignalIndicator`` per sequence light,
``SignalLight`` for status glow and the countdown); what still needs a Unity
mechanic is in ``docs/UNITY_INTEGRATION.md``. Solutions are in ``meta``.
"""

from __future__ import annotations

import math

from ..geometry import prism
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, stripes, valve_wheel
from .lettering import add_text, check_text, text_width
from .registry import model

UPRIGHT = ((1, 0, 0), (0, 0, -1), (0, 1, 0))  # (x, z) polygon facing the front, extruded towards -y


# --------------------------------------------------------------------------
# push block
# --------------------------------------------------------------------------

@model("push_block", "PushBlock", "puzzle", "Heavy block to push onto a pressure plate: crate, metal block or stone "
       "with handles and grip edges (one box collider, weight in meta)", params=[
           Param("size", "float", "Kantenlänge (m)", lo=0.4, hi=2.0, size=True),
           Param("style", "choice", "Art", choices=("crate", "metal", "stone")),
           Param("handles", "bool", "Griffe"),
           Param("glow", "bool", "Glow-Markierung"),
       ])
def push_block(rng, a):
    p = a.p
    s = p.float("size", 0.8, 1.2)
    style = p.choice("style", ["crate", "metal", "stone"])
    body = a.part("Body")
    h = s * rng.uniform(0.75, 1.0)
    if style == "crate":
        cube(body, (s, s, h), (0, 0, h / 2), p.material(["M_HazardOrange", "M_Wall", "M_RobotDark"]), bevel=0.03)
        for x in (-1, 1):
            for y in (-1, 1):
                cube(body, (s * 0.12, s * 0.12, h + 0.01), (x * s * 0.45, y * s * 0.45, h / 2), "M_RobotDark")
        density = 600
    elif style == "metal":
        cube(body, (s, s, h), (0, 0, h / 2), "M_Metal", bevel=0.04)
        for z in (h * 0.25, h * 0.75):
            cube(body, (s + 0.02, s + 0.02, s * 0.06), (0, 0, z), "M_RobotDark")
        density = 2500
    else:
        cube(body, (s, s, h), (0, 0, h / 2), "M_Ground", bevel=0.06)
        for k in range(3):  # carved rings
            cube(body, (s * 0.6, 0.02, s * 0.05), (0, -s / 2 - 0.005, h * (0.3 + 0.2 * k)), "M_Wall")
        density = 2200
    if p.bool("handles", 0.6):
        for side in (-1, 1):
            cube(body, (s * 0.4, 0.04, 0.04), (0, side * (s / 2 + 0.06), h * 0.6), "M_Metal")
            for x in (-1, 1):
                cube(body, (0.04, 0.08, 0.04), (x * s * 0.18, side * (s / 2 + 0.03), h * 0.6), "M_Metal")
    if p.bool("glow", 0.4):
        lights = a.part("Glow")
        glow = p.glow()
        for side in (-1, 1):
            cube(lights, (s * 0.5, 0.015, 0.04), (0, side * (s / 2 + 0.008), h * 0.85), glow)
    a.collider((s, s, h), (0, 0, h / 2))
    a.meta.update({"style": style, "footprint_m": round(s, 3), "weight_kg": int(s * s * h * density * 0.3)})


# --------------------------------------------------------------------------
# tone / colour sequence panel
# --------------------------------------------------------------------------

SEQUENCE_COLOURS = ("M_GlowCyan", "M_GlowRed", "M_GlowOrange", "M_Crystal", "M_Warning", "M_HazardOrange")


@model("sequence_panel", "SequencePanel", "puzzle", "Wall panel for a tone and colour sequence (Simon): 4-6 "
       "coloured buttons (Button_<n>) with lights (Light_<n>), speaker grille; sequence and deferred indicators in "
       "meta", pivot="wall", params=[
           Param("buttons", "int", "Tasten", lo=3, hi=6),
           Param("length", "int", "Länge der Folge", lo=3, hi=10),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.8, hi=2.2),
           Param("layout", "choice", "Anordnung", choices=("grid", "row", "ring")),
       ])
def sequence_panel(rng, a):
    p = a.p
    n = p.int("buttons", 4, 6)
    length = p.int("length", 4, 7)
    z = p.value("mount_height", rng.uniform(1.2, 1.5))
    layout = p.choice("layout", ["grid", "row", "ring"])
    body = a.part("Body")
    bs = rng.uniform(0.14, 0.2)
    if layout == "row":
        pos = [((i - (n - 1) / 2) * bs * 1.5, 0.0) for i in range(n)]
    elif layout == "grid":
        cols = math.ceil(n / 2)
        pos = [((i % cols - (cols - 1) / 2) * bs * 1.5, (0.5 - i // cols) * bs * 1.5) for i in range(n)]
    else:
        pos = [(math.cos(math.pi / 2 - 2 * math.pi * i / n) * bs * 1.3, math.sin(math.pi / 2 - 2 * math.pi * i / n)
                * bs * 1.3) for i in range(n)]
    xs, zs = [x for x, _ in pos], [zz for _, zz in pos]
    w = max(xs) - min(xs) + bs * 2
    h = max(zs) - min(zs) + bs * 2 + 0.18
    z = max(z, h / 2 + 0.1)
    zc = z + 0.06
    cube(body, (w, 0.08, h), (0, 0.06, z), p.material(["M_RobotDark", "M_Wall"]), bevel=0.02)
    colours = SEQUENCE_COLOURS[:n] if n <= len(SEQUENCE_COLOURS) else SEQUENCE_COLOURS
    indicators = []
    for i, ((x, zz), colour) in enumerate(zip(pos, colours), 1):
        center = (x, -0.0, zc + zz)
        cube(body, (bs * 1.15, 0.03, bs * 1.15), (x, 0.01, zc + zz), "M_Metal")
        button = a.part(f"Button_{i}", pivot=center)
        cube(button, (bs, 0.05, bs), (x, -0.02, zc + zz), "M_RobotDark", bevel=0.01)
        cube(a.part(f"Light_{i}", parent=f"Button_{i}"), (bs * 0.8, 0.012, bs * 0.8), (x, -0.051, zc + zz), colour)
        a.behaviour("SignalIndicator", {"renderers": [f"Light_{i}"]}, {"offMaterial": "M_RobotDark",
                                                                       "onMaterial": colour},
                    note=f"button {i} lights up ({colour}); Button_{i} moves ~1.5 cm towards the wall when pressed")
        # The current Unity importer allows only one indicator on a prefab root.
        # Keep independent button recipes in the manifest until their adapter exists.
        indicators.append(a.behaviours.pop())
    grille = (0.0, 0.0, z - h / 2 + 0.09)
    for k in range(4):
        cube(body, (w * 0.4, 0.02, 0.012), (grille[0], 0.01, grille[2] - 0.03 + k * 0.02), "M_Ground")
    glow = a.part("Glow")
    cube(glow, (0.05, 0.02, 0.05), (w / 2 - 0.08, 0.01, z + h / 2 - 0.07), "M_GlowRed")
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Blink"}, note="status LED: blinks while the sequence plays")
    seq = a.sub("sequence")
    a.meta.update({"buttons": n, "layout": layout, "colours": list(colours[:n]),
                   "deferred_behaviours": indicators,
                   "sequence": [seq.randint(1, n) for _ in range(length)]})


# --------------------------------------------------------------------------
# water level puzzle
# --------------------------------------------------------------------------

@model("water_level", "WaterLevel", "puzzle", "Water level puzzle: 1-3 glass tubes with water columns (Fluid_<n>), "
       "scales, valve wheels (Wheel_<n>, Rotatable), pipes between the tubes; target levels in meta", params=[
           Param("tubes", "int", "Röhren", lo=1, hi=3),
           Param("height", "float", "Höhe (m)", lo=1.0, hi=3.0, size=True),
           Param("fluid", "choice", "Flüssigkeit", choices=("water", "glowing", "toxic")),
           Param("speed", "float", "Ventil-Tempo (°/s)", lo=10, hi=1000, unity=True, default=180),
       ])
def water_level(rng, a):
    p = a.p
    n = p.int("tubes", 2, 3)
    h = p.float("height", 1.4, 2.2)
    fluid = p.choice("fluid", ["water", "water", "glowing", "toxic"])
    fluid_mat = {"water": "M_Crystal", "glowing": "M_GlowCyan", "toxic": "M_GlowOrange"}[fluid]
    body, glass = a.part("Body"), a.part("Glass")
    r = rng.uniform(0.12, 0.2)
    gap = r * 3.2
    xs = [(i - (n - 1) / 2) * gap for i in range(n)]
    plinth = 0.2
    cube(body, (gap * n + 0.2, r * 3, plinth), (0, 0, plinth / 2), "M_RobotDark", bevel=0.02)
    targets, levels = [], []
    marks = a.sub("levels")
    cube(a.part("Glow"), (gap * n * 0.6, 0.02, 0.04), (0, -r * 1.5 - 0.005, plinth * 0.5), "M_GlowRed")
    for i, x in enumerate(xs, 1):
        top = plinth + h
        cyl(body, r * 1.25, 0.1, (x, 0, plinth + 0.05), "M_Metal", sides=10)
        cyl(body, r * 1.25, 0.1, (x, 0, top - 0.05), "M_Metal", sides=10)
        cyl(glass, r, h - 0.2, (x, 0, plinth + h / 2), "M_Glass", sides=10)
        level = marks.uniform(0.15, 0.6)
        target = marks.choice([0.25, 0.5, 0.75])
        levels.append(round(level, 3))
        targets.append(target)
        fz0, fh = plinth + 0.105, (h - 0.21) * level
        cyl(a.part(f"Fluid_{i}", pivot=(x, 0.0, fz0)), r * 0.9, fh, (x, 0, fz0 + fh / 2), fluid_mat, sides=10)
        for k in range(1, 4):  # scale marks on the front, the target in warning colour
            zz = fz0 + (h - 0.2) * k / 4
            cube(body, (r * 0.5 if k / 4 != target else r * 0.8, 0.02, 0.02), (x - r * 1.3, -r * 0.3, zz),
                 "M_Warning" if k / 4 == target else "M_Metal")
        center = (x, -r * 1.5 - 0.1, plinth + 0.45)
        cyl(body, 0.03, r * 1.5, (x, -r * 0.8, plinth + 0.45), "M_Metal", sides=6, rot=ALONG_Y)
        valve_wheel(a.part(f"Wheel_{i}", pivot=center), center, radius=min(0.14, r * 0.9))
        a.mesh_collider(f"Wheel_{i}", convex=True)
        a.behaviour("Rotatable", {"target": f"Wheel_{i}", "glow": "Glow"},
                    {"axis": "forward", "step": 90, "speed": p.option("speed"), "target": int(target * 4),
                     "interactive": True}, note=f"tube {i}: each step moves Fluid_{i} a quarter of the scale")
    for x1, x2 in zip(xs, xs[1:]):  # connecting pipe at the bottom
        cyl(body, 0.035, x2 - x1 - 2 * r, ((x1 + x2) / 2, r * 0.6, plinth + 0.15), "M_Metal", sides=6, rot=ALONG_X)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Steady"}, note="red until every level matches")
    a.collider((gap * n + 0.2, r * 3, plinth + h), (0, 0, (plinth + h) / 2))
    a.meta.update({"tubes": n, "fluid": fluid, "levels": levels, "targets": targets,
                   "column_m": round(h - 0.2, 3)})


# --------------------------------------------------------------------------
# colour filter for the laser
# --------------------------------------------------------------------------

FILTERS = {"red": "M_GlowRed", "cyan": "M_GlowCyan", "orange": "M_GlowOrange"}


@model("laser_filter", "LaserFilter", "puzzle", "Colour filter for the laser: tinted pane in a turnable holder "
       "(Filter, Rotatable around up in 90° steps), status glow", params=[
           Param("colour", "choice", "Farbe", choices=tuple(FILTERS)),
           Param("height", "float", "Strahlhöhe (m)", lo=0.3, hi=1.6),
           Param("panes", "choice", "Scheiben", choices=(1, 2)),
           Param("speed", "float", "Tempo (°/s)", lo=10, hi=1000, unity=True, default=180),
       ])
def laser_filter(rng, a):
    p = a.p
    colour = p.choice("colour", list(FILTERS))
    zb = p.value("height", rng.uniform(0.8, 1.1))
    panes = p.choice("panes", [1, 1, 2])
    body = a.part("Body")
    base = rng.uniform(0.35, 0.5)
    fw, fh = rng.uniform(0.25, 0.35), rng.uniform(0.25, 0.35)
    zb = max(zb, fh / 2 + 0.45)
    zc = zb - fh / 2 - 0.1  # hub of the turning holder
    cyl(body, base / 2, 0.08, (0, 0, 0.04), "M_RobotDark", sides=8, bevel=0.01)
    cyl(body, 0.04, zc - 0.11, (0, 0, 0.08 + (zc - 0.11) / 2), "M_Metal", sides=6)
    cyl(body, 0.08, 0.06, (0, 0, zc - 0.03), "M_RobotDark", sides=8)
    center = (0.0, 0.0, zc)
    holder = a.part("Filter", pivot=center)
    for k in range(panes):
        y = (k - (panes - 1) / 2) * 0.08
        for x in (-1, 1):
            cube(holder, (0.03, 0.05, fh + 0.06), (x * (fw / 2 + 0.015), y, zb), "M_Metal")
        for zz in (-1, 1):
            cube(holder, (fw + 0.06, 0.05, 0.03), (0, y, zb + zz * (fh / 2 + 0.015)), "M_Metal")
        cube(holder, (fw, 0.015, fh), (0, y, zb), FILTERS[colour])
    cube(holder, (0.06, 0.06, 0.1), (0, 0, zc + 0.05), "M_Metal")
    cube(a.part("Glow"), (0.04, 0.02, 0.04), (0, -base / 2 + 0.03, 0.1), "M_GlowRed")
    a.behaviour("Rotatable", {"target": "Filter", "glow": "Glow"},
                {"axis": "up", "step": 90, "speed": p.option("speed"), "target": 1, "interactive": True},
                note="turned into the beam (target 1) the laser takes the filter's colour")
    a.meta.update({"colour": colour, "beam_height_m": round(zb, 3), "panes": panes})


# --------------------------------------------------------------------------
# symbol plates
# --------------------------------------------------------------------------

def _symbol(kind, s):
    """(x, z) polygon of a symbol, about ``s`` across."""
    r = s / 2
    if kind == "circle":
        return [(math.cos(2 * math.pi * k / 12) * r, math.sin(2 * math.pi * k / 12) * r) for k in range(12)]
    if kind == "triangle":
        return [(-r, -r * 0.8), (r, -r * 0.8), (0.0, r)]
    if kind == "square":
        return [(-r * 0.8, -r * 0.8), (r * 0.8, -r * 0.8), (r * 0.8, r * 0.8), (-r * 0.8, r * 0.8)]
    if kind == "diamond":
        return [(0.0, -r), (r * 0.7, 0.0), (0.0, r), (-r * 0.7, 0.0)]
    if kind == "arrow":
        return [(-r * 0.25, -r), (r * 0.25, -r), (r * 0.25, 0.0), (r * 0.6, 0.0), (0.0, r), (-r * 0.6, 0.0),
                (-r * 0.25, 0.0)]
    pts = []  # star
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        ang = math.pi / 2 + math.pi * k / 5
        pts.append((math.cos(ang) * rr, math.sin(ang) * rr))
    return pts


SYMBOLS = ("circle", "triangle", "square", "diamond", "arrow", "star")


@model("symbol_plate", "SymbolPlate", "puzzle", "Wall panel with 3-5 turnable symbol plates (Plate_<n>, Rotatable "
       "around forward in 90° steps): turn every symbol upright; solution in meta", pivot="wall", params=[
           Param("plates", "int", "Platten", lo=2, hi=5),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.8, hi=2.2),
           Param("size", "float", "Plattengröße (m)", lo=0.15, hi=0.5, size=True),
           Param("speed", "float", "Tempo (°/s)", lo=10, hi=1000, unity=True, default=180),
       ])
def symbol_plate(rng, a):
    p = a.p
    n = p.int("plates", 3, 5)
    z = p.value("mount_height", rng.uniform(1.2, 1.5))
    s = p.float("size", 0.22, 0.32)
    body = a.part("Body")
    w = n * s * 1.35 + 0.1
    z = max(z, s / 2 + 0.2)
    cube(body, (w, 0.08, s + 0.24), (0, 0.06, z), p.material(["M_Wall", "M_RobotDark", "M_Metal"]), bevel=0.02)
    ink = p.material(["M_Warning", "M_HazardOrange", "M_Platform"])
    picks = a.sub("symbols")
    kinds = picks.sample(list(SYMBOLS), n)
    turns = [picks.randint(1, 3) for _ in range(n)]
    glow = a.part("Glow")
    cube(glow, (w * 0.5, 0.02, 0.03), (0, 0.01, z + s / 2 + 0.07), "M_GlowRed")
    for i, (kind, turn) in enumerate(zip(kinds, turns), 1):
        x = (i - (n + 1) / 2) * s * 1.35
        center = (x, -0.0, z)
        plate = a.part(f"Plate_{i}", pivot=center)
        cyl(plate, s / 2, 0.04, (x, -0.0, z), "M_RobotDark", sides=12, rot=ALONG_Y)
        ang = -math.pi / 2 * turn  # shown turned away from upright
        pts = [(x + px * math.cos(ang) - pz * math.sin(ang), z + px * math.sin(ang) + pz * math.cos(ang))
               for px, pz in _symbol(kind, s * 0.6)]
        plate.add(prism([(px - x, pz - z) for px, pz in pts], 0.012, ink), loc=(x, -0.026, z), basis=UPRIGHT)
        a.behaviour("Rotatable", {"target": f"Plate_{i}", "glow": "Glow"},
                    {"axis": "forward", "step": 90, "speed": p.option("speed"), "target": (4 - turn) % 4,
                     "interactive": True})
    a.meta.update({"plates": n, "symbols": kinds, "turned": turns})


# --------------------------------------------------------------------------
# crane with magnet
# --------------------------------------------------------------------------

@model("crane", "Crane", "puzzle", "Crane with a magnet: jib crane turning in 45° steps (Jib, Rotatable) or a "
       "gantry with a trolley; magnet glows when on (Glow)", params=[
           Param("style", "choice", "Bauform", choices=("jib", "gantry")),
           Param("height", "float", "Höhe (m)", lo=2.0, hi=5.0, size=True),
           Param("reach", "float", "Ausladung (m)", lo=1.0, hi=3.5, size=True),
           Param("speed", "float", "Tempo (°/s)", lo=5, hi=360, unity=True, default=45),
       ])
def crane(rng, a):
    p = a.p
    style = p.choice("style", ["jib", "jib", "gantry"])
    h = p.float("height", 2.6, 3.8)
    reach = p.float("reach", 1.5, 2.6)
    paint = p.material(["M_HazardOrange", "M_Warning", "M_Wall"])
    body = a.part("Body")
    a.meta["style"] = style
    if style == "jib":
        cube(body, (0.8, 0.8, 0.2), (0, 0, 0.1), "M_RobotDark", bevel=0.02)
        cyl(body, 0.12, h - 0.2, (0, 0, 0.2 + (h - 0.2) / 2), paint, sides=8)
        center = (0.0, 0.0, h)
        jib = a.part("Jib", pivot=center)
        cyl(jib, 0.16, 0.2, (0, 0, h), "M_RobotDark", sides=8)
        cube(jib, (reach + 0.4, 0.16, 0.2), ((reach - 0.4) / 2, 0, h + 0.18), paint)
        cube(jib, (0.4, 0.3, 0.3), (-0.4, 0, h + 0.2), "M_RobotDark", bevel=0.02)  # counterweight
        hook_x = reach * 0.9
        wiring = ("Rotatable", {"target": "Jib", "glow": "Glow"},
                  {"axis": "up", "step": 45, "speed": p.option("speed"), "target": 2, "interactive": True},
                  "the jib turns in 45 degree steps; the magnet hangs at meta.hook_m")
        mount = jib
        parent = "Jib"
    else:
        span = reach * 2
        for s in (-1, 1):
            for y in (-0.4, 0.4):
                cube(body, (0.1, 0.1, h), (s * span / 2, y, h / 2), paint)
            cube(body, (0.12, 1.0, 0.1), (s * span / 2, 0, 0.05), "M_RobotDark")
        cube(body, (span + 0.2, 0.2, 0.2), (0, -0.25, h + 0.1), paint)
        cube(body, (span + 0.2, 0.2, 0.2), (0, 0.25, h + 0.1), paint)
        hook_x = rng.uniform(-reach * 0.5, reach * 0.5)
        trolley = a.part("Trolley", pivot=(hook_x, 0.0, h))
        cube(trolley, (0.35, 0.7, 0.15), (hook_x, 0, h + 0.05), "M_RobotDark", bevel=0.02)
        wiring = ("SignalLight", {"glow": "Glow"}, {"mode": "Steady"},
                  f"the trolley travels along X between -{reach:.2f} and +{reach:.2f} m (Unity script)")
        mount = trolley
        parent = "Trolley"
    drop = h - rng.uniform(1.0, 1.6)
    cyl(mount, 0.012, h - drop - 0.25, (hook_x, 0, (h + drop + 0.25) / 2), "M_RobotDark", sides=6)
    cyl(mount, 0.25, 0.12, (hook_x, 0, drop + 0.2), "M_Metal", sides=10, bevel=0.01)
    cube(mount, (0.1, 0.1, 0.12), (hook_x, 0, drop + 0.32), "M_RobotDark")
    cyl(a.part("Glow", parent=parent), 0.2, 0.03, (hook_x, 0, drop + 0.13), "M_GlowCyan", sides=10)
    a.behaviour(wiring[0], wiring[1], wiring[2], note=wiring[3])
    a.meta.update({"hook_m": [round(hook_x, 3), round(drop, 3)], "reach_m": round(reach, 3)})


# --------------------------------------------------------------------------
# countdown display
# --------------------------------------------------------------------------

@model("countdown", "Countdown", "puzzle", "Countdown display on the wall: glowing MM:SS digits (Glow, "
       "SignalLight), frame, warning stripes, optional caption", pivot="wall", params=[
           Param("minutes", "int", "Minuten", lo=0, hi=99),
           Param("seconds", "int", "Sekunden", lo=0, hi=59),
           Param("digit_height", "float", "Ziffernhöhe (m)", lo=0.08, hi=0.6, size=True),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=1.0, hi=3.5),
           Param("mode", "choice", "Modus", choices=("Steady", "Blink", "Pulse"), unity=True, default="Blink"),
           Param("stripes", "bool", "Warnstreifen"),
           Param("text", "text", "Beschriftung", quiet=True,
                 description="Zeile über der Anzeige, z. B. EVAKUIERUNG (bis 16 Zeichen)"),
       ])
def countdown(rng, a):
    p = a.p
    minutes = p.int("minutes", 1, 15)
    seconds = p.choice("seconds", [0, 0, 0, 30, 15, 45])
    dh = p.float("digit_height", 0.15, 0.3)
    z = p.value("mount_height", rng.uniform(1.8, 2.4))
    body = a.part("Body")
    shown = f"{minutes:02d}:{seconds:02d}"
    tw = text_width(shown, dh)
    w, h = tw + dh * 0.8, dh * 1.8
    caption = p.option("text")
    if caption:
        caption = check_text(caption, max_len=16)
        cw = text_width(caption, dh * 0.4)
        w = max(w, cw + dh * 0.6)
        h += dh * 0.7
    z = max(z, h / 2 + 0.1)
    cube(body, (w, 0.1, h), (0, 0.05, z), "M_RobotDark", bevel=0.02)
    zd = z - (dh * 0.35 if caption else 0.0)
    cube(body, (tw + dh * 0.4, 0.02, dh * 1.4), (0, -0.005, zd), "M_Ground")
    glow = p.glow_from(["M_GlowRed", "M_GlowRed", "M_GlowOrange"])
    add_text(a.part("Glow"), shown, (0, -0.015, zd), dh, 0.012, glow)
    if caption:
        add_text(body, caption, (0, -0.0, z + h / 2 - dh * 0.45), dh * 0.4, 0.012, "M_Warning")
    if p.bool("stripes", 0.5, warning=True):
        stripes(body, w * 0.9, (0, -0.005, z - h / 2 + 0.03), count=max(4, int(w * 8)), width=0.01, height=0.04)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="the digits are geometry (meta.time); Unity can swap them for a TextMesh countdown")
    a.meta.update({"time": shown, "seconds_total": minutes * 60 + seconds, **({"text": caption} if caption else {})})
