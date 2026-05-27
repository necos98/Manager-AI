# Piano di Implementazione: Icona Personalizzata Finestra Applicazione

**Obiettivo:** Impostare il logo dell'app (`logo.png`) come icona della finestra desktop (taskbar + title bar) quando eseguito con `python start.py`.

**Architettura:** Nuovo modulo `desktop_icon.py` usa ctypes (Win32 API) per trovare la finestra pywebview e impostarne l'icona tramite `WM_SETICON`. Conversione automatica logo.png → logo.ico integrata in start.py. Favicon HTML aggiornato per coerenza.

**Tech Stack:** Python ctypes (built-in), PIL/Pillow (già disponibile), Win32 API

## Modifiche

### File da creare:
- `backend/app/desktop_icon.py` — modulo con funzione `set_app_window_icon()` che usa ctypes

### File da modificare:
- `start.py` — aggiungere conversione logo.png→logo.ico, chiamata a set_app_window_icon dopo create_window
- `frontend/index.html` — aggiornare favicon link
- `frontend/public/` — aggiungere logo.png

## Task

### Task 1: Convertire logo.png in logo.ico
Aggiungere funzione `_ensure_app_icon()` in `start.py` che converte `logo.png` in `logo.ico` con multiple risoluzioni (16, 32, 48, 256 px) usando PIL. La conversione avviene solo se `logo.ico` non esiste o è più vecchio di `logo.png`.

### Task 2: Creare modulo desktop_icon.py
Nuovo modulo `backend/app/desktop_icon.py` con funzione `set_app_window_icon(window_title, ico_path)` che:
- Usa `ctypes.windll.user32.FindWindowW` per trovare l'HWND della finestra
- Usa `ctypes.windll.user32.LoadImageW` per caricare l'icona in due dimensioni (big 48x48, small 16x16)
- Usa `ctypes.windll.user32.SendMessageW` con `WM_SETICON` per impostare entrambe le icone
- Gestisce errori con fallback silenzioso (ritorna False senza crashare)

### Task 3: Integrare in start.py
Dopo `webview.create_window(...)` e prima di `webview.start(...)`, chiamare `_ensure_app_icon()` e poi `set_app_window_icon("Manager AI", str(ROOT / "logo.ico"))`.

### Task 4: Aggiornare favicon frontend
- Copiare `logo.png` in `frontend/public/`
- Aggiornare `frontend/index.html`: aggiungere `<link rel="icon" type="image/png" href="/logo.png">` (mantenendo anche il favicon.svg esistente)

### Task 5: Test end-to-end
Avviare `python start.py` e verificare che:
- L'icona della finestra nella taskbar sia il logo personalizzato
- L'icona nella title bar sia il logo personalizzato
- La conversione logo.ico funzioni automaticamente al primo avvio
- Rimuovendo logo.ico, venga ricreato