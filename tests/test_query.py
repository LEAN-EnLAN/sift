from sift.query import LANGUAGE_KEYWORDS, SPEED_KEYWORDS, build_search_queries, detect_language, detect_speed, extract_keywords, has_speed_hint


def test_spanish_query_expands_to_english_auth_terms() -> None:
    keywords = extract_keywords("autenticación con JWT")

    assert "jwt" in keywords
    assert "authentication" in keywords
    assert "auth" in keywords
    assert "login" in keywords
    assert "con" not in keywords


def test_build_search_queries_adds_language_and_default_safety_qualifiers() -> None:
    queries = build_search_queries("boilerplate de FastAPI", "Python", min_stars=100, pushed_after="2024-01-01", license_filter="mit")

    assert queries
    assert all("language:Python" in query for query in queries)
    assert all("fork:false" in query for query in queries)
    assert all("archived:false" in query for query in queries)
    assert all("stars:>=100" in query for query in queries)
    assert all("pushed:>=2024-01-01" in query for query in queries)
    assert all("license:mit" in query for query in queries)
    assert any("fastapi" in query.lower() for query in queries)


def test_build_search_queries_respects_max_variants() -> None:
    queries = build_search_queries("autenticación con JWT", "Python", max_variants=3)
    assert len(queries) <= 3


def test_build_search_queries_can_include_forks_and_archived() -> None:
    queries = build_search_queries("procesar PDFs", "Python", include_forks=True, include_archived=True)

    assert all("fork:false" not in query for query in queries)
    assert all("archived:false" not in query for query in queries)
    assert any("pdf" in query.lower() for query in queries)


# ─── NLP Detection Tests (Phase 1: detect_language / detect_speed) ───


class TestLanguageKeywords:
    """Verify LANGUAGE_KEYWORDS dict structure."""

    def test_language_keywords_has_known_languages(self) -> None:
        assert LANGUAGE_KEYWORDS["python"] == "Python"
        assert LANGUAGE_KEYWORDS["javascript"] == "JavaScript"
        assert LANGUAGE_KEYWORDS["typescript"] == "TypeScript"
        assert LANGUAGE_KEYWORDS["go"] == "Go"
        assert LANGUAGE_KEYWORDS["rust"] == "Rust"

    def test_language_keywords_has_aliases(self) -> None:
        assert LANGUAGE_KEYWORDS["py"] == "Python"
        assert LANGUAGE_KEYWORDS["js"] == "JavaScript"
        assert LANGUAGE_KEYWORDS["ts"] == "TypeScript"
        assert LANGUAGE_KEYWORDS["golang"] == "Go"
        assert LANGUAGE_KEYWORDS["cpp"] == "C++"
        assert LANGUAGE_KEYWORDS["csharp"] == "C#"

    def test_language_keywords_all_values_are_strings(self) -> None:
        for alias, lang in LANGUAGE_KEYWORDS.items():
            assert isinstance(alias, str), f"Alias {alias!r} is not str"
            assert isinstance(lang, str), f"Value for {alias!r} is not str"


class TestSpeedKeywords:
    """Verify SPEED_KEYWORDS dict structure."""

    def test_speed_keywords_has_known_terms(self) -> None:
        assert SPEED_KEYWORDS["fast"] == "fast"
        assert SPEED_KEYWORDS["balanced"] == "balanced"
        assert SPEED_KEYWORDS["thorough"] == "thorough"

    def test_speed_keywords_has_spanish_aliases(self) -> None:
        assert SPEED_KEYWORDS["rápido"] == "fast"
        assert SPEED_KEYWORDS["rapido"] == "fast"
        assert SPEED_KEYWORDS["completo"] == "thorough"
        assert SPEED_KEYWORDS["detallado"] == "thorough"
        assert SPEED_KEYWORDS["moderado"] == "balanced"


class TestDetectLanguage:
    """RED: Test detect_language() before it exists in query.py."""

    def test_detect_language_with_explicit_name(self) -> None:
        result = detect_language("necesito un ORM para Python")
        assert result == ["Python"]

    def test_detect_language_with_framework(self) -> None:
        result = detect_language("autenticación JWT con FastAPI")
        assert result == ["Python"]

    def test_detect_language_multiple_languages(self) -> None:
        result = detect_language("FastAPI con React y TypeScript")
        assert set(result) == {"Python", "TypeScript"}

    def test_detect_language_no_match_returns_empty_list(self) -> None:
        result = detect_language("necesito un ORM que funcione bien")
        assert result == []

    def test_detect_language_spanish_input(self) -> None:
        result = detect_language("framework para microservicios en python")
        assert result == ["Python"]

    def test_detect_language_dedup(self) -> None:
        """Multiple mentions of same language return single entry."""
        result = detect_language("python flask y python django")
        assert result == ["Python"]

    def test_detect_language_go_not_confused(self) -> None:
        """'go' as a word should match Go language."""
        result = detect_language("scraping en Go")
        assert result == ["Go"]

    def test_detect_language_using_alias(self) -> None:
        result = detect_language("api en js con node")
        assert "JavaScript" in result

    def test_detect_language_fallback_for_unknown_language_hint(self) -> None:
        result = detect_language("cliente mcp en zig")
        assert result == ["Zig"]


class TestDetectSpeed:
    """RED: Test detect_speed() before it exists in query.py."""

    def test_detect_speed_fast_english(self) -> None:
        result = detect_speed("búsqueda rápida de JWT")
        assert result == "fast"

    def test_detect_speed_thorough_spanish(self) -> None:
        result = detect_speed("análisis exhaustivo de ORMs")
        assert result == "thorough"

    def test_detect_speed_default_balanced(self) -> None:
        result = detect_speed("autenticación JWT")
        assert result == "balanced"

    def test_detect_speed_rapido_spanish(self) -> None:
        result = detect_speed("búsqueda rapido")
        assert result == "fast"

    def test_detect_speed_detallado(self) -> None:
        result = detect_speed("busqueda detallada")
        assert result == "thorough"

    def test_detect_speed_completo(self) -> None:
        result = detect_speed("análisis completo de librerías")
        assert result == "thorough"

    def test_detect_speed_quick(self) -> None:
        result = detect_speed("quick search python")
        assert result == "fast"

    def test_detect_speed_normal_maps_to_balanced(self) -> None:
        result = detect_speed("velocidad normal")
        assert result == "balanced"


class TestSpeedHints:
    def test_has_speed_hint_true_for_rapido(self) -> None:
        assert has_speed_hint("quiero algo rapido") is True

    def test_has_speed_hint_false_when_not_present(self) -> None:
        assert has_speed_hint("autenticacion jwt en python") is False
