# Tasks: web-ui-flag (Experimental Web Companion)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450-550 |
| 400-line budget risk | High |
| Chained PRs recommended | No (single-pr strategy) |
| Suggested split | Single PR with size:exception |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full web companion feature | PR 1 | size:exception required; all phases below in single PR |

> **Size note**: This change likely exceeds 400 changed lines (persistence layer, web server, routes, static assets, CLI wiring, tests). Under `single-pr` strategy, a `size:exception` must be acknowledged by the maintainer before apply begins.

## Phase 1: Foundation — Persistence Layer

- [x] 1.1 Create `src/sift/persistence/__init__.py` — empty package init
- [x] 1.2 Create `src/sift/persistence/history.py` — `SearchHistoryStore` class: `add_entry(query, languages, results)`, `get_entries(limit)`, `clear()`, backed by `~/.cache/sift/history.json`; atomic write via temp+rename; max 100 entries with FIFO eviction
- [x] 1.3 Create `tests/test_persistence.py` — unit tests: add+retrieve roundtrip, FIFO eviction at 100, clear, corrupt JSON recovery, atomic write (no partial file on crash)

## Phase 2: Web Server Core

- [x] 2.1 Create `src/sift/web/__init__.py` — empty package init
- [x] 2.2 Create `src/sift/web/server.py` — `create_app(history_store)` returning a Starlette `Application`; mount static files from `src/sift/web/static/`; bind to `127.0.0.1` only; port selection: try default, fall back to random available
- [x] 2.3 Create `src/sift/web/routes.py` — API routes: `GET /api/history` (JSON), `POST /api/search` (trigger search, return results), `GET /api/health`; all JSON responses
- [x] 2.4 Create `tests/test_web.py` — unit tests using Starlette `TestClient`: health endpoint returns 200, history endpoint returns stored entries, search endpoint returns results, server binds to 127.0.0.1 only

## Phase 3: CLI Integration

- [x] 3.1 Modify `src/sift/cli.py` — add `--web` flag to `parse_args()` (experimental, help text notes opt-in nature)
- [x] 3.2 Modify `src/sift/cli.py` — add `_run_web_mode(args)` function: instantiate `SearchHistoryStore`, create Starlette app, start uvicorn in background thread, open browser via `webbrowser.open`, print URL to stderr
- [x] 3.3 Modify `src/sift/cli.py` — wire `--web` in `main()`: if `args.web` and not `args.agent`, call `_run_web_mode`; if `args.web` and `args.agent`, warn on stderr that `--web` is ignored in agent mode
- [x] 3.4 Modify `src/sift/cli.py` — after successful search in all modes, persist results to `SearchHistoryStore` (non-blocking, fire-and-forget)

## Phase 4: Static Frontend (Minimal SPA)

- [x] 4.1 Create `src/sift/web/static/index.html` — minimal dashboard: search input, results list, history sidebar; vanilla JS, no build step; reuse landing-page design tokens/colors where practical
- [x] 4.2 Create `src/sift/web/static/app.js` — fetch `/api/history` on load, render recent searches; search form submits to `/api/search`, renders results with score bars and repo metadata
- [x] 4.3 Create `src/sift/web/static/style.css` — minimal dark theme matching landing-page aesthetic; responsive for desktop browsers

## Phase 5: Dependencies & Wiring

- [x] 5.1 Modify `pyproject.toml` — add `starlette` and `uvicorn` to `[project.optional-dependencies]` under a new `web` extra; do NOT add to core `dependencies`
- [x] 5.2 Modify `src/sift/web/server.py` — lazy-import starlette/uvicorn; if missing, print helpful error: `pip install sift[web]`
- [x] 5.3 Verify `sift --agent` JSON output contract unchanged — run existing `tests/test_cli.py` and `tests/test_regression.py` with no modifications needed

## Phase 6: Verification

- [x] 6.1 Run full test suite: `pytest tests/` — all existing tests pass, new tests pass
- [x] 6.2 Manual smoke test: `sift --web -q "jwt auth" -l Python` — browser opens, dashboard loads, search works, history persists
- [x] 6.3 Verify `sift --agent -q "jwt auth" -l Python` output unchanged (no `_meta` field additions, same JSON schema)
- [x] 6.4 Verify `sift -q "test" -l Python --format json` output unchanged
