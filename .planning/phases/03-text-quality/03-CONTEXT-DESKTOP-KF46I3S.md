# Phase 3: Text Quality - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 3 P0 text quality bugs: (1) generated text copies source verbatim instead of rewriting, (2) competitor brand names appear in output, (3) fabricated data passes silently when claim extraction returns 0 claims.

**Root cause hierarchy (confirmed by code analysis):**
1. **COPY**: Raw `texto_base` injected directly at `llm_service.py:1718` — no extraction/abstraction layer. Prompt says "reescreva o texto acima" but LLM has full source available to copy.
2. **COMPETITORS**: Zero competitor filtering logic exists anywhere in the pipeline — no prompt instruction, no post-scan.
3. **SILENT PASS**: `fact_check_service.py:1239-1241` — 0 claims extracted → logs warning + `claim_extraction_failed = True` → article auto-passes with reduced confidence (~0.35). No retry, no manual review flag.
4. **QUALITY LOOP BLIND**: `evaluate_quality_criteria()` at `generation_api.py:414-545` has 7 criteria but none for text similarity — a 90% verbatim copy passes all gates.

**2 parallel implementation tracks:**
- Track A (Pipeline Agent): Extract-then-generate step, competitor filtering, anti-copy few-shot examples (llm_service.py, config.py)
- Track B (Safety Agent): N-gram overlap detection, fix silent claim extraction failure (fact_check_service.py, generation_api.py)

</domain>

<decisions>
## Implementation Decisions

### Extraction Strategy (Task 3.1)
- **D-01:** Add Haiku fact extraction step BEFORE building generation prompt. Call Claude Haiku to extract ONLY factual claims/entities from source text. Build generation prompt from extracted facts, NOT raw source text.
- **D-02:** Extraction prompt instruction: "Extraia APENAS fatos verificados, entidades, numeros, datas e citacoes diretas. NAO inclua frases completas do texto original."
- **D-03:** Keep raw `texto_base` in prompt wrapped in `<source-text>` tags for reference context, but add explicit instruction: "Escreva baseado APENAS nos fatos extraidos. NAO copie frases do material em <source-text>."
- **D-04:** Cost impact: ~$0.001/article (Haiku extraction). Acceptable for production.
- **D-05:** Insert extraction step at `llm_service.py` BEFORE the `_build_user_prompt()` call. The extracted facts become a new parameter passed to the prompt builder.

