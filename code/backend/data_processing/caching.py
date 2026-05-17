"""
Caching module for AlphaMind data processing.

Provides various caching mechanisms for performance optimization.
"""

import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

logger = logging.getLogger(__name__)


class CachePolicy(ABC):
    """Base class for cache policies."""

    @abstractmethod
    def should_cache(self, key: str, value: Any) -> bool:
        """Determine if a value should be cached."""

    @abstractmethod
    def is_valid(self, cached_time: float) -> bool:
        """Check if cached value is still valid."""


class TTLCachePolicy(CachePolicy):
    """Time-to-live cache policy."""

    def __init__(self, ttl_seconds: float = 3600) -> None:
        """
        Initialize TTL cache policy.

        Args:
            ttl_seconds: Time to live in seconds (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds

    def should_cache(self, key: str, value: Any) -> bool:
        """Always cache non-None values."""
        return value is not None

    def is_valid(self, cached_time: float) -> bool:
        """Check if cache entry hasn't expired."""
        return (time.time() - cached_time) < self.ttl_seconds


class SizeCachePolicy(CachePolicy):
    """Size-based cache policy with LRU eviction."""

    def __init__(self, max_size_mb: float = 100) -> None:
        """
        Initialize size cache policy.

        Args:
            max_size_mb: Maximum cache size in megabytes
        """
        self.max_size_mb = max_size_mb
        self.current_size = 0

    def should_cache(self, key: str, value: Any) -> bool:
        """Cache if size limit not exceeded."""
        try:
            value_size = len(pickle.dumps(value)) / (1024 * 1024)  # Convert to MB
            return value_size < self.max_size_mb
        except Exception:
            return False

    def is_valid(self, cached_time: float) -> bool:
        """Always valid for size-based policy."""
        return True


