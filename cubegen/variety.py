"""Near-duplicate detection: pick variants that actually look different (``--unique``).

Two variants count as the same when they have the same parts, the same
materials and triangle counts per part, and every size (whole model and each
part) differs by less than ``max(3 cm, 8 %)``. Such pairs look alike at game
distance even though their seeds differ.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

ABS_TOL = 0.03  # metres
REL_TOL = 0.08


class Signature:
    __slots__ = ("structure", "sizes")

    def __init__(self, structure: Tuple, sizes: Tuple[float, ...]):
        self.structure = structure  # (part, parent, materials, triangles) per part
        self.sizes = sizes          # whole model + every part: x, y, z extents and pivot offsets


def signature(asset) -> Signature:
    structure, sizes = [], []
    lo, hi = asset.bbox()
    sizes += [hi[i] - lo[i] for i in range(3)]
    for o in asset.objects:
        if o.mesh is None:
            structure.append((o.name, o.parent, (), 0))
            sizes += list(o.pivot)
            continue
        structure.append((o.name, o.parent, tuple(sorted(set(o.mesh.roles))), o.mesh.triangle_count()))
        (x0, y0, z0), (x1, y1, z1) = o.mesh.bbox()
        sizes += [x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]
    return Signature(tuple(structure), tuple(sizes))


def similar(a: Signature, b: Signature, abs_tol: float = ABS_TOL, rel_tol: float = REL_TOL) -> bool:
    if a.structure != b.structure or len(a.sizes) != len(b.sizes):
        return False
    return all(abs(x - y) <= max(abs_tol, rel_tol * max(abs(x), abs(y))) for x, y in zip(a.sizes, b.sizes))


def pick_unique(count: int, build: Callable[[int], object], start: int = 0, max_tries: Optional[int] = None,
                taken: Sequence[Signature] = ()) -> Tuple[List[int], int]:
    """Indices ``start, start+1, ...`` of ``count`` variants that differ from each other.

    ``build(index)`` returns the asset of a variant. Gives up after ``max_tries``
    indices (default ``20 * count + 20``) and returns what it found, plus the
    number of indices it looked at.
    """
    limit = max_tries if max_tries is not None else 20 * count + 20
    chosen: List[int] = []
    seen: List[Signature] = list(taken)
    index = start
    while len(chosen) < count and index < start + limit:
        sig = signature(build(index))
        if not any(similar(sig, other) for other in seen):
            chosen.append(index)
            seen.append(sig)
        index += 1
    return chosen, index - start


def report(types: Sequence[str], build: Callable[[str, int], object], count: int = 12) -> Dict[str, int]:
    """How many of the first ``count`` indices per type are distinct (for the quality report)."""
    result = {}
    for t in types:
        found, _ = pick_unique(count, lambda i, t=t: build(t, i), max_tries=count)
        result[t] = len(found)
    return result


__all__ = ["Signature", "signature", "similar", "pick_unique", "report"]
