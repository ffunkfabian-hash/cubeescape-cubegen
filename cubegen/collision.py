"""Explicit fallback collision for gameplay recipes without authored shapes.

Static imports may use an envelope; gameplay adapters never do. Preserve every
authored collider set. When none exists, keep fixed meshes exact (including
openings) and put convex collision on each moving mesh and its descendants.
Pickups keep the importer's interaction trigger rather than solid collision.
"""
from .contract import CONTRACT


def complete_gameplay_collision(asset):
    if asset.colliders or not asset.behaviours:
        return
    if any(b["script"] == "ItemPickup" for b in asset.behaviours):
        return
    moving = set()
    for behaviour in asset.behaviours:
        roles = behaviour["parts"]
        keys = set(CONTRACT["behaviours"][behaviour["script"]]["moves"])
        # A Machine may create its own Rotator, and SignalLight.Rotate animates
        # a rotor without an independent Rotator behaviour.
        if behaviour["script"] in ("Machine", "SignalLight"):
            keys.add("rotor")
        for role in keys:
            value = roles.get(role, [])
            moving.update(value if isinstance(value, list) else [value])
    for obj in asset.meshes():
        if obj.name in ("Damage", "Wear") or obj.name.startswith("Clutter_"):
            continue
        ancestor = obj
        dynamic = False
        while ancestor is not None:
            dynamic |= ancestor.name in moving
            ancestor = asset.get(ancestor.parent) if ancestor.parent else None
        asset.mesh_collider(obj.name, convex=dynamic)


def complete_static_collision(asset):
    """Fixed geometry uses its meshes, never a box across openings or debris gaps."""
    if asset.colliders or asset.behaviours:
        return
    for obj in asset.meshes():
        if obj.name == "Wear":
            continue
        asset.mesh_collider(obj.name, convex=False)
