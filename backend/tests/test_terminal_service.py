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
                issue_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )

            assert term["issue_id"] == "task-1"
            assert term["project_id"] == "proj-1"
            assert term["status"] == "active"
            assert len(service.list_active()) == 1

    def test_create_two_terminals_for_same_issue(self, service):
        """Two terminals for the same issue are both allowed (split pane support)."""
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term1 = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            term2 = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            assert term1["id"] != term2["id"]
            assert len(service.list_active()) == 2

    def test_create_uses_custom_shell(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            service.create(
                issue_id="t1",
                project_id="p1",
                project_path="C:/a",
                shell="powershell.exe",
            )
            mock_pty.spawn.assert_called_once_with("powershell.exe", cwd="C:/a")

    def test_kill_removes_terminal(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                issue_id="task-1",
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
                issue_id="task-1",
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

            service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            service.create(issue_id="t2", project_id="p2", project_path="C:/b")

            p1_terms = service.list_active(project_id="p1")
            assert len(p1_terms) == 1
            assert p1_terms[0]["project_id"] == "p1"

    def test_list_filter_by_issue(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            service.create(issue_id="t2", project_id="p1", project_path="C:/a")

            t1_terms = service.list_active(issue_id="t1")
            assert len(t1_terms) == 1

    def test_active_count(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            assert service.active_count() == 0
            service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            assert service.active_count() == 1

    def test_resize(self, service):
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(
                issue_id="task-1",
                project_id="proj-1",
                project_path="C:/fake/path",
            )
            service.resize(term["id"], 200, 50)
            updated = service.get(term["id"])
            assert updated["cols"] == 200
            assert updated["rows"] == 50
            mock_pty.set_size.assert_called_with(200, 50)

    def test_cleanup_is_noop_terminal_persists(self, service):
        """cleanup() is a no-op — terminal survives WebSocket disconnections."""
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            mock_pty.close = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            tid = term["id"]

            service.cleanup(tid)

            # Terminal must still be alive after cleanup
            assert len(service.list_active()) == 1
            mock_pty.close.assert_not_called()

    def test_cleanup_is_idempotent(self, service):
        """cleanup() called multiple times does not raise."""
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            mock_pty.close = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            tid = term["id"]

            service.cleanup(tid)
            service.cleanup(tid)  # second call — must not raise

    def test_is_alive(self, service):
        """is_alive() returns True for existing terminals, False otherwise."""
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            assert service.is_alive(term["id"]) is True
            assert service.is_alive("nonexistent") is False
            service.kill(term["id"])
            assert service.is_alive(term["id"]) is False

    def test_resize_concurrent_with_kill_does_not_crash(self, service):
        """resize() inside lock prevents races with concurrent kill."""
        import threading

        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            mock_pty.set_size = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            errors = []

            def do_resize():
                try:
                    service.resize(term["id"], 100, 25)
                except KeyError:
                    pass  # terminal may have been killed first — acceptable
                except Exception as exc:
                    errors.append(exc)

            def do_kill():
                try:
                    service.kill(term["id"])
                except KeyError:
                    pass

            t1 = threading.Thread(target=do_resize)
            t2 = threading.Thread(target=do_kill)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert errors == [], f"Unexpected exceptions: {errors}"


# --- buffer tests -----------------------------------------------------------


def test_append_output_overflow_trims_from_front(service):
    """Buffer che supera MAX_BUFFER_SIZE viene trimmato dal fronte (dati vecchi persi)."""
    from app.services.terminal_service import MAX_BUFFER_SIZE

    with patch("app.services.terminal_service.PTY") as MockPTY:
        mock_pty = MagicMock()
        mock_pty.spawn = MagicMock()
        MockPTY.return_value = mock_pty

        term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
        tid = term["id"]

        # Riempi il buffer con 'A' fino al limite, poi appendi altri MAX_BUFFER_SIZE 'B'
        # per provocare un overflow che elimina tutti gli 'A' dal fronte.
        service.append_output(tid, "A" * MAX_BUFFER_SIZE)
        service.append_output(tid, "B" * MAX_BUFFER_SIZE)

        result = service.get_buffered_output(tid)
        assert len(result.encode("utf-8")) <= MAX_BUFFER_SIZE
        assert "A" not in result, "I dati più vecchi (A) devono essere eliminati dal fronte"
        assert result == "B" * MAX_BUFFER_SIZE, "Solo i dati più recenti (B) devono rimanere"


def test_append_output_unknown_terminal_is_noop(service):
    """append_output su terminal_id inesistente non deve sollevare eccezioni."""
    service.append_output("nonexistent-id", "some data")  # must not raise


def test_get_buffered_output_empty(service):
    """Terminal appena creato: get_buffered_output ritorna stringa vuota."""
    with patch("app.services.terminal_service.PTY") as MockPTY:
        mock_pty = MagicMock()
        mock_pty.spawn = MagicMock()
        MockPTY.return_value = mock_pty

        term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
        result = service.get_buffered_output(term["id"])
        assert result == ""
