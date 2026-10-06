"""Robots: drones, service robots, robot arms, sentry turrets, spider bots and androids
(``M_RobotBody`` / ``M_RobotDark``).

Joints are separate parts with their pivot in the joint and a parent chain,
so Unity can animate them: drone propellers ``Rotor_<n>``; robot arm
``Turret`` -> ``Arm_Lower`` -> ``Arm_Upper`` -> ``Gripper``; service robot and
android ``Head``; sentry ``Turret`` -> ``Gun``; spider bot ``Leg_<n>`` (pivot at the hip).
"""

from __future__ import annotations

import math

from ..geometry import sphere
from ..params import Param
from .common import ALONG_X, ALONG_Y, add_vec, cube, cyl, deg, rotated, strut, sweep_param, sweep_rotator
from .registry import model


def _eye(a, center, r, glow, sides=8):
    """Round glowing eye facing the front (-Y) in a dark socket."""
    cyl(a.part("Body"), r * 1.3, 0.04, add_vec(center, (0, 0.01, 0)), "M_RobotDark", sides=sides, rot=ALONG_Y)
    cyl(a.part("Glow"), r, 0.04, add_vec(center, (0, -0.01, 0)), glow, sides=sides, rot=ALONG_Y)


@model("drone", "Drone", "robots", "Hovering drone: body, 2-4 propellers (Rotor_<n>), glowing eye, optional claw or "
       "spotlight (pivot in the centre)", pivot="center", params=[
           Param("rotors", "choice", "Propeller", choices=(2, 3, 4)),
           Param("size", "float", "Größe (m)", lo=0.3, hi=1.5, size=True),
           Param("tool", "choice", "Werkzeug", choices=("none", "claw", "spotlight")),
           Param("rotor_speed", "float", "Propeller-Tempo (°/s)", lo=0, hi=3000, unity=True, default=1440),
           Param("mode", "choice", "Augen-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Pulse"),
       ])
def drone(rng, a):
    p = a.p
    n = p.choice("rotors", [2, 4, 4, 3])
    s = p.float("size", 0.5, 0.9)
    glow = p.glow(weights=(0.6, 0.3, 0.1))
    shell = p.material(["M_RobotBody", "M_Platform", "M_RobotDark", "M_Wall"])
    body = a.part("Body")
    a.meta["rotors"] = n
    if rng.random() < 0.5:
        cyl(body, s * 0.35, s * 0.3, (0, 0, 0), shell, sides=8, bevel=0.03)
        cyl(body, s * 0.3, s * 0.12, (0, 0, s * 0.2), "M_RobotDark", sides=8, radius_top=s * 0.18)
        front = s * 0.35 * math.cos(math.pi / 8)
    else:
        cube(body, (s * 0.6, s * 0.6, s * 0.28), (0, 0, 0), shell, bevel=0.04)
        cube(body, (s * 0.4, s * 0.4, s * 0.1), (0, 0, s * 0.18), "M_RobotDark", bevel=0.02)
        front = s * 0.3
    _eye(a, (0, -front - 0.02, -s * 0.02), s * 0.09, glow)
    arm = s * 0.65
    for i in range(n):
        ang = 2 * math.pi * i / n + (math.pi / n if n != 3 else math.pi / 2)
        dx, dy = math.cos(ang), math.sin(ang)
        cube(body, (arm, s * 0.08, s * 0.06), (dx * arm / 2, dy * arm / 2, s * 0.06), "M_RobotDark",
             rot=(0, 0, ang))
        hub = (dx * arm, dy * arm, s * 0.1)
        cyl(body, s * 0.07, s * 0.12, hub, "M_Metal", sides=8)
        guard = s * 0.32
        cyl(body, guard, s * 0.04, (hub[0], hub[1], s * 0.12), "M_RobotDark", sides=10, radius_top=guard * 1.02)
        center = (hub[0], hub[1], s * 0.2)
        rotor = a.part(f"Rotor_{i + 1}", pivot=center)
        cyl(rotor, s * 0.035, s * 0.05, center, "M_RobotDark", sides=6)
        for k in range(2):
            cube(rotor, (guard * 1.8, s * 0.06, 0.012), center, "M_Platform", rot=(deg(12), 0, ang + math.pi / 2 * k))
        a.behaviour("Rotator", {"target": f"Rotor_{i + 1}"},
                    {"axis": "up", "speed": p.option("rotor_speed") * (1 if i % 2 == 0 else -1)})
    tool = p.choice("tool", ["none", "claw", "spotlight"])
    a.meta["tool"] = tool
    if tool == "claw":
        cyl(body, s * 0.04, s * 0.25, (0, 0, -s * 0.25), "M_Metal", sides=6)
        for k in range(3):
            ang = 2 * math.pi * k / 3
            cube(body, (s * 0.03, s * 0.03, s * 0.2), (math.cos(ang) * s * 0.06, math.sin(ang) * s * 0.06,
                                                         -s * 0.45), "M_Metal",
                 rot=(math.sin(ang) * deg(25), -math.cos(ang) * deg(25), 0))
    elif tool == "spotlight":
        cube(body, (s * 0.2, s * 0.25, s * 0.15), (0, -s * 0.1, -s * 0.22), "M_RobotDark", bevel=0.01)
        cube(a.part("Lights"), (s * 0.14, 0.01, s * 0.1), (0, -s * 0.23, -s * 0.22), "M_GlowCyan")
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})


