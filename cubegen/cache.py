"""Skip ImageMagick work whose inputs did not change - in this output folder or in any other one on this machine.

Two parts since 0.25.0 "Quartermaster" (before, every new output folder or worktree started cold):

* **Shared store** (``Store``): one content-addressed directory for the whole machine - main checkout, worktrees,
  the macOS app, ``tools/unity_check.py``. ``objects/<ab>/<sha256>`` holds file contents, ``entries/<ab>/<key>.json``
  maps an input key to the files it produced (``{role: sha256}``) plus the step's data. No absolute paths anywhere:
  a key is made of inputs only, a role is a name relative to where the caller wants the files. Every write goes to a
  temporary file in the same folder and is renamed into place (a reader sees the old or the new file, never half of
  one). The size is limited (``CUBEGEN_CACHE_LIMIT_GB``, default 4): least recently used entries go first, nothing
  used in the last two hours, a hit refreshes the entry. Location: ``$CUBEGEN_CACHE``, else
  ``~/Library/Caches/Cubegen/cache`` (macOS), ``$XDG_CACHE_HOME/cubegen/cache`` (Linux, else ``~/.cache``),
  ``%LOCALAPPDATA%/Cubegen/cache`` (Windows); ``CUBEGEN_CACHE=0`` turns it off.
* **Folder index** (``OutputCache``, ``<folder>/.cubegen_cache.json``): what is folder-bound - which files in this
  folder are current. Per entry name the input key, the SHA-256 and size/time of each file, paths relative to the
  folder (format 2; format 1 of 0.15-0.24 had absolute paths and is converted when read).

A folder entry is only reused when the key matches and every file still exists with exactly that content - a file
changed or deleted by someone else is rebuilt (or copied back from the store). This needs byte-identical output for
identical input, which is why every ImageMagick call excludes the PNG time stamps (``imagemagick.REPRODUCIBLE``).
``enabled=False`` (``--force``) never reuses, but still records - in the folder and in the store.

0.21.0: an index of size and modification time per file (``stats`` of an entry, ``index`` of the cache) - a file
whose size and time are those of its last hash is not read again. 0.25.0: the index holds the *content* hash of an
input image (``png_content_hash``: Blender writes its render date into every preview, the pixels stay the same).
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
import time
import uuid
from typing import Dict, Iterable, List, Optional, Tuple, Union

CACHE_NAME = ".cubegen_cache.json"  # leading dot: Unity ignores the file inside Assets/
FORMAT = 2  # folder index: 1 = 0.15-0.24 (absolute paths), 2 = 0.25 (relative paths, content hashes of inputs)
STORE_FORMAT = 1
DEFAULT_LIMIT_GB = 4.0
KEEP_SECONDS = 2 * 3600  # pruning never removes what was written or used in the last two hours
PRUNE_EVERY = 3600  # a run checks the size at most once an hour (a stamp file in the store)
OFF = ("0", "off", "no", "false", "none")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
METADATA_CHUNKS = (b"tEXt", b"zTXt", b"iTXt", b"tIME")

#: where a step's files go: a directory (roles are paths relative to it) or ``{role: path}`` (one file: ``"out"``)
Place = Union[str, Dict[str, str], None]


def input_key(*parts) -> str:
    """Stable hash of JSON-serialisable inputs."""
    text = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_state(path: str) -> List[int]:
    """Size and modification time (ns) - what the index compares before it reads a file."""
    st = os.stat(path)
    return [st.st_size, st.st_mtime_ns]


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def png_content_hash(path: str) -> str:
    """SHA-256 of what a PNG shows: every chunk except text and time (tEXt, zTXt, iTXt, tIME). Blender stamps the
    render date and time into each preview, so the same pixels had other bytes on every render and the icons, the
    contact sheet and the set rows made from them never matched in another folder. Not a PNG: the file's hash."""
    with open(path, "rb") as fh:
        data = fh.read()
    if not data.startswith(PNG_SIGNATURE):
        return hashlib.sha256(data).hexdigest()
    h = hashlib.sha256(b"png-content\0")
    pos = len(PNG_SIGNATURE)
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        end = pos + 12 + length
        if kind not in METADATA_CHUNKS:
            h.update(data[pos:end])
        pos = end
        if kind == b"IEND":
            break
    h.update(data[pos:])  # anything after IEND (or a cut file) still counts
    return h.hexdigest()


