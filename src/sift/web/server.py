"""Web server core — Starlette app with port selection and lazy imports."""

from __future__ import annotations

import socket
from typing import Any

_DEFAULT_PORT = 5173


def find_available_port(preferred: int = _DEFAULT_PORT) -> int:
    """Return an available port, trying preferred first then falling back."""
    if _is_port_available(preferred):
        return preferred
    # Fall back to any available port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _is_port_available(port: int) -> bool:
    """Check if a port is available on 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def _check_web_dependencies() -> None:
    """Check that starlette and uvicorn are available."""
    missing = []
    try:
        import starlette  # noqa: F401
    except ImportError:
        missing.append("starlette")
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        missing.append("uvicorn")
    if missing:
        raise ImportError(
            f"Web dependencies not installed: {', '.join(missing)}. "
            f"Run: pip install sift[web]"
        )


def run_server(host: str = "127.0.0.1", port: int | None = None) -> tuple[str, int]:
    """Start the uvicorn server. Returns (url, actual_port).

    Binds to 127.0.0.1 only. If port is occupied, falls back to another port.
    This is a blocking call — run it in a background thread.
    """
    _check_web_dependencies()
    import uvicorn

    from .routes import create_app
    from ..persistence.history import SearchHistoryStore

    history_store = SearchHistoryStore()
    app = create_app(history_store)

    if port is None:
        port = find_available_port()

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    url = f"http://{host}:{port}"
    server.run()  # Blocking call — starts the event loop
    return url, port
