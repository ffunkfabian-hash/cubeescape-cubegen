"""Station appliances: coffee machine and vending machine (static decoration with glow and screens)."""

from __future__ import annotations

from ..params import Param
from .common import ALONG_Y, cube, cyl
from .registry import model

SNACK_COLOURS = ["M_HazardOrange", "M_Warning", "M_GlowCyan", "M_GlowRed", "M_Platform", "M_RobotBody"]


@model("coffee_machine", "CoffeeMachine", "props", "Coffee machine on a counter block or standing: housing, "
       "display (Screen), nozzle, drip tray, cups, water tank", params=[
           Param("style", "choice", "Bauform", choices=("counter", "standing")),
           Param("cups", "int", "Tassen", lo=0, hi=4),
       ])
def coffee_machine(rng, a):
    p = a.p
    style = p.choice("style", ["counter", "counter", "standing"])
    mat = p.material(["M_RobotDark", "M_Metal", "M_Wall", "M_HazardOrange"])
    body = a.part("Body")
    base = 0.0
    if style == "counter":
        cw, cd = rng.uniform(0.9, 1.4), 0.6
        cube(body, (cw, cd, 0.9), (0, 0, 0.45), p.styled("M_Wall", ["M_Wall", "M_Platform"]), bevel=0.02)
        cube(body, (cw + 0.04, cd + 0.04, 0.04), (0, 0, 0.92), "M_RobotDark", bevel=0.01)
        cube(body, (cw * 0.9, 0.02, 0.6), (0, -cd / 2 - 0.005, 0.45), "M_Metal")  # cabinet door
        base = 0.94
    w, d, h = rng.uniform(0.3, 0.45), rng.uniform(0.35, 0.45), rng.uniform(0.45, 0.6)
    if style == "standing":
        h = rng.uniform(1.6, 1.9)
    cube(body, (w, d, h), (0, 0, base + h / 2), mat, bevel=0.02)
    bay_z = base + (0.05 if style == "counter" else 0.8)
    cube(body, (w * 0.7, 0.04, 0.22), (0, -d / 2 + 0.01, bay_z + 0.13), "M_Ground")  # recessed cup bay
    cube(body, (w * 0.7, d * 0.4, 0.02), (0, -d / 2 + d * 0.15, bay_z + 0.01), "M_Metal")  # drip tray
    cyl(body, 0.02, 0.05, (0, -d / 2 + 0.06, bay_z + 0.22), "M_Metal", sides=6)  # nozzle
    sz = bay_z + 0.32
    cube(a.part("Screen"), (w * 0.5, 0.01, 0.08), (0, -d / 2 - 0.005, sz), p.glow(weights=(0.7, 0.0, 0.3)))
    for i in range(3):
        cyl(body, 0.015, 0.02, (-w * 0.25 + i * w * 0.25, -d / 2 - 0.01, sz + 0.08), "M_Platform", sides=6,
            rot=ALONG_Y)
    tank = a.part("Glass")
    if p.style.generation < 3:
        cube(tank, (0.12, d * 0.6, h * 0.5), (w / 2 + 0.06, 0, base + h * 0.4), "M_Glass")
    else:
        # Recognisable removable reservoir: thin glass walls, cap, cradle and level marks.
        th = h * (0.28 if style == "standing" else 0.5)
        tz, tx, td = base + h * 0.4, w / 2 + 0.06, d * 0.6
        for sx in (-1, 1):
            cube(tank, (0.006, td, th), (tx + sx * 0.057, 0, tz), "M_Glass")
        for sy in (-1, 1):
            cube(tank, (0.108, 0.006, th), (tx, sy * (td / 2 - 0.003), tz), "M_Glass")
        cube(tank, (0.108, td - 0.012, 0.006), (tx, 0, tz - th / 2 + 0.003), "M_Glass")
        for z in (tz - th / 2 - 0.012, tz + th / 2 + 0.012):
            cube(body, (0.14, td + 0.02, 0.024), (tx, 0, z), "M_RobotDark")
        cube(body, (0.16, 0.06, 0.06), (w / 2 + 0.04, 0, tz - th / 2 - 0.04), mat)
        for i in range(3):
            cube(body, (0.04, 0.008, 0.009), (tx, -td / 2 - 0.005, tz - th * 0.25 + i * th * 0.25), "M_Platform")
    cups = p.int("cups", 1, 3)
    for i in range(cups if style == "counter" else min(cups, 1)):  # next to the machine / in the bay
        x = -w / 2 - 0.12 - i * 0.11 if style == "counter" else 0.0
        z = base if style == "counter" else bay_z + 0.02
        cyl(body, 0.035, 0.08, (x, -d * 0.2, z + 0.04), rng.choice(["M_Platform", "M_HazardOrange", "M_Wall"]),
            sides=8, radius_top=0.04)
    a.meta["style"] = style


