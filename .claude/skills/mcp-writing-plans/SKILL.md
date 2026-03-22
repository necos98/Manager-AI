---
name: mcp-writing-plans
description: Use when you have an approved spec and need to write an implementation plan. MCP-native version of writing-plans - saves plan and tasks via Manager AI MCP instead of local .md files. OVERRIDES superpowers:writing-plans.
---

# MCP Writing Plans

Variante MCP-native di `superpowers:writing-plans`. Stesso processo di pianificazione dettagliata, ma il piano e i task vengono salvati nel Manager AI MCP — **nessun file .md su disco**.

**Announce at start:** "Sto usando mcp-writing-plans per creare il piano di implementazione via Manager AI."

**Contesto:** Viene invocata dopo mcp-brainstorming, con spec già approvata e task_id della spec disponibile.

## Prerequisito: project_id

Leggi `manager.json` nella root del progetto per il `project_id`.

## Struttura del piano

Prima di definire i task, mappa i file che verranno creati o modificati. Ogni file ha una responsabilità chiara.

- Unità con interfacce ben definite, testabili in isolamento
- File piccoli e focalizzati — se un file fa troppe cose, dividilo
- File che cambiano insieme vivono insieme
- In codebase esistenti, segui i pattern già presenti

## Granularità dei task

**Ogni step è un'azione (2-5 minuti):**
- "Scrivi il test che fallisce" — step
- "Esegui per verificare che fallisca" — step
- "Scrivi il codice minimo per farlo passare" — step
- "Verifica che passi" — step
- "Commit" — step

## Processo

1. **Leggi project_id** da `manager.json`
2. **Leggi la spec** — recupera da MCP con `mcp__ManagerAi__get_task_details` usando il task_id della spec
3. **Verifica scope** — se la spec copre più sottosistemi indipendenti, suggerisci di dividere in piani separati
4. **Mappa i file** — elenca tutti i file da creare/modificare con le loro responsabilità
5. **Scrivi il piano completo** — task per task, step per step (vedi struttura sotto)
6. **Salva piano via MCP** — `mcp__ManagerAi__create_task_plan`
7. **Crea task MCP** — un `mcp__ManagerAi__create_task` per ogni task principale del piano
8. **Loop revisione piano** — dispatcha subagent revisore; correggi e ri-dispatcha fino ad approvazione (max 3 iterazioni)
9. **Handoff all'esecuzione** — presenta le opzioni di esecuzione all'utente

## Struttura task nel piano

```markdown
### Task N: [Nome Componente]

**File:**
- Crea: `percorso/esatto/file.php`
- Modifica: `percorso/esatto/esistente.php:123-145`
- Test: `tests/percorso/esatto/test.php`

- [ ] **Step 1: Scrivi il test che fallisce**
[codice completo del test]

- [ ] **Step 2: Esegui per verificare che fallisca**
Comando: `...`
Atteso: FAIL con "..."

- [ ] **Step 3: Implementazione minima**
[codice completo]

- [ ] **Step 4: Verifica che passi**
Comando: `...`
Atteso: PASS

- [ ] **Step 5: Commit**
`git commit -m "feat: ..."`
```

## Salvataggio Piano via MCP

```
mcp__ManagerAi__create_task_plan
  project_id: <da manager.json>
  content: <piano completo in markdown>
```

Poi crea un task MCP per ogni task principale:

```
mcp__ManagerAi__create_task
  project_id: <da manager.json>
  name: "Task N: [Nome]"
  description: <descrizione del task>
```

## Loop Revisione Piano

1. Dispatcha subagent con: percorso al piano MCP (task_id) + task_id della spec
2. Se ❌ problemi: correggi con `mcp__ManagerAi__edit_task_plan`, ri-dispatcha
3. Se ✅ approvato: procedi all'handoff

## Handoff Esecuzione

> "Piano salvato nel Manager AI (task_id: `<id>`). Task creati: N. Come vuoi procedere?
>
> **1. Subagent per task** (raccomandato) — un subagent fresco per ogni task, review tra i task
> **2. Esecuzione inline** — eseguo i task in questa sessione con checkpoint"

- Se scelto **Subagent**: **REQUIRED SUB-SKILL:** `superpowers:subagent-driven-development`
- Se scelto **Inline**: **REQUIRED SUB-SKILL:** `superpowers:executing-plans`

## Regole

- Percorsi file sempre esatti
- Codice completo nel piano (non "aggiungi validazione")
- Comandi esatti con output atteso
- DRY, YAGNI, TDD, commit frequenti
