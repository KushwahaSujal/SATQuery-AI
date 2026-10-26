"""Puts a bi-temporal image pair in time order, earlier first, from its filenames.

The change models read the first image as T1. The order the client sends is not reliable: file
pickers return multi-selections alphabetically and POST /jobs/{id}/reuse-source sorts, so
"after.png" arrives before "before.png". Reversed, the same LEVIR scene measured 5.06 % changed
instead of 11.35 % (project/qna.md Q-061).

Only a clear signal reorders: whole filename tokens (before/after, pre/post, t1/t2, old/new …) or a
date/year in both names. Anything else keeps the client's order unchanged.
"""
import re
from pathlib import Path
from typing import List, Optional, Sequence, TypeVar

P = TypeVar("P", str, Path)

_EARLIER = {"before", "pre", "t1", "t0", "old", "older", "earlier", "past", "prev", "previous", "first"}
_LATER = {"after", "post", "t2", "new", "newer", "later", "current", "latest", "second"}
_DATE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?:[-_.]?(\d{2})(?:[-_.]?(\d{2}))?)?(?!\d)")


def _tokens(name: str) -> set:
    return set(re.split(r"[^a-z0-9]+", Path(name).stem.lower())) - {""}


def _rank(name: str) -> Optional[int]:
    """0 = reads as the earlier image, 1 = the later one, None = no signal or both."""
    t = _tokens(name)
    early, late = bool(t & _EARLIER), bool(t & _LATER)
    return 0 if early and not late else 1 if late and not early else None


def _date(name: str) -> Optional[tuple]:
    m = _DATE.search(Path(name).stem)
    return tuple(int(g or 0) for g in m.groups()) if m else None


def chronological(paths: Sequence[P]) -> List[P]:
    """Return a two-image pair earlier-first when the names say so; any other input unchanged."""
    paths = list(paths)
    if len(paths) != 2:
        return paths
    a, b = (Path(p).name for p in paths)
    ra, rb = _rank(a), _rank(b)
    if ra is not None and rb is not None:
        swap = ra > rb
    elif ra is not None or rb is not None:
        swap = ra == 1 or rb == 0
    else:
        da, db = _date(a), _date(b)
        swap = bool(da and db and da > db)
    return paths[::-1] if swap else paths
