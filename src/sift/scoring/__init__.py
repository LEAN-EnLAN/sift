"""Sift scoring: repository relevance and ranking.

This package replaces the monolithic scoring.py with a modular pipeline.
All v1 functions are preserved as _v1 suffixed fallbacks.
The default `score_repo` and `shortlist` now use the v2 pipeline.
Set SIFT_SCORING_V2=0 to use v1.

Usage (default — v2):
    from sift.scoring import shortlist, score_repo

Usage (v1 — opt-in):
    import os; os.environ["SIFT_SCORING_V2"] = "0"
    from sift.scoring import shortlist, score_repo

Usage (explicit v2):
    from sift.scoring import score_repo_v2, shortlist_v2
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone

from ..models import RepoCandidate
from ..query import classify_domain, extract_keywords

# v2 stage and seed imports (re-exported for convenient access)
from .seeds import CANONICAL_REPOS, DOMAIN_SEEDS, LEXICAL_TRAPS  # noqa: F401
from .stages import (  # noqa: F401
    stage_authority,
    stage_community,
    stage_composite,
    stage_docs,
    stage_eligibility,
    stage_maintenance,
    stage_modernity,
    stage_penalties,
    stage_relevance,
)

_SIFT_V2_DEFAULT = os.environ.get("SIFT_SCORING_V2", "1") != "0"


# ── v1: backward-compatible scoring functions (renamed _v1) ─────────────────
# These are preserved verbatim from the original scoring.py for rollback.


def parse_github_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def recency_score(value: str | None) -> float:
    dt = parse_github_date(value)
    if not dt:
        return 0.0
    days = (datetime.now(timezone.utc) - dt).days
    if days <= 30:
        return 1.0
    if days <= 90:
        return 0.85
    if days <= 180:
        return 0.70
    if days <= 365:
        return 0.50
    if days <= 730:
        return 0.25
    return 0.05


def popularity_score(stars: int, forks: int) -> float:
    star_score = clamp(math.log10(stars + 1) / 4.5)
    fork_score = clamp(math.log10(forks + 1) / 3.5)
    return 0.78 * star_score + 0.22 * fork_score


def documentation_score(readme: str) -> float:
    if not readme:
        return 0.0
    lower = readme.lower()
    length_score = clamp(len(readme) / 12000)
    sections = ["install", "installation", "usage", "quickstart", "example", "examples", "getting started", "docs"]
    section_score = clamp(sum(1 for s in sections if s in lower) / 5)
    code_score = 1.0 if "```" in readme or "pip install" in lower or "npm install" in lower else 0.0
    return 0.45 * length_score + 0.40 * section_score + 0.15 * code_score


def maintenance_score(repo: RepoCandidate) -> float:
    if repo.archived:
        return 0.0
    issue_pressure = 1.0 - clamp(repo.open_issues / max(repo.stars, 20), 0, 1)
    license_score = 1.0 if repo.license_spdx and repo.license_spdx != "NOASSERTION" else 0.55
    fork_penalty = 0.55 if repo.fork else 1.0
    return fork_penalty * (0.45 * recency_score(repo.last_commit_at or repo.pushed_at) + 0.25 * issue_pressure + 0.30 * license_score)


def relevance_score(repo: RepoCandidate, natural_query: str) -> float:
    keywords = extract_keywords(natural_query)
    if not keywords:
        return 0.35

    name = repo.full_name.lower().replace("-", " ").replace("_", " ")
    desc = (repo.description or "").lower()
    topics = " ".join(repo.topics).lower()
    readme = repo.readme_text[:30000].lower()

    weighted_hits = 0.0
    max_hits = 0.0
    for kw in keywords:
        terms = [kw.lower()]
        if " " in kw:
            terms.extend([t for t in kw.lower().split() if len(t) > 2])
        term_hit = 0.0
        for term in terms:
            if term in name:
                term_hit = max(term_hit, 1.0)
            if term in desc:
                term_hit = max(term_hit, 0.80)
            if term in topics:
                term_hit = max(term_hit, 0.85)
            if term in readme:
                term_hit = max(term_hit, 0.55)
        weighted_hits += term_hit
        max_hits += 1.0

    text_score = weighted_hits / max_hits if max_hits else 0.0
    rank_score = clamp(math.log1p(repo.search_rank_score) / 2.6)
    return clamp(0.75 * text_score + 0.25 * rank_score)


def _days_since_text(value: str | None) -> str | None:
    dt = parse_github_date(value)
    if not dt:
        return None
    days = (datetime.now(timezone.utc) - dt).days
    if days == 0:
        return "hoy"
    if days == 1:
        return "hace 1 día"
    if days < 60:
        return f"hace {days} días"
    months = round(days / 30)
    if months < 24:
        return f"hace {months} meses"
    years = round(days / 365, 1)
    return f"hace {years} años"


def _build_reasons_v1(repo: RepoCandidate) -> list[str]:
    reasons: list[str] = []
    days_text = _days_since_text(repo.last_commit_at or repo.pushed_at)
    if days_text:
        reasons.append(f"actividad reciente ({days_text})")
    if repo.stars >= 1000:
        reasons.append(f"comunidad fuerte ({repo.stars:,} stars)".replace(",", "."))
    elif repo.stars >= 100:
        reasons.append(f"tracción razonable ({repo.stars} stars)")
    if repo.score_parts.get("docs", 0) >= 55:
        reasons.append("README útil con instalación/uso/ejemplos")
    if repo.license_spdx and repo.license_spdx != "NOASSERTION":
        reasons.append(f"licencia {repo.license_spdx}")
    if not repo.archived and not repo.fork:
        reasons.append("no está archivado ni es fork")
    return reasons[:4]


def _score_repo_v1(repo: RepoCandidate, natural_query: str) -> RepoCandidate:
    rel = relevance_score(repo, natural_query)
    act = recency_score(repo.last_commit_at or repo.pushed_at)
    pop = popularity_score(repo.stars, repo.forks)
    doc = documentation_score(repo.readme_text)
    maint = maintenance_score(repo)

    raw_score = 100 * (0.35 * rel + 0.25 * act + 0.20 * pop + 0.10 * doc + 0.10 * maint)
    score = raw_score * (0.65 + 0.35 * rel)
    repo.score = round(score, 2)
    repo.score_parts = {
        "relevance": round(rel * 100, 1),
        "activity": round(act * 100, 1),
        "community": round(pop * 100, 1),
        "docs": round(doc * 100, 1),
        "maintenance": round(maint * 100, 1),
    }
    repo.reasons = _build_reasons_v1(repo)
    return repo


# Keep backward-compat alias for callers that import build_reasons.
build_reasons = _build_reasons_v1


def passes_relevance_gate(repo: RepoCandidate) -> bool:
    """Hard relevance gate: a repo must have at least 28% relevance to qualify."""
    relevance = repo.score_parts.get("relevance", 0.0) / 100
    return relevance >= 0.28


# ── v2 pipeline ─────────────────────────────────────────────────────────────


def _build_reasons_v2(repo: RepoCandidate, score_parts: dict[str, float], stage_scores: dict[str, float]) -> list[str]:
    """Build human-readable reasons from v2 score parts."""
    reasons: list[str] = []
    days_text = _days_since_text(repo.last_commit_at or repo.pushed_at)
    if days_text:
        reasons.append(f"actividad reciente ({days_text})")
    if score_parts.get("authority", 0) >= 80:
        reasons.append("proyecto canónico/referencia en el ecosistema")
    if repo.stars >= 1000:
        reasons.append(f"comunidad fuerte ({repo.stars:,} stars)".replace(",", "."))
    elif repo.stars >= 100:
        reasons.append(f"tracción razonable ({repo.stars} stars)")
    if score_parts.get("docs", 0) >= 55:
        reasons.append("README útil con instalación/uso/ejemplos")
    if repo.license_spdx and repo.license_spdx != "NOASSERTION":
        reasons.append(f"licencia {repo.license_spdx}")
    if not repo.archived and not repo.fork:
        reasons.append("no está archivado ni es fork")
    return reasons[:4]


def score_repo_v2(repo: RepoCandidate, natural_query: str) -> RepoCandidate:
    """Score a single repo using the v2 pipeline.

    Runs the 9-stage pipeline: eligibility → relevance → maintenance →
    modernity → docs → community → authority → penalties → composite.
    """
    keywords = extract_keywords(natural_query)
    domain = classify_domain(keywords)

    if not stage_eligibility(repo):
        repo.score = 0.0
        repo.score_parts = {k: 0.0 for k in (
            "relevance", "maintenance", "community", "docs",
            "modernity", "authority", "penalties",
        )}
        repo.reasons = []
        return repo

    stage_scores = {
        "relevance": stage_relevance(repo, keywords, domain),
        "maintenance": stage_maintenance(repo),
        "modernity": stage_modernity(repo),
        "docs": stage_docs(repo),
        "community": stage_community(repo),
        "authority": stage_authority(repo, domain),
    }
    penalty = stage_penalties(repo)
    composite, parts = stage_composite(repo, stage_scores, penalty)

    repo.score = round(composite, 2)
    repo.score_parts = parts
    repo.reasons = _build_reasons_v2(repo, parts, stage_scores)
    return repo


def shortlist_v2(
    candidates: list[RepoCandidate], natural_query: str, *, top: int = 5
) -> list[RepoCandidate]:
    """Shortlist candidates using the v2 pipeline exclusively."""
    scored = [score_repo_v2(repo, natural_query) for repo in candidates]
    scored = [r for r in scored if passes_relevance_gate_v2(r)]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top]


def passes_relevance_gate_v2(repo: RepoCandidate) -> bool:
    """Relevance gate for v2 scoring."""
    relevance = repo.score_parts.get("relevance", 0.0) / 100
    return relevance >= 0.28


# ── Default dispatch (env-controlled) ──────────────────────────────────────


def score_repo(repo: RepoCandidate, natural_query: str) -> RepoCandidate:
    """Score a repo using v2 by default; fall back to v1 with SIFT_SCORING_V2=0."""
    if _SIFT_V2_DEFAULT:
        return score_repo_v2(repo, natural_query)
    return _score_repo_v1(repo, natural_query)


def shortlist(
    candidates: list[RepoCandidate], natural_query: str, *, top: int = 5
) -> list[RepoCandidate]:
    """Shortlist candidates using v2 by default; fall back to v1 with SIFT_SCORING_V2=0."""
    if _SIFT_V2_DEFAULT:
        return shortlist_v2(candidates, natural_query, top=top)
    scored = [_score_repo_v1(repo, natural_query) for repo in candidates]
    scored = [r for r in scored if not r.archived and passes_relevance_gate(r)]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top]
