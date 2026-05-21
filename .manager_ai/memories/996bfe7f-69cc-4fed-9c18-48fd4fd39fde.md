---
id: 996bfe7f-69cc-4fed-9c18-48fd4fd39fde
project_id: 1baae1c7-22f1-4091-abec-b49da70cf46c
title: 'Log terminal pattern: TerminalService entry without PTY, asyncio.Queue data source'
parent_id: null
created_at: '2026-05-21T18:17:00.910852'
updated_at: '2026-05-21T18:17:00.910852'
links: []
---
A "log terminal" is a TerminalService entry with `mode: "log"` and no PTY. Data comes from `asyncio.Queue` instead of PTY read. The reader (`_terminal_reader`), buffer, WebSocket, recording, and frontend (`TerminalPanel`) all work identically — only the data source changes.

**How to use:**
1. `terminal_service.create_log(project_id, issue_id, project_path, label)` creates entry + queue, returns TerminalResponse
2. `terminal_service.push_output(terminal_id, text)` puts text into the queue
3. `_ensure_reader(terminal_id, service)` starts the reader loop (reads from queue instead of PTY)
4. `terminal_service.destroy_log(terminal_id)` pushes `None` sentinel → reader sees EOF → cleans up

**Why:** Introduced for agent pipeline live output streaming (issue #09ddcfda). Reuses all existing terminal infrastructure. A sentinel `None` value signals EOF to the reader loop.

**Thread-to-async bridge (run_streaming):** ClaudeCodeExecutor.run_streaming() reads subprocess stdout in a thread via `proc.stdout.readline()`, then bridges to async callbacks with `asyncio.run_coroutine_threadsafe(on_output(line), loop)`. The loop is captured at call time from `asyncio.get_running_loop()`.