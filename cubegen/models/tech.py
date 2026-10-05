"""Station tech: consoles, terminals, server racks, lights and crystals."""

from __future__ import annotations

import math

from .common import add_vec, cube, cyl, deg, frustum, glow_material, rotated
from .registry import model


def _tilted_screen(body, screen, center, size, tilt_deg, glow):
    """Dark screen housing tilted back by ``tilt_deg`` with a glowing pane in front."""
    rot = (deg(-tilt_deg), 0.0, 0.0)  # negative X rotation tilts the top backwards (+Y)
    cube(body, (size[0], 0.08, size[1]), center, "M_RobotDark", bevel=0.02, rot=rot)
    pane = add_vec(center, rotated(rot, (0.0, -0.045, 0.0)))
    cube(screen, (size[0] - 0.1, 0.01, size[1] - 0.1), pane, glow, rot=rot)


@model("console", "Console", "tech", "Desk console with 1-3 tilted screens, keyboard and button row")
def console(rng, a):
    w = rng.uniform(1.2, 2.0)
    d = rng.uniform(0.7, 0.9)
    h = rng.uniform(0.8, 0.9)
    glow = glow_material(rng, weights=(0.85, 0.05, 0.1))
    # multi-coloured buttons are decoration -> "Lights"; "Glow" parts must keep ONE material
    # because the game swaps renderer.sharedMaterial (= slot 0 only)
    body, screen, lights = a.part("Body"), a.part("Screen"), a.part("Lights")

    cube(body, (w, d, h - 0.04), (0, 0.05, (h - 0.04) / 2), "M_RobotDark", bevel=0.03)
    cube(body, (w, d + 0.1, 0.08), (0, 0, h), "M_Wall", bevel=0.02)
    cube(body, (w * 0.55, 0.3, 0.03), (-w * 0.1, -0.2, h + 0.055), "M_Metal")
    n = rng.choice([1, 1, 2, 3])
    tilt = rng.uniform(10, 25)
    sw = (w * 0.92) / n - 0.06
    sh = rng.uniform(0.45, 0.6)
    for i in range(n):
        x = -w * 0.46 + (i + 0.5) * (w * 0.92) / n
        cube(body, (0.08, 0.12, 0.3), (x, 0.28, h + 0.15), "M_Wall")
        _tilted_screen(body, screen, (x, 0.25, h + 0.3 + sh / 2), (sw, sh), tilt, glow)
    for i in range(rng.randint(3, 6)):
        mat = "M_GlowRed" if rng.random() < 0.25 else "M_GlowCyan"
        cube(lights, (0.06, 0.05, 0.02), (w * 0.38 - i * 0.09, -0.3, h + 0.05), mat)
    if rng.random() < 0.5:  # cables into the floor at the back
        for x in (-w * 0.4, w * 0.4):
            cyl(body, 0.035, h * 0.6, (x, d / 2 + 0.1, h * 0.3), "M_Metal")
    a.meta.update({"screens": n, "tilt": round(tilt, 1)})


@model("terminal", "Terminal", "tech", "Free-standing terminal: tapered column, tilted screen, keypad or card slot")
def terminal(rng, a):
    glow = glow_material(rng, weights=(0.85, 0.05, 0.1))
    body, screen, lights = a.part("Body"), a.part("Screen"), a.part("Glow")
    col_h = rng.uniform(0.9, 1.2)
    cube(body, (0.6, 0.5, 0.1), (0, 0, 0.05), "M_RobotDark", bevel=0.02)
    frustum(body, (0.36, 0.3), (0.24, 0.2), 0.1, col_h, rng.choice(["M_Wall", "M_Metal"]))
    sw, sh = rng.uniform(0.55, 0.8), rng.uniform(0.35, 0.5)
    _tilted_screen(body, screen, (0, -0.02, col_h + sh / 2), (sw, sh), rng.uniform(10, 25), glow)
    extra = rng.choice(["keypad", "slot", "none"])
    if extra == "keypad":
        for row in range(3):
            for col in range(3):
                cube(body, (0.05, 0.03, 0.04), (-0.06 + col * 0.06, -0.165, col_h - 0.35 + row * 0.06), "M_Metal")
    elif extra == "slot":
        cube(body, (0.2, 0.04, 0.04), (0, -0.16, col_h - 0.25), "M_Platform")
    status = "M_GlowRed"  # one material per Glow part (SignalIndicator swaps it)
    cube(lights, (0.06, 0.02, 0.06), (0.12, -0.16, col_h - 0.12), status)
    if rng.random() < 0.4:  # antenna with a tip light
        cyl(body, 0.012, 0.25, (sw * 0.35, 0.05, col_h + sh + 0.15), "M_RobotDark", sides=6)
        cube(lights, (0.04, 0.04, 0.04), (sw * 0.35, 0.05, col_h + sh + 0.29), status)
    a.meta["extra"] = extra
    a.behaviour("SignalIndicator", {"renderers": ["Glow"]}, {"offMaterial": "M_GlowRed", "onMaterial": "M_GlowCyan"})


