Bug su ordinamento record degli agenti in una pipeline:

INFO:     127.0.0.1:61834 - "PUT /api/pipelines/fae19dc5-1fd9-40e6-99da-1d989caa034f/steps/reorder HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
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
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 164, in execute
    self.await_(_cursor.execute(operation, parameters))
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 40, in execute
    await self._execute(self._cursor.execute, sql, parameters)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 32, in _execute
    return await self._conn._execute(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 122, in _execute
    return await future
           ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 105, in run
    result = function()
sqlite3.IntegrityError: UNIQUE constraint failed: pipeline_steps.pipeline_id, pipeline_steps.order_index

The above exception was the direct cause of the following exception:

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
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\routers\pipelines.py", line 128, in reorder_steps
    steps = await svc.reorder_steps(pipeline_id, data.step_ids)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\services\pipeline_service.py", line 114, in reorder_steps
    result = await self.session.execute(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<4 lines>...
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\ext\asyncio\session.py", line 449, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 203, in greenlet_spawn
    result = context.switch(value)
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
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2228, in _execute_internal
    ) = compile_state_cls.orm_pre_session_exec(
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        self,
        ^^^^^
    ...<4 lines>...
        False,
        ^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\context.py", line 577, in orm_pre_session_exec
    session._autoflush()
    ~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 3051, in _autoflush
    raise e.with_traceback(sys.exc_info()[2])
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 3040, in _autoflush
    self.flush()
    ~~~~~~~~~~^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 4331, in flush
    self._flush(objects)
    ~~~~~~~~~~~^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 4466, in _flush
    with util.safe_reraise():
         ~~~~~~~~~~~~~~~~~^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 121, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\session.py", line 4427, in _flush
    flush_context.execute()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py", line 466, in execute
    rec.execute(self)
    ~~~~~~~~~~~^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\unitofwork.py", line 642, in execute
    util.preloaded.orm_persistence.save_obj(
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        self.mapper,
        ^^^^^^^^^^^^
        uow.states_for_mapper_hierarchy(self.mapper, False, False),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        uow,
        ^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\persistence.py", line 85, in save_obj
    _emit_update_statements(
    ~~~~~~~~~~~~~~~~~~~~~~~^
        base_mapper,
        ^^^^^^^^^^^^
    ...<3 lines>...
        update,
        ^^^^^^^
    )
    ^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\orm\persistence.py", line 912, in _emit_update_statements
    c = connection.execute(
        statement, multiparams, execution_options=execution_options
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
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 2363, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
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
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\dialects\sqlite\aiosqlite.py", line 164, in execute
    self.await_(_cursor.execute(operation, parameters))
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 132, in await_only
    return current.parent.switch(awaitable)  # type: ignore[no-any-return,attr-defined] # noqa: E501
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 196, in greenlet_spawn
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 40, in execute
    await self._execute(self._cursor.execute, sql, parameters)
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\cursor.py", line 32, in _execute
    return await self._conn._execute(fn, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 122, in _execute
    return await future
           ^^^^^^^^^^^^
  File "C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\venv\Lib\site-packages\aiosqlite\core.py", line 105, in run
    result = function()
sqlalchemy.exc.IntegrityError: (raised as a result of Query-invoked autoflush; consider using a session.no_autoflush block if this flush is occurring prematurely)
(sqlite3.IntegrityError) UNIQUE constraint failed: pipeline_steps.pipeline_id, pipeline_steps.order_index
[SQL: UPDATE pipeline_steps SET order_index=?, updated_at=CURRENT_TIMESTAMP WHERE pipeline_steps.id = ?]
[parameters: (2, '39cf923b-a6fd-4a89-b024-0c26add562fc')]
(Background on this error at: https://sqlalche.me/e/20/gkpj)