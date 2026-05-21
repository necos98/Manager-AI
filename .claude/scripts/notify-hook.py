"""Claude Code Stop/Notification hook — sends desktop notification to Manager AI.

Reads JSON from stdin: {"title": "...", "message": "..."}
Falls back to --default-title / --default-message CLI args.
Posts to MANAGER_AI_BASE_URL/api/events.
All errors swallowed — must never break Claude Code.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-title", default="Claude")
    parser.add_argument("--default-message", default="Done")
    args = parser.parse_args()

    title = args.default_title
    message = args.default_message

    raw = sys.stdin.read()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data.get("title"), str):
                title = data["title"]
            if isinstance(data.get("message"), str):
                message = data["message"]
        except (json.JSONDecodeError, ValueError):
            pass

    base_url = _env("MANAGER_AI_BASE_URL", "http://localhost:8000")
    body = json.dumps({
        "type": "notification",
        "title": title,
        "message": message,
        "terminal_id": _env("MANAGER_AI_TERMINAL_ID"),
        "issue_id": _env("MANAGER_AI_ISSUE_ID"),
        "project_id": _env("MANAGER_AI_PROJECT_ID"),
    }).encode()

    try:
        req = urllib.request.Request(
            f"{base_url}/api/events",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
