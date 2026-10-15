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

The sidecars are written for the contract version Cube Escape keeps (``Assets/Resources/Cubegen/
cubegen_contract.json``, ``generate --contract``): with version 1 the Emission map of the paint probe (Crystal) stays in
the manifest, with version 2 the import reads it too.

Probe ``neutral`` (0.24.0, "Anstrich neutral") needs contract version 3 (neutral maps and the scheme in the sidecar).
Does Cube Escape read version 3, its sidecars must import. Below that it runs twice: written for version 3 the import
has to reject every model (expected - ``rejected_as_expected``), written for Cube Escape's version (without the neutral
maps) it has to import. Every probe with ``--paint`` also gets its reference maps (``tools/paint_reference.py``: every
scheme composed from the neutral maps; needs numpy - without it here, with Blender's Python like ``run_tests.py``) in
``<probe>/paint_reference`` - handed to the Unity run as
``$CUBEGEN_PAINT_REFERENCE`` for the shader comparison (Cube Escape ``SurfaceRenderTests``, once it exists).

One heavy run at a time (0.25.0, Cube Escape 0.59 "Turnstile"): before its first Unity start the check queues on Cube
Escape's machine-wide lock - an exclusive ``flock`` on ``~/Library/Caches/CubeEscape/heavy-run.lock`` (``HeavyLock``;
created when missing, never deleted). A waiting run prints who holds it (the holder's JSON line ``{"pid", "what",
"checkout", "since"}``) and again every five minutes; it holds the lock until the last probe is done. The lock's file
descriptor is never inherited (``O_CLOEXEC``): Unity or a background child of ``verify.sh`` can't keep it after the
check. Children get ``CE_HEAVY_HELD=1`` so Cube Escape's own steps don't wait for their parent; ``CE_HEAVY_LOCK=0``
skips the queue (``CE_HEAVY_LOCK_FILE`` moves the file - tests only). Each Unity step runs in a process group of its
own (0.27.0, ``run_in_group``): TERM/HUP/INT for the check go on to the whole group, and the step ends only when the
group is empty - Unity under ``verify.sh`` keeps the lock even when ``verify.sh`` died first.

The Cube Escape checkout: ``--ce`` or ``$CUBEGEN_CE_ROOT``, else ``~/Claude/Cube Escape``. Without it (or without
its verify script) the check says so and exits 0 - ``--require`` makes that an error (release check).
Report: ``output/unity_check/report.json``. Exit code 1 when a probe fails.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional

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
    "shape_voxel": {"seed": "31", "test": "cli", "about": "Form voxel (--shape): Teile, Collider und Import wie glatt",
                    "args": ["--types", "crate,console,generator,tank,locker,cargo_container", "--count", "1",
                             "--shape", "voxel"]},
    "shape_facet": {"seed": "32", "test": "cli", "about": "Form facet (--shape): grobe Hüllen runder Teile",
                    "args": ["--types", "canister,generator,tank,turbine,fan,pipe_bend", "--count", "1",
                             "--shape", "facet"]},
    "shape_round": {"seed": "34", "test": "cli", "about": "Form facet an runden Teilen: Oberseite wie glatt (0.30.2)",
                    "args": ["--types", "tank,fan,turbine,vent,pressure_tank", "--count", "1", "--shape", "facet"]},
    "shape_round_voxel": {"seed": "31", "test": "cli", "about": "Form voxel an runden Teilen: Oberseite wie glatt (0.30.2)",
                          "args": ["--types", "tank,fan,turbine,vent,pressure_tank", "--count", "3", "--shape", "voxel"]},
    "shape_holes": {"seed": "33", "test": "cli", "about": "Form holes (--shape): Löcher in flachen Platten",
                    "args": ["--types", "cage,cargo_container,battery_bank,locker,generator", "--count", "1",
                             "--shape", "holes"]},
    "zones": {"seed": "41", "test": "cli", "contract": 4,
              "about": "Vertrag 4: Zonenkarte (textures.zones) und Effektblock (effects)",
              "args": ["--types", "breakable_platform,airlock_chamber,antenna,hologram,crate,floodlight", "--count",
                       "1", "--paint", "dark", "--texture-size", "128"]},
    "runtime": {"seed": "42", "test": "runtime", "about": "alle Typen als GLB (Laufzeitpfad der Werkbank)",
                "args": ["--count", "1", "--formats", "glb"]},
    "neutral": {"seed": "23", "test": "cli", "contract": 3,
                "about": "Anstrich neutral: neutrale Karten, Thema und neue Materialnamen (Vertrag 3), Dark leuchtet",
                "args": ["--types", "crate,floor_tile,pillar,wall,test_wall_modules,vending_machine,hologram,"
                                    "floodlight", "--count", "1",
                         "--param", "test_wall_modules.crystals=some", "--paint", "dark", "--texture-size", "128"]},
}
QUICK = ("kit", "paint", "neutral")
REFERENCE = "paint_reference"  # <probe>/paint_reference: every scheme composed from the probe's neutral maps

