"""Anchors for sound and effects (generation 3): empty parts like ``Audio_Hum`` or ``FX_Steam``.

Unity hangs an ``AudioSource`` or a particle system on them; the game's scripts
ignore unknown parts. An anchor sits on a part of the model (its centre, top,
front or bottom) and is that part's child, so it moves with it (a fan's
``Audio_Fan`` turns with the ``Rotor``). Nothing is rolled: anchors never change
a model's geometry, only add empties. Ruins (``damage`` destroyed) keep only a
``FX_Smoke`` above the wreck; fractured models get none (their parts are
fragments).

Naming: ``Audio_<Sound>`` for sound sources, ``FX_<Effect>`` for particle /
effect emitters (effect direction: Unity up, front anchors Unity forward).
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

Anchor = Tuple[str, str, str]  # (name, part, where: center | top | front | bottom)

ANCHORS: Dict[str, Sequence[Anchor]] = {
    # machines and ambience
    "machine": (("Audio_Hum", "Body", "center"), ("FX_Sparks", "Body", "front")),
    "generator": (("Audio_Hum", "Body", "center"),),
    "transformer": (("Audio_Hum", "Body", "center"), ("FX_Sparks", "Body", "top")),
    "reactor_core": (("Audio_Hum", "Body", "center"), ("Audio_Core", "Rotor", "center")),
    "pump": (("Audio_Pump", "Body", "center"),),
    "fan": (("Audio_Fan", "Rotor", "center"),),
    "vent": (("Audio_Air", "Body", "front"),),
    "server_rack": (("Audio_Hum", "Body", "center"),),
    "console": (("Audio_Beep", "Body", "top"),),
    "terminal": (("Audio_Beep", "Screen", "center"),),
    "monitor_wall": (("Audio_Beep", "Body", "front"),),
    "hologram": (("Audio_Hum", "Rotor", "center"),),
    "intercom": (("Audio_Voice", "Body", "front"),),
    "vending_machine": (("Audio_Hum", "Body", "center"),),
    "coffee_machine": (("Audio_Brew", "Body", "center"), ("FX_Steam", "Body", "top")),
    "cryo_pod": (("Audio_Hum", "Body", "center"), ("FX_Mist", "Glass", "center")),
    "crystal_cluster": (("Audio_Hum", "Crystals", "center"),),
    "hanging_crystals": (("Audio_Hum", "Crystals", "center"),),
    "mushroom": (("FX_Spores", "Mushroom", "top"),),
    "pipe": (("Audio_Flow", "Pipe", "center"),),
    "fluid_basin": (("Audio_Water", "Fluid", "center"),),
    # doors, lifts, moving floors
    "door": (("Audio_Door", "Frame_Top", "center"),),
    "shutter": (("Audio_Door", "Frame_Top", "center"),),
    "lift": (("Audio_Motor", "Base", "center"),),
    "conveyor": (("Audio_Motor", "Body", "center"),),
    "retractable_bridge": (("Audio_Motor", "Housing", "center"),),
    "turntable": (("Audio_Motor", "Base", "center"),),
    "breakable_platform": (("Audio_Crack", "Frame", "center"), ("FX_Dust", "Frame", "center")),
    "phase_platform": (("Audio_Hum", "Deck", "center"),),
    "portal_frame": (("Audio_Hum", "Surface", "center"), ("FX_Portal", "Surface", "center")),
    "pad": (("Audio_Hum", "Body", "top"),),
    # traps and puzzles
    "crusher": (("Audio_Impact", "Base", "top"), ("FX_Dust", "Base", "top")),
    "saw_blade": (("Audio_Saw", "Rotor", "center"), ("FX_Sparks", "Rotor", "top")),
    "steam_vent": (("Audio_Hiss", "Body", "top"),),
    "shock_plate": (("Audio_Zap", "Body", "top"), ("FX_Sparks", "Body", "top")),
    "spike_trap": (("Audio_Spikes", "Base", "top"),),
    "force_field": (("Audio_Hum", "Field", "center"),),
    "cable_mess": (("Audio_Zap", "Glow", "center"), ("FX_Sparks", "Glow", "center")),
    "gear_puzzle": (("Audio_Gears", "Body", "front"),),
    "scanner": (("Audio_Beep", "Body", "front"),),
    "keypad": (("Audio_Beep", "Body", "front"),),
    # robots
    "turret": (("Audio_Servo", "Turret", "center"), ("FX_Muzzle", "Gun", "front")),
    "drone": (("Audio_Rotor", "Body", "center"),),
    "camera": (("Audio_Servo", "Rotor", "center"),),
    "robot_arm": (("Audio_Servo", "Turret", "center"),),
    "spider_bot": (("Audio_Servo", "Body", "center"),),
    "service_robot": (("Audio_Servo", "Body", "center"),),
    "patrol_drone": (("Audio_Rotor", "Body", "center"),),
    "vent_crawler": (("Audio_Servo", "Body", "center"),),
    "robot_dog": (("Audio_Servo", "Body", "center"),),
    "mech": (("Audio_Servo", "Torso", "center"), ("FX_Steam", "Torso", "top")),
    # the newer puzzles, lights, facilities, nature, space and ruins
    "sequence_panel": (("Audio_Tone", "Body", "front"),),
    "water_level": (("Audio_Water", "Body", "center"),),
    "crane": (("Audio_Motor", "Body", "top"),),
    "countdown": (("Audio_Beep", "Body", "front"),),
    "emergency_light": (("Audio_Alarm", "Body", "front"),),
    "light_strip": (("Audio_Buzz", "Body", "center"),),
    "floodlight": (("Audio_Hum", "Body", "top"),),
    "lab_device": (("Audio_Hum", "Body", "center"),),
    "galley": (("Audio_Hum", "Body", "center"),),
    "cocoon": (("Audio_Heartbeat", "Glow", "center"),),
    "fungus_carpet": (("FX_Spores", "Fungus", "top"),),
    "escape_pod": (("Audio_Hum", "Body", "center"),),
    "crashed_pod": (("FX_Smoke", "Wreck", "top"), ("FX_Sparks", "Wreck", "center")),
    "burnt_console": (("FX_Smoke", "Wreck", "top"), ("FX_Sparks", "Lights", "center")),
}


def _point(lo, hi, where: str):
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    if where == "top":
        c[2] = hi[2]
    elif where == "bottom":
        c[2] = lo[2]
    elif where == "front":
        c[1] = lo[1]
    elif where != "center":
        raise ValueError(f"anchor position {where!r}")
    return tuple(c)


def add_anchors(asset, model_type: str, damage: str = "intact") -> int:
    """Add the anchors of ``model_type`` (on parts that exist); returns how many. Runs after damage / wear."""
    table = ANCHORS.get(model_type, ())
    if not table or damage == "fractured":
        return 0
    if damage == "destroyed":
        lo, hi = asset.bbox()
        asset.empty("FX_Smoke", _point(lo, hi, "top"))
        return 1
    count = 0
    for name, part, where in table:
        obj = asset.get(part)
        if obj is None or obj.mesh is None or asset.get(name) is not None:
            continue
        lo, hi = obj.mesh.bbox()
        asset.empty(name, _point(lo, hi, where), parent=part)
        count += 1
    return count


__all__ = ["ANCHORS", "add_anchors"]
