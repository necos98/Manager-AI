 5. pipeline_run_service.py:104-106 — Race condition commit prima del task spawn

  await self.session.commit()
  task = asyncio.create_task(self._execute(run.id, ...))
  Se crash tra commit e create_task, il chiamante vede successo ma la pipeline non parte mai.