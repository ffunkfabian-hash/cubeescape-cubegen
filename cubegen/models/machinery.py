"""More industry and tech: pipe bends, fans, pumps, transformers, a reactor core, holograms, monitor walls and
intercoms.

``pipe_bend`` matches ``pipe`` (same radii, flanges 6 cm from the ends, arms
end on the 0.5 m grid). Machines use the ``Machine`` script like ``machine``
and ``generator``: ``Glow`` is the status part, ``Rotor`` turns while running.
"""

from __future__ import annotations

import math

from ..geometry import lathe, sphere, torus
from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl, deg, fan, strut
from .registry import model

STATUS = {"off": "M_GlowRed", "on": "M_GlowCyan"}


def _status_param():
    return Param("status", "choice", "Glow-Startzustand", choices=("off", "on"), default="off",
                 description="Status-Glow beim Export: off = M_GlowRed, on = M_GlowCyan (Unity schaltet ihn um)")


# --------------------------------------------------------------------------
# pipe bends
# --------------------------------------------------------------------------

BEND_ARMS = {  # directions of the arms
    "elbow": ((-1, 0, 0), (0, -1, 0)),
    "elbow_up": ((-1, 0, 0), (0, 0, 1)),
    "tee": ((-1, 0, 0), (1, 0, 0), (0, -1, 0)),
    "cross": ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0)),
}


@model("pipe_bend", "PipeBend", "industrial", "Pipe fitting matching pipe: elbow, elbow up, tee or cross, flanges, "
       "glow ring, floor support", params=[
           Param("kind", "choice", "Stück", choices=tuple(BEND_ARMS)),
           Param("radius", "choice", "Radius (m)", choices=(0.09, 0.18, 0.35)),
           Param("arm", "choice", "Armlänge (m)", choices=(0.5, 1.0)),
           Param("axis_height", "float", "Achshöhe (m)", lo=0.2, hi=3.0),
           Param("support", "bool", "Stütze"),
       ])
def pipe_bend(rng, a):
    p = a.p
    kind = p.choice("kind", ["elbow", "elbow", "elbow_up", "tee", "cross"])
    r = p.choice("radius", [0.09, 0.18, 0.18, 0.35])
    arm = max(p.choice("arm", [0.5, 1.0]), r * 2.5)
    z = max(p.value("axis_height", r + rng.uniform(0.25, 0.6)), r + 0.15)
    sides = 8 if r < 0.3 else 10
    mat = p.material(["M_Wall", "M_Metal"])
    glow = p.glow()
    body, lights = a.part("Pipe"), a.part("Glow")
    a.meta.update({"kind": kind, "radius": r, "arm_m": arm})
    center = (0.0, 0.0, z)
    body.add(sphere(r * 1.04, sides, 4, mat), loc=center)  # rounded knuckle where the arms meet
    rots = {(1, 0, 0): ALONG_X, (0, 1, 0): ALONG_Y, (0, 0, 1): (0.0, 0.0, 0.0)}
    for d in BEND_ARMS[kind]:
        rot = rots[tuple(abs(c) for c in d)]
        pos = lambda f: (d[0] * f, d[1] * f, z + d[2] * f)  # noqa: E731
        cyl(body, r, arm - 0.02, pos(arm / 2), mat, sides=sides, rot=rot)
        cyl(body, r * 1.25, 0.12, pos(arm - 0.06), "M_RobotDark", sides=sides, rot=rot)
    first = BEND_ARMS[kind][0]
    cyl(lights, r * 1.06, 0.08, (first[0] * arm * 0.45, 0, z), glow, sides=sides, rot=ALONG_X)
    if p.bool("support", 0.6):
        sh = z - r * 0.5
        cube(body, (max(0.12, r * 1.2), r * 2.2, sh), (0, 0, sh / 2), "M_RobotDark", bevel=0.02)
    a.behaviour("SignalIndicator", {"renderers": ["Glow"]}, {"offMaterial": "M_RobotDark", "onMaterial": "M_GlowCyan"},
                note="glow ring shows whether the line carries a signal")


