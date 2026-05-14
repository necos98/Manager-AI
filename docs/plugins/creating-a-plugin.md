# Creare un plugin MCP per Manager AI

Un plugin per Manager AI è un server MCP standard. Puoi usare qualsiasi linguaggio o trasporto (stdio o HTTP/SSE). Questa guida mostra come crearne uno.

## Struttura minima di un server MCP (Python)

```python
# my_plugin_server.py
import sys
import json

def read_msg():
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)
    return json.loads(line)

def send_response(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def send_error(rid, code, message):
    send_response({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})

# Tool registry
tools = [
    {
        "name": "hello",
        "description": "Saluta per nome",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nome da salutare"}
            },
            "required": ["name"]
        }
    }
]

def handle_tool_call(tool_name, arguments):
    if tool_name == "hello":
        name = arguments.get("name", "mondo")
        return f"Ciao, {name}!"
    return f"Tool sconosciuto: {tool_name}"

# Main loop
while True:
    req = read_msg()
    method = req.get("method", "")
    rid = req.get("id", 0)

    if method == "initialize":
        send_response({
            "jsonrpc": "2.0", "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "my-plugin", "version": "1.0"},
                "capabilities": {"tools": {}}
            }
        })
    elif method == "notifications/initialized":
        pass  # notification, no response
    elif method == "tools/list":
        send_response({"jsonrpc": "2.0", "id": rid, "result": {"tools": tools}})
    elif method == "tools/call":
        params = req.get("params", {})
        result_text = handle_tool_call(
            params.get("name", ""),
            params.get("arguments", {})
        )
        send_response({
            "jsonrpc": "2.0", "id": rid,
            "result": {"content": [{"type": "text", "text": result_text}]}
        })
    else:
        send_error(rid, -32601, f"Method not found: {method}")
```

## Protocollo MCP (riepilogo minimo)

1. **`initialize`**: Il client invia le sue capabilities. Il server risponde con serverInfo e capabilities.
2. **`notifications/initialized`**: Notifica che l'handshake è completo. Nessuna risposta.
3. **`tools/list`**: Il client chiede la lista dei tool. Il server risponde con un array di tool definitions.
4. **`tools/call`**: Il client chiama un tool con nome e argomenti. Il server esegue e risponde con il risultato.

## Definizione di un Tool

Un tool MCP è un oggetto JSON con questo schema:

```json
{
  "name": "query",
  "description": "Esegue una query SQL in sola lettura",
  "inputSchema": {
    "type": "object",
    "properties": {
      "sql": {
        "type": "string",
        "description": "La query SQL da eseguire"
      },
      "limit": {
        "type": "integer",
        "description": "Massimo numero di righe",
        "default": 100
      }
    },
    "required": ["sql"]
  }
}
```

I tipi JSON supportati nell'`inputSchema`:
- `string` — parametro testuale
- `integer` — numero intero
- `number` — numero con virgola
- `boolean` — true/false
- `array` — lista
- `object` — oggetto annidato

I parametri in `required` sono obbligatori. Gli altri sono opzionali.

## Trasporto: stdio vs HTTP

### stdio (consigliato per plugin locali)

Il server legge da stdin e scrive su stdout, una linea JSON per messaggio. Manager AI spawna il processo con `asyncio.create_subprocess_exec`.

**Vantaggi**: Semplice, nessuna porta da esporre, isolamento di processo.
**Svantaggi**: Solo locale.

### HTTP / SSE

Il server espone un endpoint SSE (Server-Sent Events). Manager AI si connette come client HTTP.

**Vantaggi**: Il server può essere remoto, su un'altra macchina.
**Svantaggi**: Richiede gestione rete, autenticazione.

## Usare librerie MCP esistenti

Non serve scrivere il server a mano. Puoi usare:

- **Python**: `mcp[cli]` (FastMCP) — `uvx mcp-server-xxx`
- **Node.js**: `@modelcontextprotocol/sdk`
- **Go**: `github.com/mark3labs/mcp-go`

La maggior parte dei plugin sarà un server MCP esistente, non scritto da zero.

## Testare il plugin

Avvia il server manualmente e invia messaggi JSON-RPC:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}' | python my_plugin_server.py
```

Oppure configuralo in `.manager_ai/plugins.yaml` e usa l'UI di Manager AI per testarlo.
