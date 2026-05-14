from __future__ import annotations

import argparse
import os
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from .auth import clear_token, load_token, login_interactive
from .github import GitHubAPIError, GitHubClient
from .interactive import InteractivePrompt, InteractiveSplash, is_interactive
from .models import SearchOptions
from .persistence.history import SearchHistoryStore
from .query import build_search_queries
from .render import render_agent_json, render_compact_table, render_json, render_markdown, render_table
from .scoring import shortlist


def _show_quick_hints(console: Any, count: int) -> None:
    """Display compact hint bar for quick-key actions."""
    console.print(
        "\n[dim][bold]o[/bold] abrir N  [bold]d[/bold] detalles N  [bold]j[/bold] JSON  "
        "[bold]r[/bold] refrescar  [bold]q[/bold] salir  [bold]?[/bold] ayuda[/dim]"
    )


def run_interactive_mode(args: argparse.Namespace) -> int:
    """Run the interactive CLI flow: prompts, search, result display."""
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()

    splash = InteractiveSplash(console)
    splash.show()

    prompt = InteractivePrompt(console)

    # Prompt for query if not provided via --query/-q.
    query = args.query
    if not query:
        result = prompt.ask_query()
        if result is None:  # Ctrl+C
            return 1
        query = result

    # Prompt for language(s) if not provided via --language/-l.
    raw_languages = args.language
    if not raw_languages:
        result = prompt.ask_language()
        if result is None:  # Ctrl+C
            return 1
        languages = result
    else:
        languages = [lang.strip() for lang in raw_languages.split(",") if lang.strip()]

    options = SearchOptions(
        query=query,
        languages=languages,
        top=args.top,
        pool_size=args.pool_size,
        min_stars=args.min_stars,
        pushed_after=args.pushed_after,
        license=args.license_filter,
        include_forks=args.include_forks,
        include_archived=args.include_archived,
        max_candidates=args.max_candidates,
        speed=args.speed,
    )

    # Search with progress spinner and Ctrl+C handling.
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Buscando en GitHub...", total=None)
            repos = run(options, token=args.token, cache_ttl=args.cache_ttl, debug=args.debug)
    except KeyboardInterrupt:
        console.print("\n[yellow]Búsqueda cancelada. Podés volver a ejecutar sin re-ingresar todo.[/yellow]")
        return 1
    except GitHubAPIError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 2

    if not repos:
        console.print("[yellow]No se encontraron repositorios con esos criterios. Podés volver a ejecutar con otros términos.[/yellow]")
        return 0

    console.print(render_compact_table(repos))
    console.print(f"\n[dim]Encontré {len(repos)} resultados. Mostrando los mejores {len(repos)}.[/dim]")

    # Quick-key action loop: single-key dispatch.
    _show_quick_hints(console, len(repos))
    while True:
        try:
            key = sys.stdin.read(1)
        except KeyboardInterrupt:
            console.print("\n[green]¡Hasta luego![/green]")
            return 0

        if key in ("q", "s"):
            console.print("[green]¡Hasta luego![/green]")
            return 0

        if key == "o":
            try:
                num_key = sys.stdin.read(1)
                idx = int(num_key) - 1 if num_key.isdigit() else -1
                if 0 <= idx < len(repos):
                    webbrowser.open(repos[idx].html_url)
                    console.print(
                        f"[dim]Abriendo {repos[idx].full_name} en el navegador...[/dim]"
                    )
                else:
                    console.print(
                        f"[yellow]Número inválido. Elegí un número entre 1 y {len(repos)}.[/yellow]"
                    )
            except (ValueError, KeyboardInterrupt):
                console.print("[yellow]Número inválido.[/yellow]")

        elif key == "r":
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True,
                ) as progress:
                    progress.add_task("Buscando en GitHub...", total=None)
                    new_repos = run(
                        options,
                        token=args.token,
                        cache_ttl=args.cache_ttl,
                        debug=args.debug,
                    )
            except KeyboardInterrupt:
                console.print(
                    "\n[yellow]Búsqueda cancelada. Podés volver a ejecutar sin re-ingresar todo.[/yellow]"
                )
                return 1
            except GitHubAPIError as e:
                console.print(f"[red]Error: {e}[/red]")
                return 2

            if new_repos:
                repos = new_repos
                console.print(render_compact_table(repos))
                console.print(
                    f"\n[dim]Encontré {len(repos)} resultados. Mostrando los mejores {len(repos)}.[/dim]"
                )
            else:
                console.print(
                    "[yellow]No se encontraron repositorios con esos criterios. Volviendo al menú...[/yellow]"
                )
            _show_quick_hints(console, len(repos))

        elif key == "?":
            _show_quick_hints(console, len(repos))

        elif key == "d":
            try:
                num_key = sys.stdin.read(1)
                idx = int(num_key) - 1 if num_key.isdigit() else -1
                if 0 <= idx < len(repos):
                    console.print(render_markdown([repos[idx]], query, languages))
                else:
                    console.print(render_markdown(repos, query, languages))
            except (ValueError, KeyboardInterrupt):
                console.print(render_markdown(repos, query, languages))

        elif key == "j":
            console.print(render_json(repos))

        # Unknown keys: silent fallthrough (hint already shown)