# --------------------------------------------------------------------------
# fan
# --------------------------------------------------------------------------

@model("fan", "Fan", "industrial", "Large fan: round fan on a stand or square box fan, guard grille, rotor (Rotor)",
       params=[
           Param("style", "choice", "Bauform", choices=("stand", "box")),
           Param("radius", "float", "Rotor-Radius (m)", lo=0.2, hi=1.5, size=True, snap_factor=2),
           Param("guard", "bool", "Schutzgitter"),
           Param("speed", "float", "Tempo (°/s)", lo=0, hi=2000, unity=True, default=360),
       ])
def fan_unit(rng, a):
    p = a.p
    style = p.choice("style", ["stand", "box"])
    r = p.float("radius", 0.35, 0.8)
    body = a.part("Body")
    mat = p.material(["M_Wall", "M_RobotDark", "M_Metal", "M_Platform"])
    a.meta["style"] = style
    if style == "stand":
        zc = r + rng.uniform(0.5, 0.9)
        cyl(body, r * 0.7, 0.08, (0, 0, 0.04), "M_RobotDark", sides=10, bevel=0.02)
        cyl(body, 0.05, zc - r * 0.3, (0, 0.12, (zc - r * 0.3) / 2), "M_Metal", sides=6)
        for sx in (-1, 1):  # yoke
            cube(body, (0.05, 0.05, r * 0.5), (sx * (r + 0.08), 0.12, zc - r * 0.25), "M_Metal")
        cube(body, (2 * r + 0.21, 0.05, 0.05), (0, 0.12, zc - r * 0.5), "M_Metal")
        n = 14
        for i in range(n):  # round housing ring
            ang = 2 * math.pi * i / n
            cube(body, (2 * math.pi * (r + 0.04) / n * 1.06, 0.22, 0.05),
                 (math.cos(ang) * (r + 0.04), 0, zc + math.sin(ang) * (r + 0.04)), mat, rot=(0, math.pi / 2 - ang, 0))
    else:
        zc = r + 0.12
        side = 2 * r + 0.16
        for sx in (-1, 1):
            cube(body, (0.08, 0.3, side), (sx * (side / 2 - 0.04), 0, zc), mat, bevel=0.015)
            cube(body, (side, 0.3, 0.08), (0, 0, zc + sx * (side / 2 - 0.04)), mat, bevel=0.015)
            cube(body, (0.1, 0.5, 0.06), (sx * side * 0.35, 0, 0.03 + zc - side / 2 - 0.06), "M_RobotDark")
        cube(body, (side * 0.2, 0.04, 0.1), (side * 0.3, -0.16, zc - side / 2 + 0.12), "M_Warning")
    cyl(body, r * 0.3, 0.2, (0, 0.12, zc), "M_RobotDark", sides=8, rot=ALONG_Y)  # motor
    for k in range(3):  # struts from the motor to the housing
        ang = deg(90 + 120 * k)
        cube(body, (r * 0.8, 0.03, 0.03), (math.cos(ang) * r * 0.55, 0.1, zc + math.sin(ang) * r * 0.55), "M_Metal",
             rot=(0, -ang, 0))
    center = (0.0, -0.02, zc)
    blades = rng.choice([3, 4, 5, 6])
    fan(a.part("Rotor", pivot=center), center, r * 0.95, blades, rng.choice(["M_Platform", "M_Metal", "M_Wall"]),
        axis="y")
    if p.bool("guard", 0.6):
        for k in range(-3, 4):  # bars in front of the rotor
            half = math.sqrt(max(0.0, (r * 1.02) ** 2 - (k * r / 3.5) ** 2))
            cube(body, (0.02, 0.02, 2 * half), (k * r / 3.5, -0.13, zc), "M_Metal")
        cube(body, (2 * r, 0.025, 0.025), (0, -0.135, zc), "M_Metal")
    cube(a.part("Lights"), (0.05, 0.02, 0.05), (r * 0.25, 0.01, zc + r * 0.25), "M_GlowCyan")
    a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "forward", "speed": p.option("speed")})