@model("server_rack", "ServerRack", "tech", "Server rack with panel rows and a seeded pattern of status LEDs")
def server_rack(rng, a):
    w = rng.uniform(0.6, 1.2)
    d = rng.uniform(0.6, 1.0)
    h = rng.uniform(1.8, 2.4)
    body, lights = a.part("Body"), a.part("Lights")  # mixed LED colours: decoration like Rack_Lights
    cube(body, (w, d, h), (0, 0, h / 2), "M_RobotDark", bevel=0.03)
    for z in (0.04, h - 0.04):  # 1 cm proud of the body: no shared (z-fighting) planes
        cube(body, (w + 0.04, d + 0.04, 0.1), (0, 0, z), "M_Wall", bevel=0.02)
    row_h = rng.uniform(0.25, 0.4)
    rows = int((h - 0.4) / row_h)
    sides = (-1, 1) if rng.random() < 0.5 else (-1,)
    red_chance = rng.uniform(0.05, 0.2)
    leds = 0
    for s in sides:
        y = s * (d / 2 + 0.01)
        for r in range(rows):
            z = 0.25 + (r + 0.5) * (h - 0.4) / rows
            cube(body, (w - 0.2, 0.02, row_h * 0.75), (0, y, z), "M_Wall", bevel=0.005)
            for k in range(rng.randint(1, 5)):
                mat = "M_GlowRed" if rng.random() < red_chance else "M_GlowCyan"
                cube(lights, (0.05, 0.02, 0.03), (w / 2 - 0.18 - k * 0.08, s * (d / 2 + 0.025), z + row_h * 0.15), mat)
                leds += 1
    a.meta.update({"rows": rows, "leds": leds})


@model("light", "Light", "tech", "Light post, short bollard or rotating emergency beacon (Rotor)")
def light(rng, a):
    style = rng.choice(["post", "bollard", "beacon"])
    glow = glow_material(rng, weights=(0.6, 0.2, 0.2))
    body, lights = a.part("Body"), a.part("Glow")
    a.meta["style"] = style
    if style == "post":
        h = rng.uniform(2.0, 3.0)
        cube(body, (0.4, 0.4, 0.15), (0, 0, 0.075), "M_RobotDark", bevel=0.02)
        cyl(body, 0.06, h - 0.3, (0, 0, 0.15 + (h - 0.3) / 2), "M_Wall", sides=6)
        cube(body, (0.3, 0.3, 0.22), (0, 0, h), "M_RobotDark", bevel=0.03)
        cube(lights, (0.24, 0.24, 0.06), (0, 0, h - 0.13), glow)
    elif style == "bollard":
        h = rng.uniform(0.6, 1.0)
        cyl(body, 0.16, h, (0, 0, h / 2), "M_Wall", sides=8, bevel=0.02)
        cyl(body, 0.2, 0.06, (0, 0, h), "M_RobotDark", sides=8)
        cyl(lights, 0.165, 0.12, (0, 0, h - 0.15), glow, sides=8)
    else:
        cyl(body, 0.25, 0.15, (0, 0, 0.075), "M_RobotDark", sides=10)
        for i in range(4):
            ang = math.pi / 2 * i
            cube(body, (0.03, 0.03, 0.3), (math.cos(ang) * 0.19, math.sin(ang) * 0.19, 0.3), "M_Metal")
        cyl(lights, 0.18, 0.28, (0, 0, 0.3), rng.choice(["M_GlowRed", "M_GlowOrange"]), sides=10, radius_top=0.12)
        center = (0.0, 0.0, 0.3)
        cube(a.part("Rotor", pivot=center), (0.3, 0.04, 0.2), (0, 0.04, 0.3), "M_Metal")
    mode = {"post": "Steady", "bollard": "Pulse", "beacon": "Rotate"}[style]
    parts = {"glow": "Glow", "rotor": "Rotor"} if style == "beacon" else {"glow": "Glow"}
    a.behaviour("SignalLight", parts, {"mode": mode},
                note="Rotate spins Rotor around Unity up (Blender Z), as in EmergencyLight")


@model("crystal_cluster", "CrystalCluster", "tech", "Energy crystals growing out of a dark base")
def crystal_cluster(rng, a):
    base_r = rng.uniform(0.6, 1.4)
    base, crystals = a.part("Base"), a.part("Crystals")
    cyl(base, base_r, 0.3, (0, 0, 0.15), "M_RobotDark", sides=7, radius_top=base_r * 0.75, bevel=0.03)
    n = rng.randint(3, 8)
    for i in range(n):
        if i == 0:
            x = y = 0.0
            hh, rr, tilt = base_r * rng.uniform(1.6, 2.4), base_r * 0.32, (0.0, 0.0, 0.0)
        else:
            ang = rng.uniform(0, 2 * math.pi)
            dist = base_r * rng.uniform(0.35, 0.7)
            x, y = math.cos(ang) * dist, math.sin(ang) * dist
            hh, rr = base_r * rng.uniform(0.6, 1.4), base_r * rng.uniform(0.1, 0.2)
            # lean outwards
            tilt = (deg(-math.sin(ang) * rng.uniform(10, 35)), deg(math.cos(ang) * rng.uniform(10, 35)), 0.0)
        sides = rng.choice([5, 6])
        foot = (x, y, 0.25)
        cyl(crystals, rr, hh * 0.7, add_vec(foot, rotated(tilt, (0, 0, hh * 0.35))), "M_Crystal", sides=sides,
            radius_top=rr * 0.9, rot=tilt)
        cyl(crystals, rr * 0.9, hh * 0.3, add_vec(foot, rotated(tilt, (0, 0, hh * 0.85))), "M_Crystal", sides=sides,
            radius_top=0.0, rot=tilt)
    for _ in range(rng.randint(0, 4)):  # rubble around the base
        ang = rng.uniform(0, 2 * math.pi)
        s = base_r * rng.uniform(0.12, 0.25)
        cube(base, (s, s * 0.8, s * 0.6), (math.cos(ang) * base_r * 1.05, math.sin(ang) * base_r * 1.05, s * 0.2),
             "M_Ground", rot=(deg(rng.uniform(-15, 15)), deg(rng.uniform(-15, 15)), ang))
    a.meta["crystals"] = n
