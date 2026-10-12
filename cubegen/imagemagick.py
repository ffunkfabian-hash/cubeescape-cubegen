"""ImageMagick wrapper: inventory icons, contact sheets and the material swatch.

Works with ImageMagick 7 (``magick``) and ImageMagick 6 (``convert`` /
``montage``).
"""

from __future__ import annotations

import copy
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Sequence

from .materials import MATERIALS, to_hex


class ImageMagickError(RuntimeError):
    pass


# Without this every PNG carries its creation time (tIME chunk, date:create / date:modify text): same pixels,
# different bytes on every run - Unity re-imports unchanged files and file hashes can't be cache keys.
REPRODUCIBLE = ("-define", "png:exclude-chunks=date,time")


# Apps started from the macOS Finder (e.g. Blender running the add-on) don't see the
# shell's PATH, so Homebrew / MacPorts installs are looked up explicitly.
_EXTRA_DIRS = ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin")


def _which(name: str) -> Optional[str]:
    found = shutil.which(name)
    if found:
        return found
    for d in _EXTRA_DIRS:
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


class ImageMagick:
    env: Optional[Dict[str, str]] = None  # environment of the calls (None = inherit)

    def __init__(self, binary: Optional[str] = None):
        binary = binary or os.environ.get("CUBEGEN_MAGICK")
        if binary:
            path = shutil.which(binary) or binary
            name = os.path.basename(path).lower()
            if name.startswith("magick"):
                self.convert = [path]
                self.montage = [path, "montage"]
            else:
                self.convert = [path]
                sibling = os.path.join(os.path.dirname(path), "montage")
                self.montage = [sibling if os.path.exists(sibling) else "montage"]
        elif _which("magick"):
            self.convert = [_which("magick")]
            self.montage = [_which("magick"), "montage"]
        elif _which("convert") and _which("montage"):
            self.convert = [_which("convert")]
            self.montage = [_which("montage")]
        else:
            raise ImageMagickError(
                "ImageMagick not found. Install it (https://imagemagick.org) or pass --magick /path/to/magick"
            )

    def single_threaded(self) -> "ImageMagick":
        """A copy whose calls use one OpenMP thread - for calls running in parallel: the thread pools of parallel
        ImageMagick processes wait for each other (robot generator: montage 3.8 s -> 1.6 s). Same pixels."""
        im = copy.copy(self)
        im.env = dict(os.environ, MAGICK_THREAD_LIMIT="1")
        return im

    # ------------------------------------------------------------------
    def run(self, args: Sequence[str], montage: bool = False) -> str:
        args = list(args)
        settings = [] if args[:1] == ["-version"] else list(REPRODUCIBLE)
        cmd = list(self.montage if montage else self.convert) + settings + args
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.env)
        if proc.returncode != 0:
            raise ImageMagickError(f"ImageMagick failed ({' '.join(cmd[:3])} ...):\n{proc.stderr.strip()}")
        return proc.stdout

    def version(self) -> str:
        out = self.run(["-version"])
        return out.splitlines()[0] if out else "unknown"

    # ------------------------------------------------------------------
    # materials
    # ------------------------------------------------------------------
    def material_swatch(self, path: str, size: int = 96) -> str:
        """Labelled overview of the Cube Escape materials (for design reviews)."""
        names = list(MATERIALS)
        layout = ["-tile", "7x", "-geometry", f"{size}x{size}+6+6", "-depth", "8", path]
        swatches: List[str] = ["-size", f"{size}x{size}"]
        for name in names:
            swatches += ["-label", f"{name}\n{to_hex(name)}", f"xc:{to_hex(name)}"]
        try:
            self.run(["-background", "#1e1e24", "-fill", "#e8e8e8", "-pointsize", "11"] + swatches + layout,
                     montage=True)
        except ImageMagickError:
            # no usable font -> unlabelled swatch
            plain = ["-size", f"{size}x{size}"] + [f"xc:{to_hex(n)}" for n in names]
            self.run(["-background", "#1e1e24"] + plain + layout, montage=True)
        return path

    # ------------------------------------------------------------------
    # previews
    # ------------------------------------------------------------------
    def make_icon(self, src: str, dst: str, size: int = 128, background: Optional[str] = None,
                  radius: int = 16, shadow: bool = True) -> str:
        """Square inventory icon: trimmed, centred, optional drop shadow and tile."""
        inner = max(8, int(size * 0.82))
        args: List[str] = []
        if background:
            args += ["-size", f"{size}x{size}", "xc:none", "-fill", background,
                     "-draw", f"roundrectangle 0,0,{size - 1},{size - 1},{radius},{radius}", "("]
        args += [src, "-trim", "+repage", "-resize", f"{inner}x{inner}"]
        if shadow:
            args += ["(", "+clone", "-background", "black", "-shadow", "55x3+0+3", ")",
                     "+swap", "-background", "none", "-layers", "merge", "+repage"]
        args += ["-background", "none", "-gravity", "center", "-extent", f"{size}x{size}"]
        if background:
            args += [")", "-gravity", "center", "-composite"]
        args.append(f"PNG32:{dst}")
        self.run(args)
        return dst

    def contact_sheet(self, images: Sequence[str], labels: Sequence[str], dst: str, columns: int = 6,
                      cell: int = 192, background: str = "#1e1e24", title: Optional[str] = None,
                      workers: int = 0) -> str:
        """Grid of all previews with names - quick visual review of a batch.

        The labels are the expensive part (about 70 ms each: 186 previews took 15-20 s), so a big sheet is made as
        blocks of ``SHEET_ROWS`` rows at the same time and stacked - the same pixels as one montage (checked with
        ``compare -metric AE``), 2 s instead of 20. ``workers``: 0 = one per core, 1 = one montage."""
        columns = max(1, min(columns, len(images)))
        block = columns * SHEET_ROWS
        workers = min(workers or os.cpu_count() or 1, -(-len(images) // block))
        if workers > 1:
            single = self.single_threaded()
            with tempfile.TemporaryDirectory(prefix="cubegen_sheet_") as work:
                parts = [os.path.join(work, f"block_{k:03d}.png") for k in range(0, len(images), block)]
                jobs = [(images[k:k + block], labels[k:k + block], part, title if k == 0 else None)
                        for k, part in zip(range(0, len(images), block), parts)]
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    list(pool.map(lambda j: single._montage(j[0], j[1], j[2], columns, cell, background, j[3]),
                                  jobs))
                self.run(parts + ["-background", background, "-append", "-depth", "8", dst])
            return dst
        return self._montage(images, labels, dst, columns, cell, background, title)

    def _montage(self, images, labels, dst, columns, cell, background, title) -> str:
        base = ["-background", background, "-fill", "#e8e8e8", "-pointsize", "13"]
        tail = ["-tile", f"{columns}x", "-geometry", f"{cell}x{cell}+8+8", "-depth", "8"]
        titled = tail + (["-title", title] if title else [])
        labelled: List[str] = []
        for img, label in zip(images, labels):
            labelled += ["-label", label, img]
        try:
            self.run(base + labelled + titled + [dst], montage=True)
        except ImageMagickError:
            # no usable font -> unlabelled sheet
            self.run(["-background", background] + list(images) + tail + [dst], montage=True)
        return dst


SHEET_ROWS = 4  # rows per block of a big contact sheet


def find_imagemagick(binary: Optional[str] = None) -> Optional[ImageMagick]:
    try:
        return ImageMagick(binary)
    except ImageMagickError:
        return None
