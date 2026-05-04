## Recap

Aggiunto backup automatico del database SQLite prima della migrazione flat-system.

### Modifiche

**Nuovo file: `backend/app/migration/db_backup.py`**
- `backup_database(db_path, backup_dir, keep=5)` — copia il DB in `data/backups/` con timestamp, ruota i backup
- `rotate_backups(backup_dir, keep)` — mantiene solo gli ultimi N backup

**Modificato: `backend/app/migration/db_to_files.py`**
- Estratto helper `_needs_migration(project)` per verificare se un progetto necessita migrazione
- `migrate_all_projects` ora fa pre-flight check: se almeno un progetto richiede migrazione, esegue backup una volta sola
- `migrate_project` refattorizzato per usare `_needs_migration`
- Backup fallito → warning log, migrazione continua comunque

**Nuovo file: `backend/tests/test_db_backup.py`**
- 8 unit test per `backup_database` e `rotate_backups`
- 4 test di integrazione per il flusso migrazione+backup

### Test
20/20 pass (8 migration esistenti + 12 nuovi).