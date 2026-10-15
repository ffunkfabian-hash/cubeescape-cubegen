"""cubegen 0.27.0 "Fieldbook": the heavy-run lock stays held until the last grandchild of a Unity step has ended."""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

# holds the lock like unity_check.main and runs one step through run_in_group (argv: tools folder, step code)
HOLDER = textwrap.dedent("""
    import sys
    sys.path.insert(0, sys.argv[1])
    import unity_check
    with unity_check.HeavyLock("Cubegen test", out=print) as lock:
        lock.acquire()
        done = unity_check.run_in_group([sys.executable, "-c", sys.argv[2]], capture_output=True, text=True)
        print("step", done.returncode, flush=True)
    """)
TRY = textwrap.dedent("""
    import fcntl, os, sys
    fd = os.open(sys.argv[1], os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("free")
    except OSError:
        print("held")
    """)


class HeavyStepGroupTest(unittest.TestCase):
    """Codex review of Toolgen 0.4: a step that died before its children (verify.sh above Unity) freed the lock."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "CubeEscape", "heavy-run.lock")
        self.started = os.path.join(self.dir, "started")
        self.marker = os.path.join(self.dir, "grandchild-ended")
        self.env = {k: v for k, v in os.environ.items() if k not in ("CE_HEAVY_LOCK", "CE_HEAVY_HELD")}
        self.env["CE_HEAVY_LOCK_FILE"] = self.path

    def lock_state(self) -> str:
        return subprocess.run([sys.executable, "-c", TRY, self.path], capture_output=True, text=True).stdout.strip()

    def hold(self, grandchild: str, then: str) -> subprocess.Popen:
        """The holder runs a step that starts `grandchild` (same process group), marks 'started', then runs `then`."""
        step = ("import subprocess, sys\n"
                f"subprocess.Popen([sys.executable, '-c', {grandchild!r}], stdout=subprocess.DEVNULL)\n"
                f"open({self.started!r}, 'w').close()\n" + then)
        holder = subprocess.Popen([sys.executable, "-c", HOLDER, TOOLS, step], stdout=subprocess.PIPE, text=True,
                                  env=self.env)
        self.addCleanup(lambda: holder.poll() is None and holder.kill())
        self.addCleanup(holder.stdout.close)
        deadline = time.monotonic() + 10
        while not os.path.exists(self.started):
            self.assertLess(time.monotonic(), deadline, "the step did not start")
            time.sleep(0.02)
        return holder

    def test_a_grandchild_keeps_the_lock_after_its_step_ended(self):
        grandchild = f"import time; time.sleep(1.5); open({self.marker!r}, 'w').write('x')"
        holder = self.hold(grandchild, "raise SystemExit(3)")  # the step ends at once, its grandchild goes on
        time.sleep(0.4)
        self.assertIsNone(holder.poll(), "the holder still waits for the grandchild")
        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual(self.lock_state(), "held")
        out, _ = holder.communicate(timeout=10)
        self.assertIn("step 3", out, "the exit code of the step is kept")
        self.assertTrue(os.path.exists(self.marker), "the lock was held until the grandchild ended")
        self.assertEqual(self.lock_state(), "free")

    def test_a_term_reaches_the_grandchildren_before_the_lock_is_free(self):
        grandchild = ("import signal, sys, time\n"
                      f"def done(*a): time.sleep(0.5); open({self.marker!r}, 'w').write('x'); sys.exit(0)\n"
                      "signal.signal(signal.SIGTERM, done)\n"
                      f"open({self.marker + '.ready'!r}, 'w').close()\ntime.sleep(30)\n")
        holder = self.hold(grandchild, "import time; time.sleep(30)")
        ready = self.marker + '.ready'
        deadline = time.monotonic() + 10
        while not os.path.exists(ready):  # the grandchild has set its handler
            self.assertLess(time.monotonic(), deadline, "the grandchild did not start")
            time.sleep(0.02)
        holder.send_signal(signal.SIGTERM)
        self.assertEqual(holder.wait(timeout=10), 128 + signal.SIGTERM, "the check ends after its step")
        self.assertTrue(os.path.exists(self.marker), "the grandchild got the TERM and ended first")
        self.assertEqual(self.lock_state(), "free")


if __name__ == "__main__":
    unittest.main()
