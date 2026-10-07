"""Visual gameplay-asset prototypes based on IDEEN.md; no game logic is implied."""

from __future__ import annotations

import math

from ..geometry import (
    angle_profile,
    grate,
    i_beam,
    pipe_section,
    rounded_box,
    sphere,
    tee_profile,
    torus,
    u_channel,
    wedge,
)
from .common import ALONG_X, ALONG_Y, cube, cyl, strut
from .registry import model

NOTE = "Experimental visual prototype only; interaction and Unity gameplay wiring are not implemented."


def _mark(asset, rng, idea: str):
    asset.scale(rng.uniform(0.92, 1.08))
    lo, hi = asset.bbox()
    size = tuple(hi[i] - lo[i] for i in range(3))
    center = tuple((hi[i] + lo[i]) / 2 for i in range(3))
    asset.collider(size, center)
    asset.meta.update({"experimental": True, "idea": idea, "gameplay_note": NOTE})


@model("test_utility_trench", "TestUtilityTrench", "environment",
       "Experimental floor utility trench with U-channel, removable-looking cover and conduits")
def test_utility_trench(rng, a):
    body = a.part("Body")
    body.add(u_channel(2.4, 0.38, 0.34, 0.06, "M_RobotDark"),
             loc=(0, 0, 0.17), rot=(math.pi / 2, 0, 0))
    cube(body, (2.25, 0.32, 0.055), (0, 0, 0.37), "M_Platform", bevel=0.015)
    for x in (-0.72, 0, 0.72):
        body.add(pipe_section(0.08, 2.1, 0.018, 8, "M_Metal"),
                 loc=(x, 0, 0.22), rot=ALONG_X)
    for x in (-0.95, 0.95):
        cube(body, (0.06, 0.38, 0.08), (x, 0, 0.4), "M_HazardOrange")
    _mark(a, rng, "utility_trench / coolant routing")


@model("test_pipe_rack", "TestPipeRack", "industrial",
       "Experimental service pipe rack using I-beam uprights and hollow pipe runs")
def test_pipe_rack(rng, a):
    body = a.part("Body")
    for x in (-0.95, 0.95):
        body.add(i_beam(0.48, 1.8, 0.18, 0.07, 0.12, "M_RobotDark"),
                 loc=(x, 0, 0.9), rot=(math.pi / 2, 0, 0))
    for z, radius, material in ((0.52, 0.11, "M_Metal"), (1.03, 0.085, "M_GlowCyan"),
                                (1.54, 0.12, "M_HazardOrange")):
        body.add(pipe_section(radius, 2.15, min(0.025, radius * 0.3), 10, material),
                 loc=(0, 0, z), rot=ALONG_X)
        for x in (-0.82, 0.82):
            body.add(torus(radius * 1.12, 0.018, 10, 4, "M_RobotDark"),
                     loc=(x, 0, z), rot=ALONG_Y)
    for x in (-0.98, 0.98):
        cube(body, (0.32, 0.42, 0.1), (x, 0, 0.05), "M_Metal")
    _mark(a, rng, "pipe_rack")


@model("test_relay_box", "TestRelayBox", "puzzle",
       "Experimental relay and breaker box with rounded housing, grille, switches and cable exits")
def test_relay_box(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.05, 0.42, 1.25, "M_RobotDark", 0.08), loc=(0, 0, 1.1))
    for x in (-0.29, -0.1, 0.1, 0.29):
        cube(body, (0.06, 0.025, 0.47), (x, -0.223, 1.12), "M_Metal")
    for x, material in ((-0.3, "M_GlowCyan"), (0, "M_Warning"), (0.3, "M_GlowOrange")):
        body.add(rounded_box(0.13, 0.045, 0.18, material, 0.025), loc=(x, -0.245, 1.48))
        cube(body, (0.05, 0.05, 0.12), (x, -0.26, 0.76), "M_HazardOrange")
    for x in (-0.3, 0.3):
        body.add(pipe_section(0.055, 0.5, 0.015, 8, "M_Metal"), loc=(x, 0.24, 0.62))
    _mark(a, rng, "relay_box / breaker_switch")