# --------------------------------------------------------------------------
# pump
# --------------------------------------------------------------------------

@model("pump", "Pump", "industrial", "Pump unit on a skid: motor with fins, coupling (Rotor), pump housing, pipe "
       "stubs, status glow (Machine)", params=[
           Param("size", "float", "Größe (Motor-Radius, m)", lo=0.1, hi=0.6, size=True),
           Param("outlet", "choice", "Auslass", choices=("up", "side")),
           Param("guard", "bool", "Kupplungsschutz (statt offener Kupplung)"),
           _status_param(),
           Param("rotor_speed", "float", "Kupplungs-Tempo (°/s)", lo=0, hi=3000, unity=True, default=720,
                 description="Nur ohne Kupplungsschutz"),
       ])
def pump(rng, a):
    p = a.p
    r = p.float("size", 0.18, 0.3)
    ml = r * rng.uniform(2.2, 3.0)
    pr = r * rng.uniform(1.2, 1.6)
    status = STATUS[p.option("status")]
    mat = p.material(["M_Wall", "M_HazardOrange", "M_RobotBody", "M_Metal"])
    body, glow = a.part("Body"), a.part("Glow")
    z = pr + 0.18
    length = ml + 0.3 + pr * 1.2
    x_motor = -length / 2 + ml / 2
    cube(body, (length + 0.2, pr * 2 + 0.2, 0.12), (0, 0, 0.06), "M_RobotDark", bevel=0.02)  # skid
    cyl(body, r, ml, (x_motor, 0, z), mat, sides=10, bevel=0.02, rot=ALONG_X)
    for i in range(int(ml / 0.06)):  # cooling fins
        cyl(body, r * 1.12, 0.015, (x_motor - ml / 2 + 0.05 + i * 0.06, 0, z), mat, sides=10, rot=ALONG_X)
    cyl(body, r * 0.85, 0.1, (x_motor - ml / 2 - 0.04, 0, z), "M_RobotDark", sides=10, rot=ALONG_X)  # fan cover
    for sx in (-1, 1):  # feet under the motor
        cube(body, (0.08, r * 2, z - r * 0.6), (x_motor + sx * ml * 0.3, 0, 0.12 + (z - r * 0.6 - 0.12) / 2),
             "M_RobotDark")
    cube(body, (r * 0.9, r * 0.8, r * 0.6), (x_motor, 0, z + r + 0.1), "M_RobotDark", bevel=0.02)  # terminal box
    cube(glow, (r * 0.6, 0.02, r * 0.18), (x_motor, -r * 0.42, z + r + 0.12), status)
    xc = x_motor + ml / 2 + 0.15
    if p.bool("guard", 0.5):
        cube(body, (0.3, r * 1.6, r * 1.6), (xc, 0, z), "M_Warning", bevel=0.02)
        a.meta["guard"] = True
    else:
        cyl(body, r * 0.15, 0.32, (xc, 0, z), "M_Metal", sides=6, rot=ALONG_X)
        center = (xc, 0.0, z)
        rotor = a.part("Rotor", pivot=center)
        cyl(rotor, r * 0.6, 0.08, center, "M_RobotDark", sides=8, rot=ALONG_X)
        cube(rotor, (0.09, r * 1.0, r * 0.18), center, "M_HazardOrange")
    xp = xc + 0.15 + pr * 0.6
    cyl(body, pr, pr * 1.0, (xp, 0, z), p.material(["M_Metal", "M_Wall"]), sides=12, bevel=0.03, rot=ALONG_Y)
    cyl(body, pr * 0.4, pr * 1.3, (xp, 0, z), "M_RobotDark", sides=8, rot=ALONG_Y)
    cube(body, (pr * 1.2, pr * 1.2, z - pr * 0.6), (xp, 0, 0.12 + (z - pr * 0.6 - 0.12) / 2), "M_RobotDark")
    inlet = (xp, -pr * 0.65 - 0.25, z)
    cyl(body, pr * 0.35, 0.5, inlet, "M_Metal", sides=8, rot=ALONG_Y)
    cyl(body, pr * 0.48, 0.06, (xp, -pr * 0.65 - 0.47, z), "M_RobotDark", sides=8, rot=ALONG_Y)
    if p.choice("outlet", ["up", "side"]) == "up":
        cyl(body, pr * 0.3, 0.6, (xp, 0, z + pr + 0.25), "M_Metal", sides=8)
        cyl(body, pr * 0.42, 0.06, (xp, 0, z + pr + 0.52), "M_RobotDark", sides=8)
    else:
        cyl(body, pr * 0.3, 0.5, (xp + pr * 0.6 + 0.2, 0, z), "M_Metal", sides=8, rot=ALONG_X)
        cyl(body, pr * 0.42, 0.06, (xp + pr * 0.6 + 0.42, 0, z), "M_RobotDark", sides=8, rot=ALONG_X)
    parts = {"body": "Body", "glow": "Glow"}
    if a.get("Rotor"):
        parts["rotor"] = "Rotor"
        a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "right", "speed": p.option("rotor_speed")},
                    note="enabled by Machine while it runs")
    a.behaviour("Machine", parts, {"needsPower": True},
                note="Glow: M_GlowRed off / M_GlowCyan running / M_GlowOrange broken")


