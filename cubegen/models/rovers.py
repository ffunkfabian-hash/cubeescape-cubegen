"""More robots: patrol drone, vent crawler, robot dog and an industrial mech.

Joints have their pivots where they turn (``Leg_<n>`` at the hip, ``Head`` at
the neck, ``Torso`` at the waist, ``Rotor_<n>`` on the fan axis), ready for
Unity animations; eyes and status lights are ``Glow`` with ``SignalLight``.
"""

from __future__ import annotations

from ..geometry import sphere
from ..params import Param
from .common import ALONG_X, ALONG_Y, add_vec, cube, cyl, deg, fan, strut
from .registry import model


@model("patrol_drone", "PatrolDrone", "robots", "Patrol drone (pivot in the centre): flat hull, two ducted fans "
       "(Rotor_1/2, Rotator), scanner head underneath (Head) with a searchlight eye (Glow)", pivot="center", params=[
           Param("size", "float", "Größe (m)", lo=0.4, hi=1.6, size=True),
           Param("rotor_speed", "float", "Rotor-Tempo (°/s)", lo=0, hi=3000, unity=True, default=1440),
           Param("scan_speed", "float", "Scanner-Tempo (°/s, 0 = steht)", lo=0, hi=360, unity=True, default=40),
           Param("mode", "choice", "Augen-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Pulse"),
       ])
def patrol_drone(rng, a):
    p = a.p
    s = p.float("size", 0.7, 1.1)
    shell = p.material(["M_RobotBody", "M_RobotDark", "M_Wall", "M_HazardOrange"])
    glow = p.glow(weights=(0.3, 0.6, 0.1))
    body = a.part("Body")
    w, d, t = s * 0.7, s * rng.uniform(0.5, 0.7), s * 0.18
    cube(body, (w, d, t), (0, 0, 0), shell, bevel=0.03)
    cube(body, (w * 0.6, d * 0.7, t * 0.4), (0, d * 0.05, t * 0.65), "M_RobotDark", bevel=0.01)
    cube(body, (w * 0.3, 0.02, t * 0.4), (0, -d / 2 - 0.005, 0), "M_Metal")  # nose plate
    for i, side in enumerate((-1, 1), 1):
        hub = (side * (w / 2 + s * 0.28), 0.0, 0.0)
        cube(body, (s * 0.2, s * 0.1, t * 0.5), (side * (w / 2 + s * 0.05), 0, 0), "M_RobotDark")
        cyl(body, s * 0.27, t * 1.2, hub, shell, sides=12)  # duct ring (closed cylinder look, fan sits on top)
        cyl(body, s * 0.05, t * 0.3, add_vec(hub, (0, 0, t * 0.75)), "M_Metal", sides=6)
        center = add_vec(hub, (0, 0, t * 0.95))
        rotor = a.part(f"Rotor_{i}", pivot=center)
        fan(rotor, center, s * 0.24, 3, "M_Platform")
        a.behaviour("Rotator", {"target": f"Rotor_{i}"},
                    {"axis": "up", "speed": p.option("rotor_speed") * side})
    neck = (0.0, -d * 0.15, -t / 2)
    head = a.part("Head", pivot=neck)
    cyl(head, s * 0.06, s * 0.08, add_vec(neck, (0, 0, -s * 0.04)), "M_Metal", sides=6)
    head.add(sphere(1.0, 8, 4, "M_RobotDark"), loc=add_vec(neck, (0, 0, -s * 0.14)), scale=(s * 0.12, s * 0.12, s * 0.1))
    eye = add_vec(neck, (0, -s * 0.11, -s * 0.15))
    cyl(a.part("Glow", parent="Head"), s * 0.05, 0.02, eye, glow, sides=8, rot=ALONG_Y)
    speed = p.option("scan_speed")
    if speed:
        a.behaviour("Rotator", {"target": "Head"}, {"axis": "up", "speed": speed},
                    note="scanner head turns around Unity up")
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})
    a.meta["size_m"] = round(s, 3)


