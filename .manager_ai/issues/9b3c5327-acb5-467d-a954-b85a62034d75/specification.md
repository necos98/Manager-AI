# Specifica: Icona personalizzata finestra applicazione

## Problema
L'app Manager AI usa pywebview (WebView2 su Windows) per mostrare l'interfaccia in una finestra desktop. La finestra mostra l'icona di default di Python nella taskbar e nella title bar. L'utente ha un logo personalizzato (`logo.png` nella root del progetto) e vuole che venga mostrato come icona dell'applicazione.

## Obiettivo
Impostare `logo.png` (convertito in `.ico`) come icona della finestra applicativa durante lo sviluppo (`python start.py`), visibile nella taskbar di Windows e nella title bar della finestra.

## Soluzione

### Approccio: ctypes + Win32 API (zero dipendenze nuove)

Usare le API Win32 via `ctypes` per trovare la finestra pywebview e impostarne l'icona, senza aggiungere dipendenze al progetto.

### Modifiche

#### 1. Conversione automatica logo.png → logo.ico
- Aggiungere logica in `start.py` che converte `logo.png` in `logo.ico` usando PIL (già disponibile)
- L'`.ico` deve contenere multiple risoluzioni: 16x16, 32x32, 48x48, 256x256
- La conversione avviene solo se `logo.ico` non esiste o è più vecchio di `logo.png`

#### 2. Nuovo modulo `backend/app/desktop_icon.py`
- Funzione `set_app_window_icon(window_title: str, ico_path: str) -> bool`
- Usa `ctypes.windll.user32` per:
  - `FindWindowW(None, window_title)` → trovare l'HWND della finestra
  - `LoadImageW(0, ico_path, IMAGE_ICON, size, size, LR_LOADFROMFILE)` → caricare l'icona
  - `SendMessageW(hwnd, WM_SETICON, ICON_BIG/SMALL, hicon)` → impostare icona grande e piccola
- Gestione errori silenziosa: se la finestra non è ancora pronta o il file manca, ritorna False senza crash

#### 3. Integrazione in `start.py`
- Dopo `webview.create_window(...)` e prima di `webview.start(...)`, chiamare `set_app_window_icon("Manager AI", str(ROOT / "logo.ico"))`
- L'icona viene impostata prima che la finestra sia visibile

#### 4. Favicon HTML (complementare)
- Aggiungere `<link rel="icon" type="image/png" href="/logo.png">` in `frontend/index.html`
- Copiare `logo.png` nella cartella `frontend/public/` per servirla staticamente
- Questo fa vedere l'icona anche quando l'app viene aperta in un browser normale

### Flusso
```
start.py → verifica/conversione logo.ico → create_window("Manager AI", ...) → set_app_window_icon() → webview.start()
```

### Vincoli
- Windows only (ctypes.windll)
- Solo per sviluppo (`python start.py`), non per packaging .exe
- Nessuna nuova dipendenza Python (ctypes è built-in, PIL già presente)
- Fallback silenzioso: se qualcosa fallisce, l'app continua a funzionare con l'icona di default

### Testing
- Avviare `python start.py` e verificare che l'icona nella taskbar sia il logo personalizzato
- Verificare che l'icona nella title bar sia il logo personalizzato
- Rimuovere `logo.ico` e verificare che la conversione automatica lo ricrei
- Testare su Windows 10 e Windows 11