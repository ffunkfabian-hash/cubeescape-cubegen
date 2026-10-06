"""More puzzles: combination lock, sliding puzzle, balance scale, frequency dial and switch panel.

All use ``Rotatable`` (turn in steps, ``target`` = solution) or carry the parts
for a new mechanic. New moving parts (pivot on their axis / hinge):

* ``Dial_<n>`` - number rings / knobs (``Rotatable``)
* ``Tile_<n>`` - sliding tiles, moved by one ``pitch`` per step (layout in ``meta``)
* ``Beam`` with ``Pan_A`` / ``Pan_B`` (children) - balance beam, ``Slot_A`` / ``Slot_B`` on the pans
* ``Switch_<n>`` - toggle switches (``Rotatable``, two positions)
"""

from __future__ import annotations

import math

from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, strut
from .registry import model

STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}


def _status_param():
    return Param("status", "choice", "Glow-Startzustand", choices=("off", "on"), default="off",
                 description="Status-Glow beim Export: off = M_GlowRed, on = M_GlowCyan (Unity schaltet ihn um)")


def _mount(p, rng, lo, hi, half_height):
    """Mount height of a wall piece: rolled, overridable, never below the floor."""
    return max(p.value("mount_height", rng.uniform(lo, hi)), half_height + 0.05)


def _indicator(a, note=""):
    a.behaviour("SignalIndicator", {"renderers": ["Glow"]}, {"offMaterial": "M_GlowRed", "onMaterial": "M_GlowCyan"},
                note=note)


# --------------------------------------------------------------------------
# combination lock
# --------------------------------------------------------------------------

@model("combination_lock", "CombinationLock", "puzzle", "Wall combination lock: 3-5 number rings (Dial_<n>, "
       "Rotatable, 10 digits), handle, status glow", pivot="wall", params=[
           Param("dials", "int", "Zahlenringe", lo=3, hi=5),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.6, hi=2.2),
           _status_param(),
       ])
def combination_lock(rng, a):
    p = a.p
    n = p.int("dials", 3, 4)
    r, ring_w = rng.uniform(0.045, 0.06), rng.uniform(0.04, 0.055)
    w, h, d = n * (ring_w + 0.012) + 0.16, r * 2 + 0.14, 0.08
    z = _mount(p, rng, 1.1, 1.4, h / 2)
    yf = 0.1 - d
    body, glow = a.part("Body"), a.part("Glow")
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_RobotDark", "M_Metal", "M_HazardOrange"]), bevel=0.012)
    cube(body, (w - 0.08, 0.02, r * 1.2), (0, yf - 0.01, z), "M_Ground")  # window over the rings
    for sx in (-1, 1):  # bearing blocks left / right of the rings
        cube(body, (0.03, 0.05, r * 2.2), (sx * (w / 2 - 0.06), yf - 0.02, z), "M_Metal")
    cube(body, (0.08, 0.04, 0.03), (0, yf - 0.015, z - h / 2 + 0.03), "M_Metal")  # pull handle below
    cube(glow, (0.04, 0.02, 0.02), (w / 2 - 0.035, yf - 0.01, z + h / 2 - 0.025), STATUS[p.option("status")])
    code = [rng.randint(0, 9) for _ in range(n)]
    for i in range(n):
        x = -w / 2 + 0.08 + ring_w / 2 + 0.006 + i * (ring_w + 0.012)
        center = (x, yf - r * 0.4, z)
        ring = a.part(f"Dial_{i + 1}", pivot=center)
        cyl(ring, r, ring_w, center, "M_Metal", sides=10, rot=ALONG_X)
        for k in range(10):  # digit marks: one notch per face, longer every fifth
            ang = 2 * math.pi * k / 10
            pos = (x, center[1] - math.cos(ang) * r * 1.0, z + math.sin(ang) * r * 1.0)
            cube(ring, (ring_w * 0.5, 0.008, 0.012 if k % 5 else 0.02), pos, "M_RobotDark", rot=(ang, 0, 0))
        a.behaviour("Rotatable", {"target": f"Dial_{i + 1}", "glow": "Glow"},
                    {"axis": "right", "step": 36, "speed": 240, "target": code[i], "interactive": True},
                    note=f"ring {i + 1} of the code: target = digit")
    a.meta.update({"dials": n, "code": "".join(str(c) for c in code)})
    _indicator(a, note="all rings on their target -> lock open")


# --------------------------------------------------------------------------
# sliding puzzle
# --------------------------------------------------------------------------

