"""Reference fingerprints ("golden digests") of every model type.

``tests/golden.json`` stores the :meth:`Asset.digest` of each type for a few
seeds and styles. ``test_golden.py`` rebuilds them and fails as soon as one
model changes - e.g. because a builder rolls one value more in the middle,
which shifts everything rolled after it.

``tests/quality_baseline.json`` holds the quality report (``cubegen check``)
of every type: ``test_quality.py`` fails when z-fighting gets worse.

Changed a model on purpose? Regenerate and commit both files (and note it in
the CHANGELOG, existing seeds then look different):

    python3 tests/golden_cases.py --update
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cubegen.models import REGISTRY, generate_asset, model_types  # noqa: E402
from cubegen.params import Style  # noqa: E402
from cubegen.quality import report  # noqa: E402
from cubegen.seeds import model_seed  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden.json")
QUALITY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quality_baseline.json")
QUALITY_SEED, QUALITY_VARIANTS = 42, 10

# (case name, asset seed, style) - built for every model type
CASES = (
    ("seed0", 0, {}),
    ("seed1", 1, {}),
    ("seed691206113", 691206113, {}),  # = model_seed(42, "crate", 0): a real batch seed
    ("styled", 5, {"size": "L", "snap": 0.5, "glow": "red", "material": "dark", "warning": "always"}),
    ("small_low_worn", 6, {"size": "S", "detail": "low", "wear": "heavy", "warning": "none"}),
    ("high_detail", 7, {"detail": "high", "material": "light", "glow": "orange"}),
    ("damaged", 3, {"damage": "damaged", "wear": "light"}),
    ("destroyed", 4, {"damage": "destroyed"}),
    ("themed", 8, {"theme": "labor-3"}),
)


def compute():
    result = {}
    for model_type in model_types():
        result[model_type] = {name: generate_asset(model_type, seed, style=Style.from_dict(style)).digest()
                              for name, seed, style in CASES}
    return result


def load(path=GOLDEN):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def quality():
    """What the baseline keeps per type (seed 42, variants 0-9)."""
    rows = report(model_types(), lambda t, i: generate_asset(t, model_seed(QUALITY_SEED, t, i)), REGISTRY,
                  QUALITY_VARIANTS)
    return {t: {k: r[k] for k in ("triangles", "draw_calls", "z_fighting_pairs", "z_fighting_variants")}
            for t, r in rows.items()}


def main(argv):
    if argv != ["--update"]:
        sys.exit("usage: python3 tests/golden_cases.py --update")
    old = load() if os.path.isfile(GOLDEN) else {}
    new = compute()
    changed = sorted(t for t in new if t in old and any(new[t].get(c) != d for c, d in old[t].items()))
    added = sorted(t for t in new if t not in old)
    with open(GOLDEN, "w", encoding="utf-8") as fh:
        json.dump(new, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"{GOLDEN}: {len(new)} types, changed: {', '.join(changed) or '-'}, new: {', '.join(added) or '-'}")
    with open(QUALITY, "w", encoding="utf-8") as fh:
        json.dump(quality(), fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"{QUALITY}: updated")


if __name__ == "__main__":
    main(sys.argv[1:])
