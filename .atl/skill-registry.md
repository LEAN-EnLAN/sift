# Skill Registry — repo-scout

Generated: 2026-05-12T00:00:00Z
Source: User-level skills (`~/.config/opencode/skills/`, `~/.agents/skills/`)
Project-level skills: none found

## User Skills

### SDD Workflow Skills (`~/.config/opencode/skills/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| sdd-init | sdd init, iniciar sdd, openspec init | Initialize SDD context, testing capabilities, registry, and persistence |
| sdd-explore | orchestrator launches exploration | Explore SDD ideas before committing to a change |
| sdd-propose | orchestrator launches proposal | Create a change proposal with intent, scope, and approach |
| sdd-spec | orchestrator launches spec | Write delta specs with requirements and scenarios |
| sdd-design | orchestrator launches design | Create technical design and architecture approach |
| sdd-tasks | orchestrator launches tasks | Break change into implementation tasks |
| sdd-apply | orchestrator launches apply | Implement SDD tasks from specs and design |
| sdd-verify | SDD verification phase, verify change | Execute tests and prove implementation matches specs/design/tasks |
| sdd-verify-design | orchestrator launches verify-design | Frontend/UI design verification: visual hierarchy, accessibility, anti-slop checks |
| sdd-archive | orchestrator launches archive | Archive completed change by syncing delta specs |
| sdd-onboard | orchestrator launches onboarding | Walk users through the full SDD cycle on real codebase |

### Code Quality & Review Skills (`~/.config/opencode/skills/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| audit-project | user says "use audit-project" | Code review multi-agente iterativo con especialistas por dominio (seguridad, performance, calidad, tests, arquitectura) |
| branch-pr | creating, opening, or preparing PRs | Create Gentle AI pull requests with issue-first checks |
| chained-pr | PRs over 400 lines, stacked PRs, review slices | Split oversized changes into chained PRs that protect review focus |
| comment-writer | PR feedback, issue replies, reviews, Slack messages, GitHub comments | Write warm, direct collaboration comments |
| cost-router | — | Optimize model routing for OpenCode/Gentle AI SDD work to minimize cost while maximizing quality |
| drift-detect | — | Compara documentación, planes y issues contra implementación real para detectar desviación (drift) |
| frontend-quality-gate | — | Strict frontend UI/UX quality gate for anti-AI-slop, product-grade design, accessibility, responsive behavior |
| judgment-day | judgment day, dual review, adversarial review, juzgar | Run blind dual review, fix confirmed issues, then re-judge |
| ship | ready to commit → merged PR with CI monitoring | Automatización de entrega con manejo de comentarios de reviewers |
| work-unit-commits | implementation, commit splitting, chained PRs | Plan commits as reviewable work units |

### Domain-Specific Skills (`~/.config/opencode/skills/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| cognitive-doc-design | writing guides, READMEs, RFCs, onboarding, architecture docs | Design docs that reduce cognitive load |
| deslop | — | Detecta y elimina patrones de 'AI slop' en código: debug logs, TODOs vacíos, comentarios excesivos, stubs, secretos hardcodeados |
| go-testing | Go tests, Go test coverage, Bubbletea teatest, golden files | Apply focused Go testing patterns |
| issue-creation | creating GitHub issues, bug reports, feature requests | Create Gentle AI issues with issue-first checks |
| pildhora-product-context | — | Product context and constraints for Pildhora health-tech portfolio project |
| repo-intel | codebase context needed, repo analysis, hotspots, ownership, bus factor | Análisis estático unificado de repositorios — historia git, símbolos AST, metadata, hotspots, ownership |
| skill-creator | new skills, agent instructions, documenting AI usage patterns | Create LLM-first skills with valid frontmatter |

### Utility Skills (`~/.config/opencode/skills/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| caveman-internal | — | Compress internal agent output to reduce token usage while preserving actionable signal |
| large-change-archive-report-writer | archiving large changes, HTML reports, handoff docs | Generate implementation reports and handoff documents for large/complex changes |
| pulpo-ui-system | — | UI system design tokens and conventions for Pulpo projects |