# --- where the store lives -----------------------------------------------------------------------------------------

def default_root(env=None, platform: Optional[str] = None) -> str:
    env = os.environ if env is None else env
    platform = platform or sys.platform
    home = os.path.expanduser("~")
    if platform == "darwin":
        return os.path.join(home, "Library", "Caches", "Cubegen", "cache")
    if platform.startswith("win"):
        return os.path.join(env.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local"), "Cubegen", "cache")
    return os.path.join(env.get("XDG_CACHE_HOME") or os.path.join(home, ".cache"), "cubegen", "cache")


def store_root(env=None) -> Optional[str]:
    """The shared store's directory, None when ``CUBEGEN_CACHE=0`` (folder index only, like 0.24)."""
    env = os.environ if env is None else env
    value = (env.get("CUBEGEN_CACHE") or "").strip()
    if value.lower() in OFF:
        return None
    return os.path.abspath(os.path.expanduser(value)) if value else default_root(env)


def limit_bytes(env=None) -> int:
    env = os.environ if env is None else env
    try:
        gb = float(env.get("CUBEGEN_CACHE_LIMIT_GB") or DEFAULT_LIMIT_GB)
    except ValueError:
        gb = DEFAULT_LIMIT_GB
    return int(max(0.0, gb) * 1024 ** 3)


# --- atomic files ----------------------------------------------------------------------------------------------------

def _temp_name(path: str) -> str:
    return f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def atomic_write(path: str, data: bytes) -> None:
    """Write ``data`` to a temporary file next to ``path`` and rename it into place."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = _temp_name(path)
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        _remove(tmp)
        raise


def atomic_copy(src: str, dst: str, expect: Optional[str] = None) -> str:
    """Copy ``src`` to ``dst`` through a temporary file; returns the SHA-256 of the copied bytes. ``expect``: when the
    bytes have another hash, ``dst`` stays untouched and ``ValueError`` is raised (a changed or broken source)."""
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    tmp = _temp_name(dst)
    h = hashlib.sha256()
    try:
        with open(src, "rb") as fi, open(tmp, "wb") as fo:
            for block in iter(lambda: fi.read(1 << 20), b""):
                h.update(block)
                fo.write(block)
        digest = h.hexdigest()
        if expect is not None and digest != expect:
            raise ValueError(f"{src}: content changed (sha256 {digest[:12]}, expected {expect[:12]})")
        os.replace(tmp, dst)
    except BaseException:
        _remove(tmp)
        raise
    return digest


def _touch(path: str) -> None:
    try:
        os.utime(path, None)
    except OSError:
        pass


def _try_lock(path: str):
    """An exclusive, non-blocking lock (one pruner at a time); None while another process holds it. Windows: no
    flock - pruning runs unlocked there (every removal tolerates a file that is already gone)."""
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows
        return -1
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0), 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def _unlock(fd) -> None:
    if fd is not None and fd >= 0:
        os.close(fd)


# --- the shared store ------------------------------------------------------------------------------------------------

class Store:
    """Content-addressed cache shared by every checkout and output folder (see the module docstring)."""

    def __init__(self, root: str, limit: Optional[int] = None):
        self.root = os.path.abspath(root)
        self.limit = limit_bytes() if limit is None else limit
        self.objects = os.path.join(self.root, "objects")
        self.entries = os.path.join(self.root, "entries")

    @classmethod
    def default(cls) -> Optional["Store"]:
        root = store_root()
        return cls(root) if root else None

    def object_path(self, sha: str) -> str:
        return os.path.join(self.objects, sha[:2], sha)

    def entry_path(self, key: str) -> str:
        return os.path.join(self.entries, key[:2], key + ".json")

    def lookup(self, key: str) -> Optional[Dict]:
        """The entry of ``key`` (``{"files": {role: sha256}, "data"}``) - a hit marks it as recently used."""
        path = self.entry_path(key)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                entry = json.load(fh)
        except (OSError, ValueError):
            return None
        if not isinstance(entry, dict) or entry.get("format") != STORE_FORMAT or entry.get("key") != key \
                or not isinstance(entry.get("files"), dict):
            return None
        _touch(path)
        return entry

    def fetch(self, sha: str, target: str) -> bool:
        """Copy the content ``sha`` to ``target`` (atomically, checked against its hash); False when it is gone."""
        source = self.object_path(sha)
        try:
            atomic_copy(source, target, expect=sha)
        except ValueError:  # a broken object never reaches an output folder
            _remove(source)
            return False
        except OSError:
            return False
        _touch(source)
        return True

    def add(self, path: str, sha: str) -> bool:
        """Store the content of ``path`` (known to hash to ``sha``); False when the file changed meanwhile."""
        target = self.object_path(sha)
        if os.path.isfile(target):
            _touch(target)
            return True
        try:
            atomic_copy(path, target, expect=sha)
        except ValueError:
            return False
        return True

    def put(self, key: str, files: Dict[str, Tuple[str, str]], data=None, step: Optional[str] = None) -> bool:
        """Record ``key`` -> ``files`` (``{role: (path, sha256)}``): the contents first, the entry last - a reader
        never finds an entry whose contents are missing (unless pruning removed them: then it is a miss)."""
        for path, sha in files.values():
            if not self.add(path, sha):
                return False
        entry = {"format": STORE_FORMAT, "key": key, "step": step, "data": data,
                 "files": {role: sha for role, (_, sha) in sorted(files.items())},
                 "bytes": sum(os.path.getsize(path) for path, _ in files.values())}
        atomic_write(self.entry_path(key), json.dumps(entry, sort_keys=True).encode("utf-8"))
        return True

    # --- size ---

    def scan(self):
        """``entries`` [(mtime, path, size, [sha])], ``objects`` {sha: (path, size, mtime)}, ``temps`` [(path, mtime)]
        (left behind by a writer that crashed)."""
        entries, objects, temps = [], {}, []
        for folder, kind in ((self.entries, "entry"), (self.objects, "object")):
            try:
                subs = sorted(os.listdir(folder))
            except OSError:
                continue
            for sub in subs:
                try:
                    names = os.listdir(os.path.join(folder, sub))
                except OSError:
                    continue
                for name in names:
                    path = os.path.join(folder, sub, name)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    if name.endswith(".tmp"):
                        temps.append((path, st.st_mtime))
                    elif kind == "object":
                        objects[name] = (path, st.st_size, st.st_mtime)
                    elif name.endswith(".json"):
                        try:
                            with open(path, "r", encoding="utf-8") as fh:
                                shas = list((json.load(fh).get("files") or {}).values())
                        except (OSError, ValueError, AttributeError):
                            shas = []
                        entries.append((st.st_mtime, path, st.st_size, shas))
        return entries, objects, temps

    def usage(self) -> Dict:
        entries, objects, _ = self.scan()
        return {"root": self.root, "entries": len(entries), "objects": len(objects),
                "bytes": sum(o[1] for o in objects.values()) + sum(e[2] for e in entries), "limit": self.limit}

    def prune(self, limit: Optional[int] = None, keep_seconds: float = KEEP_SECONDS,
              now: Optional[float] = None) -> Dict:
        """Shrink the store to ``limit`` bytes: contents no entry names first, then the least recently used entries
        with the contents only they named - never anything written or used in the last ``keep_seconds``."""
        limit = self.limit if limit is None else limit
        now = time.time() if now is None else now
        os.makedirs(self.root, exist_ok=True)
        lock = _try_lock(os.path.join(self.root, "prune.lock"))
        if lock is None:
            return {"skipped": "another process is pruning"}
        try:
            entries, objects, temps = self.scan()
            result = {"entries_removed": 0, "objects_removed": 0, "bytes_freed": 0}
            for path, mtime in temps:
                if now - mtime > keep_seconds:
                    _remove(path)
            refs: Dict[str, int] = {}
            for _, _, _, shas in entries:
                for sha in shas:
                    refs[sha] = refs.get(sha, 0) + 1
            total = sum(o[1] for o in objects.values()) + sum(e[2] for e in entries)

            def drop_object(sha: str) -> int:
                path, size, _ = objects.pop(sha)
                try:
                    if now - os.stat(path).st_mtime <= keep_seconds:  # used again since the scan
                        objects[sha] = (path, size, now)
                        return 0
                except OSError:
                    return size  # already gone
                _remove(path)
                result["objects_removed"] += 1
                return size

            for sha in [s for s, o in objects.items() if not refs.get(s) and now - o[2] > keep_seconds]:
                freed = drop_object(sha)
                total -= freed
                result["bytes_freed"] += freed
            for mtime, path, size, shas in sorted(entries):  # least recently used first
                if total <= limit or now - mtime <= keep_seconds:
                    break  # small enough, or everything left was used in the last two hours
                _remove(path)
                total -= size
                result["bytes_freed"] += size
                result["entries_removed"] += 1
                for sha in shas:
                    refs[sha] -= 1
                    if refs[sha] == 0 and sha in objects and now - objects[sha][2] > keep_seconds:
                        freed = drop_object(sha)
                        total -= freed
                        result["bytes_freed"] += freed
            result["bytes"] = total
            atomic_write(os.path.join(self.root, "pruned"), str(now).encode())
            return result
        finally:
            _unlock(lock)

    def maybe_prune(self) -> Optional[Dict]:
        """``prune`` at most once per ``PRUNE_EVERY`` seconds (stamp file ``pruned``) - a run only stats one file."""
        try:
            if time.time() - os.stat(os.path.join(self.root, "pruned")).st_mtime < PRUNE_EVERY:
                return None
        except OSError:
            pass
        try:
            return self.prune()
        except OSError:
            return None


_DEFAULT = object()


class OutputCache:
    """``<folder>/.cubegen_cache.json`` plus the shared ``Store``. ``enabled=False`` (``--force``) never reuses but
    still records. ``store``: a ``Store``, None (folder only) or the default (``Store.default()``)."""

    def __init__(self, folder: str, enabled: bool = True, store=_DEFAULT):
        self.folder = os.path.abspath(folder)
        self.path = os.path.join(self.folder, CACHE_NAME)
        self.enabled = enabled
        self.store: Optional[Store] = Store.default() if store is _DEFAULT else store
        self.entries: Dict[str, Dict] = {}
        self.index: Dict[str, List] = {}  # relative path -> [size, mtime_ns, content hash] of input images (previews)
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("format") == FORMAT:
                self.entries = dict(data.get("entries") or {})
                self.index = dict(data.get("index") or {})
            elif data.get("format") == 1:  # 0.15-0.24: absolute paths; its index held file (not content) hashes
                self.entries = {self._name_v1(n): self._entry_v1(e) for n, e in (data.get("entries") or {}).items()}
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        self.hits = 0
        self.shared = 0  # hits copied from the shared store

    # --- paths ---

    def rel(self, path: str) -> str:
        """``path`` relative to the folder ("/" separated); absolute only on another drive (Windows)."""
        try:
            return os.path.relpath(os.path.abspath(path), self.folder).replace(os.sep, "/")
        except ValueError:  # pragma: no cover - Windows, other drive
            return os.path.abspath(path)

    def abs(self, rel: str) -> str:
        return os.path.normpath(os.path.join(self.folder, rel))

    def _name_v1(self, name: str) -> str:
        prefix, sep, rest = name.partition(":")
        return f"{prefix}:{self.rel(rest)}" if sep and os.path.isabs(rest) else name

    def _entry_v1(self, entry: Dict) -> Dict:
        return {"key": entry.get("key"), "data": entry.get("data"),
                "files": {self.rel(p): h for p, h in (entry.get("files") or {}).items()},
                "stats": {self.rel(p): s for p, s in (entry.get("stats") or {}).items()}}

    # --- entries ---

    def _valid(self, entry: Dict) -> bool:
        stats = entry.get("stats", {})
        try:
            for rel, digest in entry.get("files", {}).items():
                path = self.abs(rel)
                if stats.get(rel) == file_state(path):
                    continue  # same size and time as when it was hashed: not read again
                if file_hash(path) != digest:
                    return False
        except OSError:
            return False
        return True

    def _record(self, name: str, key: str, hashes: Dict[str, str], data) -> Dict:
        self.entries[name] = {"key": key, "files": {self.rel(p): h for p, h in sorted(hashes.items())},
                              "stats": {self.rel(p): file_state(p) for p in sorted(hashes)}, "data": data}
        return self.entries[name]

    @staticmethod
    def _targets(place: Place, roles: Iterable[str]) -> Optional[Dict[str, str]]:
        roles = list(roles)
        if isinstance(place, dict):
            return dict(place) if set(place) == set(roles) else None
        out = {}
        for role in roles:
            clean = os.path.normpath(role)
            if os.path.isabs(clean) or clean == ".." or clean.startswith(".." + os.sep):
                return None  # a role never leaves its directory
            out[role] = os.path.join(place, clean)
        return out

    def get(self, name: str, key: str, place: Place = None) -> Optional[Dict]:
        """The entry (``{"key", "files", "data"}``) when this folder's files are current; else, with ``place``, the
        files of ``key`` copied from the shared store to ``place``; else None."""
        if not self.enabled:
            return None
        entry = self.entries.get(name)
        if entry and entry.get("key") == key and self._valid(entry):
            self.hits += 1
            return entry
        if place is None or self.store is None:
            return None
        found = self.store.lookup(key)
        targets = self._targets(place, found["files"]) if found else None
        if not targets:
            return None
        for role, sha in found["files"].items():
            path = targets[role]
            try:  # the same content may already be there (written under another key): keep it, Unity re-imports less
                if os.path.getsize(path) == os.path.getsize(self.store.object_path(sha)) and file_hash(path) == sha:
                    continue
            except OSError:
                pass
            if not self.store.fetch(sha, path):
                return None
        self.hits += 1
        self.shared += 1
        return self._record(name, key, {targets[r]: sha for r, sha in found["files"].items()}, found.get("data"))

    def put(self, name: str, key: str, files: Iterable[str], data=None, place: Place = None) -> None:
        """Record the files a step wrote; with ``place`` (as for ``get``) also in the shared store."""
        hashes = {os.path.abspath(p): file_hash(p) for p in set(files)}
        self._record(name, key, hashes, data)
        if place is None or self.store is None:
            return
        if isinstance(place, dict):
            roles = {role: os.path.abspath(path) for role, path in place.items()}
            if set(roles.values()) != set(hashes):
                return
        else:
            anchor = os.path.abspath(place)
            roles = {os.path.relpath(p, anchor).replace(os.sep, "/"): p for p in hashes}
            if any(r == ".." or r.startswith("../") for r in roles):
                return  # not below the place: folder-bound only
        try:
            self.store.put(key, {role: (path, hashes[path]) for role, path in roles.items()}, data,
                           step=name.partition(":")[0])
        except OSError:  # a read-only or full cache disk never fails a run: folder index only from here on
            self.store = None

    def digest(self, path: str) -> str:
        """Content hash of an input image (a preview, ``png_content_hash``), read only when its size or time changed
        since the last call."""
        rel = self.rel(path)
        state = file_state(path)
        known = self.index.get(rel)
        if known and known[:2] == state:
            return known[2]
        value = png_content_hash(path)
        self.index[rel] = state + [value]
        return value

    def prune(self, prefix: str, keep) -> None:
        """Forget entries ``<prefix><x>`` whose ``x`` is not in ``keep`` (e.g. icons of models no longer built here)."""
        keep = {prefix + k for k in keep}
        for name in [n for n in self.entries if n.startswith(prefix) and n not in keep]:
            del self.entries[name]

    def save(self) -> None:
        text = json.dumps({"format": FORMAT, "entries": self.entries, "index": self.index}, indent=1, sort_keys=True)
        atomic_write(self.path, text.encode("utf-8"))
        if self.store is not None:
            self.store.maybe_prune()
