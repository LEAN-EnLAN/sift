import json
from datetime import datetime, timedelta, timezone

from sift.models import RepoCandidate
from sift.scoring import (
    passes_relevance_gate,
    passes_relevance_gate_v2,
    popularity_score,
    recency_score,
    score_repo,
    score_repo_v2,
    shortlist,
    shortlist_v2,
)
from sift.scoring.seeds import CANONICAL_REPOS, DOMAIN_SEEDS, LEXICAL_TRAPS
from sift.scoring.stages import (
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


# ─── PR 1: Foundation — scoring v2 package ────────────────────────────────


class TestRepoCandidateSearchVariantOrigin:
    """RepoCandidate.search_variant_origin field for scoring v2."""

    def test_default_is_empty_string(self) -> None:
        repo = make_repo()
        assert repo.search_variant_origin == ""

    def test_can_be_set_via_constructor(self) -> None:
        repo = make_repo(search_variant_origin="seed-forward")
        assert repo.search_variant_origin == "seed-forward"

    def test_can_be_set_directly(self) -> None:
        repo = make_repo()
        repo.search_variant_origin = "domain-field"
        assert repo.search_variant_origin == "domain-field"


class TestSeedsConstants:
    """Domain seed maps and lexical traps from seeds.py."""

    def test_domain_seeds_pdf_has_expected_libs(self) -> None:
        pdf_seeds = DOMAIN_SEEDS["pdf"]
        assert isinstance(pdf_seeds, list)
        assert "pymupdf" in pdf_seeds
        assert "pypdf" in pdf_seeds

    def test_domain_seeds_jwt_auth_has_expected_libs(self) -> None:
        jwt_seeds = DOMAIN_SEEDS["jwt-auth"]
        assert "pyjwt" in jwt_seeds
        assert "authlib" in jwt_seeds

    def test_domain_seeds_orm_has_expected_libs(self) -> None:
        orm_seeds = DOMAIN_SEEDS["orm"]
        assert "sqlalchemy" in orm_seeds

    def test_domain_seeds_boilerplate_has_expected_libs(self) -> None:
        bp_seeds = DOMAIN_SEEDS["boilerplate"]
        assert "cookiecutter" in bp_seeds

    def test_lexical_traps_pdf_has_trap_terms(self) -> None:
        traps = LEXICAL_TRAPS["pdf"]
        assert isinstance(traps, set)
        assert "edit" in traps
        assert "editor" in traps

    def test_lexical_traps_jwt_auth_has_trap_terms(self) -> None:
        traps = LEXICAL_TRAPS["jwt-auth"]
        assert isinstance(traps, set)
        assert "build" in traps
        assert "create" in traps

    def test_canonical_repos_is_non_empty_set_of_strings(self) -> None:
        assert isinstance(CANONICAL_REPOS, set)
        assert len(CANONICAL_REPOS) > 0
        assert all(isinstance(r, str) for r in CANONICAL_REPOS)


class TestStageSignatures:
    """Stage functions exist, are callable, and return expected stub types."""

    def test_stage_eligibility_is_callable_and_returns_bool(self) -> None:
        result = stage_eligibility(make_repo())
        assert isinstance(result, bool)

    def test_stage_relevance_is_callable_and_returns_float(self) -> None:
        result = stage_relevance(make_repo(), keywords=["jwt"], domain="jwt-auth")
        assert isinstance(result, (int, float))

    def test_stage_maintenance_is_callable_and_returns_float(self) -> None:
        result = stage_maintenance(make_repo())
        assert isinstance(result, (int, float))

    def test_stage_modernity_is_callable_and_returns_float(self) -> None:
        result = stage_modernity(make_repo())
        assert isinstance(result, (int, float))

    def test_stage_docs_is_callable_and_returns_float(self) -> None:
        result = stage_docs(make_repo())
        assert isinstance(result, (int, float))

    def test_stage_community_is_callable_and_returns_float(self) -> None:
        result = stage_community(make_repo())
        assert isinstance(result, (int, float))

    def test_stage_authority_is_callable_and_returns_float(self) -> None:
        result = stage_authority(make_repo(), domain="jwt-auth")
        assert isinstance(result, (int, float))

    def test_stage_penalties_is_callable_and_returns_float(self) -> None:
        result = stage_penalties(make_repo())
        assert isinstance(result, (int, float))

    def test_stage_composite_is_callable_and_returns_tuple(self) -> None:
        result = stage_composite(make_repo(), stage_scores={"relevance": 0.5}, penalty=0.0)
        assert isinstance(result, tuple)
        assert len(result) == 2
        score_val, parts = result
        assert isinstance(score_val, float)
        assert isinstance(parts, dict)


class TestScoringV2Exports:
    """__init__.py exposes expected top-level API."""

    def test_score_repo_v2_is_callable(self) -> None:
        repo = make_repo()
        result = score_repo_v2(repo, "jwt auth")
        assert isinstance(result, RepoCandidate)
        assert isinstance(result.score, float)
        assert "modernity" in result.score_parts
        assert "authority" in result.score_parts
        assert "penalties" in result.score_parts

    def test_shortlist_v2_is_callable(self) -> None:
        result = shortlist_v2([], "jwt auth", top=5)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_passes_relevance_gate_v2_is_callable_and_returns_bool(self) -> None:
        repo = make_repo()
        result = passes_relevance_gate_v2(repo)
        assert isinstance(result, bool)


# ─── PR 2: Scoring v2 — Behavioral stage tests ──────────────────────────────


class TestStageEligibility:
    """stage_eligibility gate behavior."""

    def test_eligibility_archived_disqualified(self) -> None:
        """Archived repo fails eligibility gate."""
        repo = make_repo(archived=True)
        assert stage_eligibility(repo) is False

    def test_eligibility_normal_passes(self) -> None:
        """Normal repo passes eligibility gate."""
        repo = make_repo()
        assert stage_eligibility(repo) is True

    def test_eligibility_no_description_no_stars_disqualified(self) -> None:
        """Repo with no description AND no stars fails."""
        repo = make_repo(description=None, stars=0)
        assert stage_eligibility(repo) is False

    def test_eligibility_fork_no_desc_disqualified(self) -> None:
        """Fork with no description fails eligibility."""
        repo = make_repo(fork=True, description=None)
        assert stage_eligibility(repo) is False


class TestStageAuthority:
    """stage_authority canonical repo matching."""

    def test_authority_canonical_match(self) -> None:
        """Repo matching CANONICAL_REPOS gets high authority score."""
        repo = make_repo(full_name="jpadilla/pyjwt")
        score = stage_authority(repo, domain="jwt-auth")
        assert score >= 80

    def test_authority_no_match_low(self) -> None:
        """Non-canonical repo gets low authority score."""
        repo = make_repo(full_name="owner/random-lib")
        score = stage_authority(repo, domain="jwt-auth")
        assert score < 20

    def test_authority_domain_mismatch_low(self) -> None:
        """Canonical repo in wrong domain gets low authority."""
        repo = make_repo(full_name="jpadilla/pyjwt")
        score = stage_authority(repo, domain="pdf")
        assert score < 20


class TestStagePenalties:
    """stage_penalties penalty computation."""

    def test_penalties_awesome_list(self) -> None:
        """Repo with 'awesome' in topics gets penalty."""
        repo = make_repo(topics=["awesome", "jwt", "python"])
        penalty = stage_penalties(repo)
        assert penalty > 0

    def test_penalties_clean_repo_no_penalty(self) -> None:
        """Normal repo gets no penalty."""
        repo = make_repo()
        penalty = stage_penalties(repo)
        assert penalty == 0

    def test_penalties_toy_demo_in_name(self) -> None:
        """Repo with 'tutorial' in description gets penalty."""
        repo = make_repo(description="A tutorial project for learning JWT")
        penalty = stage_penalties(repo)
        assert penalty > 0

    def test_penalties_high_issue_ratio(self) -> None:
        """Repo with very high open-issue-to-stars ratio gets penalty."""
        repo = make_repo(stars=10, open_issues=20)
        penalty = stage_penalties(repo)
        assert penalty > 0


class TestStageComposite:
    """stage_composite score combination."""

    def test_composite_preserves_all_keys(self) -> None:
        """Composite score_parts includes all seven expected keys."""
        stage_scores = {
            "relevance": 80.0,
            "maintenance": 70.0,
            "community": 60.0,
            "docs": 50.0,
            "modernity": 40.0,
            "authority": 30.0,
        }
        repo = make_repo()
        score, parts = stage_composite(repo, stage_scores, penalty=0.0)
        assert isinstance(score, float)
        assert score > 0
        for key in ("relevance", "maintenance", "community", "docs", "modernity", "authority", "penalties"):
            assert key in parts, f"Missing key: {key}"

    def test_composite_penalty_reduces_score(self) -> None:
        """Penalty subtracts from composite score."""
        stage_scores = {k: 50.0 for k in ("relevance", "maintenance", "community", "docs", "modernity", "authority")}
        repo = make_repo()
        score_no_penalty, _ = stage_composite(repo, stage_scores, penalty=0.0)
        score_with_penalty, _ = stage_composite(repo, stage_scores, penalty=15.0)
        assert score_with_penalty < score_no_penalty

    def test_composite_clamps_between_0_and_100(self) -> None:
        """Composite score is clamped between 0 and 100."""
        repo = make_repo()
        high_scores = {k: 200.0 for k in ("relevance", "maintenance", "community", "docs", "modernity", "authority")}
        score, _ = stage_composite(repo, high_scores, penalty=0.0)
        assert score <= 100.0


class TestStageRelevance:
    """stage_relevance keyword matching."""

    def test_relevance_jwt_keyword_match(self) -> None:
        """Repo with JWT in name/description gets high relevance."""
        repo = make_repo(full_name="jpadilla/pyjwt", description="JWT auth for Python", topics=["jwt"])
        score = stage_relevance(repo, keywords=["jwt", "auth", "python"], domain="jwt-auth")
        assert score > 50

    def test_relevance_no_match_low(self) -> None:
        """Repo with no matching keywords gets low relevance."""
        repo = make_repo(
            full_name="owner/unrelated",
            description="Image processing library",
            topics=["image"],
            readme_text="A library for processing images and graphics.",
        )
        score = stage_relevance(repo, keywords=["jwt", "auth"], domain="jwt-auth")
        assert score < 30


class TestStageMaintenance:
    """stage_maintenance health scoring."""

    def test_maintenance_fresh_commit_high(self) -> None:
        """Recently committed repo gets high maintenance score."""
        repo = make_repo(last_commit_at=datetime.now(timezone.utc).isoformat(), open_issues=1, license_spdx="MIT")
        score = stage_maintenance(repo)
        assert score > 50

    def test_maintenance_archived_low(self) -> None:
        """Archived repo gets low maintenance score."""
        repo = make_repo(archived=True)
        score = stage_maintenance(repo)
        assert score < 30


class TestStageDocs:
    """stage_docs documentation quality."""

    def test_docs_rich_readme_high(self) -> None:
        """README with install+usage+examples+API gets high docs score."""
        repo = make_repo(
            readme_text=(
                "# Project\n\n"
                "A longer README with thorough coverage.\n\n"
                "## Installation\npip install project\n\n"
                "## Quickstart\n```python\nimport project\nproject.run()\n```\n\n"
                "## Usage\nSee examples below for common patterns.\n\n"
                "## Examples\nHere are some examples.\n\n"
                "## API\n\n## Configuration\n\n## Contributing\n\n## License\nMIT"
            )
        )
        score = stage_docs(repo)
        assert score > 50

    def test_docs_empty_readme_low(self) -> None:
        """Empty or missing README gets low docs score."""
        repo = make_repo(readme_text="")
        score = stage_docs(repo)
        assert score < 30


class TestStageCommunity:
    """stage_community engagement scoring."""

    def test_community_high_stars_high(self) -> None:
        """Repo with many stars/forks gets high community score."""
        repo = make_repo(stars=10000, forks=2000, watchers=5000)
        score = stage_community(repo)
        assert score > 50

    def test_community_zero_stars_low(self) -> None:
        """Repo with no stars gets low community score."""
        repo = make_repo(stars=0, forks=0, watchers=0)
        score = stage_community(repo)
        assert score < 20


class TestStageModernity:
    """stage_modernity recency scoring."""

    def test_modernity_recent_creation_high(self) -> None:
        """Recently created repo gets high modernity score."""
        repo = make_repo(created_at=datetime.now(timezone.utc).isoformat())
        score = stage_modernity(repo)
        assert score > 50

    def test_modernity_old_project_low(self) -> None:
        """Very old repo gets low modernity score."""
        repo = make_repo(created_at="2010-01-01T00:00:00Z")
        score = stage_modernity(repo)
        assert score < 30


# ─── PR 3: Integration tests + Agent JSON verification ─────────────────────


class TestScoreRepoV2EndToEnd:
    """Integration test: score_repo_v2 with synthetic candidate fixture set."""

    def test_empty_candidate_set(self) -> None:
        """Empty candidate list produces no output from shortlist_v2."""
        result = shortlist_v2([], "JWT auth python", top=5)
        assert result == []

    def test_scores_correctly_orders_repos(self) -> None:
        """score_repo_v2 produces sensible ordering: canonical > toy > irrelevant."""
        canonical = make_repo(
            full_name="jpadilla/pyjwt",
            description="JWT authentication for Python",
            stars=5000,
            forks=800,
            topics=["jwt", "auth", "python"],
            readme_text="## Installation\n```bash\npip install pyjwt\n```\n## Usage\nJWT auth examples.",
            license_spdx="MIT",
        )
        toy = make_repo(
            full_name="owner/jwt-tutorial",
            description="A tutorial project for learning JWT",
            stars=50,
            forks=5,
            topics=["jwt", "tutorial"],
            readme_text="## JWT tutorial\nA simple tutorial for JWT.",
            license_spdx="MIT",
        )
        irrelevant = make_repo(
            full_name="owner/unrelated-hw",
            description="Hardware description language tools",
            stars=10,
            forks=2,
            topics=["vhdl", "verilog", "fpga"],
            readme_text="## HDL tools\nHardware description utilities.",
            license_spdx="MIT",
        )

        for repo in [canonical, toy, irrelevant]:
            score_repo_v2(repo, "JWT authentication python")

        # Canonical should score higher than toy
        assert canonical.score > toy.score, (
            f"Canonical ({canonical.score}) should beat toy ({toy.score})"
        )
        # Irrelevant (no keyword match) should be lowest
        assert toy.score > irrelevant.score or irrelevant.score == 0, (
            f"Toy ({toy.score}) should beat irrelevant ({irrelevant.score})"
        )

    def test_shortlist_v2_orders_and_limits(self) -> None:
        """shortlist_v2 returns top-N repos ordered by score descending."""
        repos = []
        for i in range(10):
            repos.append(make_repo(
                full_name=f"owner/repo-{i}",
                description="A JWT library",
                stars=100 * (i + 1),
                topics=["jwt"],
                readme_text="## JWT lib\nJWT authentication library.",
            ))

        result = shortlist_v2(repos, "JWT authentication python", top=3)
        assert len(result) <= 3
        if len(result) >= 2:
            assert result[0].score >= result[1].score

    def test_v2_pipeline_stages_run_in_order(self) -> None:
        """Full v2 pipeline runs through all stages and produces expected score_parts."""
        repo = make_repo(
            full_name="jpadilla/pyjwt",
            description="JWT authentication for Python APIs",
            stars=5656,
            forks=1200,
            topics=["jwt", "authentication", "python"],
            readme_text=(
                "## Installation\n```bash\npip install pyjwt\n```\n"
                "## Usage\n```python\nimport jwt\n```\n"
                "## API\n## Configuration\n## Examples\n"
            ),
            license_spdx="MIT",
        )
        score_repo_v2(repo, "JSON Web Token authentication python")
        assert repo.score > 0
        assert "relevance" in repo.score_parts
        assert "maintenance" in repo.score_parts
        assert "community" in repo.score_parts
        assert "docs" in repo.score_parts
        assert "modernity" in repo.score_parts
        assert "authority" in repo.score_parts
        assert "penalties" in repo.score_parts
        assert isinstance(repo.reasons, list)

    def test_candidate_with_no_readme_scores_but_docs_low(self) -> None:
        """Repo with empty README still scores but docs part is low."""
        repo = make_repo(readme_text="", stars=5000)
        score_repo_v2(repo, "JWT auth python")
        assert repo.score > 0
        assert repo.score_parts.get("docs", 100) < 50


class TestAgentJsonPreservesFields:
    """Agent JSON output preserves score, score_parts, why fields."""

    def test_agent_json_has_all_required_fields(self) -> None:
        """Agent JSON output includes score, score_parts, and why."""
        from sift.render import render_agent_json

        repo = make_repo(
            full_name="jpadilla/pyjwt",
            score=85.3,
            score_parts={
                "relevance": 90.0,
                "maintenance": 75.0,
                "community": 82.0,
                "docs": 70.0,
                "modernity": 65.0,
                "authority": 90.0,
                "penalties": 0.0,
            },
            reasons=["actividad reciente (hace 2 meses)", "comunidad fuerte (5.656 stars)"],
        )

        output = render_agent_json([repo], speed_tier="balanced", query="test", elapsed=1.0, api_calls=3)
        data = json.loads(output)

        assert "results" in data
        assert len(data["results"]) == 1
        r = data["results"][0]
        assert "score" in r
        assert "score_parts" in r
        assert "why" in r
        assert r["score"] == 85.3
        assert r["score_parts"]["authority"] == 90.0
        assert r["score_parts"]["penalties"] == 0.0
        assert r["score_parts"]["modernity"] == 65.0

    def test_agent_json_v2_scored_repo_preserves_fields(self) -> None:
        """Repo scored via score_repo_v2 and rendered via agent JSON has all required fields."""
        from sift.render import render_agent_json

        repo = make_repo(
            full_name="jpadilla/pyjwt",
            description="JWT authentication library for Python",
            stars=5656,
            forks=1200,
            license_spdx="MIT",
        )
        score_repo_v2(repo, "JSON Web Token authentication python")

        output = render_agent_json([repo], speed_tier="balanced", query="JWT auth", elapsed=2.5, api_calls=7)
        data = json.loads(output)

        r = data["results"][0]
        assert r["name"] == "jpadilla/pyjwt"
        assert isinstance(r["score"], (int, float))
        assert r["score"] > 0
        assert "relevance" in r["score_parts"]
        assert "maintenance" in r["score_parts"]
        assert "community" in r["score_parts"]
        assert "docs" in r["score_parts"]
        assert "modernity" in r["score_parts"]
        assert "authority" in r["score_parts"]
        assert "penalties" in r["score_parts"]
        assert isinstance(r["why"], str) and len(r["why"]) > 0

    def test_agent_json_meta_fields_present(self) -> None:
        """_meta envelope contains expected keys."""
        from sift.render import render_agent_json

        repo = make_repo(score=92.0)
        output = render_agent_json([repo], speed_tier="fast", query="test", elapsed=0.5, api_calls=2)
        data = json.loads(output)

        meta = data["_meta"]
        assert "sift_version" in meta
        assert "repo_scout_version" in meta
        assert "speed_tier" in meta
        assert "query" in meta
        assert "elapsed_seconds" in meta
        assert "api_calls" in meta
        assert "?" in meta
        assert meta["speed_tier"] == "fast"
        assert meta["query"] == "test"


# ─── PR 3: Rollback safety — SIFT_SCORING_V2=0 fallback ────────────────────


class TestScoringV2Rollback:
    """SIFT_SCORING_V2=0 env var causes score_repo() to use v1 pipeline."""

    def test_v2_default_has_new_score_parts(self) -> None:
        """Default (v2) score_parts includes authority, modernity, penalties."""
        repo = make_repo(full_name="jpadilla/pyjwt", stars=5000)
        score_repo(repo, "JWT auth python")
        assert "authority" in repo.score_parts
        assert "modernity" in repo.score_parts
        assert "penalties" in repo.score_parts

    def test_v1_fallback_has_legacy_score_parts(self, monkeypatch) -> None:
        """With SIFT_SCORING_V2=0, score_parts has activity but not authority."""
        monkeypatch.setenv("SIFT_SCORING_V2", "0")
        # Reimport to pick up the new env var
        import importlib
        from sift import scoring as scoring_mod
        importlib.reload(scoring_mod)
        from sift.scoring import score_repo

        repo = make_repo(full_name="jpadilla/pyjwt", stars=5000)
        score_repo(repo, "JWT auth python")
        # v1 has 'activity' but not 'authority'
        assert "activity" in repo.score_parts
        assert "authority" not in repo.score_parts
        assert "modernity" not in repo.score_parts
        assert "penalties" not in repo.score_parts

    def test_v1_fallback_shortlist_excludes_authority(self, monkeypatch) -> None:
        """With SIFT_SCORING_V2=0, shortlist() produces v1-style results."""
        monkeypatch.setenv("SIFT_SCORING_V2", "0")
        import importlib
        from sift import scoring as scoring_mod
        importlib.reload(scoring_mod)
        from sift.scoring import shortlist

        repos = [
            make_repo(full_name="jpadilla/pyjwt", stars=5000, description="JWT library"),
            make_repo(full_name="owner/tutorial", stars=50, description="JWT tutorial"),
        ]
        result = shortlist(repos, "JWT auth python", top=5)
        assert len(result) > 0
        for r in result:
            assert "authority" not in r.score_parts
            assert "modernity" not in r.score_parts
            assert "activity" in r.score_parts
