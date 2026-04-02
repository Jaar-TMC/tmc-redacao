---
plan: 03-B
status: complete
completed_at: "2026-04-01"
---

# Plan 03-B Summary: Safety Gates

Two safety gates added to catch quality failures the pipeline was missing silently.

## Accomplishments

**Task B-1** — Fixed silent claim extraction failure in `fact_check_service.py`. The 3-line auto-pass block (0 claims -> passes with 0.35 confidence) was replaced with a retry + flag path: retry via `_extract_claims_simplified()` using a simplified 5-claim prompt, then if still 0 claims, set `needs_manual_review=True` and append "Extracao de claims falhou - verificacao manual necessaria" to `review_reasons`. Article does NOT auto-pass.

**Task B-2** — Added `text_copy` as the 8th quality criterion in `evaluate_quality_criteria()` in `generation_api.py`. When `generated_text` and `source_text` are provided, calls `check_originality()` from `llm_service.py` (created by Plan A). If 4-gram overlap exceeds 15%, appends a `text_copy` failure with `URGENTE - COPIA DETECTADA` instruction that triggers regeneration. Graceful `ImportError` fallback if Plan A not applied.

## Key Files Modified

- `FeedRSS/tmc-rss-collector/services/fact_check_service.py`
  - Lines 160-161: Added `needs_manual_review: bool = False` to `VerificationMetadata` dataclass
  - Line 201: Added `"needs_manual_review"` to `to_dict()`
  - Lines 1239-1270: Replaced 3-line auto-pass with 30-line retry + flag block
  - Lines 1604-1657: Added `_extract_claims_simplified()` async method

- `FeedRSS/tmc-rss-collector/functions/generation_api.py`
  - Lines 414-433: Extended `evaluate_quality_criteria()` signature with `generated_text` and `source_text`
  - Lines 548-578: Added `text_copy` criterion (criterion 8) before `return`
  - Line 1003-1004: First call site updated with `generated_text` and `source_text`
  - Lines 1190-1191: Second call site updated with `generated_text` and `source_text`

## How _extract_claims_simplified() Was Implemented

Uses the same `self._get_llm().call_api()` async pattern already used by `_extract_and_verify_claims()`. The method is async and accepts the generated article text. It sends a minimal prompt requesting 5 factual statements as JSON array, parses the response, and returns `ExtractedClaim` objects. `max_tokens=512` keeps cost low. On any parse or API failure it returns `[]` with a warning log.

## check_originality Import Location

The import is inside the `try` block within the `text_copy` criterion check — not at file top-level. This ensures graceful `ImportError` handling if `check_originality` does not yet exist in `llm_service.py`.

## Verification Outputs

```
fact_check_service.py: OK
generation_api.py: OK
fact_check_service.py changes: ALL OK
generation_api.py changes: ALL OK
evaluate_quality_criteria (no texts): OK
```

Acceptance criteria checks:
- `needs_manual_review` in fact_check_service.py: 4 matches (dataclass field, to_dict, log message, assignment)
- `_extract_claims_simplified` in fact_check_service.py: 2 matches (definition at 1604, call at 1248)
- `Extracao de claims falhou` in fact_check_service.py: 1 match
- `article passes with reduced confidence` in fact_check_service.py: 0 matches (removed)
- `text_copy` in generation_api.py: 2 matches
- `check_originality` in generation_api.py: 3 matches
- `generated_text` in generation_api.py: 5 matches
- `COPIA DETECTADA` in generation_api.py: 1 match
- `"fabrication"` in generation_api.py: still present (not deleted)

## Commits

- `03db409` feat(03-B): fix silent claim extraction failure with retry and manual review flag
- `49045a9` feat(03-B): add text_copy quality criterion to evaluate_quality_criteria()

## Deviations from Plan

None. The plan indicated `_extract_claims_simplified` could be synchronous calling a `_call_llm_sync()` helper, but no such helper exists in the class. The method was implemented as `async def` instead, mirroring the established `call_api()` pattern. The retry block uses `await self._extract_claims_simplified(...)` directly since the containing code is already inside an async method.
