"""TTL cache for folder listing results"""
import time
from typing import Any, Dict, List, Optional, Tuple


class ListingCache:
    """In-memory cache for Spaces folder listings keyed by prefix."""

    def __init__(self, ttl_seconds: float = 60.0):
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, List[dict], List[dict]]] = {}

    def get(self, prefix: str) -> Optional[Tuple[List[dict], List[dict]]]:
        entry = self._store.get(prefix)
        if not entry:
            return None
        ts, folders, files = entry
        if time.time() - ts > self._ttl:
            del self._store[prefix]
            return None
        return folders, files

    def put(self, prefix: str, folders: List[dict], files: List[dict]) -> None:
        self._store[prefix] = (time.time(), folders, files)

    def invalidate(self, prefix: Optional[str] = None) -> None:
        if prefix is None:
            self._store.clear()
            return
        self._store.pop(prefix, None)
        # Also invalidate child prefixes
        keys_to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._store[k]
