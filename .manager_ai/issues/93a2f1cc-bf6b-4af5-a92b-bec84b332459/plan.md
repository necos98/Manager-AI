# Enable Markdown Rendering for User Questions — Implementation Plan

## Goal

Render question text as Markdown in `QuestionCard` using the existing `MarkdownViewer` shared component.

## Architecture

`MarkdownViewer` in `frontend/src/shared/components/markdown-viewer.tsx` already wraps `react-markdown` with `<div className="prose prose-sm">`. Use it in `QuestionCard` instead of plain-text `<CardTitle>`.

## Steps

1. In `QuestionCard`, import `MarkdownViewer` and replace `<CardTitle className="text-base">{question.question}</CardTitle>` with `<MarkdownViewer content={question.question} />`
2. Verify visually that Markdown renders correctly in the browser

**Files:**
- Modify: `frontend/src/features/questions/components/question-card.tsx`

**No backend changes, no new dependencies.**
