"""Reference fingerprints ("golden digests") of every model type.

``tests/golden.json`` stores the :meth:`Asset.digest` of each type for a few
seeds and styles. ``test_golden.py`` rebuilds them and fails as soon as one
model changes - e.g. because a builder rolls one value more in the middle,
which shifts everything rolled after it.

Changed a model on purpose? Regenerate and commit the file (and note it in the
CHANGELOG, existing seeds then look different):

    python3 tests/golden_cases.py --update
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cubegen.models import generate_asset, model_types  # noqa: E402
from cubegen.params import Style  # noqa: E402

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden.json")

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
)


def compute():
    result = {}
    for model_type in model_types():
        result[model_type] = {name: generate_asset(model_type, seed, style=Style.from_dict(style)).digest()
                              for name, seed, style in CASES}
    return result


def load():
    with open(GOLDEN, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv):
    if argv != ["--update"]:
        sys.exit("usage: python3 tests/golden_cases.py --update")
    old = load() if os.path.isfile(GOLDEN) else {}
    new = compute()
    changed = sorted(t for t in new if t in old and old[t] != new[t])
    added = sorted(t for t in new if t not in old)
    with open(GOLDEN, "w", encoding="utf-8") as fh:
        json.dump(new, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"{GOLDEN}: {len(new)} types, changed: {', '.join(changed) or '-'}, new: {', '.join(added) or '-'}")


if __name__ == "__main__":
    main(sys.argv[1:])
