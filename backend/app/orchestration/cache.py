"""
SatQuery AI — Deterministic Result Cache & Idempotency Engine
Caches expensive model inferences using SHA-256 fingerprinting over inputs, queries,
model checkpoints, and configuration parameters.
"""
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import OrderedDict
from backend.app.logging import logger


class DeterministicCache:
    """
    In-memory LRU cache with SHA-256 idempotency key calculation.
    """
    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    @classmethod
    def compute_file_hash(cls, file_path: str) -> str:
        """Computes SHA-256 hash of file content."""
        p = Path(file_path)
        if not p.exists():
            return "missing_file"
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def compute_cache_key(
        cls,
        image_paths: List[str],
        query: str,
        capability_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Constructs composite idempotency hash:
        SHA256(image_hashes + query + capability + parameters)
        """
        hasher = hashlib.sha256()
        for p in sorted(image_paths):
            hasher.update(cls.compute_file_hash(p).encode("utf-8"))
        hasher.update(query.strip().lower().encode("utf-8"))
        hasher.update(capability_id.encode("utf-8"))
        if parameters:
            hasher.update(str(sorted(parameters.items())).encode("utf-8"))
        return hasher.hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached result if present, bumping to most recently used."""
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            logger.info(f"Deterministic cache hit for key: {cache_key[:12]}...")
            return self._cache[cache_key]
        return None

    def put(self, cache_key: str, value: Dict[str, Any]) -> None:
        """Stores result in cache, evicting oldest item if exceeding max_size."""
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
        self._cache[cache_key] = value
        if len(self._cache) > self.max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"Deterministic cache evicted key: {evicted_key[:12]}...")

    def clear(self) -> None:
        self._cache.clear()


orchestration_cache = DeterministicCache()
