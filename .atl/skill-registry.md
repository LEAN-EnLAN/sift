# Skill Registry — sift

Generated: 2026-05-11T00:00:00Z
Source: User-level skills only (no project-level skills found)

## User Skills

### SDD Workflow Skills (`.config/opencode/skillas/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| sdd-init | sdd init, iniciar sdd, openspec init | Initialize SDD context, testing capabilities, registry, and persistence |
| sdd-explore | orchestrator launches exploration | Explore SDD ideas before committing to a change |
| sdd-propose | orchestrator launches proposal | Create an SDD change proposal with intent, scope, and approach |
| sdd-spec | orchestrator launches spec | Write SDD delta specs with requirements and scenarios |
| sdd-design | orchestrator launches design | Create the SDD technical design and architecture approach |
| sdd-tasks | orchestrator launches tasks | Break an SDD change into implementation tasks |
| sdd-apply | orchestrator launches apply | Implement SDD tasks from specs and design |
| sdd-verify | orchestrator launches verify | Execute tests and prove implementation matches specs, design, and tasks |
| sdd-verify-design | orchestrator launches verify-design | Verification-focused sub-agent for validating frontend and UI quality |
| sdd-archive | orchestrator launches archive | Archive a completed SDD change by syncing delta specs |
| sdd-onboard | orchestrator launches onboarding | Walk users through the SDD workflow on the real codebase |

### Code Quality & Review Skills (`.config/opencode/skillas/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| audit-project | — | Code review multi-agente iterativo con especialistas por dominio |
| branch-pr | creating, opening, or preparing PRs | Create Gentle AI pull requests with issue-first checks |
| chained-pr | PRs over 400 lines, stacked PRs | Split oversized changes into chained PRs |
| comment-writer | PR feedback, issue replies, reviews | Write warm, direct collaboration comments |
| drift-detect | — | Compara docs/planes contra implementación real para detectar desviación |
| frontend-quality-gate | — | Strict frontend UI/UX quality gate for anti-AI-slop |
| judgment-day | judgment day, dual review, adversarial review | Run blind dual review, fix confirmed issues, then re-judge |
| ship | ready to commit to merged PR | Automatización de entrega con CI monitoring |

### Domain-Specific Skills (`.config/opencode/skillas/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| go-testing | Go tests, go test coverage, Bubbletea teatest | Apply focused Go testing patterns |
| repo-intel | codebase context needed before modifying | Análisis estático unificado de repositorios |
| work-unit-commits | implementation, commit splitting | Plan commits as reviewable work units |

### Meta/Configuration Skills (`.config/opencode/skillas/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| caveman-internal | — | Compress internal agent output to reduce token usage |
| cognitive-doc-design | writing guides, READMEs, RFCs | Design docs that reduce cognitive load |
| cost-router | — | Optimize model routing for OpenCode/Gentle AI SDD work |
| deslop | — | Detecta y elimina patrones de 'AI slop' en código |
| issue-creation | creating GitHub issues, bug reports | Create Gentle AI issues with issue-first checks |
| skill-creator | new skills, agent instructions | Create LLM-first skills with valid frontmatter |
| pildhora-product-context | — | Product context and constraints for Pildhora health-tech project |

### UI/UX Design Skills (`.agents/skillas/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| adapt | responsive design, mobile layouts, breakpoints | Adapt designs across screen sizes, devices, contexts |
| animate | animation, transitions, micro-interactions | Enhance features with purposeful animations and motion effects |
| audit | accessibility, performance audit, technical review | Run technical quality checks (a11y, perf, theming, responsive) |
| bolder | design looks bland, generic, too safe | Amplify safe or boring designs for more visual impact |
| btca-local | "use btca" | — |
| clarify | confusing text, unclear labels, bad error messages | Improve unclear UX copy and microcopy |
| colorize | design looking gray, dull, lacking warmth | Add strategic color to monochromatic features |
| critique | review, critique, evaluate design | Evaluate design from UX perspective with quantitative scoring |
| delight | polish, personality, animations, micro-interactions | Add moments of joy and unexpected touches |
| distill | simplify, declutter, reduce noise | Strip designs to essence by removing unnecessary complexity |
| impeccable | build web components, pages, artifacts, posters | Create distinctive, production-grade frontend interfaces |
| layout | layout feeling off, spacing issues, visual hierarchy | Improve layout, spacing, and visual rhythm |
| optimize | slow, laggy, janky, performance, bundle size | Diagnose and fix UI performance issues |
| overdrive | wow, impress, go all-out | Push interfaces past conventional limits |
| polish | polish, finishing touches, pre-launch review | Final quality pass fixing alignment, spacing, micro-details |
| quieter | too bold, too loud, overwhelming | Tone down visually aggressive designs |
| shape | planning, design direction, UX strategy | Plan UX and UI for a feature before writing code |
| typeset | fonts, type, readability, text hierarchy | Improve typography for intentional text |

## Project-Level Files

No project-level skill directories or convention files found.

## Compact Rules (Selected Skills)

### cost-router
- Use cheap models for volume; premium only for high-leverage reasoning, design, or final verification
- Never send bad diffs directly to premium verify; use cheap verify first
- Use caveman-internal for internal summaries; keep final summaries human-readable
- Routing: explore→deepseek-v4-flash, design→gemini-3.1-pro-preview, apply(frontend)→claude-sonnet-4.6

### deslop
- Phase 1 (high certainty): detect debug logs, empty TODOs/FIXMEs, empty catch blocks, disabled linters, hardcoded secrets, large commented code
- Phase 2 (medium certainty): flag excessive comment/code ratio >30%, AI preamble comments, over-engineering, dead code, unimplemented stubs
- Phase 3 (optional CLI): jscpd/madge for JS/TS, pylint/radon for Python

### drift-detect
- Collect from GitHub issues, docs, exports, CHANGELOG
- Match by concepts not strings (e.g., "user auth" ↔ auth/, login.js)
- Categorize drift as: documented-not-implemented, implemented-not-documented, feature-drift, stale-docs

### branch-pr
- Every PR MUST link an approved issue — no exceptions
- Every PR MUST have exactly one type:* label
- Blank PRs without issue linkage are blocked by CI

### skill-creator
- Skill is runtime LLM contract, not human documentation
- Target 180–450 body tokens; hard max 1000
- Keep description under 250 chars, quoted, trigger-first
- References must be local files relative to skill directory
- Structure: frontmatter, Activation Contract, Hard Rules, Decision Gates, Execution Steps, Output Contract, References

### repo-intel
- Analyze: git hotspots, change coupling, ownership (bus factor), AI-generated file detection, AST symbol mapping
- Provide: file metadata summary, hotspots ranked by change frequency, coupling groups, ownership table
- Recommend files to inspect and risky architectural areas before modifications