@model("test_coolant_loop", "TestCoolantLoop", "industrial",
       "Experimental coolant loop with supply and return pipes, elbows and a service valve")
def test_coolant_loop(rng, a):
    body = a.part("Body")
    for x, z, material in ((-0.55, 0.72, "M_GlowCyan"), (0.55, 1.48, "M_GlowOrange")):
        body.add(pipe_section(0.12, 1.5, 0.025, 10, material), loc=(x, 0, z))
        body.add(pipe_section(0.12, 1.1, 0.025, 10, material), loc=(0, 0, z - 0.38),
                 rot=ALONG_X)
        for end_x in (-0.55, 0.55):
            body.add(torus(0.12, 0.025, 10, 4, "M_Metal"),
                     loc=(end_x, 0, z - 0.38), rot=ALONG_Y)
    cube(body, (0.42, 0.5, 0.32), (0, 0, 1.1), "M_RobotDark", bevel=0.04)
    cyl(body, 0.1, 0.18, (0, -0.31, 1.1), "M_HazardOrange", rot=ALONG_Y)
    for x in (-0.2, 0.2):
        strut(body, (x, -0.28, 0.85), (x, -0.28, 1.35), 0.025, "M_Metal")
    _mark(a, rng, "coolant_loop / thermal_switch")


@model("test_warning_beacon", "TestWarningBeacon", "tech",
       "Experimental warning beacon with a framed light head and support brackets")
def test_warning_beacon(rng, a):
    body = a.part("Body")
    body.add(rounded_box(0.85, 0.72, 0.18, "M_RobotDark", 0.05), loc=(0, 0, 0.09))
    cyl(body, 0.12, 1.0, (0, 0, 0.68), "M_Metal", sides=8)
    body.add(rounded_box(0.55, 0.55, 0.48, "M_HazardOrange", 0.1), loc=(0, 0, 1.42))
    body.add(sphere(0.24, 8, 4, "M_GlowOrange"), loc=(0, -0.02, 1.43))
    for x in (-0.28, 0.28):
        body.add(angle_profile(0.2, 0.45, 0.1, 0.045, "M_Metal"),
                 loc=(x, 0.02, 1.38), rot=(0, 0, math.pi / 2))
    cube(body, (0.42, 0.04, 0.08), (0, -0.29, 1.42), "M_GlowOrange")
    _mark(a, rng, "warning_lamp / safety beacon")


@model("test_lens_array", "TestLensArray", "puzzle",
       "Experimental lens array for a beam-alignment puzzle; no laser behavior is wired")
def test_lens_array(rng, a):
    body = a.part("Body")
    cube(body, (1.8, 0.65, 0.16), (0, 0, 0.08), "M_RobotDark", bevel=0.025)
    for x, radius, material in ((-0.58, 0.22, "M_GlowCyan"), (0, 0.28, "M_Crystal"),
                                (0.58, 0.22, "M_GlowOrange")):
        cyl(body, radius * 1.25, 0.14, (x, 0, 0.23), "M_Metal", sides=10)
        body.add(torus(radius, 0.035, 12, 4, "M_RobotDark"), loc=(x, 0, 0.46), rot=ALONG_Y)
        body.add(sphere(radius * 0.78, 10, 5, material), loc=(x, -0.025, 0.46))
        strut(body, (x, 0.13, 0.22), (x, 0.13, 0.55), 0.035, "M_Metal")
    body.add(wedge(0.3, 0.2, 0.12, "M_HazardOrange"), loc=(0, -0.38, 0.32),
             rot=(math.pi / 2, 0, 0))
    _mark(a, rng, "lens_array / beam alignment")


@model("test_magnetic_lock", "TestMagneticLock", "puzzle",
       "Experimental magnetic rail lock with channel frame, coil and sliding wedge bolt")
