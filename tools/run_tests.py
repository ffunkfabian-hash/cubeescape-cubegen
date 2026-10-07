"""Run the tests in groups of similar length - in parallel locally, one group per job in CI.

    python3 tools/run_tests.py              ->  all groups at once (one process each), summary at the end
    python3 tools/run_tests.py models       ->  only this group (CI: one job per group)
    python3 tools/run_tests.py --list       ->  which test module runs in which group

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
# about 2 minutes each (all 164 types in many states); everything else goes to "rest"
GROUPS = {
    "models": ["test_core"],
    "quality": ["test_quality", "test_golden"],
}
REST = "rest"


def modules():
    return sorted(name[:-3] for name in os.listdir(TESTS) if name.startswith("test_") and name.endswith(".py"))


def groups():
    named = {m for members in GROUPS.values() for m in members}
    out = {name: [m for m in members if m in modules()] for name, members in GROUPS.items()}
    out[REST] = [m for m in modules() if m not in named]
    return out


def command(members):
    return [sys.executable, "-m", "unittest"] + [f"tests.{m}" for m in members]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="run the tests in groups (default: all groups in parallel)")
    parser.add_argument("group", nargs="?", choices=list(GROUPS) + [REST], help="only this group")
    parser.add_argument("--list", action="store_true", help="show the groups and their test modules")
    args = parser.parse_args(argv)
    plan = groups()
    if args.list:
        for name, members in plan.items():
            print(f"{name:<8} {' '.join(members)}")
        return 0
    if args.group:
        return subprocess.call(command(plan[args.group]), cwd=ROOT)
    start = time.time()
    procs = {name: subprocess.Popen(command(members), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True)
             for name, members in plan.items()}
    failed = []
    for name, proc in procs.items():
        output = proc.communicate()[0]
        summary = [line for line in output.splitlines() if line.startswith(("Ran ", "OK", "FAILED"))]
        print(f"[{name}] {' | '.join(summary)}")
        if proc.returncode:
            failed.append(name)
            print(output)
    print(f"{'FAILED: ' + ', '.join(failed) if failed else 'all groups OK'} ({time.time() - start:.0f} s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
