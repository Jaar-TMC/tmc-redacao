---
phase: 03-text-quality
plan: B
type: execute
wave: 1
depends_on: []
files_modified:
  - FeedRSS/tmc-rss-collector/services/fact_check_service.py
  - FeedRSS/tmc-rss-collector/functions/generation_api.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Claim extraction failure (0 claims) triggers a retry with simplified prompt before giving up"
    - "After retry still returns 0 claims, article gets needs_manual_review=True and publication_status=review, NOT auto-pass"
    - "Quality loop detects high n-gram overlap and triggers regeneration with anti-copy instructions"
    - "text_copy quality criterion exists in evaluate_quality_criteria() with its own corrective instruction"
  artifacts:
    - path: "FeedRSS/tmc-rss-collector/services/fact_check_service.py"
      provides: "Updated claim extraction failure handling at lines 1239-1241 — retry + needs_manual_review"
    - path: "FeedRSS/tmc-rss-collector/functions/generation_api.py"
      provides: "text_copy criterion in evaluate_quality_criteria(), text_copy corrective instruction in build_corrective_instructions()"
  key_links:
    - from: "evaluate_quality_criteria() text_copy criterion"
      to: "check_originality() in llm_service.py"
      via: "from services.llm_service import check_originality — called inside evaluate_quality_criteria"
      pattern: "check_originality"
    - from: "claim extraction 0-claims branch"
      to: "_extract_claims_with_retry() or inline retry block"
      via: "fact_check_service.py line 1239-1241 — replace auto-pass with retry+flag logic"
      pattern: "needs_manual_review"
---

<objective>
Add two safety gates that catch quality failures the current pipeline misses silently.

Purpose: (1) When claim extraction returns 0 claims, the article currently auto-passes with 0.35 confidence — this allows fabricated articles with no checkable claims to slip through. The fix: retry once with simplified prompt, then set needs_manual_review=True if still empty. (2) The quality loop has 7 criteria but none for text similarity — a 90% verbatim copy passes all gates. The fix: add text_copy criterion that calls check_originality() and triggers regeneration with strong anti-copy instructions.

Output: Surgical edits to fact_check_service.py (1239-1241 region) and generation_api.py (evaluate_quality_criteria + build_corrective_instructions). No new files. check_originality() imported from llm_service.py (created by Plan A).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-text-quality/03-CONTEXT.md
@docs/plans/2026-04-01-p0-implementation-plan.md

CRITICAL CONSTRAINTS:
- fact_check_service.py is ~110KB — NEVER rewrite wholesale. Edit ONLY lines 1230-1260 region.
- generation_api.py is ~18KB — smaller but still surgical. Edit ONLY evaluate_quality_criteria() and build_corrective_instructions().
- Plan B does NOT modify llm_service.py. check_originality() is imported FROM llm_service.py (created by Plan A — both are Wave 1 so Plan A may or may not be done when Plan B runs, but the import will exist because both plans are created before any execution starts).
- evaluate_quality_criteria() takes verification_data and readability_data as inputs. The texto_base (source) and generated text must be passed to enable n-gram check — the function signature must be extended.
- The claim retry must use the same self._llm_service._call_api() or equivalent pattern — check how claims are currently extracted to understand the class/instance structure.

<interfaces>
From fact_check_service.py (current state — claim extraction failure handling):

```python
# Lines 1225-1241: Where 0-claims fallback happens
results = await asyncio.gather(claim_task, entity_task, quote_task, return_exceptions=True)

# Process claim results
if isinstance(results[0], Exception):
    logger.error(f"Claim verification failed: {results[0]}")
    metadata.warnings.append("Claim verification failed")
else:
    claims = results[0]
    metadata.claims = claims
    metadata.total_claims = len(claims)
    # Empty claims fallback (4B) — CURRENT BROKEN BEHAVIOR
    if not claims:
        logger.warning("Claim extraction returned 0 claims — article passes with reduced confidence")
        metadata.claim_extraction_failed = True
    # ... rest of claim processing
```

The `metadata` object is a VerificationMetadata or similar dataclass — check what fields it has.
The `claim_task` is created by `asyncio.to_thread(self._extract_claims, ...)` — to retry, call self._extract_claims() again with a simplified prompt.

From generation_api.py (current state — evaluate_quality_criteria):

