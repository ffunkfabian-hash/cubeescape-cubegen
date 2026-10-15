"""One-time move of the per-folder caches of 0.15-0.24 into the shared store (0.25.0 "Quartermaster").

Before 0.25 every output folder kept its own ``.cubegen_cache.json`` with absolute paths, and its keys held the hash
of the whole generator. A folder's entries are taken over only when everything checks out:

- its manifest names a generator whose image code (``pipeline.image_code``) is today's - ``MIGRATABLE`` maps the
  ``source_hash`` of such a release to its image code, an entry counts only while that equals today's;
- each old key, recomputed from the manifest exactly as that version did, equals the stored one (so the inputs are
  known), and every file still has the hash the old cache recorded.

Then the files go into the store under today's key - the first run after the release is warm. ``migrate_once`` runs
for the default store and the ``output`` folders of the main checkout and this one (marker ``migrated.json`` in the
store); ``python3 -m cubegen cache --migrate DIR`` takes any folder.
"""

from __future__ import annotations

import json
import os
import time
from typing import Callable, Dict, List, Optional

from .cache import CACHE_NAME, Store, atomic_write, file_hash, png_content_hash
from .pipeline import (_relative_textures, icon_key, image_code, set_row_key, sheet_key, sheet_title, swatch_key,
                       texture_key)

#: generator ``source_hash`` (manifest) -> the image code of that release; 0.24.0 "Primer" made its images with the
#: same code as 0.25.0 (imagemagick, textures, materials, seeds unchanged - checked by a test against this value)
MIGRATABLE = {
    "bc82b5114f182190584fa8f46f11ee210d7adcf2487cc2885fe0381974ddd121":
        "cf79d8c2c78ad373569d81009454c03bdb95bb7138d95729860ce9a0bd196b13",
}
MARKER = "migrated.json"


