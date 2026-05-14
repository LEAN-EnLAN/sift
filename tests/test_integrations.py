"""Tests for Hermes and n8n integration output contracts.

Covers:
- Hermes: _meta with hermes_compliance, no '?' hint key
- n8n: raw JSON array, no _meta envelope
- Determinism for same input (excluding elapsed_seconds)
- Error handling: non-zero exit, no fake success JSON on stdout
- Empty results: valid JSON, exit 0
"""

from __future__ import annotations

import json
from unittest.mock import patch

from sift.models import RepoCandidate


def _make_repo(**overrides: object) -> RepoCandidate:
    values: dict = {
        "full_name": "owner/repo",
        "html_url": "https://github.com/owner/repo",
        "description": "A test repository",
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
        "topics": ["test"],
        "search_rank_score": 1.0,
        "reasons": ["Buena documentación", "Alta actividad reciente"],
    }
    values.update(**overrides)
    return RepoCandidate(**values)


class TestHermesCompliance:
    """Hermes output: _meta with hermes_compliance='1.0', no '?' hint key."""

    def test_hermes_compliance_field_present(self) -> None:
        """render_hermes_json output has hermes_compliance in _meta."""
        from sift.render import render_hermes_json

        repo = _make_repo(score=85.3)
        output = render_hermes_json([repo], speed_tier="balanced", query="test", elapsed=1.2, api_calls=1)
        data = json.loads(output)
        assert data["_meta"]["hermes_compliance"] == "1.0"

    def test_hermes_omits_hint_key(self) -> None:
        """render_hermes_json output does NOT include the '?' hint key."""
        from sift.render import render_hermes_json

        repo = _make_repo(score=85.3)
        output = render_hermes_json([repo], speed_tier="balanced", query="test")
        data = json.loads(output)
        assert "?" not in data["_meta"]

    def test_hermes_has_results_like_agent(self) -> None:
        """Hermes output includes results array with same fields as agent JSON."""
        from sift.render import render_hermes_json

        repo = _make_repo(score=85.3, stars=200, forks=20, license_spdx="Apache-2.0")
        output = render_hermes_json([repo], speed_tier="fast", query="jwt auth", elapsed=0.5, api_calls=1)
        data = json.loads(output)
        results = data["results"]
        assert len(results) == 1
        r = results[0]
        assert r["name"] == "owner/repo"
        assert r["score"] == 85.3
        assert r["stars"] == 200
        assert r["forks"] == 20
        assert r["license"] == "Apache-2.0"

    def test_hermes_empty_results_valid_json(self) -> None:
        """Empty results still return valid JSON with _meta."""
        from sift.render import render_hermes_json

        output = render_hermes_json([], speed_tier="balanced", query="test", elapsed=0.1, api_calls=0)
        data = json.loads(output)
        assert "_meta" in data
        assert "results" in data
        assert data["results"] == []
        assert data["_meta"]["hermes_compliance"] == "1.0"


class TestN8nOutput:
    """n8n output: raw JSON array, no _meta envelope."""

    def test_n8n_is_raw_array(self) -> None:
        """render_n8n_json returns a raw JSON array, not an object with _meta."""
        from sift.render import render_n8n_json

        repo = _make_repo(score=85.3)
        output = render_n8n_json([repo])
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "owner/repo"

    def test_n8n_no_meta_envelope(self) -> None:
        """n8n output does NOT contain _meta key."""
        from sift.render import render_n8n_json

        repo = _make_repo(score=85.3)
        output = render_n8n_json([repo])
        data = json.loads(output)
        assert "_meta" not in data

    def test_n8n_empty_results_valid_json(self) -> None:
        """Empty n8n results return an empty JSON array."""
        from sift.render import render_n8n_json

        output = render_n8n_json([])
        data = json.loads(output)
        assert data == []