# "Passed | bestanden 1 | fehlgeschlagen 0 | …" or "Failed(Child) | bestanden 0 | fehlgeschlagen 1 | …"
RESULT = re.compile(r"(Passed|Failed)(?:\([^)]*\))?\s*\|\s*bestanden\s+(\d+)\s*\|\s*fehlgeschlagen\s+(\d+)")
LOG = re.compile(r"Log:\s*(\S.*?\.log)")
INTEGRATION = re.compile(r"cubegen CLI integration: (\d+) Gameplay / (\d+) statisch / (\d+) Item-Zuordnungen offen / "
                         r"(\d+) ungültige Exporte abgelehnt / (\d+) Fehler\.")


#: Cube Escape's queue for heavy runs - the contract is this path plus an exclusive flock (see the module docstring)
HEAVY_LOCK = os.path.join(os.path.expanduser("~"), "Library", "Caches", "CubeEscape", "heavy-run.lock")
HEAVY_POLL = 2.0
HEAVY_REPORT = 300.0  # a waiting run says every five minutes that it still waits
HEAVY_GROUP_POLL = 0.1  # how often run_in_group looks whether a finished step's process group is empty
HEAVY_STRAGGLER = 5.0  # after this long it says which process group still keeps the lock


def heavy_lock_path() -> str:
    return os.environ.get("CE_HEAVY_LOCK_FILE") or HEAVY_LOCK


def describe_holder(text: str) -> str:
    """The holder line of the lock file in words (whatever tool wrote it)."""
    try:
        info = json.loads(text)
        return (f"{info.get('what', '?')} (PID {info.get('pid', '?')}, {info.get('checkout', '?')}, "
                f"seit {info.get('since', '?')})")
    except (ValueError, AttributeError):
        return text.strip() or "unbekannt"