@model("vent_crawler", "VentCrawler", "robots", "Small crawler for vent shafts: flat body on treads or six legs "
       "(Leg_<n>, pivot at the hip), sensor head with eyes (Glow), antenna", params=[
           Param("drive", "choice", "Antrieb", choices=("treads", "legs")),
           Param("size", "float", "Länge (m)", lo=0.2, hi=0.9, size=True),
           Param("mode", "choice", "Augen-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Blink"),
       ])
def vent_crawler(rng, a):
    p = a.p
    drive = p.choice("drive", ["treads", "legs"])
    s = p.float("size", 0.35, 0.6)
    shell = p.material(["M_RobotDark", "M_HazardOrange", "M_Metal", "M_Wall"])
    glow = p.glow(weights=(0.4, 0.5, 0.1))
    body = a.part("Body")
    w, h = s * 0.55, s * 0.18
    zb = s * 0.12 if drive == "treads" else s * 0.2
    cube(body, (w, s, h), (0, 0, zb + h / 2), shell, bevel=0.01)
    cube(body, (w * 0.7, s * 0.25, h * 0.8), (0, -s * 0.5, zb + h * 0.45), "M_RobotDark", bevel=0.01)  # sensor head
    eyes = a.part("Glow")
    for x in (-1, 1):
        cyl(eyes, s * 0.03, 0.02, (x * w * 0.2, -s * 0.63, zb + h * 0.5), glow, sides=6, rot=ALONG_Y)
    if drive == "treads":
        for x in (-1, 1):
            cube(body, (s * 0.12, s * 0.95, zb * 1.6), (x * (w / 2 + s * 0.06), 0, zb * 0.8), "M_RobotDark", bevel=0.01)
            for k in range(4):
                y = -s * 0.36 + s * 0.24 * k
                cyl(body, zb * 0.55, s * 0.13, (x * (w / 2 + s * 0.06), y, zb * 0.8), "M_Metal", sides=6, rot=ALONG_X)
    else:
        for i in range(6):
            side = -1 if i < 3 else 1
            y = (i % 3 - 1) * s * 0.3
            hip = (side * w / 2, y, zb + h * 0.4)
            knee = (side * (w / 2 + s * 0.18), y, zb + h * 0.9)
            foot = (side * (w / 2 + s * 0.28), y, 0.0)
            leg = a.part(f"Leg_{i + 1}", pivot=hip)
            strut(leg, hip, knee, s * 0.025, shell, sides=6)
            strut(leg, knee, foot, s * 0.02, "M_RobotDark", sides=6, radius_end=s * 0.01)
    cyl(body, 0.006, s * 0.4, (w * 0.3, s * 0.3, zb + h + s * 0.2), "M_Metal", sides=6)
    cube(body, (s * 0.04, s * 0.04, s * 0.04), (w * 0.3, s * 0.3, zb + h + s * 0.4), "M_RobotDark")
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")})
    a.meta.update({"drive": drive, "length_m": round(s, 3)})


@model("robot_dog", "RobotDog", "robots", "Quadruped robot dog: body, four legs (Leg_<n>, pivot at the hip), head "
       "on a neck (Head) with glowing eyes, optional back module", params=[
           Param("size", "float", "Länge (m)", lo=0.5, hi=1.6, size=True),
           Param("module", "choice", "Aufsatz", choices=("none", "sensor", "cargo", "turret")),
           Param("mode", "choice", "Augen-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Steady"),
       ])
