Ennesimo bug quando provo ad aggiornare il nome di una pipeline:

INFO:     127.0.0.1:52313 - "PUT /api/pipelines/fae19dc5-1fd9-40e6-99da-1d989caa034f HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 799, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 409, in run_asgi
    |     result = await app(  # type: ignore[func-returns-value]
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |         self.scope, self.receive, self.send
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    |     return await self.app(scope, receive, send)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 93, in __call__
    |     await self.simple_response(scope, receive, send, request_headers=headers)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 144, in simple_response
    |     await self.app(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Users\j.magarelli\AppData\Local\Python\pythoncore-3.14-64\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\middleware\error_logger.py", line 45, in dispatch
    |     return await call_next(request)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 301, in app
    |     raw_response = await run_endpoint_function(
    |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     ...<3 lines>...
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 212, in run_endpoint_function
    |     return await dependant.call(**values)
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\pipelines.py", line 75, in update_pipeline
    |     response = _response(pipeline)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\pipelines.py", line 34, in _response
    |     updated_at=str(pipeline.updated_at) if pipeline.updated_at else None,
    |                                            ^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\attributes.py", line 569, in __get__
    |     return self.impl.get(state, dict_)  # type: ignore[no-any-return]
    |            ~~~~~~~~~~~~~^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\attributes.py", line 1096, in get
    |     value = self._fire_loader_callables(state, key, passive)
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\attributes.py", line 1126, in _fire_loader_callables
    |     return state._load_expired(state, passive)
    |            ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\state.py", line 828, in _load_expired
    |     self.manager.expired_attribute_loader(self, toload, passive)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\loading.py", line 1674, in load_scalar_attributes
    |     result = load_on_ident(
    |         session,
    |     ...<4 lines>...
    |         no_autoflush=no_autoflush,
    |     )
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\loading.py", line 510, in load_on_ident
    |     return load_on_pk_identity(
    |         session,
    |     ...<11 lines>...
    |         is_user_refresh=is_user_refresh,
    |     )
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\loading.py", line 695, in load_on_pk_identity
    |     session.execute(
    |     ~~~~~~~~~~~~~~~^
    |         q,
    |         ^^
    |     ...<2 lines>...
    |         bind_arguments=bind_arguments,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2351, in execute
    |     return self._execute_internal(
    |            ~~~~~~~~~~~~~~~~~~~~~~^
    |         statement,
    |         ^^^^^^^^^^
    |     ...<4 lines>...
    |         _add_event=_add_event,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2249, in _execute_internal
    |     result: Result[Any] = compile_state_cls.orm_execute_statement(
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         self,
    |         ^^^^^
    |     ...<4 lines>...
    |         conn,
    |         ^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\context.py", line 306, in orm_execute_statement
    |     result = conn.execute(
    |         statement, params or {}, execution_options=execution_options
    |     )
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1419, in execute
    |     return meth(
    |         self,
    |         distilled_parameters,
    |         execution_options or NO_OPTIONS,
    |     )
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\sql\elements.py", line 527, in _execute_on_connection
    |     return connection._execute_clauseelement(
    |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         self, distilled_params, execution_options
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1641, in _execute_clauseelement
    |     ret = self._execute_context(
    |         dialect,
    |     ...<8 lines>...
    |         cache_hit=cache_hit,
    |     )
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1846, in _execute_context
    |     return self._exec_single_context(
    |            ~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         dialect, context, statement, parameters
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1986, in _exec_single_context
    |     self._handle_dbapi_exception(
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         e, str_statement, effective_parameters, cursor, context
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 2366, in _handle_dbapi_exception
    |     raise exc_info[1].with_traceback(exc_info[2])
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1967, in _exec_single_context
    |     self.dialect.do_execute(
    |     ~~~~~~~~~~~~~~~~~~~~~~~^
    |         cursor, str_statement, effective_parameters, context
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\default.py", line 952, in do_execute
    |     cursor.execute(statement, parameters)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 182, in execute
    |     self._adapt_connection._handle_exception(error)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 342, in _handle_exception
    |     raise error
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 159, in execute
    |     _cursor: AsyncIODBAPICursor = self.await_(self._connection.cursor())  # type: ignore[arg-type] # noqa: E501
    |                                   ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 123, in await_only
    |     raise exc.MissingGreenlet(
    |     ...<2 lines>...
    |     )
    | sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\j.magarelli\AppData\Local\Python\pythoncore-3.14-64\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\middleware\error_logger.py", line 45, in dispatch
    return await call_next(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 301, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\fastapi\routing.py", line 212, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\pipelines.py", line 75, in update_pipeline
    response = _response(pipeline)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\pipelines.py", line 34, in _response
    updated_at=str(pipeline.updated_at) if pipeline.updated_at else None,
                                           ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\attributes.py", line 569, in __get__
    return self.impl.get(state, dict_)  # type: ignore[no-any-return]
           ~~~~~~~~~~~~~^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\attributes.py", line 1096, in get
    value = self._fire_loader_callables(state, key, passive)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\attributes.py", line 1126, in _fire_loader_callables
    return state._load_expired(state, passive)
           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\state.py", line 828, in _load_expired
    self.manager.expired_attribute_loader(self, toload, passive)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\loading.py", line 1674, in load_scalar_attributes
    result = load_on_ident(
        session,
    ...<4 lines>...
        no_autoflush=no_autoflush,
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\loading.py", line 510, in load_on_ident
    return load_on_pk_identity(
        session,
    ...<11 lines>...
        is_user_refresh=is_user_refresh,
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\loading.py", line 695, in load_on_pk_identity
    session.execute(
    ~~~~~~~~~~~~~~~^
        q,
        ^^
    ...<2 lines>...
        bind_arguments=bind_arguments,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2351, in execute
    return self._execute_internal(
           ~~~~~~~~~~~~~~~~~~~~~~^
        statement,
        ^^^^^^^^^^
    ...<4 lines>...
        _add_event=_add_event,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2249, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        self,
        ^^^^^
    ...<4 lines>...
        conn,
        ^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\context.py", line 306, in orm_execute_statement
    result = conn.execute(
        statement, params or {}, execution_options=execution_options
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1419, in execute
    return meth(
        self,
        distilled_parameters,
        execution_options or NO_OPTIONS,
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\sql\elements.py", line 527, in _execute_on_connection
    return connection._execute_clauseelement(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        self, distilled_params, execution_options
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1641, in _execute_clauseelement
    ret = self._execute_context(
        dialect,
    ...<8 lines>...
        cache_hit=cache_hit,
    )
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ~~~~~~~~~~~~~~~~~~~~~~~~~^
        dialect, context, statement, parameters
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        e, str_statement, effective_parameters, cursor, context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 2366, in _handle_dbapi_exception
    raise exc_info[1].with_traceback(exc_info[2])
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
    ~~~~~~~~~~~~~~~~~~~~~~~^
        cursor, str_statement, effective_parameters, context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\default.py", line 952, in do_execute
    cursor.execute(statement, parameters)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 182, in execute
    self._adapt_connection._handle_exception(error)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 342, in _handle_exception
    raise error
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 159, in execute
    _cursor: AsyncIODBAPICursor = self.await_(self._connection.cursor())  # type: ignore[arg-type] # noqa: E501
                                  ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 123, in await_only
    raise exc.MissingGreenlet(
    ...<2 lines>...
    )
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)