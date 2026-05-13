# Mission Rules — sift / repo-scout

> Canonical mission artifact for SDD orchestration. Agents MUST read this before
> making design decisions, scoping changes, or prioritizing work across domains.
>
> **Last updated**: 2026-05-12

---

## Mission

**Active project**: sift (formerly repo-scout) — v0.3.0  
**North-star metric**: An agent or human can query a technical need in natural
language and receive the **best GitHub repository recommendation** in a single
shot — deterministic, local, no cloud dependencies.

**Benchmark reference**: `tests/test_query.py`, `tests/test_regression.py`,
`tests/test_scoring.py` define canonical queries and expected winners.

---

## How to make SDD decisions

1. **Does the change improve recommendation quality (relevance, accuracy,
   determinism)?** → High priority.
2. **Does the change reduce agent/human friction (UX, docs, speed)?** → Medium
   priority.
3. **Does the change harden reliability (tests, error handling, rollback)?** →
   Medium priority.
4. **Does the change add infrastructure without immediate user-facing value?** →
   Low priority. Defer unless it unblocks a higher-priority item.

---

## Escalation criteria

Escalate to the human maintainer when:

- A change would break the `--agent` / `--ai` JSON output contract (stable fields)
- A change would introduce cloud/LLM dependencies into local scoring
- A change would require removing or renaming stable CLI flags
- A change would conflict with an in-flight SDD change (check the SDD registry)
- A security or credential leak is discovered

---

## Prioritization rules

| Category | Rule |
|----------|------|
| **In scope** | Retrieval/ranking improvements, CLI/TUX enhancements, documentation, test coverage, SDD workflow |
| **Out of scope** | Cloud services, LLM embeddings, external scoring APIs, non-GitHub sources |
| **Human escalation** | Breaking output contract, introducing paid tiers, changing license, removing features |

### Work-in-progress guidance

- No more than **2 in-flight SDD changes** at a time
- A change that has been idle for more than 7 days SHOULD be archived or
  explicitly deferred
- New proposals MUST reference active changes to avoid conflicts

---

## Reviewable-boundary discipline

### Default budget

- **400 changed lines** per PR (insertions + deletions, excluding generated
  files and lockfiles)
- This is the MAXIMUM, not a target. Smaller PRs are always better.

### Deferral rules

Before expanding scope beyond the current PR boundary, an agent MUST:

1. State what is being deferred
2. Say WHY it is out of scope for THIS change
3. Either create a new SDD proposal or link an existing issue

### Size-exception path

To exceed 400 lines, an agent MUST:

1. Justify why the change cannot be split (e.g., atomic refactor, cross-cutting
   concern)
2. Record the exception in the apply-progress artifact
3. The human MUST acknowledge the exception before code is written

---

## Companion artifacts

- `.atl/skill-registry.md` — all installed skills, compact rules, project standards
- `.atl/` — other SDD and project-level artifacts
- Engram topic `sdd/{change-name}/proposal|spec|design|tasks|apply-progress` —
  per-change SDD artifacts

---

## How to use this document

1. **Read this first** at the start of any SDD session.
2. **Reference it** when prioritizing tasks, scoping PRs, or deciding whether
   to escalate.
3. **Update it** when the mission, north-star metric, or prioritization rules
   change — this should be rare and deliberate.
