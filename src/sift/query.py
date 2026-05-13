from __future__ import annotations

import re
from urllib.parse import quote_plus

SPANISH_TO_ENGLISH = {
    "autenticacion": ["authentication", "auth", "login"],
    "autenticación": ["authentication", "auth", "login"],
    "jwt": ["jwt", "json web token"],
    "token": ["token"],
    "pdf": ["pdf"],
    "pdfs": ["pdf"],
    "procesar": ["processing", "parse", "extract"],
    "procesamiento": ["processing", "parser", "extract"],
    "extraer": ["extract", "parser"],
    "boilerplate": ["boilerplate", "starter", "template"],
    "plantilla": ["template", "starter", "boilerplate"],
    "api": ["api", "rest"],
    "rest": ["rest"],
    "graphql": ["graphql"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "node": ["node", "nodejs"],
    "nodejs": ["node", "nodejs"],
    "express": ["express"],
    "nestjs": ["nestjs"],
    "react": ["react"],
    "vue": ["vue"],
    "angular": ["angular"],
    "scraping": ["scraping", "crawler"],
    "testing": ["testing", "test"],
    "tests": ["testing", "test"],
    "cache": ["cache", "caching"],
    "colas": ["queue", "worker", "background jobs"],
    "mensajeria": ["messaging", "queue"],
    "mensajería": ["messaging", "queue"],
    "microservicios": ["microservices", "microservice"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
}

STOPWORDS = {
    "a", "al", "con", "como", "cómo", "de", "del", "el", "en", "hay", "hacer", "hago",
    "la", "las", "lo", "los", "para", "por", "que", "qué", "un", "una", "uso", "usar",
    "libreria", "librería", "decente", "necesito", "quiero", "busco", "similar", "sobre",
}

LANGUAGE_KEYWORDS: dict[str, str] = {
    "python": "Python",
    "py": "Python",
    "python3": "Python",
    "fastapi": "Python",
    "django": "Python",
    "flask": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "node": "JavaScript",
    "nodejs": "JavaScript",
    "express": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "nestjs": "TypeScript",
    "react": "TypeScript",
    "vue": "TypeScript",
    "angular": "TypeScript",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "java": "Java",
    "ruby": "Ruby",
    "rails": "Ruby",
    "php": "PHP",
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "shell": "Shell",
    "bash": "Shell",
    "sql": "SQL",
}

SPEED_KEYWORDS: dict[str, str] = {
    "fast": "fast",
    "rapido": "fast",
    "rápido": "fast",
    "rápida": "fast",
    "rapida": "fast",
    "quick": "fast",
    "rapid": "fast",
    "balanced": "balanced",
    "normal": "balanced",
    "moderado": "balanced",
    "thorough": "thorough",
    "lento": "thorough",
    "lenta": "thorough",
    "completo": "thorough",
    "completa": "thorough",
    "detallado": "thorough",
    "detallada": "thorough",
    "detailed": "thorough",
    "exhaustivo": "thorough",
    "exhaustiva": "thorough",
}

_DOMAIN_TRIGGER_SETS: dict[str, set[str]] = {
    "pdf": {"pdf", "pdfs"},
    "jwt-auth": {"jwt", "json web token", "token"},
    "auth": {"auth", "authentication", "login", "sso", "oauth"},
    "orm": {"orm"},
    "boilerplate": {"boilerplate", "template", "starter", "scaffold"},
    "scraping": {"scraping", "crawler", "scrape"},
    "cli": {"cli", "command line"},
    "testing": {"testing", "test", "tests"},
    "cache": {"cache", "caching"},
    "logging": {"log", "logging", "logger"},
    "serialization": {"serialize", "serialization", "deserialize"},
}

LANGUAGE_HINT_PREFIXES = {"en", "in", "with", "using", "para"}
NON_LANGUAGE_FALLBACK_TOKENS = {
    *STOPWORDS,
    *SPEED_KEYWORDS.keys(),
    "jwt",
    "auth",
    "authentication",
    "login",
    "oauth",
    "ocr",
    "orm",
    "api",
    "rest",
    "graphql",
    "backend",
    "frontend",
    "server",
    "cli",
    "sdk",
    "library",
    "framework",
}


def _normalize_token(token: str) -> str:
    return token.lower().strip("_-./,;:()[]{}'\"")


def _tokenize(text: str) -> list[str]:
    """Split text into normalized tokens."""
    return [_normalize_token(t) for t in re.split(r"\s+", text) if t.strip()]


def detect_language(natural_query: str) -> list[str]:
    """Detect programming languages from natural language query.

    Scans each token against LANGUAGE_KEYWORDS.
    Returns a deduplicated sorted list of language names.
    Returns empty list if nothing detected (caller handles fallback).
    """
    detected: set[str] = set()
    tokens = _tokenize(natural_query)
    for token in tokens:
        lang = LANGUAGE_KEYWORDS.get(token)
        if lang is not None:
            detected.add(lang)
    if detected:
        return sorted(detected)

    for index, token in enumerate(tokens[:-1]):
        if token not in LANGUAGE_HINT_PREFIXES:
            continue
        candidate = tokens[index + 1]
        if (
            not candidate
            or candidate in NON_LANGUAGE_FALLBACK_TOKENS
            or candidate.isdigit()
            or len(candidate) < 2
        ):
            continue
        detected.add(_format_fallback_language(candidate))
    return sorted(detected)


def detect_speed(natural_query: str) -> str:
    """Detect speed preference from natural language query.

    Scans each token against SPEED_KEYWORDS.
    Returns "fast", "balanced", or "thorough".
    Defaults to "balanced" if nothing detected.
    """
    for token in _tokenize(natural_query):
        speed = SPEED_KEYWORDS.get(token)
        if speed is not None:
            return speed
    return "balanced"


def has_speed_hint(natural_query: str) -> bool:
    """Return True when the input explicitly mentions a speed preference."""
    return any(token in SPEED_KEYWORDS for token in _tokenize(natural_query))


def _format_fallback_language(token: str) -> str:
    if token in {"c++", "cpp"}:
        return "C++"
    if token in {"c#", "csharp"}:
        return "C#"
    if token in {"f#", "fsharp"}:
        return "F#"
    if token in {"sql", "php"}:
        return token.upper()
    return token[:1].upper() + token[1:]


def extract_keywords(natural_query: str) -> list[str]:
    """Extrae keywords técnicas y agrega equivalentes en inglés para mejorar GitHub Search.

    GitHub tiene mucha documentación en inglés; si el input viene en español, buscar sólo
    términos literales suele perder resultados buenos. Esta función no intenta ser NLP
    perfecto: mantiene términos técnicos, elimina stopwords y expande un vocabulario chico.
    """
    tokens = [_normalize_token(t) for t in re.split(r"\s+", natural_query) if t.strip()]
    keywords: list[str] = []
    original_set = set(tokens)
    for token in tokens:
        if not token or token in STOPWORDS:
            continue
        expansions = SPANISH_TO_ENGLISH.get(token, [token])
        for item in expansions:
            if item not in keywords:
                keywords.append(item)

    # Promovemos términos técnicos escritos literalmente por el usuario (JWT, PDF, FastAPI).
    # Los sinónimos genéricos como auth/login ayudan al recall, pero no deberían desplazar
    # el concepto central de la búsqueda.
    def priority(term: str) -> tuple[int, int]:
        normalized = term.lower().replace("s", "") if term.lower().endswith("s") else term.lower()
        literal = term.lower() in original_set or normalized in original_set
        technical = bool(re.search(r"[0-9]", term)) or term.lower() in {
            "jwt", "pdf", "fastapi", "django", "flask", "express", "nestjs",
            "react", "vue", "angular", "docker", "kubernetes", "k8s", "graphql",
        }
        return (0 if (literal or technical) else 1, -len(term))

    keywords.sort(key=priority)
    return keywords[:10]


def classify_domain(keywords: list[str]) -> str | None:
    """Classify a list of keywords into a domain tag.

    Counts how many keywords match each domain's trigger set.
    The domain with the most matches wins. Ties between jwt-auth
    and auth are resolved in favor of jwt-auth (more specific).

    Args:
        keywords: Extracted keyword strings from the user's query.

    Returns:
        Domain string (e.g., 'pdf', 'jwt-auth', 'auth') or None if no match.
    """
    counts: dict[str, int] = {}
    for kw in keywords:
        kw_l = kw.lower().strip()
        for domain, triggers in _DOMAIN_TRIGGER_SETS.items():
            if kw_l in triggers:
                counts[domain] = counts.get(domain, 0) + 1
    if not counts:
        return None
    max_count = max(counts.values())
    tied = [d for d, c in counts.items() if c == max_count]
    if "jwt-auth" in tied and "auth" in tied:
        return "jwt-auth"
    return tied[0]


def _apply_lexical_traps(domain: str | None, keywords: list[str]) -> list[str]:
    """Filter out keywords that match lexical traps for the given domain.

    Lexical traps are terms that indicate generic/toy projects
    rather than serious libraries (e.g., 'editor' for PDF domain).

    Args:
        domain: The inferred domain tag or None.
        keywords: List of keyword strings to filter.

    Returns:
        Filtered keyword list with trap terms removed.
    """
    if domain is None:
        return keywords[:]

    from .scoring.seeds import LEXICAL_TRAPS  # noqa: late import avoids cycles

    if domain not in LEXICAL_TRAPS:
        return keywords[:]
    traps = LEXICAL_TRAPS[domain]
    return [kw for kw in keywords if kw.lower().strip() not in traps]


def _inject_seeds(domain: str | None) -> list[str]:
    """Get domain seed repository names for the given domain.

    Args:
        domain: The inferred domain tag or None.

    Returns:
        List of seed repo names (e.g., ['pymupdf', 'pypdf']).
        Empty list if domain is None or unknown.
    """
    if domain is None:
        return []

    from .scoring.seeds import DOMAIN_SEEDS  # noqa: late import avoids cycles

    if domain not in DOMAIN_SEEDS:
        return []
    return list(DOMAIN_SEEDS[domain])


def build_search_queries(
    natural_query: str,
    language: str | None,
    *,
    min_stars: int = 0,
    pushed_after: str | None = None,
    license_filter: str | None = None,
    include_forks: bool = False,
    include_archived: bool = False,
    max_variants: int = 8,
) -> list[str]:
    """Construye hasta 5 variantes de búsqueda usando clasificación por dominio.

    En lugar de generar muchas variantes genéricas, clasificamos la intención del
    query (PDF, JWT, etc.), inyectamos seeds de ecosistemas conocidos y evitamos
    términos trampa que traen ruido (ej: "editor" en dominio PDF).

    La API de GitHub trata los términos libres como AND. Generamos variantes
    pequeñas y después re-rankeamos localmente.
    """
    keywords = extract_keywords(natural_query)
    if not keywords:
        keywords = [natural_query.strip()]

    domain = classify_domain(keywords)
    clean_kw = _apply_lexical_traps(domain, keywords)
    seeds = _inject_seeds(domain)

    qualifiers: list[str] = []
    if language:
        qualifiers.append(f"language:{language}")
    if not include_forks:
        qualifiers.append("fork:false")
    if not include_archived:
        qualifiers.append("archived:false")
    if min_stars > 0:
        qualifiers.append(f"stars:>={min_stars}")
    if pushed_after:
        qualifiers.append(f"pushed:>={pushed_after}")
    if license_filter:
        qualifiers.append(f"license:{license_filter}")

    base = " ".join(qualifiers)
    variants: list[str] = []

    # 1. Seed-forward: inject domain seeds for known libraries.
    if seeds:
        seed_terms = " ".join(seeds[:3])
        variants.append(f"{seed_terms} {base}")
        variants.append(f"{seed_terms} in:name,description,readme {base}")

    # 2. Domain-in-field: use the domain term with in qualifier.
    if domain:
        domain_term = domain.replace("-auth", " auth").replace("-", " ")
        variants.append(f"{domain_term} in:name,description,readme {base}")

    # 3. Keyword-broad: prefer a non-domain keyword (e.g. a tech/library name).
    domain_triggers = _DOMAIN_TRIGGER_SETS.get(domain, set()) if domain else set()
    non_domain_kw = [kw for kw in clean_kw if kw.lower().strip() not in domain_triggers]
    if non_domain_kw:
        variants.append(f"{non_domain_kw[0]} {base}")
    elif clean_kw:
        variants.append(f"{clean_kw[0]} {base}")

    # 4. Topic-targeted: use domain as a GitHub topic.
    if domain:
        safe_topic = re.sub(r"[^a-zA-Z0-9-]", "", domain)
        if safe_topic:
            variants.append(f"topic:{safe_topic} {base}")

    # 5. Fallback: if very few variants, add original keywords.
    if len(variants) < 2:
        for kw in keywords[:2]:
            variants.append(f"{kw} {base}")

    # Deduplicar preservando orden.
    seen: set[str] = set()
    unique: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique.append(v)

    # Siempre al menos 1 variante.
    if not unique:
        fallback = keywords[0] if keywords else natural_query.strip()
        unique.append(f"{fallback} {base}")

    return unique[:max_variants]


def github_search_url(query: str, sort: str | None = None, per_page: int = 30) -> str:
    sort_part = f"&sort={quote_plus(sort)}" if sort else ""
    return f"/search/repositories?q={quote_plus(query)}{sort_part}&order=desc&per_page={per_page}"
