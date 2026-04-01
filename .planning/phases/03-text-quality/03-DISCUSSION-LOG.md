# Phase 3: Text Quality - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 03-text-quality
**Areas discussed:** Extraction Strategy, Originality Threshold, Competitor Handling, Zero-Claims Behavior, Anti-Copy Prompt Design
**Mode:** --auto (all areas auto-selected, recommended options auto-picked)

---

## Extraction Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Haiku fact extraction | Call Claude Haiku to extract facts/entities before generation (~$0.001/article) | auto |
| Rule-based extraction | Regex/NLP extraction — cheaper but less accurate for Portuguese | |
| Stronger instructions only | Keep raw source, add more anti-copy instructions to prompt | |

**User's choice:** [auto] Haiku fact extraction (recommended — plan §3.1)
**Notes:** Eliminates ~80% verbatim copying by removing raw source from generation input. Cost is negligible.

---

## Originality Threshold

| Option | Description | Selected |
|--------|-------------|----------|
| llm_service.py, 15% 4-gram, regen trigger | New function close to generation, plan defaults, integrates with quality loop | auto |
| fact_check_service.py, 15% 4-gram | Part of verification pipeline — but bloats 110KB file further | |
| Standalone utility, 10% stricter | Separate module, stricter threshold may cause excessive regen | |

**User's choice:** [auto] llm_service.py, 15% 4-gram, quality loop regen trigger (recommended — plan §3.2)
**Notes:** Pure Python, no external deps. Keeps detection close to generation. 15% is balanced — catches verbatim copy without flagging legitimate shared terminology.

---

## Competitor Handling

| Option | Description | Selected |
|--------|-------------|----------|
| ENV var + prompt + post-scan | COMPETITOR_BRANDS env var, dual enforcement (prompt instruction + regex scan) | auto |
| Prompt-only | Tell LLM to avoid brands — simpler but unreliable | |
| Database table | More flexible but over-engineered for a list of ~10-20 brands | |

**User's choice:** [auto] ENV var + dual enforcement (recommended — plan §3.3)
**Notes:** Defense in depth. Post-scan logs warnings for editorial review but does NOT auto-replace (risk of mangling text). Editorial maintains list via env var without deploy.

---

## Zero-Claims Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Retry once + flag needs_manual_review | Retry with simpler prompt, then flag for review if still 0 | auto |
| Hard block | Stop pipeline entirely — too aggressive for production | |
| Keep auto-pass (current) | Article passes with 0.35 confidence — the bug we're fixing | |

**User's choice:** [auto] Retry once + flag (recommended — plan §3.4)
**Notes:** Keeps pipeline flowing but prevents silent hallucination pass. Article proceeds but publication status is `review` not `published`.

---

## Anti-Copy Prompt Design

| Option | Description | Selected |
|--------|-------------|----------|
| Separate ANTI_COPIA constant, 2+2 PT examples | New constant, 2 BAD + 2 GOOD Portuguese examples, injected in system prompt | auto |
| Merge into FIDELIDADE_FACTUAL | Less modular, harder to tune independently | |
| 1+1 examples (shorter prompt) | Cheaper tokens but less effective | |

**User's choice:** [auto] Separate constant, 2+2 examples (recommended — plan §3.5)
**Notes:** Clean separation from anti-hallucination rules. Portuguese examples match generation language. Injected in system prompt (not user prompt) to keep content separate.

---

## Claude's Discretion

- Exact wording of Haiku extraction prompt
- Whether word-level or character-level n-grams (default: word-level)
- Number of claims in simplified retry prompt (default: 5)
- Exact BAD/GOOD anti-copy examples (based on real TMC patterns)

## Deferred Ideas

- WhatsApp CTA removal (P1 backlog item, different concern)
- Opinion mode for entertainment (P2 feature, not a bug fix)
