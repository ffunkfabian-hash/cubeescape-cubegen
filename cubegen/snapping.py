"""Snapping kit parts together at their connectors (Blender add-on: "Einrasten").

Pure Python, no bpy: the add-on passes each model's connectors (``families.connectors``,
asset space: metres, Z up) and its pose in the scene - a turn about Z (``yaw``, radians)
and the position of its origin. :func:`snap` finds the pair of compatible connectors
(``families.JOINS``) that is closest right now and returns the pose that puts the moving
model's connector exactly onto the target's:

* ``face``  - walkway ends, wall ends, pipe ends, ceiling edges: positions meet, directions opposite
* ``align`` - door in a wall opening, cap on a wall top, baseboard on a wall face: positions meet,
  same direction

Connectors that already have a partner (another model's compatible connector at the same
spot) are skipped, so repeated snapping builds chains.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .families import JOINS, TOL

Pose = Tuple[float, Tuple[float, float, float]]  # yaw (radians about Z), origin (x, y, z)


def join(kind_a: str, kind_b: str) -> Optional[str]:
    """How two connector kinds join: "face", "align" or None (they don't)."""
    return JOINS.get((kind_a, kind_b)) or JOINS.get((kind_b, kind_a))


def _turn(yaw: float, v) -> Tuple[float, float, float]:
    c, s = math.cos(yaw), math.sin(yaw)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1], v[2])


def place(connector: Dict[str, Any], pose: Pose) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """World position and direction of a connector of a model in ``pose``."""
    yaw, origin = pose
    p = _turn(yaw, connector["pos"])
    return (p[0] + origin[0], p[1] + origin[1], p[2] + origin[2]), _turn(yaw, connector["dir"])


def pose_onto(moving: Dict[str, Any], target_pos, target_dir, mode: str) -> Pose:
    """Pose of the moving model that puts its connector ``moving`` onto the target connector."""
    want = target_dir if mode == "align" else (-target_dir[0], -target_dir[1], -target_dir[2])
    yaw = math.atan2(want[1], want[0]) - math.atan2(moving["dir"][1], moving["dir"][0])
    yaw = math.atan2(math.sin(yaw), math.cos(yaw))
    p = _turn(yaw, moving["pos"])
    return yaw, (target_pos[0] - p[0], target_pos[1] - p[1], target_pos[2] - p[2])


def _dist(a, b) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def occupied(models: Sequence[Tuple[Any, Sequence[Dict[str, Any]], Pose]]) -> set:
    """``(model id, connector name)`` of every connector that already meets a compatible one of another model."""
    placed = [(mid, c, *place(c, pose)) for mid, cons, pose in models for c in cons]
    taken = set()
    for i, (ma, ca, pa, da) in enumerate(placed):
        for mb, cb, pb, db in placed[i + 1:]:
            if ma == mb or _dist(pa, pb) > TOL:
                continue
            mode = join(ca["kind"], cb["kind"])
            dot = da[0] * db[0] + da[1] * db[1] + da[2] * db[2]
            if (mode == "face" and dot < -0.99) or (mode == "align" and dot > 0.99):
                taken.update({(ma, ca["name"]), (mb, cb["name"])})
    return taken


def snap(moving: Sequence[Dict[str, Any]], moving_pose: Pose,
         targets: Iterable[Tuple[Any, Sequence[Dict[str, Any]], Pose]], moving_id: Any = None,
         max_distance: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """The best snap of a model onto the others: {"pose", "connector", "target", "target_connector", "distance",
    "mode"} or None when no compatible free connector exists (within ``max_distance`` metres, if given)."""
    targets = list(targets)
    taken = occupied([(mid, cons, pose) for mid, cons, pose in targets])
    best = None
    for cm in moving:
        pm, dm = place(cm, moving_pose)
        for mid, cons, pose in targets:
            if mid == moving_id:
                continue
            for ct in cons:
                mode = join(cm["kind"], ct["kind"])
                if mode is None or (mid, ct["name"]) in taken:
                    continue
                pt, dt = place(ct, pose)
                distance = _dist(pm, pt)
                if max_distance is not None and distance > max_distance:
                    continue
                new_pose = pose_onto(cm, pt, dt, mode)
                turn = abs(math.atan2(math.sin(new_pose[0] - moving_pose[0]), math.cos(new_pose[0] - moving_pose[0])))
                score = distance + turn * 0.25  # prefer the nearest joint, then the smallest turn
                if best is None or score < best["score"] - 1e-9:
                    best = {"pose": new_pose, "connector": cm["name"], "target": mid, "target_connector": ct["name"],
                            "distance": distance, "mode": mode, "score": score}
    return best


def connector_data(asset, model_type: str) -> List[Dict[str, Any]]:
    """The connectors of an asset as plain lists (JSON for Blender custom properties)."""
    from .families import connectors

    out = []
    for c in connectors(asset, model_type):
        entry = {k: (list(v) if isinstance(v, tuple) else v) for k, v in c.items() if k != "moves"}
        out.append(entry)
    return out


__all__ = ["join", "place", "pose_onto", "occupied", "snap", "connector_data"]
