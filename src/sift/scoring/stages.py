"""Scoring v2 pipeline stage functions.

Each stage is a pure function that evaluates one dimension of a repository.
Stages return 0-100 scores (or a boolean for eligibility, or a penalty scalar).

PR 2: All stages are now fully implemented with local-only heuristics.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from ..models import RepoCandidate
from .seeds import CANONICAL_REPOS


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _days_ago(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).days


def _parse_github_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Stage 1: Eligibility Gate ──────────────────────────────────────────────


def stage_eligibility(repo: RepoCandidate) -> bool:
    """Gate stage: returns True if the repo is eligible for scoring.

    Disqualifies archived repos, forks with no description, or repos
    with missing critical metadata (no description, no stars).

    Returns:
        True if the repo passes the eligibility gate, False otherwise.
    """
    if repo.archived:
        return False
    # Fork without any description is likely uninteresting.
    if repo.fork and not repo.description:
        return False
    # No description AND no stars means it's essentially metadata-empty.
    if not repo.description and repo.stars == 0:
        return False
    return True


# ── Stage 2: Relevance ─────────────────────────────────────────────────────


def stage_relevance(repo: RepoCandidate, keywords: list[str], domain: str | None) -> float:
    """Score how well the repo's text content matches the user's keywords.

    Checks name, description, topics, and README for keyword matches.
    Name matches score highest, then topics, then description, then README.

    Args:
        repo: The repository candidate.
        keywords: Extracted keywords from the user's natural query.
        domain: Inferred domain tag or None (used for domain boost).

    Returns:
        Float 0-100 representing textual relevance.
    """
    if not keywords:
        return 0.0

    name = repo.full_name.lower().replace("-", " ").replace("_", " ")
    desc = (repo.description or "").lower()
    topics = " ".join(repo.topics).lower()
    readme = repo.readme_text[:30000].lower() if repo.readme_text else ""

    weighted_hits = 0.0
    for kw in keywords:
        term_hit = 0.0
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue
        if kw_lower in name:
            term_hit = max(term_hit, 1.0)
        if kw_lower in topics:
            term_hit = max(term_hit, 0.85)
        if kw_lower in desc:
            term_hit = max(term_hit, 0.80)
        if kw_lower in readme:
            term_hit = max(term_hit, 0.55)
        weighted_hits += term_hit

    text_score = weighted_hits / len(keywords)
    # Domain boost: if the domain appears in the repo name/desc, nudge up.
    if domain:
        domain_clean = domain.replace("-auth", "").replace("-", " ")
        if domain_clean in name or domain_clean in topics:
            text_score = min(1.0, text_score * 1.15)

    return round(_clamp(text_score, 0, 1) * 100, 1)


# ── Stage 3: Maintenance ────────────────────────────────────────────────────


def stage_maintenance(repo: RepoCandidate) -> float:
    """Score maintenance health based on recency, issue pressure, license, and fork status.

    Returns:
        Float 0-100 where higher means better maintained.
    """
    if repo.archived:
        return 0.0

    # Recency score based on last commit or pushed_at.
    last_dt = _parse_github_date(repo.last_commit_at or repo.pushed_at)
    days = _days_ago(last_dt) if last_dt else 999
    if days is None:
        recency = 0.0
    elif days <= 30:
        recency = 1.0
    elif days <= 90:
        recency = 0.85
    elif days <= 180:
        recency = 0.70
    elif days <= 365:
        recency = 0.50
    elif days <= 730:
        recency = 0.25
    else:
        recency = 0.05

    # Issue pressure: high issues relative to stars is a warning sign.
    issue_pressure = 1.0 - _clamp(repo.open_issues / max(repo.stars, 20), 0, 1)

    # License score.
    license_score = 1.0 if repo.license_spdx and repo.license_spdx != "NOASSERTION" else 0.55

    # Fork penalty.
    fork_penalty = 0.55 if repo.fork else 1.0

    composite = fork_penalty * (
        0.45 * recency + 0.25 * issue_pressure + 0.30 * license_score
    )
    return round(_clamp(composite, 0, 1) * 100, 1)


# ── Stage 4: Modernity ──────────────────────────────────────────────────────


def stage_modernity(repo: RepoCandidate) -> float:
    """Score how modern the repo is based on creation date.

    Newer repos indicate modern practices and tooling.

    Returns:
        Float 0-100 where higher means more modern.
    """
    dt = _parse_github_date(repo.created_at)
    days = _days_ago(dt) if dt else None
    if days is None:
        return 0.0
    # Graduated decay over 10 years.
    if days <= 90:
        return 100.0
    if days <= 365:
        return 85.0
    if days <= 730:
        return 70.0
    if days <= 1460:  # 4 years
        return 50.0
    if days <= 2190:  # 6 years
        return 30.0
    if days <= 3650:  # 10 years
        return 15.0
    return 5.0


# ── Stage 5: Documentation ──────────────────────────────────────────────────


def stage_docs(repo: RepoCandidate) -> float:
    """Score documentation quality based on README length, section coverage,
    and presence of code examples or installation instructions.

    Returns:
        Float 0-100 where higher means better documented.
    """
    readme = repo.readme_text or ""
    if not readme:
        return 0.0
    lower = readme.lower()

    # Length score: longer READMEs tend to be more thorough.
    length_score = _clamp(len(readme) / 12000, 0, 1)

    # Section coverage.
    sections = [
        "install", "installation", "usage", "quickstart",
        "example", "examples", "getting started", "docs",
        "api", "configuration", "contributing",
    ]
    section_score = _clamp(sum(1 for s in sections if s in lower) / 6, 0, 1)

    # Code/docs quality indicators.
    has_code = 1.0 if ("```" in readme or "pip install" in lower or "npm install" in lower) else 0.0
    has_badge = 1.0 if re.search(r"https://img\.shields\.io|https://badge\.fury\.io", lower) else 0.0

    composite = 0.40 * length_score + 0.35 * section_score + 0.15 * has_code + 0.10 * has_badge
    return round(_clamp(composite, 0, 1) * 100, 1)


# ── Stage 6: Community ──────────────────────────────────────────────────────


def stage_community(repo: RepoCandidate) -> float:
    """Score community engagement based on stars, forks, and watchers
    using log-scale normalization.

    Returns:
        Float 0-100 where higher means stronger community.
    """
    # Log-scale: each order of magnitude adds roughly equal points.
    star_score = _clamp(math.log10(repo.stars + 1) / 4.5, 0, 1)  # ~100k stars = 1.0
    fork_score = _clamp(math.log10(repo.forks + 1) / 3.5, 0, 1)    # ~3k forks = 1.0
    watcher_score = _clamp(math.log10(repo.watchers + 1) / 4.0, 0, 1)  # ~10k watchers = 1.0

    composite = 0.50 * star_score + 0.25 * fork_score + 0.25 * watcher_score
    return round(_clamp(composite, 0, 1) * 100, 1)


# ── Stage 7: Authority ─────────────────────────────────────────────────────


def stage_authority(repo: RepoCandidate, domain: str | None) -> float:
    """Score authority based on canonical repo matching.

    Uses the CANONICAL_REPOS set from seeds.py. A repo whose full_name
    is in the canonical set scores highly, but only if the repo name
    corresponds to a seed for the given domain.

    Args:
        repo: The repository candidate.
        domain: Inferred domain tag or None.

    Returns:
        Float 0-100 where higher means more authoritative.
    """
    if domain is None:
        return 0.0
    if repo.full_name not in CANONICAL_REPOS:
        return 0.0

    from .seeds import DOMAIN_SEEDS  # noqa: late import keeps stages self-contained

    # Verify domain relevance: the repo's short name should match a seed for this domain.
    repo_name_only = repo.full_name.split("/")[-1].lower()
    domain_seeds = DOMAIN_SEEDS.get(domain, [])
    if any(
        repo_name_only in seed.lower() or seed.lower() in repo_name_only
        for seed in domain_seeds
    ):
        return 90.0
    return 0.0


# ── Stage 8: Penalties ──────────────────────────────────────────────────────

_TOY_KEYWORDS = {"tutorial", "demo", "example", "playground", "sandbox", "learn", "sample"}


def stage_penalties(repo: RepoCandidate) -> float:
    """Compute penalty score for undesirable characteristics.

    Penalized patterns include:
    - Being in an awesome-list (detected via topics or name)
    - Being a toy/demo project
    - Having excessive open issues relative to stars
    - Being a fork without substantial divergence

    Returns:
        Float 0-25 (0 = no penalty, 25 = maximum penalty).
    """
    penalty = 0.0

    # Awesome-list penalty.
    name_lower = repo.full_name.lower()
    topics_lower = [t.lower() for t in repo.topics]
    if "awesome" in name_lower or "awesome" in topics_lower:
        penalty += 10.0

    # Toy/demo penalty.
    desc_lower = (repo.description or "").lower()
    repo_name_only = name_lower.split("/")[-1] if "/" in name_lower else name_lower
    for toy_word in _TOY_KEYWORDS:
        if toy_word in repo_name_only or toy_word in desc_lower:
            penalty += 8.0
            break  # At most one toy penalty.

    # High issue-to-stars ratio (potential abandonment).
    if repo.stars > 0 and repo.open_issues > repo.stars * 0.5:
        penalty += 5.0

    # Fork penalty (forks are usually derivative).
    if repo.fork:
        penalty += 3.0

    return min(penalty, 25.0)


# ── Stage 9: Composite ──────────────────────────────────────────────────────

_STAGE_WEIGHTS: dict[str, float] = {
    "relevance": 0.30,
    "maintenance": 0.20,
    "docs": 0.15,
    "community": 0.15,
    "modernity": 0.10,
    "authority": 0.10,
}


def stage_composite(
    repo: RepoCandidate,
    stage_scores: dict[str, float],
    penalty: float,
) -> tuple[float, dict[str, float]]:
    """Combine all stage scores into a final composite score.

    Applies domain-specific weights, subtracts penalties,
    and returns both the final score and a full score_parts dict.

    Args:
        repo: The repository candidate.
        stage_scores: dict of stage_name -> score (0-100).
        penalty: Penalty scalar (0-25).

    Returns:
        Tuple of (composite_score: float, score_parts: dict[str, float]).
    """
    weighted_sum = 0.0
    score_parts: dict[str, float] = {}
    for stage, weight in _STAGE_WEIGHTS.items():
        value = stage_scores.get(stage, 0.0)
        score_parts[stage] = round(value, 1)
        weighted_sum += value * weight

    # Subtract penalty.
    final = weighted_sum - penalty
    final = _clamp(final, 0, 100)

    # Add penalty to score_parts for transparency.
    score_parts["penalties"] = round(penalty, 1)

    return round(final, 2), score_parts
