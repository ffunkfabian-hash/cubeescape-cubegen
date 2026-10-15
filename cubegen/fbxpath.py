"""Rewrite the folder-bound strings of a binary FBX (pure Python, 0.26.0 "Stockpile").

Blender's FBX exporter writes the absolute path of every texture (``Texture.FileName``, ``Video.Filename`` and the
video's ``Path`` property) - the only part of an FBX that depends on the folder it was written to
(``RelativeFilename`` is relative to the FBX). Time stamps and object IDs differ between any two exports anyway. To
reuse an export from the shared cache in another folder, :func:`canonical` replaces such paths by a token
(``<cubegen:textures>/MTA_Crate_000_Albedo.png``) and :func:`concrete` puts the new folder in - every other byte
stays as Blender wrote it.

Binary FBX: a header (27 bytes, version at 23), node records (end offset, property count, property list length, name,
properties, child records, a null record after children), a null record, then a footer whose padding depends on the
file length. Changing a string changes lengths and offsets, so the records are written anew; the footer is rebuilt
the way Blender writes it. :func:`parse` checks that writing the unchanged tree gives the input byte for byte -
anything else (an unknown layout) raises ``ValueError`` and the caller leaves the file out of the cache.
"""

from __future__ import annotations

import struct
from typing import Callable, Dict, List, Optional, Tuple

MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
HEADER = 27
FOOTER_TAIL = 140  # version (4) + 120 zero bytes + 16 bytes of magic
FOOTER_HEAD = 20   # footer id (16) + 4 zero bytes
_SIZES = {"Y": 2, "C": 1, "I": 4, "F": 4, "D": 8, "L": 8}
_ARRAYS = "fdlib"


class Record:
    __slots__ = ("name", "props", "children", "sentinel")

    def __init__(self, name: bytes, props: List[Tuple[str, bytes]], children: List["Record"], sentinel: bool):
        self.name, self.props, self.children, self.sentinel = name, props, children, sentinel


def _props(data: bytes, pos: int, count: int) -> Tuple[List[Tuple[str, bytes]], int]:
    """Properties as (type code, raw bytes after the code); strings ('S', 'R') without their length."""
    out = []
    for _ in range(count):
        code = chr(data[pos])
        pos += 1
        if code in _SIZES:
            size = _SIZES[code]
            out.append((code, data[pos:pos + size]))
            pos += size
        elif code in _ARRAYS:
            (clen,) = struct.unpack_from("<I", data, pos + 8)
            out.append((code, data[pos:pos + 12 + clen]))
            pos += 12 + clen
        elif code in "SR":
            (length,) = struct.unpack_from("<I", data, pos)
            out.append((code, data[pos + 4:pos + 4 + length]))
            pos += 4 + length
        else:
            raise ValueError(f"unknown FBX property type {code!r}")
    return out, pos


def _record(data: bytes, pos: int, wide: bool) -> Tuple[Optional[Record], int]:
    head = 25 if wide else 13
    end, count, _ = struct.unpack_from("<QQQ" if wide else "<III", data, pos)
    if end == 0:
        return None, pos + head
    name_len = data[pos + head - 1]
    pos += head
    name = data[pos:pos + name_len]
    pos += name_len
    props, pos = _props(data, pos, count)
    children: List[Record] = []
    sentinel = False
    while pos < end:
        child, pos = _record(data, pos, wide)
        if child is None:
            sentinel = True
            break
        children.append(child)
    if pos != end:
        raise ValueError("FBX record does not end at its end offset")
    return Record(name, props, children, sentinel), end


class Document:
    """A parsed binary FBX: header, top-level records, footer parts."""

    def __init__(self, version: int, records: List[Record], footer_head: bytes, footer_tail: bytes):
        self.version, self.records = version, records
        self.footer_head, self.footer_tail = footer_head, footer_tail

    @property
    def wide(self) -> bool:
        return self.version >= 7500

    def strings(self) -> List[bytes]:
        found: List[bytes] = []

        def walk(record: Record):
            found.extend(raw for code, raw in record.props if code == "S")
            for child in record.children:
                walk(child)
        for record in self.records:
            walk(record)
        return found

    def map_strings(self, func: Callable[[bytes], bytes]) -> int:
        """Replace every string property ``s`` by ``func(s)``; returns how many changed."""
        changed = [0]

        def walk(record: Record):
            for i, (code, raw) in enumerate(record.props):
                if code == "S":
                    new = func(raw)
                    if new != raw:
                        record.props[i] = (code, new)
                        changed[0] += 1
            for child in record.children:
                walk(child)
        for record in self.records:
            walk(record)
        return changed[0]

    def to_bytes(self) -> bytes:
        out = bytearray(MAGIC + struct.pack("<I", self.version))
        head = 25 if self.wide else 13
        layout = "<QQQ" if self.wide else "<III"

        def write(record: Record):
            start = len(out)
            out.extend(b"\0" * (head - 1))
            out.append(len(record.name))
            out.extend(record.name)
            props_start = len(out)
            for code, raw in record.props:
                out.extend(code.encode("ascii"))
                if code in "SR":
                    out.extend(struct.pack("<I", len(raw)))
                out.extend(raw)
            props_len = len(out) - props_start
            for child in record.children:
                write(child)
            if record.sentinel:
                out.extend(b"\0" * head)
            struct.pack_into(layout, out, start, len(out), len(record.props), props_len)

        for record in self.records:
            write(record)
        out.extend(b"\0" * head)
        out.extend(self.footer_head)
        offset = len(out)
        pad = ((offset + 15) & ~15) - offset  # Blender's rule (io_scene_fbx encode_bin): 1..16 zero bytes
        out.extend(b"\0" * (pad or 16))
        out.extend(self.footer_tail)
        return bytes(out)


