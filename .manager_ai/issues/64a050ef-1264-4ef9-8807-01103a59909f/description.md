Fix plugin MySQL: tutti i tool (`fetch_data`, `execute_query`, `describe_table` e probabilmente `insert_data` e `create_table`) falliscono con errore di validazione Pydantic.

**Errore**:
```
Error executing tool X: 1 validation error for XArguments
query/table — Field required
```

**Causa**: I tool MCP sono registrati con firma che accetta solo `kwargs` (stringa), ma il backend interno si aspetta parametri nominati espliciti (`query`, `table`, ecc.). Il JSON dentro `kwargs` non viene spacchettato — arriva come dict annidato e la validazione Pydantic lo boccia.

**Fix atteso**: Riesporre i tool MySQL con parametri nominati invece del `kwargs` catch-all.