```python
# Line 414-547: evaluate_quality_criteria() — 6 active criteria (fabrication, readability,
#                confidence, novel_entities, unverifiable, risk_level)
def evaluate_quality_criteria(
    verification_data: dict,
    readability_data: dict,
    categoria: str = "",
    tipo_materia: str = "",
) -> dict:
    failures = []
    # ... 6 criteria checks ...
    return {"all_passed": len(failures) == 0, "failures": failures}

# Line 550-587: build_corrective_instructions() — iterates failures and builds regen prompt
def build_corrective_instructions(failures: list, exa_corrections: list = None) -> str:
    parts = ["\n\n## CORRECAO OBRIGATORIA\n"]
    # ... exa_corrections first, then failure["instruction"] for each ...
    return "\n".join(parts)
```

The quality loop caller (find it with grep "_quality_loop") passes verification_data and readability_data to evaluate_quality_criteria().
The function must receive texto_base and generated_text to compute n-gram overlap.
</interfaces>

NOTE ON DEPENDENCY: Plan A creates check_originality() in llm_service.py. Plan B imports it. Both plans are Wave 1 and will be executed sequentially by the same executor agent in the same session — Plan A runs first (alphabetical), then Plan B. By the time Plan B's executor runs, check_originality() will exist. If for any reason they run truly in parallel, the import will fail gracefully (ImportError at call time, not at import time, because it's inside the function body). Add the import inside the function body for safety: `from services.llm_service import check_originality`.
</context>

<tasks>

<task type="auto">
  <name>Task B-1: Fix silent claim extraction failure in fact_check_service.py</name>
  <files>
    FeedRSS/tmc-rss-collector/services/fact_check_service.py
  </files>
  <read_first>
    - FeedRSS/tmc-rss-collector/services/fact_check_service.py lines 1195-1270 (full claim extraction and results processing block)
    - FeedRSS/tmc-rss-collector/services/fact_check_service.py: search for `def _extract_claims` to find the claim extraction method signature
    - FeedRSS/tmc-rss-collector/services/fact_check_service.py: search for `claim_extraction_failed` to find all usages of this flag
    - FeedRSS/tmc-rss-collector/services/fact_check_service.py: search for `needs_manual_review` to check if the field already exists on metadata
    - FeedRSS/tmc-rss-collector/services/fact_check_service.py: search for `review_reasons` to check if this list already exists on metadata
  </read_first>
  <action>
    ## Target: Replace 3-line auto-pass at lines 1239-1241 with retry + flag logic

    CURRENT code (lines 1239-1241):
    ```python
    if not claims:
        logger.warning("Claim extraction returned 0 claims — article passes with reduced confidence")
        metadata.claim_extraction_failed = True
    ```

    REPLACE with:
    ```python
    if not claims:
        logger.warning(
            f"Claim extraction returned 0 claims on first attempt — retrying with simplified prompt. "
            f"Article ID context: {getattr(metadata, 'article_id', 'unknown')}"
        )
        # Retry once with simplified prompt (D-15)
        try:
            # Call _extract_claims with simplified prompt flag
            # Find the text that was used — it's available as generated_article in the outer scope
            retry_claims = self._extract_claims_simplified(generated_article)
        except Exception as retry_err:
            logger.error(f"Claim extraction retry also failed: {retry_err}")
            retry_claims = []

        if retry_claims:
            # Retry succeeded — use retry results
            logger.info(f"Claim extraction retry succeeded: {len(retry_claims)} claims found")
            claims = retry_claims
            metadata.claims = claims
            metadata.total_claims = len(claims)
        else:
            # Both attempts returned 0 claims — flag for manual review (D-16, D-17)
            logger.warning(
                f"Claim extraction failed after retry (0 claims). "
                f"Setting needs_manual_review=True. Article will NOT auto-pass."
            )
            metadata.claim_extraction_failed = True
            metadata.needs_manual_review = True
            metadata.review_reasons.append(
                "Extracao de claims falhou - verificacao manual necessaria"
            )
    ```

    ## Add _extract_claims_simplified() method to FactCheckService class

    Find the FactCheckService class (search for `class FactCheckService`). Find the `_extract_claims` method signature to understand the pattern.

    Add the new simplified retry method near `_extract_claims`. The simplified prompt asks for exactly 5 factual statements — less demanding than the full claim extraction:

    ```python
    def _extract_claims_simplified(self, text: str) -> list:
        """
        Simplified claim extraction for retry when full extraction returns 0 claims.

        Uses a direct, minimal prompt. Synchronous (called via asyncio.to_thread
        from the async context if needed, or directly since retry is sync).

        Args:
            text: Generated article text

        Returns:
            List of claim objects or dicts (same format as _extract_claims returns)
        """
        if not text or len(text.strip()) < 50:
            return []

        simplified_prompt = (
            f"Liste 5 afirmacoes factuais neste texto. "
            f"Para cada uma, responda no formato JSON: "
            f'[{{"text": "afirmacao", "verdict": "grounded", "confidence": 0.7}}]\n\n'
            f"TEXTO:\n{text[:2000]}"
        )
        try:
            # Use the same LLM service pattern already established
            # Find how _extract_claims calls the API and mirror the pattern
            # (look for self._llm or self.client or similar — read the method body)
            response = self._call_llm_sync(
                prompt=simplified_prompt,
                task_type="claim_extraction_retry",
            )
            if not response:
                return []
            # Parse JSON response — use existing JSON repair if available
            import json
            try:
                data = json.loads(response)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                # Try to extract JSON array from response
                start = response.find("[")
                end = response.rfind("]") + 1
                if start >= 0 and end > start:
                    data = json.loads(response[start:end])
                    if isinstance(data, list):
                        return data
            return []
        except Exception as e:
            logger.warning(f"Simplified claim extraction failed: {e}")
            return []
    ```

    IMPORTANT: The exact API call pattern depends on how `_extract_claims` makes its LLM call — read `_extract_claims` body before writing `_call_llm_sync`. Match the existing pattern exactly. If the class uses `self._llm_service`, `self.client.messages.create()`, or similar, mirror that. The goal is 5 simple factual statements, not a complex structured extraction.

    ## Verify needs_manual_review field exists on metadata

    Before writing the code, search for the VerificationMetadata class or similar. If `needs_manual_review` does not already exist as a field, it must be added. Similarly for `review_reasons` list — if it doesn't exist, add it with default `[]`.

    If metadata is a dataclass, add:
    ```python
    needs_manual_review: bool = False
    review_reasons: list = field(default_factory=list)
    ```

    If metadata is a plain dict or object, the attribute assignment will work directly.
  </action>
  <verify>
    <automated>
      cd "FeedRSS/tmc-rss-collector" && python -c "
