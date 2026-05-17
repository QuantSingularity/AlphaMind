"""
Unit tests for the AlphaMind caching module (data_processing/caching.py).

Covers:
* TTLCachePolicy: validity window, expiry, None-value rejection.
* SizeCachePolicy: should_cache always True for non-None, is_valid always True.
* CacheManager: get/set/delete/clear lifecycle, hit/miss stats, TTL eviction.
* cache_function decorator: transparent wrapping, result reuse.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data_processing.caching import (
    CacheManager,
    SizeCachePolicy,
    TTLCachePolicy,
    cache_function,
)


class TestTTLCachePolicy:
    def test_valid_within_ttl(self):
        policy = TTLCachePolicy(ttl_seconds=60)
        assert policy.is_valid(time.time()) is True

    def test_expired_outside_ttl(self):
        policy = TTLCachePolicy(ttl_seconds=1)
        expired_time = time.time() - 2
        assert policy.is_valid(expired_time) is False

    def test_should_cache_non_none(self):
        policy = TTLCachePolicy()
        assert policy.should_cache("k", {"data": [1, 2, 3]}) is True

    def test_should_not_cache_none(self):
        policy = TTLCachePolicy()
        assert policy.should_cache("k", None) is False

    def test_zero_ttl_immediately_expired(self):
        policy = TTLCachePolicy(ttl_seconds=0)
        # A cache entry set now should already be expired
        assert policy.is_valid(time.time()) is False


class TestSizeCachePolicy:
    def test_should_cache_non_none(self):
        policy = SizeCachePolicy(max_size_mb=50)
        assert policy.should_cache("k", [1, 2, 3]) is True

    def test_should_cache_none_returns_true(self):
        """SizeCachePolicy pickling None succeeds; it evaluates size, not None-ness."""
        policy = SizeCachePolicy()
        # None pickles to ~5 bytes — well under the limit, so should_cache returns True
        assert policy.should_cache("k", None) is True

    def test_is_valid_always_true(self):
        """Size policy validity is based on eviction, not time."""
        policy = SizeCachePolicy()
        assert policy.is_valid(0.0) is True
        assert policy.is_valid(time.time() - 1_000_000) is True


class TestCacheManager:
    @pytest.fixture
    def manager(self):
        policy = TTLCachePolicy(ttl_seconds=30)
        return CacheManager(policy=policy)

    def test_miss_returns_default(self, manager):
        result = manager.get("nonexistent", default="fallback")
        assert result == "fallback"

    def test_miss_returns_none_when_no_default(self, manager):
        assert manager.get("missing") is None

    def test_set_then_get(self, manager):
        manager.set("key1", {"value": 42})
        result = manager.get("key1")
        assert result == {"value": 42}

    def test_delete_removes_entry(self, manager):
        manager.set("to_delete", "hello")
        manager.delete("to_delete")
        assert manager.get("to_delete") is None

    def test_delete_nonexistent_returns_false(self, manager):
        assert manager.delete("phantom") is False

    def test_clear_empties_cache(self, manager):
        manager.set("a", 1)
        manager.set("b", 2)
        manager.clear()
        assert manager.get("a") is None
        assert manager.get("b") is None

    def test_stats_structure(self, manager):
        stats = manager.get_stats()
        assert isinstance(stats, dict)

    def test_stats_entries_tracked(self, manager):
        manager.clear()
        manager.set("x", 99)
        manager.set("y", 100)
        stats = manager.get_stats()
        assert stats.get("entries", stats.get("total_entries", 0)) >= 1

    def test_tuple_key(self, manager):
        manager.set(("a", "b", 1), "tuple_key_value")
        assert manager.get(("a", "b", 1)) == "tuple_key_value"

    def test_ttl_eviction(self):
        policy = TTLCachePolicy(ttl_seconds=0.05)
        mgr = CacheManager(policy=policy)
        mgr.set("expiring", "soon")
        time.sleep(0.10)
        result = mgr.get("expiring")
        assert result is None, "Entry should have expired after TTL"


class TestCacheFunctionDecorator:
    def test_decorator_returns_same_result(self):
        call_count = {"n": 0}

        @cache_function(ttl_seconds=30)
        def expensive(x: int) -> int:
            call_count["n"] += 1
            return x * 2

        r1 = expensive(5)
        r2 = expensive(5)
        assert r1 == r2 == 10

    def test_decorator_caches_result(self):
        call_count = {"n": 0}

        @cache_function(ttl_seconds=30)
        def counted(x: int) -> int:
            call_count["n"] += 1
            return x + 1

        counted(7)
        counted(7)
        assert (
            call_count["n"] == 1
        ), "Function body should only execute once for same args"

    def test_different_args_not_cached(self):
        call_count = {"n": 0}

        @cache_function(ttl_seconds=30)
        def f(x: int) -> int:
            call_count["n"] += 1
            return x

        f(1)
        f(2)
        assert call_count["n"] == 2
