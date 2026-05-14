"""Tests for CLI argument parsing and main branching."""

from __future__ import annotations

import os
from unittest.mock import patch

from sift.cli import main, parse_args
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
    }
    values.update(**overrides)
    return RepoCandidate(**values)


class TestParseArgs:
    """Task 2.1: New flags for interactive mode."""

    def test_default_format_is_table(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.format == "table"

    def test_json_format_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--format", "json"])
        assert args.format == "json"

    def test_markdown_format_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--format", "markdown"])
        assert args.format == "markdown"

    def test_force_interactive_flag_defaults_to_false(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.force_interactive is False

    def test_force_interactive_flag_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--force-interactive"])
        assert args.force_interactive is True

    def test_no_interactive_flag_defaults_to_false(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.no_interactive is False

    def test_no_interactive_flag_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--no-interactive"])
        assert args.no_interactive is True


class TestAgentFlag:
    """Tests for --agent flag (Phase 2)."""

    def test_agent_flag_defaults_to_false(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.agent is False

    def test_agent_flag_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--agent"])
        assert args.agent is True

    def test_ai_alias_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--ai"])
        assert args.agent is True


class TestSpeedFlag:
    """Tests for --speed flag (Phase 4)."""

    def test_speed_default_is_balanced(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.speed == "balanced"

    def test_speed_fast_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--speed", "fast"])
        assert args.speed == "fast"

    def test_speed_thorough_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--speed", "thorough"])
        assert args.speed == "thorough"


class TestMainBranching:
    """Tasks 2.2-2.4: Interactive branching in main()."""

    def test_interactive_path_calls_run_tui_mode(self) -> None:
        with patch("sift.cli.is_interactive", return_value=True), patch(
            "sift.cli.run_tui_mode", return_value=0
        ) as mock_run_tui:
            result = main(["-q", "test", "-l", "Python"])
            assert result == 0
            mock_run_tui.assert_called_once()

    def test_headless_path_calls_run(self) -> None:
        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sift.cli.run", return_value=[]) as mock_run,
            patch("sift.cli.render_table", return_value="") as mock_table,
        ):
            result = main(["-q", "test", "-l", "Python"])
            assert result == 0
            mock_run.assert_called_once()
            mock_table.assert_called_once()

    def test_missing_query_in_headless_returns_error(self) -> None:
        with patch("sift.cli.is_interactive", return_value=False):
            result = main([])
            assert result == 2

    def test_missing_language_in_headless_returns_error(self) -> None:
        with patch("sift.cli.is_interactive", return_value=False):
            result = main(["-q", "test"])
            assert result == 2

    def test_existing_json_output_preserved_in_headless(self) -> None:
        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sift.cli.run", return_value=[]),
            patch("sift.cli.render_json", return_value="[]") as mock_json,
        ):
            result = main(["-q", "test", "-l", "Python", "--format", "json"])
            assert result == 0
            mock_json.assert_called_once()

    def test_login_command_still_works(self) -> None:
        with patch("sift.cli.login_interactive"):
            result = main(["--login"])
            assert result == 0

    def test_logout_command_still_works(self) -> None:
        with patch("sift.cli.clear_token"):
            result = main(["--logout"])
            assert result == 0

    def test_headless_env_var_blocks_interactive(self) -> None:
        """REPO_SCOUT_HEADLESS=true skips interactive path even in TTY."""
        with (
            patch("sift.cli.is_interactive", return_value=True),
            patch("sift.cli.run", return_value=[]) as mock_run,
            patch("sift.cli.render_table", return_value=""),
            patch.dict(os.environ, {"REPO_SCOUT_HEADLESS": "true"}, clear=False),
        ):
            result = main(["-q", "test", "-l", "Python"])
            assert result == 0
            mock_run.assert_called_once()


class TestRunInteractiveModeThroughForce:
    """run_interactive_mode internals via --force-interactive (TTY path now uses TUI)."""

    def test_progress_context_exits_before_compact_render(self) -> None:
        """Progress __exit__ fires before render_compact_table is called (lifecycle)."""
        events: list[str] = []

        class _MockProgress:
            """Minimal Progress stand-in that records __exit__ order."""

            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            def __enter__(self) -> _MockProgress:
                return self

            def __exit__(self, *args: object) -> None:
                events.append("progress_exit")

            def add_task(self, description: str = "", total: object = None) -> None:  # noqa: ARG002
                pass

        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("rich.progress.Progress", _MockProgress),
            patch(
                "sift.cli.render_compact_table",
                side_effect=lambda _: events.append("render") or "",
            ),
            patch("sys.stdin.read", return_value="q"),
            patch("rich.console.Console"),
        ):
            result = main(["-q", "test", "-l", "Python", "--force-interactive"])

        assert result == 0
        assert events == ["progress_exit", "render"], (
            f"Expected progress_exit before render, got: {events}"
        )

    def test_interactive_mode_uses_compact_renderer(self) -> None:
        """Interactive mode calls render_compact_table, not render_table."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("sift.cli.render_compact_table", return_value="") as mock_compact,
            patch("sys.stdin.read", return_value="q"),
            patch("rich.console.Console"),
        ):
            result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0
        mock_compact.assert_called_once()

    def test_search_uses_provided_query_and_language(self) -> None:
        """Interactive mode with pre-supplied inputs skips prompts and calls run."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("sift.cli.render_compact_table", return_value=""),
            patch("sys.stdin.read", return_value="q"),
            patch("rich.console.Console"),
        ):
            result = main(["-q", "jwt auth", "-l", "Python", "--force-interactive"])
            assert result == 0

    def test_ctrl_c_during_search_cancels(self) -> None:
        with (
            patch("sift.cli.run", side_effect=KeyboardInterrupt),
            patch("rich.console.Console"),
        ):
            result = main(["-q", "test", "-l", "Python", "--force-interactive"])
            assert result == 1

    def test_empty_results_in_interactive_mode(self) -> None:
        with (
            patch("sift.cli.run", return_value=[]),
            patch("rich.console.Console"),
        ):
            result = main(["-q", "test", "-l", "Python", "--force-interactive"])
            assert result == 0

    def test_no_interactive_flag_blocks_force_interactive(self) -> None:
        """--no-interactive takes priority even with --force-interactive."""
        with (
            patch("sift.cli.run", return_value=[]),
            patch("sift.cli.render_table", return_value=""),
        ):
            result = main(["-q", "test", "-l", "Python", "--force-interactive", "--no-interactive"])
            assert result == 0


class TestQuickKeyLoop:
    """Quick-key action loop: single-key dispatch with o/r/q/s/?."""

    def _run_with_keys(self, key_sequence: list[str]) -> int:
        """Helper: run main() with mocked interactive flow and sys.stdin.read."""
        repo = _make_repo()
        stdin_read = iter(key_sequence)

        def mock_read(_n: int = 1) -> str:
            return next(stdin_read)

        with (
            patch("sift.cli.run", return_value=[repo]),
            patch("sys.stdin.read", side_effect=mock_read),
            patch("webbrowser.open"),
            patch("rich.console.Console"),
        ):
            return main(["-q", "test", "-l", "Python", "--force-interactive"])

    def test_q_quits(self) -> None:
        """Pressing 'q' exits the loop."""
        result = self._run_with_keys(["q"])
        assert result == 0

    def test_s_quits(self) -> None:
        """Pressing 's' also exits (salir)."""
        result = self._run_with_keys(["s"])
        assert result == 0

    def test_o_then_number_opens_browser(self) -> None:
        """'o' then a digit opens the repo in browser."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("webbrowser.open") as mock_browser,
            patch("rich.console.Console"),
        ):
            stdin_data = iter(["o", "1", "q"])

            def mock_read(_n: int = 1) -> str:
                return next(stdin_data)

            with patch("sys.stdin.read", side_effect=mock_read):
                result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0
        mock_browser.assert_called_once_with("https://github.com/owner/repo")

    def test_r_refreshes_then_q_quits(self) -> None:
        """'r' re-runs search, 'q' exits."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("webbrowser.open"),
            patch("rich.console.Console"),
        ):
            stdin_data = iter(["r", "q"])

            def mock_read(_n: int = 1) -> str:
                return next(stdin_data)

            with patch("sys.stdin.read", side_effect=mock_read):
                result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0

    def test_invalid_repo_number_handled_gracefully(self) -> None:
        """Out-of-range repo number shows error but stays in loop."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("webbrowser.open"),
            patch("rich.console.Console"),
        ):
            stdin_data = iter(["o", "9", "q"])

            def mock_read(_n: int = 1) -> str:
                return next(stdin_data)

            with patch("sys.stdin.read", side_effect=mock_read):
                result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0

    def test_unknown_key_shows_hint_and_stays(self) -> None:
        """Unknown key shows hint bar and stays in loop."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("webbrowser.open"),
            patch("rich.console.Console"),
        ):
            stdin_data = iter(["x", "q"])

            def mock_read(_n: int = 1) -> str:
                return next(stdin_data)

            with patch("sys.stdin.read", side_effect=mock_read):
                result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0

    def test_d_with_valid_number_shows_detail_for_one_repo(self) -> None:
        """'d' followed by a valid number shows markdown for that repo."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("sift.cli.render_markdown", return_value="") as mock_md,
            patch("webbrowser.open"),
            patch("rich.console.Console"),
        ):
            stdin_data = iter(["d", "1", "q"])

            def mock_read(_n: int = 1) -> str:
                return next(stdin_data)

            with patch("sys.stdin.read", side_effect=mock_read):
                result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0
        mock_md.assert_called_once()

    def test_d_with_invalid_number_shows_all_details(self) -> None:
        """'d' followed by invalid number shows details for all repos."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("sift.cli.render_markdown", return_value="") as mock_md,
            patch("webbrowser.open"),
            patch("rich.console.Console"),
        ):
            stdin_data = iter(["d", "0", "q"])

            def mock_read(_n: int = 1) -> str:
                return next(stdin_data)

            with patch("sys.stdin.read", side_effect=mock_read):
                result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0
        mock_md.assert_called_once()

    def test_j_shows_json(self) -> None:
        """'j' shows JSON output of current results."""
        with (
            patch("sift.cli.run", return_value=[_make_repo()]),
            patch("sift.cli.render_json", return_value="") as mock_json,
            patch("webbrowser.open"),
            patch("rich.console.Console"),
        ):
            stdin_data = iter(["j", "q"])

            def mock_read(_n: int = 1) -> str:
                return next(stdin_data)

            with patch("sys.stdin.read", side_effect=mock_read):
                result = main(["-q", "test", "-l", "Python", "--force-interactive"])
        assert result == 0
        mock_json.assert_called_once()


