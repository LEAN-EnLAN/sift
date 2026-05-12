from datetime import datetime, timedelta, timezone

from sift.models import RepoCandidate
from sift.scoring import passes_relevance_gate, popularity_score, recency_score, score_repo, shortlist


def make_repo(**overrides) -> RepoCandidate:
    values = {
        "full_name": "owner/project",
        "html_url": "https://github.com/owner/project",
        "description": "JWT authentication helper for Python APIs",
        "language": "Python",
        "stars": 250,
        "forks": 20,
        "watchers": 250,
        "open_issues": 5,
        "pushed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_at": "2022-01-01T00:00:00Z",
        "archived": False,
        "fork": False,
        "license_spdx": "MIT",
        "topics": ["jwt", "authentication"],
        "search_rank_score": 2.0,
        "readme_text": "## Installation\n```bash\npip install project\n```\n## Usage\nJWT authentication examples",
    }
    values.update(overrides)
    return RepoCandidate(**values)


def test_recency_score_decreases_for_older_commits() -> None:
    recent = datetime.now(timezone.utc) - timedelta(days=10)
    stale = datetime.now(timezone.utc) - timedelta(days=900)

    assert recency_score(recent.isoformat()) == 1.0
    assert recency_score(stale.isoformat()) == 0.05


def test_archived_repo_is_removed_from_shortlist() -> None:
    archived = make_repo(full_name="owner/archived", archived=True)
    active = make_repo(full_name="owner/active")

    result = shortlist([archived, active], "autenticación con JWT", top=5)

    assert [repo.full_name for repo in result] == ["owner/active"]


def test_popularity_uses_log_scale_not_linear_dominance() -> None:
    small = popularity_score(stars=100, forks=10)
    huge = popularity_score(stars=100_000, forks=10_000)

    assert huge <= 1.0
    assert huge < small * 3


def test_relevance_gate_excludes_popular_weak_match_with_low_search_rank() -> None:
    weak = make_repo(
        full_name="owner/popular-unrelated",
        description="A popular machine learning toolkit",
        stars=100_000,
        forks=20_000,
        topics=["machine-learning"],
        readme_text="Deep learning examples and tutorials",
        search_rank_score=0.2,
    )
    score_repo(weak, "autenticación con JWT")

    assert not passes_relevance_gate(weak)
    assert shortlist([weak], "autenticación con JWT", top=5) == []


def test_relevance_gate_keeps_specific_match() -> None:
    specific = make_repo(search_rank_score=0.5)
    score_repo(specific, "autenticación con JWT")

    assert passes_relevance_gate(specific)


def test_hard_gate_rejects_high_search_rank_with_low_relevance() -> None:
    """Relevance < 0.28 is rejected even with high search_rank_score (new hard gate)."""
    high_rank = make_repo(
        full_name="owner/high-rank-low-rel",
        description="Machine learning toolkit for deep learning",
        stars=100_000,
        forks=20_000,
        topics=["machine-learning", "deep-learning"],
        readme_text="Deep learning framework with GPU support",
        search_rank_score=5.0,
    )
    score_repo(high_rank, "autenticación con JWT")
    # High search_rank_score should NOT bypass the hard relevance gate.
    assert not passes_relevance_gate(high_rank)