def robot_dog(rng, a):
    p = a.p
    s = p.float("size", 0.8, 1.1)
    shell = p.material(["M_RobotBody", "M_Warning", "M_RobotDark", "M_HazardOrange"])
    glow = p.glow(weights=(0.6, 0.3, 0.1))
    body = a.part("Body")
    zb = s * rng.uniform(0.5, 0.6)
    bl, bw, bh = s * 0.75, s * 0.3, s * 0.2
    cube(body, (bw, bl, bh), (0, 0, zb), shell, bevel=0.02)
    cube(body, (bw * 0.8, bl * 0.6, bh * 0.3), (0, 0, zb + bh * 0.6), "M_RobotDark", bevel=0.01)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1)), 1):
        hip = (sx * bw * 0.55, sy * bl * 0.38, zb)
        knee = (sx * bw * 0.62, sy * bl * 0.38 + s * 0.12 * (1 if sy < 0 else -1) * -1, zb * 0.5)
        foot = (sx * bw * 0.6, sy * bl * 0.38, 0.03)
        leg = a.part(f"Leg_{i}", pivot=hip)
        cyl(leg, s * 0.06, s * 0.08, hip, "M_RobotDark", sides=6, rot=ALONG_X)
        strut(leg, hip, knee, s * 0.04, shell, sides=6)
        leg.add(sphere(s * 0.045, 6, 3, "M_RobotDark"), loc=knee)
        strut(leg, knee, foot, s * 0.03, "M_RobotDark", sides=6, radius_end=s * 0.02)
        cyl(leg, s * 0.04, 0.03, (foot[0], foot[1], 0.015), "M_RobotDark", sides=6)
    neck = (0.0, -bl / 2, zb + bh * 0.3)
    head = a.part("Head", pivot=neck)
    strut(head, neck, add_vec(neck, (0, -s * 0.08, s * 0.1)), s * 0.04, "M_RobotDark", sides=6)
    hc = add_vec(neck, (0, -s * 0.15, s * 0.14))
    cube(head, (s * 0.2, s * 0.22, s * 0.14), hc, shell, bevel=0.02)
    eyes = a.part("Glow", parent="Head")
    cube(eyes, (s * 0.14, 0.015, s * 0.03), add_vec(hc, (0, -s * 0.11 - 0.007, s * 0.02)), glow)
    module = p.choice("module", ["none", "sensor", "cargo", "turret"])
    top = zb + bh / 2 + bh * 0.15
    if module == "sensor":
        cyl(body, s * 0.05, s * 0.15, (0, bl * 0.2, top + s * 0.075), "M_Metal", sides=6)
        cyl(body, s * 0.1, s * 0.04, (0, bl * 0.2, top + s * 0.17), "M_Platform", sides=8, rot=(deg(-25), 0, 0))
    elif module == "cargo":
        cube(body, (bw * 0.9, bl * 0.5, s * 0.15), (0, bl * 0.1, top + s * 0.075), "M_HazardOrange", bevel=0.01)
    elif module == "turret":
        cyl(body, s * 0.08, s * 0.06, (0, 0, top + s * 0.03), "M_RobotDark", sides=8)
        cyl(body, s * 0.025, s * 0.3, (0, -s * 0.12, top + s * 0.08), "M_Metal", sides=6, rot=ALONG_Y)
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="Leg_<n> pivot at the hip, Head at the neck - ready for a walk animation")
    a.meta.update({"module": module, "length_m": round(s, 3)})


@model("mech", "Mech", "robots", "Industrial mech: two legs (Leg_1/2, pivot at the hip), torso turning at the "
       "waist (Torso) with cockpit glass, work arms (Arm_L / Arm_R, pivot at the shoulder), lights (Glow)", params=[
           Param("height", "float", "Höhe (m)", lo=2.0, hi=4.5, size=True),
           Param("arms", "choice", "Arme", choices=("claw", "drill", "loader")),
           Param("torso_speed", "float", "Torso-Tempo (°/s, 0 = steht)", lo=0, hi=180, unity=True, default=0),
           Param("mode", "choice", "Licht-Modus", choices=("Steady", "Pulse", "Blink"), unity=True, default="Steady"),
       ])
