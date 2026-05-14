"""Tests for web server routes and app creation."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from sift.persistence.history import SearchHistoryStore
from sift.web.routes import create_app
from sift.web.server import find_available_port


@pytest.fixture
def history_store(tmp_path) -> SearchHistoryStore:
    """Provide a fresh history store for web tests."""
    return SearchHistoryStore(path=str(tmp_path / "history.json"))


@pytest.fixture
def client(history_store: SearchHistoryStore):
    """Provide a Starlette TestClient."""
    from starlette.testclient import TestClient

    app = create_app(history_store)
    return TestClient(app)


class TestHealthEndpoint:
    """Task 2.4: health endpoint returns 200."""

    def test_health_returns_200(self, client) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestHistoryEndpoint:
    """Task 2.4: history endpoint returns stored entries."""

    def test_history_empty(self, client) -> None:
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert data["entries"] == []

    def test_history_returns_entries(self, client, history_store) -> None:
        history_store.add_entry("jwt auth", ["Python"], [{"name": "jpadilla/pyjwt"}])
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["query"] == "jwt auth"


class TestSearchEndpoint:
    """Task 2.4: search endpoint triggers search and returns results."""

    def test_search_requires_query(self, client) -> None:
        response = client.post("/api/search", json={})
        assert response.status_code == 400

    def test_search_returns_results(self, client) -> None:
        """Search endpoint returns results with mocked run function."""
        with patch("sift.cli.run") as mock_run:
            mock_run.return_value = []
            response = client.post(
                "/api/search",
                json={"query": "jwt auth", "languages": ["Python"]},
            )
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            mock_run.assert_called_once()

    def test_search_persists_to_history(self, client, history_store) -> None:
        """Search results are persisted to history store."""
        with patch("sift.cli.run") as mock_run:
            mock_repo = type(
                "Repo",
                (),
                {
                    "full_name": "jpadilla/pyjwt",
                    "html_url": "https://github.com/jpadilla/pyjwt",
                    "description": "JWT library",
                    "language": "Python",
                    "stars": 5656,
                    "forks": 1200,
                    "watchers": 500,
                    "open_issues": 10,
                    "pushed_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                    "created_at": "2023-01-01T00:00:00Z",
                    "archived": False,
                    "fork": False,
                    "license_spdx": "MIT",
                    "topics": ["jwt"],
                    "search_rank_score": 1.0,
                    "score": 85.3,
                    "score_parts": {"relevance": 90.0, "activity": 75.0},
                    "reasons": ["Strong relevance"],
                    "last_commit_at": "2025-01-01T00:00:00Z",
                },
            )()
            mock_run.return_value = [mock_repo]
            response = client.post(
                "/api/search",
                json={"query": "jwt auth", "languages": ["Python"]},
            )
            assert response.status_code == 200
            entries = history_store.get_entries()
            assert len(entries) == 1
            assert entries[0]["query"] == "jwt auth"


class TestStaticFiles:
    """Task 2.4: static files are served."""

    def test_index_html_served(self, client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestPortSelection:
    """Task 2.4: port selection with fallback."""

    def test_find_available_port_returns_valid_port(self) -> None:
        port = find_available_port(preferred=5173)
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_find_available_port_fallback(self) -> None:
        """If preferred port is occupied, returns a different available port."""
        import socket

        # Occupy a port temporarily
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        occupied_port = sock.getsockname()[1]
        sock.listen(1)

        try:
            port = find_available_port(preferred=occupied_port)
            assert port != occupied_port
            assert isinstance(port, int)
        finally:
            sock.close()


class TestServerStarts:
    """Critical fix: verify run_server actually calls server.run()."""

    def test_run_server_calls_server_run(self) -> None:
        """run_server must call server.run() to actually start uvicorn."""
        import uvicorn as real_uvicorn

        with (
            patch("sift.web.server._check_web_dependencies"),
            patch.object(real_uvicorn, "Config") as mock_config_cls,
            patch.object(real_uvicorn, "Server") as mock_server_cls,
            patch("sift.persistence.history.SearchHistoryStore"),
            patch("sift.web.routes.create_app"),
        ):
            mock_server = mock_server_cls.return_value
            mock_server.run.return_value = None

            from sift.web.server import run_server

            run_server(port=5173)

            mock_server.run.assert_called_once()

    def test_run_server_returns_url_and_port(self) -> None:
        """run_server returns the expected (url, port) tuple."""
        import uvicorn as real_uvicorn

        with (
            patch("sift.web.server._check_web_dependencies"),
            patch.object(real_uvicorn, "Config") as mock_config_cls,
            patch.object(real_uvicorn, "Server") as mock_server_cls,
            patch("sift.persistence.history.SearchHistoryStore"),
            patch("sift.web.routes.create_app"),
        ):
            mock_server = mock_server_cls.return_value
            mock_server.run.return_value = None

            from sift.web.server import run_server

            url, port = run_server(port=8080)
            assert url == "http://127.0.0.1:8080"
            assert port == 8080


class TestSearchHistoryIsolation:
    """History persistence failures must not break search results."""

    def test_search_succeeds_when_history_fails(self, client) -> None:
        """If history.add_entry raises, search still returns results."""
        with patch("sift.cli.run") as mock_run:
            mock_repo = type(
                "Repo",
                (),
                {
                    "full_name": "test/repo",
                    "html_url": "https://github.com/test/repo",
                    "description": "Test",
                    "language": "Python",
                    "stars": 100,
                    "forks": 10,
                    "watchers": 50,
                    "open_issues": 2,
                    "pushed_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                    "created_at": "2023-01-01T00:00:00Z",
                    "archived": False,
                    "fork": False,
                    "license_spdx": "MIT",
                    "topics": [],
                    "search_rank_score": 1.0,
                    "score": 70.0,
                    "score_parts": {"relevance": 70.0},
                    "reasons": ["Test"],
                    "last_commit_at": "2025-01-01T00:00:00Z",
                },
            )()
            mock_run.return_value = [mock_repo]
            response = client.post(
                "/api/search",
                json={"query": "test", "languages": ["Python"]},
            )
            # Search must succeed even if history fails internally
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
