---
name: asking-questions
description: Use when you need to ask the user a question or get their input on a decision. Tells Claude to use the ask_user_question MCP tool instead of inline text or AskUserQuestion.
---

# Asking Questions to the User

## The Rule

**ALWAYS use the `ask_user_question` MCP tool when you need user input.** Never use inline text questions or `AskUserQuestion`.

## When to Use

Use `ask_user_question` whenever:
- You need the user to make a decision between options
- You need clarification on requirements
- You want to confirm an approach before proceeding
- You hit a blocker that requires user input

## How to Use

```
ask_user_question(issue_id, question, options?, timeout_seconds?)
```

### Parameters

- `issue_id` (required): The ID of the current issue you're working on
- `question` (required): Clear, concise question text
- `options` (optional): List of 2-4 possible answers. Always provide options when choices are clear.
- `timeout_seconds` (optional): How long to wait for an answer (default 300s / 5 min)

### Best Practices

1. **Always provide options** when the user faces a clear choice (2-4 options)
2. **Allow free-text** — the user can always write a custom answer instead of picking an option
3. **Be specific** — don't ask "What should I do?" but "Which library should we use for date formatting?"
4. **One question at a time** — don't batch multiple questions
5. **Wait for the answer** — the tool blocks until the user responds, then continue

### Example

```python
# Good — specific question with options
ask_user_question(
    issue_id="abc-123",
    question="Which authentication method should we use?",
    options=["JWT tokens", "Session cookies", "OAuth 2.0"]
)

# Also good — open-ended when needed
ask_user_question(
    issue_id="abc-123",
    question="What should the rate limit be for this endpoint?"
)
```

### What the User Sees

Your question appears in:
1. The Issue page (under the issue detail)
2. The global Questions page (grouped by project)

The user can click an option button or type a custom answer. The tool waits until they respond.
