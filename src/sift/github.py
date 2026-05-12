from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .auth import load_token
from .models import RepoCandidate
from .query import github_search_url

API_BASE = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None, cache_dir: str = ".cache/sift", ttl_seconds: int = 3600):
        self.token = token or os.getenv("GITHUB_TOKEN") or load_token()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.last_rate_remaining: int | None = None
        self.last_rate_reset: int | None = None
        self._lock = threading.Lock()
        self._last_request_at = 0.0

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "sift-zafirus-exercise",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _cache_key(self, path: str) -> Path:
        digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _throttle(self, path: str) -> None:
        # Search API tiene límites específicos (10/min sin token, 30/min con token).
        # Un sleep chico evita secondary rate limits durante demos.
        if path.startswith("/search/"):
            min_interval = 2.2 if self.token else 6.2
        else:
            min_interval = 0.35 if self.token else 1.1
        with self._lock:
            elapsed = time.time() - self._last_request_at
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_at = time.time()

    def get_json(self, path: str, *, use_cache: bool = True, _retry: bool = True) -> Any:
        """GET con cache simple y manejo básico de rate limit.

        Con token GitHub permite mucho más margen. Sin token, la search API es limitada;
        cachear respuestas evita gastar cuota al repetir demos o ajustar scoring.
        """
        cache_file = self._cache_key(path)
        if use_cache and cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age <= self.ttl_seconds:
                return json.loads(cache_file.read_text(encoding="utf-8"))

        self._throttle(path)
        url = API_BASE + path
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                self.last_rate_remaining = _safe_int(resp.headers.get("X-RateLimit-Remaining"))
                self.last_rate_reset = _safe_int(resp.headers.get("X-RateLimit-Reset"))
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            remaining = e.headers.get("X-RateLimit-Remaining")
            reset = _safe_int(e.headers.get("X-RateLimit-Reset"))
            if e.code in (403, 429) and "secondary rate limit" in body.lower() and _retry:
                wait = 15 if self.token else 45
                time.sleep(wait)
                return self.get_json(path, use_cache=use_cache, _retry=False)
            if e.code in (403, 429) and remaining == "0" and reset:
                reset_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reset))
                raise GitHubAPIError(
                    f"Rate limit agotado. Configurá GITHUB_TOKEN o esperá hasta {reset_at}."
                ) from e
            raise GitHubAPIError(f"GitHub API error {e.code}: {body[:400]}") from e
        except urllib.error.URLError as e:
            raise GitHubAPIError(f"No se pudo conectar a GitHub: {e}") from e

        if use_cache:
            cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def search_repositories(self, queries: list[str], *, per_page: int = 30) -> list[RepoCandidate]:
        merged: dict[int, RepoCandidate] = {}
        rank_points: dict[int, float] = {}

        # Combinamos best-match, stars y updated sin disparar demasiadas requests.
        # La versión sin token de GitHub Search es especialmente limitada (10/min).
        search_specs: list[tuple[str, str | None]] = []
        if queries:
            search_specs.extend([(queries[0], None), (queries[0], "stars"), (queries[0], "updated")])
            search_specs.extend((q, None) for q in queries[1:5])

        for q, sort in search_specs:
            data = self.get_json(github_search_url(q, sort=sort, per_page=per_page))
            for index, item in enumerate(data.get("items", [])):
                repo_id = item["id"]
                # Mayor puntaje si aparece temprano o en varias variantes.
                rank_points[repo_id] = rank_points.get(repo_id, 0.0) + max(0.1, 1.0 - index / max(per_page, 1))
                if repo_id not in merged:
                    merged[repo_id] = repo_from_item(item)

        for repo_id, repo in merged.items():
            repo.search_rank_score = rank_points.get(repo_id, 0.0)
        return list(merged.values())

    def enrich(self, repo: RepoCandidate, *, readme_limit: int = 70000) -> RepoCandidate:
        owner_repo = repo.full_name
        # Último commit real sobre default branch. Si falla, usamos pushed_at como fallback.
        try:
            branch = urllib.parse.quote(repo.default_branch or "main", safe="")
            commits = self.get_json(f"/repos/{owner_repo}/commits?per_page=1&sha={branch}")
            if commits:
                commit = commits[0]
                repo.last_commit_at = (
                    commit.get("commit", {}).get("committer", {}).get("date")
                    or commit.get("commit", {}).get("author", {}).get("date")
                )
                repo.last_commit_sha = commit.get("sha")
                repo.last_commit_url = commit.get("html_url")
        except GitHubAPIError:
            repo.last_commit_at = repo.pushed_at

        # README para relevancia y documentación. El endpoint devuelve base64.
        try:
            readme = self.get_json(f"/repos/{owner_repo}/readme")
            encoded = readme.get("content", "")
            if encoded:
                raw = base64.b64decode(encoded, validate=False)
                repo.readme_text = raw.decode("utf-8", errors="replace")[:readme_limit]
        except GitHubAPIError:
            repo.readme_text = ""
        return repo


def repo_from_item(item: dict[str, Any]) -> RepoCandidate:
    license_obj = item.get("license") or {}
    return RepoCandidate(
        full_name=item.get("full_name", ""),
        html_url=item.get("html_url", ""),
        description=item.get("description"),
        language=item.get("language"),
        stars=item.get("stargazers_count", 0),
        forks=item.get("forks_count", 0),
        watchers=item.get("watchers_count", 0),
        open_issues=item.get("open_issues_count", 0),
        pushed_at=item.get("pushed_at"),
        updated_at=item.get("updated_at"),
        created_at=item.get("created_at"),
        archived=item.get("archived", False),
        fork=item.get("fork", False),
        license_spdx=license_obj.get("spdx_id"),
        topics=item.get("topics") or [],
        default_branch=item.get("default_branch") or "main",
        raw=item,
    )


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
