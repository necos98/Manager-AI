## Feature: Voice Input in New Issue Dialog

Add speech-to-text (voice input) to the New Issue description field, reusing the existing `SpeechModal` and `useSpeechRecognition` hook already used in the terminal.

### Current State
- `useSpeechRecognition` hook: wraps browser SpeechRecognition API (Web Speech API), supports continuous + interim results, language detection
- `SpeechModal` component: modal with mic toggle, live transcript display, editable textarea for corrections, "Send" callback
- Both live in `frontend/src/features/terminals/` but are generic (no terminal-specific dependencies)
- NewIssueDialog has a Textarea for description with a "Browse Files" button below it

### Design

**Approach:** Move reusable pieces to shared, then wire into NewIssueDialog.

1. **Relocate `useSpeechRecognition` hook** to `frontend/src/shared/hooks/use-speech-recognition.ts`
2. **Relocate `SpeechModal` component** to `frontend/src/shared/components/speech-modal.tsx`
3. **Add mic button** in NewIssueDialog next to the "Browse Files" button below the description textarea
4. **Wire callback**: on SpeechModal "Send", append transcribed text to the description at cursor position (same pattern as file tag insertion)

### Why relocate instead of cross-import
- Both hook and component have zero terminal-specific code
- Cross-feature imports create hidden coupling; shared/ is the intended home for reusable UI
- TerminalPanel import paths get updated (one-line change each)

### UX flow
1. User clicks mic button → SpeechModal opens
2. User clicks Start, speaks → live transcript appears
3. User clicks Stop, reviews/edits transcript
4. User clicks Send → text appended to description textarea at cursor position, modal closes

### Error handling
- Browser without SpeechRecognition: SpeechModal shows "not supported" message (already built)
- Recognition errors: SpeechModal shows error text (already built)
- Empty transcript: Send button disabled (already built)