ROW_COLOURS = ["M_GlowCyan", "M_GlowOrange", "M_GlowRed", "M_Warning"]


def _shuffled(n, rng, moves):
    """Solvable layout: random legal moves of the gap from the solved board (0 = gap, bottom right)."""
    solved = list(range(1, n * n)) + [0]
    board, gap, last = list(solved), n * n - 1, -1
    done = 0
    while done < moves or board == solved:  # never export a solved board
        r, c = divmod(gap, n)
        options = [g for g, ok in ((gap - n, r > 0), (gap + n, r < n - 1), (gap - 1, c > 0), (gap + 1, c < n - 1))
                   if ok and g != last]
        nxt = rng.choice(options)
        board[gap], board[nxt] = board[nxt], board[gap]
        last, gap = gap, nxt
        done += 1
    return board


@model("sliding_puzzle", "SlidingPuzzle", "puzzle", "Wall sliding puzzle: 3x3 or 4x4 frame with tiles (Tile_<n>) "
       "and one gap; row colour + pips mark the solved position", pivot="wall", params=[
           Param("grid", "choice", "Raster", choices=(3, 4)),
           Param("tile", "float", "Kachelgröße (m)", lo=0.08, hi=0.3),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.6, hi=2.2),
           _status_param(),
       ])
def sliding_puzzle(rng, a):
    p = a.p
    n = p.choice("grid", [3, 3, 4])
    t = p.float("tile", 0.12, 0.18)
    pitch = t + 0.008
    size = n * pitch + 0.08
    d = 0.06
    z = _mount(p, rng, 1.1, 1.5, size / 2)
    yf = 0.1 - d
    body, glow = a.part("Body"), a.part("Glow")
    frame = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    cube(body, (size, d, size), (0, 0.1 - d / 2, z), "M_Ground")
    for s in (-1, 1):  # raised frame
        cube(body, (size, 0.03, 0.04), (0, yf - 0.015, z + s * (size / 2 - 0.02)), frame, bevel=0.005)
        cube(body, (0.04, 0.03, size - 0.08), (s * (size / 2 - 0.02), yf - 0.015, z), frame, bevel=0.005)
    cube(glow, (size * 0.5, 0.02, 0.02), (0, yf - 0.02, z + size / 2 + 0.01), STATUS[p.option("status")])
    board = _shuffled(n, rng, 40 + n * 20)
    tile_mat = p.material(["M_Platform", "M_Wall", "M_Metal"])
    pip_mat = None if p.style.generation >= 2 else "M_RobotDark"  # 2: pips in the row colour (2 materials)
    for cell, number in enumerate(board):
        if number == 0:
            continue
        r, c = divmod(cell, n)
        center = (-n * pitch / 2 + (c + 0.5) * pitch, yf - 0.015, z + n * pitch / 2 - (r + 0.5) * pitch)
        tile = a.part(f"Tile_{number}", pivot=center)
        cube(tile, (t, 0.03, t), center, tile_mat, bevel=0.006)
        sr, sc = divmod(number - 1, n)  # solved row / column -> colour bar + number of pips
        cube(tile, (t * 0.8, 0.006, t * 0.12), (center[0], center[1] - 0.017, center[2] + t * 0.3), ROW_COLOURS[sr])
        for k in range(sc + 1):
            px = center[0] - (sc * t * 0.2) / 2 + k * t * 0.2
            cube(tile, (t * 0.12, 0.006, t * 0.12), (px, center[1] - 0.017, center[2] - t * 0.1),
                 pip_mat or ROW_COLOURS[sr])
    a.meta.update({"grid": n, "pitch_m": round(pitch, 4), "layout": [board[i * n:(i + 1) * n] for i in range(n)],
                   "solved": "Tile_1..Tile_<n*n-1> row by row from the top left, gap bottom right"})
    _indicator(a, note="tiles slide by pitch_m (Unity X / Y) into the gap; solved -> on")


# --------------------------------------------------------------------------
# balance scale
# --------------------------------------------------------------------------

@model("balance_scale", "BalanceScale", "puzzle", "Balance scale: column, tilting beam (Beam, Rotatable) with two "
       "hanging pans (Pan_A / Pan_B, item anchors Slot_A / Slot_B)", params=[
           Param("width", "float", "Balken-Länge (m)", lo=0.6, hi=2.4, size=True),
           Param("height", "float", "Höhe (m)", lo=0.8, hi=2.0, size=True),
           Param("tilt", "float", "Neigung pro Stellung (°)", lo=3, hi=30, unity=True, default=12),
           _status_param(),
       ])