### UI/UX Design Skills (`~/.agents/skills/`)
| Skill | Trigger | Description |
|-------|---------|-------------|
| adapt | responsive design, mobile layouts, breakpoints, viewport, cross-device | Adapt designs across screen sizes, devices, contexts |
| animate | animation, transitions, micro-interactions, motion design, hover effects | Review and enhance with purposeful animations and micro-interactions |
| audit | accessibility (a11y), performance audit, technical quality review | Run technical quality checks across a11y, perf, theming, responsive, anti-patterns |
| bolder | design looks bland, generic, too safe, lacks personality | Amplify safe designs for more visual impact while maintaining usability |
| btca-local | "use btca" | — |
| clarify | confusing text, unclear labels, bad error messages, UX writing | Improve unclear UX copy, error messages, microcopy, labels, instructions |
| colorize | design looking gray, dull, lacking warmth, needs color | Add strategic color to monochromatic features for more engaging interfaces |
| critique | review, critique, evaluate design, UX feedback | Evaluate design from UX perspective: visual hierarchy, IA, emotional resonance, cognitive load |
| delight | polish, personality, animations, micro-interactions, fun, memorable | Add moments of joy and unexpected touches that make interfaces memorable |
| distill | simplify, declutter, reduce noise, cleaner UI | Strip designs to essence by removing unnecessary complexity |
| impeccable | build web components, pages, artifacts, posters, applications | Create distinctive production-grade frontends; call with 'craft', 'teach', or 'extract' |
| layout | layout feels off, spacing issues, visual hierarchy, crowded, alignment | Improve layout, spacing, and visual rhythm |
| optimize | slow, laggy, janky, performance, bundle size, load time | Diagnose and fix UI performance across loading, rendering, animations, images |
| overdrive | wow, impress, go all-out, technically ambitious | Push interfaces past conventional limits with shaders, spring physics, scroll-driven reveals |
| polish | polish, finishing touches, pre-launch review, something looks off | Final quality pass fixing alignment, spacing, consistency, micro-details |
| quieter | too bold, too loud, overwhelming, aggressive, garish | Tone down visually aggressive or overstimulating designs |
| shape | planning, design direction, UX strategy, before writing code | Plan UX/UI for a feature before writing code — structured discovery interview → design brief |
| typeset | fonts, type, readability, text hierarchy, sizing feels off | Improve typography: font choices, hierarchy, sizing, weight, readability |

### Skill Resolution Notes
- `find-skills` (at `~/.agents/skills/`) exists but is excluded from registry — it's a meta-skill for discovering other skills
- `_shared`, `skill-registry` are excluded per scan rules (internal/SDD infrastructure)
- No project-level skills found in `.claude/skills/`, `.gemini/skills/`, `.agent/skills/`, or `skills/`

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
- Match by concepts not strings (e.g. "user auth" ↔ auth/, login.js)
- Categorize drift as: documented-not-implemented, implemented-not-documented, feature-drift, stale-docs

### branch-pr
- Every PR MUST link an approved issue — no exceptions
- Every PR MUST have exactly one type:* label
- Blank PRs without issue linkage are blocked by CI

### chained-pr
- Split at 400+ lines: each chain PR must be independently reviewable
- First PR: foundation/infra; later PRs: features on top
- Each chain PR must pass CI independently before next is opened

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

### sdd-init
- Detect real stack/conventions/architecture/testing/persistence — never guess
- engram mode: save to Engram only; openspec mode: write file artifacts
- Always persist testing capabilities separately
- Always build `.atl/skill-registry.md`
- Use capture_prompt: false for automated SDD/config saves

### sdd-propose
- Define: intent (problem + why now), scope (in/out), approach (how, architecture, tradeoffs)
- Validate against specs and design before proceeding to tasks
- Proposals must be rejected or accepted explicitly

### sdd-verify-design
- Validates: visual hierarchy, accessibility (color contrast, focus indicators), implementation cleanliness, anti-slop detection
- Produces deterministic pass/fail verdicts with specific findings and required fixes
- Not for backend-only, infra-only, database, or API-only tasks

### judgment-day
- Blind dual review: two independent reviews without cross-contamination
- Fix confirmed issues only
- Re-judge after fixes before declaring done

### work-unit-commits
- Each commit = one reviewable work unit (not one file, not all changes)
- Keep tests and docs with the code they belong to
- Split across chained PRs when total >400 lines

### pulpo-ui-system
- Project-specific UI tokens and conventions for Pulpo projects
- Load when working on UI components in Pulpo projects

### large-change-archive-report-writer
- Generate HTML reports and handoff documentation for large/high-complexity changes
- Include: implementation summary, architecture decisions, future maintenance risks
- Only for changes spanning many files, multiple domains, or introducing new features/refactors

### frontend-quality-gate
- Check: anti-AI-slop patterns, product-grade design, accessibility (WCAG), responsive behavior
- Strict gate: no debug artifacts, no placeholder content in production
- Run before shipping any frontend change

### ship
- Automate from ready-to-commit → merged PR
- Monitor CI pipeline after push
- Handle reviewer comments in the loop
