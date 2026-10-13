"""Skip ImageMagick work whose inputs did not change: texture sets, icons, the contact sheet, the material swatch.

An entry remembers the key of its inputs and the SHA-256 of every file it wrote. It is only reused when the key
matches and every file still exists with exactly that content - a file changed or deleted by someone else (another
run writing into a shared textures folder, a hand edit) is rebuilt. This needs byte-identical output for identical
input, which is why every ImageMagick call excludes the PNG time stamps (``imagemagick.REPRODUCIBLE``).

0.21.0: an index of size and modification time per file (``stats`` of an entry, ``index`` of the cache) - a file
whose size and time are those of its last hash is not read again (a rerun of the catalog read every preview and
every written PNG in full only to confirm it was unchanged). A changed file has a new time and is hashed as before.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Iterable, List, Optional

CACHE_NAME = ".cubegen_cache.json"  # leading dot: Unity ignores the file inside Assets/
FORMAT = 1


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


class OutputCache:
    """``<folder>/.cubegen_cache.json``; ``enabled=False`` (``--force``) never reuses but still records."""

    def __init__(self, folder: str, enabled: bool = True):
        self.path = os.path.join(folder, CACHE_NAME)
        self.enabled = enabled
        self.entries: Dict[str, Dict] = {}
        self.index: Dict[str, List] = {}  # path -> [size, mtime_ns, sha256] of files only read (previews)
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("format") == FORMAT:
                self.entries = dict(data.get("entries") or {})
                self.index = dict(data.get("index") or {})
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        self.hits = 0

    def get(self, name: str, key: str) -> Optional[Dict]:
        """The stored entry (``{"key", "files", "data"}``) when it is still valid, else None."""
        entry = self.entries.get(name)
        if not self.enabled or not entry or entry.get("key") != key:
            return None
        stats = entry.get("stats", {})
        try:
            for path, digest in entry.get("files", {}).items():
                if stats.get(path) == file_state(path):
                    continue  # same size and time as when it was hashed: not read again
                if file_hash(path) != digest:
                    return None
        except OSError:
            return None
        self.hits += 1
        return entry

    def put(self, name: str, key: str, files: Iterable[str], data=None) -> None:
        paths = sorted(set(files))
        self.entries[name] = {"key": key, "files": {p: file_hash(p) for p in paths},
                              "stats": {p: file_state(p) for p in paths}, "data": data}

    def digest(self, path: str) -> str:
        """SHA-256 of an input file (a preview), read only when its size or time changed since the last call."""
        state = file_state(path)
        known = self.index.get(path)
        if known and known[:2] == state:
            return known[2]
        value = file_hash(path)
        self.index[path] = state + [value]
        return value

    def prune(self, prefix: str, keep) -> None:
        """Forget entries ``<prefix><x>`` whose ``x`` is not in ``keep`` (e.g. icons of models no longer built here)."""
        keep = {prefix + k for k in keep}
        for name in [n for n in self.entries if n.startswith(prefix) and n not in keep]:
            del self.entries[name]

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"format": FORMAT, "entries": self.entries, "index": self.index}, fh, indent=1, sort_keys=True)
