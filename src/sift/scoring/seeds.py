"""Domain seed maps and lexical traps for scoring v2.

These are hardcoded, deterministic maps that guide query expansion
and ranking heuristics. No external I/O, no configuration files.
"""

DOMAIN_SEEDS: dict[str, list[str]] = {
    "pdf": ["pymupdf", "pypdf", "pikepdf", "borb", "reportlab", "pdfplumber"],
    "jwt-auth": ["pyjwt", "python-jose", "authlib", "jose"],
    "orm": ["sqlalchemy", "peewee", "pony", "tortoise-orm"],
    "boilerplate": ["cookiecutter", "copier", "yeoman"],
    "auth": ["passport", "devise", "omniauth", "next-auth", "auth.js", " Lucia"],
    "scraping": ["scrapy", "beautifulsoup", "playwright", "puppeteer", "selenium"],
    "cli": ["click", "typer", "argparse", "commander", "oclif"],
    "testing": ["pytest", "vitest", "jest", "mocha", "rspec", "junit"],
    "cache": ["redis", "memcached", "varnish", "cloudflare"],
    "logging": ["log4j", "logback", "winston", "pino", "structlog"],
    "serialization": ["protobuf", "avro", "msgpack", " pickle", "json"],
}

LEXICAL_TRAPS: dict[str, set[str]] = {
    "pdf": {"edit", "editor", "create", "make", "build"},
    "jwt-auth": {"build", "create", "make", "tool"},
    "orm": {"builder", "generator", "tool", "make"},
    "boilerplate": {"framework", "library", "sdk"},
    "scraping": {"framework", "platform"},
}

CANONICAL_REPOS: set[str] = {
    "pymupdf/PyMuPDF",
    "py-pdf/pypdf",
    "jpadilla/pyjwt",
    "mitsuhiko/flask-jwt-extended",
    "sqlalchemy/sqlalchemy",
    "cookiecutter/cookiecutter",
    "scrapy/scrapy",
    "pallets/click",
    "pytest-dev/pytest",
    "redis/redis-py",
    "Textualize/rich",
}
