"""Run the tests in groups of similar length - in parallel, locally and in CI (one job per Python version).

    python3 tools/run_tests.py                  ->  full tier: all groups at once (one process each), summary at the end
    python3 tools/run_tests.py --tier quick     ->  everyday check after a change, without Blender and the sweeps
    python3 tools/run_tests.py --tier standard  ->  every module, without Blender
    python3 tools/run_tests.py models           ->  only this group
    python3 tools/run_tests.py --list           ->  which test module runs in which group and tier, with which Python

Tiers (like the robot generator's): ``quick`` leaves out Blender and the modules that sweep every type
(``SWEEPS``), ``standard`` runs every module without Blender, ``full`` (default) is the whole suite - before a
release and for the Stage 2 acceptance, with Blender and ImageMagick installed. Without Blender is
``$CUBEGEN_SKIP_BLENDER=1``: ``find_blender`` reports none, the Blender tests skip themselves.

**numpy** (0.25.0): the modules that import numpy run in their own group ``numpy`` with the first interpreter that
has it - ``$CUBEGEN_NUMPY_PYTHON``, this Python, other ``python3.x`` on the PATH, then the Python inside Blender
(``Blender.app/Contents/Resources/<version>/python/bin/python3.x``, which ships numpy). The system Python of a Mac
has no numpy; before 0.25 those 13 tests were skipped there. Every run says which interpreters it used, and the
summary lists each remaining skip with its reason (``CUBEGEN_UNITY_CHECK=1`` and ``CUBEGEN_SLOW_TESTS=1`` stay
opt-in: a real Unity run and the 2048 px bake).

The groups share one fresh, temporary shared cache (``CUBEGEN_CACHE``, removed afterwards) - tests never read or
fill the machine's cache, and a warm cache can't hide a step that no longer works. A ``CUBEGEN_CACHE`` set by the
caller is kept.

A test module that no group names runs in "rest", so a new module is never skipped.
Same result as ``python3 -m unittest discover -s tests``, just faster.
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
# measured 0.15.0 (Apple M5, one process each): test_core 57 s, test_quality 65 s + test_golden 7 s,
# test_params 30 s + test_families 10 s + test_textures_damage 11 s, Blender tests about 60 s; everything else -> rest.
# 0.25.0: rest had grown to 111 s (the whole run waited for it), test_pipeline alone 38 s -> its own group
GROUPS = {
    "models": ["test_core"],
    "quality": ["test_quality", "test_golden"],
    "params": ["test_params", "test_families", "test_textures_damage"],
    "pipeline": ["test_pipeline"],
}
NUMPY = "numpy"  # the modules importing numpy (found in their source), run by an interpreter that has it
REST = "rest"
SWEEPS = ("test_core", "test_quality", "test_params")  # every type in many states: not in the quick tier
TIERS = ("quick", "standard", "full")
USES_NUMPY = re.compile(r"^\s*(import numpy|from numpy\b)", re.MULTILINE)
SKIPPED = re.compile(r"\.\.\. skipped '(.*)'$", re.MULTILINE)
RAN = re.compile(r"^Ran (\d+) tests? in", re.MULTILINE)


def modules():
    return sorted(name[:-3] for name in os.listdir(TESTS) if name.startswith("test_") and name.endswith(".py"))


def numpy_modules():
    found = []
    for name in modules():
        with open(os.path.join(TESTS, name + ".py"), "r", encoding="utf-8") as fh:
            if USES_NUMPY.search(fh.read()):
                found.append(name)
    return found


def groups(tier="full"):
    named = {m for members in GROUPS.values() for m in members}
    out = {name: [m for m in members if m in modules()] for name, members in GROUPS.items()}
    out[NUMPY] = [m for m in numpy_modules() if m not in named]
    out[REST] = [m for m in modules() if m not in named and m not in out[NUMPY]]
    if tier == "quick":
        out = {name: [m for m in members if m not in SWEEPS] for name, members in out.items()}
    return {name: members for name, members in out.items() if members}


def numpy_version(python):
    """numpy's version in ``python``, None without it."""
    try:
        out = subprocess.run([python, "-c", "import numpy; print(numpy.__version__)"], capture_output=True, text=True,
                             timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def blender_pythons():
    """The Python interpreters inside an installed Blender ($CUBEGEN_BLENDER / $BLENDER / PATH / /Applications)."""
    found = []
    candidates = [os.environ.get(k) for k in ("CUBEGEN_BLENDER", "BLENDER", "BLENDER_PATH")]
    candidates += [shutil.which("blender"), "/Applications/Blender.app/Contents/MacOS/Blender"]
    for blender in candidates:
        if not blender or not os.path.isfile(blender):
            continue
        home = os.path.dirname(os.path.realpath(blender))
        for pattern in (os.path.join(home, "..", "Resources", "*", "python", "bin", "python3*"),  # macOS app
                        os.path.join(home, "*", "python", "bin", "python3*"),  # Linux / Windows archive
                        os.path.join(home, "*", "python", "bin", "python.exe")):
            for path in sorted(glob.glob(pattern), reverse=True):  # newest Blender version first
                path = os.path.normpath(path)
                if os.access(path, os.X_OK) and not path.endswith("-config") and path not in found:
                    found.append(path)
    return found


def numpy_python():
    """(interpreter, numpy version) for the numpy group - (this Python, None) when no interpreter has numpy: then
    its tests skip with their reason, as before."""
    candidates = [os.environ.get("CUBEGEN_NUMPY_PYTHON"), sys.executable]
    candidates += [shutil.which(f"python3.{minor}") for minor in range(14, 8, -1)] + [shutil.which("python3")]
    candidates += blender_pythons()
    seen = set()
    for python in candidates:
        if not python or python in seen:
            continue
        seen.add(python)
        version = numpy_version(python)
        if version:
            return python, version
    return sys.executable, None


def environment(tier):
    env = dict(os.environ)
    env.pop("CUBEGEN_SKIP_BLENDER", None)  # full means full, even if a quick run left it exported in the shell
    if tier != "full":
        env["CUBEGEN_SKIP_BLENDER"] = "1"
    return env


def command(members, python=None):
    return [python or sys.executable, "-m", "unittest", "-v"] + [f"tests.{m}" for m in members]


def interpreter(python):
    try:
        version = subprocess.run([python, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True,
                                 text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        version = "?"
    return f"Python {version or '?'} ({python})"


def summary(output):
    """``Ran …`` and the result line of a unittest run, and its skip reasons."""
    lines = [line for line in output.splitlines() if line.startswith(("Ran ", "OK", "FAILED"))]
    return " | ".join(lines), SKIPPED.findall(output)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="run the tests in groups (default: all groups in parallel)")
    parser.add_argument("group", nargs="?", choices=list(GROUPS) + [NUMPY, REST], help="only this group")
    parser.add_argument("--tier", choices=TIERS, default="full",
                        help="quick: no Blender, no sweeps; standard: no Blender; full (default): everything")
    parser.add_argument("--list", action="store_true", help="show the groups and their test modules")
    args = parser.parse_args(argv)
    plan = groups(args.tier)
    env = environment(args.tier)
    np_python, np_version = numpy_python() if NUMPY in plan else (sys.executable, None)
    python = {name: (np_python if name == NUMPY else sys.executable) for name in plan}
    pythons = (f"Python: {interpreter(sys.executable)}; group {NUMPY}: {interpreter(np_python)}, "
               f"numpy {np_version or 'missing - its tests skip'}")
    if args.list:
        for name, members in plan.items():
            print(f"{name:<8} {' '.join(members)}")
        print(f"tier {args.tier}: {'without' if args.tier != 'full' else 'with'} Blender")
        print(pythons)
        return 0
    temporary = None
    if not env.get("CUBEGEN_CACHE"):  # one fresh shared cache for this run (see the docstring)
        temporary = tempfile.mkdtemp(prefix="cubegen_test_cache_")
        env["CUBEGEN_CACHE"] = temporary
    try:
        if args.group:
            members = plan.get(args.group)
            if not members:
                return 0
            print(f"[{args.group}] {interpreter(python[args.group])}", flush=True)
            return subprocess.call(command(members, python[args.group]), cwd=ROOT, env=env)
        start = time.time()
        print(pythons, flush=True)
        procs = {name: subprocess.Popen(command(members, python[name]), cwd=ROOT, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, env=env)
                 for name, members in plan.items()}
        failed, skips, total = [], {}, 0
        for name, proc in procs.items():
            output = proc.communicate()[0]
            line, skipped = summary(output)
            ran = RAN.search(output)
            total += int(ran.group(1)) if ran else 0
            for reason in skipped:
                skips[reason] = skips.get(reason, 0) + 1
            print(f"[{name}] {line}")
            if proc.returncode:
                failed.append(name)
                print(output)
        print(f"skipped: {sum(skips.values())}" + "".join(f"\n  {n} x {r}" for r, n in sorted(skips.items())))
        print(f"tier {args.tier}: {'FAILED: ' + ', '.join(failed) if failed else 'all groups OK'}, {total} tests "
              f"({time.time() - start:.0f} s)")
        return 1 if failed else 0
    finally:
        if temporary:
            shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
