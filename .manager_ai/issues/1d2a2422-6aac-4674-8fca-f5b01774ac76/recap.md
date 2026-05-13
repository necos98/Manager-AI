## Changes Made

### `backend/requirements.txt`
- Added `openai-whisper>=20240930` dependency

### `backend/app/services/file_reader.py`
- Added `AUDIO_EXTENSIONS` set: ogg, mp3, wav, flac, m4a, aac
- Added `_get_whisper_model()` — lazy singleton loading `whisper.load_model("base")`
- Added `_extract_audio(path)` — calls `model.transcribe()`, returns stripped text
- Wired audio extensions into `extract()` dispatcher
- ImportError for missing whisper caught by existing try/except, returns status "failed"

### `backend/app/services/file_service.py`
- Added audio extensions to `ALLOWED_EXTENSIONS`
- Added audio MIME types to `MIME_MAP` (ogg→audio/ogg, mp3→audio/mpeg, wav→audio/wav, flac→audio/flac, m4a→audio/mp4, aac→audio/aac)
- Audio files set `extraction_status = "pending"` on upload (no sync extraction)
- After upload: `asyncio.create_task(_transcribe_async())` schedules background transcription
- `_transcribe_async()`: runs `_extract_audio` via `asyncio.to_thread`, updates record on success/failure
- `recover_pending_transcriptions()`: scans file_store for pending audio files, re-triggers transcription (called on startup)

### `backend/app/main.py`
- Added startup recovery: after watcher init, calls `recover_pending_transcriptions()` for each active project
- Wrapped in try/except via `else` clause on existing try block

### `backend/tests/test_file_reader.py`
- `test_audio_extensions_defined` — verifies ogg, mp3, wav in AUDIO_EXTENSIONS
- `test_extract_audio_dispatcher_routes` — verifies dispatcher routes audio extensions to _extract_audio
- `test_extract_audio_missing_whisper` — verifies graceful failure when whisper not installed
- `test_extract_audio_unsupported_format` — verifies unsupported extension handling

## Architecture Notes
- **No frontend changes needed** — existing UI handles extraction_status lifecycle (pending→ok/failed)
- **No new API endpoints** — reuse existing upload, preview, content, reextract endpoints
- **Model: base** (~1GB) — good accuracy/speed balance; configurable by editing `_get_whisper_model()`
- **Async pattern**: fire-and-forget via `asyncio.create_task` + startup recovery for resilience
