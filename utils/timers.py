"""Named stopwatch state shared between CidTimerStart and CidTimerStop.

Timestamps come from ``time.perf_counter()`` (monotonic, high resolution).
The functions call it through the :mod:`time` module so tests can monkeypatch
the clock.
"""

import time

_timers = {}


def start_timer(name):
    """Record a start timestamp for ``name``, overwriting any previous one."""
    _timers[name] = time.perf_counter()


def stop_timer(name):
    """Return the seconds elapsed since ``start_timer(name)`` was called.

    The start stamp is kept, so several stops can measure against one start
    (split timing). Raises ``ValueError`` if the timer was never started.
    """
    try:
        started = _timers[name]
    except KeyError:
        raise ValueError(
            f"CidTimerStop: no start timestamp for timer '{name}'. "
            "Connect a CidTimerStart node with the same 'timer_name' "
            "upstream, and make sure it executes before this node."
        ) from None
    return time.perf_counter() - started


def clear_timers():
    """Forget all start stamps (used by the test suite)."""
    _timers.clear()