# --------------------------------------------------------------------------
# transformer
# --------------------------------------------------------------------------

@model("transformer", "Transformer", "industrial", "Power transformer: tank with cooling fins, insulator bushings, "
       "optional conservator, warning sign, status glow (Machine)", params=[
           Param("width", "float", "Breite (m)", lo=0.6, hi=3.0, size=True),
           Param("height", "float", "Höhe (m)", lo=0.6, hi=2.5, size=True),
           Param("bushings", "int", "Isolatoren", lo=1, hi=6),
           Param("conservator", "bool", "Ausgleichsbehälter oben"),
           _status_param(),
       ])
def transformer(rng, a):
    p = a.p
    w = p.float("width", 1.0, 1.8)
    h = p.float("height", 1.0, 1.6)
    d = w * rng.uniform(0.5, 0.7)
    mat = p.material(["M_Wall", "M_Metal", "M_RobotBody"])
    status = STATUS[p.option("status")]
    body, glow = a.part("Body"), a.part("Glow")
    cube(body, (w + 0.15, d + 0.15, 0.15), (0, 0, 0.075), "M_RobotDark", bevel=0.02)
    cube(body, (w, d, h), (0, 0, 0.15 + h / 2), mat, bevel=0.03)
    cube(body, (w + 0.05, d + 0.05, 0.08), (0, 0, 0.15 + h), "M_RobotDark", bevel=0.01)
    fins = max(3, int(d / 0.09))
    for sx in (-1, 1):  # radiator fins on both sides
        for i in range(fins):
            cube(body, (0.22, 0.025, h * 0.75), (sx * (w / 2 + 0.11), -d / 2 + 0.06 + i * (d - 0.12) / (fins - 1),
                                                 0.15 + h * 0.48), mat)
        cube(body, (0.24, d - 0.06, 0.05), (sx * (w / 2 + 0.11), 0, 0.15 + h * 0.86), "M_RobotDark")
    top = 0.19 + h
    n = p.int("bushings", 2, 3)
    for i in range(n):  # insulator stacks (sheds) with a metal cap
        x = -w * 0.3 + i * w * 0.6 / max(1, n - 1) if n > 1 else 0.0
        bh = rng.uniform(0.35, 0.55)
        profile = [(0.06, 0.0)]
        sheds = 5
        for k in range(sheds):
            z0 = bh * k / sheds
            profile += [(0.06, z0 + 0.01), (0.12, z0 + bh / sheds * 0.4), (0.06, z0 + bh / sheds * 0.6)]
        profile += [(0.05, bh), (0.0, bh)]
        body.add(lathe(profile, 8, "M_PortalPanel"), loc=(x, -d * 0.15, top))
        cyl(body, 0.05, 0.06, (x, -d * 0.15, top + bh + 0.03), "M_Metal", sides=6)
    if p.bool("conservator", 0.5):
        cr = min(0.22, h * 0.15)
        cl = w * 0.7
        for sx in (-1, 1):
            cube(body, (0.05, 0.05, 0.4), (sx * cl * 0.35, d * 0.3, top + 0.2), "M_RobotDark")
        cyl(body, cr, cl, (0, d * 0.3, top + 0.4 + cr), mat, sides=10, bevel=0.03, rot=ALONG_X)
        a.meta["conservator"] = True
    yf = -d / 2 - 0.005
    cube(body, (0.3, 0.01, 0.26), (w * 0.2, yf, 0.15 + h * 0.6), "M_Warning", rot=(0, deg(45), 0))  # sign
    cube(body, (0.04, 0.012, 0.18), (w * 0.2, yf - 0.002, 0.15 + h * 0.6), "M_RobotDark", rot=(0, deg(20), 0))
    cube(body, (w * 0.25, 0.04, h * 0.25), (-w * 0.25, yf - 0.02, 0.15 + h * 0.35), "M_RobotDark", bevel=0.01)
    cube(glow, (w * 0.15, 0.02, 0.05), (-w * 0.25, yf - 0.045, 0.15 + h * 0.4), status)
    a.behaviour("Machine", {"body": "Body", "glow": "Glow"}, {"needsPower": False},
                note="power source: Glow shows whether it is live")


