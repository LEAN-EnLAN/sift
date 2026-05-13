"""Scoring v2 HTML report generator.

Self-contained report that documents old vs new retrieval and scoring logic,
benchmark evidence, local-only scope, and tradeoffs/limitations.

Usage:
    from sift.scoring.report import BenchmarkCase, render_html_report

    benchmarks = [
        BenchmarkCase(query="JWT auth python", language="Python",
                       old_top5=["owner/a", "owner/b"],
                       new_top5=["jpadilla/pyjwt", "owner/b"],
                       notes="pyjwt now ranks first due to authority boost"),
    ]
    html = render_html_report(benchmarks)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkCase:
    """A single benchmark example comparing v1 and v2 ranking results.

    Attributes:
        query: The natural-language query used.
        language: Programming language filter (or None).
        old_top5: Repository full_names from the v1 pipeline run.
        new_top5: Repository full_names from the v2 pipeline run.
        notes: Human-readable explanation of what changed and why.
    """

    query: str
    language: str | None
    old_top5: list[str]
    new_top5: list[str]
    notes: str


# ── Report sections ──────────────────────────────────────────────────────────

_HEAD = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scoring v2 — Local Heuristics Report</title>
<style>
  :root {
    --accent: #22f5a7;
    --accent-strong: #0f9f6e;
    --bg: #08110f;
    --panel: #0f1b18;
    --panel-2: #12211e;
    --fg: #e7f7f2;
    --muted: #98b8b0;
    --border: #1f3a34;
    --code: #112823;
    --shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { background: radial-gradient(circle at top, #122320 0%, var(--bg) 58%); }
  body {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    background: transparent;
    color: var(--fg);
    line-height: 1.65;
    padding: 3rem 1.25rem 4rem;
    max-width: 1100px;
    margin: 0 auto;
  }
  h1 {
    font-size: clamp(2rem, 3vw, 2.8rem);
    margin-bottom: 0.35rem;
    color: var(--accent);
    letter-spacing: -0.03em;
  }
  h2 {
    font-size: 1.35rem;
    margin: 2.4rem 0 0.85rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.45rem;
    color: #d7fff1;
  }
  h3 {
    font-size: 1.05rem;
    margin: 1.25rem 0 0.55rem;
    color: #d1fced;
  }
  p, li { margin-bottom: 0.65rem; color: var(--fg); }
  ul, ol { padding-left: 1.5rem; margin-bottom: 1rem; }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0 1.5rem;
    background: rgba(15, 27, 24, 0.88);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: var(--shadow);
  }
  th, td {
    text-align: left;
    vertical-align: top;
    padding: 0.7rem 0.8rem;
    border: 1px solid rgba(31, 58, 52, 0.85);
  }
  th {
    background: rgba(34, 245, 167, 0.12);
    color: #dffff5;
    font-weight: 700;
  }
  tr:hover td { background: rgba(34, 245, 167, 0.04); }
  code {
    background: var(--code);
    color: #baffea;
    padding: 0.14rem 0.34rem;
    border-radius: 6px;
    font-size: 0.9em;
  }
  .badge {
    display: inline-block;
    padding: 0.16rem 0.52rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    border: 1px solid transparent;
  }
  .badge-good { background: rgba(34, 245, 167, 0.16); color: #96ffd6; border-color: rgba(34, 245, 167, 0.2); }
  .badge-warn { background: rgba(251, 191, 36, 0.14); color: #fde68a; border-color: rgba(251, 191, 36, 0.16); }
  .badge-neutral { background: rgba(148, 163, 184, 0.14); color: #cbd5e1; border-color: rgba(148, 163, 184, 0.16); }
  .score-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.85rem;
    margin: 1rem 0 1.25rem;
  }
  .score-card {
    background: linear-gradient(180deg, rgba(18, 33, 30, 0.98) 0%, rgba(11, 20, 18, 0.98) 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.95rem;
    box-shadow: var(--shadow);
  }
  .score-card h4 { font-size: 0.9rem; color: var(--accent); margin-bottom: 0.3rem; }
  .score-card p { font-size: 1.4rem; font-weight: 800; }
  .flow-diagram {
    background: linear-gradient(180deg, rgba(18, 33, 30, 0.98) 0%, rgba(11, 20, 18, 0.98) 100%);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem;
    margin: 1rem 0 1.5rem;
    font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
    white-space: pre;
    overflow-x: auto;
    color: #d3fff1;
    box-shadow: var(--shadow);
  }
  .footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    font-size: 0.88rem;
    color: var(--muted);
  }
  @media (max-width: 720px) {
    body { padding: 2rem 0.9rem 3rem; }
    table { display: block; overflow-x: auto; }
  }
</style>
</head>
<body>
"""

