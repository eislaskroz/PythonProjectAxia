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


def test_mark_returns_elapsed_seconds():
    from core.performance import mark
    value = mark("prueba")
    assert isinstance(value, float)
    assert value >= 0


def test_measure_context_manager():
    from core.performance import measure
    with measure("prueba rápida", warning_ms=999999):
        value = 2 + 2
    assert value == 4


def test_background_task_success():
    import threading
    from core.performance import run_in_background

    done = threading.Event()
    received = []
    thread = run_in_background(
        lambda: 42,
        on_success=lambda value: (received.append(value), done.set()),
        name="test-worker",
    )
    assert done.wait(2)
    thread.join(timeout=2)
    assert received == [42]
