# Proposal: web-ui-flag (Experimental)

## Intent

Sift is CLI-first today, but lacks persistent search history and rich multi-repo
comparison views. Opening a browser is worth exploring because: (1) persistent
history makes repeated queries fast, (2) HTML/CSS can express comparison and detail
far beyond terminal tables, and (3) a dashboard gives a quick landing spot between
sessions.

**This is an experimental, opt-in capability.** The goal of the first iteration is
to validate whether browser UX creates enough real user value versus the existing
CLI and TUI — not to ship a finished product. If it doesn't prove valuable, it
can be removed without breaking anything.

This change adds a `--web` flag that launches a local-only sidecar web server,
without breaking the existing JSON output contract.

## Scope

### In Scope
- `--web` flag (experimental) that starts a local HTTP server (127.0.0.1) on a random available port and opens the browser
- `web-companion` capability: local web server with minimal SPA, search history stored in `~/.cache/sift/history.json`
- Basic dashboard: recent searches, richer detail/compare view for repos

### Out of Scope
- User accounts, auth, BYOK (future work)
- Cloud telemetry or external service dependencies (banned by mission)
- Advanced report generation (PDF, etc.) — deferred
- Multi-user or collaborative features — deferred
- Changing `--format json` or `--agent` output contract

## Capabilities

### New Capabilities
- `web-companion`: Experimental local sidecar web server providing a search history dashboard and richer repo comparison views, invoked via `--web` flag

### Modified Capabilities
- None (CLI JSON contract unchanged; new capability is additive and gated behind `--web`)

## Approach

1. **`--web` flag entry point** in `cli.py`: parse `--web`, launch server, open browser.
2. **Local-only server** using Starlette (lighter than FastAPI) + uvicorn, bound to `127.0.0.1` only. No telemetry, no external calls.
3. **Search history** persisted as JSON in `~/.cache/sift/history.json` — simple, no DB.
4. **Minimal SPA** serving from `src/sift/web/static/` — vanilla JS or lightweight framework, no build step for initial release.
5. **Port strategy**: try default port, fall back to random available port if taken.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sift/cli.py` | Modified | Add `--web` flag, server orchestration |
| `src/sift/web/` | New | Web server package (server, routes, static assets) |
| `src/sift/persistence/` | New | Search history read/write (`~/.cache/sift/history.json`) |
| `pyproject.toml` | Modified | Add `starlette`, `uvicorn` as optional dependencies |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dependency bloat (web framework) | Medium | Gate behind `--web` flag; only install when flag is used |
| Port conflict | Low | Retry with random available port; surface clear error |
| Breaking CLI JSON contract | None | No change to `--format json` or `--agent` output |
| Feature dropped post-experiment | Low | Design for clean removal; history file stays harmless if abandoned |
| User confusion if experimental UX is unstable | Medium | Document `--web` as experimental in help output |

## Rollback Plan

- Remove `--web` flag from `cli.py`
- Delete `src/sift/web/` and `src/sift/persistence/` packages
- Revert `pyproject.toml` to remove new dependencies
- History file at `~/.cache/sift/history.json` can be left or deleted manually

## Dependencies

- `starlette` + `uvicorn` — optional runtime dependencies, imported only when `--web` is invoked

## Success Criteria

- [ ] `sift --web` launches a local server and opens the browser
- [ ] Search history persists across separate CLI invocations
- [ ] Dashboard displays recent searches with rich compare/detail views
- [ ] Existing `--format json` and `--agent` output unchanged
- [ ] No external network calls or telemetry; server is 127.0.0.1 only
- [ ] **Validation criterion**: After first iteration, enough user feedback to determine whether browser UX justifies continued investment vs CLI/TUI