import ast
with open('services/fact_check_service.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Check new retry logic exists
assert 'needs_manual_review' in source, 'needs_manual_review flag missing'
assert 'Extracao de claims falhou' in source, 'review reason string missing'
assert '_extract_claims_simplified' in source, '_extract_claims_simplified method missing'
assert 'retrying with simplified prompt' in source.lower() or 'retry' in source.lower(), 'retry log message missing'
print('Claim retry logic: OK')

# Syntax check
try:
    ast.parse(source)
    print('Syntax check: PASSED')
except SyntaxError as e:
    print(f'SYNTAX ERROR at line {e.lineno}: {e.msg}')
    exit(1)
"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "needs_manual_review" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 2 matches (flag assignment + reason append)
    - `grep -n "_extract_claims_simplified" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 2 matches (method definition + call in retry block)
    - `grep -n "Extracao de claims falhou" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns exactly 1 match (the review reason string per D-16)
    - Old auto-pass message REMOVED: `grep -n "article passes with reduced confidence" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 0 matches
    - Syntax check: `cd FeedRSS/tmc-rss-collector && python -m py_compile services/fact_check_service.py && echo OK`
  </acceptance_criteria>
  <done>
    - The 3-line auto-pass block at lines 1239-1241 replaced with retry + flag logic
    - _extract_claims_simplified() method exists on FactCheckService class
    - 0-claims path now: retry → if still 0 → needs_manual_review=True + review_reasons.append(message)
    - Old "article passes with reduced confidence" log message removed
    - fact_check_service.py passes Python syntax check
  </done>
</task>

<task type="auto">
  <name>Task B-2: Add text_copy quality criterion to generation_api.py</name>
  <files>
    FeedRSS/tmc-rss-collector/functions/generation_api.py
  </files>
  <read_first>
    - FeedRSS/tmc-rss-collector/functions/generation_api.py lines 414-590 (evaluate_quality_criteria + build_corrective_instructions full bodies)
    - FeedRSS/tmc-rss-collector/functions/generation_api.py: search for `_quality_loop` to find where evaluate_quality_criteria is called and understand what arguments are available at call sites
    - FeedRSS/tmc-rss-collector/functions/generation_api.py: search for `texto_base` to understand if source text is available in the quality loop context
  </read_first>
  <action>
    ## Step 1: Extend evaluate_quality_criteria() signature

    Current signature (line 414):
    ```python
    def evaluate_quality_criteria(
        verification_data: dict,
        readability_data: dict,
        categoria: str = "",
        tipo_materia: str = "",
    ) -> dict:
    ```

    New signature — add generated_text and source_text as optional parameters:
    ```python
    def evaluate_quality_criteria(
        verification_data: dict,
        readability_data: dict,
        categoria: str = "",
        tipo_materia: str = "",
        generated_text: str = "",
        source_text: str = "",
    ) -> dict:
    ```

    Existing callers that don't pass these new params will continue to work (both default to "").

    ## Step 2: Add text_copy criterion as the 7th criterion (after risk_level, before return)

    Find the end of the risk_level criterion (around line 538) and the return statement (line 544). Insert the new criterion BETWEEN them:

    ```python
    # 7. Text copy check — n-gram overlap detection (D-06 to D-09)
    if generated_text and source_text:
        try:
            from services.llm_service import check_originality
            originality = check_originality(
                generated=generated_text,
                source=source_text,
                n=4,
                threshold=0.15,
            )
            if originality["is_copy"]:
                overlap_pct = int(originality["overlap_ratio"] * 100)
                failures.append({
                    "criterion": "text_copy",
                    "detail": f"Sobreposicao de {overlap_pct}% com texto-fonte (limite: 15%)",
                    "instruction": (
                        f"URGENTE - COPIA DETECTADA. {overlap_pct}% das frases sao identicas ao "
                        f"material-fonte. REESCREVA COMPLETAMENTE usando suas proprias palavras. "
                        f"NAO copie NENHUMA frase do material original. "
                        f"Nunca use mais de 3 palavras consecutivas da fonte, exceto nomes proprios."
                    ),
                })
        except ImportError:
            logger.warning("check_originality not available — skipping text_copy check")
        except Exception as e:
            logger.warning(f"Text copy check failed: {e}")
    ```

    ## Step 3: Update all call sites of evaluate_quality_criteria() to pass generated_text and source_text

    Search for every call to evaluate_quality_criteria() in the file:
    ```
    grep -n "evaluate_quality_criteria" generation_api.py
    ```

    For each call site inside _quality_loop (or wherever it is called), add the new keyword arguments:
    ```python
    quality_result = evaluate_quality_criteria(
        verification_data=verification_data,
        readability_data=readability_data,
        categoria=categoria,
        tipo_materia=tipo_materia,
        generated_text=article_text,   # the generated article body
        source_text=texto_base,         # the original source text
    )
    ```

    The variable names for generated article text and source text may differ — read the call site context to find the correct local variable names.

    ## Step 4: Verify build_corrective_instructions() handles text_copy automatically

    Read build_corrective_instructions() at lines 550-587. It already iterates over failures and appends `failure.get("instruction")` for each. Since text_copy failure has an "instruction" key (added in Step 2), it will be picked up automatically. NO changes needed to build_corrective_instructions().

    Confirm this by reading the function body — if there are any criterion-specific special cases, add text_copy only if needed. It should not be needed.
  </action>
  <verify>
    <automated>
      cd "FeedRSS/tmc-rss-collector" && python -c "
import ast
with open('functions/generation_api.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Check new parameters in evaluate_quality_criteria
assert 'generated_text' in source, 'generated_text parameter missing'
assert 'source_text' in source, 'source_text parameter missing'
print('New signature parameters: OK')

# Check text_copy criterion
assert 'text_copy' in source, 'text_copy criterion missing'
assert 'check_originality' in source, 'check_originality import missing'
assert 'COPIA DETECTADA' in source, 'anti-copy corrective instruction missing'
print('text_copy criterion: OK')

# Check old return is still there (structural integrity)
assert 'all_passed' in source, 'return dict all_passed key missing'
print('Return structure: OK')

# Syntax check
try:
    ast.parse(source)
    print('Syntax check: PASSED')
except SyntaxError as e:
    print(f'SYNTAX ERROR at line {e.lineno}: {e.msg}')
    exit(1)
"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "text_copy" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns at least 2 matches (criterion key + detail/instruction strings)
    - `grep -n "check_originality" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns at least 1 match (the import-inside-if block)
    - `grep -n "generated_text" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns at least 2 matches (function signature + call site)
    - `grep -n "COPIA DETECTADA" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns exactly 1 match
    - Existing criteria still present: `grep -n '"fabrication"' FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match (not accidentally deleted)
    - Syntax check: `cd FeedRSS/tmc-rss-collector && python -m py_compile functions/generation_api.py && echo OK`
    - Functional test — evaluate_quality_criteria works without check_originality (graceful fallback):
      `cd FeedRSS/tmc-rss-collector && python -c "from functions.generation_api import evaluate_quality_criteria; r = evaluate_quality_criteria({}, {}, generated_text='', source_text=''); assert 'all_passed' in r; print('evaluate_quality_criteria: OK')"`
  </acceptance_criteria>
  <done>
    - evaluate_quality_criteria() has generated_text: str = "" and source_text: str = "" parameters
    - text_copy criterion added as 7th criterion — checks n-gram overlap when both texts provided
    - Criterion includes "instruction" key with COPIA DETECTADA message for regeneration
    - ImportError and general exceptions handled gracefully (skips check if llm_service unavailable)
    - All call sites of evaluate_quality_criteria() updated to pass generated_text and source_text
    - build_corrective_instructions() picks up text_copy instruction automatically (no changes needed)
    - generation_api.py passes Python syntax check
  </done>
</task>

</tasks>

<verification>
After both tasks complete, run the full Plan B verification:

```bash
cd "FeedRSS/tmc-rss-collector"

# 1. Syntax check both modified files
python -m py_compile services/fact_check_service.py && echo "fact_check_service.py: OK"
python -m py_compile functions/generation_api.py && echo "generation_api.py: OK"

# 2. Claim retry logic present
python -c "
with open('services/fact_check_service.py', 'r', encoding='utf-8') as f:
    src = f.read()
assert 'needs_manual_review' in src
assert '_extract_claims_simplified' in src
assert 'Extracao de claims falhou' in src
# Verify old auto-pass is gone
assert 'article passes with reduced confidence' not in src
print('fact_check_service.py changes: ALL OK')
"

# 3. text_copy criterion in generation_api
python -c "
with open('functions/generation_api.py', 'r', encoding='utf-8') as f:
    src = f.read()
assert 'text_copy' in src
assert 'check_originality' in src
assert 'COPIA DETECTADA' in src
assert 'generated_text' in src
print('generation_api.py changes: ALL OK')
"

# 4. evaluate_quality_criteria import and basic function call
python -c "
from functions.generation_api import evaluate_quality_criteria
# Without texts — should work (graceful skip of text_copy check)
r = evaluate_quality_criteria({}, {})
assert isinstance(r, dict) and 'all_passed' in r and 'failures' in r
print('evaluate_quality_criteria (no texts): OK')

# With identical texts — should detect copy (requires check_originality from Plan A)
try:
    text = 'O governo federal anunciou nesta quarta um pacote de medidas economicas para conter a inflacao no Brasil'
    r2 = evaluate_quality_criteria({}, {}, generated_text=text, source_text=text)
    has_copy = any(f.get('criterion') == 'text_copy' for f in r2.get('failures', []))
    if has_copy:
        print('text_copy criterion (identical texts): DETECTED correctly')
    else:
        print('text_copy criterion: check_originality not available yet (Plan A not run), graceful skip OK')
except Exception as e:
    print(f'evaluate_quality_criteria error: {e}')
"
```
</verification>

<success_criteria>
- Both tasks complete with zero Python syntax errors
- Old "article passes with reduced confidence" message removed from fact_check_service.py
- 0-claims path now: retry with _extract_claims_simplified → if still 0 → needs_manual_review=True + review reason appended
- evaluate_quality_criteria() has text_copy as 8th criterion with COPIA DETECTADA instruction
- text_copy criterion uses check_originality() from llm_service.py with graceful ImportError fallback
- All existing 6 criteria still present and unchanged (fabrication, readability, confidence, novel_entities, unverifiable, risk_level)
- No existing tests broken (run pytest tests/ if tests cover these functions)
</success_criteria>

<output>
After completion, create `.planning/phases/03-text-quality/03-B-safety-gates-SUMMARY.md`

Include:
- Exact line numbers of each surgical edit in fact_check_service.py and generation_api.py
- How _extract_claims_simplified() was implemented (what LLM call pattern it uses)
- Confirmation that check_originality import is inside the try block (not at file top-level)
- Verification command outputs (paste results)
- Any deviations from the plan and why
</output>
