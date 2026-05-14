# Integrations

Sift supports dedicated output modes for Hermes and n8n integrations alongside the existing `--agent` flag.

## Hermes

```bash
sift --query "JWT authentication" --language Python --hermes
```

Returns a JSON object with `_meta` and `results`, identical to `--agent` but:

- `_meta` includes `hermes_compliance: "1.0"`
- The human hint key `?` is omitted

```json
{
  "_meta": {
    "sift_version": "0.3.0",
    "repo_scout_version": "0.3.0",
    "speed_tier": "balanced",
    "query": "JWT authentication",
    "elapsed_seconds": 3.42,
    "api_calls": 5,
    "hermes_compliance": "1.0"
  },
  "results": [...]
}
```

## n8n

```bash
sift --query "JWT authentication" --language Python --n8n
```

Returns a **raw JSON array** of result objects — no `_meta` envelope. Designed for direct consumption in n8n workflows.

```json
[
  {
    "name": "owner/repo",
    "url": "https://github.com/owner/repo",
    "description": "...",
    "language": "Python",
    "last_commit": "2025-01-01T00:00:00Z",
    "score": 85.3,
    "score_parts": {...},
    "stars": 5656,
    "forks": 1200,
    "license": "MIT",
    "why": "..."
  }
]
```

### n8n Workflow Template

A ready-to-import workflow template is available at `integrations/n8n/sift-search.json`. It uses an **Execute Command** node to run `sift --n8n` and a **Code** node to parse the raw JSON array into n8n items.

Import the template into your n8n instance and configure the `query` and `language` inputs.

## Common Behavior

- Both modes require `--query` and `--language` (exit code 2 if missing).
- Errors go to stderr with non-zero exit code; stdout stays clean.
- Empty result sets return valid JSON and exit 0.
- Independent from `--agent` — use one output mode at a time.
