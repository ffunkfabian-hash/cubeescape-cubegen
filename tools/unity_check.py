#!/usr/bin/env python3
"""Unity check: fixed probe exports through Cube Escape's real importer (in its verify copy, never on a checkout).

    python3 tools/unity_check.py                 # every probe (about 3-5 min)
    python3 tools/unity_check.py --quick         # build kit + paint only
    python3 tools/unity_check.py --only paint,runtime --keep

Each probe is a small, fixed ``cubegen generate`` run (same seed, same options every time). Its models go through
the tests Cube Escape itself uses for real exports - started with ``verify.sh`` of the Cube Escape checkout, which
runs Unity in that checkout's verify copy (the game's rule: Unity never on a checkout):

- FBX + sidecar -> ``CubegenCliIntegrationTests`` (editor import: contract, hierarchy, materials, colliders, LODs,
  stable re-import); the log line "cubegen CLI integration: …" gives the counts.
- GLB + sidecar of every type -> ``CubegenRealGenerationTests`` (the workbench's runtime path); it writes
  ``runtime-audit.json`` next to the models.

The Cube Escape checkout: ``--ce`` or ``$CUBEGEN_CE_ROOT``, else ``~/Claude/Cube Escape``. Without it (or without
its verify script) the check says so and exits 0 - ``--require`` makes that an error (release check).
Report: ``output/unity_check/report.json``. Exit code 1 when a probe fails.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(".agents", "skills", "ce-testing", "scripts", "verify.sh")
RUN_NAME = "cubegen_check"
TESTS = {
    "cli": ("CubeEscape.Tests.EditMode.CubegenCliIntegrationTests."
            "RealCliExportsPreserveHierarchyMaterialsAndReimportIdentity", "CUBEGEN_TEST_EXPORTS"),
    "runtime": ("CubeEscape.Tests.EditMode.CubegenRealGenerationTests", "CUBEGEN_RUNTIME_EXPORTS"),
}
BUILD_KIT = ("wall,floor_tile,ceiling_module,ceiling_panel,catwalk,railing,pillar,crate,stairs,platform,ramp,wall_cap,"
             "wall_corner")
# fixed probes: name -> seed, generate options, test. Change a probe only on purpose (results stay comparable).
PROBES: Dict[str, Dict] = {
    "kit": {"seed": "42", "test": "cli", "about": "Bau-Kit als Sets (Anschlussseiten, Maß-Parameter)",
            "args": ["--types", BUILD_KIT, "--count", "2", "--set"]},
    "variety": {"seed": "42", "test": "cli", "about": "Zusatzdetails, Torbogen, Kamera, Laserteile, Werkzeug",
                "args": ["--types", "ceiling_module,warning_beacon,archway,camera,laser_mirror,laser_receiver,"
                                    "laser_splitter,tool", "--count", "2"]},
    "gameplay": {"seed": "7", "test": "cli", "about": "Verhalten: Tür, Hebel, Knopf, Ventil, Drehteller, Förderband",
                 "args": ["--types", "door,lever,button,valve,turntable,conveyor,keypad,lift", "--count", "1"]},
    "paint": {"seed": "19", "test": "cli", "about": "Anstrich Crystal, Anbauten, facettierte Kristalle",
              "args": ["--types", "floor_tile,pillar,catwalk,rock,hanging_crystals,test_wall_modules", "--count", "1",
                       "--param", "floor_tile.dressing=ruin", "--param", "pillar.dressing=organic",
                       "--param", "catwalk.dressing=organic", "--param", "rock.crystals=3",
                       "--param", "rock.crystal_cut=faceted", "--param", "hanging_crystals.crystal_cut=faceted",
                       "--param", "test_wall_modules.crystals=many", "--paint", "crystal", "--texture-size", "128"]},
    "custom": {"seed": "3", "test": "cli", "about": "eigenes Thema aus einer Datei (--paint-file)",
               "args": ["--types", "wall,door,crate,pillar", "--count", "1",
                        "--paint-file", os.path.join(ROOT, "paints", "custom_example.json"), "--texture-size", "128"]},
    "textures": {"seed": "5", "test": "cli", "about": "Kacheltexturen (tiled)",
                 "args": ["--types", "crate,wall,console", "--count", "1", "--textures", "tiled",
                          "--texture-size", "128"]},
    "damage": {"seed": "11", "test": "cli", "about": "beschädigte Varianten",
               "args": ["--types", "crate,wall,pillar,console", "--count", "1", "--damage", "damaged"]},
    "single": {"seed": "21", "test": "cli", "about": "ein Renderer je statischem Modell (--single-renderer, mit LODs)",
               "args": ["--types", "crate,pillar,wall,console,rock,catwalk,window_wall,shelf", "--count", "1",
                        "--single-renderer", "--lods"]},
    "runtime": {"seed": "42", "test": "runtime", "about": "alle Typen als GLB (Laufzeitpfad der Werkbank)",
                "args": ["--count", "1", "--formats", "glb"]},
}
QUICK = ("kit", "paint")

# "Passed | bestanden 1 | fehlgeschlagen 0 | …" or "Failed(Child) | bestanden 0 | fehlgeschlagen 1 | …"
RESULT = re.compile(r"(Passed|Failed)(?:\([^)]*\))?\s*\|\s*bestanden\s+(\d+)\s*\|\s*fehlgeschlagen\s+(\d+)")
LOG = re.compile(r"Log:\s*(\S.*?\.log)")
INTEGRATION = re.compile(r"cubegen CLI integration: (\d+) Gameplay / (\d+) statisch / (\d+) Item-Zuordnungen offen / "
                         r"(\d+) ungültige Exporte abgelehnt / (\d+) Fehler\.")


def ce_root(explicit: Optional[str] = None) -> str:
    return os.path.abspath(os.path.expanduser(explicit or os.environ.get("CUBEGEN_CE_ROOT")
                                              or "~/Claude/Cube Escape"))


def available(ce: str) -> str:
    """'' when the check can run against ``ce``, else why not."""
    if not os.path.isdir(ce):
        return f"kein Cube-Escape-Checkout unter {ce} (--ce oder $CUBEGEN_CE_ROOT)"
    if not os.access(os.path.join(ce, VERIFY), os.X_OK):
        return f"{VERIFY} fehlt in {ce}"
    return ""


def plan(only: Optional[List[str]] = None, quick: bool = False) -> List[str]:
    names = list(QUICK) if quick else list(PROBES)
    if only:
        unknown = [n for n in only if n not in PROBES]
        if unknown:
            raise ValueError(f"unbekannte Prüfsätze: {', '.join(unknown)} (bekannt: {', '.join(PROBES)})")
        names = [n for n in PROBES if n in only]
    return names


def generate_command(name: str, out: str) -> List[str]:
    probe = PROBES[name]
    return [sys.executable, "-m", "cubegen", "generate", "--seed", probe["seed"], *probe["args"], "--no-render",
            "--no-blend", "--out", out]


def parse_verify(stdout: str) -> Dict:
    """Result line and log of a ``verify.sh test`` run."""
    found = RESULT.search(stdout)
    log = LOG.search(stdout)
    return {"passed": bool(found) and found.group(1) == "Passed" and found.group(3) == "0",
            "tests": int(found.group(2)) + int(found.group(3)) if found else 0,
            "log": log.group(1).strip() if log else None}


def parse_integration(text: str) -> Optional[Dict]:
    found = INTEGRATION.search(text)
    if not found:
        return None
    keys = ("gameplay", "static", "unmapped_items", "rejected", "errors")
    return dict(zip(keys, (int(v) for v in found.groups())))


def runtime_audit(models: str) -> Optional[Dict]:
    path = os.path.join(models, "runtime-audit.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh).get("models", [])
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row.get("result", "?")] = counts.get(row.get("result", "?"), 0) + 1
    return {"models": len(rows), **counts,
            "failed_files": [row["file"] for row in rows if row.get("result") == "failed"][:20]}


def run_probe(name: str, ce: str, work: str, log=print) -> Dict:
    probe = PROBES[name]
    out = os.path.join(work, name)
    shutil.rmtree(out, ignore_errors=True)
    start = time.time()
    env = dict(os.environ, PYTHONPATH=ROOT + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH")
                                              else ""))
    gen = subprocess.run(generate_command(name, out), cwd=ROOT, env=env, capture_output=True, text=True)
    entry = {"name": name, "about": probe["about"], "test": probe["test"], "seconds": {}}
    entry["seconds"]["generate"] = round(time.time() - start, 1)
    if gen.returncode != 0:
        entry.update(ok=False, problem="cubegen generate fehlgeschlagen", output=(gen.stdout + gen.stderr)[-2000:])
        return entry
    models = os.path.join(out, "models")
    entry["exports"] = len([f for f in os.listdir(models) if f.endswith(".cubegen.json")])
    test_filter, variable = TESTS[probe["test"]]
    start = time.time()
    unity = subprocess.run([os.path.join(ce, VERIFY), "test", "EditMode", test_filter, RUN_NAME], cwd=ce,
                           env=dict(os.environ, **{variable: models}), capture_output=True, text=True)
    entry["seconds"]["unity"] = round(time.time() - start, 1)
    result = parse_verify(unity.stdout + unity.stderr)
    entry.update(result)
    if result["log"] and os.path.isfile(result["log"]):
        with open(result["log"], "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        entry["integration"] = parse_integration(text)
    if probe["test"] == "runtime":
        entry["runtime"] = runtime_audit(models)
    entry["ok"] = result["passed"] and unity.returncode == 0
    if not entry["ok"]:
        entry["output"] = (unity.stdout + unity.stderr)[-3000:]
    return entry


def summary_line(entry: Dict) -> str:
    if "exports" not in entry:
        return f"{entry['name']:9s} FEHLER  {entry.get('problem', '')}"
    counts = entry.get("integration")
    if counts:
        detail = (f"{counts['gameplay']} Gameplay / {counts['static']} statisch / {counts['unmapped_items']} "
                  f"Items offen / {counts['rejected']} abgelehnt / {counts['errors']} Fehler")
    elif entry.get("runtime"):
        rt = entry["runtime"]
        detail = (f"{rt['models']} GLB: {rt.get('accepted', 0)} angenommen, {rt.get('unsupported', 0)} mit nicht "
                  f"unterstütztem Verhalten, {rt.get('failed', 0)} fehlgeschlagen")
    else:
        detail = "kein Zähler im Log"
    state = "ok    " if entry["ok"] else "FEHLER"
    seconds = sum(entry["seconds"].values())
    return f"{entry['name']:9s} {state} {entry['exports']:3d} Modelle, {detail} ({seconds:.0f} s)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ce", help="Cube-Escape-Checkout (Standard: $CUBEGEN_CE_ROOT oder ~/Claude/Cube Escape)")
    ap.add_argument("--quick", action="store_true", help=f"nur {', '.join(QUICK)}")
    ap.add_argument("--only", help="Prüfsätze, kommagetrennt: " + ", ".join(PROBES))
    ap.add_argument("--out", default=os.path.join(ROOT, "output", "unity_check"), help="Arbeitsordner und Bericht")
    ap.add_argument("--require", action="store_true", help="fehlendes Cube Escape ist ein Fehler (Release-Prüfung)")
    ap.add_argument("--keep", action="store_true", help="Exporte behalten (Standard: nur bei Fehlern)")
    ap.add_argument("--list", action="store_true", help="Prüfsätze zeigen")
    args = ap.parse_args(argv)
    if args.list:
        for name, probe in PROBES.items():
            print(f"{name:9s} {probe['test']:7s} {probe['about']}")
        return 0
    names = plan(args.only.split(",") if args.only else None, args.quick)
    ce = ce_root(args.ce)
    why = available(ce)
    if why:
        print(f"Unity-Check übersprungen: {why}")
        return 2 if args.require else 0
    os.makedirs(args.out, exist_ok=True)
    report = {"cubegen": _version(), "ce": ce, "ce_commit": _git_head(ce), "probes": []}
    for name in names:
        print(f"> {name}: {PROBES[name]['about']} …", flush=True)
        entry = run_probe(name, ce, args.out)
        report["probes"].append(entry)
        print("  " + summary_line(entry), flush=True)
        if entry["ok"] and not args.keep:
            shutil.rmtree(os.path.join(args.out, name), ignore_errors=True)
    report["ok"] = all(p["ok"] for p in report["probes"])
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    total = sum(p.get("exports", 0) for p in report["probes"])
    print(f"Unity-Check {'bestanden' if report['ok'] else 'FEHLGESCHLAGEN'}: {len(report['probes'])} Prüfsätze, "
          f"{total} Modelle, Cube Escape {report['ce_commit'] or '?'} - Bericht {os.path.join(args.out, 'report.json')}")
    for p in report["probes"]:
        if not p["ok"]:
            print(f"--- {p['name']} ---\n{p.get('output', '')}")
    return 0 if report["ok"] else 1


def _version() -> str:
    sys.path.insert(0, ROOT)
    from cubegen import __version__

    return __version__


def _git_head(path: str) -> Optional[str]:
    try:
        out = subprocess.run(["git", "-C", path, "log", "--oneline", "-1"], capture_output=True, text=True)
        return out.stdout.strip() or None
    except OSError:
        return None


if __name__ == "__main__":
    sys.exit(main())
