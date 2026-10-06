"""Lights: floodlights, neon and LED strips, emergency lighting.

Every light has its glowing part ``Glow`` (one material) driven by the game's
``SignalLight``. Floodlights also say where Unity should put a real light
(``lightPosition``, ``range``, ``intensity``, model coordinates in Unity units).
"""

from __future__ import annotations

import math

from ..asset import to_unity
from ..geometry import add_up, prism
from ..params import Param
from .common import ALONG_X, add_vec, cube, cyl, deg, rotated, strut
from .lettering import add_text, text_width
from .registry import model

UPRIGHT = ((1, 0, 0), (0, 0, -1), (0, 1, 0))  # (x, z) polygon facing the front, extruded towards -y


GLOW_LAMPS = {"cyan": "M_GlowCyan", "red": "M_GlowRed", "orange": "M_GlowOrange"}


@model("floodlight", "Floodlight", "tech", "Floodlight on a tripod or mast: tilted lamp head with a glowing front "
       "(Glow), SignalLight with a real light (lightPosition, range, intensity)", params=[
           Param("mount", "choice", "Unterbau", choices=("tripod", "mast", "base")),
           Param("height", "float", "Höhe (m)", lo=0.5, hi=5.0, size=True),
           Param("heads", "choice", "Strahler", choices=(1, 2, 4)),
           Param("tilt", "float", "Neigung (°)", lo=0, hi=60),
           Param("range", "float", "Reichweite (m)", lo=2, hi=60, unity=True, default=15),
           Param("intensity", "float", "Helligkeit", lo=0.1, hi=20, unity=True, default=3),
       ])
def floodlight(rng, a):
    p = a.p
    mount = p.choice("mount", ["tripod", "tripod", "mast", "base"])
    h = p.float("height", 1.5, 3.0) if mount != "base" else p.float("height", 0.5, 1.0)
    heads = p.choice("heads", [1, 1, 2, 4])
    tilt = deg(p.float("tilt", 10, 35))
    body, lights = a.part("Body"), a.part("Glow")
    dark = "M_RobotDark"
    a.meta.update({"mount": mount, "heads": heads})
    if mount == "tripod":
        for k in range(3):
            ang = deg(90 + 120 * k)
            strut(body, (0, 0, h - 0.2), (math.cos(ang) * h * 0.35, math.sin(ang) * h * 0.35, 0.02), 0.025, dark)
            cube(body, (0.08, 0.08, 0.04), (math.cos(ang) * h * 0.35, math.sin(ang) * h * 0.35, 0.02), "M_Metal")
        cyl(body, 0.035, h * 0.4, (0, 0, h * 0.8 - 0.05), "M_Metal", sides=6)
    elif mount == "mast":
        cube(body, (0.5, 0.5, 0.15), (0, 0, 0.075), dark, bevel=0.02)
        cyl(body, 0.06, h - 0.15, (0, 0, 0.15 + (h - 0.15) / 2), p.material(["M_Wall", "M_Metal", "M_Warning"]),
            sides=8)
    else:
        cube(body, (0.6, 0.4, h * 0.6), (0, 0, h * 0.3), p.material(["M_Warning", "M_RobotDark", "M_Wall"]), bevel=0.02)
        cyl(body, 0.05, h * 0.4 + 0.02, (0, 0.05, h * 0.8 + 0.01), "M_Metal", sides=6)
    hw, hh = rng.uniform(0.3, 0.5), rng.uniform(0.25, 0.35)
    cols = 2 if heads >= 2 else 1
    rows = 2 if heads == 4 else 1
    top = h + hh * rows / 2 + 0.05
    cube(body, (hw * cols + 0.1, 0.06, 0.06), (0, 0.05, h + 0.02), "M_Metal")  # yoke bar
    lamp_points = []
    lamp = GLOW_LAMPS.get(p.style.glow or "", "M_Crystal")  # bright white-cyan unless the style fixes a glow
    for c in range(cols):
        for r in range(rows):
            center = ((c - (cols - 1) / 2) * (hw + 0.05), 0.0, h + 0.08 + hh / 2 + r * (hh + 0.04))
            rot = (-tilt, 0.0, 0.0)
            cube(body, (hw, 0.2, hh), center, dark, bevel=0.02, rot=rot)
            cube(body, (hw + 0.02, 0.04, hh + 0.02), add_vec(center, rotated(rot, (0, -0.09, 0))), "M_Metal", rot=rot)
            front = add_vec(center, rotated(rot, (0, -0.115, 0)))
            cube(lights, (hw * 0.85, 0.01, hh * 0.8), front, lamp, rot=rot)
            for k in range(3):  # cooling fins on the back
                cube(body, (hw * 0.9, 0.06, 0.015), add_vec(center, rotated(rot, (0, 0.12, (k - 1) * hh * 0.3))),
                     "M_RobotDark", rot=rot)
            lamp_points.append(front)
    a.meta["top_m"] = round(top, 3)
    cx = add_up(q[0] for q in lamp_points) / len(lamp_points)
    cz = add_up(q[2] for q in lamp_points) / len(lamp_points)
    light_at = (cx, min(q[1] for q in lamp_points) - 0.05, cz)
    a.behaviour("SignalLight", {"glow": "Glow"},
                {"mode": "Steady", "lightPosition": list(to_unity(light_at)), "range": p.option("range"),
                 "intensity": p.option("intensity")},
                note=f"spot light at lightPosition, aimed forward and {math.degrees(tilt):.0f} degrees down")


