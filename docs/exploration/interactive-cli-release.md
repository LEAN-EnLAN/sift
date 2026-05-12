# Exploration: interactive-cli-release

## Current State

**Module breakdown (1902 total lines):**

| Module | Lines | Coverage | Notes |
|--------|-------|----------|-------|
| `cli.py` | 162 | ❌ untested | argparse-only, no interactive input, no progress indicator, Ctrl+C unhandled in search |
| `render.py` | 155 | ❌ untested | Rich Table (7 cols) — "Why" column wraps creating noise, URL wraps on wide terminals |
| `scoring.py` | 186 | ✅ 9 tests | 5-factor formula + relevance gate, solid |
| `query.py` | 150 | ✅ 3 tests | Spanish→English expansion, query variant generation |
| `models.py` | 51 | — | Clean dataclasses |
| `auth.py` | 240 | ❌ untested | OAuth device flow, token persistence |
| `github.py` | 187 | ❌ untested | GitHub API client, cache, throttle, rate limit retry |
| `web.py` | 768 | ❌ untested | Standalone web UI (embedded HTML/CSS/JS) |

**Dependencies**: Only `rich>=14,<15` (v14.3.3). No Textual, no prompt_toolkit.

**Git**: No repository initialized. No CI. No changelog.

### Verified output pain points

```
                                            Top 2 repositorios recomendados
  #   Repo                              Score   Last               ★   Lang   Why
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1   owner/project-a                   60.84   2026-04-25      1.9k   Python  actividad reciente (hace 16 días);
                                                                                  comunidad fuerte (1.855 stars).
  2   owner/project-b                   44.10   2026-03-31      5.7k   Python  actividad reciente (hace 41 días);
                                                                                  comunidad fuerte (5.656 stars).
```

Problems:
1. 7-column Rich table forces wrapping on standard terminals
2. "Why" column wraps creating tall uneven rows
3. URL shown below repo name on wide terminals (visual clutter)
4. No progress feedback during 10-30s GitHub API wait
5. Language must be supplied via `-l` every invocation
6. No post-results action layer

## Affected Areas

- `src/repo_scout/cli.py` — Add interactive mode, progress indicator, Ctrl+C signal handler
- `src/repo_scout/render.py` — Cleaner compact table for interactive mode
- `pyproject.toml` — No new deps needed (Rich-only)
- `src/repo_scout/__init__.py` — Version bump to 0.2.0-dev
- `README.md` — Interactive mode docs, English content
- `tests/test_cli.py` (new) — interactive mode tests
- `tests/test_render.py` (new) — render tests

## Approaches

### 1. Rich-only interactive mode (RECOMMENDED)

Zero new dependencies. Use built-in `rich.prompt.Prompt`, `rich.progress.Progress`, `rich.live.Live`.

**Flow:**
```
$ repo-scout                        # enters interactive mode
🔍 Enter your technical need: autenticación con JWT
📚 Language(s) [Python]: Python
⏳ Searching... ━━━━━━━━━━━━━━ 100%

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ #  Repo                   Score    ┃
┃ 1  owner/project-a        60.84    ┃
┃ 2  owner/project-b        44.10    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Open [N], Refresh [R], Quit [Q]:
```

- **Pros**: Zero new deps, ~120 lines added, ships today, CI-safe via `--format json`
- **Cons**: No arrow-key navigation, no fuzzy search
- **Effort**: Low

### 2. Rich + prompt_toolkit interactive

Add `prompt_toolkit` for fuzzy-searchable list selector with vim keys.

- **Pros**: Polished keyboard navigation, search filtering, multi-select support
- **Cons**: Adds ~2MB dep, more code, justifies only after MVP validation
- **Effort**: Medium

### 3. Textual-based TUI

Full async TUI with screen navigation.

- **Pros**: Most polished UX
- **Cons**: Major rewrite, ~10MB dep, violates "don't rewrite" constraint
- **Effort**: High

## Recommendation

**Option 1 (Rich-only)** — Ship the interactive MVP with zero new dependencies.

This is the most defensible approach for a v0.1 release:
- Fixes the #1 complaint (noisy output) without architectural risk
- Progress feedback transforms the 10-30s wait from frustrating to tolerable
- Every feature is additive — `--format json` / `--format markdown` / `--format table` remain untouched
- Can upgrade to prompt_toolkit or Textual in a future change without breaking anything

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Network latency (no token → 30-60s) | High | Rich Progress spinner; auto-reduce candidates; document token requirement |
| Ctrl+C during ThreadPoolExecutor | High | Add signal handler that sets shutdown flag; `wait()` with timeout |
| Score quality unvalidated | Medium | Ship as-is with disclaimer; add feedback mechanism later |
| Rate limit without auth (60 req/h) | Medium | Already auto-reduces candidates to 12; document prominently in README |
| README is Spanish-only | Medium | Add English README or bilingual sections for release |
| No git repo / CI | Low | Separate setup task (not part of this change) |
| Test gap (0% coverage on 5/7 modules) | Low | Prioritize cli.py + render.py tests for this change |

## Ready for Proposal

**Yes.** Scope boundaries:

| In scope | Out of scope |
|----------|-------------|
| Rich-only interactive mode (default) | Textual TUI |
| Cleaner table output | Fuzzy search |
| Progress indicator | Scoring changes |
| Ctrl+C signal handling | Web app changes |
| Prompt-based query/language input | Git init / CI setup |
| Compact result view | CHANGELOG creation |
| CLI mode tests | README rewrite (minor update only) |
| Render polish | |
