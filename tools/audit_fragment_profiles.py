"""Compare targeted fragment decomposition steps without rendering or exports."""

import argparse
import json
import time
from unittest.mock import patch
from contextlib import ExitStack

from cubegen.models import generate_asset, model_types
from cubegen.params import Style
from cubegen.seeds import model_seed


def audit(master_seed=42, baseline="original"):
    started = time.monotonic()
    rows = []
    changed = 0
    style = Style(generation=3, damage="fractured")
    for kind in model_types():
        seed = model_seed(master_seed, kind, 0)
        with ExitStack() as stack:
            stack.enter_context(patch("cubegen.models.fracture._radial_parts", return_value=None))
            if baseline != "box":
                stack.enter_context(patch("cubegen.models.fracture._box_topology", return_value=False))
            if baseline == "original":
                stack.enter_context(patch("cubegen.models.fracture._convex_components", side_effect=lambda p: [p]))
            elif baseline == "structural":
                stack.enter_context(patch("cubegen.models.fracture._convex_recipe_parts", return_value=None))
            elif baseline not in ("lathe", "box"):
                stack.enter_context(patch("cubegen.geometry._lathe_convex_faces", return_value=None))
                if baseline == "round":
                    stack.enter_context(patch("cubegen.geometry._convex_polygon_parts", return_value=None))
            before = generate_asset(kind, seed, style=style)
        after = generate_asset(kind, seed, style=style)
        old_bad = sum(not c.convex for c in before.colliders)
        new_bad = sum(not c.convex for c in after.colliders)
        different = before.digest() != after.digest()
        changed += different
        if old_bad or new_bad or different:
            rows.append({"type": kind, "seed": seed, "changed": different, "bodies_before": before.meta["fragments"],
                         "bodies_after": after.meta["fragments"], "shapes_before": len(before.colliders),
                         "shapes_after": len(after.colliders), "nonconvex_before": old_bad,
                         "nonconvex_after": new_bad, "triangles_before": before.stats()["triangles"],
                         "triangles_after": after.stats()["triangles"]})
    return {"baseline": baseline, "master_seed": master_seed, "generation": 3, "index": 0,
            "sources": len(model_types()), "changed_sources": changed, "unchanged_sources": len(model_types()) - changed,
            "blocked_before": sum(r["nonconvex_before"] > 0 for r in rows),
            "blocked_after": sum(r["nonconvex_after"] > 0 for r in rows),
            "seconds": round(time.monotonic() - started, 3), "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", choices=("original", "structural", "round", "extrusion", "lathe", "box"), default="original")
    args = parser.parse_args()
    print(json.dumps(audit(baseline=args.baseline), indent=2))