# --------------------------------------------------------------------------
# reactor core
# --------------------------------------------------------------------------

@model("reactor_core", "ReactorCore", "industrial", "Reactor core: stepped plinth, glass column with a turning "
       "crystal core (Rotor), pillars, cap and coolant pipes (Machine)", params=[
           Param("radius", "float", "Radius (m)", lo=0.4, hi=1.8, size=True, snap_factor=2),
           Param("height", "float", "Höhe (m)", lo=1.5, hi=5.0, size=True),
           Param("pillars", "int", "Säulen", lo=3, hi=8),
           Param("pipes", "bool", "Kühlrohre"),
           _status_param(),
           Param("rotor_speed", "float", "Kern-Tempo (°/s)", lo=0, hi=720, unity=True, default=30),
       ])
def reactor_core(rng, a):
    p = a.p
    R = p.float("radius", 0.7, 1.2)
    H = p.float("height", 2.2, 3.4)
    status = STATUS[p.option("status")]
    body, glow = a.part("Body"), a.part("Glow")
    mat = p.material(["M_Wall", "M_RobotDark", "M_Metal"])
    cyl(body, R * 1.4, 0.15, (0, 0, 0.075), "M_RobotDark", sides=8, bevel=0.02)
    cyl(body, R * 1.15, 0.2, (0, 0, 0.25), mat, sides=8, bevel=0.02)
    cyl(glow, R * 1.17, 0.05, (0, 0, 0.3), status, sides=8)
    base = 0.35
    cap_h = H * 0.18
    col = H - base - cap_h
    gr = R * 0.6
    cyl(body, gr * 1.15, 0.12, (0, 0, base + 0.06), "M_RobotDark", sides=10)
    cyl(body, gr, col - 0.24, (0, 0, base + col / 2), "M_Glass", sides=10)
    for f in (0.33, 0.66):
        cyl(body, gr * 1.06, 0.08, (0, 0, base + col * f), "M_RobotDark", sides=10)
    cyl(body, gr * 1.15, 0.12, (0, 0, base + col - 0.06), "M_RobotDark", sides=10)
    n = p.int("pillars", 4, 6)
    for i in range(n):
        ang = 2 * math.pi * i / n + math.pi / n
        x, y = math.cos(ang) * R * 0.95, math.sin(ang) * R * 0.95
        cube(body, (0.16, 0.16, col + 0.1), (x, y, base + col / 2), mat, bevel=0.02, rot=(0, 0, ang))
        cube(glow, (0.04, 0.02, col * 0.6), (x * 1.09, y * 1.09, base + col / 2), status, rot=(0, 0, ang))
    top = base + col
    body.add(lathe([(R * 1.05, 0.0), (R * 1.05, cap_h * 0.4), (R * 0.6, cap_h * 0.9), (R * 0.25, cap_h),
                    (0.0, cap_h)], 8, mat), loc=(0, 0, top))
    cyl(body, R * 0.18, 0.3, (0, 0, top + cap_h + 0.1), "M_RobotDark", sides=8)
    center = (0.0, 0.0, base + col / 2)
    core = a.part("Rotor", pivot=center)
    cr = gr * 0.45
    cyl(core, cr, col * 0.55, center, "M_Crystal", sides=6)
    for dz in (-1, 1):
        cyl(core, cr, col * 0.12, (0, 0, center[2] + dz * col * 0.335), "M_Crystal", sides=6,
            radius_top=0.0, rot=(0 if dz > 0 else math.pi, 0, 0))
    for f in (-0.18, 0.0, 0.18):
        core.add(torus(cr * 1.5, 0.02, 10, 4, "M_Metal"), loc=(0, 0, center[2] + col * f))
    if p.bool("pipes", 0.7):
        for i in range(4):
            ang = math.pi / 2 * i
            start = (math.cos(ang) * R * 0.7, math.sin(ang) * R * 0.7, top + cap_h * 0.5)
            mid = (math.cos(ang) * R * 1.5, math.sin(ang) * R * 1.5, top + cap_h * 0.2)
            foot = (math.cos(ang) * R * 1.5, math.sin(ang) * R * 1.5, 0.15)
            strut(body, start, mid, 0.07, "M_Metal", sides=8)
            strut(body, mid, foot, 0.07, "M_Metal", sides=8)
            cyl(body, 0.1, 0.12, (mid[0], mid[1], mid[2] - 0.02), "M_RobotDark", sides=8)
            cyl(body, 0.12, 0.08, foot, "M_RobotDark", sides=8)
    a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": p.option("rotor_speed")},
                note="crystal core, enabled by Machine while it runs")
    a.behaviour("Machine", {"body": "Body", "glow": "Glow", "rotor": "Rotor"}, {"needsPower": False},
                note="power source; Glow red off / cyan running / orange broken")


