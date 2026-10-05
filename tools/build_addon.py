"""Build the installable Blender add-on zip.

    python3 tools/build_addon.py            ->  dist/cubegen_blender_addon.zip

The zip contains ``cubegen_addon/`` with a copy of the ``cubegen`` package, so
the add-on works on its own. Install it in Blender via
Preferences > Add-ons > Install... (Blender 4.2+: "Install from Disk...").
"""

import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, "blender_addon", "cubegen_addon")
PACKAGE = os.path.join(ROOT, "cubegen")


def build(out_path: str) -> str:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(ADDON, "__init__.py"), "cubegen_addon/__init__.py")
        for folder, dirs, files in os.walk(PACKAGE):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith(".py"):
                    src = os.path.join(folder, name)
                    rel = os.path.relpath(src, ROOT)
                    zf.write(src, os.path.join("cubegen_addon", rel).replace(os.sep, "/"))
    return out_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist", "cubegen_blender_addon.zip")
    print(build(target))
