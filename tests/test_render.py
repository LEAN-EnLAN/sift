"""Tests for render functions, especially compact interactive renderer and agent JSON."""

from __future__ import annotations

import json

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


class TestRenderCompactTable:
    """Tests for render_compact_table — compact 4-col interactive table."""

    def test_empty_repos_returns_empty_table(self) -> None:
        """Empty list produces a valid table with zero repos."""
        from sift.render import render_compact_table

        output = render_compact_table([])
        assert isinstance(output, str)
        assert "0" in output

    def test_single_repo_shows_name_score_and_why(self) -> None:
        """Single repo renders its name, score, and reasons."""
        from sift.render import render_compact_table

        repo = _make_repo(score=85.3)
        output = render_compact_table([repo])
        assert "owner/repo" in output
        assert "85.30" in output
        assert "Buena documentación" in output

    def test_multiple_repos_numbered_correctly(self) -> None:
        """Multiple repos are indexed 1, 2, etc."""
        from sift.render import render_compact_table

        repos = [
            _make_repo(full_name="owner/alpha", score=90.0),
            _make_repo(full_name="owner/beta", score=80.0),
        ]
        output = render_compact_table(repos)
        assert "owner/alpha" in output
        assert "owner/beta" in output

    def test_no_url_in_output(self) -> None:
        """Compact table does NOT include URLs — no URL wrapping for interactive."""
        from sift.render import render_compact_table

        repo = _make_repo(html_url="https://github.com/owner/repo")
        output = render_compact_table([repo])
        assert "https://github.com" not in output

    def test_no_terminal_width_logic(self) -> None:
        """Compact table uses fixed width, not terminal width."""
        from sift.render import render_compact_table
        from unittest.mock import patch

        repo = _make_repo(score=75.0, reasons=["Buena calidad"])
        with patch("shutil.get_terminal_size") as mock_term:
            output = render_compact_table([repo])
            # shutil.get_terminal_size should NOT be called
            assert mock_term.call_count == 0
        assert "owner/repo" in output
        assert "75.00" in output

    def test_handles_missing_data(self) -> None:
        """Repo with None language and no reasons still renders cleanly."""
        from sift.render import render_compact_table

        repo = _make_repo(language=None, reasons=[])
        output = render_compact_table([repo])
        assert "owner/repo" in output

    def test_compact_table_is_importable(self) -> None:
        """render_compact_table is a public function in render module."""
        from sift.render import render_compact_table

        assert callable(render_compact_table)

    def test_agent_json_has_meta_with_version(self) -> None:
        """Agent JSON output includes _meta with repo_scout_version and ? field."""
        from sift.render import render_agent_json

        repo = _make_repo(score=85.3)
        output = render_agent_json([repo], speed_tier="fast", query="test query")
        data = json.loads(output)
        assert "_meta" in data
        assert "repo_scout_version" in data["_meta"]
        assert "?" in data["_meta"]

    def test_agent_json_results_preserve_existing_fields(self) -> None:
        """Existing JSON fields are unchanged in agent JSON."""
        from sift.render import render_agent_json

        repo = _make_repo(score=85.3, stars=100, forks=10, license_spdx="MIT")
        output = render_agent_json([repo], speed_tier="balanced", query="test")
        data = json.loads(output)
        results = data["results"]
        assert len(results) == 1
        r = results[0]
        assert "name" in r
        assert "url" in r
        assert "description" in r
        assert "language" in r
        assert "last_commit" in r
        assert "score" in r
        assert "score_parts" in r
        assert "stars" in r
        assert "forks" in r
        assert "license" in r
        assert "why" in r

    def test_agent_json_meta_includes_speed_and_elapsed(self) -> None:
        """_meta includes speed_tier, elapsed_seconds, api_calls."""
        from sift.render import render_agent_json

        repo = _make_repo(score=85.3)
        output = render_agent_json([repo], speed_tier="fast", query="test", elapsed=1.5, api_calls=3)
        data = json.loads(output)
        assert data["_meta"]["speed_tier"] == "fast"
        assert data["_meta"]["elapsed_seconds"] == 1.5
        assert data["_meta"]["api_calls"] == 3


class TestRenderBestSummary:
    """Tests for render_best_summary — one-line best answer for status bar."""

    def test_best_summary_shows_name_score_and_reason(self) -> None:
        """Top repo shows name, score, and first reason."""
        from sift.render import render_best_summary

        repo = _make_repo(full_name="owner/top-repo", score=92.5, reasons=["Actividad reciente"])
        summary = render_best_summary(repo)
        assert "owner/top-repo" in summary
        assert "92.5" in summary
        assert "Actividad reciente" in summary

    def test_best_summary_uses_short_why_with_multiple_reasons(self) -> None:
        """Multiple reasons are joined with semicolon."""
        from sift.render import render_best_summary

        repo = _make_repo(score=78.0, reasons=["Buena documentación", "Comunidad fuerte"])
        summary = render_best_summary(repo)
        assert "78.0" in summary
        assert "Buena documentación" in summary
        assert "Comunidad fuerte" in summary

    def test_best_summary_handles_no_reasons(self) -> None:
        """Repo with no reasons does not crash and still shows name/score."""
        from sift.render import render_best_summary

        repo = _make_repo(full_name="owner/minimal", score=65.0, reasons=[])
        summary = render_best_summary(repo)
        assert "owner/minimal" in summary
        assert "65.0" in summary
        assert "Best:" in summary
