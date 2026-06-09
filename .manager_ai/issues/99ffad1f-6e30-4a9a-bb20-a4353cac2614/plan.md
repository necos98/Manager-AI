## Piano: Aggiungere flag --max-turns ai comandi Hermes provider

### Approccio
Modifica diretta del file `backend/app/providers/hermes_provider.py` per aggiungere `--max-turns 300` in due metodi.

### Task

1. **Aggiungere `--max-turns 300` in `build_run_issue_command`**
   - File: `backend/app/providers/hermes_provider.py`, righe 24-28
   - Modifica: inserire `--max-turns 300` tra `--skills run-issue` e `--yolo`

2. **Aggiungere `--max-turns 300` in `build_run_pipeline_command`**
   - File: `backend/app/providers/hermes_provider.py`, righe 30-34
   - Modifica: inserire `--max-turns 300` tra `--skills run-pipeline` e `--yolo`

3. **Verificare il file risultante**
   - Leggere il file per confermare che entrambi i comandi contengano `--max-turns 300`
   - Controllare che gli altri metodi siano invariati