# --------------------------------------------------------------------------
# tech: hologram, monitor wall, intercom
# --------------------------------------------------------------------------

@model("hologram", "Hologram", "tech", "Hologram projector: round table or pedestal with a turning projection "
       "(Rotor): globe, station or cube", params=[
           Param("style", "choice", "Sockel", choices=("table", "pedestal")),
           Param("kind", "choice", "Projektion", choices=("globe", "station", "cube")),
           Param("radius", "float", "Radius (m)", lo=0.3, hi=1.5, size=True, snap_factor=2),
           Param("speed", "float", "Dreh-Tempo (°/s)", lo=0, hi=360, unity=True, default=20),
           Param("mode", "choice", "SignalLight-Modus", choices=("Steady", "Pulse", "Blink"), unity=True,
                 default="Pulse"),
       ])
def hologram(rng, a):
    p = a.p
    style = p.choice("style", ["table", "pedestal"])
    kind = p.choice("kind", ["globe", "station", "cube"])
    R = p.float("radius", 0.45, 0.9)
    light = p.glow(weights=(0.85, 0.05, 0.1))
    body, glow = a.part("Body"), a.part("Glow")
    mat = p.material(["M_RobotDark", "M_Wall", "M_Metal"])
    a.meta.update({"style": style, "kind": kind})
    if style == "table":
        top = rng.uniform(0.85, 1.0)
        cyl(body, R * 0.5, 0.1, (0, 0, 0.05), "M_RobotDark", sides=10)
        cyl(body, R * 0.25, top - 0.15, (0, 0, (top - 0.05) / 2), mat, sides=10)
        cyl(body, R, 0.1, (0, 0, top - 0.05), mat, sides=12, bevel=0.02)
        cyl(glow, R * 1.02, 0.03, (0, 0, top - 0.06), light, sides=12)
    else:
        top = rng.uniform(1.0, 1.3)
        cyl(body, R * 0.6, 0.15, (0, 0, 0.075), "M_RobotDark", sides=8, bevel=0.02)
        cyl(body, R * 0.35, top - 0.15, (0, 0, 0.15 + (top - 0.15) / 2), mat, sides=8, radius_top=R * 0.45)
        cyl(glow, R * 0.47, 0.03, (0, 0, top - 0.02), light, sides=8)
    cyl(body, R * 0.3, 0.05, (0, 0, top + 0.02), "M_Metal", sides=10)
    cyl(glow, R * 0.2, 0.02, (0, 0, top + 0.05), light, sides=10)  # projector lens
    size = R * rng.uniform(0.45, 0.6)
    zc = top + 0.15 + size
    center = (0.0, 0.0, zc)
    holo = a.part("Rotor", pivot=center)
    if kind == "globe":
        holo.add(sphere(size, 10, 6, "M_Crystal"), loc=center)
        for tilt in (deg(20), deg(-35)):
            holo.add(torus(size * 1.35, 0.012, 16, 3, light), loc=center, rot=(tilt, 0, 0))
        cyl(holo, size * 0.2, size * 0.15, (size * 0.9, 0, zc + size * 0.9), light, sides=6)  # moon
    elif kind == "station":
        holo.add(torus(size, size * 0.08, 14, 4, "M_Crystal"), loc=center)
        cyl(holo, size * 0.15, size * 1.2, center, "M_Crystal", sides=6)
        for k in range(4):
            ang = math.pi / 2 * k
            cube(holo, (size, 0.025, 0.025), (math.cos(ang) * size / 2, math.sin(ang) * size / 2, zc), light,
                 rot=(0, 0, ang))
    else:  # wireframe cube with a solid inner cube
        e = size * 0.8
        for ax in range(3):
            for s1 in (-1, 1):
                for s2 in (-1, 1):
                    pos = [0.0, 0.0, 0.0]
                    others = [i for i in range(3) if i != ax]
                    pos[others[0]], pos[others[1]] = s1 * e, s2 * e
                    dims = [0.025, 0.025, 0.025]
                    dims[ax] = 2 * e + 0.025
                    cube(holo, tuple(dims), (pos[0], pos[1], zc + pos[2]), light)
        cube(holo, (e * 0.8, e * 0.8, e * 0.8), center, "M_Crystal", rot=(deg(35), deg(45), 0))
    a.behaviour("Rotator", {"target": "Rotor"}, {"axis": "up", "speed": p.option("speed")})
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})


