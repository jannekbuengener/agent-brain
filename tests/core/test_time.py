from datetime import datetime
from importlib import import_module


def _time_module():
    return import_module("agent_brain.core.time")


def test_fixed_clock_injection_reproduces_utcnow_contract() -> None:
    time = _time_module()
    fixed = datetime(2020, 1, 1, 0, 0, 0)

    assert time.utcnow(time.FixedClock(fixed)) == fixed


def test_default_clock_can_be_replaced_and_restored() -> None:
    time = _time_module()
    previous = time.get_default_clock()
    fixed = datetime(2026, 10, 20, 12, 34, 56)

    time.set_default_clock(time.FixedClock(fixed))
    try:
        assert time.utcnow() == fixed
    finally:
        time.set_default_clock(previous)


def test_fixed_clock_can_advance_by_explicit_replacement_only() -> None:
    time = _time_module()
    first = datetime(2024, 1, 2, 3, 4, 5)
    second = datetime(2024, 1, 2, 3, 4, 6)
    clock = time.FixedClock(first)

    assert clock.now() == first
    clock.set_time(second)
    assert clock.now() == second


def test_system_clock_preserves_claire_naive_utc_shape() -> None:
    time = _time_module()

    assert time.SystemClock().now().tzinfo is None
