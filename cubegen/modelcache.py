"""Blender results in the shared cache (0.26.0 "Stockpile"): export, bake and preview of a model as one unit.

0.25.0 shared the ImageMagick work between output folders and checkouts; the Blender work - FBX/GLB/OBJ export,
the baked or painted maps (on a paint run most of the time) and the preview - still ran again in every new folder.
Since 0.26.0 a model's Blender results are an entry of the shared ``Store`` (``cubegen/cache.py``):

* **Key = every input of the Blender worker:** the job as the worker gets it (formats, texture mode, size, set,
  palette, paint scheme with its data, bake device, render engine and camera) and the model's spec (type, seed,
  name, parameters, style, LOD, set, ...), the folder-bound parts replaced: the textures folder relative to the
  models folder (``RelativeFilename`` in the FBX, ``map_*`` in an MTL), the tile textures by their own cache key
  (``pipeline.texture_key``: size, set, image code, ImageMagick), plus the code that makes the files
  (:func:`model_code`: ``blender_worker`` and everything it imports, the package's data files), Blender's version,
  ImageMagick's version (the grime of ``--textures baked``) and the platform (CPU and GPU bakes differ). A key that
  would still hold an absolute path is not used - that model is built as before.
* **One unit:** export, bake and preview of a model come from the same Blender run, so the baked maps always match
  the UVs of the cached FBX (Smart UV Project is deterministic here - test - but the unit does not rely on it).
* **Only the FBX is folder-bound:** Blender writes the absolute path of every texture into it. The entry keeps a
  canonical FBX (``cubegen/fbxpath.py``: ``<cubegen:textures>/...``) and a hit writes the new folder in - every
  other byte as Blender wrote it (time stamps and object IDs differ between any two exports anyway). GLB, OBJ, MTL,
  the maps and the previews are identical in every folder (checked when the entry is written: the canonical FBX
  must not contain any folder of the run). Side files (an OBJ's MTL, a glTF's buffers and images) belong to the
  unit.
* **Roles instead of paths:** ``models/<file>`` (the model's folder), ``textures/<file>`` (the textures folder,
  ``Neutral/`` included), ``previews/<name>.png``. Not cached: the overview ``.blend`` (it holds absolute image
  paths, and it is the one Blender start a fully cached run still makes) and anything a model writes outside these
  folders.

``--force`` reuses nothing but records, like the image steps; ``CUBEGEN_CACHE=0`` turns the shared cache off.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from .cache import Store, atomic_write, file_hash, input_key

FORMAT = 1  # entry layout of a model unit (roles, data); a change makes every model entry a miss
STEP = "model"
FOLDERS = ("textures", "models", "previews")
#: job keys that are host-side plumbing or folders, not inputs of a model's files
JOB_VOLATILE = ("models", "blend", "textures_ready", "queue_dir", "result_path", "magick", "models_dir", "previews_dir",
                "textures_dir", "textures", "uv_dir")
SPEC_VOLATILE = ("build_key", "models_dir", "skip", "bake_cache")
#: the package files that never shape a model's files: the command line entry point
CODE_SKIP = ("__main__.py",)
VERSION_LINE = re.compile(rb"^__version__\s*=.*$", re.MULTILINE)

_MODEL_CODE: List[str] = []


def code_files(root: str) -> List[str]:
    """Every file of the package (sources and data: contract.json, family recipes), sorted, without ``__pycache__``."""
    found = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        found += [os.path.join(folder, f) for f in sorted(files)
                  if not f.endswith((".pyc", ".pyo")) and f not in CODE_SKIP and not f.startswith(".")]
    return found


def model_code(root: Optional[str] = None) -> str:
    """Hash of the code that makes a model's Blender files: the whole package - the Blender worker imports nearly
    all of it (``pipeline.module_closure("blender_worker")`` names 68 of 72 modules) and reading the closure from the
    sources costs 0.4 s per run, hashing every file 5 ms. Left out: ``__main__.py`` and the version line of
    ``cubegen/__init__.py`` - a release that leaves the code alone keeps the cache warm (the version is written by the
    pipeline into the sidecars, never into a Blender file)."""
    if root is None and _MODEL_CODE:
        return _MODEL_CODE[0]
    base = root or os.path.dirname(os.path.abspath(__file__))
    h = hashlib.sha256(b"cubegen-model-code\0")
    for path in code_files(base):
        with open(path, "rb") as fh:
            data = fh.read()
        rel = os.path.relpath(path, base).replace(os.sep, "/")
        if rel == "__init__.py":
            data = VERSION_LINE.sub(b"", data)
        h.update(rel.encode() + b"\0" + hashlib.sha256(data).digest())
    value = h.hexdigest()
    if root is None:
        _MODEL_CODE.append(value)
    return value


def host() -> List[str]:
    """What else a bake depends on: platform and machine (Cycles on the CPU and on a GPU give other noise)."""
    return [sys.platform, platform.machine()]


# --- folders <-> roles -----------------------------------------------------------------------------------------------

def _norm(path: str) -> str:
    return os.path.normpath(os.path.abspath(path))


def _under(path: str, folder: str) -> Optional[str]:
    """``path`` relative to ``folder`` ("/" separated) when it lies below it, else None."""
    try:
        rel = os.path.relpath(_norm(path), _norm(folder))
    except ValueError:  # pragma: no cover - Windows, other drive
        return None
    if rel == os.curdir or rel == os.pardir or rel.startswith(os.pardir + os.sep) or os.path.isabs(rel):
        return None
    return rel.replace(os.sep, "/")


class Folders:
    """The folders of one model in this run: ``models`` (its own, library category included), ``textures``,
    ``previews``; ``out`` only to check that nothing else is folder-bound."""

    def __init__(self, models: str, previews: str, textures: Optional[str], out: str):
        self.models, self.previews, self.out = _norm(models), _norm(previews), _norm(out)
        self.textures = _norm(textures) if textures else None

    def items(self) -> List[Tuple[str, str]]:
        """(role prefix, folder), deepest first - ``models/Textures`` belongs to ``textures``."""
        pairs = [("textures", self.textures), ("models", self.models), ("previews", self.previews)]
        return sorted([(k, v) for k, v in pairs if v], key=lambda p: -len(p[1]))

    def role(self, path: str) -> Optional[str]:
        for name, folder in self.items():
            rel = _under(path, folder)
            if rel is not None:
                return f"{name}/{rel}"
        return None

    def path(self, role: str) -> Optional[str]:
        name, _, rel = role.partition("/")
        folder = getattr(self, name, None) if name in FOLDERS else None
        if not folder or not rel or rel.startswith("/") or ".." in rel.split("/"):
            return None
        return os.path.join(folder, *rel.split("/"))

    def all(self) -> List[str]:
        """Every folder of the run, also as resolved real path (``/tmp`` -> ``/private/tmp``) - none may remain in a
        cached file."""
        found = set()
        for folder in (self.models, self.previews, self.textures, self.out):
            if folder:
                found.update({folder, os.path.realpath(folder)})
        return sorted(found, key=len, reverse=True)

    def relative_textures(self) -> Optional[str]:
        return os.path.relpath(self.textures, self.models).replace(os.sep, "/") if self.textures else None


def _sanitize(value: Any, folders: Folders) -> Any:
    """``value`` with every absolute path below a folder of the run as ``<role>``: a key never holds a folder."""
    if isinstance(value, dict):
        return {k: _sanitize(v, folders) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v, folders) for v in value]
    if isinstance(value, str) and os.path.isabs(value):
        role = folders.role(value)
        return f"<{role}>" if role else value
    return value


def _has_absolute(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_absolute(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_absolute(v) for v in value)
    return isinstance(value, str) and (os.path.isabs(value) or (len(value) > 2 and value[1] == ":" and value[2] in "\\/"))


def model_key(spec: Dict, job: Dict, folders: Folders, extra: Dict[str, Any]) -> Optional[str]:
    """The model's cache key - None when an input still names a folder (then the model is not cached).

    ``extra``: what the job does not carry itself - ``blender`` (version), ``magick`` (version), ``texture_key``
    (the tile textures' own key, when the run has them)."""
    inputs = {
        "format": FORMAT,
        "spec": _sanitize({k: v for k, v in spec.items() if k not in SPEC_VOLATILE}, folders),
        "job": _sanitize({k: v for k, v in job.items() if k not in JOB_VOLATILE}, folders),
        # the tile textures: names and maps (their files come from texture_key), relative to the textures folder
        "textures": _sanitize(job.get("textures") or {}, folders),
        "relative_textures": folders.relative_textures(),
        "code": model_code(),
        "host": host(),
        **extra,
    }
    if _has_absolute(inputs):
        return None
    return input_key(STEP, inputs)


# --- the files of a worker result -----------------------------------------------------------------------------------

def _mtl_of(obj_path: str) -> List[str]:
    """The MTL files an OBJ names (``mtllib``), next to it."""
    found = []
    try:
        with open(obj_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("mtllib "):
                    found.append(os.path.join(os.path.dirname(obj_path), line[7:].strip()))
                elif line.startswith(("v ", "f ")):
                    break
    except OSError:
        pass
    return found


def _gltf_side_files(gltf_path: str) -> List[str]:
    """Buffers and images a separate glTF names by relative URI."""
    try:
        with open(gltf_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    found = []
    for item in (data.get("buffers") or []) + (data.get("images") or []):
        uri = item.get("uri") if isinstance(item, dict) else None
        if uri and not uri.startswith("data:") and "://" not in uri:
            from urllib.parse import unquote

            found.append(os.path.join(os.path.dirname(gltf_path), *unquote(uri).split("/")))
    return found


def result_files(result: Dict) -> List[str]:
    """Every file of a worker result: exports with their side files, preview, baked / painted / neutral maps."""
    files = []
    for fmt, path in (result.get("files") or {}).items():
        if fmt == "rig":
            continue
        files.append(path)
        if fmt == "obj":
            files += _mtl_of(path)
        elif fmt == "gltf":
            files += _gltf_side_files(path)
    if result.get("preview"):
        files.append(result["preview"])
    for key in ("baked", "neutral_maps"):
        files += list((result.get(key) or {}).values())
    for value in (result.get("neutral") or {}).values():
        files += value if isinstance(value, list) else [value]
    return list(dict.fromkeys(files))


def _to_roles(value: Any, roles: Dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: _to_roles(v, roles) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_roles(v, roles) for v in value]
    if isinstance(value, str) and value in roles:
        return {"role": roles[value]}
    return value


def _from_roles(value: Any, folders: Folders) -> Any:
    if isinstance(value, dict):
        if set(value) == {"role"}:
            return folders.path(value["role"])
        return {k: _from_roles(v, folders) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_roles(v, folders) for v in value]
    return value


#: the worker result's keys that describe the files (timings are this run's, not the entry's); ``engine``: the render
#: engine of the run that made the preview (manifest ``blender.render_engine`` of a run without a Blender start)
RESULT_KEYS = ("name", "files", "preview", "baked", "baked_material", "bake_device", "paint", "neutral", "weight_layout",
               "neutral_maps", "engine")


class ModelCache:
    """Fetch and record model units in a ``Store``. ``fetch`` copies a unit into this run's folders and returns the
    worker result it stands for; ``put`` records what a worker built."""

    def __init__(self, store: Store, log=None):
        self.store = store
        self.log = log or (lambda message: None)
        self.fetched = 0
        self.stored = 0
        self.refused: List[str] = []  # models that could not be recorded (reason)

    def fetch(self, key: str, folders: Folders) -> Optional[Dict]:
        entry = self.store.lookup(key)
        if not entry or entry.get("step") != STEP or not isinstance(entry.get("data"), dict):
            return None
        data = entry["data"]
        canonical = set(data.get("canonical") or [])
        targets = {role: folders.path(role) for role in entry["files"]}
        if not all(targets.values()):
            return None
        for role, sha in entry["files"].items():
            target = targets[role]
            if role in canonical:
                if not self._fetch_fbx(sha, target, folders):
                    return None
                continue
            try:  # the same content may already be there (another model's tile texture, a second run): keep it
                if os.path.getsize(target) == os.path.getsize(self.store.object_path(sha)) and file_hash(target) == sha:
                    continue
            except OSError:
                pass
            if not self.store.fetch(sha, target):
                return None
        result = _from_roles(data["result"], folders)
        result.update(timings={}, reused=True, shared=True)
        self.fetched += 1
        return result

    def _fetch_fbx(self, sha: str, target: str, folders: Folders) -> bool:
        from .fbxpath import concrete

        source = self.store.object_path(sha)
        try:
            with open(source, "rb") as fh:
                raw = fh.read()
            if hashlib.sha256(raw).hexdigest() != sha:
                os.remove(source)  # a broken object never reaches an output folder
                return False
            data = concrete(raw, {"textures": folders.textures or "", "models": folders.models})
            os.makedirs(os.path.dirname(target), exist_ok=True)
            atomic_write(target, data)
            os.utime(source, None)
        except (OSError, ValueError):
            return False
        return True

    def put(self, key: str, result: Dict, folders: Folders) -> bool:
        """Record a worker result under ``key``; False (with the reason in ``refused``) when a file is outside the
        run's folders or an FBX still names a folder after the rewrite."""
        from .fbxpath import canonical

        name = result.get("name", "?")
        files: Dict[str, Tuple[str, str]] = {}  # role -> (path, sha)
        roles: Dict[str, str] = {}
        canonical_roles = []
        blobs: Dict[str, bytes] = {}
        markers = [folder.encode("utf-8") for folder in folders.all()]
        for path in result_files(result):
            role = folders.role(path)
            if role is None or not os.path.isfile(path):
                self.refused.append(f"{name}: {path} is outside the output folders")
                return False
            roles[path] = role
            if path.lower().endswith(".fbx"):
                try:
                    with open(path, "rb") as fh:
                        data, _ = canonical(fh.read(), {"textures": folders.textures or "", "models": folders.models})
                except (OSError, ValueError) as exc:
                    self.refused.append(f"{name}: {os.path.basename(path)} not rewritable ({exc})")
                    return False
                if any(marker in data for marker in markers):
                    self.refused.append(f"{name}: {os.path.basename(path)} names a folder of this run")
                    return False
                sha = hashlib.sha256(data).hexdigest()
                blobs[sha] = data
                canonical_roles.append(role)
                files[role] = ("", sha)
            else:
                files[role] = (path, file_hash(path))
        stored = {k: _to_roles(result[k], roles) for k in RESULT_KEYS if k in result}
        try:
            for sha, data in blobs.items():
                self.store.add_bytes(data, sha)
            for role, (path, sha) in files.items():
                if path and not self.store.add(path, sha):
                    self.refused.append(f"{name}: {os.path.basename(path)} changed while it was recorded")
                    return False
            self.store.put_entry(key, {role: sha for role, (_, sha) in files.items()},
                                 {"result": stored, "canonical": sorted(canonical_roles)}, step=STEP)
        except OSError as exc:
            self.refused.append(f"{name}: cache not writable ({exc})")
            return False
        self.stored += 1
        return True


# --- bakes on their own: a unit that missed (other formats, preview settings, paint scheme) keeps its bake ----------

BAKE_STEP = "bake"
#: job keys a bake depends on (not formats, camera or - for a paint run - the scheme: the neutral bake is the same
#: for every scheme; Compose, export and preview run again). The render engine stays in: a preview set-up (world,
#: light, view transform) comes before the bakes of a Blender process.
BAKE_JOB_KEYS = ("texture_mode", "texture_size", "bake_device")


def bake_key(spec: Dict, job: Dict, folders: Folders, extra: Dict[str, Any]) -> Optional[str]:
    """Key of a model's bake alone - None without a bake (``--textures baked`` / ``--paint``) or when an input still
    names a folder. A paint run's neutral bake and a plain bake differ (``kind``)."""
    if job.get("texture_mode") != "baked" or not job.get("textures"):
        return None
    render = job.get("render") or {}
    inputs = {
        "format": FORMAT,
        "kind": "paint" if job.get("paint") else "baked",
        "spec": _sanitize({k: v for k, v in spec.items() if k not in SPEC_VOLATILE}, folders),
        "job": {k: job.get(k) for k in BAKE_JOB_KEYS},
        "render": [bool(render.get("enabled")), render.get("engine") if render.get("enabled") else None],
        "textures": _sanitize(job.get("textures") or {}, folders),
        "code": model_code(),
        "host": host(),
        **extra,
    }
    if _has_absolute(inputs):
        return None
    return input_key(BAKE_STEP, inputs)


def bake_maps(result: Dict) -> Optional[Dict]:
    """What a worker result's bake made, in the shape the worker takes back (``bake.bake_asset`` /
    ``stylebake.bake_masks``): a paint run's raw neutral maps with layout and device, else the baked maps."""
    if result.get("neutral"):
        return dict(result["neutral"], layout=result.get("weight_layout"), device=result.get("bake_device"))
    if result.get("baked"):
        return dict(result["baked"])
    return None


class BakeCache:
    """Bakes (maps + the atlas UVs they lie on) in a ``Store``: ``fetch`` copies the maps into the run's folders and
    the UVs into ``uv_dir`` and returns what the worker takes as ``spec["bake_cache"]``; ``put`` records a new bake
    (``result["bake_uvs"]``, written by the worker)."""

    def __init__(self, store: Store):
        self.store = store
        self.fetched = 0
        self.stored = 0
        self.refused: List[str] = []

    def fetch(self, key: str, name: str, folders: Folders, uv_dir: str) -> Optional[Dict]:
        entry = self.store.lookup(key)
        if not entry or entry.get("step") != BAKE_STEP or not isinstance(entry.get("data"), dict) \
                or "uvs" not in entry["files"]:
            return None
        uvs = os.path.join(uv_dir, f"{name}.cached.uvs.json")
        if not self.store.fetch(entry["files"]["uvs"], uvs):
            return None
        for role, sha in entry["files"].items():
            if role == "uvs":
                continue
            target = folders.path(role)
            if not target or not self.store.fetch(sha, target):
                return None
        self.fetched += 1
        return {"uvs": uvs, "maps": _from_roles(entry["data"]["maps"], folders), "device": entry["data"]["device"]}

    def put(self, key: str, result: Dict, folders: Folders) -> bool:
        name = result.get("name", "?")
        maps = bake_maps(result)
        uvs = result.get("bake_uvs")
        if not maps or not uvs or not os.path.isfile(uvs):
            return False
        files: Dict[str, Tuple[str, str]] = {"uvs": (uvs, file_hash(uvs))}
        roles = {}
        for value in maps.values():
            for path in value if isinstance(value, list) else [value]:
                if not isinstance(path, str) or not os.path.isabs(path):
                    continue
                role = folders.role(path)
                if role is None or not os.path.isfile(path):
                    self.refused.append(f"{name}: bake map {path} is outside the output folders")
                    return False
                roles[path] = role
                files[role] = (path, file_hash(path))
        try:
            self.store.put(key, files, {"maps": _to_roles(maps, roles), "device": result.get("bake_device")},
                           step=BAKE_STEP)
        except OSError as exc:
            self.refused.append(f"{name}: cache not writable ({exc})")
            return False
        self.stored += 1
        return True
