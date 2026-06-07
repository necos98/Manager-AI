from datetime import datetime, timezone


def now() -> datetime:
    """Current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def iso_now() -> str:
    """Current UTC time as ISO string."""
    return now().isoformat()


def naive_utc_now() -> datetime:
    """Current UTC datetime without tzinfo (naive)."""
    return datetime.utcnow()


def utc_timestamp() -> float:
    """Current UTC time as Unix timestamp."""
    return now().timestamp()


def date_str(fmt: str = "%Y-%m-%d") -> str:
    """Current UTC date as string."""
    return now().strftime(fmt)


def format_ts(dt: datetime | None = None, **kwargs) -> str:
    """Format a datetime as ISO string, passing kwargs to isoformat().

    Args:
        dt: Datetime to format (default: now)
        **kwargs: Passed to isoformat(), e.g. sep="T", timespec="microseconds"

    Returns:
        ISO-formatted string
    """
    if dt is None:
        dt = now()
    return dt.isoformat(**kwargs)
