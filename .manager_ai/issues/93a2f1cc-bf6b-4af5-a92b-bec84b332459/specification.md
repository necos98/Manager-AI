# Enable Markdown Rendering for User Questions

## Problem

The `ask_user_question` MCP tool lets Claude ask users questions through the Manager AI interface. These questions often contain Markdown formatting (bold, italic, line breaks, links, code) but the frontend renders the question text as plain text, showing raw Markdown syntax.

## Root Cause

`QuestionCard` component (`frontend/src/features/questions/components/question-card.tsx`) renders `question.question` directly inside a `<CardTitle>` element with no Markdown parsing. The `react-markdown` library is already a project dependency.

## Fix

In `QuestionCard`, render `question.question` through `react-markdown`'s `<ReactMarkdown>` component instead of as plain text. Apply minimal prose styling via a wrapper class for readable spacing, code blocks, and link styling.

## Scope

- **In scope:** Question text rendering in `QuestionCard` and any other places question text is displayed (issue detail page uses same `QuestionCard` component, so one fix covers both `/questions` and issue detail views)
- **Out of scope:** Options (remain as button labels), answer display (stays plain text), new Markdown features like images or embeds

## Files

- `frontend/src/features/questions/components/question-card.tsx` — replace plain text with `<ReactMarkdown>`