class HeavyLock:
    """Waits for and holds Cube Escape's lock for heavy runs; ``acquire`` may be called often (the first call waits),
    ``release`` frees it. Skipped with ``CE_HEAVY_LOCK=0``, inside a holder (``CE_HEAVY_HELD=1``) and without flock."""

    def __init__(self, what: str, checkout: str = ROOT, out: Callable[[str], None] = None,
                 poll: float = HEAVY_POLL, report: float = HEAVY_REPORT):
        self.what, self.checkout, self.poll, self.report = what, checkout, poll, report
        self.out = out or (lambda line: print(line, flush=True))
        self.fd: Optional[int] = None
        self.skipped: Optional[str] = None
        self.waited = 0.0
        self._previous_held: Optional[str] = None

    def acquire(self) -> None:
        if self.fd is not None or self.skipped:
            return
        if os.environ.get("CE_HEAVY_LOCK", "1").strip() == "0":
            self.skipped = "CE_HEAVY_LOCK=0"
        elif os.environ.get("CE_HEAVY_HELD") == "1":
            self.skipped = "der Elternprozess hält die Sperre (CE_HEAVY_HELD=1)"
        try:
            import fcntl
        except ImportError:  # pragma: no cover - Windows: no Unity check there anyway
            self.skipped = self.skipped or "kein flock auf diesem System"
        if self.skipped:
            return
        path = heavy_lock_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)  # never inherited (PEP 446 + O_CLOEXEC)
        start = last = time.monotonic()
        announced = False
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    holder = describe_holder(os.pread(fd, 4096, 0).decode("utf-8", "replace"))
                    now = time.monotonic()
                    if not announced:
                        self.out(f"Warte auf die Sperre für schwere Läufe ({path}): belegt von {holder} - "
                                 "CE_HEAVY_LOCK=0 überspringt")
                        announced = True
                    elif now - last >= self.report:
                        self.out(f"... wartet seit {(now - start) / 60:.0f} min auf {holder}")
                        last = now
                    time.sleep(self.poll)
        except BaseException:
            os.close(fd)
            raise
        self.waited = time.monotonic() - start
        if announced:
            self.out(f"Sperre für schwere Läufe frei nach {self.waited:.0f} s")
        info = {"pid": os.getpid(), "what": self.what, "checkout": self.checkout,
                "since": time.strftime("%Y-%m-%d %H:%M:%S")}
        os.ftruncate(fd, 0)
        os.pwrite(fd, (json.dumps(info) + "\n").encode(), 0)
        self.fd = fd
        self._previous_held = os.environ.get("CE_HEAVY_HELD")
        os.environ["CE_HEAVY_HELD"] = "1"  # verify.sh / testplan.py below us must not wait for their own parent

    def release(self) -> None:
        if self.fd is None:
            return
        if self._previous_held is None:
            os.environ.pop("CE_HEAVY_HELD", None)
        else:
            os.environ["CE_HEAVY_HELD"] = self._previous_held
        try:
            os.ftruncate(self.fd, 0)  # still holding it: nobody reads an old holder afterwards
        finally:
            os.close(self.fd)  # releases the lock
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()


def group_alive(pgid: int) -> bool:
    """True while any process of the group still exists (EPERM: one runs that this user may not signal)."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_in_group(argv: List[str], capture_output: bool = False, **popen) -> subprocess.CompletedProcess:
    """``subprocess.run`` for a heavy step (0.27.0): the command runs in a process group of its own, TERM/HUP/INT for
    this process go on to the whole group, and it returns only when the group is empty - the heavy-run lock is never
    free while Unity still runs, also not when ``verify.sh`` above it died first. After a forwarded signal this process
    ends too (exit 128 + signal; ``HeavyLock`` frees the lock on the way out)."""
    if capture_output:
        popen.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child = subprocess.Popen(argv, start_new_session=True, **popen)  # its pid is the group id
    received: List[int] = []

    def forward(signum, _frame):
        received.append(signum)
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(child.pid, signum)

    previous = {}
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        try:
            previous[sig] = signal.signal(sig, forward)
        except ValueError:  # not the main thread
            pass
    try:
        out, err = child.communicate()
        start, told = time.monotonic(), False
        while group_alive(child.pid):
            if not told and time.monotonic() - start >= HEAVY_STRAGGLER:
                print(f"  Schritt beendet (Exit {child.returncode}), die Sperre bleibt bis zum Ende seiner übrigen "
                      f"Prozesse (Prozessgruppe {child.pid})", flush=True)
                told = True
            time.sleep(HEAVY_GROUP_POLL)
    finally:
        for sig, handler in previous.items():
            if handler is not None:
                signal.signal(sig, handler)
    if received:
        raise SystemExit(128 + received[0])
    return subprocess.CompletedProcess(argv, child.returncode, out, err)


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


#: the contract file Cube Escape keeps (python -m cubegen contract --out ...): its version decides what the sidecars may
#: name (0.22.0: version 2 adds the Emission map of a paint scheme)
CE_CONTRACT = os.path.join("Assets", "Resources", "Cubegen", "cubegen_contract.json")


def ce_contract_version(ce: str) -> Optional[int]:
    """The contract version Cube Escape's import reads (None: no contract file there)."""
    try:
        with open(os.path.join(ce, CE_CONTRACT), "r", encoding="utf-8") as fh:
            version = json.load(fh).get("version")
    except (OSError, ValueError, AttributeError):
        return None
    return version if isinstance(version, int) and not isinstance(version, bool) else None


