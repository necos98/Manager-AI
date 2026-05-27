pipeline bug. mi esce questo errore in console "[05/27/26 22:08:52] INFO     Created new transport with session ID:                       streamable_http_manager.py:229
                             e6ff2b35ae654291b7f201aaf4a5dd06
                    ERROR    Error handling POST request                                          streamable_http.py:526
                             ╭─────────────── Traceback (most recent call last) ────────────────╮
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site │
                             │ -packages\mcp\server\streamable_http.py:337 in                   │
                             │ _handle_post_request                                             │
                             │                                                                  │
                             │   334 │   │   │   │   return                                     │
                             │   335 │   │   │                                                  │
                             │   336 │   │   │   # Parse the body - only read it once           │
                             │ ❱ 337 │   │   │   body = await request.body()                    │
                             │   338 │   │   │   if len(body) > MAXIMUM_MESSAGE_SIZE:           │
                             │   339 │   │   │   │   response = self._create_error_response(    │
                             │   340 │   │   │   │   │   "Payload Too Large: Message exceeds ma │
                             │                                                                  │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site │
                             │ -packages\starlette\requests.py:241 in body                      │
                             │                                                                  │
                             │   238 │   async def body(self) -> bytes:                         │
                             │   239 │   │   if not hasattr(self, "_body"):                     │
                             │   240 │   │   │   chunks: list[bytes] = []                       │
                             │ ❱ 241 │   │   │   async for chunk in self.stream():              │
                             │   242 │   │   │   │   chunks.append(chunk)                       │
                             │   243 │   │   │   self._body = b"".join(chunks)                  │
                             │   244 │   │   return self._body                                  │
                             │                                                                  │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site │
                             │ -packages\starlette\requests.py:235 in stream                    │
                             │                                                                  │
                             │   232 │   │   │   │   │   yield body                             │
                             │   233 │   │   │   elif message["type"] == "http.disconnect":  #  │
                             │   234 │   │   │   │   self._is_disconnected = True               │
                             │ ❱ 235 │   │   │   │   raise ClientDisconnect()                   │
                             │   236 │   │   yield b""                                          │
                             │   237 │                                                          │
                             │   238 │   async def body(self) -> bytes:                         │
                             ╰────────────────────────────────
"