"""Human-readable duration formatting for the timer nodes."""


def format_duration(seconds):
    """Format a number of seconds as a short human-readable string.

    Examples: ``823.4 ms``, ``12.34 s``, ``1m 23.4s``, ``1h 02m 03.4s``.
    Negative values are clamped to zero.
    """
    seconds = max(float(seconds), 0.0)
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    if seconds < 3600:
        minutes, sec = divmod(seconds, 60)
        return f"{int(minutes)}m {sec:04.1f}s"
    hours, rem = divmod(seconds, 3600)
    minutes, sec = divmod(rem, 60)
    return f"{int(hours)}h {int(minutes):02d}m {sec:04.1f}s"