def generate_command(name: str, out: str, contract: Optional[int] = None) -> List[str]:
    """``contract``: the importer's version - the sidecars are written for exactly that one (never newer than
    cubegen knows: an unknown version fails the generate step with a clear message)."""
    probe = PROBES[name]
    return [sys.executable, "-m", "cubegen", "generate", "--seed", probe["seed"], *probe["args"], "--no-render",
            "--no-blend", *(["--contract", str(contract)] if contract is not None else []), "--out", out]


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


def _unity(name: str, ce: str, models: str, reference: Optional[str]) -> subprocess.CompletedProcess:
    test_filter, variable = TESTS[PROBES[name]["test"]]
    env = dict(os.environ, **{variable: models})
    if reference:
        env["CUBEGEN_PAINT_REFERENCE"] = reference
    return run_in_group([os.path.join(ce, VERIFY), "test", "EditMode", test_filter, RUN_NAME], cwd=ce, env=env,
                        capture_output=True, text=True)


def _generate(name: str, out: str, contract: Optional[int]) -> subprocess.CompletedProcess:
    shutil.rmtree(out, ignore_errors=True)
    env = dict(os.environ, PYTHONPATH=ROOT + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH")
                                              else ""))
    return subprocess.run(generate_command(name, out, contract), cwd=ROOT, env=env, capture_output=True, text=True)


def paint_reference(out: str) -> Optional[str]:
    """Reference maps of a probe with --paint (every scheme, ``tools/paint_reference.py``); None without paint."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import paint_reference as ref

    try:
        manifest = ref.load_manifest(out)
    except (OSError, ValueError):
        return None
    if not ref.models_with_maps(manifest):
        return None
    target = os.path.join(out, REFERENCE)
    try:
        ref.write_reference(out, target, log=lambda _: None)
    except ImportError:  # numpy: in Blender's Python, not in the Mac's system Python - use one that has it (0.25.0)
        import run_tests

        python, version = run_tests.numpy_python()
        if version is None:
            print("  Referenzbilder übersprungen: kein Python mit numpy (auch nicht in Blender)", flush=True)
            return None
        done = subprocess.run([python, os.path.join(ROOT, "tools", "paint_reference.py"), out, "--out", target],
                              cwd=ROOT, capture_output=True, text=True)
        if done.returncode != 0:
            print(f"  Referenzbilder fehlgeschlagen ({python}): {(done.stdout + done.stderr)[-500:]}", flush=True)
            return None
    return target


def expected_rejection(stdout: str, models: List[str]) -> bool:
    """A verify run that failed because the import rejected every model: each one named in the failure (verify output
    or its Unity log - the test lists "<model>: <warnings>" per rejected model)."""
    result = parse_verify(stdout)
    text = stdout
    if result["log"] and os.path.isfile(result["log"]):
        with open(result["log"], "r", encoding="utf-8", errors="replace") as fh:
            text += fh.read()
    return not result["passed"] and bool(models) and all(f"{m}:" in text for m in models)


def legs(name: str, contract: Optional[int]) -> List[Dict]:
    """The runs of a probe: [{contract, expect}] - expect "import" or "reject". A probe needing a newer contract than
    Cube Escape reads runs once for that version (rejected) and once for Cube Escape's (imported)."""
    need = PROBES[name].get("contract")
    if need is None or contract is None or contract >= need:  # None: no contract file - cubegen's own version
        return [{"contract": need if need is not None else contract, "expect": "import"}]
    return [{"contract": need, "expect": "reject"}, {"contract": contract, "expect": "import"}]