@model("light_strip", "LightStrip", "tech", "Neon tube or LED strip on the wall or under the ceiling (1-4 m along "
       "X): holder, diffuser, glowing tube (Glow, SignalLight)", pivot="wall", params=[
           Param("style", "choice", "Art", choices=("neon", "led", "double")),
           Param("length", "choice", "Länge (m)", choices=(1.0, 2.0, 4.0)),
           Param("mount", "choice", "Montage", choices=("wall", "ceiling")),
           Param("mount_height", "float", "Höhe (m)", lo=0.5, hi=6.0),
           Param("mode", "choice", "Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Steady"),
       ])
def light_strip(rng, a):
    p = a.p
    style = p.choice("style", ["neon", "led", "double"])
    ln = p.choice("length", [1.0, 2.0, 2.0, 4.0])
    mount = p.choice("mount", ["wall", "wall", "ceiling"])
    z = p.value("mount_height", rng.uniform(2.0, 2.6) if mount == "wall" else 3.0)
    glow = p.glow(weights=(0.6, 0.15, 0.25))
    body, lights = a.part("Body"), a.part("Glow")
    a.meta.update({"style": style, "length_m": ln, "mount": mount})
    if mount == "wall":
        y = 0.1 - 0.03
        cube(body, (ln, 0.06, 0.08), (0, y, z), "M_RobotDark")
        tubes = (0.0,) if style != "double" else (-0.035, 0.035)
        for dz in tubes:
            if style == "led":
                cube(lights, (ln - 0.04, 0.012, 0.025), (0, y - 0.036, z + dz), glow)
            else:
                cyl(lights, 0.02, ln - 0.1, (0, y - 0.05, z + dz), glow, sides=6, rot=ALONG_X)
        for x in (-1, 1):
            cube(body, (0.04, 0.08, 0.1), (x * (ln / 2 - 0.03), y - 0.02, z), "M_Metal")
    else:
        cube(body, (ln, 0.1, 0.05), (0, 0, z - 0.025), "M_RobotDark")
        for x in (-1, 1):  # hanging wires
            cube(body, (0.01, 0.01, 0.2), (x * ln * 0.4, 0, z - 0.15), "M_Metal")
        cube(body, (ln, 0.12, 0.05), (0, 0, z - 0.275), "M_Metal")
        tubes = (0.0,) if style != "double" else (-0.03, 0.03)
        for dy in tubes:
            if style == "led":
                cube(lights, (ln - 0.04, 0.03, 0.012), (0, dy, z - 0.306), glow)
            else:
                cyl(lights, 0.02, ln - 0.1, (0, dy, z - 0.32), glow, sides=6, rot=ALONG_X)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})


