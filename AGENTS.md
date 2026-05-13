# Agent Integration Guide — sift

> **Current session context** — set these before starting work:
> - **Active mission**: {{ mission-name }}
> - **Benchmark artifact**: {{ link to benchmark or spec }}
> - **Current SDD gate**: {{ explore / propose / spec / design / tasks / apply / verify / archive }}
> - **Next gate to clear**: {{ next-gate }}
> - **Mission rules**: [`.atl/mission-rules.md`](.atl/mission-rules.md)

## Quick Start

```bash
sift --agent --query "JWT authentication" --language Python
```

Output is JSON on stdout with a `_meta` envelope:

```json
{
  "_meta": {
    "sift_version": "0.3.0",
    "repo_scout_version": "0.3.0",
    "speed_tier": "balanced",
    "query": "JWT authentication",
    "elapsed_seconds": 12.4,
    "api_calls": 5,
    "?": "send --query, --language and --agent for machine-readable output"
  },
  "results": [
    {
      "name": "jpadilla/pyjwt",
      "url": "https://github.com/jpadilla/pyjwt",
      "description": "JSON Web Token implementation in Python",
      "language": "Python",
      "last_commit": "2026-03-31T10:00:00Z",
      "score": 85.3,
      "score_parts": {"relevance": 90.0, "activity": 75.0, "community": 82.0, "docs": 70.0, "maintenance": 95.0},
      "stars": 5656,
      "forks": 1200,
      "license": "MIT",
      "why": "actividad reciente (hace 2 meses); comunidad fuerte (5.656 stars); licencia MIT; no está archivado ni es fork."
    }
  ]
}
```

## Invocation

| Flag | Purpose |
|------|---------|
| `--agent` / `--ai` | Enable agent mode: JSON stdout, machine-readable `_meta` |
| `--speed fast\|balanced\|thorough` | Control query breadth and enrichment depth |
| `--top N` | Limit results (default: 5) |
| `--query` / `-q` | Natural-language search query |
| `--language` / `-l` | Programming language(s), comma-separated |

## Output Contract

- **stdout**: Final JSON with `_meta` + `results`. Stable field names are preserved (`name`, `url`, `description`, `language`, `last_commit`, `score`, `score_parts`, `stars`, `forks`, `license`, `why`).
- **stderr**: Human-readable progress and warnings. Machine-consumable stderr events are planned for a future release.
- **Exit code**: `0` on success, `1` on cancel/interrupt, `2` on error.

## Speed Tiers

| Tier | Max Queries | Max Candidates | Pool Size | Enrichment |
|------|-------------|----------------|-----------|------------|
| `fast` | 4 | 8 | 20 | Bottom 50% skipped |
| `balanced` (default) | 7 | 35 | 30 | All candidates enriched |
| `thorough` | 8 | 50 | 35 | All candidates enriched |

## TUI Caveat

When running in a TTY without `--agent`, `--no-interactive`, or headless env vars,
sift launches a Textual TUI. This TUI is NOT suitable for agent/CI pipelines.
Always pass `--agent` (or `--ai`) for machine-readable JSON output, or set
`SIFT_HEADLESS=1` to force headless mode.

Advanced filters (`--min-stars`, `--pushed-after`, `--license`, forks/archived
flags, and explicit `--speed`) are CLI/headless controls. The TUI is optimized
for a one-shot human recommendation: natural-language request in, best answer +
top 5 out. Agents should pass filters explicitly via flags.

## Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token (recommended for higher rate limits).
- `SIFT_HEADLESS=1`: Force headless mode even in TTY environments (legacy `REPO_SCOUT_HEADLESS` also accepted).
- `GITHUB_CLIENT_ID`: Custom OAuth App client ID for `--login` device flow.

## Stability Guarantees

1. **Entrypoint**: The `sift` CLI is the sole entrypoint. The `python -m sift.cli` form is also supported but not stable.
2. **JSON fields**: `results[].{name,url,description,language,last_commit,score,score_parts,stars,forks,license,why}` are stable across releases.
3. **`_meta` fields**: New keys may be added; existing keys will not be removed without a major version bump.
4. **Exit codes**: Preserved across releases.

## Mission Orchestration

### Source of truth

[`.atl/mission-rules.md`](.atl/mission-rules.md) is the **canonical mission
artifact** for this project. Every agent MUST read it before making design
decisions, scoping changes, or prioritizing work. If the mission, north-star
metric, or prioritization rules change, `.atl/mission-rules.md` is updated —
no other artifact overrides it.

### Prioritization guidance

When ranking work across domains and in-flight changes:

1. **Scoring/retrieval v2 improvements** (recommendation quality) come first.
2. **UX and documentation** that reduces agent or human friction comes second.
3. **Test/reliability hardening** comes next.
4. **New infrastructure without user-facing value** is deferred unless it
   unblocks higher-priority work.
5. No more than **2 SDD changes in flight** at once. Idle changes (>7 days)
   should be archived or deferred.

### Boundary discipline

Before expanding a change's scope beyond its current PR boundary, an agent
MUST explicitly state:

- WHAT is being deferred
- WHY it is out of scope for the current change
- WHERE the deferred work is tracked (new SDD proposal or existing issue)

The 400-line default PR budget applies unless a `size:exception` is recorded
and acknowledged.