@model("monitor_wall", "MonitorWall", "tech", "Wall of 2-12 screens (Screen) with graph overlays, brackets and "
       "cables", pivot="wall", params=[
           Param("columns", "int", "Spalten", lo=1, hi=4),
           Param("rows", "int", "Reihen", lo=1, hi=3),
           Param("screen", "float", "Bildschirmbreite (m)", lo=0.3, hi=1.2, size=True),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=1.0, hi=3.0),
           Param("mode", "choice", "SignalLight-Modus", choices=("Steady", "Pulse", "Blink"), unity=True,
                 default="Steady"),
       ])
def monitor_wall(rng, a):
    p = a.p
    cols = p.int("columns", 2, 4)
    rows = p.int("rows", 1, 3)
    sw = p.float("screen", 0.45, 0.7)
    sh = sw * 0.6
    gap = 0.05
    w, h = cols * (sw + gap) + gap, rows * (sh + gap) + gap
    z = max(p.value("mount_height", rng.uniform(1.6, 2.0)), h / 2 + 0.3)
    body, screen, lights = a.part("Body"), a.part("Screen"), a.part("Lights")
    light = p.glow(weights=(0.8, 0.05, 0.15))
    cube(body, (w * 0.6, 0.06, h * 0.6), (0, 0.07, z), "M_Metal")  # wall bracket
    cube(body, (w, 0.08, h), (0, 0.0, z), "M_RobotDark", bevel=0.015)
    other = [m for m in ("M_GlowCyan", "M_GlowOrange", "M_GlowRed", "M_Platform") if m != light]
    for c in range(cols):
        for r in range(rows):
            x = -w / 2 + gap + sw / 2 + c * (sw + gap)
            zz = z - h / 2 + gap + sh / 2 + r * (sh + gap)
            cube(screen, (sw, 0.02, sh), (x, -0.045, zz), light)
            content = rng.choice(["bars", "lines", "dot", "none"])
            if content == "bars":
                for k in range(5):
                    bh = sh * rng.uniform(0.15, 0.7)
                    cube(lights, (sw * 0.1, 0.01, bh), (x - sw * 0.35 + k * sw * 0.17, -0.057, zz - sh * 0.4 + bh / 2),
                         rng.choice(other))
            elif content == "lines":
                for k in range(3):
                    cube(lights, (sw * rng.uniform(0.3, 0.8), 0.01, 0.015),
                         (x - sw * 0.05, -0.057, zz + sh * 0.25 - k * sh * 0.2), "M_RobotDark")
            elif content == "dot":
                cyl(lights, sh * 0.25, 0.01, (x, -0.057, zz), rng.choice(other), sides=10, rot=ALONG_Y)
    for k in range(rng.randint(2, 4)):  # cables down the wall
        x = -w * 0.3 + k * w * 0.2
        cyl(body, 0.015, z - h / 2 - 0.1, (x, 0.06, (z - h / 2 - 0.1) / 2 + 0.1), rng.choice(["M_RobotDark",
                                                                                             "M_HazardOrange"]),
            sides=6)
    a.meta.update({"columns": cols, "rows": rows})
    a.behaviour("SignalLight", {"glow": "Screen"}, {"mode": p.option("mode")})


