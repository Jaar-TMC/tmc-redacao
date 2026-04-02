---
phase: 03-text-quality
plan: A
status: complete
completed_at: "2026-04-01"
commits:
  - 5ca03d3: "feat(03-A): add COMPETITOR_BRANDS config, ANTI_COPIA constant, and competitor filter injection into system prompts"
  - f16515a: "feat(03-A): add Haiku fact extraction step, extracted_facts injection into user prompt, and post-generation competitor scan"
  - 6071273: "feat(03-A): add check_originality() n-gram overlap detection function (module-level, pure Python)"
---

# Plan A Execution Summary

Fix the root cause of verbatim text copying in article generation and add competitor brand filtering.

## What Was Accomplished

Three surgical changes to stop generated articles from copying source text verbatim, plus competitor brand filtering infrastructure.

## Key Files Modified

### `FeedRSS/tmc-rss-collector/services/config.py`
- **Lines 79-80**: Added `competitor_brands: str = ""` field to `AppConfig` dataclass (after `cors_allowed_origins`)
- **Lines 171-172**: Added `competitor_brands=os.environ.get("COMPETITOR_BRANDS", "")` to `load_config()`

### `FeedRSS/tmc-rss-collector/services/llm_service.py`

**Task A-1 additions (lines ~211-237):**
- `ANTI_COPIA` constant added after `ANTI_FABRICACAO_PADROES` — 2 BAD examples labeled "INACEITAVEL" + 2 GOOD examples labeled "CORRETO", with absolute rule: never use >3 consecutive words from source

**Task A-1 additions (lines ~1412-1451):**
- `_build_competitor_instruction(competitor_brands: str) -> str` helper — builds FILTRAGEM instruction from comma-separated brand list; returns empty string when no brands configured
- `scan_competitor_mentions(text: str, competitor_brands: str) -> list` — regex word-boundary scan (case-insensitive), returns list of found brand names

**Task A-1 changes to `get_system_prompt()` (line ~1453):**
- Added `competitor_brands: str = ""` parameter
- Legacy return path now injects `{ANTI_COPIA}` and `{_build_competitor_instruction(competitor_brands)}`
- Category path propagates `competitor_brands` to `_build_category_prompt()`

**Task A-1 changes to `_build_category_prompt()` (line ~1578):**
- Added `competitor_brands: str = ""` parameter
- Return f-string now injects `{ANTI_COPIA}` and `{_build_competitor_instruction(competitor_brands)}` after `{LEGIBILIDADE_ALVO}`

**Task A-1 changes to `generate_article()` (line ~2368):**
- Reads `_competitor_brands = _get_config().competitor_brands` before `get_system_prompt()` call
- Passes `competitor_brands=_competitor_brands` to `get_system_prompt()`

**Task A-2 additions:**
- `_extract_facts_with_haiku()` async method on `LLMService` (lines ~2273-2322) — calls Haiku with `task_type="fact_extraction"`, truncates source to 3000 chars, returns "" on failure (graceful degradation)
- `build_user_prompt()` gained `extracted_facts: str = ""` parameter (line ~1766) — injects `<extracted-facts>` block with anti-copy instruction when non-empty
- `generate_article()` awaits `_extract_facts_with_haiku()` between system prompt construction and `build_user_prompt()` call
- Post-generation competitor scan in `generate_article()` after JSON parse: logs WARNING + sets `result["competitor_mentions"]` list

**Task A-3 additions:**
- `check_originality(generated, source, n=4, threshold=0.15) -> dict` added as module-level function between `_RateLimitError` and `LLMService` classes (lines ~1970-2033)
- Returns `{overlap_ratio, is_copy, overlapping_ngrams, total_generated_ngrams}`
- Pure Python (no dependencies), word-level 4-grams, >15% overlap threshold

## Verification Results

```
config.py: competitor_brands field OK
config.py: default competitor_brands OK
config.py: COMPETITOR_BRANDS env var loading OK
llm_service.py: OK (py_compile)
config.py: OK (py_compile)
check_originality: ALL TESTS PASSED (identical=1.00, rewritten=0.00, short=OK)
scan_competitor_mentions: OK
COMPETITOR_BRANDS config: OK
```

## Deviations from Plan

- **ANTI_COPIA content check**: The plan's smoke test asserted `assert 'ANTI_COPIA' in ANTI_COPIA` (checking if the string "ANTI_COPIA" appears in the constant value). The constant uses "ANTI-COPIA" (hyphenated) in its header. This is a test string mismatch in the plan, not an implementation issue — the constant is correct and `'INACEITAVEL' in ANTI_COPIA` passes cleanly.
- **`re` import**: `scan_competitor_mentions` uses `import re as _re` locally to avoid shadowing the module-level `re` import (already imported at line 11). This is a minor defensive choice.
- **Insertion point for `check_originality`**: Inserted between `_RateLimitError` class and `LLMService` class (after `build_user_prompt` end, before class definitions) — module-level as required, not inside any class.

## Downstream Dependencies (for Plan B)

Plan B (`generation_api.py`) can now import:
- `from services.llm_service import check_originality` — for n-gram text_copy quality criterion
- `from services.llm_service import scan_competitor_mentions` — if needed in evaluation layer
