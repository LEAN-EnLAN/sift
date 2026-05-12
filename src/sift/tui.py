"""Textual TUI for sift — smart input with NLP detection.

Provides a full-screen terminal UI with a single smart input,
auto-detection of language and speed, preview panel, async search
with LoadingIndicator, scrollable results, detail view,
and quick-open browser action.

Headless/agent contract: TUI changes must not affect headless --agent
JSON output or --query --language pipeline behavior.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import webbrowser
from enum import Enum, auto
from time import monotonic

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    RichLog,
    Static,
)

from . import __version__
from .models import RepoCandidate
from .query import detect_language, detect_speed, extract_keywords, has_speed_hint
from .render import render_best_summary, render_markdown

# Re-export the run function so tests can mock it at module level
from .cli import run  # noqa: F401 — used by tests for mocking at sift.tui.run


SIFT_BANNER = f"""
   ▄▄▄▄▄▄
  ██      ██    sift v{__version__}
  ██           CLI-first · open source
   ▀▀▀▀▀▄
        ██    busca por intención
  ██    ██    puntúa por señales
   ▀▀▀▀▀▀
"""


class AppState(Enum):
    """TUI finite state machine states."""

    INPUT = auto()
    PREVIEW = auto()
    SEARCHING = auto()
    RESULTS = auto()


CSS = """
Screen {
    background: #0D0D0D;
}

#input-panel {
    padding: 1 2;
    background: #141414;
    border: solid #22F5A7;
    height: auto;
    margin: 1 2;
    max-height: 20;
}

#input-panel Label {
    color: #22F5A7;
    text-style: bold;
    margin-bottom: 0;
}

#smart-input {
    background: #1A1A1A;
    color: #E0E0E0;
    border: none;
    margin-bottom: 1;
}

#smart-input:focus {
    background: #222;
}

#preview-panel {
    display: none;
    border: solid #22F5A7;
    padding: 0 1;
    margin-top: 1;
}

#preview-panel.visible {
    display: block;
}

#preview-panel Label {
    color: #22F5A7;
    text-style: bold;
}

#preview-query,
#preview-language,
#preview-speed {
    background: #1A1A1A;
    color: #E0E0E0;
    border: none;
    margin: 0 0 1 0;
}

#preview-query:focus,
#preview-language:focus,
#preview-speed:focus {
    background: #222;
}

#preview-actions {
    align: center middle;
    height: 3;
    margin-top: 1;
}

#preview-confirm {
    background: #22F5A7;
    color: #0D0D0D;
    margin: 0 1;
}

#preview-back {
    background: #444;
    color: #E0E0E0;
    margin: 0 1;
}

#status-bar {
    height: 3;
    margin: 0 2;
    padding: 0 1;
}

#status-text {
    color: #888;
    text-style: italic;
}

#status-text.searching {
    color: #22F5A7;
}

#status-text.done {
    color: #22F5A7;
}

#status-text.error {
    color: #F87171;
}

#search-spinner {
    display: none;
    margin: 0 0 0 0;
}

#search-spinner.visible {
    display: block;
}

#results-panel {
    margin: 0 2;
    padding: 0 1;
    height: 1fr;
    border: solid #333;
    overflow-y: auto;
}

#results-panel:focus-within {
    border: solid #22F5A7;
}

#detail-panel {
    margin: 0 2;
    padding: 0 1;
    height: 1fr;
    border: solid #333;
    display: none;
    overflow-y: auto;
}

#detail-panel.visible {
    display: block;
    border: solid #22F5A7;
}

RichLog {
    background: #0D0D0D;
    color: #E0E0E0;
}

ListView {
    background: #0D0D0D;
}

ListView > ListItem {
    background: #141414;
    padding: 0 1;
}

ListView > ListItem:hover {
    background: #1A1A1A;
}

ListView > ListItem:focus {
    background: #1A2A1A;
}

.footer {
    background: #141414;
    color: #666;
}

