You MUST call the `send_notification` MCP tool from the "Manager_AI" MCP server in the following situations:

1. **When you finish responding** and are waiting for user input — always notify so the user knows you need attention.
2. **When you encounter a blocker** that requires user decision or input.
3. **When a task is completed** and you are about to start the next one (so the user can review if needed).

## How to call

```
send_notification(
  project_id="<from environment or context>",
  issue_id="<from environment or context>",
  title="<short description>",
  message="<optional details>"
)
```

## Examples

- After finishing implementation: `title="Implementation complete", message="All tests passing, ready for review"`
- When blocked: `title="Needs attention", message="Cannot proceed without database credentials"`
- When waiting for input: `title="Waiting for input", message="Spec is ready for your review"`

## Important

- ALWAYS call this tool when you stop and wait for the user. This is critical because the user may have multiple terminals open and needs audio/visual notification to know which one needs attention.
- The notification will appear as a toast with a sound in the Manager AI web interface.