def balance_scale(rng, a):
    p = a.p
    w = p.float("width", 0.9, 1.6)
    h = p.float("height", 1.0, 1.4)
    mat = p.material(["M_Metal", "M_RobotDark", "M_HazardOrange"])
    body, glow = a.part("Body"), a.part("Glow")
    cyl(body, 0.25, 0.08, (0, 0, 0.04), "M_RobotDark", sides=8, bevel=0.02)
    cube(body, (0.08, 0.08, h - 0.1), (0, 0, (h - 0.1) / 2 + 0.05), mat, bevel=0.01)
    cube(glow, (0.1, 0.02, 0.04), (0, -0.05, h * 0.6), STATUS[p.option("status")])
    center = (0.0, 0.0, h)
    beam = a.part("Beam", pivot=center)
    cube(beam, (w, 0.05, 0.06), center, mat, bevel=0.01)
    cyl(beam, 0.05, 0.1, center, "M_RobotDark", sides=8, rot=ALONG_Y)
    cube(beam, (0.02, 0.02, 0.18), (0, -0.04, h + 0.12), "M_Warning")  # pointer
    drop = h * rng.uniform(0.35, 0.5)
    pan_r = min(w * 0.22, 0.3)
    for side, x in (("A", -w / 2 + 0.03), ("B", w / 2 - 0.03)):
        hang = (x, 0.0, h - 0.03)
        pan = a.part(f"Pan_{side}", pivot=hang, parent="Beam")
        for k in range(3):  # chains
            ang = math.pi / 2 + 2 * math.pi * k / 3
            strut(pan, hang, (x + math.cos(ang) * pan_r * 0.9, math.sin(ang) * pan_r * 0.9, h - drop), 0.006,
                  "M_Metal", sides=4)
        cyl(pan, pan_r, 0.04, (x, 0, h - drop - 0.02), "M_Metal", sides=10, radius_top=pan_r * 1.1)
        a.empty(f"Slot_{side}", (x, 0.0, h - drop), parent=f"Pan_{side}")
    a.meta.update({"beam_m": round(w, 3), "pan_drop_m": round(drop, 3)})
    a.behaviour("Rotatable", {"target": "Beam", "glow": "Glow"},
                {"axis": "forward", "step": p.option("tilt"), "speed": 30, "target": 0, "interactive": False},
                note="game logic sets the position from the weights in Slot_A / Slot_B: -1 / 0 / +1; "
                     "target 0 = balanced. Pans hang from the beam - counter-rotate them to keep them level")


# --------------------------------------------------------------------------
# frequency dial
# --------------------------------------------------------------------------

@model("freq_dial", "FreqDial", "puzzle", "Wall frequency tuner: oscilloscope screen (Screen), 1-3 knobs "
       "(Dial_<n>, Rotatable), scale ticks, status glow", pivot="wall", params=[
           Param("knobs", "int", "Drehknöpfe", lo=1, hi=3),
           Param("step", "choice", "Raster (°)", choices=(15, 30, 45), unity=True, default=30),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.6, hi=2.2),
           _status_param(),
       ])
