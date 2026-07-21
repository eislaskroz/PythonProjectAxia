import time
from core.performance import page_range, TTLCache


def test_page_range():
    assert page_range(1, 100) == (0, 99)
    assert page_range(3, 25) == (50, 74)
    assert page_range(0, 9999) == (0, 499)


def test_ttl_cache_expires():
    cache = TTLCache(ttl_seconds=0.01)
    cache.set("x", [1])
    assert cache.get("x") == [1]
    time.sleep(0.02)
    assert cache.get("x") is None
