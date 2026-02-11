from datetime import datetime, timezone, date, time

def now_utc_compact() -> str:
    """
    Return a compact UTC timestamp suitable for filenames.

    Example:
        20251220_184455Z
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")

def now_utc_iso() -> str:
    """
    Return the current UTC time in ISO 8601 format.

    Example:
        2025-12-20T18:44:55

        timespec="seconds" omits microseconds for a cleaner look, since sub-second precision is usually not needed in logs and reports.
        if timespec="auto", you get microseconds like 2025-12-20T18:44:55.298806Z, which can be noisy and less human-friendly in most cases.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def now_utc_human() -> str:
    """
    Return a human-friendly UTC timestamp for logs and reports.

    Format:
        Dec 20, 2025, 18:44 UTC

    Design goals:
    - Month spelled out (no numeric ambiguity)
    - 24-hour clock (no AM/PM confusion)
    - Explicit UTC marker
    - Optimized for instant human readability
    """
    return datetime.now(timezone.utc).strftime("%b %d, %Y, %H:%M UTC")


def _format_seconds_human(seconds: float) -> str:
    """
    Convert seconds to a short, human-friendly duration string.

    Examples
    --------
    - 0.53  -> "0.53s"
    - 12.4  -> "12.40s"
    - 75.2  -> "1m 15.20s"
    - 3723  -> "1h 2m 3.00s"
    """
    if seconds < 60:
        return f"{seconds:.2f}s"

    minutes, sec = divmod(seconds, 60.0)
    if minutes < 60:
        return f"{int(minutes)}m {sec:.2f}s"

    hours, minutes = divmod(minutes, 60.0)
    return f"{int(hours)}h {int(minutes)}m {sec:.2f}s"

