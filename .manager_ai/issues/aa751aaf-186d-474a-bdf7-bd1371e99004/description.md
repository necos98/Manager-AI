## ⚠️ Auto-rilevato: UnicodeDecodeError

**Errore:** 'utf-8' codec can't decode byte 0x97 in position 235: invalid start byte
**Fonte:** `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\mcp\server\streamable_http.py:526`
**Request:**  N/A

```
--- Traceback ---
Traceback (most recent call last):
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\mcp\server\streamable_http.py", line 347, in _handle_post_request
    raw_message = json.loads(body)
  File "C:\Users\j.magarelli\AppData\Local\Python\pythoncore-3.14-64\Lib\json\__init__.py", line 347, in loads
    s = s.decode(detect_encoding(s), 'surrogatepass')
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 235: invalid start byte

--- Metadata ---
PID: 18904
Logger: mcp.server.streamable_http
Process: MainProcess
```