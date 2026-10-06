"""Gameplay building blocks: portals, phase / breakable platforms, retractable bridges, turntables,
spike traps, fluid basins and cargo containers.

Every moving or switchable piece is its own part with its pivot where it moves
(``Deck``, ``Spikes``, ``Door_Left`` ...), static frames are separate, and the
walkable / blocking shapes are explicit ``colliders`` - openings and interiors
stay free. Existing game scripts are only wired where they really do the job:

* ``turntable``: ``Rotatable`` turns the ``Deck`` in steps (direction puzzles)
* ``retractable_bridge``, ``spike_trap``: ``Door`` moves the deck / spikes (like ``lift``)
* ``cargo_container``: one ``Rotatable`` per door leaf
* ``portal_frame``, ``phase_platform``: ``SignalLight`` on the status glow

Portal travel, phasing, breaking, spike damage and fluids need game-side
mechanics that don't exist yet (see docs/UNITY_INTEGRATION.md); the models
are prepared for them, they don't fake them.
"""

from __future__ import annotations

import math

from ..params import Param
from .common import ALONG_X, ALONG_Y, cube, cyl
from .environment import DOOR_STYLES
from .kit import rail_run
from .registry import model

SIGNAL_MODES = ("Steady", "Blink", "Pulse")
FLUIDS = {"water": "M_Glass", "mud": "M_Ground", "toxic": "M_GlowOrange"}


def _frame_of(style: str):
    post, top = DOOR_STYLES[style][2], DOOR_STYLES[style][9]
    return post, (top if top is not None else post)


# --------------------------------------------------------------------------
# portal_frame
# --------------------------------------------------------------------------

@model("portal_frame", "PortalFrame", "tech", "Portal frame for a wall or the floor: separate frame, portal surface "
       "(Surface) and status glow; the passage stays free", params=[
           Param("mount", "choice", "Einbau", choices=("wall", "floor")),
           Param("width", "float", "Portal Breite (m)", lo=0.6, hi=6.0, size=True),
           Param("height", "float", "Portal Höhe (m)", lo=0.6, hi=6.0, size=True,
                 description="Bodenportal: Tiefe"),
           Param("frame_style", "choice", "Rahmenprofil", choices=tuple(sorted(DOOR_STYLES)),
                 description="Rahmenmaß wie die Tür dieses Stils: passt in dieselbe Wandöffnung"),
           Param("surface", "choice", "Portalfläche", choices=("panel", "glow")),
           Param("mode", "choice", "Glow-Modus", choices=SIGNAL_MODES, unity=True, default="Pulse"),
       ])
def portal_frame(rng, a):
    p = a.p
    mount = p.choice("mount", ["wall", "wall", "floor"])
    w = p.float("width", 1.4, 2.4)
    h = p.float("height", 2.2, 2.8) if mount == "wall" else p.float("height", 1.4, 2.4)
    style = p.choice("frame_style", sorted(DOOR_STYLES))
    post, top = _frame_of(style)
    depth = rng.uniform(0.3, 0.5)
    mat = p.material(["M_RobotDark", "M_Metal", "M_Wall"])
    glow = p.glow()
    surface_mat = "M_PortalPanel" if p.choice("surface", ["panel", "panel", "glow"]) == "panel" else glow
    frame, lights = a.part("Frame"), a.part("Glow")
    a.meta.update({"mount": mount, "opening_m": [round(w, 4), round(h, 4)], "frame_style": style,
                   "outer_m": [round(w + 2 * post, 4),
                               round(h + top, 4) if mount == "wall" else round(h + 2 * post, 4)]})
    if mount == "wall":
        for s in (-1, 1):  # posts, a plinth each, inner glow strip
            x = s * (w + post) / 2
            cube(frame, (post, depth, h + top), (x, 0, (h + top) / 2), mat, bevel=0.03)
            cube(frame, (post + 0.06, depth + 0.06, 0.2), (x, 0, 0.1), "M_RobotDark", bevel=0.01)
            a.collider((post, depth, h + top), (x, 0, (h + top) / 2))
            cube(lights, (0.03, depth * 0.5, h * 0.8), (s * (w / 2 - 0.016), 0, h * 0.45), glow)
        cube(frame, (w, depth, top), (0, 0, h + top / 2), mat, bevel=0.03)
        a.collider((w, depth, top), (0, 0, h + top / 2))
        cube(lights, (w * 0.6, 0.02, 0.08), (0, -(depth / 2 + 0.011), h + top / 2), glow)
        surf = a.part("Surface", pivot=(0, 0, h / 2))
        cube(surf, (w - 0.06, 0.02, h - 0.03), (0, 0, h / 2 + 0.015), surface_mat)
    else:  # lying on the floor: a ring around a horizontal portal surface
        d = h
        ring_h = 0.15
        for s in (-1, 1):
            cube(frame, (post, d + 2 * post, ring_h), (s * (w + post) / 2, 0, ring_h / 2), mat, bevel=0.02)
            a.collider((post, d + 2 * post, ring_h), (s * (w + post) / 2, 0, ring_h / 2))
            cube(frame, (w, post, ring_h), (0, s * (d + post) / 2, ring_h / 2), mat, bevel=0.02)
            a.collider((w, post, ring_h), (0, s * (d + post) / 2, ring_h / 2))
            cube(lights, (w * 0.7, 0.03, 0.03), (0, s * (d / 2 + 0.03), ring_h + 0.015), glow)
        surf = a.part("Surface", pivot=(0, 0, 0.05))
        cube(surf, (w - 0.02, d - 0.02, 0.02), (0, 0, 0.05), surface_mat)
    a.behaviour("SignalLight", {"glow": ["Glow"]}, {"mode": p.option("mode")},
                note="status glow only; the portal surface (Surface) has no collider and no travel logic yet")


