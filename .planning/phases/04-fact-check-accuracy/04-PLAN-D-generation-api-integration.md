---
wave: 2
depends_on:
  - 04-PLAN-B-temporal-classification-exa.md
  - 04-PLAN-C-embedding-crossref-cove-safety.md
files_modified:
  - FeedRSS/tmc-rss-collector/functions/generation_api.py
autonomous: true
---

# Plan D: Generation API Integration — Request Model, Call Site, Safety Gate, Publication Status

Wires the temporal pipeline into the generation API: adds `source_published_at` to the
request model, passes it to `enrich_context()`, ensures the safety gate excludes
`recent_unverifiable` from hard block counts, and overrides publication_status to
`"review"` for breaking news with temporal unverifiable claims.

## must_haves

- `GenerateRequest` model has `source_published_at: Optional[str] = None` field
- `enrich_context()` call passes `source_published_at` from request data
- `evaluate_safety_gates()` reads `recent_unverifiable_claims` from verification_data but does NOT count it toward hard block
- When `recent_unverifiable_claims > 0`, `publication_status` is forced to `"review"` (D-15) — not `"draft"`, not `"ready_for_review"`
- All changes backward-compatible (field optional, safety gate reads from dict with default 0)

## Tasks

<task id="D1" title="Add source_published_at field to GenerateRequest model">
<read_first>
- FeedRSS/tmc-rss-collector/functions/generation_api.py (lines 143–177 — GenerateRequest model definition)
</read_first>
<action>
In the `GenerateRequest` model (around line 167, after `source_type` field), add:

```python
    source_published_at: Optional[str] = Field(default=None, description="ISO datetime of source article publication (for temporal fact-check)")
```