def run_tui_mode(args: argparse.Namespace) -> int:
    """Run the Textual TUI mode — conversational search UI."""
    from .tui import SiftApp

    app = SiftApp()
    app.run()
    return 0


def _is_headless() -> bool:
    """Check if headless mode is forced via environment variables."""
    # Headless/agent contract: TUI changes must not affect headless --agent
    # JSON output or --query --language pipeline behavior.
    for var in ("SIFT_HEADLESS", "REPO_SCOUT_HEADLESS"):
        if os.environ.get(var, "").lower() in ("1", "true", "yes"):
            return True
    return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sift",
        description="Sift: buscador inteligente de repositorios de GitHub por necesidad técnica.",
    )
    parser.add_argument("--query", "-q", help="Necesidad técnica en lenguaje natural")
    parser.add_argument(
        "--language",
        "-l",
        help="Lenguaje o lista separada por coma. Ej: Python o Python,JavaScript",
    )
    parser.add_argument("--login", action="store_true", help="Iniciar sesión con GitHub OAuth (device flow)")
    parser.add_argument("--logout", action="store_true", help="Cerrar sesión y borrar el token guardado")
    parser.add_argument("--top", type=int, default=5, help="Cantidad de repos recomendados")
    parser.add_argument("--min-stars", type=int, default=0, help="Filtro mínimo de stars")
    parser.add_argument("--pushed-after", help="Filtro GitHub pushed:>=YYYY-MM-DD")
    parser.add_argument("--license", dest="license_filter", help="Filtro de licencia GitHub, ej: mit, apache-2.0")
    parser.add_argument("--include-forks", action="store_true", help="Permite forks en la búsqueda")
    parser.add_argument("--include-archived", action="store_true", help="Permite archivados en la búsqueda")
    parser.add_argument("--pool-size", type=int, default=30, help="Resultados por query antes del re-ranking")
    parser.add_argument("--max-candidates", type=int, default=35, help="Máximo de candidatos a enriquecer")
    parser.add_argument("--format", choices=["table", "markdown", "json"], default="table")
    parser.add_argument("--cache-ttl", type=int, default=3600, help="TTL de cache en segundos")
    parser.add_argument("--token", help="GitHub token. Si se omite usa GITHUB_TOKEN")
    parser.add_argument("--force-interactive", action="store_true", help="Forzar modo interactivo aunque no haya TTY")
    parser.add_argument("--no-interactive", action="store_true", help="Deshabilitar modo interactivo aunque haya TTY")
    parser.add_argument(
        "--speed",
        choices=["fast", "balanced", "thorough"],
        default="balanced",
        help="Velocidad de búsqueda: fast (mínimo de queries/candidatos), balanced (default), thorough (máximo recall)",
    )
    parser.add_argument(
        "--agent",
        "--ai",
        action="store_true",
        dest="agent",
        help="Modo agente: salida JSON con _meta, machine-readable. Para integración con agentes/CI",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        dest="web",
        help="[Experimental] Abrir companion web UI. Opt-in, no cambia comportamiento sin el flag.",
    )
    parser.add_argument("--debug", action="store_true", help="Muestra queries y configuración sin exponer secretos")
    return parser.parse_args(argv)


# Speed tier config: controls query breadth, candidate pool, and enrichment depth.
_SPEED_CONFIG = {
    "fast": {"max_variants": 4, "max_candidates": 8, "pool_size": 20, "enrich_cutoff": 0.5},
    "balanced": {"max_variants": 7, "max_candidates": 35, "pool_size": 30, "enrich_cutoff": 1.0},
    "thorough": {"max_variants": 8, "max_candidates": 50, "pool_size": 35, "enrich_cutoff": 1.0},
}