# --------------------------------------------------------------------------
# phase_platform
# --------------------------------------------------------------------------

@model("phase_platform", "PhasePlatform", "environment", "Phase platform (top at z = 0): permanent anchors / "
       "pedestal (Base), separate Deck and glow for later phase control", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 3.0, 4.0)),
           Param("anchors", "choice", "Halterung", choices=("pylons", "pedestal", "brackets")),
           Param("pattern", "choice", "Deck-Muster", choices=("grid", "rings", "plain")),
           Param("mode", "choice", "Glow-Modus", choices=SIGNAL_MODES, unity=True, default="Pulse"),
       ])
def phase_platform(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 2.0, 2.0, 3.0])
    anchors = p.choice("anchors", ["pylons", "pedestal", "brackets"])
    deck_mat = p.material(["M_Platform", "M_PortalPanel", "M_Metal"])
    glow = p.glow()
    pattern = p.choice("pattern", ["grid", "rings", "plain"])
    deck = a.part("Deck", pivot=(0, 0, -0.1))
    base, lights = a.part("Base"), a.part("Glow")
    a.meta.update({"size_m": size, "anchors": anchors})
    cube(deck, (size, size, 0.2), (0, 0, -0.1), deck_mat, bevel=0.03)
    a.collider((size, size, 0.2), (0, 0, -0.1), part="Deck")
    if pattern == "grid":
        n = max(2, int(size))
        for i in range(1, n):
            f = -size / 2 + size * i / n
            cube(deck, (0.03, size - 0.2, 0.01), (f, 0, 0.005), "M_RobotDark")
            cube(deck, (size - 0.2, 0.03, 0.012), (0, f, 0.008), "M_RobotDark")
    elif pattern == "rings":
        cyl(deck, size * 0.35, 0.01, (0, 0, 0.005), "M_RobotDark", sides=12)
        cyl(deck, size * 0.2, 0.012, (0, 0, 0.009), deck_mat, sides=12)
    gap = 0.06  # the deck floats above its anchors: nothing shares a face with it
    if anchors == "pylons":
        for x in (-1, 1):
            for y in (-1, 1):
                c = (x * (size / 2 - 0.15), y * (size / 2 - 0.15))
                cube(base, (0.16, 0.16, 1.2), (c[0], c[1], -0.2 - gap - 0.6), "M_RobotDark", bevel=0.02)
                a.collider((0.16, 0.16, 1.2), (c[0], c[1], -0.2 - gap - 0.6))
                cube(lights, (0.1, 0.1, 0.03), (c[0], c[1], -0.2 - gap + 0.015), glow)
    elif anchors == "pedestal":
        cyl(base, size * 0.18, 1.4, (0, 0, -0.2 - gap - 0.7), "M_RobotDark", sides=8)
        cyl(base, size * 0.3, 0.1, (0, 0, -0.2 - gap - 1.36), "M_Metal", sides=8)
        a.collider((size * 0.36, size * 0.36, 1.4), (0, 0, -0.2 - gap - 0.7))
        cyl(lights, size * 0.12, 0.03, (0, 0, -0.2 - gap + 0.015), glow, sides=8)
    else:  # wall brackets at the back (+Y): the platform sticks out of a wall
        for x in (-size / 2 + 0.2, size / 2 - 0.2):
            cube(base, (0.12, 0.5, 0.5), (x, size / 2 + 0.25, -0.2 - gap - 0.25), "M_RobotDark")
            a.collider((0.12, 0.5, 0.5), (x, size / 2 + 0.25, -0.2 - gap - 0.25))
            cube(lights, (0.08, 0.03, 0.08), (x, size / 2 + 0.005 - 0.02, -0.2 - gap - 0.1), glow)
    a.behaviour("SignalLight", {"glow": ["Glow"]}, {"mode": p.option("mode")},
                note="phase indicator; switching the Deck (renderer + collider) on and off needs a phase script")


