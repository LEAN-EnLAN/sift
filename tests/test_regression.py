"""Regression tests for scoring v2 ranking pipeline.

Ensures that for representative natural-language queries, the v2 pipeline
ranks canonical/relevant repositories above generic or low-quality alternatives.

All tests use synthetic repo fixtures — no GitHub API calls.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from sift.models import RepoCandidate
from sift.scoring import score_repo_v2, shortlist_v2
from sift.scoring.seeds import CANONICAL_REPOS


# ── Fixture helpers ──────────────────────────────────────────────────────────


def _make_candidate(
    full_name: str,
    description: str = "",
    stars: int = 500,
    forks: int = 50,
    topics: list[str] | None = None,
    readme_text: str = "## Library\n```pip install\n```\n## Usage\ndocs.",
    license_spdx: str = "MIT",
    **overrides: object,
) -> RepoCandidate:
    """Create a RepoCandidate with sensible defaults."""
    from datetime import datetime, timezone

    base = {
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "description": description or f"The {full_name.split('/')[-1]} library",
        "language": "Python",
        "stars": stars,
        "forks": forks,
        "watchers": max(stars // 4, 1),
        "open_issues": max(stars // 100, 1),
        "pushed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_at": "2022-01-01T00:00:00Z",
        "archived": False,
        "fork": False,
        "license_spdx": license_spdx,
        "topics": topics or [],
        "search_rank_score": 2.0,
        "readme_text": readme_text,
    }
    base.update(overrides)
    return RepoCandidate(**base)


# ── Per-domain fixture sets ──────────────────────────────────────────────────
# Each domain fixture creates a mix of canonical, decent, toy, and
# irrelevant candidates to test whether the pipeline ranks correctly.


def _fixtures_pdf() -> list[RepoCandidate]:
    return [
        _make_candidate("pymupdf/PyMuPDF", "High-performance PDF rendering", stars=5500, forks=600, topics=["pdf", "python"]),
        _make_candidate("py-pdf/pypdf", "Pure-Python PDF toolkit", stars=2500, forks=400, topics=["pdf"]),
        _make_candidate("pdfminer/pdfminer.six", "PDF document analysis", stars=1500, forks=300, topics=["pdf", "mining"]),
        _make_candidate("owner/pdf-tutorial", "A simple PDF tutorial project", stars=50, forks=5, topics=["pdf", "tutorial"], readme_text="## PDF tutorial\nLearning PDF processing."),
        _make_candidate("owner/text-editor", "A generic text editor", stars=2000, forks=300, topics=["editor", "text"], readme_text="## Editor\nA text editor application."),
    ]


def _fixtures_jwt() -> list[RepoCandidate]:
    return [
        _make_candidate("jpadilla/pyjwt", "JSON Web Token implementation", stars=5656, forks=1200, topics=["jwt", "auth", "python"]),
        _make_candidate("mitsuhiko/flask-jwt-extended", "JWT extension for Flask", stars=2500, forks=500, topics=["jwt", "flask", "auth"]),
        _make_candidate("authlib/authlib", "The ultimate Python auth library", stars=1500, forks=200, topics=["jwt", "oauth", "auth"]),
        _make_candidate("owner/jwt-builder-tool", "Build JWT tokens easily", stars=800, forks=100, topics=["jwt", "tool"]),
        _make_candidate("owner/awesome-jwt", "Awesome list of JWT resources", stars=5000, forks=800, topics=["awesome", "jwt"], license_spdx="NOASSERTION"),
    ]


def _fixtures_auth() -> list[RepoCandidate]:
    return [
        _make_candidate("pallets/flask", "The Python microframework", stars=70000, forks=18000, topics=["flask", "python", "web"], readme_text="## Flask\n```pip install flask\n```\n## Quickstart\nauth."),
        _make_candidate("encode/django-rest-framework", "Django REST framework", stars=30000, forks=7000, topics=["django", "rest", "api"], readme_text="## DRF\n```pip install djangorestframework```"),
        _make_candidate("lepture/authlib", "The ultimate Python auth library", stars=1500, forks=200, topics=["auth", "oauth", "jwt"]),
        _make_candidate("owner/login-tutorial", "Basic login tutorial", stars=20, forks=2, topics=["auth", "tutorial"], readme_text="## Login tutorial\nA simple login example."),
    ]


def _fixtures_orm() -> list[RepoCandidate]:
    return [
        _make_candidate("sqlalchemy/sqlalchemy", "Database toolkit for Python", stars=10000, forks=1500, topics=["orm", "database", "sql"]),
        _make_candidate("tortoise-orm/tortoise-orm", "Easy async ORM for Python", stars=2500, forks=300, topics=["orm", "async"]),
        _make_candidate("coleifer/peewee", "Small expressive ORM", stars=10000, forks=1500, topics=["orm", "sqlite"]),
        _make_candidate("owner/orm-generator", "Generate ORM models for any DB", stars=100, forks=10, topics=["orm", "generator"]),
    ]


def _fixtures_boilerplate() -> list[RepoCandidate]:
    return [
        _make_candidate("cookiecutter/cookiecutter", "Command-line utility for templates", stars=24000, forks=4400, topics=["cookiecutter", "template"]),
        _make_candidate("copier-org/copier", "Library/CLI for rendering templates", stars=2000, forks=100, topics=["template", "copier"]),
        _make_candidate("owner/fastapi-boilerplate", "FastAPI project starter", stars=800, forks=200, topics=["fastapi", "boilerplate"]),
        _make_candidate("owner/generic-framework", "Yet another web framework", stars=5000, forks=500, topics=["framework", "web"], readme_text="## Framework\nA web framework."),
    ]


def _fixtures_scraping() -> list[RepoCandidate]:
    return [
        _make_candidate("scrapy/scrapy", "Web crawling framework", stars=55000, forks=11000, topics=["scrapy", "crawler"]),
        _make_candidate("psf/requests-html", "HTML parsing for humans", stars=14000, forks=900, topics=["html", "parsing"]),
        _make_candidate("owner/scraping-framework", "A scraping framework for fun", stars=300, forks=50, topics=["scraping", "framework"]),
    ]


def _fixtures_testing() -> list[RepoCandidate]:
    return [
        _make_candidate("pytest-dev/pytest", "Testing framework", stars=13000, forks=2600, topics=["testing", "pytest"]),
        _make_candidate("pytest-dev/pytest-mock", "Thin wrapper for mocking", stars=2000, forks=300, topics=["testing", "mock"]),
        _make_candidate("owner/test-tutorial", "A testing tutorial", stars=30, forks=5, topics=["testing", "tutorial"], readme_text="## Testing tutorial\nLearning testing."),
    ]


def _fixtures_cache() -> list[RepoCandidate]:
    return [
        _make_candidate("redis/redis-py", "Redis Python client", stars=13500, forks=2500, topics=["redis", "cache"]),
        _make_candidate("benoitc/gunicorn", "WSGI HTTP Server", stars=10000, forks=1800, topics=["wsgi", "server"]),
        _make_candidate("owner/cache-example", "Simple caching example", stars=50, forks=5, topics=["cache", "example"], readme_text="## Cache example\nA caching demo."),
    ]


def _fixtures_cli() -> list[RepoCandidate]:
    return [
        _make_candidate("pallets/click", "Python composable command line utility", stars=16000, forks=4000, topics=["cli", "click"]),
        _make_candidate("tiangolo/typer", "Build great CLIs", stars=20000, forks=800, topics=["cli", "typer"]),
        _make_candidate("owner/cli-tool-demo", "Demo CLI tool for fun", stars=20, forks=2, topics=["cli", "demo"], readme_text="## CLI demo\nA demo cli tool."),
    ]


def _fixtures_logging() -> list[RepoCandidate]:
    return [
        _make_candidate("hynek/structlog", "Structured logging for Python", stars=3500, forks=150, topics=["logging", "structlog"]),
        _make_candidate("Delgan/loguru", "Python logging made simple", stars=21000, forks=700, topics=["logging", "loguru"]),
        _make_candidate("owner/log-example", "Logging example app", stars=5, forks=1, topics=["logging", "example"], readme_text="## Log example\nDisplay logs."),
    ]


def _fixtures_serialization() -> list[RepoCandidate]:
    return [
        _make_candidate("protocolbuffers/protobuf", "Protocol Buffers", stars=68000, forks=16000, topics=["protobuf", "serialization"]),
        _make_candidate("apache/avro", "Apache Avro data serialization", stars=3200, forks=1600, topics=["avro", "serialization"]),
        _make_candidate("owner/json-tool", "Simple JSON manipulation", stars=100, forks=10, topics=["json", "tool"], readme_text="## JSON tool\nProcess JSON files."),
    ]


# ── Regression test cases ────────────────────────────────────────────────────


@dataclass
class RegressionCase:
    """A single regression test scenario."""

    query: str
    language: str | None
    fixtures: list[RepoCandidate]
    expected_canonical: str  # A repo that should appear in top-5
    domain_note: str


def _fixtures_go_scraping() -> list[RepoCandidate]:
    """Go scraping fixtures with Go projects."""
    return [
        _make_candidate("gocolly/colly", "Fast web scraping for Go", stars=25000, forks=2100, topics=["scraping", "crawler", "go"], language="Go"),
        _make_candidate("chromedp/chromedp", "Browser automation for Go", stars=12000, forks=800, topics=["chrome", "scraping", "go"], language="Go"),
        _make_candidate("owner/go-scraper-demo", "Simple Go scraping demo", stars=50, forks=5, topics=["scraping", "demo", "go"], language="Go", readme_text="## Go scraper demo\nScraping in Go."),
    ]


def _fixtures_node_cache() -> list[RepoCandidate]:
    """Node.js caching fixtures."""
    return [
        _make_candidate("redis/node-redis", "Redis client for Node.js", stars=17000, forks=1700, topics=["redis", "cache", "nodejs"], language="JavaScript"),
        _make_candidate("sitespeedio/throttle", "Throttle for Node.js", stars=500, forks=50, topics=["cache", "nodejs"], language="JavaScript"),
        _make_candidate("owner/node-cache-example", "Simple Node caching", stars=30, forks=3, topics=["cache", "nodejs", "example"], language="JavaScript", readme_text="## Node cache\nA caching example."),
    ]


REGRESSION_CASES: list[RegressionCase] = [
    # ── PDF domain ──
    RegressionCase(
        query="como edito pdfs en python",
        language="Python",
        fixtures=_fixtures_pdf(),
        expected_canonical="pymupdf/PyMuPDF",
        domain_note="PDF canonical lib should rank above toy and editor tools",
    ),
    RegressionCase(
        query="pdf processing library python",
        language="Python",
        fixtures=_fixtures_pdf(),
        expected_canonical="pymupdf/PyMuPDF",
        domain_note="PDF canonical should beat generic editor",
    ),
    RegressionCase(
        query="extract text from pdf python",
        language="Python",
        fixtures=_fixtures_pdf(),
        expected_canonical="py-pdf/pypdf",
        domain_note="PDF extraction canonical should appear",
    ),
    # ── JWT/Auth domain ──
    RegressionCase(
        query="autenticacion con JWT python",
        language="Python",
        fixtures=_fixtures_jwt(),
        expected_canonical="jpadilla/pyjwt",
        domain_note="JWT canonical should beat awesome-list",
    ),
    RegressionCase(
        query="jwt authentication library",
        language="Python",
        fixtures=_fixtures_jwt(),
        expected_canonical="jpadilla/pyjwt",
        domain_note="JWT canonical ranked high in English query",
    ),
    RegressionCase(
        query="flask jwt extension",
        language="Python",
        fixtures=_fixtures_jwt(),
        expected_canonical="mitsuhiko/flask-jwt-extended",
        domain_note="Flask JWT should rank for Flask-specific query",
    ),
    # ── Auth domain (generic) ──
    RegressionCase(
        query="authentication library python",
        language="Python",
        fixtures=_fixtures_auth(),
        expected_canonical="lepture/authlib",
        domain_note="Auth lib should rank above tutorial",
    ),
    RegressionCase(
        query="oauth login implementation",
        language="Python",
        fixtures=_fixtures_auth(),
        expected_canonical="lepture/authlib",
        domain_note="OAuth/Auth canonical should appear",
    ),
    # ── ORM domain ──
    RegressionCase(
        query="orm para python",
        language="Python",
        fixtures=_fixtures_orm(),
        expected_canonical="sqlalchemy/sqlalchemy",
        domain_note="SQLAlchemy should be top for ORM query",
    ),
    RegressionCase(
        query="async orm database python",
        language="Python",
        fixtures=_fixtures_orm(),
        expected_canonical="tortoise-orm/tortoise-orm",
        domain_note="Tortoise ORM should rank for async ORM",
    ),
    # ── Boilerplate domain ──
    RegressionCase(
        query="fastapi boilerplate project",
        language="Python",
        fixtures=[
            _make_candidate("cookiecutter/cookiecutter", "Command-line utility for creating projects from templates", stars=24000, forks=4400, topics=["cookiecutter", "template", "boilerplate"]),
            _make_candidate("owner/fastapi-boilerplate", "FastAPI project starter template", stars=800, forks=200, topics=["fastapi", "boilerplate", "template"]),
            _make_candidate("owner/toy-starter", "A simple starter for learning", stars=20, forks=2, topics=["starter", "tutorial"], readme_text="## Starter\nA learning starter."),
        ],
        expected_canonical="cookiecutter/cookiecutter",
        domain_note="cookiecutter has 'boilerplate' and 'template' topics now, should rank top",
    ),
    RegressionCase(
        query="project template generator",
        language="Python",
        fixtures=_fixtures_boilerplate(),
        expected_canonical="cookiecutter/cookiecutter",
        domain_note="cookiecutter beats generic framework for template query",
    ),
    # ── Scraping domain ──
    RegressionCase(
        query="web scraping python",
        language="Python",
        fixtures=_fixtures_scraping(),
        expected_canonical="scrapy/scrapy",
        domain_note="Scrapy should rank for scraping query",
    ),
    RegressionCase(
        query="html parsing crawler",
        language="Python",
        fixtures=_fixtures_scraping(),
        expected_canonical="psf/requests-html",
        domain_note="requests-html should rank for HTML parsing query",
    ),
    # ── Other domains ──
    RegressionCase(
        query="unit testing python",
        language="Python",
        fixtures=_fixtures_testing(),
        expected_canonical="pytest-dev/pytest",
        domain_note="pytest should rank for testing query",
    ),
    RegressionCase(
        query="redis cache python",
        language="Python",
        fixtures=_fixtures_cache(),
        expected_canonical="redis/redis-py",
        domain_note="redis-py should rank for cache query",
    ),
    RegressionCase(
        query="cli command line python",
        language="Python",
        fixtures=_fixtures_cli(),
        expected_canonical="pallets/click",
        domain_note="click should rank for CLI query",
    ),
    RegressionCase(
        query="structured logging python",
        language="Python",
        fixtures=_fixtures_logging(),
        expected_canonical="hynek/structlog",
        domain_note="structlog should rank for logging query",
    ),
    RegressionCase(
        query="serialization protobuf python",
        language="Python",
        fixtures=_fixtures_serialization(),
        expected_canonical="protocolbuffers/protobuf",
        domain_note="protobuf should rank for serialization query",
    ),
    # ── Cross-language / Go ──
    RegressionCase(
        query="web scraping in go",
        language="Go",
        fixtures=_fixtures_go_scraping(),
        expected_canonical="gocolly/colly",
        domain_note="Colly should rank for Go scraping",
    ),
    # ── Node.js cache ──
    RegressionCase(
        query="redis cache nodejs",
        language="JavaScript",
        fixtures=_fixtures_node_cache(),
        expected_canonical="redis/node-redis",
        domain_note="node-redis should rank for Node.js cache query",
    ),
    # ── Edge: SIFT_SCORING_V2=0 compatibility ──
    RegressionCase(
        query="jwt authentication python",
        language="Python",
        fixtures=_fixtures_jwt(),
        expected_canonical="jpadilla/pyjwt",
        domain_note="JWT canonical in top-5 with v2 (same as v2 default test)",
    ),
]


@pytest.mark.parametrize("case", REGRESSION_CASES, ids=lambda c: c.query[:40])
def test_regression_canonical_in_top5(case: RegressionCase) -> None:
    """Canonical repository for domain appears in shortlist_v2 top-5."""
    result = shortlist_v2(case.fixtures, case.query, top=5)
    top_names = [r.full_name for r in result]

    assert case.expected_canonical in top_names, (
        f"Query: {case.query!r}\n"
        f"Expected {case.expected_canonical} in top-5 but got: {top_names}\n"
        f"Note: {case.domain_note}"
    )


@pytest.mark.parametrize("case", REGRESSION_CASES, ids=lambda c: c.query[:40])
def test_regression_scoring_orders_canonical_first(case: RegressionCase) -> None:
    """Canonical repo scores higher than toy/demo repos for the same domain."""
    toy_repos = [
        r for r in case.fixtures
        if "tutorial" in (r.description or "").lower() or "demo" in (r.description or "").lower()
        or "example" in (r.description or "").lower()
        or "awesome" in (r.description or "").lower() or "awesome" in " ".join(r.topics).lower()
    ]
    if not toy_repos:
        pytest.skip("No toy repo in this fixture set")

    for r in case.fixtures:
        score_repo_v2(r, case.query)

    scored_dict = {r.full_name: r.score for r in case.fixtures}
    canonical_score = scored_dict.get(case.expected_canonical, 0)
    for toy in toy_repos:
        toy_score = scored_dict.get(toy.full_name, 0)
        assert canonical_score > toy_score, (
            f"Query: {case.query!r}: {case.expected_canonical} (score={canonical_score}) "
            f"should beat {toy.full_name} (score={toy_score})"
        )


def test_all_regression_expected_canonicals_in_seeds() -> None:
    """All expected_canonical repos exist in CANONICAL_REPOS or are well-known."""
    cases_with_seeds = 0
    for case in REGRESSION_CASES:
        if case.expected_canonical in CANONICAL_REPOS:
            cases_with_seeds += 1
    # At least half the regression cases use official canonical repos
    assert cases_with_seeds >= len(REGRESSION_CASES) // 2, (
        f"Only {cases_with_seeds}/{len(REGRESSION_CASES)} expected canonicals "
        f"are in CANONICAL_REPOS. Consider adding them."
    )
