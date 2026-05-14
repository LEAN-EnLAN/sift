"""API routes for the web companion server."""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ..persistence.history import SearchHistoryStore

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(history_store: SearchHistoryStore) -> Starlette:
    """Create the Starlette application with API routes and static files."""

    async def health(request: Any) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def get_history(request: Any) -> JSONResponse:
        limit = request.query_params.get("limit")
        entries = history_store.get_entries(limit=int(limit) if limit else None)
        return JSONResponse({"entries": entries})

    async def search(request: Any) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

        query = body.get("query")
        if not query:
            return JSONResponse({"error": "query is required"}, status_code=400)

        languages = body.get("languages", [])
        top = body.get("top", 5)

        # Lazy import to avoid hard dependency when web extras not installed.
        try:
            from ..cli import run
            from ..models import SearchOptions
        except ImportError:
            return JSONResponse(
                {"error": "Core sift modules unavailable"},
                status_code=500,
            )

        options = SearchOptions(
            query=query,
            languages=languages,
            top=top,
            speed="balanced",
        )
        try:
            repos = run(options)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

        # Persist to history (isolated — must not break search results)
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
                    "why": _why_text(r),
                }
            )
        try:
            history_store.add_entry(query, languages, results)
        except Exception:
            pass  # History failure must not break search response

        return JSONResponse({"results": results})

    routes = [
        Route("/api/health", health),
        Route("/api/history", get_history),
        Route("/api/search", search, methods=["POST"]),
        Mount("/", app=StaticFiles(directory=str(_STATIC_DIR), html=True), name="static"),
    ]

    return Starlette(routes=routes)


def _why_text(repo: Any) -> str:
    """Generate a 'why' explanation for a repo candidate."""
    if repo.reasons:
        return "; ".join(repo.reasons) + "."
    return "Buen balance entre relevancia, actividad, documentación y señales de comunidad."
