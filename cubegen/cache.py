"""Skip ImageMagick work whose inputs did not change: texture sets, icons, the contact sheet, the material swatch.

An entry remembers the key of its inputs and the SHA-256 of every file it wrote. It is only reused when the key
matches and every file still exists with exactly that content - a file changed or deleted by someone else (another
run writing into a shared textures folder, a hand edit) is rebuilt. This needs byte-identical output for identical
input, which is why every ImageMagick call excludes the PNG time stamps (``imagemagick.REPRODUCIBLE``).
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Iterable, Optional

CACHE_NAME = ".cubegen_cache.json"  # leading dot: Unity ignores the file inside Assets/
FORMAT = 1


def input_key(*parts) -> str:
    """Stable hash of JSON-serialisable inputs."""
    text = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("format") == FORMAT:
                self.entries = dict(data.get("entries") or {})
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        self.hits = 0

    def get(self, name: str, key: str) -> Optional[Dict]:
        """The stored entry (``{"key", "files", "data"}``) when it is still valid, else None."""
        entry = self.entries.get(name)
        if not self.enabled or not entry or entry.get("key") != key:
            return None
        try:
            if any(file_hash(path) != digest for path, digest in entry.get("files", {}).items()):
                return None
        except OSError:
            return None
        self.hits += 1
        return entry

    def put(self, name: str, key: str, files: Iterable[str], data=None) -> None:
        self.entries[name] = {"key": key, "files": {p: file_hash(p) for p in sorted(set(files))}, "data": data}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"format": FORMAT, "entries": self.entries}, fh, indent=1, sort_keys=True)
