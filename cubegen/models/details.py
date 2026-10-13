"""Variety details: small additions that make the variants of a type tell apart (bolts, a coded plate, a conduit,
warning chevrons, a power box, a cage ...).

They roll from the model's own stream ``asset.sub("variety")`` - never from the builder's ``rng`` - so everything the
seed made so far stays where it was; each variant gets one or two details of its own. Rules: details are small and
static (no collider of their own, no moving part), stay off rotating parts and gameplay points (beam heights, lenses)
and inside the type's ``set_faces``.
"""

from __future__ import annotations

import math

from .common import ALONG_X, cube, cyl, strut
from .lettering import add_text, text_width


def variety(a):
    """The details' own random stream of a model."""
    return a.sub("variety")


def pick(rng, options, most: int = 2):
    """One or ``most`` different details from ``options`` (order kept, so the result reads like the list)."""
    chosen = rng.sample(list(options), min(len(options), rng.randint(1, most)))
    return [o for o in options if o in chosen]


def code(rng, prefix: str) -> str:
    return f"{prefix}-{rng.randint(1, 99):02d}"


def bolts(m, center, radius, z, count, size=0.028, material="M_Metal", phase=0.0):
    """Bolt heads on a ring (on a round or square top face at height ``z``)."""
    for k in range(count):
        ang = phase + 2 * math.pi * k / count
        cube(m, (size, size, size * 0.6), (center[0] + math.cos(ang) * radius, center[1] + math.sin(ang) * radius,
                                           z + size * 0.3), material, rot=(0, 0, ang))


def chevrons(m, center, radius, z, count, material="M_Warning"):
    """Flat warning chevrons around a round top face."""
    for k in range(count):
        ang = 2 * math.pi * (k + 0.5) / count
        for s in (-1, 1):
            cube(m, (0.07, 0.022, 0.006), (center[0] + math.cos(ang) * radius, center[1] + math.sin(ang) * radius,
                                           z + 0.003), material, rot=(0, 0, ang + math.pi / 2 + s * math.radians(35)))


def plate(m, rng, center, width, prefix, height=None, material="M_Platform", letters="M_RobotDark"):
    """A coded plate facing -Y (``center``: its front face), e.g. ``L-07``; returns the code."""
    text = code(rng, prefix)
    height = height or width * 0.32
    cap = height * 0.55
    while text_width(text, cap) > width * 0.86:
        cap *= 0.9
    cube(m, (width, 0.012, height), (center[0], center[1] + 0.006, center[2]), material)
    add_text(m, text, (center[0], center[1], center[2]), cap, 0.006, letters)
    return text


def conduit(m, start, end, radius=0.016, clamps=2, material="M_RobotDark"):
    """A cable conduit between two points with clamp blocks."""
    strut(m, start, end, radius, material, sides=6)
    for k in range(clamps):
        t = (k + 1) / (clamps + 1)
        cube(m, (radius * 4, radius * 3, radius * 2.4), tuple(start[i] + (end[i] - start[i]) * t for i in range(3)),
             "M_Metal")


def power_box(m, rng, at, floor=0.0):
    """A small junction box with a cable down to ``floor``."""
    w, d, h = rng.uniform(0.1, 0.14), rng.uniform(0.07, 0.1), rng.uniform(0.07, 0.1)
    cube(m, (w, d, h), at, "M_RobotDark", bevel=0.008)
    cube(m, (w * 0.5, 0.008, h * 0.3), (at[0], at[1] - d / 2 - 0.004, at[2] + h * 0.15), "M_Warning")
    if at[2] - h / 2 > floor + 0.03:
        strut(m, (at[0], at[1], at[2] - h / 2), (at[0], at[1], floor + 0.01), 0.012, "M_RobotDark", sides=5)


# --------------------------------------------------------------------------
# per type (each picks from its own list)
# --------------------------------------------------------------------------

def round_base(a, m, radius, top, prefix):
    """Turntable bases of the laser parts (round top at ``top``; the turning part stays inside 0.22 m)."""
    rng = variety(a)
    ring = (0.22 + radius) / 2
    picks = pick(rng, ("bolts", "chevrons", "box", "plate"))
    for detail in picks:
        if detail == "bolts":
            bolts(m, (0, 0), ring, top, rng.choice((4, 6, 8)), phase=rng.uniform(0, math.pi))
        elif detail == "chevrons":
            chevrons(m, (0, 0), ring, top, rng.choice((3, 4)))
        elif detail == "box":
            ang = rng.uniform(0, 2 * math.pi)
            power_box(m, rng, (math.cos(ang) * (radius + 0.06), math.sin(ang) * (radius + 0.06), 0.05))
        else:
            plate(m, rng, (0, -radius * 0.92 - 0.006, top / 2), 0.16, prefix, height=min(0.06, top * 0.7))
    a.meta["details"] = picks