@model("service_robot", "ServiceRobot", "robots", "Service robot: wheels or treads, body with panel, turning head "
       "(Head) with glowing eye, tool arm", params=[
           Param("drive", "choice", "Antrieb", choices=("wheels", "treads", "hover")),
           Param("height", "float", "Höhe (m)", lo=0.5, hi=2.2, size=True),
           Param("arms", "choice", "Arme", choices=(0, 1, 2)),
           Param("antenna", "bool", "Antenne"),
           Param("head_speed", "float", "Kopf-Tempo (°/s, 0 = steht)", lo=0, hi=180, unity=True, default=0),
       ])
def service_robot(rng, a):
    p = a.p
    drive = p.choice("drive", ["wheels", "treads", "hover"])
    h = p.float("height", 0.9, 1.4)
    w = h * rng.uniform(0.4, 0.55)
    shell = p.material(["M_RobotBody", "M_RobotBody", "M_Platform", "M_HazardOrange", "M_Warning"])
    glow = p.glow(weights=(0.7, 0.2, 0.1))
    body = a.part("Body")
    a.meta["drive"] = drive
    base_h = h * 0.15
    if drive == "wheels":
        for x in (-w / 2, w / 2):
            for y in (-w * 0.3, w * 0.3):
                cyl(body, base_h * 0.6, w * 0.12, (x, y, base_h * 0.6), "M_RobotDark", sides=10, rot=ALONG_X)
                cyl(body, base_h * 0.3, w * 0.13, (x, y, base_h * 0.6), "M_Metal", sides=6, rot=ALONG_X)
        z0 = base_h * 0.6
    elif drive == "treads":
        for x in (-w / 2, w / 2):
            cube(body, (w * 0.2, w * 1.1, base_h), (x, 0, base_h / 2), "M_RobotDark", bevel=0.02)
            for y in (-w * 0.45, 0, w * 0.45):
                cyl(body, base_h * 0.35, w * 0.21, (x, y, base_h / 2), "M_Metal", sides=8, rot=ALONG_X)
        z0 = base_h * 0.8
    else:  # hover: glowing ring underneath, body floats
        cyl(body, w * 0.4, base_h * 0.4, (0, 0, base_h * 0.2), "M_RobotDark", sides=10)
        cyl(a.part("Lights"), w * 0.45, 0.03, (0, 0, base_h * 0.45), glow, sides=10)
        z0 = base_h
    bh = h * 0.5
    cube(body, (w * 0.9, w * 0.8, bh), (0, 0, z0 + bh / 2), shell, bevel=0.05)
    cube(body, (w * 0.95, w * 0.85, 0.06), (0, 0, z0 + 0.03), "M_RobotDark")
    cube(body, (w * 0.5, 0.02, bh * 0.4), (0, -w * 0.4 - 0.01, z0 + bh * 0.55), "M_RobotDark")
    for k in range(3):
        cube(a.part("Lights"), (0.04, 0.02, 0.03), (-w * 0.15 + k * w * 0.15, -w * 0.4 - 0.02, z0 + bh * 0.3),
             rng.choice(["M_GlowCyan", "M_GlowRed", "M_GlowOrange"]))
    neck_z = z0 + bh
    cyl(body, w * 0.12, h * 0.06, (0, 0, neck_z + h * 0.03), "M_Metal", sides=8)
    center = (0.0, 0.0, neck_z + h * 0.06)
    head = a.part("Head", pivot=center)
    hh = h * rng.uniform(0.18, 0.25)
    cube(head, (w * 0.7, w * 0.6, hh), (0, 0, center[2] + hh / 2), shell, bevel=0.04)
    cube(head, (w * 0.6, 0.02, hh * 0.5), (0, -w * 0.3 - 0.005, center[2] + hh * 0.55), "M_RobotDark")
    eyes = rng.choice([1, 2])
    for k in range(eyes):
        x = 0.0 if eyes == 1 else (k - 0.5) * w * 0.28
        cyl(a.part("Glow", parent="Head"), hh * 0.12, 0.03, (x, -w * 0.3 - 0.02, center[2] + hh * 0.55), glow,
            sides=8, rot=ALONG_Y)
    if p.bool("antenna", 0.5):
        cyl(head, 0.012, hh * 0.9, (w * 0.25, 0, center[2] + hh + hh * 0.45), "M_Metal", sides=6)
        cube(head, (0.04, 0.04, 0.04), (w * 0.25, 0, center[2] + hh * 1.9), "M_HazardOrange")
    for k in range(p.choice("arms", [0, 1, 1, 2])):  # tool arms on the sides
        s = 1 if k == 0 else -1
        sh = (s * (w * 0.45 + 0.03), 0, z0 + bh * 0.8)
        cyl(body, w * 0.08, 0.06, sh, "M_RobotDark", sides=8, rot=ALONG_X)
        ln = bh * 0.7
        tilt = (deg(rng.uniform(10, 40)), 0, 0)
        cube(body, (0.05, 0.05, ln), add_vec(sh, rotated(tilt, (s * 0.03, 0, -ln / 2))), "M_Metal", rot=tilt)
        tip = add_vec(sh, rotated(tilt, (s * 0.03, 0, -ln)))
        cube(body, (0.08, 0.06, 0.08), tip, "M_RobotDark", bevel=0.01)
        for dx in (-0.025, 0.025):
            cube(body, (0.015, 0.03, 0.08), add_vec(tip, (dx, 0, -0.06)), "M_Metal")
    speed = p.option("head_speed")
    if speed:
        a.behaviour("Rotator", {"target": "Head"}, {"axis": "up", "speed": speed})
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Pulse"}, note="Glow = eyes (child of Head)")