# --------------------------------------------------------------------------
# retractable_bridge
# --------------------------------------------------------------------------

@model("retractable_bridge", "RetractableBridge", "environment", "Retractable bridge (top at z = 0): fixed landing "
       "with a pocket (Housing), Deck that slides out to the far side (Door)", pivot="top", params=[
           Param("length", "choice", "Spannweite (m)", choices=(2.0, 4.0)),
           Param("width", "float", "Breite (m)", lo=0.8, hi=3.0),
           Param("rails", "bool", "Geländer am Podest"),
           Param("speed", "float", "Ausfahr-Tempo (m/s)", lo=0.1, hi=5.0, unity=True, default=0.8),
           Param("starts_open", "bool", "Startet ausgefahren", unity=True, default=False),
       ])
def retractable_bridge(rng, a):
    p = a.p
    span = p.choice("length", [2.0, 4.0, 4.0])
    w = p.value("width", rng.choice([1.0, 1.0, 2.0]))
    mat = p.material(["M_Metal", "M_RobotDark", "M_Platform"])
    glow = p.glow()
    lift = 0.3  # the deck slides out diagonally from under the landing up to z = 0
    housing = a.part("Housing")
    a.meta.update({"length_m": span, "width_m": w})
    # landing (walkable, top at 0) over the pocket the deck rests in
    cube(housing, (span, w, 0.2), (-span / 2, 0, -0.1), mat, bevel=0.02)
    a.collider((span, w, 0.2), (-span / 2, 0, -0.1))
    for s in (-1, 1):
        cube(housing, (span, 0.06, 0.32), (-span / 2, s * (w / 2 + 0.04), -0.36), "M_RobotDark")
        a.collider((span, 0.06, 0.32), (-span / 2, s * (w / 2 + 0.04), -0.36))
    cube(housing, (span, w + 0.14, 0.06), (-span / 2, 0, -0.55), "M_RobotDark")
    a.collider((span, w + 0.14, 0.06), (-span / 2, 0, -0.55))
    for s in (-1, 1):  # glow guide strips along the landing edges
        cube(housing, (span * 0.9, 0.02, 0.05), (-span / 2, s * (w / 2 + 0.011), -0.06), glow)
    deck = a.part("Deck", pivot=(-span / 2, 0, -lift - 0.06))
    cube(deck, (span - 0.02, w - 0.02, 0.12), (-span / 2, 0, -lift - 0.06), mat, bevel=0.02)
    a.collider((span - 0.02, w - 0.02, 0.12), (-span / 2, 0, -lift - 0.06), part="Deck")
    for i in range(int(span / 0.5)):  # anti-slip bars on the deck
        cube(deck, (0.04, w - 0.2, 0.02), (-span + 0.25 + i * 0.5, 0, -lift + 0.01), "M_RobotDark")
    for name, s in (("StatusLight_Front", -1), ("StatusLight_Back", 1)):  # lamps on posts at the bridge end
        post = a.part(name)
        cube(post, (0.12, 0.12, 0.12), (-0.08, s * (w / 2 + 0.16), 0.9), "M_GlowRed")
    for s in (-1, 1):
        cube(housing, (0.08, 0.08, 0.84), (-0.08, s * (w / 2 + 0.16), 0.42), "M_RobotDark")
        a.collider((0.08, 0.08, 0.84), (-0.08, s * (w / 2 + 0.16), 0.42))
    if p.bool("rails", 0.5):
        r = a.part("Rail")
        for s in (-1, 1):
            size, center = rail_run(r, (-span + 0.05, s * (w / 2 - 0.04)), (-0.25, s * (w / 2 - 0.04)))
            a.collider(size, center, part="Rail")
    a.behaviour("Door", {"panels": ["Deck"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "colliders": ["Housing"]},
                {"openOffset": [-span, lift, 0.0], "speed": p.option("speed"), "startsOpen": p.option("starts_open")},
                note="'open' = Deck slid out to the far side (Unity -X = Blender +X) and up to the walkway")


# --------------------------------------------------------------------------
# turntable
# --------------------------------------------------------------------------

@model("turntable", "Turntable", "puzzle", "Turntable (top at z = 0): fixed ring and hub (Base), Deck turning around "
       "its centre in steps (Rotatable) - for players, crates and direction puzzles", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 3.0, 4.0)),
           Param("shape", "choice", "Form", choices=("round", "square")),
           Param("arrow", "bool", "Richtungspfeil"),
           Param("step", "choice", "Schritt (°)", choices=(45, 90), unity=True, default=90),
           Param("speed", "float", "Drehtempo (°/s)", lo=10, hi=720, unity=True, default=90),
           Param("target", "int", "Zielstellung", lo=0, hi=7, unity=True, default=1),
           Param("interactive", "bool", "Spieler kann drehen", unity=True, default=True),
       ])