.footer Key {
    color: #22F5A7;
}
"""


def _result_label(repo: RepoCandidate) -> str:
    """Format a repo result as a one-line label."""
    return f"#{_index_counter[0]} {repo.full_name}  score: {repo.score:.1f}  ★{repo.stars}"


# Global counter for result numbering (reset per search)
_index_counter: list[int] = [0]


class ResultItem(ListItem):
    """A single search result in the list."""

    def __init__(self, repo: RepoCandidate, index: int) -> None:
        self.repo = repo
        self.result_index = index
        label = Text.assemble(
            (f"#{index} ", "dim"),
            (f"{repo.full_name}", "bold"),
            "  ",
            (f"score: {repo.score:.1f}", "green"),
            "  ",
            (f"★{repo.stars}", "yellow"),
        )
        super().__init__(Label(label))

    def on_mount(self) -> None:
        self.styles.height = 1


def _popen_silent(command: list[str]) -> bool:
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except (FileNotFoundError, OSError):
        return False


def _silent_browser_launcher(url: str) -> str | None:
    """Try deterministic browser launchers without leaking xdg-open errors."""
    browser_env = os.environ.get("BROWSER", "").strip()
    candidates: list[tuple[str, list[str]]] = []

    helium = shutil.which("helium")
    if helium:
        candidates.append(("Helium", [helium, url]))

    if browser_env:
        parts = shlex.split(browser_env)
        if parts:
            label = "Helium" if "helium" in parts[0].lower() else os.path.basename(parts[0])
            candidates.append((label, [*parts, url]))

    for binary, label in (("open", "open"), ("xdg-open", "xdg-open")):
        resolved = shutil.which(binary)
        if resolved:
            candidates.append((label, [resolved, url]))

    for label, command in candidates:
        if _popen_silent(command):
            return label
    return None


def _webbrowser_open_silent(url: str) -> bool:
    """Last-resort webbrowser fallback with fd-level stderr suppression."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved_stderr = os.dup(2)
    try:
        os.dup2(devnull, 2)
        return bool(webbrowser.open(url))
    except Exception:
        return False
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)
        os.close(devnull)