### N-gram Overlap Detection (Task 3.2)
- **D-06:** New function `check_originality(generated, source, n=4, threshold=0.15)` in `llm_service.py` — keeps detection close to generation, avoids bloating fact_check_service.py further.
- **D-07:** Threshold: >15% 4-gram overlap = "high_copy". Pure Python implementation (word-level n-grams, no external library).
- **D-08:** Normalize both texts before comparison: lowercase, remove punctuation, collapse whitespace. Portuguese stop words are NOT removed (they're part of copied phrases).
- **D-09:** New "text_copy" criterion in `evaluate_quality_criteria()` at `generation_api.py`. Triggers regeneration with stronger anti-copy instructions when overlap exceeds threshold.
- **D-10:** Quality loop instruction for text_copy failure: "URGENTE - COPIA DETECTADA. {overlap_ratio}% das frases sao identicas ao material-fonte. REESCREVA COMPLETAMENTE usando suas proprias palavras. NAO copie NENHUMA frase do material original."

### Competitor Brand Filtering (Task 3.3)
- **D-11:** New `COMPETITOR_BRANDS` env var in `config.py` (comma-separated list). Editorial team maintains the list without deploy.
- **D-12:** Default list (if env var unset): empty — no filtering unless editorial configures it.
- **D-13:** Dual enforcement: (a) Prompt instruction in system prompt: "NAO mencione estes veiculos pelo nome: [lista]. Use 'segundo apuracao' ou 'de acordo com fontes'." (b) Post-generation regex scan: find brand names in output, log warning but do NOT auto-replace (editorial must review replacements).
- **D-14:** Post-generation scan returns list of found competitor mentions. Added to generation audit trail for editorial review.

### Claim Extraction Failure Recovery (Task 3.4)
- **D-15:** When claim extraction returns 0 claims: retry ONCE with simplified prompt ("Liste 5 afirmacoes factuais neste texto:").
- **D-16:** If still 0 after retry: set `needs_manual_review = True` and `review_reasons.append("Extracao de claims falhou - verificacao manual necessaria")`. Do NOT auto-pass with 0.35 confidence.
- **D-17:** Article still proceeds through pipeline (not hard-blocked) but publication status is set to `review` instead of `published`.
- **D-18:** Log at WARNING level with article ID for operational monitoring.

### Anti-Copy Few-Shot Examples (Task 3.5)
- **D-19:** New `ANTI_COPIA` constant in `llm_service.py` (separate from FIDELIDADE_FACTUAL). 2 BAD examples labeled "INACEITAVEL" + 2 GOOD examples labeled "CORRETO". All in Portuguese.
- **D-20:** Inject ANTI_COPIA into system prompt via `get_system_prompt()` — NOT in user prompt (keeps user prompt focused on the actual content).
- **D-21:** Hard rule in prompt: "Nunca use mais de 3 palavras consecutivas do material fonte, exceto nomes proprios e citacoes entre aspas."
- **D-22:** Examples must show the transformation clearly: source sentence → BAD (copied) vs GOOD (rewritten with same facts).

### Claude's Discretion
- Exact wording of Haiku extraction prompt (D-02) — optimize through testing
- Whether to use word-level or character-level n-grams (D-07 says word-level, but Claude can adjust if testing shows better results)
- Number of claims in simplified retry prompt (D-15 says 5, adjustable)
- Exact BAD/GOOD examples for ANTI_COPIA (D-19) — Claude writes these based on real TMC source material patterns

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Plan
- `docs/plans/2026-04-01-p0-implementation-plan.md` §Phase 3 — Full task breakdown with line numbers, verification checklist, parallel track structure

### Backlog
- `docs/backlog-prioritizado-abril-2026.md` — P0 Qualidade section: copied text, competitor mentions, fabricated data

### Backend — Generation Pipeline (Track A primary files)
- `FeedRSS/tmc-rss-collector/services/llm_service.py:1387-1410` — `get_system_prompt()` function — where competitor filter instructions and ANTI_COPIA injection go
- `FeedRSS/tmc-rss-collector/services/llm_service.py:1697-1760` — `_build_user_prompt()` — where raw `texto_base` is injected; extraction step goes BEFORE this
- `FeedRSS/tmc-rss-collector/services/llm_service.py:146-186` — FIDELIDADE_FACTUAL/CURTA/MEDIA constants — adjacent to new ANTI_COPIA constant
- `FeedRSS/tmc-rss-collector/services/config.py` — AppConfig dataclass, env var loading — where COMPETITOR_BRANDS goes

### Backend — Safety Pipeline (Track B primary files)
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:1225-1255` — Claim extraction result handling — where 0-claims retry logic goes
- `FeedRSS/tmc-rss-collector/functions/generation_api.py:414-547` — `evaluate_quality_criteria()` — where new text_copy criterion goes
- `FeedRSS/tmc-rss-collector/functions/generation_api.py:550-580` — `build_corrective_instructions()` — where text_copy corrective prompt goes

### Prior Phase Context
- `.planning/phases/01-session-persistence/01-CONTEXT.md` — Surgical edit discipline established
- `.planning/phases/02-search-filter-performance/02-CONTEXT.md` — Env var pattern for editorial config (D-11 follows same pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FIDELIDADE_FACTUAL` constant at `llm_service.py:150` — established pattern for prompt constants; ANTI_COPIA follows same structure
- `get_system_prompt()` at `llm_service.py:1387` — already accepts `source_len`, `has_enrichment` params; easy to add competitor list injection
- `evaluate_quality_criteria()` at `generation_api.py:414` — 7 existing criteria with standard structure `{criterion, detail, instruction}`; text_copy criterion follows same pattern
- `build_corrective_instructions()` at `generation_api.py:550` — already builds regen prompts from failure list; will auto-handle text_copy failures
- `_get_config()` singleton at `config.py` — standard pattern for env var access; COMPETITOR_BRANDS integrates here
- `claim_extraction_failed` flag at `fact_check_service.py:1241` — already exists, just needs behavioral change

### Established Patterns
- Prompt constants: SCREAMING_SNAKE_CASE strings at top of `llm_service.py` (e.g., FIDELIDADE_FACTUAL, FIDELIDADE_CURTA)
- Quality criteria: dict with `criterion`, `detail`, `instruction` keys; `instruction` is injected into regen prompt
- Config: env vars loaded in `AppConfig.__init__()`, accessed via `get_config().attribute`
- LLM calls: `await self._call_claude(prompt, model="haiku")` pattern for cheap classification/extraction tasks
- Error handling: `logger.warning()` + metadata flags for soft failures; `logger.error()` for hard failures

### Integration Points
- Extraction step: Must happen BEFORE `_build_user_prompt()` is called in the main generation flow
- N-gram check: Must happen AFTER generation returns text, BEFORE quality loop evaluation
- Competitor scan: Must happen AFTER generation returns text, results added to audit trail
- Claim retry: Changes are isolated to `fact_check_service.py` claim extraction section
- Quality loop: `evaluate_quality_criteria()` is called by `_quality_loop()` in generation_api.py — adding a criterion is additive

</code_context>

<specifics>
## Specific Ideas

- The extraction step (D-01) should use the SAME `_call_claude()` method already in llm_service.py — no new API client needed
- N-gram check (D-06) is pure Python — no pip dependency needed. Implementation from the plan is correct
- COMPETITOR_BRANDS env var must handle empty/unset gracefully — skip filtering when list is empty
- The claim retry (D-15) must not double-count API tokens in `llm_usage_log` — log both attempts separately
- Track A (llm_service.py) and Track B (fact_check_service.py + generation_api.py) edit DIFFERENT files — safe for parallel execution with no merge conflicts
- The only shared concern: n-gram function (D-06) is in llm_service.py but called from generation_api.py — Track B needs to import it

</specifics>

<deferred>
## Deferred Ideas

- **WhatsApp CTA removal**: Backlog P1 item "Retirar CTA WhatsApp" — related to text quality but different concern (template content, not generation logic). Belongs in separate P1 cleanup.
- **Opinion mode for entertainment**: Backlog P2 item — would need quality threshold adjustments but is a feature, not a bug fix.

</deferred>

---

*Phase: 03-text-quality*
*Context gathered: 2026-04-01*
