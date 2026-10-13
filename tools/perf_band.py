#!/usr/bin/env python3
"""Performance bands: fixed workloads, several runs, every run classified by the machine's load.

    python3 tools/perf_band.py --save before                 # measure, keep the band as "before"
    python3 tools/perf_band.py --compare before              # measure again, compare with "before"
    python3 tools/perf_band.py --code ../other/checkout --save main   # measure another checkout's code
    python3 tools/perf_band.py --workload catalog --runs 5

Measure first, then optimise - and compare bands, not single runs (Cube Escape 0.49, ``Tools/perfdiff.py``):

- **Named steps:** each run's ``manifest.json`` gives the stages (``timings.seconds``), the steps inside them
  (``timings.steps``: model builds, contract check, planning) and the summed Blender times (``worker_seconds``),
  plus the wall clock of the whole command.
- **Load:** the 1-minute load average per core before and after a run: up to 0.5 *ruhig*, up to 1.0 *leicht*
  (tolerance doubled), above *stark* - such a run is kept in the report but not counted.
- **CPU time** (``cpu``: user + system of the command and its Blender processes) hardly depends on other load - it
  is counted in every run, also *stark* ones: the comparison that still works on a busy machine.
- **Band:** min / median / max of the counted runs per step. A comparison looks at the medians: a step is
  *langsamer* or *schneller* only beyond the tolerance (15 % and at least 0.3 s; doubled when a run was *leicht*).

Bands are saved under ``output/perf/<name>.json`` (machine-specific, not checked in). Other sessions may pause for
a measurement (AGENTS.md › "Ganze Leistung des Geräts").
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import statistics
import subprocess
import sys
import time
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "perf")
TOLERANCE = 0.15       # relative
TOLERANCE_S = 0.3      # absolute floor in seconds
QUIET, LIGHT = 0.5, 1.0  # load per core: ruhig up to QUIET, leicht up to LIGHT, stark above

# fixed workloads: name -> (cubegen arguments, warm-up: run once before measuring in the same folder)
WORKLOADS: Dict[str, Dict] = {
    "catalog": {"about": "Katalog ohne Blender (561 Modelle): Planen, Bauen, Vertrag, OBJ, Manifest",
                "args": ["generate", "--seed", "42", "--count", "3", "--no-blender"], "warm": False},
    "cached": {"about": "Katalog mit Blender, zweiter Lauf: alles aus dem Cache (Prüfen statt Bauen)",
               "args": ["generate", "--seed", "42", "--count", "3", "--no-blend"], "warm": True},
    "kit": {"about": "Bau-Kit mit Blender als Sets (26 Modelle, FBX, Vorschauen)",
            "args": ["generate", "--seed", "42", "--types", "wall,floor_tile,ceiling_module,ceiling_panel,catwalk,"
                     "railing,pillar,crate,stairs,platform,ramp,wall_cap,wall_corner", "--count", "2", "--set",
                     "--no-blend", "--force"], "warm": False},
}
DEFAULT = ("catalog", "cached")


def load_per_core() -> Optional[float]:
    try:
        return os.getloadavg()[0] / (os.cpu_count() or 1)
    except (AttributeError, OSError):
        return None


def classify(load: Optional[float]) -> str:
    if load is None:
        return "ruhig"
    return "ruhig" if load <= QUIET else "leicht" if load <= LIGHT else "stark"


def run_once(name: str, code: str, folder: str) -> Dict:
    spec = WORKLOADS[name]
    env = dict(os.environ, PYTHONPATH=code)
    cmd = [sys.executable, "-m", "cubegen", *spec["args"], "--out", folder]
    before = load_per_core()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=code, env=env, capture_output=True, text=True)
    wall = time.perf_counter() - start
    done = resource.getrusage(resource.RUSAGE_CHILDREN)  # the command and every process it waited for (Blender)
    cpu = (done.ru_utime - usage.ru_utime) + (done.ru_stime - usage.ru_stime)
    after = load_per_core()
    if proc.returncode != 0:
        raise RuntimeError(f"{name}: cubegen failed:\n{(proc.stdout + proc.stderr)[-1500:]}")
    with open(os.path.join(folder, "manifest.json"), "r", encoding="utf-8") as fh:
        timings = json.load(fh).get("timings") or {}
    values = {"wall": wall, "cpu": cpu}
    values.update({f"stage.{k}": v for k, v in (timings.get("seconds") or {}).items()})
    values.update({f"step.{k}": v for k, v in (timings.get("steps") or {}).items()})
    values.update({f"blender.{k}": v for k, v in (timings.get("worker_seconds") or {}).items()})
    load = max(x for x in (before, after) if x is not None) if before is not None or after is not None else None
    return {"values": values, "load": None if load is None else round(load, 2), "class": classify(load)}


def measure(names: List[str], runs: int, code: str, log=print) -> Dict:
    result = {"code": os.path.abspath(code), "version": _version(code), "cores": os.cpu_count(), "workloads": {}}
    for name in names:
        folder = os.path.join(OUT, "work", name)
        shutil.rmtree(folder, ignore_errors=True)
        if WORKLOADS[name]["warm"]:
            run_once(name, code, folder)
        rows = []
        for k in range(runs):
            row = run_once(name, code, folder)
            rows.append(row)
            log(f"  {name} {k + 1}/{runs}: {row['values']['wall']:.1f} s, Last {row['load']} je Kern ({row['class']})")
        result["workloads"][name] = {"runs": rows, "band": band(rows)}
    return result


def band(rows: List[Dict]) -> Dict:
    counted = [r for r in rows if r["class"] != "stark"]
    keys = sorted({k for r in rows for k in r["values"]})
    out = {"counted": len(counted), "light": any(r["class"] == "leicht" for r in counted), "steps": {}}
    for key in keys:
        source = rows if key == "cpu" else counted  # CPU time: every run; wall clock times: not under heavy load
        vals = [r["values"][key] for r in source if key in r["values"]]
        if vals:
            out["steps"][key] = {"min": round(min(vals), 2), "median": round(statistics.median(vals), 2),
                                 "max": round(max(vals), 2)}
    return out


def compare(base: Dict, now: Dict) -> Dict[str, List[Dict]]:
    """Per workload and step: before / after medians and a verdict."""
    report = {}
    for name, entry in now["workloads"].items():
        old = base.get("workloads", {}).get(name)
        rows = []
        if not old:
            report[name] = [{"step": "-", "verdict": "keine Basis"}]
            continue
        timed = old["band"]["counted"] and entry["band"]["counted"]
        factor = 2.0 if old["band"]["light"] or entry["band"]["light"] else 1.0
        for step, b in entry["band"]["steps"].items():
            if step != "cpu" and not timed:
                continue  # wall clock under heavy load: not counted

            a = old["band"]["steps"].get(step)
            if not a:
                rows.append({"step": step, "after": b["median"], "verdict": "neu"})
                continue
            delta = b["median"] - a["median"]
            limit = max(TOLERANCE * a["median"], TOLERANCE_S) * factor
            verdict = "gleich" if abs(delta) <= limit else "schneller" if delta < 0 else "langsamer"
            rows.append({"step": step, "before": a["median"], "after": b["median"], "delta": round(delta, 2),
                         "verdict": verdict})
        if not timed:
            rows.append({"step": "Laufzeiten", "verdict": "nicht gewertet (stark belastet) - nur CPU-Zeit verglichen"})
        report[name] = rows
    return report


def _version(code: str) -> str:
    out = subprocess.run([sys.executable, "-m", "cubegen", "--version"], cwd=code, capture_output=True, text=True,
                         env=dict(os.environ, PYTHONPATH=code))
    return out.stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--workload", help="Arbeitslasten, kommagetrennt: " + ", ".join(WORKLOADS)
                    + f" (Standard: {', '.join(DEFAULT)})")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--code", default=ROOT, help="Checkout, dessen cubegen gemessen wird (Standard: dieser)")
    ap.add_argument("--save", help="Band unter output/perf/<Name>.json speichern")
    ap.add_argument("--compare", help="mit output/perf/<Name>.json vergleichen")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    if args.list:
        for name, w in WORKLOADS.items():
            print(f"{name:8s} {w['about']}")
        return 0
    names = args.workload.split(",") if args.workload else list(DEFAULT)
    unknown = [n for n in names if n not in WORKLOADS]
    if unknown:
        ap.error(f"unbekannte Arbeitslast: {', '.join(unknown)}")
    os.makedirs(OUT, exist_ok=True)
    result = measure(names, args.runs, args.code)
    for name, entry in result["workloads"].items():
        b = entry["band"]
        print(f"{name}: {b['counted']} von {len(entry['runs'])} Läufen gewertet" + (" (leicht belastet)" if b["light"]
                                                                                     else "") + "; CPU-Zeit aus allen")
        for step, v in b["steps"].items():
            print(f"  {step:22s} {v['min']:7.2f} {v['median']:7.2f} {v['max']:7.2f} s")
    if args.save:
        with open(os.path.join(OUT, args.save + ".json"), "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=1)
        print(f"Band gespeichert: output/perf/{args.save}.json")
    if args.compare:
        with open(os.path.join(OUT, args.compare + ".json"), "r", encoding="utf-8") as fh:
            base = json.load(fh)
        print(f"Vergleich mit {args.compare} ({base.get('version')}) -> {result['version']}:")
        for name, rows in compare(base, result).items():
            print(f"  {name}")
            for r in rows:
                if "before" in r:
                    print(f"    {r['step']:22s} {r['before']:7.2f} -> {r['after']:7.2f} s  {r['verdict']}")
                else:
                    print(f"    {r['step']:22s} {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
