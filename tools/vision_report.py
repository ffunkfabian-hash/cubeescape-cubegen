#!/usr/bin/env python3
"""Neural Engine report on a finished run (macOS only): near-duplicate variants and hard-to-read icons.

    python3 tools/vision_report.py <output dir> [--threshold 0.2] [--json report.json]

Apple Vision (``tools/vision_check.swift``, compiled once into ``output/tools``) compares the previews of each type
with feature prints and looks at every icon with the attention-based saliency model:

- **Doubletten:** pairs of variants of one type whose previews are closer than ``--threshold`` - a list to tune the
  deterministic signature (``cubegen.variety``), never a decision about the variants a run writes (the distances
  differ between Neural Engine, GPU and CPU).
- **Icons:** the model is cut off (pixels on the icon's edge differ from its background - the saliency boxes are
  too coarse for that), the salient area is small (the model gets lost) or sits far off centre.

Only a hint: exit code 0 also with findings; on other systems it says so and exits 0. Time rule (ROADMAP): at most
one minute for the whole catalog.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWIFT = os.path.join(ROOT, "tools", "vision_check.swift")
BORDER_PIXELS = 3  # this many pixels of the model on the icon's edge: cut off
SMALL = 0.08       # salient box smaller than this share of the icon: the model gets lost
OFF_CENTRE = 0.22  # centre of the salient box further than this from the icon centre


def available() -> str:
    """'' when the report can run here, else why not."""
    if sys.platform != "darwin":
        return "only on macOS (Apple Vision)"
    if not shutil.which("swiftc") and not shutil.which("xcrun"):
        return "swiftc not found (Xcode or the command line tools)"
    return ""


def checker(build_dir: str) -> str:
    """The compiled checker - rebuilt when the Swift source changed."""
    with open(SWIFT, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()[:12]
    exe = os.path.join(build_dir, f"vision_check_{digest}")
    if not os.path.isfile(exe):
        os.makedirs(build_dir, exist_ok=True)
        swiftc = shutil.which("swiftc") or "swiftc"
        cmd = [swiftc, "-O", SWIFT, "-o", exe] if shutil.which("swiftc") else ["xcrun", "swiftc", "-O", SWIFT, "-o", exe]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    return exe


def icon_findings(icon) -> list:
    x, y, w, h = icon["box"]
    found = []
    if icon.get("border", 0) >= BORDER_PIXELS:
        found.append(f"angeschnitten ({icon['border']} Randpixel)")
    if icon["objects"] == 0 or w * h == 0:
        return found + ["kein Blickpunkt gefunden"]
    if w * h < SMALL:
        found.append(f"klein ({w * h:.0%} der Fläche)")
    cx, cy = x + w / 2, y + h / 2
    if ((cx - 0.5) ** 2 + (cy - 0.5) ** 2) ** 0.5 > OFF_CENTRE:
        found.append("nicht mittig")
    return found


def report(out_dir: str, threshold: float = 0.2, build_dir: str = "") -> dict:
    with open(os.path.join(out_dir, "manifest.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    def entries(key):
        rows = []
        for m in manifest["models"]:
            path = m.get(key)
            if path and os.path.isfile(os.path.join(out_dir, path)):
                rows.append({"name": m["name"], "type": m["type"], "path": os.path.join(out_dir, path)})
        return rows

    data = {"previews": entries("preview"), "icons": entries("icon")}
    exe = checker(build_dir or os.path.join(ROOT, "output", "tools"))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(data, fh)
        listing = fh.name
    try:
        start = time.time()
        result = subprocess.run([exe, listing], check=True, capture_output=True, text=True)
        seconds = time.time() - start
    finally:
        os.unlink(listing)
    raw = json.loads(result.stdout)
    doubles = sorted((p for p in raw["pairs"] if p["distance"] < threshold), key=lambda p: p["distance"])
    icons = []
    for icon in raw["icons"]:
        found = icon_findings(icon)
        if found:
            icons.append({"name": icon["name"], "type": icon["type"], "findings": found,
                          "box": [round(v, 3) for v in icon["box"]]})
    return {"previews": len(data["previews"]), "icons_checked": len(data["icons"]), "threshold": threshold,
            "doubles": doubles, "icons": icons, "seconds": round(seconds, 2), "vision_seconds": raw["seconds"],
            "closest": sorted(raw["pairs"], key=lambda p: p["distance"])[:5]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="output folder of a cubegen run (manifest.json, previews, icons)")
    ap.add_argument("--threshold", type=float, default=0.2, help="feature print distance below which two variants "
                                                                 "count as near-duplicates (default 0.2)")
    ap.add_argument("--json", help="also write the report as JSON")
    args = ap.parse_args(argv)
    why = available()
    if why:
        print(f"vision report skipped: {why}")
        return 0
    rep = report(args.out, args.threshold)
    print(f"Neural Engine: {rep['previews']} previews, {rep['icons_checked']} icons in {rep['seconds']:.1f} s")
    print(f"near-duplicates (distance < {rep['threshold']}): {len(rep['doubles'])}")
    for p in rep["doubles"]:
        print(f"  {p['type']:18s} {p['a']} / {p['b']}  {p['distance']:.3f}")
    print(f"icons with findings: {len(rep['icons'])}")
    for icon in rep["icons"]:
        print(f"  {icon['name']:28s} {', '.join(icon['findings'])}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
