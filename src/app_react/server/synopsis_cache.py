"""Tiny bounded TTL cache for AI synopsis results.

Synopsis generation calls Claude via ai_query (several seconds). The result is
stable for a given case over a short window, so caching it makes re-opening the
same claim/underwriting case instant during a demo. Bounded LRU so a long-lived
process can't grow without limit.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict

_CACHE: "OrderedDict[str, tuple[float, dict]]" = OrderedDict()
_LOCK = threading.Lock()
_TTL = 900.0      # 15 minutes — plenty for a demo session
_MAX = 256


def get(key: str) -> dict | None:
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and (time.time() - hit[0]) < _TTL:
            _CACHE.move_to_end(key)
            return hit[1]
    return None


def put(key: str, value: dict) -> None:
    with _LOCK:
        _CACHE[key] = (time.time(), value)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _MAX:
            _CACHE.popitem(last=False)
