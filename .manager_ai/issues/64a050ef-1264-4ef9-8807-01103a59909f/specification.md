# Fix MySQL plugin: convert kwargs-based tools to explicit named parameters

## Problem

I tool MySQL (`fetch_data`, `execute_query`, `describe_table`, `insert_data`, `create_table`) falliscono tutti con:

```
Error executing tool X: 1 validation error for XArguments
query/table — Field required
```

## Root cause

`_make_proxy_function` in `backend/app/mcp/plugin_proxy.py` genera funzioni proxy con `**kwargs`. FastMCP usa `inspect.signature()` sulla funzione per generare il modello Pydantic di validazione. Con `**kwargs`, il modello risultante ha un singolo parametro `kwargs: str` — quindi quando Claude chiama il tool con parametri nominati reali (es. `query="SELECT..."`), Pydantic li rifiuta.

## Fix

Modificare `_make_proxy_function` per:
1. Accettare il `Tool` object come parametro aggiuntivo
2. Leggere `tool.inputSchema["properties"]` per estrarre i nomi dei parametri
3. Costruire un `inspect.Signature` con `inspect.Parameter` per ogni parametro (required → no default, optional → default `None`)
4. Assegnare la signature al proxy via `proxy.__signature__`

Modificare `register_plugin_tools` per passare ogni `tool` a `_make_proxy_function`.

## File to change

- `backend/app/mcp/plugin_proxy.py` — solo questo file

## Edge cases

- Tool senza parametri → signature vuota → comportamento invariato
- Tutti i plugin (non solo MySQL) beneficiano del fix
- I tipi reali sono validati dal server MCP remoto, non dal proxy locale