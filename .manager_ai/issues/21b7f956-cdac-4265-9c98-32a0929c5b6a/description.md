Non so cosa sia successo, ma credo che l'llm abbia provato ad usare il plugin mysql e il backend sia esploso. Cerca attentamente il problema e risolvilo alla radice dopo una lunga analisi


                    ERROR    SSE response error                                                   streamable_http.py:520
                             ╭─────────────── Traceback (most recent call last) ────────────────╮
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site │
                             │ -packages\mcp\server\streamable_http.py:513 in                   │
                             │ _handle_post_request                                             │
                             │                                                                  │
                             │   510 │   │   │   │   # Start the SSE response (this will send h │
                             │   511 │   │   │   │   try:                                       │
                             │   512 │   │   │   │   │   # First send the response to establish │
                             │ ❱ 513 │   │   │   │   │   async with anyio.create_task_group() a │
                             │   514 │   │   │   │   │   │   tg.start_soon(response, scope, rec │
                             │   515 │   │   │   │   │   │   # Then send the message to be proc │
                             │   516 │   │   │   │   │   │   metadata = ServerMessageMetadata(r │
                             │                                                                  │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site │
                             │ -packages\anyio\_backends\_asyncio.py:799 in __aexit__           │
                             │                                                                  │
                             │    796 │   │   │   │   │   # added to self._exceptions so it's o │
                             │    797 │   │   │   │   │   # chaining and avoid adding a "During │
                             │    798 │   │   │   │   │   # for each nesting level.             │
                             │ ❱  799 │   │   │   │   │   raise BaseExceptionGroup(             │
                             │    800 │   │   │   │   │   │   "unhandled errors in a TaskGroup" │
                             │    801 │   │   │   │   │   ) from None                           │
                             │    802 │   │   │   │   elif exc_val:                             │
                             ╰──────────────────────────────────────────────────────────────────╯
                             ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)

                             ╭──────────────────────── Sub-exception #1 ────────────────────────╮
                             │ ╭───────────── Traceback (most recent call last) ──────────────╮ │
                             │ │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\ │ │
                             │ │ site-packages\mcp\server\streamable_http.py:518 in           │ │
                             │ │ _handle_post_request                                         │ │
                             │ │                                                              │ │
                             │ │   515 │   │   │   │   │   │   # Then send the message to be  │ │
                             │ │   516 │   │   │   │   │   │   metadata = ServerMessageMetada │ │
                             │ │   517 │   │   │   │   │   │   session_message = SessionMessa │ │
                             │ │ ❱ 518 │   │   │   │   │   │   await writer.send(session_mess │ │
                             │ │   519 │   │   │   │   except Exception:                      │ │
                             │ │   520 │   │   │   │   │   logger.exception("SSE response err │ │
                             │ │   521 │   │   │   │   │   await sse_stream_writer.aclose()   │ │
                             │ │                                                              │ │
                             │ │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\ │ │
                             │ │ site-packages\anyio\streams\memory.py:249 in send            │ │
                             │ │                                                              │ │
                             │ │   246 │   │   """                                            │ │
                             │ │   247 │   │   await checkpoint()                             │ │
                             │ │   248 │   │   try:                                           │ │
                             │ │ ❱ 249 │   │   │   self.send_nowait(item)                     │ │
                             │ │   250 │   │   except WouldBlock:                             │ │
                             │ │   251 │   │   │   # Wait until there's someone on the receiv │ │
                             │ │   252 │   │   │   send_event = Event()                       │ │
                             │ │                                                              │ │
                             │ │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\ │ │
                             │ │ site-packages\anyio\streams\memory.py:218 in send_nowait     │ │
                             │ │                                                              │ │
                             │ │   215 │   │                                                  │ │
                             │ │   216 │   │   """                                            │ │
                             │ │   217 │   │   if self._closed:                               │ │
                             │ │ ❱ 218 │   │   │   raise ClosedResourceError                  │ │
                             │ │   219 │   │   if not self._state.open_receive_channels:      │ │
                             │ │   220 │   │   │   raise BrokenResourceError                  │ │
                             │ │   221                                                        │ │
                             │ ╰──────────────────────────────────────────────────────────────╯ │
                             │ ClosedResourceError                                              │
                             ╰──────────────────────────────────────────────────────────────────╯
ERROR:    ASGI callable returned without completing response.
INFO:     127.0.0.1:47992 - "GET /mcp/ HTTP/1.1" 200 OK