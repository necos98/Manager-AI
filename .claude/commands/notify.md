Notifications are handled automatically via Claude Code hooks.

When Claude Code triggers a Notification event (e.g., waiting for input, permission needed), the configured hook in `.claude/settings.json` automatically sends a POST request to the Manager AI backend, which broadcasts the notification to the web interface as a toast with a sound.

No manual action is needed — the hook uses the `MANAGER_AI_*` environment variables injected into the terminal to identify the terminal, issue, and project.

The `send_notification` MCP tool is also available as a manual fallback if you need to send a custom notification.
