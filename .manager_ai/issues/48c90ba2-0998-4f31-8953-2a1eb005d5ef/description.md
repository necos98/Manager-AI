Due problemi residui dopo l'implementazione della issue #0df22702 (rigenerazione index YAML da directory):

## 1. Index file ancora tracciati da git (RISOLTO)

`issues.yaml` e `memories.yaml` erano ancora tracciati da git dopo l'aggiornamento del `.gitignore`. Aggiungere un file a `.gitignore` non rimuove il tracking di file già tracciati — serviva `git rm --cached`. Eseguito manualmente:
```bash
git rm --cached .manager_ai/issues.yaml .manager_ai/memories.yaml
```
`files.yaml` non era mai stato tracciato, ok.

## 2. La reindicizzazione non recupera tutte le issue

Dopo l'avvio con la nuova logica di rebuild, alcune issue non vengono visualizzate nell'interfaccia. Issue che erano state "nascoste" (perse dall'index durante operazioni git) non riappaiono dopo la rebuild.

### Ipotesi da verificare:
- **Cache TTL troppo lungo**: `list_issues()` ha cache TTL 300s. Se la rebuild invalida solo `__index__` ma una richiesta precedente ha cached la lista, potrebbe servire un restart per vedere i cambiamenti.
- **Watcher non triggera rebuild per nuove directory**: Se una cartella issue viene aggiunta (es. via `git pull`), il watcher la classifica correttamente? Verificare che `_classify` gestisca eventi `FileCreatedEvent` per directory.
- **Rebuild chiamata prima che le directory esistano**: Se `start_project()` viene chiamato prima che tutte le cartelle issue siano presenti (es. in ambienti git dopo un clone pulito), le issue mancanti non vengono mai indicizzate finché il watcher non triggera un rebuild successivo.
- **Il server non è stato riavviato dopo il deploy della fix**: La rebuild avviene solo in `start_project()`. Se il server è rimasto in esecuzione con la vecchia logica, le issue non vengono recuperate fino al prossimo restart.

### Cosa fare:
1. Verificare che la rebuild in `start_project()` venga effettivamente eseguita (aggiungere log)
2. Verificare che la cache venga invalidata correttamente dopo la rebuild
3. Aggiungere un endpoint o un meccanismo per forzare la rebuild senza restart
4. Testare con una issue "nascosta" per riprodurre il problema