def _load(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _old_entries(folder: str) -> Dict[str, Dict]:
    """The entries of a format-1 cache file (0.15-0.24), paths absolute; {} for anything else."""
    data = _load(os.path.join(folder, CACHE_NAME))
    if not isinstance(data, dict) or data.get("format") != 1:
        return {}
    return {name: entry for name, entry in (data.get("entries") or {}).items() if isinstance(entry, dict)}


def _unchanged(entry: Dict) -> bool:
    try:
        return all(file_hash(path) == digest for path, digest in (entry.get("files") or {}).items())
    except OSError:
        return False


def migrate_folder(out: str, store: Store, log: Optional[Callable[[str], None]] = None) -> Dict:
    """Take the verified image entries of the output folder ``out`` (and of its textures folder) into ``store``."""
    out = os.path.abspath(out)
    result: Dict = {"folder": out, "migrated": 0, "skipped": 0}
    manifest = _load(os.path.join(out, "manifest.json"))
    if not isinstance(manifest, dict):
        result["reason"] = "no manifest.json"
        return result
    source, magick = manifest.get("source_hash"), manifest.get("imagemagick")
    if MIGRATABLE.get(source) != image_code():
        result["reason"] = f"generator {manifest.get('version', '?')}: other image code"
        return result
    cfg = manifest.get("config") or {}
    models = manifest.get("models") or []
    previews = {m["name"]: os.path.normpath(os.path.join(out, m["preview"])) for m in models if m.get("preview")}
    work = []  # (entry, old key, new key, {role: path}, data)

    def hashes(paths):
        return [file_hash(p) for p in paths], [png_content_hash(p) for p in paths]

    for name, entry in _old_entries(out).items():
        files = list((entry.get("files") or {}))
        if len(files) != 1:
            continue
        target = files[0]
        try:
            if name == "swatch":
                old, new = swatch_key(magick, code=source), swatch_key(magick)
            elif name.startswith("icon:"):
                preview = previews[os.path.basename(target)[len("Icon_"):-len(".png")]]
                (old_hash,), (new_hash,) = hashes([preview])
                old = icon_key(old_hash, cfg.get("icon_size"), cfg.get("icon_background"), magick, code=source)
                new = icon_key(new_hash, cfg.get("icon_size"), cfg.get("icon_background"), magick)
            elif name == "contact_sheet":
                labels = [m["name"] for m in models if m.get("preview")]
                old_hashes, new_hashes = hashes([previews[n] for n in labels])
                title = sheet_title(manifest.get("seed"), manifest.get("family"))
                old = sheet_key(labels, old_hashes, title, magick, code=source)
                new = sheet_key(labels, new_hashes, title, magick)
            elif name.startswith("set:"):
                row = os.path.relpath(target, out).replace(os.sep, "/")
                members = next(s["members"] for s in manifest.get("sets") or [] if s.get("preview") == row)
                paths = [previews[m] for m in members if m in previews and os.path.isfile(previews[m])]
                old_hashes, new_hashes = hashes(paths)
                old = set_row_key(old_hashes, magick, code=source, legacy=True)
                new = set_row_key(new_hashes, magick)
            else:
                continue
        except (KeyError, StopIteration, OSError, TypeError):
            result["skipped"] += 1
            continue
        work.append((entry, old, new, {"out": target}, entry.get("data")))

    textures = manifest.get("textures") or {}
    if textures.get("dir") and textures.get("mode") != "palette":
        folder = os.path.normpath(os.path.join(out, textures["dir"]))
        entry = _old_entries(folder).get("texture_set")
        if entry and isinstance(entry.get("data"), dict):
            old = texture_key(cfg.get("texture_size"), cfg.get("texture_set"), magick, code=source, legacy_dir=folder)
            roles = {os.path.relpath(p, folder).replace(os.sep, "/"): p for p in entry.get("files") or {}}
            try:
                data = _relative_textures(entry["data"], folder)
            except (KeyError, TypeError, AttributeError, ValueError):
                data = None
            if data is not None and not any(r.startswith("../") for r in roles):
                work.append((entry, old, texture_key(cfg.get("texture_size"), cfg.get("texture_set"), magick),
                             roles, data))

    for entry, old, new, roles, data in work:
        if entry.get("key") != old or not _unchanged(entry):
            result["skipped"] += 1
            continue
        files = {role: (path, entry["files"][path]) for role, path in roles.items()}
        if store.put(new, files, data, step="migrated"):
            result["migrated"] += 1
        else:
            result["skipped"] += 1
    if log and (result["migrated"] or result["skipped"]):
        log(f"shared cache: {result['migrated']} entries taken over from {out}"
            + (f", {result['skipped']} skipped" if result["skipped"] else ""))
    return result


def default_roots(package_root: Optional[str] = None) -> List[str]:
    """``output`` of this checkout and, in a worktree, of the main checkout."""
    root = package_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = [os.path.join(root, "output")]
    git = os.path.join(root, ".git")
    if os.path.isfile(git):  # a worktree: "gitdir: <main>/.git/worktrees/<name>"
        try:
            with open(git, "r", encoding="utf-8") as fh:
                gitdir = fh.read().strip().partition("gitdir:")[2].strip()
        except OSError:
            gitdir = ""
        marker = os.sep + os.path.join(".git", "worktrees") + os.sep
        if marker in gitdir:
            roots.append(os.path.join(gitdir.split(marker)[0], "output"))
    return [r for i, r in enumerate(roots) if r not in roots[:i] and os.path.isdir(r)]


def find_folders(roots: List[str], depth: int = 2) -> List[str]:
    """Output folders (a manifest and an old cache file) up to ``depth`` levels below each root."""
    found = []
    for root in roots:
        for folder, dirs, files in os.walk(root):
            level = os.path.relpath(folder, root).count(os.sep) + (0 if folder == root else 1)
            if level >= depth:
                dirs[:] = []
            dirs.sort()
            if "manifest.json" in files and CACHE_NAME in files:
                found.append(folder)
    return found


def migrate_once(store: Store, log: Callable[[str], None] = print, roots: Optional[List[str]] = None,
                 force: bool = False) -> Optional[Dict]:
    """Migrate the default folders into the default store once (marker ``migrated.json``). Another store (the tests'
    ``CUBEGEN_CACHE``) only with ``roots`` given or ``force``."""
    marker = os.path.join(store.root, MARKER)
    if not force and (os.path.isfile(marker) or (roots is None and os.environ.get("CUBEGEN_CACHE"))):
        return None
    folders = find_folders(roots if roots is not None else default_roots())
    results = []
    for folder in folders:
        try:
            results.append(migrate_folder(folder, store, log))
        except OSError as exc:  # a full or read-only cache disk never fails the run that triggered this
            results.append({"folder": folder, "migrated": 0, "skipped": 0, "reason": str(exc)})
    summary = {"format": 1, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "folders": results}
    try:
        atomic_write(marker, json.dumps(summary, indent=1).encode("utf-8"))
    except OSError:
        pass
    return summary
