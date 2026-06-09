"""Plain-text error log file format builder."""

from __future__ import annotations

from typing import Any


def format_error_log(
    *,
    exc_type_name: str,
    message: str,
    pathname: str,
    lineno: int,
    timestamp: str,
    traceback_str: str = "",
    request_context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Build a plain-text error log entry.

    Returns a formatted string matching the spec:

        ========================================
        ERROR - {timestamp}
        ========================================
        Type:       {exc_type_name}
        Message:    {message}
        Source:     {pathname}:{lineno}

        --- Request Context ---
        {key}: {value}

        --- Traceback ---
        {full_traceback}

        --- Metadata ---
        PID: {process}
        Logger: {name}
        Process: {processName}
    """
    lines: list[str] = [
        "=" * 40,
        f"ERROR - {timestamp}",
        "=" * 40,
        f"Type:       {exc_type_name}",
        f"Message:    {message}",
        f"Source:     {pathname}:{lineno}",
    ]

    if request_context:
        lines.append("")
        lines.append("--- Request Context ---")
        for key, value in request_context.items():
            lines.append(f"{key}: {value}")

    if traceback_str:
        lines.append("")
        lines.append("--- Traceback ---")
        lines.append(traceback_str.rstrip("\n"))

    if metadata:
        lines.append("")
        lines.append("--- Metadata ---")
        for key, value in metadata.items():
            lines.append(f"{key}: {value}")

    lines.append("")
    return "\n".join(lines)
