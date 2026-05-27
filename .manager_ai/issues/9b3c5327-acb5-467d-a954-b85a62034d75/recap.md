## Riepilogo Implementazione

Aggiunta icona personalizzata finestra applicativa usando `logo.png` del progetto.

### Modifiche

**Nuovo file:**
- `backend/app/desktop_icon.py` — modulo che usa ctypes (Win32 API) per impostare l'icona della finestra via `FindWindowW` + `LoadImageW` + `SendMessageW(WM_SETICON)`. Zero dipendenze nuove. Gestisce sia icona grande (48px, taskbar) che piccola (16px, title bar). Fallback silenzioso in caso di errore.

**File modificati:**
- `start.py`:
  - `_ensure_app_icon()` — converte `logo.png` → `logo.ico` con PIL in 4 risoluzioni (16, 32, 48, 256 px). Solo se .ico assente o più vecchio del .png.
  - `poll_worker()` — imposta icona finestra al primo ciclo (dopo che pywebview ha creato la finestra nativa)
- `backend/requirements.txt` — aggiunto `Pillow>=11.0`
- `frontend/index.html` — aggiunto `<link rel="icon" type="image/png" href="/logo.png">`, titolo cambiato in "Manager AI"
- `frontend/public/logo.png` — copia del logo per servirlo come favicon

### Comportamento
- Al primo avvio: `logo.png` → `logo.ico` (conversione automatica)
- Avvii successivi: conversione saltata (`.ico` già aggiornato)
- Se `logo.png` assente: skip silenzioso, app usa icona default
- Se finestra non trovata: skip silenzioso
- Compatibile solo Windows (ctypes.windll)

### Verifica
- Sintassi Python valida (entrambi i file)
- Conversione PNG→ICO testata con successo
- Modulo desktop_icon importabile e funzionante