@model("robot_arm", "RobotArm", "robots", "Industrial robot arm: base, turret, lower and upper arm, gripper - "
       "joint chain with pivots (Turret > Arm_Lower > Arm_Upper > Gripper)", params=[
           Param("reach", "float", "Reichweite (m)", lo=0.8, hi=3.0, size=True),
           Param("pose", "choice", "Pose", choices=("rest", "reach", "up")),
           Param("gripper", "choice", "Greifer", choices=("claw", "suction", "welder")),
           Param("turret_speed", "float", "Dreh-Tempo (°/s, 0 = steht)", lo=0, hi=180, unity=True, default=0),
       ])
def robot_arm(rng, a):
    p = a.p
    reach = p.float("reach", 1.2, 2.0)
    pose = p.choice("pose", ["rest", "reach", "up"])
    shell = p.material(["M_HazardOrange", "M_HazardOrange", "M_Warning", "M_RobotBody"])
    glow = p.glow(weights=(0.7, 0.2, 0.1))
    l1, l2 = reach * 0.5, reach * 0.42
    t = reach * 0.08  # arm thickness
    base = a.part("Base")
    cyl(base, reach * 0.22, 0.12, (0, 0, 0.06), "M_RobotDark", sides=8, bevel=0.02)
    cyl(a.part("Glow"), reach * 0.225, 0.03, (0, 0, 0.1), glow, sides=8)
    a.meta["pose"] = pose
    tz = 0.12
    turret = a.part("Turret", pivot=(0.0, 0.0, tz))
    cyl(turret, reach * 0.16, reach * 0.12, (0, 0, tz + reach * 0.06), shell, sides=8, bevel=0.02)
    shoulder = (0.0, 0.0, tz + reach * 0.2)
    for s in (-1, 1):
        cube(turret, (t * 0.5, t * 1.6, reach * 0.15), (s * t * 0.85, 0, tz + reach * 0.15), shell, bevel=0.01)
    cyl(turret, t * 0.55, t * 2.3, shoulder, "M_RobotDark", sides=8, rot=ALONG_X)
    a1, a2 = {"rest": (35.0, 110.0), "reach": (55.0, 40.0), "up": (10.0, 20.0)}[pose]
    a1 += rng.uniform(-8, 8)
    a2 = min(a2 + rng.uniform(-10, 10), 150.0 - a1)  # gripper stays above the floor
    # angles from vertical, leaning to the front (-Y): rotation around X
    r1 = (deg(a1), 0.0, 0.0)
    lower = a.part("Arm_Lower", pivot=shoulder, parent="Turret")
    cube(lower, (t, t, l1), add_vec(shoulder, rotated(r1, (0, 0, l1 / 2))), shell, bevel=0.02, rot=r1)
    cube(lower, (t * 1.05, t * 0.4, l1 * 0.6), add_vec(shoulder, rotated(r1, (0, t * 0.4, l1 / 2))), "M_RobotDark",
         rot=r1)
    elbow = add_vec(shoulder, rotated(r1, (0, 0, l1)))
    cyl(lower, t * 0.5, t * 1.6, elbow, "M_RobotDark", sides=8, rot=ALONG_X)
    r2 = (deg(a1 + a2), 0.0, 0.0)
    upper = a.part("Arm_Upper", pivot=elbow, parent="Arm_Lower")
    cube(upper, (t * 0.8, t * 0.8, l2), add_vec(elbow, rotated(r2, (0, 0, l2 / 2))), shell, bevel=0.02, rot=r2)
    cyl(upper, t * 0.15, l2 * 0.8, add_vec(elbow, rotated(r2, (t * 0.5, 0, l2 / 2))), "M_RobotDark", sides=6,
        rot=r2)  # hydraulic line
    wrist = add_vec(elbow, rotated(r2, (0, 0, l2)))
    gripper = a.part("Gripper", pivot=wrist, parent="Arm_Upper")
    cyl(gripper, t * 0.45, t * 0.5, add_vec(wrist, rotated(r2, (0, 0, t * 0.25))), "M_RobotDark", sides=8, rot=r2)
    kind = p.choice("gripper", ["claw", "suction", "welder"])
    tip = add_vec(wrist, rotated(r2, (0, 0, t * 0.5)))
    if kind == "claw":
        cube(gripper, (t * 1.2, t * 0.4, t * 0.3), add_vec(tip, rotated(r2, (0, 0, t * 0.15))), "M_Metal", rot=r2)
        for s in (-1, 1):
            cube(gripper, (t * 0.15, t * 0.35, t * 0.9), add_vec(tip, rotated(r2, (s * t * 0.5, 0, t * 0.7))),
                 "M_Metal", rot=r2)
    elif kind == "suction":
        cyl(gripper, t * 0.15, t * 0.5, add_vec(tip, rotated(r2, (0, 0, t * 0.25))), "M_Metal", sides=6, rot=r2)
        cyl(gripper, t * 0.5, t * 0.15, add_vec(tip, rotated(r2, (0, 0, t * 0.55))), "M_RobotDark", sides=8,
            radius_top=t * 0.6, rot=r2)
    else:
        cyl(gripper, t * 0.2, t * 0.9, add_vec(tip, rotated(r2, (0, 0, t * 0.45))), "M_Metal", sides=6,
            radius_top=t * 0.08, rot=r2)
        cube(a.part("Lights", parent="Gripper"), (t * 0.15, t * 0.15, t * 0.15),
             add_vec(tip, rotated(r2, (0, 0, t * 0.95))), "M_GlowOrange", rot=r2)
    a.meta["gripper"] = kind
    speed = p.option("turret_speed")
    if speed:
        a.behaviour("Rotator", {"target": "Turret"}, {"axis": "up", "speed": speed})
    a.behaviour("SignalIndicator", {"renderers": ["Glow"]}, {"offMaterial": "M_RobotDark", "onMaterial": glow},
                note="joints: Turret (Unity up), Arm_Lower / Arm_Upper (Unity right), Gripper")