def _speed_slice(options: SearchOptions) -> SearchOptions:
    """Apply speed tier limits to a SearchOptions copy."""
    cfg = _SPEED_CONFIG.get(options.speed, _SPEED_CONFIG["balanced"])
    opts = SearchOptions(
        query=options.query,
        languages=options.languages,
        top=options.top,
        pool_size=min(options.pool_size, cfg["pool_size"]),
        min_stars=options.min_stars,
        pushed_after=options.pushed_after,
        license=options.license,
        include_forks=options.include_forks,
        include_archived=options.include_archived,
        max_candidates=min(options.max_candidates, cfg["max_candidates"]),
        speed=options.speed,
    )
    return opts


def run(
    options: SearchOptions,
    *,
    token: str | None = None,
    cache_ttl: int = 3600,
    debug: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> list:
    client = GitHubClient(token=token, ttl_seconds=cache_ttl)
    # Sin token, el límite core es 60 req/h; cada candidato usa commit+README.
    # Bajamos automáticamente el enriquecimiento para que el prototipo sea usable.
    if not client.token:
        options.max_candidates = min(options.max_candidates, 12)

    # Apply speed tier limits.
    opts = _speed_slice(options)

    if debug:
        print(f"debug: GitHub token present: {'yes' if client.token else 'no'}", file=sys.stderr)
        print(f"debug: speed tier: {opts.speed}", file=sys.stderr)
        print(f"debug: max_candidates after token+speed adjustment: {opts.max_candidates}", file=sys.stderr)
        print(f"debug: cache TTL seconds: {client.ttl_seconds}", file=sys.stderr)

    max_variants = _SPEED_CONFIG.get(opts.speed, _SPEED_CONFIG["balanced"])["max_variants"]
    all_candidates = []

    languages = options.languages or [None]
    if progress_callback:
        progress_callback("Preparando búsqueda…")

    for index, language in enumerate(languages, 1):
        if progress_callback:
            label = language or "todos los lenguajes"
            progress_callback(f"Buscando en GitHub ({index}/{len(languages)}): {label}…")
        queries = build_search_queries(
            options.query,
            language,
            min_stars=options.min_stars,
            pushed_after=options.pushed_after,
            license_filter=options.license,
            include_forks=options.include_forks,
            include_archived=options.include_archived,
            max_variants=max_variants,
        )[:max_variants]
        if debug:
            print(f"debug: generated {len(queries)} GitHub queries for {language}:", file=sys.stderr)
            for query in queries:
                print(f"debug:   {query}", file=sys.stderr)
        candidates = client.search_repositories(queries, per_page=opts.pool_size)
        all_candidates.extend(candidates)

    # Dedup entre lenguajes/queries y preorden por señales baratas para no enriquecer cientos.
    dedup = {c.full_name: c for c in all_candidates}
    preselected = sorted(
        dedup.values(),
        key=lambda c: (c.search_rank_score, c.stars, c.forks),
        reverse=True,
    )[: opts.max_candidates]
    if progress_callback:
        progress_callback(f"Analizando {len(preselected)} candidatos…")

    # Enriquecimiento con concurrencia baja y cutoff opcional por speed.
    enrich_cutoff = _SPEED_CONFIG.get(opts.speed, _SPEED_CONFIG["balanced"])["enrich_cutoff"]
    if enrich_cutoff < 1.0:
        cutoff = max(1, int(len(preselected) * enrich_cutoff))
        to_enrich = preselected[:cutoff]
    else:
        to_enrich = preselected

    enriched = []
    workers = 2 if client.token else 1
    if debug:
        print(f"debug: enrichment workers: {workers}, enriching {len(to_enrich)}/{len(preselected)}", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(client.enrich, candidate) for candidate in to_enrich]
        for completed, future in enumerate(as_completed(futures), 1):
            try:
                enriched.append(future.result())
                if progress_callback:
                    progress_callback(f"Enriqueciendo repositorios ({completed}/{len(to_enrich)})…")
            except GitHubAPIError as e:
                print(f"warning: no se pudo enriquecer un repo: {e}", file=sys.stderr)
    if progress_callback:
        progress_callback("Rankeando resultados…")
    return shortlist(enriched, options.query, top=options.top)


def _run_agent(args: argparse.Namespace) -> int:
    """Run search in agent mode: JSON output on stdout, progress stderr, _meta envelope."""
    if not args.query:
        print("Error: --query/-q es requerido para buscar.", file=sys.stderr)
        return 2
    if not args.language:
        print("Error: --language/-l es requerido para buscar.", file=sys.stderr)
        return 2

    languages = [lang.strip() for lang in args.language.split(",") if lang.strip()]
    options = SearchOptions(
        query=args.query,
        languages=languages,
        top=args.top,
        pool_size=args.pool_size,
        min_stars=args.min_stars,
        pushed_after=args.pushed_after,
        license=args.license_filter,
        include_forks=args.include_forks,
        include_archived=args.include_archived,
        max_candidates=args.max_candidates,
        speed=args.speed,
    )

    started = time.perf_counter()
    try:
        repos = run(options, token=args.token, cache_ttl=args.cache_ttl, debug=args.debug)
    except GitHubAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    elapsed = time.perf_counter() - started
    print(
        render_agent_json(
            repos,
            speed_tier=args.speed,
            query=args.query,
            elapsed=round(elapsed, 2),
            api_calls=len(repos),  # approximate: enriched repos = results
        )
    )
    return 0


def _run_web_mode(args: argparse.Namespace) -> int:
    """Run web companion mode: start local server and open browser."""
    import threading

    from .web.server import find_available_port, run_server

    history_store = SearchHistoryStore()
    port = find_available_port()

    def _start_server() -> None:
        try:
            run_server(port=port)
        except Exception as e:
            print(f"Error starting web server: {e}", file=sys.stderr)

    url = f"http://127.0.0.1:{port}"
    print(f"Sift Web Companion: {url}", file=sys.stderr)

    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    try:
        opened = webbrowser.open(url)
        if not opened:
            print(f"Could not open browser automatically. Visit: {url}", file=sys.stderr)
    except Exception:
        print(f"Could not open browser. Visit: {url}", file=sys.stderr)

    # Keep the main thread alive until interrupted
    try:
        server_thread.join()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Comandos de sesión — no necesitan query ni language.
    if args.login:
        try:
            login_interactive()
        except (RuntimeError, KeyboardInterrupt) as e:
            print(f"❌  Login fallido: {e}", file=sys.stderr)
            return 2
        return 0

    if args.logout:
        clear_token()
        print("👋  Token eliminado. La próxima búsqueda va a necesitar login o GITHUB_TOKEN.")
        return 0

    # Agent mode — force headless JSON with _meta.
    if args.agent:
        if args.web:
            print("Warning: --web is ignored in agent mode (--agent).", file=sys.stderr)
        return _run_agent(args)

    # Web companion mode (experimental, opt-in).
    if args.web:
        return _run_web_mode(args)

    # Interactive/TUI path — prompts for missing inputs.
    if args.force_interactive:
        return run_interactive_mode(args)
    if not args.no_interactive and not _is_headless():
        if is_interactive():
            return run_tui_mode(args)

    # Headless path — unchanged.
    if not args.query:
        print("Error: --query/-q es requerido para buscar.", file=sys.stderr)
        return 2
    if not args.language:
        print("Error: --language/-l es requerido para buscar.", file=sys.stderr)
        return 2

    # Si no hay token ni variable de entorno, sugerir login.
    if not load_token() and not args.token and not __import__("os").getenv("GITHUB_TOKEN"):
        print("💡  Sin token de GitHub. Podés correr `sift --login` para autenticarte fácil con OAuth.", file=sys.stderr)
        print("    O configurá GITHUB_TOKEN si preferís un token manual.", file=sys.stderr)

    languages = [lang.strip() for lang in args.language.split(",") if lang.strip()]
    options = SearchOptions(
        query=args.query,
        languages=languages,
        top=args.top,
        pool_size=args.pool_size,
        min_stars=args.min_stars,
        pushed_after=args.pushed_after,
        license=args.license_filter,
        include_forks=args.include_forks,
        include_archived=args.include_archived,
        max_candidates=args.max_candidates,
        speed=args.speed,
    )
    try:
        repos = run(options, token=args.token, cache_ttl=args.cache_ttl, debug=args.debug)
    except GitHubAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Persist results to history (fire-and-forget).
    try:
        _persist_search(args.query, languages, repos)
    except Exception:
        pass  # Non-blocking; history failure should not break the search.

    if args.format == "json":
        print(render_json(repos))
    elif args.format == "markdown":
        print(render_markdown(repos, args.query, languages))
    else:
        print(render_table(repos))
    return 0


def _persist_search(query: str, languages: list[str], repos: list) -> None:
    """Persist search results to history store (fire-and-forget)."""
    store = SearchHistoryStore()
    results = []
    for r in repos:
        results.append(
            {
                "name": r.full_name,
                "url": r.html_url,
                "description": r.description,
                "language": r.language,
                "stars": r.stars,
                "forks": r.forks,
                "score": r.score,
                "score_parts": r.score_parts,
                "license": r.license_spdx,
            }
        )
    store.add_entry(query, languages, results)


if __name__ == "__main__":
    raise SystemExit(main())
