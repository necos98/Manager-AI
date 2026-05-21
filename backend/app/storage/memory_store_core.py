from __future__ import annotations

from typing import Any


class MemoryStore:
    """RAM-first store. Source of truth for all records at runtime.

    _projects: dict[project_path, dict[store_type, StoreData]]
    StoreData = {"records": dict[id, Record], "index": list[IndexEntry]}
    """

    def __init__(self) -> None:
        self._projects: dict[str, dict[str, dict[str, Any]]] = {}

    # --- project lifecycle ---

    def has_project(self, project_path: str) -> bool:
        return project_path in self._projects

    def init_project(
        self,
        project_path: str,
        store_type: str,
        records: dict[str, Any],
        index: list[dict[str, Any]],
    ) -> None:
        if project_path not in self._projects:
            self._projects[project_path] = {}
        self._projects[project_path][store_type] = {
            "records": records,
            "index": index,
        }

    def remove_project(self, project_path: str) -> None:
        self._projects.pop(project_path, None)

    # --- CRUD ---

    def get(self, project_path: str, store_type: str, record_id: str) -> Any | None:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return None
        return store["records"].get(record_id)

    def list_index(self, project_path: str, store_type: str) -> list[dict[str, Any]]:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return []
        return list(store["index"])

    def list_all(self, project_path: str, store_type: str) -> list[Any]:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return []
        return list(store["records"].values())

    def upsert(
        self,
        project_path: str,
        store_type: str,
        record_id: str,
        record: Any,
        index_entry: dict[str, Any],
    ) -> None:
        store = self._ensure(project_path, store_type)
        store["records"][record_id] = record
        idx = store["index"]
        for i, e in enumerate(idx):
            if e.get("id") == record_id:
                idx[i] = index_entry
                break
        else:
            idx.append(index_entry)
        idx.sort(key=lambda e: (e.get("created_at", ""), e.get("id", "")))

    def delete(self, project_path: str, store_type: str, record_id: str) -> None:
        store = self._projects.get(project_path, {}).get(store_type)
        if store is None:
            return
        store["records"].pop(record_id, None)
        store["index"] = [e for e in store["index"] if e.get("id") != record_id]

    def reset(self) -> None:
        self._projects.clear()

    def _ensure(self, project_path: str, store_type: str) -> dict:
        p = self._projects.setdefault(project_path, {})
        return p.setdefault(store_type, {"records": {}, "index": []})


memory_store = MemoryStore()
