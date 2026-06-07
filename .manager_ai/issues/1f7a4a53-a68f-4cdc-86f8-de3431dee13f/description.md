26. alembic/env.py:9 — Importa solo 3 modelli

  from app.models import Project, Question, Task
  Molti modelli (Agent, Pipeline, PipelineRun, Issue, Memory...) non importati esplicitamente. Se import ordering
  cambia, Alembic non rileva tabelle.