@model("turret", "Turret", "robots", "Sentry turret on a tripod or pedestal: turning Turret with a tilting Gun "
       "(child), laser sight", params=[
           Param("mount", "choice", "Unterbau", choices=("tripod", "pedestal")),
           Param("barrels", "choice", "Läufe", choices=(1, 2)),
           Param("size", "float", "Größe (m)", lo=0.3, hi=1.5, size=True),
           Param("shield", "bool", "Schutzschild"),
           Param("speed", "float", "Schwenk-Tempo (°/s, 0 = steht)", lo=0, hi=360, unity=True, default=0,
                 description="Rotator dreht endlos; 0, bis es ein Schwenk-Script gibt"),
           Param("mode", "choice", "Visier-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Steady"),
           sweep_param(),
       ])
def turret(rng, a):
    p = a.p
    mount = p.choice("mount", ["tripod", "pedestal"])
    s = p.float("size", 0.6, 1.0)
    shell = p.material(["M_RobotBody", "M_Wall", "M_RobotDark", "M_HazardOrange"])
    body = a.part("Body")
    a.meta["mount"] = mount
    if mount == "tripod":
        top = s * 0.8
        for k in range(3):
            ang = deg(90 + 120 * k)
            strut(body, (0, 0, top - 0.05), (math.cos(ang) * s * 0.6, math.sin(ang) * s * 0.6, 0.02), s * 0.035,
                  "M_RobotDark", sides=6)
            cube(body, (s * 0.12, s * 0.12, 0.04), (math.cos(ang) * s * 0.6, math.sin(ang) * s * 0.6, 0.02), "M_Metal")
        cyl(body, s * 0.12, s * 0.15, (0, 0, top - 0.05), "M_Metal", sides=8)
    else:
        top = s * 0.9
        cyl(body, s * 0.45, 0.1, (0, 0, 0.05), "M_RobotDark", sides=8, bevel=0.02)
        cyl(body, s * 0.18, top - 0.1, (0, 0, 0.1 + (top - 0.1) / 2), shell, sides=8, radius_top=s * 0.14)
    center = (0.0, 0.0, top)
    yaw = a.part("Turret", pivot=center)
    cyl(yaw, s * 0.2, s * 0.08, (0, 0, top + s * 0.04), "M_RobotDark", sides=10)
    for sx in (-1, 1):  # yoke arms
        cube(yaw, (s * 0.06, s * 0.2, s * 0.35), (sx * s * 0.26, 0, top + s * 0.2), shell, bevel=0.01)
    if p.bool("shield", 0.5):
        cube(yaw, (s * 0.7, s * 0.04, s * 0.4), (0, -s * 0.24, top + s * 0.25), "M_Metal", bevel=0.01,
             rot=(deg(-10), 0, 0))
        cube(yaw, (s * 0.25, s * 0.045, s * 0.12), (0, -s * 0.245, top + s * 0.25), "M_Ground")  # gun port
    trunnion = (0.0, 0.0, top + s * 0.3)
    gun = a.part("Gun", pivot=trunnion, parent="Turret")
    cube(gun, (s * 0.42, s * 0.5, s * 0.26), (0, s * 0.02, trunnion[2]), shell, bevel=0.02)
    cyl(gun, s * 0.05, s * 0.5, (0, 0, trunnion[2]), "M_Metal", sides=6, rot=ALONG_X)  # trunnion pin
    n = p.choice("barrels", [1, 2])
    for k in range(n):
        x = 0.0 if n == 1 else (k - 0.5) * s * 0.18
        cyl(gun, s * 0.045, s * 0.45, (x, -s * 0.45, trunnion[2] - s * 0.02), "M_RobotDark", sides=8, rot=ALONG_Y)
        cyl(gun, s * 0.06, s * 0.08, (x, -s * 0.66, trunnion[2] - s * 0.02), "M_Metal", sides=8, rot=ALONG_Y)
    cube(gun, (s * 0.12, s * 0.3, s * 0.18), (s * 0.3, 0.0, trunnion[2] - s * 0.04), "M_Warning", bevel=0.01)  # ammo
    cyl(a.part("Glow", parent="Gun"), s * 0.03, s * 0.03, (0, -s * 0.25, trunnion[2] + s * 0.1), "M_GlowRed",
        sides=8, rot=ALONG_Y)
    a.meta["barrels"] = n
    sweep_rotator(a, "Turret", p.option("speed"), p.option("sweep"),
                  "yaw around Unity up; speed 0 = still (a Rotator spins endlessly, not a sweep); Gun tilts "
                  "around Unity right")
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})