@model("emergency_light", "EmergencyLight", "tech", "Emergency lighting on the wall: twin-lamp box, rotating beacon "
       "(Rotor) or a lit EXIT box", pivot="wall", params=[
           Param("style", "choice", "Art", choices=("twin", "beacon", "exit")),
           Param("mount_height", "float", "Höhe (m)", lo=1.5, hi=4.0),
           Param("mode", "choice", "Modus", choices=("Steady", "Blink", "Pulse", "Rotate"), unity=True),
       ])
def emergency_light(rng, a):
    p = a.p
    style = p.choice("style", ["twin", "beacon", "exit"])
    z = p.value("mount_height", rng.uniform(2.2, 2.7))
    body, lights = a.part("Body"), a.part("Glow")
    a.meta["style"] = style
    if style == "twin":
        w = rng.uniform(0.3, 0.45)
        cube(body, (w, 0.12, 0.2), (0, 0.04, z), "M_Warning", bevel=0.02)
        cube(body, (w * 0.5, 0.02, 0.06), (0, -0.025, z - 0.04), "M_RobotDark")
        cube(lights, (w * 0.3, 0.01, 0.03), (0, -0.04, z - 0.04), "M_GlowRed")
        for s in (-1, 1):
            head = (s * w * 0.35, -0.05, z + 0.16)
            cube(body, (0.04, 0.06, 0.08), (s * w * 0.35, 0.0, z + 0.12), "M_Metal")
            cyl(body, 0.06, 0.1, head, "M_RobotDark", sides=8, rot=(deg(70), 0, s * deg(25)))
            cyl(body, 0.05, 0.02, add_vec(head, rotated((deg(70), 0, s * deg(25)), (0, 0, 0.06))), "M_Platform",
                sides=8, rot=(deg(70), 0, s * deg(25)))
        mode = "Steady"
        parts = {"glow": "Glow"}
    elif style == "beacon":
        cube(body, (0.2, 0.15, 0.2), (0, 0.025, z), "M_RobotDark", bevel=0.02)
        cube(body, (0.08, 0.2, 0.06), (0, -0.1, z), "M_Metal")
        center = (0.0, -0.2, z + 0.1)
        cyl(body, 0.12, 0.05, (0, -0.2, z + 0.025), "M_RobotDark", sides=10)
        cyl(lights, 0.1, 0.18, (0, -0.2, z + 0.14), p.glow_from(["M_GlowRed", "M_GlowOrange"]), sides=10,
            radius_top=0.07)
        cube(a.part("Rotor", pivot=center), (0.16, 0.03, 0.12), (0, -0.17, z + 0.14), "M_Metal")
        mode = "Rotate"
        parts = {"glow": "Glow", "rotor": "Rotor"}
    else:
        text = "EXIT"
        th = rng.uniform(0.08, 0.12)
        w = text_width(text, th) + th * 1.6
        cube(body, (w, 0.1, th * 2.4), (0, 0.05, z), "M_RobotDark", bevel=0.01)
        cube(body, (w - 0.03, 0.01, th * 2.4 - 0.03), (0, -0.005, z), "M_Platform")
        ink = "M_GlowCyan" if rng.random() < 0.5 else "M_GlowRed"
        add_text(lights, text, (-th * 0.5, -0.01, z), th, 0.01, ink)
        x = text_width(text, th) / 2 + th * 0.15
        lights.add(prism([(0.0, -th * 0.4), (th * 0.5, 0.0), (0.0, th * 0.4)], 0.01, ink), loc=(x - th * 0.5, -0.015, z),
                   basis=UPRIGHT)
        mode = "Steady"
        parts = {"glow": "Glow"}
    mode = p.value("mode", mode)
    if mode == "Rotate" and style != "beacon":  # only the beacon has a rotor: the others blink instead
        mode = "Blink"
    a.behaviour("SignalLight", parts, {"mode": mode},
                note="Rotate spins Rotor around Unity up" if style == "beacon" else "")
