import pytest
from app.services.wsl_support import quote_url_for_shell


class TestQuoteUrlForShell:
    def test_normal_url_wsl(self):
        """shlex.quote leaves safe URLs unquoted (no special chars)."""
        result = quote_url_for_shell("http://192.168.1.1:8000/mcp/", is_wsl=True)
        assert result == "http://192.168.1.1:8000/mcp/"

    def test_normal_url_cmd(self):
        result = quote_url_for_shell("http://192.168.1.1:8000/mcp/", is_wsl=False)
        assert result == '"http://192.168.1.1:8000/mcp/"'

    def test_metacharacters_wsl(self):
        result = quote_url_for_shell("http://x;rm -rf /:8000/", is_wsl=True)
        assert result == "'http://x;rm -rf /:8000/'"

    def test_spaces_wsl(self):
        result = quote_url_for_shell("http://x y:8000/", is_wsl=True)
        assert result == "'http://x y:8000/'"

    def test_empty_wsl(self):
        result = quote_url_for_shell("", is_wsl=True)
        assert result == "''"

    def test_empty_cmd(self):
        result = quote_url_for_shell("", is_wsl=False)
        assert result == '""'

    def test_url_with_backtick_wsl(self):
        result = quote_url_for_shell("http://x`whoami`:8000/", is_wsl=True)
        assert result == "'http://x`whoami`:8000/'"

    def test_url_with_dollar_paren_wsl(self):
        result = quote_url_for_shell("http://x$(id):8000/", is_wsl=True)
        assert result == "'http://x$(id):8000/'"