class TestIntegrationCliRouting:
    """CLI routing: --hermes and --n8n flags trigger correct output."""

    def test_hermes_flag_parsed(self) -> None:
        """--hermes flag is parsed correctly."""
        from sift.cli import parse_args

        args = parse_args(["-q", "test", "-l", "Python", "--hermes"])
        assert args.hermes is True

    def test_n8n_flag_parsed(self) -> None:
        """--n8n flag is parsed correctly."""
        from sift.cli import parse_args

        args = parse_args(["-q", "test", "-l", "Python", "--n8n"])
        assert args.n8n is True

    def test_hermes_flag_defaults_false(self) -> None:
        """--hermes defaults to False."""
        from sift.cli import parse_args

        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.hermes is False

    def test_n8n_flag_defaults_false(self) -> None:
        """--n8n defaults to False."""
        from sift.cli import parse_args

        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.n8n is False

    def test_hermes_cli_emits_hermes_json(self, capsys: object) -> None:
        """--hermes routes to render_hermes_json and prints valid Hermes JSON to stdout."""
        from sift.cli import main

        repo = _make_repo(score=85.3)
        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sift.cli.run", return_value=[repo]),
        ):
            result = main(["-q", "test", "-l", "Python", "--hermes"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "_meta" in data
        assert data["_meta"]["hermes_compliance"] == "1.0"
        assert "?" not in data["_meta"]
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "owner/repo"
        assert data["results"][0]["score"] == 85.3

    def test_n8n_cli_emits_raw_array(self, capsys: object) -> None:
        """--n8n routes to render_n8n_json and prints raw JSON array to stdout."""
        from sift.cli import main

        repo = _make_repo(score=85.3)
        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sift.cli.run", return_value=[repo]),
        ):
            result = main(["-q", "test", "-l", "Python", "--n8n"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "owner/repo"
        assert data[0]["score"] == 85.3
        assert "_meta" not in data

    def test_hermes_empty_results_exit_zero(self, capsys: object) -> None:
        """--hermes with empty results returns exit 0 and valid JSON with _meta."""
        from sift.cli import main

        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sift.cli.run", return_value=[]),
        ):
            result = main(["-q", "test", "-l", "Python", "--hermes"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "_meta" in data
        assert data["_meta"]["hermes_compliance"] == "1.0"
        assert data["results"] == []

    def test_n8n_empty_results_exit_zero(self, capsys: object) -> None:
        """--n8n with empty results returns exit 0 and valid empty JSON array."""
        from sift.cli import main

        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sift.cli.run", return_value=[]),
        ):
            result = main(["-q", "test", "-l", "Python", "--n8n"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data == []


class TestDeterminism:
    """Deterministic output for same input, excluding elapsed_seconds."""

    def test_hermes_deterministic_except_elapsed(self) -> None:
        """Same repos produce same Hermes output when elapsed is normalized."""
        from sift.render import render_hermes_json

        repo = _make_repo(score=85.3, stars=200)
        out1 = render_hermes_json([repo], speed_tier="balanced", query="test", elapsed=1.0, api_calls=1)
        out2 = render_hermes_json([repo], speed_tier="balanced", query="test", elapsed=2.0, api_calls=1)
        data1 = json.loads(out1)
        data2 = json.loads(out2)
        # Remove elapsed_seconds for comparison
        data1["_meta"].pop("elapsed_seconds", None)
        data2["_meta"].pop("elapsed_seconds", None)
        assert data1 == data2

    def test_n8n_deterministic(self) -> None:
        """Same repos produce identical n8n output."""
        from sift.render import render_n8n_json

        repo = _make_repo(score=85.3, stars=200)
        out1 = render_n8n_json([repo])
        out2 = render_n8n_json([repo])
        assert out1 == out2


class TestErrorHandling:
    """Error paths: non-zero exit, errors to stderr, no fake success JSON."""

    def test_hermes_missing_query_returns_error(self) -> None:
        """--hermes without --query returns exit 2."""
        from sift.cli import main

        with patch("sift.cli.is_interactive", return_value=False):
            result = main(["-l", "Python", "--hermes"])
        assert result == 2

    def test_hermes_missing_language_returns_error(self) -> None:
        """--hermes without --language returns exit 2."""
        from sift.cli import main

        with patch("sift.cli.is_interactive", return_value=False):
            result = main(["-q", "test", "--hermes"])
        assert result == 2

    def test_n8n_missing_query_returns_error(self) -> None:
        """--n8n without --query returns exit 2."""
        from sift.cli import main

        with patch("sift.cli.is_interactive", return_value=False):
            result = main(["-l", "Python", "--n8n"])
        assert result == 2

    def test_n8n_missing_language_returns_error(self) -> None:
        """--n8n without --language returns exit 2."""
        from sift.cli import main

        with patch("sift.cli.is_interactive", return_value=False):
            result = main(["-q", "test", "--n8n"])
        assert result == 2

    def test_error_does_not_contaminate_stdout(self) -> None:
        """Error path writes to stderr, stdout stays clean."""
        import io
        from sift.cli import main

        stdout_capture = io.StringIO()
        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sys.stdout", stdout_capture),
        ):
            result = main(["-l", "Python", "--hermes"])
        assert result == 2
        assert stdout_capture.getvalue().strip() == ""
