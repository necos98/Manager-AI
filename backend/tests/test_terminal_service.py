import pytest
from unittest.mock import patch, MagicMock
from app.services.terminal_service import TerminalService


@pytest.fixture
def service():
    svc = TerminalService()
    yield svc
    # Cleanup: kill any spawned terminals
    for tid in list(svc._terminals.keys()):
        try:
            svc.kill(tid)
        except Exception:
            pass


class TestTerminalServiceRegistry:
    def test_list_empty(self, service):
        assert service.list_active() == []

    def test_create_and_list(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )

            assert term["task_id"] == "task-1"
            assert term["project_id"] == "proj-1"
            assert term["status"] == "active"
            assert len(service.list_active()) == 1

    def test_create_duplicate_task_returns_existing(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term1 = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            term2 = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            assert term1["id"] == term2["id"]
            assert len(service.list_active()) == 1

    def test_kill_removes_terminal(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            service.kill(term["id"])
            assert len(service.list_active()) == 0

    def test_kill_nonexistent_raises(self, service):
        with pytest.raises(KeyError):
            service.kill("nonexistent")

    def test_get_by_id(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            found = service.get(term["id"])
            assert found["id"] == term["id"]

    def test_get_nonexistent_raises(self, service):
        with pytest.raises(KeyError):
            service.get("nonexistent")

    def test_list_filter_by_project(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            service.create(task_id="t1", project_id="p1", project_path="C:/a")
            service.create(task_id="t2", project_id="p2", project_path="C:/b")

            p1_terms = service.list_active(project_id="p1")
            assert len(p1_terms) == 1
            assert p1_terms[0]["project_id"] == "p1"

    def test_list_filter_by_task(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            service.create(task_id="t1", project_id="p1", project_path="C:/a")
            service.create(task_id="t2", project_id="p1", project_path="C:/a")

            t1_terms = service.list_active(task_id="t1")
            assert len(t1_terms) == 1

    def test_active_count(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            assert service.active_count() == 0
            service.create(task_id="t1", project_id="p1", project_path="C:/a")
            assert service.active_count() == 1

    def test_resize(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                task_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            service.resize(term["id"], 200, 50)
            updated = service.get(term["id"])
            assert updated["cols"] == 200
            assert updated["rows"] == 50
            mock_pty.set_size.assert_called_with(200, 50)