def parse(data: bytes) -> Document:
    """Parse ``data``; ``ValueError`` unless writing the tree again gives exactly ``data``."""
    if not data.startswith(MAGIC) or len(data) < HEADER + FOOTER_HEAD + FOOTER_TAIL:
        raise ValueError("not a binary FBX")
    (version,) = struct.unpack_from("<I", data, 23)
    wide = version >= 7500
    pos, records = HEADER, []
    while True:
        record, pos = _record(data, pos, wide)
        if record is None:
            break
        records.append(record)
    doc = Document(version, records, data[pos:pos + FOOTER_HEAD], data[-FOOTER_TAIL:])
    if doc.to_bytes() != data:
        raise ValueError("FBX layout not understood (writing it again changes bytes)")
    return doc


# --- folder-bound paths --------------------------------------------------------------------------------------------

def _encode(path: str) -> bytes:
    return path.encode("utf-8")


def _swap(value: bytes, pairs: List[Tuple[bytes, bytes]]) -> bytes:
    """``value`` with the first matching prefix of ``pairs`` (old, new) replaced - only whole path components."""
    for old, new in pairs:
        if value == old:
            return new
        if value.startswith(old) and value[len(old):len(old) + 1] in (b"/", b"\\"):
            return new + value[len(old):]
    return value


def canonical(data: bytes, folders: Dict[str, str]) -> Tuple[bytes, int]:
    """``data`` with every string that starts with one of ``folders`` (``{token: absolute folder}``) starting with
    ``<cubegen:token>`` instead; returns (bytes, strings changed). Longer folders first (``models/Textures`` before
    ``models``)."""
    doc = parse(data)
    pairs = sorted(((_encode(path.rstrip("/\\")), _encode(f"<cubegen:{token}>")) for token, path in folders.items()),
                   key=lambda p: -len(p[0]))
    changed = doc.map_strings(lambda s: _swap(s, pairs))
    return doc.to_bytes(), changed


def concrete(data: bytes, folders: Dict[str, str]) -> bytes:
    """The inverse of :func:`canonical`: ``<cubegen:token>`` back to the folder of this run."""
    doc = parse(data)
    pairs = [(_encode(f"<cubegen:{token}>"), _encode(path.rstrip("/\\"))) for token, path in folders.items()]
    doc.map_strings(lambda s: _swap(s, pairs))
    return doc.to_bytes()


def tokens(data: bytes) -> List[str]:
    """The tokens a canonical FBX still needs (``["textures"]``)."""
    found = set()
    for value in parse(data).strings():
        if value.startswith(b"<cubegen:"):
            end = value.find(b">")
            if end > 0:
                found.add(value[len(b"<cubegen:"):end].decode("utf-8", "replace"))
    return sorted(found)


#: what differs between any two exports of the same scene: Blender's clock (CreationTimeStamp, CreationTime)
VOLATILE_RECORDS = (b"CreationTimeStamp", b"CreationTime")


def normalized(data: bytes, folders: Dict[str, str]):
    """A comparable form of an FBX: the record tree with folders as tokens, object IDs numbered in the order they
    are defined (Blender draws new ones for every export) and without the time stamps - two exports of the same
    scene in two folders give the same value (tests, the release comparison)."""
    doc = parse(canonical(data, folders)[0])
    ids: Dict[bytes, int] = {}
    for record in doc.records:
        if record.name in (b"Objects", b"Documents"):
            for child in record.children:
                if child.props and child.props[0][0] == "L":
                    ids.setdefault(child.props[0][1], len(ids))

    def form(record: Record):
        if record.name in VOLATILE_RECORDS:
            return (record.name, "volatile")
        props = tuple(("id", ids[raw]) if code == "L" and raw in ids else (code, raw) for code, raw in record.props)
        return (record.name, props, tuple(form(child) for child in record.children), record.sentinel)
    return tuple(form(record) for record in doc.records)