def pillar_front(a, m, front_y, z0, z1, width, prefix):
    """A box mount's front face (y = ``front_y``) between ``z0`` and ``z1``."""
    rng = variety(a)
    picks = pick(rng, ("plate", "conduit", "bolts"))
    a.meta["details"] = picks
    for detail in picks:
        if detail == "plate":
            plate(m, rng, (0, front_y, z0 + (z1 - z0) * rng.uniform(0.3, 0.6)), width * 0.6, prefix)
        elif detail == "conduit":
            x = rng.choice((-1, 1)) * width * 0.3
            conduit(m, (x, front_y - 0.02, z0 + 0.05), (x, front_y - 0.02, z1 - 0.1))
        else:
            for x in (-width * 0.38, width * 0.38):
                for z in (z0 + 0.08, z1 - 0.08):
                    cube(m, (0.025, 0.012, 0.025), (x, front_y - 0.006, z), "M_Metal")


def wall_mount(a, m, z, back_y, prefix):
    """Wall-mounted devices (camera): a conduit down the wall, a coded plate or a junction box below the mount."""
    rng = variety(a)
    picks = pick(rng, ("conduit", "plate", "box"))
    a.meta["details"] = picks
    for detail in picks:
        if detail == "conduit":
            x = rng.choice((-0.06, 0.0, 0.06))
            conduit(m, (x, back_y - 0.02, z - 0.13), (x, back_y - 0.02, z - rng.uniform(0.45, 0.8)), clamps=1)
        elif detail == "plate":
            plate(m, rng, (rng.uniform(-0.12, 0.12), back_y - 0.012, z - rng.uniform(0.22, 0.32)), 0.16, prefix)
        else:
            power_box(m, rng, (rng.choice((-0.16, 0.16)), back_y - 0.05, z - 0.05), floor=z - 0.05)


def pole_tower(a, m, r, z0, z_top, pole_r, mount):
    """Signal towers (warning beacon): a lamp cage, a conduit down the pole or a coded plate at the foot."""
    rng = variety(a)
    picks = pick(rng, ("cage", "conduit", "plate"))
    a.meta["details"] = picks
    for detail in picks:
        if detail == "cage":
            bars = rng.choice((4, 6))
            cr = r * 1.35
            for k in range(bars):
                ang = 2 * math.pi * k / bars + math.pi / bars
                cube(m, (0.012, 0.012, z_top - z0), (math.cos(ang) * cr, math.sin(ang) * cr, (z0 + z_top) / 2),
                     "M_RobotDark")
            cyl(m, cr + 0.008, 0.015, (0, 0, z_top + 0.0075), "M_RobotDark", sides=bars * 2)
        elif detail == "conduit" and mount == "pole":
            conduit(m, (pole_r + 0.02, 0, 0.08), (pole_r + 0.02, 0, z0 - 0.02), radius=0.012, clamps=3)
        else:
            y = -0.22 if mount == "pole" else -0.255
            plate(m, rng, (0, y - 0.006, 0.03 if mount == "pole" else 0.11), 0.14, "W", height=0.045)


def passage(a, m, t, w, oh, h, post, length, prefix):
    """Archways: a coded sign over the passage, lamps on the posts, a conduit up a post or stripes at the feet - all
    within the lintel's depth (t/2 + 0.04), so front and back stay flush."""
    rng = variety(a)
    front = -t / 2
    picks = pick(rng, ("sign", "lamps", "conduit", "feet"))
    a.meta["details"] = picks
    for detail in picks:
        if detail == "sign" and h - oh > 0.32:
            plate(m, rng, (0, front - 0.024, oh + (h - 0.12 - oh) / 2), min(0.9, w * 0.5), prefix,
                  height=min(0.22, (h - 0.12 - oh) * 0.7))
        elif detail == "lamps":
            for s in (-1, 1):
                x = s * (w / 2 + min(post, 0.5) / 2)
                cube(m, (0.14, 0.03, 0.1), (x, front - 0.015, min(oh, h - 0.4) - 0.1), "M_RobotDark", bevel=0.008)
                cube(m, (0.1, 0.008, 0.03), (x, front - 0.034, min(oh, h - 0.4) - 0.12), "M_Warning")
        elif detail == "conduit":
            x = rng.choice((-1, 1)) * (length / 2 - min(post, 0.6) / 2)
            conduit(m, (x, front - 0.014, 0.3), (x, front - 0.014, h - 0.2), radius=0.01, clamps=3)
        elif detail == "feet":
            for s in (-1, 1):
                x = s * (w / 2 + 0.06)
                for k in range(3):
                    cube(m, (0.06, 0.012, 0.05), (x, front - 0.006, 0.3 + k * 0.1), "M_Warning",
                         rot=(0, math.radians(30), 0))