@model("intercom", "Intercom", "tech", "Wall intercom: speaker grille, call button (Button), LED; video version "
       "with a screen and camera", pivot="wall", params=[
           Param("style", "choice", "Art", choices=("audio", "video")),
           Param("mount_height", "float", "Mitte über Boden (m)", lo=0.8, hi=2.2),
           Param("mode", "choice", "LED-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Blink"),
       ])
def intercom(rng, a):
    p = a.p
    style = p.choice("style", ["audio", "video"])
    w, h, d = rng.uniform(0.18, 0.26), rng.uniform(0.3, 0.42), rng.uniform(0.05, 0.08)
    z = max(p.value("mount_height", rng.uniform(1.3, 1.5)), h / 2 + 0.05)
    yf = 0.1 - d
    body, glow = a.part("Body"), a.part("Glow")
    a.meta["style"] = style
    cube(body, (w, d, h), (0, 0.1 - d / 2, z), p.material(["M_Metal", "M_Wall", "M_RobotDark", "M_RobotBody"]),
         bevel=0.015)
    if style == "video":
        cube(a.part("Screen"), (w * 0.75, 0.015, h * 0.25), (0, yf - 0.005, z + h * 0.22), p.glow())
        cyl(body, 0.02, 0.02, (0, yf - 0.01, z + h * 0.43), "M_Glass", sides=8, rot=ALONG_Y)
        grille_z = z - h * 0.08
    else:
        grille_z = z + h * 0.15
    for k in range(5):  # speaker slots
        cube(body, (w * 0.6, 0.012, 0.012), (0, yf - 0.004, grille_z + 0.06 - k * 0.03), "M_Ground")
    center = (0.0, yf - 0.015, z - h * 0.32)
    btn = a.part("Button", pivot=center)
    cyl(btn, w * 0.16, 0.03, center, rng.choice(["M_Platform", "M_HazardOrange", "M_Warning"]), sides=10,
        rot=ALONG_Y)
    cube(glow, (0.03, 0.015, 0.03), (w * 0.3, yf - 0.005, z - h * 0.32), "M_GlowCyan")
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="Button moves ~1 cm towards the wall (Unity -Z) when pressed")
