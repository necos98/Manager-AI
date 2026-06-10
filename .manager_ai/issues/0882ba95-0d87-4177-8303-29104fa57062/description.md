Ho ricevuto questo errore, fixalo:

[06/09/26 21:13:15] ERROR    AttributeError: 'EventService' object has no attribute 'notify'                                                                                                logging_config.py:162
                             ╭──────────────────────────────────────────────────────────── Traceback (most recent call last) ─────────────────────────────────────────────────────────────╮
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py:148 in call_next                                    │
                             │                                                                                                                                                            │
                             │   145 │   │   │   task_group.start_soon(coro)                                                                                                              │
                             │   146 │   │   │                                                                                                                                            │
                             │   147 │   │   │   try:                                                                                                                                     │
                             │ ❱ 148 │   │   │   │   message = await recv_stream.receive()                                                                                                │
                             │   149 │   │   │   │   info = message.get("info", None)                                                                                                     │
                             │   150 │   │   │   │   if message["type"] == "http.response.debug" and info is not None:                                                                    │
                             │   151 │   │   │   │   │   message = await recv_stream.receive()                                                                                            │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\anyio\streams\memory.py:132 in receive                                           │
                             │                                                                                                                                                            │
                             │   129 │   │   │   try:                                                                                                                                     │
                             │   130 │   │   │   │   return receiver.item                                                                                                                 │
                             │   131 │   │   │   except AttributeError:                                                                                                                   │
                             │ ❱ 132 │   │   │   │   raise EndOfStream from None                                                                                                          │
                             │   133 │                                                                                                                                                    │
                             │   134 │   def clone(self) -> MemoryObjectReceiveStream[T_co]:                                                                                              │
                             │   135 │   │   """                                                                                                                                          │
                             ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                             EndOfStream

                             During handling of the above exception, another exception occurred:

                             ╭──────────────────────────────────────────────────────────── Traceback (most recent call last) ─────────────────────────────────────────────────────────────╮
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\middleware\error_logger.py:24 in dispatch                                                   │
                             │                                                                                                                                                            │
                             │   21 │                                                                                                                                                     │
                             │   22 │   async def dispatch(self, request: Request, call_next) -> Response:                                                                                │
                             │   23 │   │   try:                                                                                                                                          │
                             │ ❱ 24 │   │   │   return await call_next(request)                                                                                                           │
                             │   25 │   │   except ClientDisconnect:                                                                                                                      │
                             │   26 │   │   │   logger.debug("Client disconnected during request to %s", request.url.path)                                                                │
                             │   27 │   │   │   return Response(status_code=499)                                                                                                          │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py:156 in call_next                                    │
                             │                                                                                                                                                            │
                             │   153 │   │   │   │   if app_exc is not None:                                                                                                              │
                             │   154 │   │   │   │   │   nonlocal exception_already_raised                                                                                                │
                             │   155 │   │   │   │   │   exception_already_raised = True                                                                                                  │
                             │ ❱ 156 │   │   │   │   │   raise app_exc                                                                                                                    │
                             │   157 │   │   │   │   raise RuntimeError("No response returned.")                                                                                          │
                             │   158 │   │   │                                                                                                                                            │
                             │   159 │   │   │   assert message["type"] == "http.response.start"                                                                                          │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py:141 in coro                                         │
                             │                                                                                                                                                            │
                             │   138 │   │   │   │                                                                                                                                        │
                             │   139 │   │   │   │   with send_stream:                                                                                                                    │
                             │   140 │   │   │   │   │   try:                                                                                                                             │
                             │ ❱ 141 │   │   │   │   │   │   await self.app(scope, receive_or_disconnect, send_no_error)                                                                  │
                             │   142 │   │   │   │   │   except Exception as exc:                                                                                                         │
                             │   143 │   │   │   │   │   │   app_exc = exc                                                                                                                │
                             │   144                                                                                                                                                      │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\exceptions.py:62 in __call__                                │
                             │                                                                                                                                                            │
                             │   59 │   │   else:                                                                                                                                         │
                             │   60 │   │   │   conn = WebSocket(scope, receive, send)                                                                                                    │
                             │   61 │   │                                                                                                                                                 │
                             │ ❱ 62 │   │   await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)                                                                      │
                             │   63 │                                                                                                                                                     │
                             │   64 │   def http_exception(self, request: Request, exc: Exception) -> Response:                                                                           │
                             │   65 │   │   assert isinstance(exc, HTTPException)                                                                                                         │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py:53 in wrapped_app                                │
                             │                                                                                                                                                            │
                             │   50 │   │   │   │   handler = _lookup_exception_handler(exception_handlers, exc)                                                                          │
                             │   51 │   │   │                                                                                                                                             │
                             │   52 │   │   │   if handler is None:                                                                                                                       │
                             │ ❱ 53 │   │   │   │   raise exc                                                                                                                             │
                             │   54 │   │   │                                                                                                                                             │
                             │   55 │   │   │   if response_started:                                                                                                                      │
                             │   56 │   │   │   │   raise RuntimeError("Caught handled exception, but response already                                                                    │
                             │      started.") from exc                                                                                                                                   │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py:42 in wrapped_app                                │
                             │                                                                                                                                                            │
                             │   39 │   │   │   await send(message)                                                                                                                       │
                             │   40 │   │                                                                                                                                                 │
                             │   41 │   │   try:                                                                                                                                          │
                             │ ❱ 42 │   │   │   await app(scope, receive, sender)                                                                                                         │
                             │   43 │   │   except Exception as exc:                                                                                                                      │
                             │   44 │   │   │   handler = None                                                                                                                            │
                             │   45                                                                                                                                                       │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py:714 in __call__                                             │
                             │                                                                                                                                                            │
                             │   711 │   │   """                                                                                                                                          │
                             │   712 │   │   The main entry point to the Router class.                                                                                                    │
                             │   713 │   │   """                                                                                                                                          │
                             │ ❱ 714 │   │   await self.middleware_stack(scope, receive, send)                                                                                            │
                             │   715 │                                                                                                                                                    │
                             │   716 │   async def app(self, scope: Scope, receive: Receive, send: Send) -> None:                                                                         │
                             │   717 │   │   assert scope["type"] in ("http", "websocket", "lifespan")                                                                                    │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py:734 in app                                                  │
                             │                                                                                                                                                            │
                             │   731 │   │   │   match, child_scope = route.matches(scope)                                                                                                │
                             │   732 │   │   │   if match == Match.FULL:                                                                                                                  │
                             │   733 │   │   │   │   scope.update(child_scope)                                                                                                            │
                             │ ❱ 734 │   │   │   │   await route.handle(scope, receive, send)                                                                                             │
                             │   735 │   │   │   │   return                                                                                                                               │
                             │   736 │   │   │   elif match == Match.PARTIAL and partial is None:                                                                                         │
                             │   737 │   │   │   │   partial = route                                                                                                                      │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py:288 in handle                                               │
                             │                                                                                                                                                            │
                             │   285 │   │   │   │   response = PlainTextResponse("Method Not Allowed", status_code=405,                                                                  │
                             │       headers=headers)                                                                                                                                     │
                             │   286 │   │   │   await response(scope, receive, send)                                                                                                     │
                             │   287 │   │   else:                                                                                                                                        │
                             │ ❱ 288 │   │   │   await self.app(scope, receive, send)                                                                                                     │
                             │   289 │                                                                                                                                                    │
                             │   290 │   def __eq__(self, other: typing.Any) -> bool:                                                                                                     │
                             │   291 │   │   return (                                                                                                                                     │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py:76 in app                                                   │
                             │                                                                                                                                                            │
                             │    73 │   │   │   response = await f(request)                                                                                                              │
                             │    74 │   │   │   await response(scope, receive, send)                                                                                                     │
                             │    75 │   │                                                                                                                                                │
                             │ ❱  76 │   │   await wrap_app_handling_exceptions(app, request)(scope, receive, send)                                                                       │
                             │    77 │                                                                                                                                                    │
                             │    78 │   return app                                                                                                                                       │
                             │    79                                                                                                                                                      │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py:53 in wrapped_app                                │
                             │                                                                                                                                                            │
                             │   50 │   │   │   │   handler = _lookup_exception_handler(exception_handlers, exc)                                                                          │
                             │   51 │   │   │                                                                                                                                             │
                             │   52 │   │   │   if handler is None:                                                                                                                       │
                             │ ❱ 53 │   │   │   │   raise exc                                                                                                                             │
                             │   54 │   │   │                                                                                                                                             │
                             │   55 │   │   │   if response_started:                                                                                                                      │
                             │   56 │   │   │   │   raise RuntimeError("Caught handled exception, but response already                                                                    │
                             │      started.") from exc                                                                                                                                   │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py:42 in wrapped_app                                │
                             │                                                                                                                                                            │
                             │   39 │   │   │   await send(message)                                                                                                                       │
                             │   40 │   │                                                                                                                                                 │
                             │   41 │   │   try:                                                                                                                                          │
                             │ ❱ 42 │   │   │   await app(scope, receive, sender)                                                                                                         │
                             │   43 │   │   except Exception as exc:                                                                                                                      │
                             │   44 │   │   │   handler = None                                                                                                                            │
                             │   45                                                                                                                                                       │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py:73 in app                                                   │
                             │                                                                                                                                                            │
                             │    70 │   │   request = Request(scope, receive, send)                                                                                                      │
                             │    71 │   │                                                                                                                                                │
                             │    72 │   │   async def app(scope: Scope, receive: Receive, send: Send) -> None:                                                                           │
                             │ ❱  73 │   │   │   response = await f(request)                                                                                                              │
                             │    74 │   │   │   await response(scope, receive, send)                                                                                                     │
                             │    75 │   │                                                                                                                                                │
                             │    76 │   │   await wrap_app_handling_exceptions(app, request)(scope, receive, send)                                                                       │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py:301 in app                                                    │
                             │                                                                                                                                                            │
                             │    298 │   │   │   │   )                                                                                                                                   │
                             │    299 │   │   │   │   errors = solved_result.errors                                                                                                       │
                             │    300 │   │   │   │   if not errors:                                                                                                                      │
                             │ ❱  301 │   │   │   │   │   raw_response = await run_endpoint_function(                                                                                     │
                             │    302 │   │   │   │   │   │   dependant=dependant,                                                                                                        │
                             │    303 │   │   │   │   │   │   values=solved_result.values,                                                                                                │
                             │    304 │   │   │   │   │   │   is_coroutine=is_coroutine,                                                                                                  │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py:212 in run_endpoint_function                                  │
                             │                                                                                                                                                            │
                             │    209 │   assert dependant.call is not None, "dependant.call must be a function"                                                                          │
                             │    210 │                                                                                                                                                   │
                             │    211 │   if is_coroutine:                                                                                                                                │
                             │ ❱  212 │   │   return await dependant.call(**values)                                                                                                       │
                             │    213 │   else:                                                                                                                                           │
                             │    214 │   │   return await run_in_threadpool(dependant.call, **values)                                                                                    │
                             │    215                                                                                                                                                     │
                             │                                                                                                                                                            │
                             │ C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\issues.py:159 in force_finish_issue_endpoint                                        │
                             │                                                                                                                                                            │
                             │   156 │   await db.commit()                                                                                                                                │
                             │   157 │                                                                                                                                                    │
                             │   158 │   project = await ProjectService(db).get_by_id(project_id)                                                                                         │
                             │ ❱ 159 │   await event_service.notify({                                                                                                                     │
                             │   160 │   │   "type": "issue_status_changed",                                                                                                              │
                             │   161 │   │   "new_status": IssueStatus.FINISHED.value,                                                                                                    │
                             │   162 │   │   "project_id": project_id,                                                                                                                    │
                             ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                             AttributeError: 'EventService' object has no attribute 'notify'