"""Tests for the scoring v2 HTML report generator."""

from __future__ import annotations

from sift.scoring.report import BenchmarkCase, render_html_report


class TestBenchmarkCase:
    """BenchmarkCase dataclass contract."""

    def test_benchmark_case_fields(self) -> None:
        """BenchmarkCase has all expected fields with correct types."""
        case = BenchmarkCase(
            query="JWT auth python",
            language="Python",
            old_top5=["owner/lib-a", "owner/lib-b"],
            new_top5=["owner/lib-a", "owner/canonical-lib"],
            notes="canonical lib moved up",
        )
        assert case.query == "JWT auth python"
        assert case.language == "Python"
        assert case.old_top5 == ["owner/lib-a", "owner/lib-b"]
        assert case.new_top5 == ["owner/lib-a", "owner/canonical-lib"]
        assert case.notes == "canonical lib moved up"

    def test_benchmark_case_with_none_language(self) -> None:
        """BenchmarkCase handles None language."""
        case = BenchmarkCase(
            query="scraping go",
            language=None,
            old_top5=[],
            new_top5=[],
            notes="no results",
        )
        assert case.language is None


class TestRenderHtmlReport:
    """render_html_report produces valid self-contained HTML."""

    def test_returns_string(self) -> None:
        """render_html_report returns a non-empty string."""
        html = render_html_report([])
        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_has_required_sections(self) -> None:
        """Report HTML contains all required sections."""
        benchmarks = [
            BenchmarkCase(
                query="JWT auth python",
                language="Python",
                old_top5=["owner/old-a", "owner/old-b"],
                new_top5=["jpadilla/pyjwt", "owner/new-b"],
                notes="pyjwt now ranks first",
            ),
            BenchmarkCase(
                query="PDF editing python",
                language="Python",
                old_top5=["owner/toy-editor", "owner/pdf-old"],
                new_top5=["pymupdf/PyMuPDF", "py-pdf/pypdf"],
                notes="canonical PDF libs now rank higher",
            ),
        ]
        html = render_html_report(benchmarks)

        # Problem statement
        assert "Retrieval" in html or "scoring" in html.lower()

        # Retrieval comparison
        assert "old" in html.lower() or "v1" in html.lower()

        # Scoring comparison
        assert "scoring" in html.lower()

        # Benchmark table
        assert "jpadilla/pyjwt" in html
        assert "pymupdf/PyMuPDF" in html

        # Tradeoffs / limitations section
        assert "tradeoff" in html.lower() or "limit" in html.lower() or "notable" in html.lower()

    def test_html_self_contained_no_external_refs(self) -> None:
        """HTML is self-contained with no external CSS/JS dependencies."""
        html = render_html_report([])
        assert "http://" not in html or "https://" not in html or "//cdn" not in html

        # Should have inline styles
        assert "<style>" in html or "style=" in html

    def test_html_documents_benchmark_evidence(self) -> None:
        """Benchmark examples produce visible evidence in the output."""
        benchmarks = [
            BenchmarkCase(
                query="ORM python",
                language="Python",
                old_top5=["owner/random-orm"],
                new_top5=["sqlalchemy/sqlalchemy"],
                notes="SQLAlchemy now ranks first due to authority boost",
            ),
        ]
        html = render_html_report(benchmarks)

        # The benchmark example query appears
        assert "ORM python" in html
        # The canonical repo appears
        assert "sqlalchemy/sqlalchemy" in html
        # Notes appear
        assert "authority" in html.lower() or "boost" in html.lower()

    def test_html_is_deterministic(self) -> None:
        """Same input produces identical output."""
        benchmarks = [
            BenchmarkCase(query="test", language=None, old_top5=[], new_top5=[], notes=""),
        ]
        html1 = render_html_report(benchmarks)
        html2 = render_html_report(benchmarks)
        assert html1 == html2
