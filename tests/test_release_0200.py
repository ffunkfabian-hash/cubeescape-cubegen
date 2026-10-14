"""cubegen 0.20.0 "Gatekeeper": the Unity check (tools/unity_check.py) - fixed probes through Cube Escape's importer."""

import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)

import unity_check  # noqa: E402

PASSED = """Log: /Users/x/Library/Caches/CubeEscape/verify/Cube_Escape-1.out/cubegen_check_20261013_175000.log
Passed | bestanden 1 | fehlgeschlagen 0 | uebersprungen 0 | Dauer 21.0 s
"""
FAILED = """Failed(Child) | bestanden 0 | fehlgeschlagen 1 | uebersprungen 0 | Dauer 0.4768605 s
FAIL CubeEscape.Tests.EditMode.CubegenCliIntegrationTests.RealCliExportsPreserveHierarchyMaterialsAndReimportIdentity
    Expected: greater than 0
Log: /Users/x/Library/Caches/CubeEscape/verify/Cube_Escape-1.out/cubegen_check_20261013_175428.log
"""


class ParseTest(unittest.TestCase):
    def test_verify_output(self):
        # both lines as verify.sh printed them in the real runs of 0.20.0 (the failing one: empty export folder)
        ok = unity_check.parse_verify(PASSED)
        self.assertEqual((ok["passed"], ok["tests"]), (True, 1))
        self.assertTrue(ok["log"].endswith("cubegen_check_20261013_175000.log"))
        bad = unity_check.parse_verify(FAILED)
        self.assertEqual((bad["passed"], bad["tests"]), (False, 1))
        self.assertEqual(unity_check.parse_verify("verify.sh: Kopie belegt")["passed"], False)

    def test_integration_counts_from_the_log(self):
        line = ("cubegen CLI integration: 8 Gameplay / 6 statisch / 2 Item-Zuordnungen offen / 0 ungültige Exporte "
                "abgelehnt / 0 Fehler.")
        self.assertEqual(unity_check.parse_integration("x\n" + line + "\ny"),
                         {"gameplay": 8, "static": 6, "unmapped_items": 2, "rejected": 0, "errors": 0})
        self.assertIsNone(unity_check.parse_integration("nothing"))

    def test_runtime_audit(self):
        import json

        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "runtime-audit.json"), "w", encoding="utf-8") as fh:
                json.dump({"models": [{"file": "a.glb", "result": "accepted"}, {"file": "b.glb", "result": "failed"},
                                      {"file": "c.glb", "result": "unsupported"}]}, fh)
            audit = unity_check.runtime_audit(d)
        self.assertEqual((audit["models"], audit["accepted"], audit["failed"]), (3, 1, 1))
        self.assertEqual(audit["failed_files"], ["b.glb"])


class PlanTest(unittest.TestCase):
    def test_probes_are_fixed_and_cover_both_import_paths(self):
        # 0.24.0: --quick also runs the probe "neutral" (contract version 3, test_release_0240)
        self.assertEqual(unity_check.plan(quick=True), ["kit", "paint", "neutral"])
        self.assertEqual(unity_check.plan(["runtime", "kit"]), ["kit", "runtime"])  # in the fixed order
        self.assertEqual({p["test"] for p in unity_check.PROBES.values()}, {"cli", "runtime"})
        with self.assertRaises(ValueError):
            unity_check.plan(["nope"])
        for name in unity_check.PROBES:
            cmd = unity_check.generate_command(name, "/tmp/x")
            self.assertIn("--seed", cmd)  # same models every time
            self.assertIn("--no-render", cmd)
        self.assertIn("glb", unity_check.generate_command("runtime", "/tmp/x"))

    def test_probe_commands_are_valid_cubegen_command_lines(self):
        from cubegen.cli import build_config, make_parser

        for name in unity_check.PROBES:
            argv = unity_check.generate_command(name, "/tmp/x")[3:]  # after "python -m cubegen"
            config = build_config(make_parser().parse_args(argv))
            self.assertTrue(config.models or config.family, name)

    def test_without_cube_escape_it_says_so(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "unity_check.py"), "--ce", "/nonexistent"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("übersprungen", result.stdout)
        result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "unity_check.py"), "--ce", "/nonexistent",
                                 "--require"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


@unittest.skipUnless(os.environ.get("CUBEGEN_UNITY_CHECK") == "1", "real Unity run: CUBEGEN_UNITY_CHECK=1")
class RealRunTest(unittest.TestCase):
    def test_quick_check_passes(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "unity_check.py"), "--only", "gameplay",
                                     "--require", "--out", out], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
