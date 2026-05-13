# Changelog

## 2026-05-12 — Scoring v2 Local Heuristics

### New `score_parts` Keys

Scoring v2 introduces three new keys in `score_parts`:

| Key | Type | Range | Description |
|-----|------|-------|-------------|
| `modernity` | float | 0–100 | Age since creation (10-year graduated decay) |
| `authority` | float | 0–100 | Canonical repository match per domain |
| `penalties` | float | 0–25 | Subtractive penalty (awesome-list, toy, fork, high issue ratio) |

### Removed Key

- `activity`: this signal is folded into `maintenance`. Renderers should use
  `score_parts.get("activity", score_parts.get("maintenance", 0))` for one release cycle.

### Migration

- Default behavior is unchanged: `score_repo()` and `shortlist()` use v2.
- Set `SIFT_SCORING_V2=0` to restore v1 pipeline.
- Agent JSON output preserves all stable fields (`score`, `score_parts`, `why`).

### Rollback

- `pre-scoring-v2` git tag cut before merge.
- Set `SIFT_SCORING_V2=0` environment variable to use v1 functions.