def run_probe(name: str, ce: str, work: str, log=print, contract: Optional[int] = None,
              lock: Optional[HeavyLock] = None) -> Dict:
    probe = PROBES[name]
    entry = {"name": name, "about": probe["about"], "test": probe["test"], "seconds": {}}
    runs = legs(name, contract)
    for leg in runs:
        tag = "" if len(runs) == 1 else f"_v{leg['contract'] if leg['contract'] is not None else 'ce'}"
        out = os.path.join(work, name + tag)
        start = time.time()
        gen = _generate(name, out, leg["contract"])
        entry["seconds"]["generate" + tag] = round(time.time() - start, 1)
        if gen.returncode != 0:
            entry.update(ok=False, problem="cubegen generate fehlgeschlagen", output=(gen.stdout + gen.stderr)[-2000:])
            return entry
        models = os.path.join(out, "models")
        names = sorted(f[: -len(".cubegen.json")] for f in os.listdir(models) if f.endswith(".cubegen.json"))
        reference = paint_reference(out)
        if lock is not None:
            lock.acquire()  # the first Unity start of the check waits for the machine-wide queue
        start = time.time()
        unity = _unity(name, ce, models, reference)
        entry["seconds"]["unity" + tag] = round(time.time() - start, 1)
        text = unity.stdout + unity.stderr
        if leg["expect"] == "reject":
            ok = expected_rejection(text, names)
            entry["rejected_as_expected"] = {"contract": leg["contract"], "models": len(names), "ok": ok}
            if not ok:
                entry.update(ok=False, problem=f"Vertrag {leg['contract']}: Import hat nicht jedes Modell abgelehnt",
                             output=text[-3000:])
                return entry
            continue
        entry["exports"] = len(names)
        if reference:
            entry["reference"] = reference
        result = parse_verify(text)
        entry.update(result)
        if result["log"] and os.path.isfile(result["log"]):
            with open(result["log"], "r", encoding="utf-8", errors="replace") as fh:
                log_text = fh.read()
            entry["integration"] = parse_integration(log_text)
        if probe["test"] == "runtime":
            entry["runtime"] = runtime_audit(models)
        entry["ok"] = result["passed"] and unity.returncode == 0
        if not entry["ok"]:
            entry["output"] = text[-3000:]
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
    rejected = entry.get("rejected_as_expected")
    if rejected:
        detail += f"; mit Vertrag {rejected['contract']} {rejected['models']} abgelehnt wie erwartet"
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
    contract = ce_contract_version(ce)
    report = {"cubegen": _version(), "ce": ce, "ce_commit": _git_head(ce), "contract": contract, "probes": []}
    print(f"Vertrag von Cube Escape: Version {contract if contract is not None else '? (Standard von cubegen)'}")
    with HeavyLock(f"Cubegen tools/unity_check.py ({', '.join(names)})") as lock:
        for name in names:
            print(f"> {name}: {PROBES[name]['about']} …", flush=True)
            entry = run_probe(name, ce, args.out, contract=contract, lock=lock)
            report["probes"].append(entry)
            print("  " + summary_line(entry), flush=True)
            if entry["ok"] and not args.keep:
                for folder in os.listdir(args.out):
                    if folder == name or folder.startswith(name + "_v"):
                        shutil.rmtree(os.path.join(args.out, folder), ignore_errors=True)
    report["heavy_lock"] = {"skipped": lock.skipped} if lock.skipped else {"waited_s": round(lock.waited, 1)}
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