@model("spider_bot", "SpiderBot", "robots", "Crawling spider robot: body, 4 or 6 legs (Leg_<n>, pivot at the hip), "
       "eye cluster, optional sensor", params=[
           Param("legs", "choice", "Beine", choices=(4, 6)),
           Param("size", "float", "Größe (m)", lo=0.2, hi=1.5, size=True),
           Param("sensor", "choice", "Aufsatz", choices=("none", "antenna", "dish")),
           Param("mode", "choice", "Augen-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Pulse"),
       ])
def spider_bot(rng, a):
    p = a.p
    n = p.choice("legs", [4, 6, 6])
    s = p.float("size", 0.4, 0.8)
    shell = p.material(["M_RobotDark", "M_RobotBody", "M_Wall", "M_HazardOrange"])
    glow = p.glow(weights=(0.4, 0.5, 0.1))
    body = a.part("Body")
    zb = s * rng.uniform(0.45, 0.6)
    body.add(sphere(1.0, 8, 4, shell), loc=(0, s * 0.1, zb), scale=(s * 0.35, s * 0.45, s * 0.22))
    body.add(sphere(1.0, 8, 4, "M_RobotDark"), loc=(0, -s * 0.32, zb - s * 0.02), scale=(s * 0.2, s * 0.16, s * 0.14))
    eyes = a.part("Glow")
    for ex, ez in ((-0.07, 0.04), (0.07, 0.04), (-0.04, -0.03), (0.04, -0.03)):
        cyl(eyes, s * 0.03, 0.02, (ex * s, -s * 0.47, zb + ez * s), glow, sides=6, rot=ALONG_Y)
    cube(body, (s * 0.3, s * 0.4, 0.03), (0, s * 0.15, zb + s * 0.22), "M_Metal")  # back plate
    half = n // 2
    for i in range(n):
        side = -1 if i < half else 1
        k = i % half
        fy = (k - (half - 1) / 2) * s * 0.35
        hip = (side * s * 0.3, fy, zb)
        spread = (k - (half - 1) / 2) * 0.5
        knee = (side * s * 0.65, fy + spread * s * 0.3, zb + s * 0.25)
        foot = (side * s * 0.95, fy + spread * s * 0.6, 0.0)
        leg = a.part(f"Leg_{i + 1}", pivot=hip)
        cyl(leg, s * 0.06, s * 0.08, hip, "M_RobotDark" if p.style.generation >= 2 else "M_Metal", sides=6,
            rot=ALONG_X)
        strut(leg, hip, knee, s * 0.04, shell, sides=6)
        leg.add(sphere(s * 0.05, 6, 3, "M_RobotDark"), loc=knee)
        strut(leg, knee, foot, s * 0.035, "M_RobotDark", sides=6, radius_end=s * 0.015)
    sensor = p.choice("sensor", ["none", "antenna", "dish"])
    if sensor == "antenna":
        cyl(body, 0.01, s * 0.4, (s * 0.1, s * 0.25, zb + s * 0.4), "M_Metal", sides=6)
        cube(a.part("Lights"), (0.03, 0.03, 0.03), (s * 0.1, s * 0.25, zb + s * 0.6), "M_GlowRed")
    elif sensor == "dish":
        cyl(body, s * 0.04, s * 0.12, (0, s * 0.2, zb + s * 0.28), "M_Metal", sides=6)
        cyl(body, s * 0.14, 0.03, (0, s * 0.2, zb + s * 0.36), "M_Platform", sides=8, radius_top=s * 0.18,
            rot=(deg(-30), 0, 0))
    a.meta.update({"legs": n, "sensor": sensor})
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="Leg_<n> have their pivot at the hip, ready for a walk animation")


