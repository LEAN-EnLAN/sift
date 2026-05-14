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

VECTOR_DB_TIEBREAKER_TOLERANCE = 0.4
JWT_AUTH_TIEBREAKER_TOLERANCE = 0.2
LOW_CONFIDENCE_SCORE_DELTA = 0.5
SINGLE_SOFT_HIT_PENALTY = 0.4

_DOMAIN_PROFILES: dict[str, dict[str, set[str]]] = {
    "pdf": {"strict": {"pdf", "pdfs"}, "soft": set(), "negative": set()},
    "jwt-auth": {"strict": {"jwt", "json web token"}, "soft": {"token", "jws", "jwe"}, "negative": set()},
    "auth": {"strict": {"auth", "authentication", "login", "sso", "oauth"}, "soft": {"oidc", "signin"}, "negative": set()},
    "orm": {"strict": {"orm"}, "soft": {"sqlalchemy", "hibernate", "entity"}, "negative": set()},
    "boilerplate": {"strict": {"boilerplate", "template", "starter", "scaffold"}, "soft": set(), "negative": set()},
    "scraping": {"strict": {"scraping", "crawler", "scrape"}, "soft": {"spider"}, "negative": set()},
    "cli": {"strict": {"cli", "command line"}, "soft": {"terminal", "shell"}, "negative": set()},
    "testing": {"strict": {"testing", "test", "tests"}, "soft": {"unit", "integration"}, "negative": set()},
    "cache": {"strict": {"cache", "caching"}, "soft": {"redis", "memcached"}, "negative": set()},
    "vector-db": {
        "strict": {"vector database", "vectordb", "vector-db", "ann", "qdrant", "weaviate", "milvus", "pinecone"},
        "soft": {"vector", "vectors", "embedding", "embeddings", "semantic search", "faiss", "pgvector", "lancedb"},
        "negative": {"svg", "vector graphics", "illustrator"},
    },
    "embedding": {
        "strict": {"embedding", "embeddings"},
        "soft": {"sentence transformer", "feature vector", "bert", "clip"},
        "negative": {"iframe", "embed html"},
    },
    "rag": {"strict": {"rag", "retrieval augmented generation"}, "soft": {"context retrieval", "knowledge base"}, "negative": set()},
    "mlops": {"strict": {"mlops"}, "soft": {"ml pipeline", "model serving", "feature store"}, "negative": set()},
    "ci-cd": {"strict": {"ci", "cd", "ci/cd", "jenkins", "github actions", "gitlab ci"}, "soft": {"pipeline", "build", "deploy"}, "negative": {"ml pipeline", "etl"}},
    "logging": {"strict": {"log", "logging", "logger"}, "soft": {"structured logging"}, "negative": set()},
    "serialization": {"strict": {"serialize", "serialization", "deserialize"}, "soft": {"protobuf", "avro", "msgpack"}, "negative": set()},
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


def _has_term(term: str, *, joined: str, token_set: set[str]) -> bool:
    term_n = _normalize_token(term)
    if " " in term_n:
        return term_n in joined
    return term_n in token_set


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
    scores: dict[str, float] = {}
    evidence: dict[str, tuple[int, int, int]] = {}
    joined = " ".join(keywords).lower()
    token_set = {_normalize_token(k) for k in keywords}

    for domain, profile in _DOMAIN_PROFILES.items():
        score = 0.0
        strict_hits = 0
        soft_hits = 0
        negative_hits = 0
        for term in profile["strict"]:
            if _has_term(term, joined=joined, token_set=token_set):
                score += 2.0
                strict_hits += 1
        for term in profile["soft"]:
            if _has_term(term, joined=joined, token_set=token_set):
                score += 1.0
                soft_hits += 1
        for term in profile["negative"]:
            if _has_term(term, joined=joined, token_set=token_set):
                score -= 1.5
                negative_hits += 1
        # Precision: single-soft-hit intents are allowed but penalized to avoid erratic jumps.
        if strict_hits == 0 and soft_hits == 1:
            score -= SINGLE_SOFT_HIT_PENALTY
        if strict_hits == 0 and soft_hits < 1:
            continue
        if score > 0 and negative_hits <= strict_hits + soft_hits:
            scores[domain] = score
            evidence[domain] = (strict_hits, soft_hits, negative_hits)
    if not scores:
        return None
    # Prefer domains with stronger evidence before raw score.
    ranked = sorted(
        scores,
        key=lambda d: (evidence[d][0], scores[d], evidence[d][1], -evidence[d][2]),
        reverse=True,
    )
    best = ranked[0]
    tied = [d for d in ranked if scores[d] == scores[best]]
    if "jwt-auth" in tied and "auth" in tied:
        return "jwt-auth"
    if "vector-db" in tied and "embedding" in tied:
        return "vector-db"
    if "vector-db" in scores and "embedding" in scores and scores["vector-db"] >= scores["embedding"] - VECTOR_DB_TIEBREAKER_TOLERANCE:
        return "vector-db"
    if "jwt-auth" in scores and "auth" in scores and scores["jwt-auth"] >= scores["auth"] - JWT_AUTH_TIEBREAKER_TOLERANCE:
        return "jwt-auth"
    # Low-confidence ambiguity guard.
    if len(ranked) > 1 and abs(scores[ranked[0]] - scores[ranked[1]]) < LOW_CONFIDENCE_SCORE_DELTA and evidence[ranked[0]][0] == 0:
        return None
    return best


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
    profile = _DOMAIN_PROFILES.get(domain, {}) if domain else {}
    domain_triggers = profile.get("strict", set()) | profile.get("soft", set())
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