def turntable(rng, a):
    p = a.p
    size = p.choice("size", [1.0, 2.0, 2.0, 3.0])
    shape = p.choice("shape", ["round", "square"])
    mat = p.material(["M_Platform", "M_Metal", "M_RobotDark"])
    glow = p.glow()
    base, lights = a.part("Base"), a.part("Glow")
    deck = a.part("Deck", pivot=(0, 0, 0))
    ring = 0.2
    outer = size + 2 * ring
    a.meta.update({"size_m": size, "shape": shape, "outer_m": outer})
    for s in (-1, 1):  # surrounding frame, flush with the deck
        cube(base, (outer, ring - 0.02, 0.2), (0, s * (size / 2 + ring / 2 + 0.01), -0.1), "M_RobotDark")
        a.collider((outer, ring - 0.02, 0.2), (0, s * (size / 2 + ring / 2 + 0.01), -0.1))
        cube(base, (ring - 0.02, size + 0.02, 0.2), (s * (size / 2 + ring / 2 + 0.01), 0, -0.1), "M_RobotDark")
        a.collider((ring - 0.02, size + 0.02, 0.2), (s * (size / 2 + ring / 2 + 0.01), 0, -0.1))
    cyl(base, size * 0.15, 0.3, (0, 0, -0.38), "M_Metal", sides=8)  # hub below the deck
    cube(base, (size, size, 0.05), (0, 0, -0.555), "M_RobotDark")
    a.collider((size, size, 0.05), (0, 0, -0.555))
    if shape == "round":
        cyl(deck, size / 2, 0.2, (0, 0, -0.1), mat, sides=16)
        cyl(deck, size / 2 - 0.08, 0.01, (0, 0, 0.005), "M_RobotDark", sides=16)
        a.mesh_collider("Deck", convex=True)
    else:
        cube(deck, (size, size, 0.2), (0, 0, -0.1), mat, bevel=0.02)
        a.collider((size, size, 0.2), (0, 0, -0.1), part="Deck")
    if p.bool("arrow", 0.8):  # direction marker on the deck, pointing to the front (-Y) at rest
        cube(deck, (size * 0.1, size * 0.4, 0.012), (0, size * 0.02, 0.016), "M_Warning")
        cube(deck, (size * 0.2, size * 0.2, 0.012), (0, -size * 0.2, 0.017), "M_Warning", rot=(0, 0, math.pi / 4))
    for s in (-1, 1):  # direction lights in the frame
        cube(lights, (0.08, 0.04, 0.03), (0, s * (size / 2 + ring / 2 + 0.01), 0.015), glow)
        cube(lights, (0.04, 0.08, 0.03), (s * (size / 2 + ring / 2 + 0.01), 0, 0.015), glow)
    a.behaviour("Rotatable", {"target": "Deck", "glow": "Glow", "body": "Base"},
                {"axis": "up", "step": p.option("step"), "speed": p.option("speed"), "target": p.option("target"),
                 "interactive": p.option("interactive")},
                note="Deck turns around its centre (Unity up); a carried player / crate needs the platform-follow "
                     "logic the game has for MovingPlatform")


