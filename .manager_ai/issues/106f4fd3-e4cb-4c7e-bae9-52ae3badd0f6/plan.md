# Add voice input to New Issue dialog — Implementation Plan

**Goal:** Reuse existing SpeechModal + useSpeechRecognition hook in NewIssueDialog by moving them to shared first, then wiring a mic button next to the description textarea.

**Architecture:** Two generic pieces (hook, modal) relocate from `features/terminals/` to `shared/`. TerminalPanel gets import path updates. NewIssueDialog gains a mic button + SpeechModal instance wired to append voice text at cursor position. No new code — just move + wire.

**Tech Stack:** React, TypeScript, Web Speech API (browser-native), existing shadcn/ui Dialog/Button/Textarea

---

### Task 1: Move useSpeechRecognition hook to shared

**Files:**
- Create: `frontend/src/shared/hooks/use-speech-recognition.ts`
- Delete: `frontend/src/features/terminals/hooks/use-speech-recognition.ts`

Move the hook file from terminals to shared. No code changes — pure file move. The hook has zero terminal-specific dependencies.

### Task 2: Move SpeechModal to shared

**Files:**
- Create: `frontend/src/shared/components/speech-modal.tsx`
- Delete: `frontend/src/features/terminals/components/speech-modal.tsx`

Move the SpeechModal component to shared. Update its internal import to point to the new hook location:
- `@/features/terminals/hooks/use-speech-recognition` → `@/shared/hooks/use-speech-recognition`

No other changes to the component.

### Task 3: Update TerminalPanel imports

**Files:**
- Modify: `frontend/src/features/terminals/components/terminal-panel.tsx`

Update two import paths:
- `./speech-modal` → `@/shared/components/speech-modal`
- No hook import change needed (terminal-panel uses SpeechModal, not the hook directly)

### Task 4: Add voice input to NewIssueDialog

**Files:**
- Modify: `frontend/src/features/issues/components/new-issue-dialog.tsx`

Changes:
1. Import `SpeechModal` from `@/shared/components/speech-modal`
2. Import `Mic` icon from `lucide-react`
3. Add `const [speechOpen, setSpeechOpen] = useState(false)` state
4. Add mic button next to "Browse Files" button below textarea
5. Add `handleSpeechSend` callback: append text at cursor position (same pattern as `handleFileSelect`)
6. Render `<SpeechModal open={speechOpen} onClose={() => setSpeechOpen(false)} onSend={handleSpeechSend} />`