_FOOT = """\
<div class="footer">
  <p>Generado por <code>sift.scoring.report.render_html_report()</code> — Deterministic, no external dependencies.</p>
  <p>Zafirus — RepoScout &bull; Scoring v2 Local Heuristics Report</p>
</div>
</body>
</html>
"""


def _render_benchmark_table(benchmarks: list[BenchmarkCase]) -> str:
    if not benchmarks:
        return "<p>No hay benchmarks disponibles.</p>"

    rows: list[str] = []
    for b in benchmarks:
        old_str = "; ".join(b.old_top5) if b.old_top5 else "<em>(vacio)</em>"
        new_str = "; ".join(b.new_top5) if b.new_top5 else "<em>(vacio)</em>"
        lang_str = b.language or "—"
        rows.append(f"<tr><td><code>{b.query}</code></td><td>{lang_str}</td><td>{old_str}</td><td>{new_str}</td><td>{b.notes}</td></tr>")

    return f"""\
<table>
<thead><tr><th>Query</th><th>Lenguaje</th><th>v1 (old) Top-5</th><th>v2 (new) Top-5</th><th>Notas</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>"""


def render_html_report(benchmarks: list[BenchmarkCase]) -> str:
    """Generate a self-contained HTML report for the scoring v2 changes.

    Args:
        benchmarks: List of BenchmarkCase examples comparing v1 vs v2 results.

    Returns:
        A complete HTML document as a string.
    """
    sections: list[str] = []

    # ── Header ──
    sections.append(_HEAD)
    sections.append("<h1>Scoring v2 — Local Heuristics Report</h1>")
    sections.append("<p style='color:#64748b;'>RepoScout &bull; Deterministic ranking rewrite &bull; Zafirus</p>")

    # ── 1. Problem Statement ──
    sections.append("<h2>1. Problem Statement</h2>")
    sections.append("<p>")
    sections.append("  The original scoring pipeline (<strong>v1</strong>) used a monolithic <code>score_repo()</code> ")
    sections.append("  function that combined relevance, activity, and popularity into a single weighted score. ")
    sections.append("  While functional, it had several limitations:")
    sections.append("</p>")
    sections.append("<ul>")
    sections.append("  <li><strong>Flat retrieval:</strong> queries were expanded generically without understanding the user's domain intent (PDF, JWT, ORM, etc.)</li>")
    sections.append("  <li><strong>No lexical traps:</strong> generic action words like 'editor' for PDF searches widened results to text-editor tools instead of PDF libraries</li>")
    sections.append("  <li><strong>No seed injection:</strong> known ecosystem libraries were not explicitly promoted in search variants</li>")
    sections.append("  <li><strong>Monolithic scoring:</strong> a single 5-factor weighted formula mixed relevance, activity, popularity, docs, and maintenance without separation of concerns</li>")
    sections.append("  <li><strong>No penalties:</strong> awesome-lists, toy projects, and forks received no demerit, letting them outrank production libraries</li>")
    sections.append("  <li><strong>No authority signal:</strong> canonical ecosystem libraries (e.g., PyMuPDF for PDF, pyjwt for JWT) received no special recognition</li>")
    sections.append("</ul>")
    sections.append("<p>")
    sections.append("  <strong>Scoring v2</strong> addresses all six limitations with a deterministic, local-only pipeline that requires no cloud APIs, LLMs, or vector search.")
    sections.append("</p>")

    # ── 2. Retrieval Comparison: Old vs New ──
    sections.append("<h2>2. Retrieval Logic: v1 vs v2</h2>")

    sections.append("<h3>v1 (original)</h3>")
    sections.append("<ul>")
    sections.append("  <li>Keyword extraction with Spanish-to-English expansion</li>")
    sections.append("  <li>Up to 8 generic search variants: broad keyword matches</li>")
    sections.append("  <li>No domain classification, no lexical trap filtering, no seed injection</li>")
    sections.append("  <li>Variants differ only in keyword ordering and qualifier combinations</li>")
    sections.append("</ul>")

    sections.append("<h3>v2 (local heuristics)</h3>")
    sections.append("<ul>")
    sections.append("  <li><strong>Domain classification</strong> (<code>classify_domain()</code>): detects intent (pdf, jwt-auth, orm, boilerplate, auth, scraping, cli, testing, cache, logging, serialization) from extracted keywords</li>")
    sections.append("  <li><strong>Lexical trap filtering</strong> (<code>_apply_lexical_traps()</code>): removes generic action words that cause false positives (e.g., 'editor' in PDF domain)</li>")
    sections.append("  <li><strong>Seed injection</strong> (<code>_inject_seeds()</code>): hardcoded, per-domain ecosystem seeds (e.g., pymupdf, pypdf for PDF) are injected into search variants</li>")
    sections.append("  <li>Max <strong>5 variants</strong> (down from 8 in v1) — each variant is sharper and more intent-specific</li>")
    sections.append("  <li>Variant types: seed-forward, domain-in-field, keyword-broad, topic-targeted, fallback</li>")
    sections.append("</ul>")

    sections.append("<h3>Retrieval comparison summary</h3>")
    sections.append("<table><thead><tr><th>Aspect</th><th>v1</th><th>v2</th></tr></thead><tbody>")
    sections.append("<tr><td>Max variants</td><td>8</td><td>5</td></tr>")
    sections.append("<tr><td>Domain intent</td><td>None</td><td><code>classify_domain()</code> from keyword triggers</td></tr>")
    sections.append("<tr><td>Lexical traps</td><td>None</td><td>Per-domain trap sets filter generic action words</td></tr>")
    sections.append("<tr><td>Seed injection</td><td>None</td><td>Hardcoded per-domain ecosystem seeds in variants</td></tr>")
    sections.append("<tr><td>Language detection</td><td><code>detect_language()</code></td><td>Same (unchanged)</td></tr>")
    sections.append("<tr><td>Spanish expansion</td><td><code>SPANISH_TO_ENGLISH</code> map</td><td>Same (unchanged)</td></tr>")
    sections.append("</tbody></table>")

    # ── 3. Scoring Comparison: Old vs New ──
    sections.append("<h2>3. Scoring Logic: v1 vs v2</h2>")

    sections.append("<h3>v1 (original)</h3>")
    sections.append("<ul>")
    sections.append("  <li><code>score_repo()</code>: single 5-factor weighted formula</li>")
    sections.append("  <li><code>score = 100 × (0.35×relevance + 0.25×activity + 0.20×popularity + 0.10×docs + 0.10×maintenance)</code></li>")
    sections.append("  <li>Final score adjusted by <code>× (0.65 + 0.35×relevance)</code></li>")
    sections.append("  <li><code>score_parts</code>: relevance, activity, community, docs, maintenance</li>")
    sections.append("  <li>No penalties, no authority signal, no modernity signal</li>")
    sections.append("</ul>")

    sections.append("<h3>v2 (9-stage pipeline)</h3>")
    sections.append("<ul>")
    sections.append("  <li><strong>Stage 1 — Eligibility</strong> (<code>stage_eligibility</code>): archived, empty forks, and no-metadata repos are disqualified early</li>")
    sections.append("  <li><strong>Stage 2 — Relevance</strong> (<code>stage_relevance</code>): keyword matching in name/desc/topics/README + domain boost</li>")
    sections.append("  <li><strong>Stage 3 — Maintenance</strong> (<code>stage_maintenance</code>): recency (last commit), issue pressure, license quality, fork penalty</li>")
    sections.append("  <li><strong>Stage 4 — Modernity</strong> (<code>stage_modernity</code>): age since creation (10-year graduated decay) — NEW</li>")
    sections.append("  <li><strong>Stage 5 — Documentation</strong> (<code>stage_docs</code>): README length, section coverage, code examples, badges</li>")
    sections.append("  <li><strong>Stage 6 — Community</strong> (<code>stage_community</code>): log-scale stars/forks/watchers</li>")
    sections.append("  <li><strong>Stage 7 — Authority</strong> (<code>stage_authority</code>): canonical repo matching per domain — NEW</li>")
    sections.append("  <li><strong>Stage 8 — Penalties</strong> (<code>stage_penalties</code>): awesome-list (+10), toy/demo (+8), high issue ratio (+5), fork (+3), capped 25 — NEW</li>")
    sections.append("  <li><strong>Stage 9 — Composite</strong> (<code>stage_composite</code>): weighted sum (relevance 0.30, maintenance 0.20, docs 0.15, community 0.15, modernity 0.10, authority 0.10) minus penalty, clamped 0-100</li>")
    sections.append("</ul>")

    sections.append("<h3>Pipeline flow</h3>")
    sections.append('<div class="flow-diagram">')
    sections.append("Natural Query")
    sections.append("  │")
    sections.append("  ▼")
    sections.append("┌─────────────────┐")
    sections.append("│  classify_domain │")
    sections.append("│  lexical traps   │")
    sections.append("│  seed injection  │")
    sections.append("│  3-5 variants    │")
    sections.append("└────────┬────────┘")
    sections.append("         │ variants")
    sections.append("         ▼")
    sections.append("┌─────────────────┐")
    sections.append("│  GitHub Search   │")
    sections.append("└────────┬────────┘")
    sections.append("         │ candidates")
    sections.append("         ▼")
    sections.append("┌──────────────────────────────────────┐")
    sections.append("│  1. Eligibility  (gate)              │")
    sections.append("│  2. Relevance    (keyword match)     │")
    sections.append("│  3. Maintenance  (recency/issues)    │")
    sections.append("│  4. Modernity    (creation age)      │")
    sections.append("│  5. Docs         (README quality)    │")
    sections.append("│  6. Community    (stars/forks)       │")
    sections.append("│  7. Authority    (canonical match)   │")
    sections.append("│  8. Penalties    (awesome/toy/fork)  │")
    sections.append("│  9. Composite    (weighted sum)      │")
    sections.append("└──────────────────────────────────────┘")
    sections.append("         │ scored candidates")
    sections.append("         ▼")
    sections.append("┌─────────────────┐")
    sections.append("│  shortlist_v2    │")
    sections.append("│  (top-N, sorted) │")
    sections.append("└─────────────────┘")
    sections.append("</div>")

    sections.append("<h3>Score parts comparison</h3>")
    sections.append("<table><thead><tr><th>Key</th><th>v1</th><th>v2</th><th>Notes</th></tr></thead><tbody>")
    sections.append("<tr><td><code>relevance</code></td><td>✅</td><td>✅</td><td>Same semantics, domain boost added</td></tr>")
    sections.append("<tr><td><code>activity</code></td><td>✅</td><td>➖</td><td>Removed; folded into maintenance</td></tr>")
    sections.append("<tr><td><code>maintenance</code></td><td>✅</td><td>✅</td><td>Now includes recency + fork penalty</td></tr>")
    sections.append("<tr><td><code>community</code></td><td>✅</td><td>✅</td><td>Log-scale stars/forks/watchers</td></tr>")
    sections.append("<tr><td><code>docs</code></td><td>✅</td><td>✅</td><td>Extended README checklist (11 sections)</td></tr>")
    sections.append("<tr><td><code>modernity</code></td><td>❌</td><td>✅</td><td><strong>New</strong> — creation-age decay</td></tr>")
    sections.append("<tr><td><code>authority</code></td><td>❌</td><td>✅</td><td><strong>New</strong> — canonical repo per domain</td></tr>")
    sections.append("<tr><td><code>penalties</code></td><td>❌</td><td>✅</td><td><strong>New</strong> — subtractive 0-25 scalar</td></tr>")
    sections.append("</tbody></table>")

    # ── 4. Local-Only Scope ──
    sections.append("<h2>4. Local-Only Scope</h2>")
    sections.append("<p>Scoring v2 operates entirely with <strong>local heuristics</strong>. No external services are used beyond the standard GitHub API calls that v1 already made:</p>")
    sections.append("<ul>")
    sections.append("  <li><span class='badge badge-good'>✅</span> <strong>Domain seeds:</strong> hardcoded Python dicts in <code>seeds.py</code></li>")
    sections.append("  <li><span class='badge badge-good'>✅</span> <strong>Lexical traps:</strong> hardcoded per-domain sets in <code>seeds.py</code></li>")
    sections.append("  <li><span class='badge badge-good'>✅</span> <strong>Canonical repos:</strong> hardcoded set of known ecosystem projects</li>")
    sections.append("  <li><span class='badge badge-good'>✅</span> <strong>Scoring pipeline:</strong> pure Python functions, no I/O, no caching</li>")
    sections.append("  <li><span class='badge badge-warn'>⚠️</span> <strong>GitHub Search API:</strong> still required for candidate retrieval (unchanged from v1)</li>")
    sections.append("</ul>")
    sections.append("<p><strong>Excluded features</strong> (not in scope for this report):</p>")
    sections.append("<ul>")
    sections.append("  <li><span class='badge badge-neutral'>❌</span> Cloud-based AI / LLM query understanding</li>")
    sections.append("  <li><span class='badge badge-neutral'>❌</span> Vector search or embedding-based similarity</li>")
    sections.append("  <li><span class='badge badge-neutral'>❌</span> External API calls for enrichment (beyond GitHub Search)</li>")
    sections.append("  <li><span class='badge badge-neutral'>❌</span> Download counts, dependents count, or package registry data</li>")
    sections.append("  <li><span class='badge badge-neutral'>❌</span> Machine learning model inference</li>")
    sections.append("</ul>")

    # ── 5. Benchmark Evidence ──
    sections.append("<h2>5. Benchmark Examples</h2>")
    sections.append("<p>")
    sections.append("  The following benchmarks compare v1 and v2 ranking output for representative queries. ")
    sections.append("  Each case shows the top-5 results from each pipeline and explains the differences.")
    sections.append("</p>")

    sections.append(_render_benchmark_table(benchmarks))

    sections.append("<h3>What improved</h3>")
    sections.append("<ul>")
    sections.append("  <li><strong>JWT/auth queries:</strong> canonical <code>jpadilla/pyjwt</code> now ranks at or near the top, boosted by domain-aware authority scoring</li>")
    sections.append("  <li><strong>PDF processing:</strong> <code>pymupdf/PyMuPDF</code> and <code>py-pdf/pypdf</code> are promoted; generic text-editor tools (from lexical trap 'editor') are demoted</li>")
    sections.append("  <li><strong>Boilerplate queries:</strong> <code>cookiecutter/cookiecutter</code> ranks higher; generic 'framework' repos are penalized</li>")
    sections.append("  <li><strong>ORM queries:</strong> <code>sqlalchemy/sqlalchemy</code> receives authority boost matching canonical set</li>")
    sections.append("  <li><strong>Scraping queries:</strong> <code>scrapy/scrapy</code> recognized as canonical; 'framework' lexical trap filters noise</li>")
    sections.append("  <li><strong>Cache queries:</strong> <code>redis/redis-py</code> recognized as canonical</li>")
    sections.append("</ul>")

    # ── 6. Tradeoffs and Limitations ──
    sections.append("<h2>6. Tradeoffs and Limitations</h2>")
    sections.append("<ul>")
    sections.append("  <li><strong>Domain coverage:</strong> currently 11 domains (pdf, jwt-auth, auth, orm, boilerplate, scraping, cli, testing, cache, logging, serialization). Adding new domains requires updating <code>DOMAIN_SEEDS</code>, <code>LEXICAL_TRAPS</code>, <code>CANONICAL_REPOS</code>, and <code>_DOMAIN_TRIGGER_SETS</code> — no runtime learning.</li>")
    sections.append("  <li><strong>Domain detection precision:</strong> uses simple keyword-trigger counting. A query mentioning 'jwt' and 'pdf' equally may misclassify; tie-breaking prefers jwt-auth over auth but cannot resolve unrelated domain ties.</li>")
    sections.append("  <li><strong>English-first bias:</strong> <code>SPANISH_TO_ENGLISH</code> expansion supports Spanish queries. Other languages have no equivalent mapping.</li>")
    sections.append("  <li><strong>Static canonical set:</strong> <code>CANONICAL_REPOS</code> is a manually curated set. New or emerging libraries not in this set receive no authority boost regardless of quality.</li>")
    sections.append("  <li><strong>Penalty thresholds:</strong> awesome-list, toy/demo, issue-ratio, and fork penalties use fixed thresholds. Edge cases near boundaries may produce surprising scores.</li>")
    sections.append("  <li><strong>No activity signal in v2 score_parts:</strong> v1's <code>activity</code> key is removed. Rendering code uses <code>.get('activity', score_parts.get('maintenance', 0))</code> for one release cycle, but consumers relying directly on <code>activity</code> will see fallback values.</li>")
    sections.append("  <li><strong>Report is static:</strong> the HTML is generated once and committed. It does not auto-update with new benchmarks or algorithm changes.</li>")
    sections.append("</ul>")

    sections.append("<h3>Rollback</h3>")
    sections.append("<p>")
    sections.append("  Set <code>SIFT_SCORING_V2=0</code> to restore the original v1 pipeline. The v1 <code>_score_repo_v1()</code> and <code>_build_reasons_v1()</code> functions are preserved as private fallbacks. ")
    sections.append("  A git tag <code>pre-scoring-v2</code> is cut before the merge for quick rollback.")
    sections.append("</p>")

    # ── Footer ──
    sections.append(_FOOT)

    return "\n".join(sections)
