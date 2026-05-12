# Exploration: `tui-nlp-smart-input`

## Current State

### TUI (`src/sift/tui.py` — 312 lines)
- **Two sequential inputs**: `#query-input` + `#language-input`
- Flow: type query → Enter → focus moves to language input → type language → Enter → search starts
- **No progress indicator**: `Static` status text "Buscando en GitHub..." only — no spinner, no bar
- **No auto-detection**: raw strings passed directly to `_start_search()`, no NLP parsing of the natural input
- Result display: `ListView` with `ResultItem(ListItem)` works, arrow keys native
- Detail view: `RichLog` with markdown render, toggled via `ctrl+d` or Enter on selected item
- Quick keys via Textual `BINDINGS`: `q` quit, `escape` back, `ctrl+d` detail, `r` refresh
- CSS: dark theme, `#22F5A7` accent, `#333` borders, 3-panel layout (input, results, detail)
- Search runs via `@work(exclusive=True, group="search")` async worker

### NLP Pipeline (`src/sift/query.py` — 151 lines)
- `extract_keywords(natural_query)`: tokenizes, removes stopwords (Spanish + English), expands via `SPANISH_TO_ENGLISH` dict (42 entries), sorts by priority (literal/technical terms first), returns top 10
- `build_search_queries(natural_query, language, ...)`: generates multiple GitHub API query variants with qualifiers
- **No language detection function exists** — language is always passed explicitly
- The `SPANISH_TO_ENGLISH` dict already contains framework/language names (fastapi, django, flask, node, express, react, vue, angular, docker, kubernetes), but only for search expansion, not for detection
- **No speed detection**

### CLI (`src/sift/cli.py` — 457 lines)
- `run_tui_mode(args)`: creates `SiftApp()` and calls `app.run()` — thin wrapper
- `run_interactive_mode(args)`: uses Rich `InteractivePrompt` for query + language in non-TUI interactive mode
- `_run_agent(args)`: requires both `--query` and `--language`, outputs JSON with `_meta`
- Headless: `_is_headless()` checks `SIFT_HEADLESS` / `REPO_SCOUT_HEADLESS` env vars
- Main branching: agent → `_run_agent()`, force_interactive → `run_interactive_mode()`, TTY + not headless → `run_tui_mode()`, else headless

### Tests
- `tests/test_tui.py` (104 lines): basic import, lifecycle, widget presence, one search flow with mocked `run()`
- `tests/test_query.py` (37 lines): keyword extraction, search query building, no language detection tests
- Uses `pytest-asyncio`, Textual Pilot via `app.run_test(size=(100, 30))`

### Dependencies (`pyproject.toml`)
- `rich>=14,<15`, `textual>=2.0` (runtime)
- `pytest`, `pytest-asyncio` (dev)
- **No AI/ML dependencies**. External AI APIs explicitly forbidden.

---

## Affected Areas

| File | Why Affected |
|------|-------------|
| `src/sift/tui.py` | Core TUI rewrite: single smart input, preview panel, progress indicator |
| `src/sift/query.py` | Add `detect_language()` and `detect_speed()` functions |
| `src/sift/cli.py` | No changes needed — `run_tui_mode()` is a thin wrapper; smart input lives in TUI layer |
| `tests/test_tui.py` | New tests: smart input parsing, preview flow, confirmation, edge cases |
| `tests/test_query.py` | New tests: language detection cases, speed detection cases |
| `src/sift/interactive.py` | No changes — this is the non-TUI interactive mode (Rich prompts), kept as-is |

---

## Approaches

### 1. Keyword-based smart parse (RECOMMENDED)

Build a `detect_language()` function that scans tokens against a `LANGUAGE_HINTS` dict, mapping framework/ecosystem names to standard language names. Build a `detect_speed()` function that scans for keywords like "rápido"/"fast" → `fast`, "detallado"/"thorough" → `thorough`. Collapse TUI to a single input, show parsed preview on submit.

```
User types: "necesito autenticacion jwt en python fastapi"
→ detect_language tokens: ["autenticacion", "jwt", "python", "fastapi"]
→ LANGUAGE_HITS: {"python": "Python", "fastapi": "Python"} → ["Python"]
→ speed: balanced (default)
→ query: "necesito autenticacion jwt en python fastapi"
```

Preview panel shows:
```
┌─────────────────────────────────────┐
│  Query: autenticacion jwt           │
│  Language: Python                   │
│  Speed: balanced                    │
│  [Enter] to search [Tab] to edit    │
└─────────────────────────────────────┘
```

**Pros**:
- Zero new dependencies
- Deterministic, testable, debuggable
- Reuses existing `_normalize_token()` and stopword logic
- Works offline, fast (<1ms parse)
- Aligns with project's existing "simple keyword" philosophy

**Cons**:
- Ambiguous cases: "node" could be JavaScript or Node.js itself (minor — both valid for search)
- False positives: project names that match language keywords (unlikely in natural language input)
- No multi-language disambiguation: "fastapi react" → detects Python AND JavaScript, both are correct