Place it after the existing `source_type` field and before `research_source_urls`. This is an optional field with `None` default so it is fully backward-compatible — existing frontend code that omits it will get `None`, which `_get_temporal_tier()` treats as `"breaking"` (the correct default for Phase 4's goal of being more permissive with breaking news).
</action>
<acceptance_criteria>
- `grep "source_published_at: Optional\[str\]" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match
- `grep 'default=None.*temporal' FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match
- The field has `Field(default=None, ...)` making it optional
</acceptance_criteria>
</task>

<task id="D2" title="Pass source_published_at to enrich_context() call">
<read_first>
- FeedRSS/tmc-rss-collector/functions/generation_api.py (lines 760–780 — enrich_context call site)
</read_first>
<action>
In the `enrich_context()` call (around line 765), add the `source_published_at` parameter:

Change from:
```python
                    enrichment = await fact_checker.enrich_context(
                        texto_base=request_data.texto_base,
                        titulo_fonte=request_data.titulo_fonte,
                        tags=request_data.tags,
                        correlation_id=correlation_id,
                    )
```
to:
```python
                    enrichment = await fact_checker.enrich_context(
                        texto_base=request_data.texto_base,
                        titulo_fonte=request_data.titulo_fonte,
                        tags=request_data.tags,
                        correlation_id=correlation_id,
                        source_published_at=request_data.source_published_at,
                    )
```
</action>
<acceptance_criteria>
- `grep "source_published_at=request_data.source_published_at" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match
- The call is inside the `else:` branch of the enrichment cache check (the non-cached path)
</acceptance_criteria>
</task>

<task id="D3" title="Add recent_unverifiable_claims read in evaluate_safety_gates() — log only, no behavior change needed">
<read_first>
- FeedRSS/tmc-rss-collector/functions/generation_api.py (lines 237–410 — evaluate_safety_gates full function)
</read_first>
<action>
In `evaluate_safety_gates()`, after the existing `unverifiable_claims` read (around line 273):

```python
    unverifiable_claims = verification_data.get("unverifiable_claims", 0)
```

Add:
```python
    recent_unverifiable_claims = verification_data.get("recent_unverifiable_claims", 0)
```

NOTE: The hard block logic at line 350 (`if total_claims > 0 and unverifiable_claims >= 3:`) already works correctly because `unverifiable_claims` in the dict now contains ONLY standard unverifiable (the split happened in `verify_article()` — Plan C, Task C3). No modification to the block logic is needed.

However, add a logging line after the existing block for operational visibility:

After the unverifiable hard block check (around line 355), add:
```python
    # Phase 4: Log temporal unverifiable for monitoring (not counted toward block)
    if recent_unverifiable_claims > 0:
        decision.review_reasons.append(
            f"{recent_unverifiable_claims} afirmacao(oes) inverificavel(eis) por ser noticia recente"
        )
        decision.human_review_required = True
```

Also in the soft gate section (around line 380), the existing soft gate on `unverifiable_claims >= 2` already uses the split count, so no change needed there either.
</action>
<acceptance_criteria>
- `grep "recent_unverifiable_claims = verification_data.get" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match
- `grep "noticia recente" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match
- The hard block at line 350 still reads `unverifiable_claims` (not `recent_unverifiable_claims`)
- When `recent_unverifiable_claims > 0`, `human_review_required` is set to True
</acceptance_criteria>
</task>

<task id="D4" title="Override publication_status to 'review' when recent_unverifiable_claims > 0">
<read_first>
- FeedRSS/tmc-rss-collector/functions/generation_api.py (lines 1410–1425 — Phase 5.1 publication status block)
- FeedRSS/tmc-rss-collector/functions/generation_api.py (lines 910–930 — verify_article call site, to find where verification_data is available)
</read_first>
<action>
In the publication status block (around lines 1410–1421), after the existing status logic:

```python
        if result.get("publish_blocked"):
            result["publication_status"] = "blocked"
        elif result.get("human_review_required"):
            result["publication_status"] = "draft_review"
        elif result.get("verification", {}).get("is_verified"):
            result["publication_status"] = "ready_for_review"
        else:
            result["publication_status"] = "draft"
```

Add a D-15 override AFTER this block (so it can override `draft_review` or `ready_for_review` to the more specific `review` status):

```python
        # Phase 4 D-15: Breaking news with recent_unverifiable claims → "review"
        # Editor must eyeball before publication — standard newsroom practice
        verification = result.get("verification", {})
        if verification.get("recent_unverifiable_claims", 0) > 0:
            if result["publication_status"] not in ("blocked",):
                result["publication_status"] = "review"
                result["temporal_review_required"] = True
```

This ensures:
- `blocked` articles stay blocked (fabricated claims still block regardless of temporal)
- All other statuses (draft, draft_review, ready_for_review) are overridden to `review`
- A `temporal_review_required` flag is added for the frontend to display appropriate messaging
</action>
<acceptance_criteria>
- `grep "recent_unverifiable_claims" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns at least 3 matches (read, review_reason, publication_status)
- `grep 'publication_status.*review' FeedRSS/tmc-rss-collector/functions/generation_api.py` includes the temporal override
- `grep "temporal_review_required" FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match
- `grep 'not in ("blocked",)' FeedRSS/tmc-rss-collector/functions/generation_api.py` returns 1 match (blocked articles are never overridden)
</acceptance_criteria>
</task>

## Verification

```bash
cd FeedRSS/tmc-rss-collector
python -c "
from functions.generation_api import GenerateRequest, evaluate_safety_gates

# Test GenerateRequest has source_published_at
req = GenerateRequest(texto_base='x' * 20)
assert req.source_published_at is None, 'Default should be None'
print('GenerateRequest field: OK')

# Test safety gate with recent_unverifiable (should NOT block)
decision = evaluate_safety_gates(
    verification_data={
        'confidence_score': 0.80,
        'risk_level': 'medium',
        'fabricated_claims': 0,
        'unverifiable_claims': 0,
        'recent_unverifiable_claims': 5,
        'total_claims': 10,
        'grounded_claims': 5,
        'context_claims': 0,
        'is_verified': True,
    },
    content_length=2000,
    effective_source_len=1000,
)
assert not decision.publish_blocked, f'Should NOT be blocked, reasons: {decision.block_reasons}'
assert decision.human_review_required, 'Should require human review'
print('Safety gate excludes recent_unverifiable: OK')

# Test safety gate with standard unverifiable (should block)
decision2 = evaluate_safety_gates(
    verification_data={
        'confidence_score': 0.80,
        'risk_level': 'medium',
        'fabricated_claims': 0,
        'unverifiable_claims': 5,
        'recent_unverifiable_claims': 0,
        'total_claims': 10,
        'grounded_claims': 5,
        'context_claims': 0,
        'is_verified': True,
    },
    content_length=2000,
    effective_source_len=1000,
)
assert decision2.publish_blocked, 'Standard unverifiable should block'
print('Standard unverifiable still blocks: OK')

print('ALL CHECKS PASSED')
"
```
