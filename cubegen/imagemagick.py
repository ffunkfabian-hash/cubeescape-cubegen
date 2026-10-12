"""ImageMagick wrapper: inventory icons, contact sheets and the material swatch.

Works with ImageMagick 7 (``magick``) and ImageMagick 6 (``convert`` /
``montage``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Optional, Sequence

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

    # ------------------------------------------------------------------
    def run(self, args: Sequence[str], montage: bool = False) -> str:
        args = list(args)
        settings = [] if args[:1] == ["-version"] else list(REPRODUCIBLE)
        cmd = list(self.montage if montage else self.convert) + settings + args
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
                      cell: int = 192, background: str = "#1e1e24", title: Optional[str] = None) -> str:
        """Grid of all previews with names - quick visual review of a batch."""
        columns = max(1, min(columns, len(images)))
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


def find_imagemagick(binary: Optional[str] = None) -> Optional[ImageMagick]:
    try:
        return ImageMagick(binary)
    except ImageMagickError:
        return None
