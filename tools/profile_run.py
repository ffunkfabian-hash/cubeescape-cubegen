"""Profile a cubegen command with cProfile (the host process; Blender workers report their own times in the manifest).

    python3 tools/profile_run.py -- check --types door,crate
    python3 tools/profile_run.py --top 40 --sort tottime --out run.prof -- generate --seed 42 --no-blender

Prints the most expensive functions; ``--out`` keeps the raw profile (``python3 -m pstats run.prof``).
Like the robot generator's ``scripts/profile_run.py``: measure first, then optimise the place that costs.
"""

import argparse
import cProfile
import io
import os
import pstats
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    rest = []
    if "--" in argv:
        rest = argv[argv.index("--") + 1:]
        argv = argv[:argv.index("--")]
    parser = argparse.ArgumentParser(description="profile a cubegen command (arguments after --)")
    parser.add_argument("--top", type=int, default=25, help="how many functions to show (default 25)")
    parser.add_argument("--sort", choices=["cumulative", "tottime", "ncalls"], default="cumulative")
    parser.add_argument("--out", help="also write the raw profile here")
    args = parser.parse_args(argv)
    if not rest:
        parser.error("pass the cubegen command after --, e.g. -- check --types door")

    from cubegen.cli import main as cubegen_main

    profile = cProfile.Profile()
    code = 0
    profile.enable()
    try:
        code = cubegen_main(rest) or 0
    except SystemExit as exc:  # argparse / --help
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        profile.disable()
    if args.out:
        profile.dump_stats(args.out)
    text = io.StringIO()
    pstats.Stats(profile, stream=text).strip_dirs().sort_stats(args.sort).print_stats(args.top)
    print(text.getvalue())
    return code


if __name__ == "__main__":
    sys.exit(main())
