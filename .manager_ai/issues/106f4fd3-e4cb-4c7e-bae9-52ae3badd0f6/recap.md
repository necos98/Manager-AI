## Recap

Moved the reusable `useSpeechRecognition` hook and `SpeechModal` component from `features/terminals/` to `shared/`, then wired a "Voice" mic button into the NewIssueDialog.

### Changes
- **Moved** `use-speech-recognition.ts` → `frontend/src/shared/hooks/` (no code changes)
- **Moved** `speech-modal.tsx` → `frontend/src/shared/components/` (updated internal import to new hook path)
- **Updated** `terminal-panel.tsx` import from `@/features/terminals/components/speech-modal` → `@/shared/components/speech-modal`
- **Added** `SpeechModal` + mic button to `new-issue-dialog.tsx` — same cursor-position append pattern as file tag insertion

### UX
1. Click "Voice" button next to "Browse Files" below description textarea
2. SpeechModal opens → Start → speak → transcript appears with live interim text
3. Stop → edit transcript if needed → Send
4. Text inserted at cursor position in description

Build verified passing.