def test_magnetic_lock(rng, a):
    body = a.part("Body")
    body.add(u_channel(1.4, 1.0, 0.16, 0.09, "M_RobotDark"),
             loc=(0, 0, 0.88), rot=(math.pi / 2, 0, 0))
    for x in (-0.42, 0.42):
        cyl(body, 0.23, 0.18, (x, -0.14, 0.88), "M_Metal", rot=ALONG_Y)
        for k in range(3):
            body.add(torus(0.18 + k * 0.025, 0.018, 10, 4, "M_GlowCyan"),
                     loc=(x, -0.25, 0.88), rot=ALONG_Y)
    body.add(wedge(0.48, 0.38, 0.22, "M_HazardOrange"), loc=(0, -0.35, 0.82),
             rot=(math.pi / 2, 0, 0))
    cube(body, (1.6, 0.22, 0.14), (0, 0.25, 0.1), "M_Metal")
    _mark(a, rng, "magnetic_lock / sliding rail")


@model("test_scanner_pad", "TestScannerPad", "puzzle",
       "Experimental floor scanner pad with grate surface, guide rails and a status wedge")
def test_scanner_pad(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.8, 1.5, 0.2, "M_RobotDark", 0.09), loc=(0, 0, -0.1))
    body.add(grate(1.35, 1.05, 0.045, 0.055, 0.07, "M_Metal"), loc=(0, 0, -0.015))
    for x in (-0.78, 0.78):
        body.add(u_channel(0.12, 0.22, 1.18, 0.035, "M_GlowCyan"),
                 loc=(x, 0, 0.055), rot=(math.pi / 2, 0, 0))
    body.add(wedge(0.28, 0.16, 0.08, "M_GlowOrange"), loc=(0, -0.82, 0.04),
             rot=(math.pi / 2, 0, 0))
    _mark(a, rng, "scanner_pad / identity scan")


@model("test_power_routing", "TestPowerRouting", "puzzle",
       "Experimental power-routing board with visible channels and three connection nodes")
def test_power_routing(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.8, 0.38, 1.15, "M_RobotDark", 0.07), loc=(0, 0, 1.0))
    for x, material in ((-0.56, "M_GlowCyan"), (0, "M_HazardOrange"), (0.56, "M_GlowOrange")):
        body.add(rounded_box(0.22, 0.06, 0.24, material, 0.035), loc=(x, -0.225, 1.36))
        cyl(body, 0.09, 0.06, (x, -0.25, 0.81), "M_Metal", rot=ALONG_Y)
        cyl(body, 0.045, 0.075, (x, -0.29, 0.81), material, rot=ALONG_Y)
    for x in (-0.56, 0, 0.56):
        body.add(pipe_section(0.025, 0.46, 0.007, 6, "M_HazardOrange"),
                 loc=(x, 0.24, 0.82), rot=ALONG_X)
    body.add(tee_profile(0.8, 0.1, 0.04, 0.035, "M_Metal"), loc=(0, -0.25, 1.03))
    _mark(a, rng, "power_routing / relay sequence")


@model("test_thermal_switch", "TestThermalSwitch", "puzzle",
       "Experimental thermal switch with cooling fins, pipe stubs and a temperature selector")
def test_thermal_switch(rng, a):
    body = a.part("Body")
    body.add(rounded_box(1.1, 0.38, 0.95, "M_RobotDark", 0.07), loc=(0, 0, 1.08))
    for x in (-0.37, -0.22, -0.07, 0.08, 0.23, 0.38):
        cube(body, (0.055, 0.06, 0.58), (x, -0.235, 1.08), "M_Metal")
    body.add(torus(0.22, 0.045, 12, 5, "M_GlowCyan"), loc=(0, -0.26, 1.42), rot=ALONG_Y)
    cyl(body, 0.14, 0.08, (0, -0.3, 1.42), "M_HazardOrange", rot=ALONG_Y)
    for x in (-0.32, 0.32):
        body.add(pipe_section(0.07, 0.55, 0.018, 8, "M_Metal"), loc=(x, 0.24, 0.86))
        cyl(body, 0.09, 0.045, (x, -0.23, 0.78), "M_GlowOrange", rot=ALONG_Y)
    _mark(a, rng, "thermal_switch / coolant control")