class SiftApp(App):
    """Textual TUI for sift — smart input with NLP detection."""

    CSS = CSS

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("escape", "back", "Atrás"),
        ("ctrl+d", "view_detail", "Detalles"),
        ("r", "refresh", "Refrescar"),
        ("o", "open_repo", "Abrir"),
        ("d", "view_detail", "Detalles"),
        ("tab", "focus_toggle", "Siguiente"),
        ("shift+tab", "focus_toggle", "Anterior"),
    ]

    # Reactive state
    state: reactive[AppState] = reactive(AppState.INPUT)
    results: reactive[list[RepoCandidate]] = reactive([])
    searching: reactive[bool] = reactive(False)
    detail_mode: reactive[bool] = reactive(False)

    # Internal state (not reactive — only read by event handlers)
    _current_query: str = ""
    _current_languages: list[str] = []
    _current_speed: str = "balanced"
    _search_started_at: float = 0.0

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        with Vertical(id="input-panel"):
            yield Label("¿Qué necesitás buscar?")
            yield Input(
                id="smart-input",
                placeholder='Ej: "autenticación JWT en Python"',
            )
            with Vertical(id="preview-panel"):
                yield Label("Resumen de búsqueda")
                yield Input(
                    id="preview-query",
                    placeholder="Consulta",
                )
                yield Input(
                    id="preview-language",
                    placeholder="Lenguaje(s) — separado por coma",
                )
                yield Input(
                    id="preview-speed",
                    placeholder="Velocidad (fast / balanced / thorough)",
                )
                with Horizontal(id="preview-actions"):
                    yield Button("Buscar", id="preview-confirm", variant="primary")
                    yield Button("Atrás", id="preview-back")
        with Horizontal(id="status-bar"):
            yield LoadingIndicator(id="search-spinner")
            yield Static("Presioná Enter para buscar", id="status-text")
        yield ListView(id="results-panel")
        with Container(id="detail-panel"):
            yield RichLog(id="detail-log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        """Focus the smart input and show welcome banner."""
        self.query_one("#smart-input", Input).focus()
        # Show ASCII logo briefly
        status = self.query_one("#status-text", Static)
        status.update(SIFT_BANNER)

    def watch_state(self, state: AppState) -> None:
        """React to state changes — show/hide panels and toggle focus."""
        preview = self.query_one("#preview-panel")
        smart_input = self.query_one("#smart-input", Input)
        status = self.query_one("#status-text", Static)
        preview_query = self.query_one("#preview-query", Input)
        preview_language = self.query_one("#preview-language", Input)
        preview_speed = self.query_one("#preview-speed", Input)
        preview_confirm = self.query_one("#preview-confirm", Button)
        preview_back = self.query_one("#preview-back", Button)

        if state == AppState.INPUT:
            preview.remove_class("visible")
            preview.styles.display = "none"
            smart_input.disabled = False
            preview_query.disabled = False
            preview_language.disabled = False
            preview_speed.disabled = False
            preview_confirm.disabled = False
            preview_back.disabled = False
            smart_input.focus()
            status.update("Presioná Enter para buscar")
            status.remove_class("done", "error", "searching")
        elif state == AppState.PREVIEW:
            preview.remove_class("visible")
            preview.styles.display = "block"
            preview.add_class("visible")
            smart_input.disabled = True
            preview_query.disabled = False
            preview_language.disabled = False
            preview_speed.disabled = False
            preview_confirm.disabled = False
            preview_back.disabled = False
            # Focus the first preview field
            self.query_one("#preview-query", Input).focus()
        elif state == AppState.SEARCHING:
            preview.styles.display = "none"
            preview.remove_class("visible")
            smart_input.disabled = True
            preview_query.disabled = True
            preview_language.disabled = True
            preview_speed.disabled = True
            preview_confirm.disabled = True
            preview_back.disabled = True
            status.update("Buscando en GitHub…")
            status.add_class("searching")
        elif state == AppState.RESULTS:
            status.remove_class("searching")
            status.add_class("done")
            if self.results:
                elapsed = monotonic() - self._search_started_at if self._search_started_at else 0.0
                best = render_best_summary(self.results[0])
                status.update(f"✓ {best}  ({len(self.results)} resultados · {elapsed:.1f}s)")
            else:
                status.update("No se encontraron resultados")

    def watch_results(self, results: list[RepoCandidate]) -> None:
        """React to results changes — rebuild the ListView."""
        list_view = self.query_one("#results-panel", ListView)
        list_view.clear()
        if results:
            for i, repo in enumerate(results, 1):
                list_view.append(ResultItem(repo, i))
        self.state = AppState.RESULTS

    def watch_searching(self, searching: bool) -> None:
        """React to search state changes — toggle spinner."""
        spinner = self.query_one("#search-spinner", LoadingIndicator)
        status = self.query_one("#status-text", Static)
        if searching:
            spinner.display = True
            spinner.add_class("visible")
            status.update("Buscando en GitHub…")
            status.remove_class("done", "error")
            status.add_class("searching")
            self.state = AppState.SEARCHING
        else:
            spinner.display = False
            spinner.remove_class("visible")
            status.remove_class("searching")

    def watch_detail_mode(self, detail_mode: bool) -> None:
        """Show/hide detail panel."""
        detail_panel = self.query_one("#detail-panel", Container)
        results_panel = self.query_one("#results-panel", ListView)
        if detail_mode:
            detail_panel.add_class("visible")
            results_panel.styles.display = "none"
        else:
            detail_panel.remove_class("visible")
            results_panel.styles.display = "block"

    def _set_status(self, message: str, *, style: str | None = None) -> None:
        status = self.query_one("#status-text", Static)
        status.update(message)
        status.remove_class("done", "error", "searching")
        if style:
            status.add_class(style)

    def _set_results(self, repos: list[RepoCandidate]) -> None:
        self.results = repos

    def _set_search_error(self, message: str) -> None:
        self._set_status(message, style="error")

    def _finish_search(self) -> None:
        self.searching = False

    # ─── Event Handlers ──────────────────────────────────────────────

    @on(Input.Submitted, "#smart-input")
    def on_smart_submitted(self, event: Input.Submitted) -> None:
        """Parse smart input and start search if language detected.

        Direct-search shortcut preserves headless contract because it only
        affects TUI flow, not CLI/run() pipeline.
        """
        if self.searching:
            return
        text = event.value.strip()
        if not text:
            self.query_one("#status-text", Static).update("⚠ Ingresá una consulta")
            return

        # NLP detection
        langs = detect_language(text)
        speed = detect_speed(text)
        if speed == "balanced" and not has_speed_hint(text):
            speed = "fast"

        # Store for search
        self._current_query = text
        self._current_languages = langs
        self._current_speed = speed

        # Fill preview fields (for back-navigation if user returns to edit)
        self.query_one("#preview-query", Input).value = text
        self.query_one("#preview-language", Input).value = ", ".join(langs) if langs else ""
        self.query_one("#preview-speed", Input).value = speed

        if langs:
            # Direct search — skip preview, start immediately
            self._set_status(
                f"Interpreté lenguaje={', '.join(langs)} · velocidad={speed}. Buscando…",
                style="searching",
            )
            self._start_search()
        else:
            self._set_status(
                "No detecté lenguaje. Podés escribirlo abajo o buscar sin filtro por lenguaje.",
                style="error",
            )
            self.state = AppState.PREVIEW

    @on(Button.Pressed, "#preview-confirm")
    def on_preview_confirm(self) -> None:
        """Confirm preview and start search."""
        self._start_search()

    @on(Button.Pressed, "#preview-back")
    def on_preview_back(self) -> None:
        """Go back to input from preview."""
        if self.state == AppState.PREVIEW:
            self.state = AppState.INPUT

    @on(Input.Submitted, "#preview-query")
    def on_preview_query_submitted(self) -> None:
        """Preview query submitted — move to language field."""
        self.query_one("#preview-language", Input).focus()

    @on(Input.Submitted, "#preview-language")
    def on_preview_language_submitted(self) -> None:
        """Preview language submitted — move to speed field."""
        self.query_one("#preview-speed", Input).focus()

    @on(Input.Submitted, "#preview-speed")
    def on_preview_speed_submitted(self) -> None:
        """Preview speed submitted — move to confirm button."""
        self.query_one("#preview-confirm", Button).focus()

    @on(ListView.Selected)
    def on_result_selected(self, event: ListView.Selected) -> None:
        """Handle result selection — open repo in browser."""
        if isinstance(event.item, ResultItem):
            self._open_repo(event.item.repo)

    # ─── Actions ─────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        """Re-run the current search."""
        if self.searching:
            return
        if self._current_query:
            self._start_search()

    def action_back(self) -> None:
        """Return to previous state."""
        if self.searching:
            return
        if self.detail_mode:
            self.detail_mode = False
        elif self.state == AppState.PREVIEW:
            self.state = AppState.INPUT
        elif self.state == AppState.RESULTS:
            self.state = AppState.INPUT
            self.query_one("#smart-input", Input).disabled = False
            self.query_one("#smart-input", Input).focus()

    def action_view_detail(self) -> None:
        """Show detail for the selected result."""
        list_view = self.query_one("#results-panel", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, ResultItem):
            self._show_detail(list_view.highlighted_child.repo)

    def action_open_repo(self) -> None:
        """Open the selected repo in a browser ('o' key)."""
        list_view = self.query_one("#results-panel", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, ResultItem):
            self._open_repo(list_view.highlighted_child.repo)

    def action_focus_toggle(self) -> None:
        """Cycle focus between smart input and results panel."""
        if self.state in (AppState.PREVIEW, AppState.SEARCHING):
            self.action_focus_next()
            return
        if self.state == AppState.RESULTS:
            # Have results — toggle between input and results
            results = self.query_one("#results-panel", ListView)
            if self.focused is results:
                self.query_one("#smart-input", Input).focus()
            else:
                results.focus()
        else:
            self.action_focus_next()

    # ─── Search ──────────────────────────────────────────────────────

    def _start_search(self) -> None:
        """Read preview values, validate, and kick off search worker."""
        if self.searching:
            return
        query = self.query_one("#preview-query", Input).value.strip()
        if not query:
            query = self._current_query
        if not query:
            self._set_status("⚠ Ingresá una consulta", style="error")
            return

        raw_langs = self.query_one("#preview-language", Input).value.strip()
        languages = [lang.strip() for lang in raw_langs.split(",") if lang.strip()]
        if not languages:
            languages = self._current_languages

        raw_speed = self.query_one("#preview-speed", Input).value.strip().lower()
        speed = raw_speed if raw_speed in {"fast", "balanced", "thorough"} else self._current_speed or "fast"

        self._current_query = query
        self._current_languages = languages
        self._current_speed = speed

        # Derive clean search keywords from NLP pipeline (strip noise:
        # language names, speed words, stopwords already handled by extract_keywords).
        clean_keywords = extract_keywords(query)
        # Also strip speed-adverb keywords so they don't pollute the GitHub query.
        from .query import SPEED_KEYWORDS as _SK, LANGUAGE_KEYWORDS as _LK
        noise_words = set(_SK.keys()) | set(_LK.keys())
        clean_keywords = [kw for kw in clean_keywords if kw.lower() not in noise_words]
        search_query = " ".join(clean_keywords) if clean_keywords else query
        self._search_started_at = monotonic()
        search_label = ", ".join(languages) if languages else "todos los lenguajes"
        self._set_status(f"Preparando búsqueda en {search_label} · modo {speed}…", style="searching")
        self.searching = True
        self._run_search(search_query, languages, speed)

    def _open_repo(self, repo: RepoCandidate) -> bool:
        """Open repo URL without leaking browser launcher stderr into the TUI.

        Returns True if a launch was attempted.
        """
        launcher = _silent_browser_launcher(repo.html_url)
        if launcher:
            self._set_status(f"Abriendo {repo.full_name} con {launcher}…")
            return True

        if _webbrowser_open_silent(repo.html_url):
            self._set_status(f"Abriendo {repo.full_name} en el navegador…")
            return True

        self._set_status(
            "No pude abrir el navegador automáticamente. Copiá la URL desde el detalle.",
            style="error",
        )
        return False

    def _show_detail(self, repo: RepoCandidate) -> None:
        """Display detail view for a repo."""
        detail_log = self.query_one("#detail-log", RichLog)
        detail_log.clear()
        md = render_markdown([repo], self._current_query, self._current_languages)
        detail_log.write(md)
        self.detail_mode = True

    @work(exclusive=True, group="search", thread=True)
    def _run_search(self, query: str, languages: list[str], speed: str) -> None:
        """Async worker wrapping sift.cli.run().

        Uses the module-level re-export (from .cli import run) so tests
        can mock at ``sift.tui.run`` without import-scope trickery.
        """
        from .models import SearchOptions

        try:
            options = SearchOptions(
                query=query,
                languages=languages,
                top=5,
                speed=speed,
            )
            repos = run(
                options,
                progress_callback=lambda message: self.call_from_thread(self._set_status, message, style="searching"),
            )
            self.call_from_thread(self._set_results, repos)
        except Exception as exc:
            self.call_from_thread(self._set_search_error, f"Error: {exc}")
        finally:
            self.call_from_thread(self._finish_search)
