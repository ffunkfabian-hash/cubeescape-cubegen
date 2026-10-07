"""Experimental showcase for the geometry primitives; not a gameplay asset."""

from __future__ import annotations

import math

from ..geometry import (
    angle_profile,
    grate,
    i_beam,
    pipe_section,
    rounded_box,
    tee_profile,
    u_channel,
    wedge,
)
from .registry import model


@model(
    "geometry_test",
    "GeometryTest",
    "props",
    "Experimental showcase of the eight added geometry primitives; for visual testing only",
    pivot="floor",
)
def geometry_test(rng, asset):
    accent = rng.choice(("M_Warning", "M_HazardOrange", "M_GlowOrange", "M_GlowCyan"))
    pipe_height = rng.choice((0.7, 0.8, 0.9))
    samples = (
        ("01_PipeSection", pipe_section(0.32, pipe_height, 0.06, sides=8, role="M_Metal"),
         (0, 0, pipe_height / 2),
         (0.0, 0.0, 0.0)),
        ("02_UChannel", u_channel(0.8, 0.55, 0.16, 0.07, role="M_RobotDark"), (1.2, 0, 0.08),
         (math.pi / 2, 0.0, 0.0)),
        ("03_AngleProfile", angle_profile(0.75, 0.65, 0.16, 0.07, role="M_Metal"), (2.4, 0, 0.08),
         (math.pi / 2, 0.0, 0.0)),
        ("04_TeeProfile", tee_profile(0.8, 0.6, 0.16, 0.07, role="M_HazardOrange"), (3.6, 0, 0.08),
         (math.pi / 2, 0.0, 0.0)),
        ("05_IBeam", i_beam(0.9, 0.7, 0.16, 0.07, 0.1, role="M_RobotDark"), (0, 1.1, 0.08),
         (math.pi / 2, 0.0, 0.0)),
        ("06_Wedge", wedge(0.8, 0.5, 0.16, role=accent), (1.2, 1.1, 0.4),
         (0.0, math.pi / 2, 0.0)),
        ("07_Grate", grate(0.9, 0.7, 0.08, 0.055, 0.045, role="M_Metal"), (2.4, 1.1, 0.04),
         (0.0, 0.0, 0.0)),
        ("08_RoundedBox", rounded_box(0.8, 0.65, 0.45, accent, radius=0.12), (3.6, 1.1, 0.225),
         (0.0, 0.0, 0.0)),
    )
    for name, primitive, location, rotation in samples:
        asset.part(name).add(primitive, loc=location, rot=rotation, name=name)
    asset.meta["experimental"] = True
    asset.meta["geometry_demo"] = [name for name, _, _, _ in samples]