def mech(rng, a):
    p = a.p
    h = p.float("height", 2.6, 3.6)
    arms = p.choice("arms", ["claw", "drill", "loader"])
    paint = p.material(["M_Warning", "M_HazardOrange", "M_Wall", "M_RobotBody"])
    body = a.part("Body")
    hip_z = h * 0.48
    stance = h * 0.16
    cube(body, (stance * 2.2, h * 0.16, h * 0.08), (0, 0, hip_z), "M_RobotDark", bevel=0.02)  # pelvis
    for i, side in enumerate((-1, 1), 1):
        hip = (side * stance, 0.0, hip_z)
        knee = (side * stance * 1.1, -h * 0.08, hip_z * 0.5)
        ankle = (side * stance * 1.05, 0.0, h * 0.06)
        leg = a.part(f"Leg_{i}", pivot=hip)
        cyl(leg, h * 0.05, h * 0.07, hip, "M_RobotDark", sides=8, rot=ALONG_X)
        strut(leg, hip, knee, h * 0.045, paint, sides=6)
        leg.add(sphere(h * 0.045, 6, 3, "M_RobotDark"), loc=knee)
        strut(leg, knee, ankle, h * 0.04, "M_RobotDark", sides=6)
        cube(leg, (h * 0.12, h * 0.2, h * 0.05), (ankle[0], -h * 0.02, h * 0.025), "M_RobotDark", bevel=0.01)
    waist = (0.0, 0.0, hip_z + h * 0.04)
    torso = a.part("Torso", pivot=waist)
    tw, td, th = h * 0.36, h * 0.28, h * 0.26
    tc = (0.0, 0.0, hip_z + h * 0.06 + th / 2)
    cube(torso, (tw, td, th), tc, paint, bevel=0.03)
    cube(torso, (tw * 0.6, 0.04, th * 0.5), add_vec(tc, (0, -td / 2 - 0.01, th * 0.1)), "M_Glass")  # cockpit
    cube(torso, (tw * 0.3, td * 0.5, th * 0.3), add_vec(tc, (0, td * 0.4, th * 0.2)), "M_RobotDark", bevel=0.01)
    lights = a.part("Glow", parent="Torso")
    lamp = p.glow_from(["M_GlowCyan", "M_GlowOrange"])
    for x in (-1, 1):
        cube(lights, (h * 0.04, 0.02, h * 0.03), add_vec(tc, (x * tw * 0.4, -td / 2 - 0.012, th * 0.38)), lamp)
    for name, side in (("Arm_L", -1), ("Arm_R", 1)):
        shoulder = add_vec(tc, (side * (tw / 2 + h * 0.03), 0, th * 0.25))
        arm = a.part(name, pivot=shoulder, parent="Torso")
        cyl(arm, h * 0.05, h * 0.06, shoulder, "M_RobotDark", sides=8, rot=ALONG_X)
        elbow = add_vec(shoulder, (side * h * 0.04, -h * 0.1, -h * 0.18))
        hand = add_vec(elbow, (0, -h * 0.16, -h * 0.02))
        strut(arm, shoulder, elbow, h * 0.035, paint, sides=6)
        strut(arm, elbow, hand, h * 0.03, "M_RobotDark", sides=6)  # two materials per moving part
        if arms == "claw":
            for k in (-1, 1):
                cube(arm, (h * 0.02, h * 0.1, h * 0.03), add_vec(hand, (k * h * 0.03, -h * 0.04, 0)), "M_RobotDark",
                     rot=(0, 0, k * deg(15)))
        elif arms == "drill":
            cyl(arm, h * 0.04, h * 0.14, add_vec(hand, (0, -h * 0.07, 0)), paint, sides=8, radius_top=0.0,
                rot=(deg(90), 0, 0))
        else:
            cube(arm, (h * 0.14, h * 0.12, h * 0.015), add_vec(hand, (side * -h * 0.03, -h * 0.06, -h * 0.02)),
                 paint)
    speed = p.option("torso_speed")
    if speed:
        a.behaviour("Rotator", {"target": "Torso"}, {"axis": "up", "speed": speed})
    a.behaviour("SignalLight", {"glow": "Glow"}, {"mode": p.option("mode")},
                note="joints: Leg_1/2 at the hips, Torso at the waist, Arm_L/R at the shoulders")
    a.meta.update({"arms": arms, "height_m": round(h, 3)})
