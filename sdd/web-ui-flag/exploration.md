## Exploration: Web UI Flag

### Current State
`sift` is currently a CLI-first tool with two primary interactive modes: a Rich-based prompt loop and a full-screen Textual TUI. While it supports exporting results to JSON and Markdown, it lacks a persistent search history and a rich, multi-repo comparison view. A static landing page already exists in `landing-page/` which mocks the vision of a "Chromium-simulated" companion.

### Affected Areas
- `src/sift/cli.py` — Needs `--web` flag and orchestration to launch the local companion server.
- `src/sift/web/` (New) — Package to hold the server logic (FastAPI/Starlette) and frontend assets.
- `src/sift/persistence/` (New) — Shared logic for search history and session management (stored in `~/.cache/sift/history.json`).
- `pyproject.toml` — Potential new dependencies for the web server (e.g., `fastapi`, `uvicorn`).

### Approaches
1. **Sidecar Local Server (FastAPI/Starlette)**
   - **Description**: Launch a local web server on a random/fixed port (127.0.0.1) that serves a React/Vue/Vanilla SPA.
   - **Pros**: Enables real-time history, side-by-side comparison, and a richer UX than terminal buffers.
   - **Cons**: Adds runtime dependencies and complexity to the build/distribution.
   - **Effort**: High

2. **Static Interactive Export (Self-contained HTML)**
   - **Description**: `sift --web` generates a single HTML file with all search results and bundled JS for filtering/sorting, then opens it.
   - **Pros**: Zero dependencies, no long-running process, extremely portable.
   - **Cons**: Cannot easily support "History" across different runs without a central server or complex local storage hacks.
   - **Effort**: Medium

3. **Hybrid: Persistent API + Static Frontend**
   - **Description**: A minimal background service (started on demand) that provides a JSON API for history, while the UI is served from the local filesystem or a simple python `http.server`.
   - **Pros**: Decouples the UI from the tool; follows the "CLI-first" philosophy where the server is just another consumer.
   - **Cons**: Orchestration of two parts (API + UI) can be brittle.
   - **Effort**: High

### Recommendation
**Approach 1 (Sidecar Local Server)** is recommended. It directly fulfills the user intent for a "real web experience" and "persistence as a value prop." By using a lightweight async framework (like FastAPI), we can provide a robust API for the UI to consume history and trigger new searches, while keeping the "local-only" mission intact.

### Risks
- **Mission Fit**: The server MUST remain local-only (127.0.0.1) and should not introduce any cloud telemetry or external dependencies.
- **Dependency Bloat**: Adding a web framework increases the package size; we should opt for minimal alternatives if possible.
- **Port Conflicts**: Need a strategy for handling port 5173 (suggested in landing page) if already in use.

### Ready for Proposal
**Yes.** The architectural vision is clear, and the existing `landing-page` assets provide a strong starting point for the frontend design.

### Scope Note
- **In Scope**: `--web` flag, local history persistence (JSON), basic Dashboard (Search/History/Compare).
- **Deferred**: User accounts/auth (stay local), multi-user collaboration, advanced report generation (PDF/etc).