@model("vending_machine", "VendingMachine", "props", "Vending machine: glass front with snack rows, keypad, "
       "coin slot, output flap, glow sign (Glow)", params=[
           Param("width", "float", "Breite (m)", lo=0.7, hi=1.4, size=True),
           Param("rows", "int", "Fächer-Reihen", lo=3, hi=6),
           Param("lit", "bool", "Beleuchtet"),
       ])
def vending_machine(rng, a):
    p = a.p
    w = p.float("width", 0.8, 1.1)
    d, h = rng.uniform(0.7, 0.85), rng.uniform(1.8, 2.0)
    mat = p.material(["M_RobotDark", "M_HazardOrange", "M_Wall", "M_Metal"])
    body = a.part("Body")
    cube(body, (w, d, h), (0, 0, h / 2), mat, bevel=0.025)
    gw = w * 0.68
    gx = -w / 2 + 0.04 + gw / 2
    cube(body, (gw, 0.04, h * 0.66), (gx, -d / 2 + 0.01, h * 0.58), "M_Ground")  # dark inside
    n = p.int("rows", 4, 5)
    for r in range(n):
        z = h * 0.27 + (r + 0.3) * h * 0.66 / n
        cube(body, (gw - 0.04, 0.12, 0.012), (gx, -d / 2 + 0.06, z - 0.01), "M_Metal")  # shelf
        k = rng.randint(3, 5)
        for i in range(k):
            sx = gx - gw / 2 + (i + 0.5) * gw / k
            cube(body, (gw / k * 0.6, 0.08, h * 0.66 / n * 0.5), (sx, -d / 2 + 0.07, z + h * 0.66 / n * 0.25),
                 rng.choice(SNACK_COLOURS))
    cube(a.part("Glass"), (gw, 0.02, h * 0.66), (gx, -d / 2 - 0.005, h * 0.58), "M_Glass")
    px = w / 2 - (w - gw - 0.04) / 2
    pw = w - gw - 0.08
    cube(a.part("Screen"), (pw * 0.8, 0.01, 0.07), (px, -d / 2 - 0.005, h * 0.78), "M_GlowCyan")
    for r in range(4):  # keypad
        for c in range(3):
            cube(body, (pw * 0.18, 0.015, 0.03), (px - pw * 0.25 + c * pw * 0.25, -d / 2 - 0.007, h * 0.68 - r * 0.045),
                 "M_Platform")
    cube(body, (0.02, 0.015, 0.06), (px, -d / 2 - 0.007, h * 0.48), "M_Metal")  # coin slot
    cube(body, (gw * 0.7, 0.03, 0.14), (gx, -d / 2 - 0.01, h * 0.13), "M_Metal", bevel=0.008)  # output flap
    lit = p.bool("lit", 0.7)
    cube(a.part("Glow"), (w * 0.85, 0.02, 0.1), (0, -d / 2 - 0.005, h * 0.95),
         p.glow(weights=(0.5, 0.2, 0.3)) if lit else "M_RobotDark")
    a.meta["lit"] = lit
