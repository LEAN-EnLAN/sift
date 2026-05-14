from __future__ import annotations

import json
import shutil
from io import StringIO
from datetime import datetime
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table

from . import __version__
from .models import RepoCandidate


def render_compact_table(repos: list[RepoCandidate]) -> str:
    """Compact 4-column table optimized for interactive terminal use.

    Columns: #, Repo, Score, Why. No URL wrapping, no terminal width logic.
    This is the interactive equivalent of render_table — headless mode
    continues to use render_table unchanged.
    """
    table = Table(
        title=f"Top {len(repos)} repositorios recomendados",
        box=box.SIMPLE_HEAVY,
        expand=False,
        show_lines=False,
        pad_edge=False,
    )
    table.add_column("#", justify="right", style="cyan", no_wrap=True, width=2)
    table.add_column("Repo", style="bold", min_width=22)
    table.add_column("Score", justify="right", style="green", no_wrap=True, width=6)
    table.add_column("Why", overflow="fold", min_width=28)

    for index, repo in enumerate(repos, 1):
        table.add_row(
            str(index),
            repo.full_name,
            f"{repo.score:.2f}",
            _short_why(repo),
        )

    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, color_system=None, width=100)
    console.print(table)
    return buffer.getvalue().rstrip()


def render_json(repos: list[RepoCandidate]) -> str:
    payload: list[dict[str, Any]] = []
    for r in repos:
        payload.append(
            {
                "name": r.full_name,
                "url": r.html_url,
                "description": r.description,
                "language": r.language,
                "last_commit": r.last_commit_at or r.pushed_at,
                "score": r.score,
                "score_parts": r.score_parts,
                "stars": r.stars,
                "forks": r.forks,
                "license": r.license_spdx,
                "why": why_text(r),
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_agent_json(
    repos: list[RepoCandidate],
    *,
    speed_tier: str = "balanced",
    query: str = "",
    elapsed: float = 0.0,
    api_calls: int = 0,
) -> str:
    """JSON output with _meta envelope for agent/CI consumption.

    Preserves all existing JSON fields inside ``results``.
    ``_meta`` provides machine-readable execution metadata.
    """
    payload: list[dict[str, Any]] = []
    for r in repos:
        payload.append(
            {
                "name": r.full_name,
                "url": r.html_url,
                "description": r.description,
                "language": r.language,
                "last_commit": r.last_commit_at or r.pushed_at,
                "score": r.score,
                "score_parts": r.score_parts,
                "stars": r.stars,
                "forks": r.forks,
                "license": r.license_spdx,
                "why": why_text(r),
            }
        )
    return json.dumps(
        {
            "_meta": {
                "sift_version": __version__,
                "repo_scout_version": __version__,
                "speed_tier": speed_tier,
                "query": query,
                "elapsed_seconds": elapsed,
                "api_calls": api_calls,
                "?": "send --query, --language and --agent for machine-readable output",
            },
            "results": payload,
        },
        ensure_ascii=False,
        indent=2,
    )


def render_hermes_json(
    repos: list[RepoCandidate],
    *,
    speed_tier: str = "balanced",
    query: str = "",
    elapsed: float = 0.0,
    api_calls: int = 0,
) -> str:
    """JSON output for Hermes integration.

    Same shape as agent JSON but:
    - Adds ``hermes_compliance: "1.0"`` to _meta
    - Omits the human hint key ``?``
    """
    payload: list[dict[str, Any]] = []
    for r in repos:
        payload.append(
            {
                "name": r.full_name,
                "url": r.html_url,
                "description": r.description,
                "language": r.language,
                "last_commit": r.last_commit_at or r.pushed_at,
                "score": r.score,
                "score_parts": r.score_parts,
                "stars": r.stars,
                "forks": r.forks,
                "license": r.license_spdx,
                "why": why_text(r),
            }
        )
    return json.dumps(
        {
            "_meta": {
                "sift_version": __version__,
                "repo_scout_version": __version__,
                "speed_tier": speed_tier,
                "query": query,
                "elapsed_seconds": elapsed,
                "api_calls": api_calls,
                "hermes_compliance": "1.0",
            },
            "results": payload,
        },
        ensure_ascii=False,
        indent=2,
    )


def render_n8n_json(repos: list[RepoCandidate]) -> str:
    """Raw JSON array for n8n integration, no _meta envelope."""
    payload: list[dict[str, Any]] = []
    for r in repos:
        payload.append(
            {
                "name": r.full_name,
                "url": r.html_url,
                "description": r.description,
                "language": r.language,
                "last_commit": r.last_commit_at or r.pushed_at,
                "score": r.score,
                "score_parts": r.score_parts,
                "stars": r.stars,
                "forks": r.forks,
                "license": r.license_spdx,
                "why": why_text(r),
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_table(repos: list[RepoCandidate]) -> str:
    width = max(88, shutil.get_terminal_size((120, 24)).columns)
    table = Table(
        title=f"Top {len(repos)} repositorios recomendados",
        box=box.SIMPLE_HEAVY,
        expand=True,
        show_lines=False,
        pad_edge=False,
    )
    table.add_column("#", justify="right", style="cyan", no_wrap=True, width=2)
    table.add_column("Repo", style="bold", overflow="fold", ratio=4, min_width=22)
    table.add_column("Score", justify="right", style="green", no_wrap=True, width=6)
    table.add_column("Last", no_wrap=True, width=10)
    table.add_column("★", justify="right", no_wrap=True, width=7)
    table.add_column("Lang", no_wrap=True, width=8)
    table.add_column("Why", overflow="fold", ratio=5, min_width=28)

    for index, repo in enumerate(repos, 1):
        table.add_row(
            str(index),
            _repo_label(repo, include_url=width >= 150),
            f"{repo.score:.2f}",
            _date_only(repo.last_commit_at or repo.pushed_at),
            _compact_number(repo.stars),
            repo.language or "N/D",
            _short_why(repo),
        )

    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, color_system=None, width=width)
    console.print(table)
    return buffer.getvalue().rstrip()


def _repo_label(repo: RepoCandidate, *, include_url: bool) -> str:
    if not include_url:
        return repo.full_name
    url = repo.html_url.replace("https://", "")
    return f"{repo.full_name}\n{url}"


def _short_why(repo: RepoCandidate) -> str:
    if not repo.reasons:
        return "Buen balance entre relevancia, actividad, docs y comunidad."
    return "; ".join(repo.reasons[:2]) + "."


def _date_only(value: str | None) -> str:
    if not value:
        return "N/D"
    return value[:10]


def _compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value // 1_000}k"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def render_markdown(repos: list[RepoCandidate], query: str, languages: list[str]) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append(f"# Top {len(repos)} repos para: {query!r}")
    lines.append("")
    lines.append(f"Lenguaje(s): {', '.join(languages)}  ")
    lines.append(f"Generado: {now}")
    lines.append("")
    if not repos:
        lines.append("No encontré repositorios con señales de calidad suficientes. Probá relajar filtros o usar keywords más específicas.")
        return "\n".join(lines)

    lines.append("## Recomendaciones")
    lines.append("")
    for i, r in enumerate(repos, 1):
        last_commit = r.last_commit_at or r.pushed_at or "desconocido"
        lines.append(f"### {i}. [{r.full_name}]({r.html_url}) — score {r.score}/100")
        lines.append("")
        lines.append(f"- **Descripción:** {r.description or 'Sin descripción'}")
        lines.append(f"- **Última actividad (último commit):** {last_commit}")
        lines.append(f"- **Lenguaje:** {r.language or 'N/D'} | **Stars:** {r.stars} | **Forks:** {r.forks} | **Licencia:** {r.license_spdx or 'N/D'}")
        lines.append(f"- **Por qué este repo:** {why_text(r)}")
        lines.append(
            "- **Score breakdown:** "
            f"relevancia {r.score_parts.get('relevance', 0)}%, "
            f"actividad {r.score_parts.get('activity', r.score_parts.get('maintenance', 0))}%, "
            f"comunidad {r.score_parts.get('community', 0)}%, "
            f"docs {r.score_parts.get('docs', 0)}%, "
            f"mantenimiento {r.score_parts.get('maintenance', 0)}%, "
            f"modernidad {r.score_parts.get('modernity', 0)}%, "
            f"autoridad {r.score_parts.get('authority', 0)}%, "
            f"penalización {r.score_parts.get('penalties', 0)}%"
        )
        lines.append("")

    lines.append("## Mini comparación")
    lines.append("")
    lines.append("| Repo | Score | Último commit | Stars | Docs | Mantenimiento | Mejor para |")
    lines.append("|---|---:|---|---:|---:|---:|---|")
    for r in repos:
        lines.append(
            "| "
            f"[{r.full_name}]({r.html_url}) | {r.score} | {r.last_commit_at or r.pushed_at or 'N/D'} | "
            f"{r.stars} | {r.score_parts.get('docs')}% | {r.score_parts.get('maintenance')}% | {best_for(r)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_best_summary(repo: RepoCandidate) -> str:
    """One-line best-answer string for the TUI status bar.

    Format: "Best: owner/repo — score 85.3 — first reason; second reason."
    """
    parts = [f"Best: {repo.full_name} — score {repo.score:.1f}"]
    if repo.reasons:
        parts.append(" — " + "; ".join(repo.reasons[:2]) + ".")
    return "".join(parts)


def why_text(repo: RepoCandidate) -> str:
    if repo.reasons:
        return "; ".join(repo.reasons) + "."
    return "Buen balance entre relevancia, actividad, documentación y señales de comunidad."


def best_for(repo: RepoCandidate) -> str:
    name_desc = f"{repo.full_name} {repo.description or ''}".lower()
    if any(word in name_desc for word in ["boilerplate", "starter", "template"]):
        return "arrancar un proyecto rápido"
    if repo.score_parts.get("docs", 0) >= 70:
        return "integración con buena documentación"
    if repo.stars >= 5000:
        return "solución madura y popular"
    if repo.score_parts.get("activity", 0) >= 85:
        return "proyecto activo"
    return "evaluación técnica"
