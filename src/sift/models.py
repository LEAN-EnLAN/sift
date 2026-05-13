from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchOptions:
    query: str
    languages: list[str]
    top: int = 5
    pool_size: int = 35
    min_stars: int = 0
    pushed_after: str | None = None
    license: str | None = None
    include_forks: bool = False
    include_archived: bool = False
    max_candidates: int = 45
    speed: str = "balanced"


@dataclass
class RepoCandidate:
    full_name: str
    html_url: str
    description: str | None
    language: str | None
    stars: int
    forks: int
    watchers: int
    open_issues: int
    pushed_at: str | None
    updated_at: str | None
    created_at: str | None
    archived: bool
    fork: bool
    license_spdx: str | None
    topics: list[str] = field(default_factory=list)
    default_branch: str = "main"
    search_rank_score: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    # Enrichment
    readme_text: str = ""
    last_commit_at: str | None = None
    last_commit_sha: str | None = None
    last_commit_url: str | None = None

    # Query variant tracking (scoring v2)
    search_variant_origin: str = ""

    # Score output
    score: float = 0.0
    score_parts: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