@model("android", "Android", "robots", "Humanoid android, standing or slumped against a wall (broken): Head with "
       "glowing visor, chest core", params=[
           Param("pose", "choice", "Haltung", choices=("standing", "slumped")),
           Param("height", "float", "Größe (m)", lo=1.2, hi=2.4, size=True),
           Param("visor", "choice", "Gesicht", choices=("visor", "eyes")),
       ])
def android(rng, a):
    p = a.p
    pose = p.choice("pose", ["standing", "standing", "slumped"])
    H = p.float("height", 1.6, 2.0)
    shell = p.material(["M_RobotBody", "M_Platform", "M_Wall", "M_RobotDark"])
    joint = "M_RobotDark" if shell != "M_RobotDark" else "M_Metal"
    glow = p.glow(weights=(0.7, 0.2, 0.1)) if pose == "standing" else "M_GlowRed"
    body, lights = a.part("Body"), a.part("Glow")
    u = H / 1.8  # proportions of a 1.8 m figure
    a.meta["pose"] = pose
    if pose == "standing":
        hip_z, lean, sit = 0.95 * u, 0.0, False
    else:
        hip_z, lean, sit = 0.16 * u, deg(-20), True
    pelvis = (0.0, 0.0, hip_z)
    up = lambda dz: add_vec(pelvis, rotated((lean, 0, 0), (0, 0, dz)))  # noqa: E731 - along the leaning spine
    cube(body, (0.32 * u, 0.2 * u, 0.16 * u), pelvis, joint, bevel=0.02, rot=(lean, 0, 0))
    chest = up(0.38 * u)
    cube(body, (0.44 * u, 0.26 * u, 0.42 * u), chest, shell, bevel=0.04, rot=(lean, 0, 0))
    cube(body, (0.2 * u, 0.2 * u, 0.2 * u), up(0.13 * u), joint, rot=(lean, 0, 0))  # waist
    cyl(lights, 0.06 * u, 0.04, add_vec(chest, rotated((lean, 0, 0), (0, -0.13 * u, 0.04 * u))), glow, sides=8,
        rot=(lean + math.pi / 2, 0, 0))
    neck = up(0.64 * u)
    cyl(body, 0.05 * u, 0.1 * u, neck, joint, sides=6, rot=(lean, 0, 0))
    tilt = (lean, deg(rng.uniform(-25, 25)) if sit else 0.0, 0.0)
    head = a.part("Head", pivot=neck)
    hc = add_vec(neck, rotated(tilt, (0, 0, 0.15 * u)))
    cube(head, (0.2 * u, 0.24 * u, 0.24 * u), hc, shell, bevel=0.04, rot=tilt)
    if p.choice("visor", ["visor", "eyes"]) == "visor":
        cube(lights, (0.17 * u, 0.02, 0.05 * u), add_vec(hc, rotated(tilt, (0, -0.12 * u, 0.02 * u))), glow, rot=tilt)
    else:
        for sx in (-1, 1):
            cyl(lights, 0.025 * u, 0.02, add_vec(hc, rotated(tilt, (sx * 0.05 * u, -0.12 * u, 0.02 * u))), glow,
                sides=6, rot=(tilt[0] + math.pi / 2, tilt[1], 0))
    for sx in (-1, 1):
        shoulder = add_vec(up(0.55 * u), (sx * 0.27 * u, 0, 0))
        body.add(sphere(0.07 * u, 6, 3, joint), loc=shoulder)
        if sit:
            elbow = (sx * 0.38 * u, shoulder[1] - 0.05 * u, shoulder[2] - 0.28 * u)
            hand = (sx * 0.45 * u, shoulder[1] - 0.25 * u, 0.04 * u)
        else:
            elbow = (sx * 0.32 * u, 0.02 * u, shoulder[2] - 0.3 * u)
            hand = (sx * 0.34 * u, -0.06 * u, shoulder[2] - 0.6 * u)
        strut(body, shoulder, elbow, 0.05 * u, shell, sides=6)
        body.add(sphere(0.05 * u, 6, 3, joint), loc=elbow)
        strut(body, elbow, hand, 0.042 * u, shell, sides=6)
        cube(body, (0.07 * u, 0.06 * u, 0.1 * u), hand, joint)
        hip = (sx * 0.1 * u, 0.0, hip_z - 0.05 * u)
        if sit:
            knee = (sx * 0.14 * u, -0.45 * u, 0.12 * u + rng.uniform(0, 0.15) * u)
            foot = (sx * 0.17 * u, -0.85 * u, 0.06 * u)
        else:
            knee = (sx * 0.11 * u, -0.02 * u, 0.5 * u)
            foot = (sx * 0.12 * u, 0.0, 0.07 * u)
        strut(body, hip, knee, 0.065 * u, shell, sides=6)
        body.add(sphere(0.06 * u, 6, 3, joint), loc=knee)
        strut(body, knee, foot, 0.055 * u, shell, sides=6)
        cube(body, (0.1 * u, 0.2 * u, 0.07 * u), (foot[0], foot[1] - 0.05 * u, max(foot[2], 0.035 * u)), joint,
             bevel=0.01)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": "Steady" if pose == "standing" else "Blink"},
                note="slumped = broken: red flickering eyes")
