10. issue_service.py:110-116 — get_by_id() scan O(n) di tutti i progetti

  for project in await ProjectService(self.session).list_all(archived=False):
      rec = issue_store.load_issue(project.path, issue_id)
  Con 50 progetti = 50 letture disco per ogni lookup.
  Fix: Mantenere indice issue_id → project_id in memoria.