def slab_underside(a, m, size, h, lights_part, glow):
    """Ceiling slabs: a cable tray, a sprinkler line or hanging lamps under the slab - inside the slab's footprint."""
    rng = variety(a)
    y = rng.choice((-1, 1)) * (size / 2 - 0.35)
    span = size - 0.5
    picks = pick(rng, ("tray", "sprinkler", "lamps"))
    a.meta["details"] = picks
    for detail in picks:
        if detail == "tray":
            z = h - rng.uniform(0.32, 0.42)
            cube(m, (span, 0.22, 0.04), (0, y, z), "M_Metal")
            for s in (-1, 1):
                cube(m, (span, 0.015, 0.07), (0, y + s * 0.11, z + 0.035), "M_Metal")
            for k in range(max(2, int(span) + 1)):
                x = -span / 2 + 0.1 + (span - 0.2) * k / max(1, int(span))
                cube(m, (0.02, 0.02, h - z), (x, y, (h + z) / 2), "M_RobotDark")
        elif detail == "sprinkler":
            z = h - 0.28
            cyl(m, 0.025, span, (0, -y, z), "M_HazardOrange", sides=6, rot=ALONG_X)
            for k in range(max(2, int(span))):
                x = -span / 2 + span * (k + 0.5) / max(2, int(span))
                cyl(m, 0.02, 0.05, (x, -y, z - 0.045), "M_Metal", sides=6, radius_top=0.035)
                cube(m, (0.015, 0.015, 0.28), (x, -y, h - 0.14), "M_RobotDark")
        else:
            for k in range(rng.choice((1, 2)) if size >= 2 else 1):
                x = 0.0 if size < 2 else (k - 0.5) * size * 0.4
                drop = rng.uniform(0.3, 0.5)
                strut(m, (x, y * 0.5, h), (x, y * 0.5, h - drop), 0.008, "M_RobotDark", sides=4)
                cyl(m, 0.12, 0.08, (x, y * 0.5, h - drop - 0.04), "M_RobotDark", sides=8, radius_top=0.05)
                cyl(lights_part(), 0.1, 0.012, (x, y * 0.5, h - drop - 0.086), glow, sides=8)


def tool_grip(a, m, kind, length):
    """Hand tools: grip bands or a coded tag (the item pickup takes every part)."""
    rng = variety(a)
    material = rng.choice(("M_Warning", "M_HazardOrange", "M_RobotDark", "M_Metal"))
    bands = rng.randint(1, 3)
    if kind == "screwdriver":
        r, hl = length * 0.07, length * 0.42
        for k in range(bands):
            x = -length / 2 + hl * (0.2 + 0.18 * k)
            cyl(m, r * 1.1, 0.012, (x, 0, 0), material, sides=6, rot=ALONG_X)
    elif kind == "crowbar":
        r = length * 0.03
        start, bend = (-length / 2, -length * 0.05), (length / 2 - length * 0.12, length * 0.02)  # the shaft
        for k in range(bands):
            t = 0.12 + 0.1 * k
            x, z = start[0] + (bend[0] - start[0]) * t, start[1] + (bend[1] - start[1]) * t
            cyl(m, r * 1.35, 0.018, (x, 0, z), material, sides=6, rot=ALONG_X)
    elif kind == "wrench":
        w = length * 0.12
        for k in range(bands):
            cube(m, (0.012, 0.034, w * 1.15), (length * (-0.06 + 0.06 * k), 0, 0), material)
    else:  # pliers: a spring between the handles
        strut(m, (-length * 0.1, 0, -length * 0.03), (-length * 0.1, 0, length * 0.03), 0.004, "M_Metal", sides=4)
        for k in range(bands):
            cube(m, (0.014, 0.03, length * 0.075), (-length * (0.28 + 0.06 * k), 0, length * 0.05), material,
                 rot=(0, math.radians(8), 0))
    a.meta["grip"] = bands