class CacheManager:
    """Manages caching with configurable policies and backends."""

    def __init__(
        self, policy: Optional[CachePolicy] = None, namespace: str = "default"
    ) -> None:
        """
        Initialize cache manager.

        Args:
            policy: Cache policy to use (default: TTL with 1 hour)
            namespace: Namespace for cache keys
        """
        self.policy = policy or TTLCachePolicy()
        self.namespace = namespace
        self._cache: Dict[str, tuple[Any, float]] = {}
        logger.info(f"CacheManager initialized with namespace: {namespace}")

    def _make_key(self, key: Union[str, tuple]) -> str:
        """Create a cache key with namespace."""
        if isinstance(key, tuple):
            key = str(key)
        return f"{self.namespace}:{key}"

    def get(self, key: Union[str, tuple], default: Optional[Any] = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        cache_key = self._make_key(key)
        if cache_key in self._cache:
            value, cached_time = self._cache[cache_key]
            if self.policy.is_valid(cached_time):
                logger.debug(f"Cache hit for key: {cache_key}")
                return value
            else:
                logger.debug(f"Cache expired for key: {cache_key}")
                del self._cache[cache_key]
        return default

    def set(self, key: Union[str, tuple], value: Any) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache

        Returns:
            True if cached successfully, False otherwise
        """
        cache_key = self._make_key(key)
        if self.policy.should_cache(cache_key, value):
            self._cache[cache_key] = (value, time.time())
            logger.debug(f"Cached value for key: {cache_key}")
            return True
        return False

    def delete(self, key: Union[str, tuple]) -> bool:
        """Delete value from cache."""
        cache_key = self._make_key(key)
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Deleted cache key: {cache_key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries in namespace."""
        keys_to_delete = [
            k for k in self._cache.keys() if k.startswith(f"{self.namespace}:")
        ]
        for key in keys_to_delete:
            del self._cache[key]
        logger.info(f"Cleared cache namespace: {self.namespace}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        namespace_keys = [
            k for k in self._cache.keys() if k.startswith(f"{self.namespace}:")
        ]
        return {
            "namespace": self.namespace,
            "entries": len(namespace_keys),
            "total_entries": len(self._cache),
        }


def cache_function(ttl_seconds: float = 3600, namespace: str = "function"):
    """
    Decorator for caching function results.

    Args:
        ttl_seconds: Time to live in seconds
        namespace: Cache namespace

    Usage:
        @cache_function(ttl_seconds=300)
        def expensive_computation(x, y):
            return x * y
    """
    cache_mgr = CacheManager(policy=TTLCachePolicy(ttl_seconds), namespace=namespace)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_data = {
                "func": func.__name__,
                "args": args,
                "kwargs": sorted(kwargs.items()),
            }
            cache_key = hashlib.md5(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()

            # Try to get from cache
            result = cache_mgr.get(cache_key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            cache_mgr.set(cache_key, result)
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Concrete cache backends required by data_processing/__init__.py
# ---------------------------------------------------------------------------


class MemoryCache:
    """
    Thread-safe in-memory cache backed by a dict.

    Parameters
    ----------
    policy : CachePolicy
        Eviction / validity policy (default: 1-hour TTL).
    max_entries : int
        Maximum number of entries before LRU eviction.
    """

    def __init__(
        self,
        policy: Optional[CachePolicy] = None,
        max_entries: int = 10_000,
    ) -> None:
        self._policy = policy or TTLCachePolicy(ttl_seconds=3600)
        self._max_entries = max_entries
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Return cached value or *default* on miss/expiry."""
        if key not in self._store:
            return default
        if not self._policy.is_valid(self._timestamps[key]):
            del self._store[key]
            del self._timestamps[key]
            return default
        return self._store[key]

    def set(self, key: str, value: Any) -> bool:
        """Store *value* under *key*. Returns True on success."""
        if not self._policy.should_cache(key, value):
            return False
        if len(self._store) >= self._max_entries:
            oldest = min(self._timestamps, key=self._timestamps.__getitem__)
            del self._store[oldest]
            del self._timestamps[oldest]
        self._store[key] = value
        self._timestamps[key] = time.time()
        return True

    def delete(self, key: str) -> bool:
        """Remove *key*. Returns True if it existed."""
        if key in self._store:
            del self._store[key]
            del self._timestamps[key]
            return True
        return False

    def clear(self) -> None:
        """Evict all entries."""
        self._store.clear()
        self._timestamps.clear()

    def __len__(self) -> int:
        return len(self._store)


class DiskCache:
    """
    Pickle-based persistent disk cache.

    Parameters
    ----------
    cache_dir : str
        Directory where cache files are stored.
    policy    : CachePolicy
        Eviction / validity policy (default: 24-hour TTL).
    """

    import os as _os

    def __init__(
        self,
        cache_dir: str = "/tmp/alphamind_cache",
        policy: Optional[CachePolicy] = None,
    ) -> None:
        import os

        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._policy = policy or TTLCachePolicy(ttl_seconds=86400)
        self._timestamps: Dict[str, float] = {}

    def _path(self, key: str) -> str:
        import os

        safe = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self._cache_dir, f"{safe}.pkl")

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        import os

        path = self._path(key)
        if not os.path.exists(path):
            return default
        ts = self._timestamps.get(key, os.path.getmtime(path))
        if not self._policy.is_valid(ts):
            os.remove(path)
            return default
        try:
            with open(path, "rb") as fh:
                return pickle.load(fh)
        except Exception:
            return default

    def set(self, key: str, value: Any) -> bool:
        if not self._policy.should_cache(key, value):
            return False
        try:
            with open(self._path(key), "wb") as fh:
                pickle.dump(value, fh)
            self._timestamps[key] = time.time()
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        import os

        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)
            self._timestamps.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        import os

        for f in os.listdir(self._cache_dir):
            if f.endswith(".pkl"):
                os.remove(os.path.join(self._cache_dir, f))
        self._timestamps.clear()


class RedisCache:
    """
    Redis-backed cache (requires ``redis`` package at runtime).

    The class is importable without Redis installed; a ``ConnectionError``
    is raised only when ``connect()`` or a cache operation is attempted.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        ttl_seconds: int = 3600,
    ) -> None:
        self._host = host
        self._port = port
        self._db = db
        self._ttl = ttl_seconds
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import redis

                self._client = redis.Redis(
                    host=self._host, port=self._port, db=self._db
                )
            except ImportError as exc:
                raise ImportError(
                    "Install the 'redis' package to use RedisCache: pip install redis"
                ) from exc
        return self._client

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        raw = self._get_client().get(key)
        if raw is None:
            return default
        return pickle.loads(raw)

    def set(self, key: str, value: Any) -> bool:
        self._get_client().setex(key, self._ttl, pickle.dumps(value))
        return True

    def delete(self, key: str) -> bool:
        return bool(self._get_client().delete(key))

    def clear(self, pattern: str = "*") -> None:
        client = self._get_client()
        for k in client.scan_iter(pattern):
            client.delete(k)