def freq_dial(rng, a):
    p = a.p
    n = p.int("knobs", 1, 3)
    step = p.option("step")
    kr = rng.uniform(0.05, 0.07)
    w = max(0.45, n * (kr * 2 + 0.08) + 0.1)
    h = rng.uniform(0.45, 0.6)
    d = 0.08
    z = _mount(p, rng, 1.1, 1.4, h / 2)
    yf = 0.1 - d
    body, glow = a.part("Body"), a.part("Glow")
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_RobotDark", "M_Wall", "M_Metal"]), bevel=0.015)
    sz = z + h * 0.18
    sw, sh = w - 0.1, h * 0.38
    cube(a.part("Screen"), (sw, 0.01, sh), (0, yf - 0.005, sz), p.glow(weights=(0.7, 0.05, 0.25)))
    lights = a.part("Lights")
    k = 10
    for i in range(k):  # sine wave on the screen, drawn as short dark segments
        x0, x1 = -sw * 0.45 + sw * 0.9 * i / k, -sw * 0.45 + sw * 0.9 * (i + 1) / k
        y0 = math.sin(i / k * 4 * math.pi) * sh * 0.3
        y1 = math.sin((i + 1) / k * 4 * math.pi) * sh * 0.3
        strut(lights, (x0, yf - 0.012, sz + y0), (x1, yf - 0.012, sz + y1), 0.005, "M_RobotDark", sides=4)
    cube(glow, (0.04, 0.02, 0.02), (w / 2 - 0.04, yf - 0.01, z + h / 2 - 0.03), STATUS[p.option("status")])
    kz = z - h * 0.25
    targets = []
    for i in range(n):
        x = -w / 2 + w * (i + 0.5) / n
        for t in range(12):  # scale ticks around the knob
            ang = 2 * math.pi * t / 12
            cube(body, (0.006, 0.01, 0.018), (x + math.sin(ang) * kr * 1.35, yf - 0.004, kz + math.cos(ang) * kr * 1.35),
                 "M_Platform", rot=(0, ang, 0))
        center = (x, yf - 0.03, kz)
        knob = a.part(f"Dial_{i + 1}", pivot=center)
        cyl(knob, kr, 0.05, center, "M_Metal", sides=10, bevel=0.008, rot=ALONG_Y)
        cube(knob, (0.012, 0.012, kr * 0.8), (x, yf - 0.058, kz + kr * 0.45), "M_Warning")  # marker
        target = rng.randint(1, 360 // step - 1)
        targets.append(target)
        a.behaviour("Rotatable", {"target": f"Dial_{i + 1}", "glow": "Glow"},
                    {"axis": "forward", "step": step, "speed": 120, "target": target, "interactive": True},
                    note="tune: the wave on the screen gets calm when every knob is on target")
    a.meta.update({"knobs": n, "targets": targets})
    _indicator(a, note="all knobs on target -> on")


# --------------------------------------------------------------------------
# switch panel
# --------------------------------------------------------------------------

@model("switch_panel", "SwitchPanel", "puzzle", "Wall panel with 3-8 toggle switches (Switch_<n>, Rotatable, "
       "two positions), LEDs, status glow", pivot="wall", params=[
           Param("switches", "int", "Schalter", lo=2, hi=8),
           Param("rows", "choice", "Reihen", choices=(1, 2)),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.6, hi=2.2),
           _status_param(),
       ])
def switch_panel(rng, a):
    p = a.p
    n = p.int("switches", 3, 6)
    rows = p.choice("rows", [1, 1, 2]) if n >= 4 else p.choice("rows", [1])
    per_row = math.ceil(n / rows)
    pitch = rng.uniform(0.08, 0.11)
    w, h, d = per_row * pitch + 0.1, rows * 0.16 + 0.1, 0.06
    z = _mount(p, rng, 1.0, 1.4, h / 2)
    yf = 0.1 - d
    body, glow, lights = a.part("Body"), a.part("Glow"), a.part("Lights")
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_RobotDark", "M_Wall", "M_Metal"]), bevel=0.012)
    cube(glow, (w * 0.5, 0.02, 0.02), (0, yf - 0.01, z + h / 2 - 0.025), STATUS[p.option("status")])
    pattern = [rng.randint(0, 1) for _ in range(n)]
    if not any(pattern):
        pattern[rng.randrange(n)] = 1
    angle = 30
    for i in range(n):
        r, c = divmod(i, per_row)
        x = -per_row * pitch / 2 + (c + 0.5) * pitch
        zz = z + h / 2 - 0.13 - r * 0.16
        cube(body, (0.04, 0.02, 0.05), (x, yf - 0.01, zz), "M_Metal")
        cube(lights, (0.016, 0.016, 0.016), (x, yf - 0.01, zz + 0.05), rng.choice(["M_GlowCyan", "M_GlowOrange"]))
        center = (x, yf - 0.02, zz)
        sw = a.part(f"Switch_{i + 1}", pivot=center)
        tip = (x, yf - 0.02 - math.sin(deg(angle)) * 0.05, zz + math.cos(deg(angle)) * 0.05)
        strut(sw, center, tip, 0.006, "M_Metal", sides=6)
        cyl(sw, 0.011, 0.02, tip, "M_HazardOrange", sides=6)
        a.behaviour("Rotatable", {"target": f"Switch_{i + 1}", "glow": "Glow"},
                    {"axis": "right", "step": 2 * angle, "speed": 360, "target": pattern[i], "interactive": True},
                    note="toggle: position 0 = up, 1 = flipped down (two positions)")
    a.meta.update({"switches": n, "pattern": pattern})
    _indicator(a, note="every switch on its target pattern -> on")
