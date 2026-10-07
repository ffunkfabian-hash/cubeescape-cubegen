"""Keep release metadata consistent across the CLI, package and standalone Blender bundle."""

import ast
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cubegen import __version__
from tools.build_addon import build


ROOT = Path(__file__).resolve().parents[1]


def addon_version(source):
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "bl_info"
                                               for target in node.targets):
            return ".".join(str(number) for number in ast.literal_eval(node.value)["version"])
    raise AssertionError("Blender add-on release metadata is missing")


class VersionTests(unittest.TestCase):
    def test_package_cli_and_blender_metadata_agree(self):
        metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        version = re.search(r'^version\s*=\s*"([^"]+)"', metadata, re.MULTILINE).group(1)
        self.assertEqual(version, __version__)
        self.assertEqual(addon_version((ROOT / "blender_addon/cubegen_addon/__init__.py").read_text(encoding="utf-8")), version)
        result = subprocess.run([sys.executable, "-m", "cubegen", "--version"], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "cubegen " + version)

    def test_standalone_addon_bundle_contains_the_same_release(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = build(os.path.join(directory, "cubegen_addon.zip"))
            with zipfile.ZipFile(archive) as bundle:
                info = bundle.read("cubegen_addon/__init__.py").decode("utf-8")
                package = bundle.read("cubegen_addon/cubegen/__init__.py").decode("utf-8")
                namespace = {}
                exec(compile(package, "bundled __init__.py", "exec"), namespace)
                self.assertEqual(addon_version(info), __version__)
                self.assertEqual(namespace["__version__"], __version__)


if __name__ == "__main__":
    unittest.main()
