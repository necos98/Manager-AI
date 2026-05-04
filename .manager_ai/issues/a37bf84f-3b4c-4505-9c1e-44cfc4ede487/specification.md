# Specifica: Backup SQLite prima della migrazione flat-system

## Obiettivo

Aggiungere un backup automatico del database SQLite (`data/manager_ai.db`) prima che la migrazione flat-system (`db_to_files.py`) venga eseguita. Il backup deve avvenire **solo** quando almeno un progetto necessita effettivamente la migrazione, non a ogni avvio.

## Contesto

Manager AI sta migrando da storage SQLite a flat-file YAML sotto `.manager_ai/`. La migrazione e attualmente non-distruttiva (i dati DB rimangono dopo l'export), ma non esiste alcun meccanismo di backup in caso di errori durante la scrittura dei file flat.

## Design

### Nuovo modulo: `backend/app/migration/db_backup.py`

- `backup_database(db_path, backup_dir, keep=5)` → copia il file SQLite in `backup_dir` con timestamp nel nome (`manager_ai_2026-05-04T125300.db`). Ruota i backup mantenendo solo gli ultimi `keep`.
- `rotate_backups(backup_dir, keep)` → elimina i backup piu vecchi oltre il limite.

### Modifica: `migrate_all_projects` in `db_to_files.py`

Pre-flight check: prima di iterare i progetti, verifica se almeno uno necessita migrazione (sentinel assente, directory non gia popolata, path esistente). Se si, esegue il backup una volta sola, poi procede con il loop normale.

### Backup path

`data/backups/` — directory creata automaticamente se non esiste.

### Error handling

- Backup fallito → logga warning, **non blocca** la migrazione
- Rotazione fallita → logga warning, ignora

### Testing

- `test_backup_creates_file_with_correct_name`
- `test_backup_skips_when_db_not_found`
- `test_rotation_keeps_last_n_files`
- `test_migrate_all_projects_backups_when_needed`
- `test_migrate_all_projects_skips_backup_when_all_migrated`
- `test_migration_continues_even_if_backup_fails`