**Effort**: Low-Medium (primarily TUI refactor + new parse functions)

### 2. Regex-pattern-based detection

Use regex patterns instead of token scanning: `\bpython\b` for Python, `\bfastapi\b` → Python, `\breact\b` → JavaScript/TypeScript. Also detect phrases like "en python" or "para javascript".

**Pros**:
- Handles word boundaries correctly (avoids "jupyter" matching "python")
- Can extract multi-word patterns like "machine learning" → no language
- Slightly more robust against compound words

**Cons**:
- More complex regex maintenance
- Same dependency profile (still no AI needed)
- Overlap with approach 1 in most cases
- Marginal benefit over simple token scanning for this use case

**Effort**: Low (slightly more than approach 1)

### 3. Rich Prompt-based smart input (carries current UX forward)

Keep two inputs but add auto-detection: when user types in query input, auto-detect language and pre-fill the language input. Show a parsed summary above the inputs.

**Pros**:
- Minimal TUI restructuring
- Backward compatible with existing tests

**Cons**:
- Still two inputs, confusing UX
- Doesn't solve the core problem of "type one thing and go"
- Preview UX is clunky with two inputs
- Auto-filling while typing creates weird focus behavior

**Effort**: Low (only NLP additions, minimal TUI change) — but doesn't fully solve the problem

---

## Recommendation

**Approach 1** (keyword-based smart parse + single input + preview panel).

Rationale:
- Directly addresses the user problem: "type one natural sentence, get results"
- Zero new dependencies, consistent with project's existing simple NLP approach
- The `SPANISH_TO_ENGLISH` dict is already in `query.py` — adding `LANGUAGE_HINTS` is the same pattern
- Preview panel provides transparency: user sees what was detected before search runs
- Fully testable with unit tests + Textual Pilot
- Falls back gracefully (no detected language → empty → user prompted)

### Proposed UX Flow

```
1. TUI opens with single input: "¿Qué necesitás buscar?"
   Placeholder: 'Ej: "autenticación JWT en Python"'

2. User types natural input and presses Enter

3. NLP parses input:
   a. detect_language() — scans tokens against LANGUAGE_HINTS
   b. detect_speed() — scans for speed keywords
   c. extract_keywords() — existing function for search enhancement
   d. Clean query (remove detected keywords from search if redundant)

4. Preview panel slides in below input showing parsed values:
   ┌─ Preview ────────────────────────────┐
   │  Consulta: autenticación JWT         │
   │  Lenguaje(s): Python                 │
   │  Velocidad: balanced                 │
   │                                      │
   │  [Enter] Buscar  [↑↓] Editar        │
   └──────────────────────────────────────┘

5a. Press Enter → search starts with LoadingIndicator
5b. Edit input → press Enter → re-parse → re-preview

6. Results appear in ListView (same as now), progress indicator stops

7. Detail view via Enter on result, escape to go back
```

### Progress Visibility

Replace `Static("Buscando en GitHub...")` with Textual's `LoadingIndicator` widget during search. The `@work` async pattern remains, but we toggle LoadingIndicator visibility.

```python
# In compose():
yield LoadingIndicator(id="search-spinner")

# In watch_searching():
spinner = self.query_one("#search-spinner", LoadingIndicator)
spinner.display = searching
```

### Result Navigation

Already working: `ListView` + `ResultItem` with native arrow key navigation and Enter for detail. Keep existing behavior.

### Quick Keys

Keep Textual `BINDINGS` approach. Add:
- `d` (lowercase) for detail view (ergonomic alternative to `ctrl+d`)
- `r` for refresh (already exists)
- `q` / `escape` (already exists)
- Remove `sys.stdin.read()` patterns entirely (already not used in TUI — only in `run_interactive_mode`)

---

## New Functions to Add

### `query.py` additions:

```python
# Framework/language mapping (extends the same pattern as SPANISH_TO_ENGLISH)
LANGUAGE_HINTS: dict[str, str] = {
    "python": "Python",
    "py": "Python",
    "python3": "Python",
    "fastapi": "Python",
    "django": "Python",
    "flask": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "node": "JavaScript",
    "nodejs": "JavaScript",
    "express": "JavaScript",
    "nestjs": "TypeScript",
    "react": "TypeScript",
    "vue": "TypeScript",
    "angular": "TypeScript",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "rails": "Ruby",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "scala": "Scala",
    "php": "PHP",
    "c#": "C#",
    "csharp": "C#",
    "dotnet": "C#",
    "cpp": "C++",
    "c++": "C++",
    "c": "C",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
}

SPEED_HINTS: dict[str, str] = {
    "rápido": "fast",
    "rapido": "fast",
    "fast": "fast",
    "quick": "fast",
    "rapid": "fast",
    "detallado": "thorough",
    "thorough": "thorough",
    "detailed": "thorough",
    "exhaustivo": "thorough",
    "completo": "thorough",
}

def detect_language(natural_query: str) -> list[str]:
    """Detect programming languages from natural language query.
    
    Returns a deduplicated list of detected language names.
    Falls back to [] if nothing detected (user must specify).
    """
    tokens = [_normalize_token(t) for t in re.split(r"\s+", natural_query) if t.strip()]
    detected: set[str] = set()
    for token in tokens:
        if token in LANGUAGE_HINTS:
            detected.add(LANGUAGE_HINTS[token])
    return sorted(detected)

def detect_speed(natural_query: str) -> str:
    """Detect speed preference from natural language query.
    
    Returns "fast", "balanced", or "thorough". Defaults to "balanced".
    """
    tokens = [_normalize_token(t) for t in re.split(r"\s+", natural_query) if t.strip()]
    for token in tokens:
        if token in SPEED_HINTS:
            return SPEED_HINTS[token]
    return "balanced"
```

