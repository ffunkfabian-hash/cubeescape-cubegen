"""Host-side Blender CLI integration (find Blender, probe engines, run jobs)."""

from __future__ import annotations

import glob
import json
import os
import platform
import shutil
import subprocess
import tempfile
from typing import Callable, Dict, List, Optional

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender_worker.py")
LOG_PREFIX = "[cubegen]"


class BlenderError(RuntimeError):
    pass


def find_blender(explicit: Optional[str] = None) -> Optional[str]:
    """Locate the Blender executable.

    Order: ``--blender`` argument, ``$BLENDER`` / ``$CUBEGEN_BLENDER``, ``PATH``,
    then the usual install locations on macOS and Windows.
    """
    candidates: List[str] = []
    if explicit:
        candidates.append(explicit)
    for env in ("CUBEGEN_BLENDER", "BLENDER", "BLENDER_PATH"):
        if os.environ.get(env):
            candidates.append(os.environ[env])
    found = shutil.which("blender")
    if found:
        candidates.append(found)
    system = platform.system()
    if system == "Darwin":
        candidates.append("/Applications/Blender.app/Contents/MacOS/Blender")
    elif system == "Windows":
        pattern = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Blender Foundation",
                               "Blender*", "blender.exe")
        candidates.extend(sorted(glob.glob(pattern), reverse=True))
    for cand in candidates:
        path = shutil.which(cand) or cand
        if os.path.isfile(path):
            return path
    if explicit:
        raise BlenderError(f"Blender not found at {explicit!r}")
    return None


def blender_version(blender: str) -> str:
    try:
        out = subprocess.run([blender, "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable ({exc})"
    for line in out.splitlines():
        if line.startswith("Blender"):
            return line.strip()
    return out.strip().splitlines()[0] if out.strip() else "unknown"


def _base_cmd(blender: str) -> List[str]:
    return [blender, "-b", "--factory-startup", "--python-exit-code", "3", "-P", WORKER, "--"]


def probe_engine(blender: str, engine: str = "workbench") -> bool:
    """Try a tiny render. Workbench/Eevee need an OpenGL context which headless servers often lack."""
    with tempfile.TemporaryDirectory(prefix="cubegen_probe_") as tmp:
        out = os.path.join(tmp, "probe.png")
        try:
            subprocess.run(_base_cmd(blender) + ["--probe", out, "--engine", engine], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return os.path.isfile(out) and os.path.getsize(out) > 0


def resolve_engine(blender: str, requested: str, log: Callable[[str], None] = print) -> str:
    requested = requested.lower()
    if requested != "auto":
        return requested
    if probe_engine(blender, "workbench"):
        return "workbench"
    log("Workbench needs OpenGL which is not available here - falling back to Cycles (CPU) for previews")
    return "cycles"


def run_job(blender: str, job: Dict, workdir: str, verbose: bool = False,
            log: Callable[[str], None] = print) -> Dict:
    """Run the Blender worker for a job and return its result dictionary."""
    job_path = os.path.join(workdir, "job.json")
    result_path = os.path.join(workdir, "job_result.json")
    job = dict(job, result_path=result_path)
    with open(job_path, "w", encoding="utf-8") as fh:
        json.dump(job, fh, indent=2)
    cmd = _base_cmd(blender) + ["--job", job_path]
    tail: List[str] = []
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            tail = (tail + [line])[-40:]
            if line.startswith(LOG_PREFIX):
                log(line[len(LOG_PREFIX):].strip())
            elif verbose:
                log("  blender: " + line)
        code = proc.wait()
    if code != 0 or not os.path.isfile(result_path):
        raise BlenderError(f"Blender worker failed (exit code {code}). Last output:\n" + "\n".join(tail))
    with open(result_path, "r", encoding="utf-8") as fh:
        return json.load(fh)
