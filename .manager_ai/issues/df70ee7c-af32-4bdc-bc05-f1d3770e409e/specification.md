# Specifica: Health check per inconsistenza project_id tra manager.json e resources

## Problema
Prima dell'aggiornamento "Flat System", due utenti sullo stesso progetto potevano sovrascrivere `manager.json` con `project_id` diversi, rompendo l'instradamento MCP. Serve un processo di health check che rilevi e corregga automaticamente queste inconsistenze.

## Soluzione
Estendere l'endpoint esistente `GET /api/projects/{project_id}/health` con un nuovo check `_check_resource_consistency()` che:

1. Legge `manager.json` per ottenere il `project_id` autorevole
2. Scansiona tutti i file YAML in `.manager_ai/` che contengono un campo `project_id`:
   - `issues.yaml` (ogni entry)
   - `.manager_ai/issues/<id>/issue.yaml` (ogni file)
   - `memories.yaml` (ogni entry)
   - `.manager_ai/memories/<id>.md` (frontmatter `project_id`)
3. Confronta ogni `project_id` con quello autorevole
4. Se diversi → riscrive il file correggendo il `project_id` in-place
5. Ritorna un report: `{ ok, scanned, fixed, details[] }`

## Comportamento
- **Auto-fix sempre attivo**: il check corregge automaticamente le inconsistenze senza flag opzionali
- **Skip se manager.json assente**: se `manager.json` non esiste, il check viene saltato (già segnalato da `_check_manager_json`)
- **Scrittura atomica**: usa pattern `temp + rename` per evitare corruzione durante la scrittura

## Response shape
```json
{
  "manager_json": { ... },
  "claude_resources": { ... },
  "mcp": { ... },
  "resource_consistency": {
    "ok": true,
    "scanned": 12,
    "fixed": 0,
    "details": []
  }
}
```

## File coinvolti
- `backend/app/routers/projects.py` — aggiungere `_check_resource_consistency()` e integrarlo in `project_health()`

## Test
- Test unitario: `_check_resource_consistency` con mock filesystem (file YAML con project_id corretti e errati)
- Test integrazione: chiamata a `GET /api/projects/{id}/health` verifica che il campo `resource_consistency` sia presente