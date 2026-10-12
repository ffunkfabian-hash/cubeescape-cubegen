"""Run the tests in groups of similar length - in parallel locally, one group per job in CI.

    python3 tools/run_tests.py                  ->  full tier: all groups at once (one process each), summary at the end
    python3 tools/run_tests.py --tier quick     ->  everyday check after a change, without Blender and the sweeps
    python3 tools/run_tests.py --tier standard  ->  every module, without Blender
    python3 tools/run_tests.py models           ->  only this group (CI: one job per group)
    python3 tools/run_tests.py --list           ->  which test module runs in which group and tier

Tiers (like the robot generator's): ``quick`` leaves out Blender and the modules that sweep every type
(``SWEEPS``), ``standard`` runs every module without Blender, ``full`` (default) is the whole suite - before a
release and for the Stage 2 acceptance, with Blender and ImageMagick installed. Without Blender is
``$CUBEGEN_SKIP_BLENDER=1``: ``find_blender`` reports none, the Blender tests skip themselves.

A test module that no group names runs in "rest", so a new module is never skipped.
Same result as ``python3 -m unittest discover -s tests``, just faster.
"""

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
# measured 0.15.0 (Apple M5, one process each): test_core 57 s, test_quality 65 s + test_golden 7 s,
# test_params 30 s + test_families 10 s + test_textures_damage 11 s, Blender tests about 60 s; everything else -> rest
GROUPS = {
    "models": ["test_core"],
    "quality": ["test_quality", "test_golden"],
    "params": ["test_params", "test_families", "test_textures_damage"],
}
REST = "rest"
SWEEPS = ("test_core", "test_quality", "test_params")  # every type in many states: not in the quick tier
TIERS = ("quick", "standard", "full")


def modules():
    return sorted(name[:-3] for name in os.listdir(TESTS) if name.startswith("test_") and name.endswith(".py"))


def groups(tier="full"):
    named = {m for members in GROUPS.values() for m in members}
    out = {name: [m for m in members if m in modules()] for name, members in GROUPS.items()}
    out[REST] = [m for m in modules() if m not in named]
    if tier == "quick":
        out = {name: [m for m in members if m not in SWEEPS] for name, members in out.items()}
    return {name: members for name, members in out.items() if members}


def environment(tier):
    env = dict(os.environ)
    if tier != "full":
        env["CUBEGEN_SKIP_BLENDER"] = "1"
    return env


def command(members):
    return [sys.executable, "-m", "unittest"] + [f"tests.{m}" for m in members]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="run the tests in groups (default: all groups in parallel)")
    parser.add_argument("group", nargs="?", choices=list(GROUPS) + [REST], help="only this group")
    parser.add_argument("--tier", choices=TIERS, default="full",
                        help="quick: no Blender, no sweeps; standard: no Blender; full (default): everything")
    parser.add_argument("--list", action="store_true", help="show the groups and their test modules")
    args = parser.parse_args(argv)
    plan = groups(args.tier)
    env = environment(args.tier)
    if args.list:
        for name, members in plan.items():
            print(f"{name:<8} {' '.join(members)}")
        print(f"tier {args.tier}: {'without' if args.tier != 'full' else 'with'} Blender")
        return 0
    if args.group:
        members = plan.get(args.group)
        return subprocess.call(command(members), cwd=ROOT, env=env) if members else 0
    start = time.time()
    procs = {name: subprocess.Popen(command(members), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, env=env)
             for name, members in plan.items()}
    failed = []
    for name, proc in procs.items():
        output = proc.communicate()[0]
        summary = [line for line in output.splitlines() if line.startswith(("Ran ", "OK", "FAILED"))]
        print(f"[{name}] {' | '.join(summary)}")
        if proc.returncode:
            failed.append(name)
            print(output)
    print(f"tier {args.tier}: {'FAILED: ' + ', '.join(failed) if failed else 'all groups OK'} "
          f"({time.time() - start:.0f} s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
