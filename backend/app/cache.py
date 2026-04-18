import asyncio
import time
from typing import Any

class AsyncTTLCache:
    """In-memory Time-To-Live Cache for async applications."""
    def __init__(self, ttl: int = 30):
        self.ttl = ttl
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            if key in self._cache:
                timestamp, value = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        _ttl = ttl if ttl is not None else self.ttl
        async with self._lock:
            self._cache[key] = (time.time() - self.ttl + _ttl, value)

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