### `tui.py` changes:

- Replace `Input(id="query-input")` + `Input(id="language-input")` with a single `Input(id="smart-input")`
- Add `preview_panel` container (hidden by default) with Static widgets showing parsed values
- Hook `Input.Submitted` on smart input:
  1. Call `detect_language()` and `detect_speed()`
  2. Show preview panel with detected values
  3. If user presses Enter again (focus on confirm button or Enter re-triggers on input), start search
  4. If user edits input and submits again, re-parse
- Add `LoadingIndicator(id="search-spinner")` to compose
- BINDINGS: keep existing, add `d` as alias for detail toggle

---

## Test Strategy

### Unit Tests (new file: `tests/test_nlp.py` or add to `tests/test_query.py`)

| Test Case | Input | Expected |
|-----------|-------|----------|
| detect_language with framework name | "autenticación JWT con FastAPI" | ["Python"] |
| detect_language with explicit name | "un buen ORM para Python" | ["Python"] |
| detect_language multiple languages | "FastAPI + React" | ["Python", "TypeScript"] |
| detect_language no match | "necesito un ORM" | [] |
| detect_language go vs golang | "scraping en Go" | ["Go"] |
| detect_speed fast | "búsqueda rápida de JWT" | "fast" |
| detect_speed thorough | "análisis exhaustivo de ORMs" | "thorough" |
| detect_speed default | "autenticación JWT" | "balanced" |

### TUI Integration Tests (add to `tests/test_tui.py`)

| Test | Scenario |
|------|----------|
| Smart input on mount | Verify single smart input exists, language input does not |
| Parse and preview | Type "jwt Python", press Enter, verify preview shows query + language |
| Confirm and search | Preview visible → press Enter → verify `_run_search` called with correct params |
| Re-parse on edit | Preview visible → edit input → Enter → new preview |
| No language fallback | Input with no language hint → preview shows warning/empty language |
| LoadingIndicator | During search → spinner visible; after search → spinner hidden |
| Edge: empty input | Press Enter with empty → error message stays, no search |

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Scope creep**: adding too much NLP (stemming, NER, etc.) | Medium | Hard rule: no external AI APIs, no new deps. Keep keyword-based. |
| **TUI complexity**: preview/edit flow adds state machine | Medium | Keep it simple: only two states (input mode, preview mode). Single input always editable. |
| **Test flakiness**: async worker + Pilot race conditions | Low | Already using `pilot.pause()`. Add more granular `await pilot.pause()` after each action. |
| **False positives** in language detection | Low | Keywords are well-known framework/language names. False positives in natural language are unlikely. |
| **Edge case**: user types very short query ("python") | Low | detect_language returns ["Python"], query is "python" — `extract_keywords()` handles it. |
| **Edge case**: user types only language name | Low | Treat as query. Search will find top Python repos generally. |
| **BREAKING**: existing tests reference `#query-input` and `#language-input` | Low | Update test selectors. Both inputs are replaced by `#smart-input`. |

---

## Ready for Proposal

**Yes**. The exploration is complete. All code paths have been read and analyzed. The approach is clear:
1. Add `detect_language()` and `detect_speed()` to `query.py` (keyword-based)
2. Collapse TUI to single smart input with preview panel
3. Add `LoadingIndicator` for search progress
4. Update tests for new widget tree and NLP functions

Approach 1 (keyword-based smart parse) is the clear winner: zero new dependencies, deterministic, testable, and aligned with the project's existing simple-keyword philosophy. The orchestrator can proceed directly to `sdd-propose`, `sdd-spec`, `sdd-design`, and `sdd-tasks`.

### Input Contract for Next Phases

- `change_name`: `tui-nlp-smart-input`
- `approach`: keyword-based smart parse (Approach 1)
- `affected_modules`: `src/sift/tui.py`, `src/sift/query.py`, `tests/test_tui.py`, `tests/test_query.py`
- `new_dependencies`: none
- `external_APIs`: none
- `test_framework`: pytest + pytest-asyncio + Textual Pilot