class TestWebFlag:
    """Tasks 3.1-3.3: --web flag parsing and routing."""

    def test_web_flag_defaults_to_false(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python"])
        assert args.web is False

    def test_web_flag_parsed(self) -> None:
        args = parse_args(["-q", "test", "-l", "Python", "--web"])
        assert args.web is True

    def test_web_flag_with_agent_warns(self, capsys) -> None:
        """--web with --agent prints warning and runs agent mode."""
        with patch("sift.cli._run_agent", return_value=0) as mock_agent:
            result = main(["-q", "test", "-l", "Python", "--web", "--agent"])
            assert result == 0
            mock_agent.assert_called_once()
        captured = capsys.readouterr()
        assert "--web" in captured.err

    def test_web_mode_calls_run_web(self) -> None:
        """--web without --agent calls _run_web_mode."""
        with patch("sift.cli._run_web_mode", return_value=0) as mock_web:
            result = main(["-q", "test", "-l", "Python", "--web"])
            assert result == 0
            mock_web.assert_called_once()


class TestWebPersistence:
    """Task 3.4: search results persisted to history in all modes."""

    def test_headless_mode_persists_results(self) -> None:
        """Headless search persists results to history."""
        with (
            patch("sift.cli.is_interactive", return_value=False),
            patch("sift.cli.run", return_value=[_make_repo()]) as mock_run,
            patch("sift.cli.render_table", return_value=""),
            patch("sift.cli.SearchHistoryStore") as mock_store_cls,
        ):
            mock_store = mock_store_cls.return_value
            result = main(["-q", "test", "-l", "Python"])
            assert result == 0
            mock_run.assert_called_once()
            mock_store.add_entry.assert_called_once()