# --------------------------------------------------------------------------
# breakable_platform
# --------------------------------------------------------------------------

@model("breakable_platform", "BreakablePlatform", "environment", "Unstable platform (top at z = 0): fixed frame, "
       "deck tiles (Tile_<n>) with cracks and weak spots", pivot="top", params=[
           Param("size", "choice", "Größe (m)", choices=(1.0, 2.0, 3.0, 4.0)),
           Param("tiles", "choice", "Platten je Seite", choices=(2, 3)),
           Param("cracks", "int", "Risse", lo=1, hi=10),
           Param("weak_spots", "bool", "Markierte Schwachstellen"),
           Param("supports", "bool", "Stützen"),
       ])
def breakable_platform(rng, a):
    p = a.p
    size = p.choice("size", [2.0, 2.0, 3.0])
    n = p.choice("tiles", [2, 3])
    cracks = p.int("cracks", 2, 6)
    mat = p.material(["M_Platform", "M_Wall", "M_Metal"])
    frame = a.part("Frame")
    rim = 0.1
    inner = size - 2 * rim
    a.meta.update({"size_m": size, "tiles": n * n})
    for s in (-1, 1):  # rim beams
        cube(frame, (size, rim, 0.25), (0, s * (size / 2 - rim / 2), -0.125), "M_RobotDark")
        a.collider((size, rim, 0.25), (0, s * (size / 2 - rim / 2), -0.125))
        cube(frame, (rim, inner, 0.25), (s * (size / 2 - rim / 2), 0, -0.125), "M_RobotDark")
        a.collider((rim, inner, 0.25), (s * (size / 2 - rim / 2), 0, -0.125))
    t = inner / n
    for i in range(1, n):  # beams under the tile joints
        f = -inner / 2 + t * i
        cube(frame, (0.08, inner, 0.12), (f, 0, -0.19), "M_RobotDark")
        cube(frame, (inner, 0.08, 0.12), (0, f, -0.19), "M_RobotDark")
    tiles = []
    for ix in range(n):
        for iy in range(n):
            cx, cy = -inner / 2 + t * (ix + 0.5), -inner / 2 + t * (iy + 0.5)
            name = f"Tile_{ix * n + iy + 1}"
            tile = a.part(name, pivot=(cx, cy, -0.06))
            cube(tile, (t - 0.02, t - 0.02, 0.12), (cx, cy, -0.06), mat)
            a.collider((t - 0.02, t - 0.02, 0.12), (cx, cy, -0.06), part=name)
            tiles.append((tile, cx, cy))
    crack_list = []
    for _ in range(cracks):  # dark cracks across random tiles
        tile, cx, cy = tiles[rng.randrange(len(tiles))]
        ln = t * rng.uniform(0.3, 0.7)
        ang = rng.uniform(0, math.pi)
        dx = (t - ln) / 2 * 0.6
        crack_list.append((tile, (ln, 0.025, 0.008), (cx + rng.uniform(-dx, dx), cy + rng.uniform(-dx, dx), 0.004),
                           ang))
    weak = tiles[:: max(1, len(tiles) // 3)] if p.bool("weak_spots", 0.6, warning=True) else []
    weak_parts = {id(tile) for tile, _, _ in weak} if p.style.generation >= 2 else set()
    for tile, size_, center_, ang in crack_list:  # a weak tile's cracks in its warning colour: 2 materials per tile
        cube(tile, size_, center_, "M_Warning" if id(tile) in weak_parts else "M_RobotDark", rot=(0, 0, ang))
    for tile, cx, cy in weak:
        cube(tile, (0.12, 0.12, 0.01), (cx, cy, 0.009), "M_Warning", rot=(0, 0, math.pi / 4))
    if p.bool("supports", 0.5):
        for x in (-1, 1):
            for y in (-1, 1):
                c = (x * (size / 2 - 0.1), y * (size / 2 - 0.1))
                cube(frame, (0.1, 0.1, 1.0), (c[0], c[1], -0.25 - 0.5), "M_RobotDark")
                a.collider((0.1, 0.1, 1.0), (c[0], c[1], -0.25 - 0.5))


# --------------------------------------------------------------------------
# spike_trap
# --------------------------------------------------------------------------

@model("spike_trap", "SpikeTrap", "puzzle", "Spike trap (top at z = 0): fixed plate and housing (Base), retractable "
       "spikes (Spikes, moved by Door), warning lights", pivot="top", params=[
           Param("size", "float", "Größe (m)", lo=0.6, hi=4.0, size=True),
           Param("spike_height", "float", "Stachelhöhe (m)", lo=0.2, hi=1.2),
           Param("spacing", "float", "Abstand (m)", lo=0.15, hi=0.6),
           Param("speed", "float", "Ausfahr-Tempo (m/s)", lo=0.1, hi=20.0, unity=True, default=4.0),
           Param("starts_open", "bool", "Startet ausgefahren", unity=True, default=False),
       ])
def spike_trap(rng, a):
    p = a.p
    size = p.float("size", 1.0, 2.0)
    sh = p.float("spike_height", 0.35, 0.7)
    spacing = p.float("spacing", 0.22, 0.35)
    mat = p.material(["M_Metal", "M_RobotDark"])
    base = a.part("Base")
    a.meta.update({"size_m": round(size, 4), "spike_height_m": round(sh, 4)})
    cube(base, (size, size, 0.1), (0, 0, -0.05), mat, bevel=0.01)
    a.collider((size, size, 0.1), (0, 0, -0.05))
    depth = sh + 0.15
    for s in (-1, 1):  # housing below the floor
        cube(base, (size, 0.06, depth), (0, s * (size / 2 - 0.03), -0.1 - depth / 2), "M_RobotDark")
        cube(base, (0.06, size - 0.12, depth), (s * (size / 2 - 0.03), 0, -0.1 - depth / 2), "M_RobotDark")
    n = max(2, int((size - 0.2) / spacing))
    pitch = (size - 0.2) / n
    spikes = a.part("Spikes", pivot=(0, 0, -sh - 0.02))
    holes = []
    for i in range(n):
        for j in range(n):
            x, y = -size / 2 + 0.1 + pitch * (i + 0.5), -size / 2 + 0.1 + pitch * (j + 0.5)
            holes.append((x, y))
            cyl(spikes, pitch * 0.22, sh, (x, y, -sh / 2 - 0.02), "M_Metal", sides=6, radius_top=0.0)
            cube(base, (pitch * 0.5, pitch * 0.5, 0.006), (x, y, 0.003), "M_RobotDark")  # hole mark
    cube(spikes, (size - 0.14, size - 0.14, 0.05), (0, 0, -sh - 0.045), "M_RobotDark")  # carrier plate
    a.collider((size - 0.14, size - 0.14, sh + 0.05), (0, 0, -sh / 2 - 0.045), part="Spikes")
    for name, s in (("StatusLight_Front", -1), ("StatusLight_Back", 1)):
        light = a.part(name)
        cube(light, (size * 0.6, 0.04, 0.03), (0, s * (size / 2 - 0.04), 0.015), "M_GlowRed")
    a.meta["spikes"] = len(holes)
    a.behaviour("Door", {"panels": ["Spikes"], "statusLights": ["StatusLight_Front", "StatusLight_Back"],
                         "colliders": ["Base"]},
                {"openOffset": [0.0, round(sh + 0.02, 4), 0.0], "speed": p.option("speed"),
                 "startsOpen": p.option("starts_open")},
                note="'open' = spikes out; damage needs a hazard trigger on Spikes (no such script yet)")


# --------------------------------------------------------------------------
# fluid_basin
# --------------------------------------------------------------------------

@model("fluid_basin", "FluidBasin", "industrial", "Open water / mud basin: rim, inlet, drain, a separate fluid "
       "surface (Fluid); walls and floor are separate colliders, the inside stays open", params=[
           Param("width", "float", "Breite (m)", lo=1.0, hi=8.0, size=True),
           Param("depth", "float", "Tiefe (m)", lo=1.0, hi=8.0, size=True),
           Param("rim_height", "float", "Randhöhe (m)", lo=0.3, hi=1.5),
           Param("fill", "float", "Füllstand (0-1)", lo=0.1, hi=0.95),
           Param("fluid", "choice", "Flüssigkeit", choices=tuple(FLUIDS)),
           Param("inlet", "bool", "Zulauf"),
           Param("outlet", "bool", "Ablauf"),
           Param("pipe_radius", "choice", "Rohr-Radius (m)", choices=(0.09, 0.18, 0.35), default=0.09),
           Param("outlet_height", "float", "Ablauf-Achshöhe (m)", lo=0.1, hi=2.5, quiet=True,
                 description="Ohne Angabe knapp über dem Beckenboden; der Rand wird bei Bedarf höher"),
       ])
def fluid_basin(rng, a):
    p = a.p
    w = p.float("width", 2.0, 4.0)
    d = p.float("depth", 1.6, 3.0)
    rim = p.float("rim_height", 0.5, 0.9)
    fill = p.float("fill", 0.55, 0.85)
    kind = p.choice("fluid", ["water", "water", "mud", "toxic"])
    mat = p.material(["M_Wall", "M_Metal", "M_RobotDark"])
    r = p.option("pipe_radius")
    t, floor = 0.15, 0.12
    outlet_z = p.option("outlet_height")
    zo = max(floor + r + 0.02, outlet_z if outlet_z is not None else 0.0)
    rim = max(rim, zo + r * 1.25 + 0.1)  # the outlet (with its flange) sits in the wall below the rim
    basin = a.part("Basin")
    a.meta.update({"inner_m": [round(w - 2 * t, 4), round(d - 2 * t, 4)], "fluid": kind})
    cube(basin, (w - 2 * t, d - 2 * t, floor), (0, 0, floor / 2), "M_RobotDark")  # between the walls
    a.collider((w - 2 * t, d - 2 * t, floor), (0, 0, floor / 2))
    walls = [((w, t, rim), (0, -(d - t) / 2)), ((w, t, rim), (0, (d - t) / 2)),
             ((t, d - 2 * t, rim), (-(w - t) / 2, 0)), ((t, d - 2 * t, rim), ((w - t) / 2, 0))]
    for size, (x, y) in walls:
        cube(basin, size, (x, y, rim / 2), mat, bevel=0.02)
        a.collider(size, (x, y, rim / 2))
    for s in (-1, 1):  # coping on the rim
        cube(basin, (w + 0.04, t + 0.04, 0.05), (0, s * (d - t) / 2, rim + 0.025), "M_RobotDark")
    level = floor + (rim - floor) * fill
    fluid = a.part("Fluid", pivot=(0, 0, level))
    cube(fluid, (w - 2 * t - 0.01, d - 2 * t - 0.01, 0.03), (0, 0, level - 0.015), FLUIDS[kind])
    connectors = {}
    if p.bool("inlet", 0.7):  # pipe over the back rim pouring in
        zi = rim + r + 0.1
        cyl(basin, r, 0.6, (0, d / 2 + 0.1, zi), "M_Metal", sides=8, rot=ALONG_Y)
        cyl(basin, r * 1.25, 0.08, (0, d / 2 + 0.35, zi), "M_RobotDark", sides=8, rot=ALONG_Y)
        cube(basin, (r * 2, 0.12, zi - rim), (0, d / 2 - t / 2, rim + (zi - rim) / 2), "M_RobotDark")
        connectors["inlet"] = [0.0, round(d / 2 + 0.4, 4), round(zi, 4)]
    if p.bool("outlet", 0.7):  # drain grate on the floor, pipe out through the left wall
        cube(basin, (0.3, 0.3, 0.01), (-(w - 2 * t) / 2 + 0.3, 0, floor + 0.005), "M_Metal")
        cyl(basin, r, 0.4, (-w / 2 - 0.15, 0, zo), "M_Metal", sides=8, rot=ALONG_X)
        cyl(basin, r * 1.25, 0.08, (-w / 2 - 0.30, 0, zo), "M_RobotDark", sides=8, rot=ALONG_X)
        connectors["outlet"] = [round(-w / 2 - 0.35, 4), 0.0, round(zo, 4)]
    a.meta["pipe_ends"] = connectors


# --------------------------------------------------------------------------
# cargo_container
# --------------------------------------------------------------------------

@model("cargo_container", "CargoContainer", "environment", "Walk-in cargo container: shell with a free interior, "
       "two door leaves (Door_Left / Door_Right, Rotatable) at the front", params=[
           Param("length", "choice", "Länge (m)", choices=(4.0, 6.0)),
           Param("width", "float", "Breite (m)", lo=2.0, hi=3.2),
           Param("height", "float", "Höhe (m)", lo=2.4, hi=3.4),
           Param("ribs", "bool", "Sicken"),
           Param("speed", "float", "Tür-Tempo (°/s)", lo=10, hi=720, unity=True, default=90),
           Param("interactive", "bool", "Spieler kann öffnen", unity=True, default=True),
       ])
def cargo_container(rng, a):
    p = a.p
    ln = p.choice("length", [4.0, 6.0, 6.0])
    w = p.value("width", rng.uniform(2.3, 2.6))
    h = p.value("height", rng.uniform(2.5, 2.9))
    mat = p.material(["M_HazardOrange", "M_Wall", "M_Metal", "M_RobotBody"])
    glow = p.glow()
    body = a.part("Body")
    t, fl = 0.08, 0.15
    a.meta.update({"length_m": ln, "opening_m": [round(w - 2 * t - 0.12, 4), round(h - fl - 0.25 - t, 4)]})
    cube(body, (w, ln, fl), (0, 0, fl / 2), "M_RobotDark")
    a.collider((w, ln, fl), (0, 0, fl / 2))
    for s in (-1, 1):  # side walls
        cube(body, (t, ln, h - fl - t), (s * (w - t) / 2, 0, fl + (h - fl - t) / 2), mat)
        a.collider((t, ln, h - fl - t), (s * (w - t) / 2, 0, fl + (h - fl - t) / 2))
    cube(body, (w - 2 * t, t, h - fl - t), (0, (ln - t) / 2, fl + (h - fl - t) / 2), mat)  # back wall
    a.collider((w - 2 * t, t, h - fl - t), (0, (ln - t) / 2, fl + (h - fl - t) / 2))
    cube(body, (w, ln, t), (0, 0, h - t / 2), mat)  # roof
    a.collider((w, ln, t), (0, 0, h - t / 2))
    front = -ln / 2
    head = 0.25
    cube(body, (w - 2 * t, 0.12, head), (0, front + 0.06, h - t - head / 2), "M_RobotDark")  # header
    a.collider((w - 2 * t, 0.12, head), (0, front + 0.06, h - t - head / 2))
    for s in (-1, 1):  # corner posts at the front
        cube(body, (0.06, 0.12, h - fl - t - head), (s * (w / 2 - t - 0.03), front + 0.06,
                                                     fl + (h - fl - t - head) / 2), "M_RobotDark")
        a.collider((0.06, 0.12, h - fl - t - head), (s * (w / 2 - t - 0.03), front + 0.06,
                                                     fl + (h - fl - t - head) / 2))
    if p.bool("ribs", 0.7):  # corrugation on the outside
        for i in range(int(ln / 0.5)):
            y = -ln / 2 + 0.25 + i * 0.5
            for s in (-1, 1):
                cube(body, (0.03, 0.12, h - fl - t - 0.2), (s * (w / 2 + 0.015), y, fl + (h - fl - t) / 2), mat)
    opening_w = w - 2 * t - 0.12
    opening_h = h - fl - t - head
    leaf_w = opening_w / 2
    for name, s, step in (("Door_Left", -1, 90), ("Door_Right", 1, -90)):
        hinge = (s * opening_w / 2, front - 0.04, fl)
        door = a.part(name, pivot=hinge)
        cx = hinge[0] - s * leaf_w / 2
        cube(door, (leaf_w - 0.01, 0.05, opening_h - 0.02), (cx, front - 0.04, fl + opening_h / 2), mat)
        a.collider((leaf_w - 0.01, 0.05, opening_h - 0.02), (cx, front - 0.04, fl + opening_h / 2), part=name)
        for f in (-0.25, 0.25):  # locking rods
            cyl(door, 0.02, opening_h - 0.1, (cx + f * leaf_w, front - 0.09, fl + opening_h / 2), "M_Metal",
                sides=6)
    cube(a.part("Glow"), (0.3, 0.03, 0.06), (0, front - 0.02, h - t - head / 2), glow)
    for name, step in (("Door_Left", 90), ("Door_Right", -90)):
        a.behaviour("Rotatable", {"target": name, "glow": "Glow", "body": "Body"},
                    {"axis": "up", "step": step, "speed": p.option("speed"), "target": 1,
                     "interactive": p.option("interactive")},
                    note="leaf swings out to the front around its hinge (Unity up)")
