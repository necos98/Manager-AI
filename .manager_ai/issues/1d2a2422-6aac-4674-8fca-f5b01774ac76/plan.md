# Implementation Plan: Audio-to-Text Transcription

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/requirements.txt` | Add `openai-whisper` dependency |
| Modify | `backend/app/services/file_reader.py` | `_extract_audio()` + dispatcher wiring |
| Modify | `backend/app/services/file_service.py` | Audio constants, MIME types, async transcription + recovery |
| Modify | `backend/app/main.py` | Startup recovery scan invocation |
| Modify | `backend/tests/test_file_reader.py` | Audio extraction unit tests |

## Implementation Steps

### Task 1: Add `openai-whisper` dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] Step 1: Add `openai-whisper` line to requirements.txt

### Task 2: Audio extraction in file_reader.py

**Files:**
- Modify: `backend/app/services/file_reader.py`

- [ ] Step 1: Add `AUDIO_EXTENSIONS` set at module level
- [ ] Step 2: Add `_get_whisper_model()` — lazy singleton loading `whisper.load_model("base")`
- [ ] Step 3: Add `_extract_audio(path: str) -> str` — calls `model.transcribe(path)`, returns `result["text"]`
- [ ] Step 4: Wire into `extract()` dispatcher: add `elif ext in AUDIO_EXTENSIONS: text = _extract_audio(path)`
- [ ] Step 5: Handle ImportError for missing whisper lib → return ExtractionResult with status "failed" and clear message

### Task 3: Audio constants and async transcription in file_service.py

**Files:**
- Modify: `backend/app/services/file_service.py`

- [ ] Step 1: Add `AUDIO_EXTENSIONS` set and add to `ALLOWED_EXTENSIONS`
- [ ] Step 2: Add MIME type mappings for ogg, mp3, wav, flac, m4a, aac
- [ ] Step 3: In `upload_files()`, audio files skip immediate extraction → set `extraction_status = "pending"`, `extracted_text = None`
- [ ] Step 4: After upload loop, schedule `asyncio.create_task(_transcribe_async(project_path, record))` for each audio file
- [ ] Step 5: Implement `_transcribe_async()` — calls `_extract_audio` via `asyncio.to_thread`, updates record on success/failure
- [ ] Step 6: Implement `recover_pending_transcriptions(project_path)` — scans file_store for audio files with pending status, re-triggers `_transcribe_async`. Called on startup.
- [ ] Step 7: Ensure re-extract endpoint works — `reextract()` already calls `file_reader.extract()`, audio branch is picked up automatically

### Task 4: Startup recovery in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] Step 1: In lifespan startup, after project iteration loop, call `recover_pending_transcriptions()` for each project's path
- [ ] Step 2: Wrap in try/except to avoid blocking startup on recovery errors

### Task 5: Tests

**Files:**
- Modify: `backend/tests/test_file_reader.py`

- [ ] Step 1: Test `_extract_audio()` with a generated test WAV file (sine wave with simple speech using `wave` stdlib module — expect text back from Whisper, even if empty/minimal for tones)
- [ ] Step 2: Test audio extension routing in `extract()` dispatcher
- [ ] Step 3: Test graceful failure when whisper not available
- [ ] Step 4: Test audio files get `pending` status on upload (integration with FileService)
- [ ] Step 5: Run full test suite, verify no regressions

## Execution Order

```
Task 1 (dependency) → Task 2 (extraction) → Task 3 (service) → Task 4 (recovery) → Task 5 (tests)
```
