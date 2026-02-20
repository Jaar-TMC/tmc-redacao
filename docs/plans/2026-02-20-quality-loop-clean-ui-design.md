# Quality Loop + Clean UI Design

**Date:** 2026-02-20
**Status:** Approved
**Problem:** Post-generation UI dumps 7+ technical banners (verification %, Flesch score, expansion ratio, Schema.org JSON-LD, etc.) that confuse journalists. Users don't know what to do with this information.

## Core Principle

> "The AI should deliver a publishable article. If there are problems, fix them automatically before showing to the user."

## Target User

Journalists who need to produce articles fast, without technical knowledge of SEO/verification metrics.

## Design: Two Fronts

### Front 1: Backend — Quality Loop (Auto-Correction)

Expand the current auto-regeneration (Phase 2.1, fabrications-only) into a comprehensive quality loop that fixes ALL detectable issues before delivering to the user.

#### Quality Loop Flow

```
Phase 1: Enrichment (Exa search — existing)
Phase 2: Generation (existing)
Phase 3: Verification (existing)
Phase 4: Quality Loop (NEW)
  ├── Evaluate all quality criteria
  ├── All pass? → Deliver clean article ✓
  ├── Failures detected?
  │   ├── Fabricated/unverifiable claims → Exa claim-level search
  │   │   ├── Confirmed true → Reclassify as verified
  │   │   ├── Found correct data → Corrective instruction with real data
  │   │   └── Not found → Instruction to remove
  │   ├── Low readability (Flesch < 42) → Instruction to simplify
  │   ├── Low confidence (< 50%) → Instruction to restrict to source
  │   └── Excessive novel entities (>60%) → Instruction to remove
  │
  ├── Regenerate with accumulated corrective instructions
  ├── Re-verify (Phase 3 again)
  └── Repeat (max 3 total attempts)

If max attempts exhausted:
  → Deliver best version
  → If still critical → block with simple user message
```

#### Quality Criteria (triggers corrective regeneration)

| Criterion | Threshold | Corrective Instruction |
|---|---|---|
| Fabricated claims | >= 1 | Exa search per claim → correct/remove with real data |
| Unverifiable claims | >= 3 (>40% of total) | Exa search per claim → verify or remove |
| Readability (Flesch PT-BR) | < 42 | "Reescreva com frases mais curtas (max 20 palavras). Evite subordinadas longas." |
| Confidence score | < 50% | "Restrinja-se APENAS ao material-fonte. Nao adicione informacoes externas." |
| Novel entities | > 60% of output entities | "Nao introduza nomes/lugares/organizacoes que nao estejam na fonte." |

#### Exa Claim Verification (New)

For each fabricated or unverifiable claim:
1. Extract the factual assertion (e.g., "PIB cresceu 5% em 2024")
2. Exa search with specific query
3. Compare result:
   - Confirmed → reclassify claim as verified
   - Contradicted → build corrective instruction with correct data (e.g., "CORRIGIR: PIB foi 3.1%, nao 5%")
   - Not found → instruction to remove the claim

**Limits:**
- Max 5 claims searched per iteration (cost/latency control)
- 3s timeout per Exa search
- Cache: skip if Exa already searched this topic in Phase 1 enrichment
- Expected latency: +10-15s per iteration

#### Quality Loop Response Fields

```json
{
  "quality_loop_passed": true,
  "quality_loop_attempts": 2,
  "quality_loop_issues_fixed": ["fabrication", "readability"],
  "quality_loop_claims_corrected": 1,
  "quality_loop_claims_removed": 0,
  "quality_loop_claims_confirmed": 2
}
```

### Front 2: Frontend — Clean UI

#### Remove from UI (when quality loop passed):
- VerificationBanner (confidence %, claims, expansion ratio, risk level)
- Readability bar (Flesch score, avg sentence length, long sentences %)
- Enrichment degradation warning
- Auto-regeneration notice
- Publication status badge "Verificado" (if it passed, it's obvious)

#### Keep in UI:
- Sensitive content warnings (minors, suicide, sexual violence) — ALWAYS visible, legal/ethical requirement
- Schema.org collapsible (as-is)
- Slug field (as-is)
- Correlation ID (as-is)
- Nota forced notice (informative)

#### Quality Loop Failed (rare — after 3 attempts):
Simple, clear message (no jargon):
> "Nao foi possivel gerar uma materia 100% confiavel com este material. Sugerimos revisar o texto manualmente ou adicionar mais fontes de referencia."

Buttons:
- "Publicar Mesmo Assim" (with confirmation dialog)
- "Tentar Novamente"
- "Adicionar Mais Fontes" (navigate back to texto-base)

#### RevisarPage Progress Update:
Add a 5th phase to the generation progress screen:
```
1. Enriquecimento (existing)
2. Geracao (existing)
3. Verificacao (existing)
4. Refinamento (NEW — quality loop)
5. Finalizacao (existing)
```

## Files Affected

### Backend
- `FeedRSS/tmc-rss-collector/functions/generation_api.py` — Quality Loop orchestration, replace Phase 2.1
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py` — Exa claim-level search, claim correction helpers

### Frontend
- `tmc-redacao/src/pages/CriarPostPage.jsx` — Remove technical banners, add quality loop failure UI
- `tmc-redacao/src/components/ui/VerificationBanner.jsx` — Conditionally hide when quality loop passed
- `tmc-redacao/src/pages/criar/RevisarPage.jsx` — Add "Refinamento" phase to progress

## Success Criteria

1. Journalist sees zero technical banners after successful generation
2. 90%+ of articles pass quality loop in ≤ 2 attempts
3. Fabricated claims reduced to near-zero via Exa claim verification
4. Total generation time stays under 90 seconds for 95th percentile
5. Sensitive content warnings always visible when applicable
