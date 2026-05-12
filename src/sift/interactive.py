from __future__ import annotations

import sys

from rich.console import Console
from rich.prompt import Prompt


def is_interactive() -> bool:
    """Returns True when both stdin and stdout are connected to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


class InteractiveSplash:
    """Welcome message and current config display for interactive mode."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def show(self) -> None:
        """Display welcome splash."""
        self.console.print("[bold cyan]🔍 sift[/bold cyan] — [italic]recomendaciones inteligentes de GitHub[/italic]")
        self.console.print()


class InteractivePrompt:
    """Prompt for query and language inputs in interactive mode."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def ask_query(self) -> str | None:
        """Prompt for the search query. Returns None on KeyboardInterrupt."""
        try:
            while True:
                value = Prompt.ask("¿Qué necesitás buscar?")
                stripped = value.strip()
                if stripped:
                    return stripped
        except KeyboardInterrupt:
            return None

    def ask_language(self) -> list[str] | None:
        """Prompt for programming language(s). Returns None on KeyboardInterrupt."""
        try:
            while True:
                value = Prompt.ask("¿Lenguaje? (ej: Python, JavaScript)")
                parts = [p.strip() for p in value.split(",") if p.strip()]
                if parts:
                    return parts
        except KeyboardInterrupt:
            return None
