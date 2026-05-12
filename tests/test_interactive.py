"""Tests for interactive mode detection and interactive components."""

from __future__ import annotations

from unittest.mock import patch

from io import StringIO
from rich.console import Console

from sift.interactive import InteractivePrompt, InteractiveSplash, is_interactive


class TestIsInteractive:
    """Task 1.1: is_interactive() guard — sys.stdin.isatty() and sys.stdout.isatty()."""

    def test_returns_true_when_both_are_ttys(self) -> None:
        with patch("sys.stdin.isatty", return_value=True), patch(
            "sys.stdout.isatty", return_value=True
        ):
            assert is_interactive() is True

    def test_returns_false_when_stdin_not_tty(self) -> None:
        with patch("sys.stdin.isatty", return_value=False), patch(
            "sys.stdout.isatty", return_value=True
        ):
            assert is_interactive() is False

    def test_returns_false_when_stdout_not_tty(self) -> None:
        with patch("sys.stdin.isatty", return_value=True), patch(
            "sys.stdout.isatty", return_value=False
        ):
            assert is_interactive() is False

    def test_returns_false_when_neither_tty(self) -> None:
        with patch("sys.stdin.isatty", return_value=False), patch(
            "sys.stdout.isatty", return_value=False
        ):
            assert is_interactive() is False


class TestInteractivePrompt:
    """Tasks 1.2-1.4: InteractivePrompt class, ask_query, ask_language."""

    def _make_prompt(self) -> tuple[InteractivePrompt, StringIO]:
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=80)
        return InteractivePrompt(console), buf

    def test_ask_query_returns_trimmed_string(self) -> None:
        prompt, _ = self._make_prompt()
        with patch("rich.prompt.Prompt.ask", return_value="  autenticación con JWT  "):
            result = prompt.ask_query()
        assert result == "autenticación con JWT"

    def test_ask_query_reprompts_on_empty_input(self) -> None:
        prompt, _ = self._make_prompt()
        with patch("rich.prompt.Prompt.ask", side_effect=["", "jwt auth"]):
            result = prompt.ask_query()
        assert result == "jwt auth"

    def test_ask_query_returns_none_on_keyboard_interrupt(self) -> None:
        prompt, _ = self._make_prompt()
        with patch("rich.prompt.Prompt.ask", side_effect=KeyboardInterrupt):
            result = prompt.ask_query()
        assert result is None

    def test_ask_language_returns_list_of_stripped_languages(self) -> None:
        prompt, _ = self._make_prompt()
        with patch("rich.prompt.Prompt.ask", return_value="Python, JavaScript  "):
            result = prompt.ask_language()
        assert result == ["Python", "JavaScript"]

    def test_ask_language_reprompts_on_empty(self) -> None:
        prompt, _ = self._make_prompt()
        with patch("rich.prompt.Prompt.ask", side_effect=["", "Python"]):
            result = prompt.ask_language()
        assert result == ["Python"]

    def test_ask_language_returns_none_on_keyboard_interrupt(self) -> None:
        prompt, _ = self._make_prompt()
        with patch("rich.prompt.Prompt.ask", side_effect=KeyboardInterrupt):
            result = prompt.ask_language()
        assert result is None

    def test_single_language_returns_single_item_list(self) -> None:
        prompt, _ = self._make_prompt()
        with patch("rich.prompt.Prompt.ask", return_value="Python"):
            result = prompt.ask_language()
        assert result == ["Python"]


class TestInteractiveSplash:
    """Task 1.5: InteractiveSplash welcome message."""

    def test_show_outputs_welcome_message(self) -> None:
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=80, color_system=None)
        splash = InteractiveSplash(console)
        splash.show()
        output = buf.getvalue()
        assert "sift" in output
        assert "recomendaciones" in output.lower()
