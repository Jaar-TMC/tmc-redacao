# Phase 4: Fact-Check Accuracy - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 04-fact-check-accuracy
**Areas discussed:** Temporal thresholds, Confidence adjustments, Embedding cross-reference, Rollout strategy

---

## Temporal Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| 48h/7d with env vars | Breaking <48h, recent 48h-7d, historic >7d. Configurable via TEMPORAL_BREAKING_HOURS and TEMPORAL_RECENT_DAYS | ✓ |
| Fixed constants | Hardcoded thresholds, simpler but no editorial tuning | |
| Shorter windows (6h/48h) | More aggressive breaking window for fast-cycle newsrooms | |

**User's choice:** 48h/7d as defaults, env vars for editorial tuning
**Notes:** User delegated to newsroom specialist analysis. 48h covers the critical window where Exa and search engines lack corroborating results. Env vars follow established pattern from Phase 2/3.

---

## Confidence Adjustments

| Option | Description | Selected |
|--------|-------------|----------|
| recent_unverifiable at 0.7 + exclude from hard block | Softer scoring for new claims, excluded from unverifiable>=3 block, fabricated still blocks | ✓ |
| Simple threshold reduction | Lower confidence floor for all recent articles (less targeted) | |
| Bypass safety gates entirely for breaking | Too permissive — risks letting fabrications through | |

**User's choice:** recent_unverifiable verdict at 0.7 weight, excluded from hard block count, fabricated still blocks, publication status = review
**Notes:** Key principle: "unverifiable because too new" ≠ "unverifiable because fabricated." Temporal awareness relaxes unverifiable, never fabricated. Breaking news defaults to review status for editorial oversight.

---

## Embedding Cross-Reference

| Option | Description | Selected |
|--------|-------------|----------|
| Implement with cosine >0.7, 3+ sources | Primary verification for breaking news, runs before Exa, FREE | ✓ |
| Skip — rely on date-scoped Exa alone | Simpler but misses the strongest signal (multiple RSS sources) | |
| Lower threshold (cosine >0.6, 2+ sources) | More permissive, risks false positives | |

**User's choice:** Implement. Cosine >0.7, 3+ independent sources = grounded. For breaking claims, skip Exa if confirmed.
**Notes:** Multiple independent sources = THE gold standard for newsroom verification. This is the highest-value change in Phase 4. Uses existing article_embeddings infrastructure at zero API cost.

---

## Rollout Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Ship directly with feature flag | TEMPORAL_AWARENESS_ENABLED=true default, instant revert if needed | ✓ |
| Logging-only first (1 week) | Safer but delays fixing the active bug | |
| Gradual rollout (50% traffic) | Requires A/B infrastructure TMC doesn't have | |

**User's choice:** Ship directly with feature flag ON by default. Monitor generation_audit_trail for 48h.
**Notes:** Current behavior IS the bug — every day unfixed = lost breaking news coverage. Feature flag allows instant revert. No logging-only phase needed since the problem is already well-characterized.

---

## Claude's Discretion

- Embedding query implementation details (SQL vs Python cosine)
- CoVe temporal question exact wording
- Whether to log temporal classification distribution
- Method placement for embedding cross-reference

## Deferred Ideas

None — discussion stayed within phase scope
