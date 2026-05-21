"""Claude Code Stop hook — sends TTS (text-to-speech) payload to Manager AI.

Reads JSON from stdin: {"transcript_path": "/path/to/transcript.jsonl"}
Parses JSONL transcript, extracts last assistant message.
Optionally summarizes via claude CLI if tts.summarize_enabled is true.
Posts final text to MANAGER_AI_BASE_URL/api/events with type=tts.
All errors swallowed — must never break Claude Code.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _fetch_settings(base_url: str) -> dict[str, str]:
    try:
        req = urllib.request.Request(
            f"{base_url}/api/settings",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        if isinstance(data, list):
            return {item["key"]: item["value"] for item in data if isinstance(item, dict)}
        return {}
    except Exception:
        return {}


def _extract_last_assistant_text(transcript_path: str) -> str | None:
    last_text = None
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                role = None
                content = None
                if isinstance(msg.get("message"), dict):
                    role = msg["message"].get("role")
                    content = msg["message"].get("content")
                if not role:
                    role = msg.get("role")
                if not content:
                    content = msg.get("content")
                if role != "assistant" or not content:
                    continue

                if isinstance(content, str):
                    last_text = content.strip()
                elif isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            parts.append(block)
                    joined = "\n".join(parts).strip()
                    if joined:
                        last_text = joined
    except Exception:
        pass
    return last_text


def _summarize(text: str, settings: dict[str, str]) -> str | None:
    model = settings.get("tts.summarize_model", "claude-haiku-4-5-20251001")
    prompt_template = settings.get(
        "tts.summarize_prompt",
        "Summarize the following text for voice reading in Italian. "
        "Write as flowing prose, max {max_length} words. "
        "No code blocks, no bullet lists, no markdown. "
        "Read commands and filenames as normal text.",
    )
    max_length = 60
    try:
        max_length = int(settings.get("tts.summarize_max_length", "60"))
    except ValueError:
        pass
    timeout_s = 10
    try:
        timeout_s = int(settings.get("tts.summarize_timeout_seconds", "10"))
    except ValueError:
        pass

    prompt = prompt_template.replace("{max_length}", str(max_length))

    try:
        proc = subprocess.run(
            [
                "claude",
                "-p",
                "--model", model,
                "--dangerously-skip-permissions",
                "--output-format", "text",
            ],
            input=(prompt + "\n\n" + text),
            capture_output=True,
            timeout=timeout_s,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return None


def main() -> None:
    raw = sys.stdin.read()
    if not raw:
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return

    transcript_path = payload.get("transcript_path")
    if not transcript_path:
        return

    last_text = _extract_last_assistant_text(transcript_path)
    if not last_text:
        return

    base_url = _env("MANAGER_AI_BASE_URL", "http://localhost:8000")
    settings = _fetch_settings(base_url)

    final_text = last_text
    if settings.get("tts.summarize_enabled") == "true":
        summary = _summarize(last_text, settings)
        if summary:
            final_text = summary

    body = json.dumps({
        "type": "tts",
        "text": final_text,
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
