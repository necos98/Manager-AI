# Audio-to-Text Transcription for Uploaded Files

## Overview

When user uploads audio files, they are automatically transcribed to text via local Whisper model. Transcription runs asynchronously — upload returns immediately with `pending` status, background job transcribes, text becomes available when done. Original audio file and transcribed text both preserved.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Engine | Local openai-whisper | No API cost, works offline, good accuracy |
| Formats | ogg, mp3, wav, flac, m4a, aac | Common formats Whisper handles natively |
| Timing | Async background job | Avoid HTTP timeouts on large audio files |
| Resilience | Startup recovery scan | Survive server restart without queue infra |
| Model size | `base` (142M params, ~1GB VRAM/CPU) | Good accuracy/speed balance; upgradeable |

## Backend Changes

### 1. Dependencies

- Add `openai-whisper` to requirements
- System dependency: `ffmpeg` (documented in setup, Whisper requires it)

### 2. Constants (`file_service.py`)

```python
AUDIO_EXTENSIONS = {"ogg", "mp3", "wav", "flac", "m4a", "aac"}

MIME_MAP update:
  ogg → audio/ogg, mp3 → audio/mpeg, wav → audio/wav,
  flac → audio/flac, m4a → audio/mp4, aac → audio/aac
```

Add `AUDIO_EXTENSIONS` to `ALLOWED_EXTENSIONS`.

### 3. Audio extraction (`file_reader.py`)

New function `_extract_audio(path: str) -> str`:
- Uses lazy-loaded singleton Whisper model (`base` size)
- Calls `model.transcribe(path)`, returns `result["text"]`
- Added to `extract()` dispatcher for audio extensions

### 4. Async transcription (`file_service.py`)

- `upload_files()`: audio files set `extraction_status = "pending"` immediately, no sync extraction
- After upload loop: `asyncio.create_task(_transcribe_async(...))` for each audio file
- `_transcribe_async()`: runs `_extract_audio` in thread via `asyncio.to_thread`, updates record (status + text) on success, sets `failed` + error on failure
- Text capped at `MAX_CHARS` (500,000)

### 5. Startup recovery (`app/main.py` lifespan)

On server start, scan all `.manager_ai/files.yaml` across projects for audio files with `extraction_status == "pending"`. Re-trigger `_transcribe_async()` for each. This handles server restarts without a persistent queue.

### 6. Re-extract support

Existing `POST /{file_id}/reextract` endpoint already calls `file_reader.extract()`. Once audio extension is in the dispatcher, re-extract works automatically. Users can retry failed transcriptions.

## Frontend

No changes required. Existing file list UI already shows `extraction_status`:
- Audio files show "Transcribing..." while `pending`
- Show extracted text when `ok`
- Show error message when `failed`
- User can click "Re-extract" to retry

## Test Plan

- Unit test: `_extract_audio()` with small test audio file
- Unit test: audio extension detection and MIME mapping
- Unit test: `upload_files()` sets pending status for audio
- Integration test: upload workflow for audio file returns 201 with pending status
- Manual test: upload real audio file, verify transcription appears after processing
- Edge case: ffmpeg missing → graceful error, status = failed
- Edge case: empty audio → handled by Whisper (returns minimal text)
- Edge case: very long audio → text capped at MAX_CHARS, status ok

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| First request slow (model download ~1GB) | Lazy load with logging; first transcription takes extra time |
| VRAM/RAM usage of Whisper model | Use `base` model (~1GB); document how to change model size |
| ffmpeg not installed | Graceful error in extraction, status = failed with clear message |
| Async task lost on crash | Startup recovery scan re-triggers pending transcriptions |
