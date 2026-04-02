# Phase 4: Fact-Check Accuracy — Research Findings

**Researched:** 2026-04-02
**Status:** Ready for planning

---

## 1. Current Architecture Analysis

### 1.1 Claim Extraction — `_extract_and_verify_claims()` (lines 1452–1602)

**Signature:**
```python
async def _extract_and_verify_claims(
    self,
    texto_base: str,
    generated_article: str,
    enrichment: Optional[EnrichmentContext] = None
) -> list[ExtractedClaim]
```

**Current verdict vocabulary (line 1514):**
`grounded | fabricated | unverifiable | inaccurate | opinion | context`

**JSON schema currently returned per claim (lines 1510–1519):**
```json
{
  "text": "...",
  "verdict": "grounded|fabricated|unverifiable|inaccurate|opinion|context",
  "source_evidence": "...",
  "source_reference": "...",
  "category": "fact|statistic|quote|outcome|attribution|opinion"
}
```

**Parsing block (lines 1584–1596):** Builds `ExtractedClaim` from parsed dict. Handles legacy `editorial` → `context` mapping. **Adding `temporalidade` is purely additive** — read `c.get("temporalidade", "historico")` after the verdict parse.

**`ExtractedClaim` dataclass (lines 84–90):**
```python
@dataclass
class ExtractedClaim:
    text: str
    verdict: str = "unverifiable"
    source_evidence: str = ""
    source_reference: str = ""
    category: str = "fact"
```
Adding `temporalidade: str = "historico"` is a one-line field addition.

**Retry path `_extract_claims_simplified()` (lines 1604–1662):** Uses a minimal prompt, defaults all verdicts to `"unverifiable"`. Must also default `temporalidade = "historico"` for backward compatibility when temporal flag is OFF.

### 1.2 Exa Search — `_search_exa()` + `_get_date_range_start()` (lines 673–790)

**Root cause of bug:** `_get_date_range_start()` at lines 786–790 always returns a date `EXA_SEARCH_DAYS` (default 7) days ago:
```python
def _get_date_range_start(self) -> str:
    from datetime import datetime, timedelta
    start = datetime.utcnow() - timedelta(days=_get_exa_search_days())
    return start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
```

This single date is hardcoded into the Exa payload at line 718:
```python
"startPublishedDate": self._get_date_range_start(),
```

**`_search_exa()` accepts no `published_at` or temporal tier parameter.** It is called from `enrich_context()` at line 556–559 via `asyncio.gather` with no temporal context.

**`enrich_context()` signature (lines 502–508):**
```python
async def enrich_context(
    self,
    texto_base: str,
    titulo_fonte: Optional[str] = None,
    tags: Optional[list] = None,
    correlation_id: str = "",
) -> EnrichmentContext:
```
Currently has **no `published_at` parameter** — this must be added.

**`enrich_context()` is called from `generation_api.py` at line 765:**
```python
enrichment = await fact_checker.enrich_context(
    texto_base=request_data.texto_base,
    titulo_fonte=request_data.titulo_fonte,
    tags=request_data.tags,
    correlation_id=correlation_id,
)
```
The `published_at` of the source article is **not currently passed**. It would need to be extracted from `request_data` or passed separately.

**`GenerateRequest` model (lines 144–176):** Does NOT have a `published_at` / `source_published_at` field. **This field needs to be added** to `GenerateRequest` to pass source publication date from frontend → backend → enrichment.

Alternatively: if the frontend passes `source_article_ids`, the backend can look up `published_at` from the DB. But looking at the request model there is no such field either — simplest path is adding an optional `source_published_at: Optional[str]` to `GenerateRequest`.

### 1.3 CoVe Verification — `_cove_single_claim()` (lines 2330–2431)

**Structure:** Two sequential LLM calls per fabricated claim:
1. **Call 1 (Q&A, lines 2352–2382):** Generate `COVE_QUESTIONS_PER_CLAIM` (default 3) verification questions and answer them from source. Uses `prompt_qa` (lines 2357–2375).
2. **Call 2 (verdict, lines 2384–2430):** Re-classify based only on Q&A pairs. Uses `prompt_verdict` (lines 2393–2415).

**Call 1 prompt** has space for a temporal question after line 2375 (`"NAO classifique. Apenas gere perguntas e respostas factuais."`).

**Call 2 verdict options (line 2404):**
`"final_verdict": "grounded|context|opinion|unverifiable|fabricated"`
Adding `recent_unverifiable` here: if temporal flag is ON and the claim was classified as `breaking` tier, CoVe verdict can return `recent_unverifiable` to inform the caller.

**Temporal question location:** Should be appended to `prompt_qa` so the Q&A call captures temporal context. The temporal answer then flows into `prompt_verdict` via `qa_summary`, informing the verdict.

**`_cove_verify_claims()` (lines 2249–2328):** Only runs on `verdict == "fabricated"` claims. Temporal awareness applies to `verdict == "unverifiable"` claims — so this function does NOT need modification for the main temporal path. CoVe temporal question is additive when CoVe runs for `fabricated` claims.

### 1.4 `_compute_confidence()` (lines 2437–2585)

**Claim grounding score computation (lines 2456–2502):**
```python
_non_factual = {"opinion", "editorial"}
factual_claims = [c for c in metadata.claims if verdict not in _non_factual]
# Counts: grounded, context (at 0.8x), fabricated
# fabrication_penalty: 1 fabricated = 0.30, 2 = 0.55, 3+ = 0.80
claim_score = max(0, grounded_ratio - fabrication_penalty)
```

**Adding `recent_unverifiable` weight 0.7:** The change is in how `claim_score` counts these claims:
- Standard `unverifiable` contributes 0 to `grounded_ratio` (already — unverifiable is not grounded/context, so numerator doesn't increase but denominator does, dragging ratio down)
- `recent_unverifiable` should contribute `0.7` to the numerator (like context contributes `0.8 * count`)

**Weights module-level constants (lines 71–76):**
```python
WEIGHT_CLAIM_GROUNDING = 0.45
WEIGHT_ENTITY_OVERLAP = 0.15
WEIGHT_EXPANSION_RATIO = 0.10
WEIGHT_QUOTE_VERIFICATION = 0.10
WEIGHT_MATERIAL_SUFFICIENCY = 0.10
WEIGHT_CLAIM_SIMILARITY = 0.10
```
Note: CONTEXT says weights are `claims=0.40, entities=0.25...` but actual code has `0.45, 0.15...` (updated to v7). The CONTEXT doc has stale weights. **Use code values.**

**`unverifiable_claims` counter (lines 1278–1280):**
```python
metadata.unverifiable_claims = sum(
    1 for c in claims if c.verdict == "unverifiable"
)
```
After Phase 4, this must separately count `recent_unverifiable` claims. `VerificationMetadata` needs a new `recent_unverifiable_claims: int = 0` field.

**Post-CoVe recount (lines 1344–1364):** Recounts `grounded_claims`, `fabricated_claims`, `unverifiable_claims`. Must also recount `recent_unverifiable_claims` here.

### 1.5 `evaluate_safety_gates()` — Hard Block on Unverifiable (generation_api.py:350–355)

**The exact unverifiable hard block (lines 350–354):**
```python
if total_claims > 0 and unverifiable_claims >= 3:
    if unverifiable_claims / total_claims > 0.40:
        decision.publish_blocked = True
        decision.block_reasons.append(
            f"{unverifiable_claims}/{total_claims} afirmacoes inverificaveis"
        )
```

**The soft gate (lines 380–385):**
```python
if total_claims > 0 and unverifiable_claims >= 2:
    if unverifiable_claims / total_claims > 0.30:
        decision.human_review_required = True
        decision.review_reasons.append(...)
```

**`verification_data` dict is built from `VerificationMetadata.to_dict()`.** The dict currently includes `"unverifiable_claims"` (line 186). After Phase 4:
- `"unverifiable_claims"` will contain only **standard** unverifiable count
- `"recent_unverifiable_claims"` will be added as a separate key
- Safety gate reads `verification_data.get("unverifiable_claims", 0)` — this lookup needs no change if `unverifiable_claims` field is split correctly at the source

**D-15 (breaking news → `review` status):** This is separate from `evaluate_safety_gates()`. It means the publication_status in the generation response should be set to `review` when `recent_unverifiable_claims > 0`. Location: `generation_api.py` around line 925–960 where `publication_status` is determined.

### 1.6 Embedding Cross-Reference Infrastructure

**Existing `cosine_similarity()` in `clustering_service.py` (lines 52–85):**
```python
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    a = np.array(vec1, dtype=np.float64)
    b = np.array(vec2, dtype=np.float64)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return float(max(0.0, min(1.0, similarity)))
```
**This is in `clustering_service.py`, not `fact_check_service.py`.** The planner should decide: copy the function to `fact_check_service.py` (self-contained) or import from `clustering_service`. The import approach risks circular imports — prefer a local copy or a shared `utils/` function.

**`EmbeddingService.generate_embedding()` (embedding_service.py:94–111):** Single text → `List[float]`. Raises `RuntimeError` on failure and `ValueError` on empty text. This is the entry point for embedding a claim text.

**`database.py` embedding retrieval patterns:**
- `get_articles_pending_clustering()` (line 2563): joins `collected_articles` + `article_embeddings`, returns `{"id", "title", "preview", "embedding": json.loads(row[3])}`. Embeddings stored as JSON strings in `embedding` column.
- `get_article_embedding()` (line 2021): retrieves a single article's embedding.

**No existing function to query top-K similar articles by a query vector.** The embedding cross-reference method needs to either:
1. Load all recent article embeddings into memory and compute cosine similarity in Python (feasible for last 48h window, typically 50–200 articles)
2. Or add a DB method that returns embeddings with a time filter for efficiency

**Query pattern needed:**
```sql
SELECT a.id, a.title, e.embedding
FROM collected_articles a
JOIN article_embeddings e ON a.id = e.article_id
WHERE a.published_at >= DATEADD(hour, -48, GETUTCDATE())
ORDER BY a.published_at DESC
```
Then compute cosine similarity in Python. This is exactly how `get_articles_pending_clustering()` works but with a `published_at` time filter.

**`numpy` is already imported in `clustering_service.py`** (line 19: `import numpy as np`). It is NOT currently imported in `fact_check_service.py`. Adding numpy to fact_check_service requires either importing it or using a pure-Python cosine fallback.

**Pure-Python cosine similarity (no numpy):**
```python
import math
def _cosine_sim(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot / (na * nb) if na and nb else 0.0
```
For 1536-dim vectors this is fast enough in Python (sub-millisecond per comparison). Avoids numpy dependency in fact_check_service.

**`EmbeddingService` initialization requires `AZURE_OPENAI_API_KEY`** — will raise `ValueError` if key not set. The cross-reference method must guard with `try/except` and degrade gracefully (return no results, not crash).

**`FactCheckService.__init__`:** Already creates `self.http_client = httpx.AsyncClient(...)`. Does NOT create an `EmbeddingService`. The embedding cross-reference method will need to import and instantiate `EmbeddingService` lazily (or accept it as a parameter).

### 1.7 AppConfig — Adding Temporal Env Vars (config.py:15–99)

**Pattern for adding fields:**
1. Add fields to the frozen `AppConfig` dataclass (after line 65 feature flags block)
2. Add corresponding `_int_env()`/`_bool_env()` loading in `load_config()` (around line 162)

**Existing similar fields for reference:**
```python
# Feature flags section (lines 57–65)
fact_check_enabled: bool = True
cove_enabled: bool = True
# Exa section (lines 51–54)
exa_search_days: int = 7
exa_max_results: int = 5
```

**New fields to add:**
```python
# Temporal awareness (Phase 4)
temporal_awareness_enabled: bool = True
temporal_breaking_hours: int = 48
temporal_recent_days: int = 7
```

**Loading in `load_config()`:**
```python
temporal_awareness_enabled=_bool_env("TEMPORAL_AWARENESS_ENABLED", True),
temporal_breaking_hours=_int_env("TEMPORAL_BREAKING_HOURS", 48),
temporal_recent_days=_int_env("TEMPORAL_RECENT_DAYS", 7),
```

**Lazy accessor pattern in `fact_check_service.py` (lines 38–65):**
```python
def _get_temporal_awareness_enabled():
    return get_config().temporal_awareness_enabled
```

---

## 2. Integration Points and Risks

### Risk 1: `VerificationMetadata.to_dict()` is the contract between fact_check_service and generation_api
The dict is what `evaluate_safety_gates()` reads. Adding `recent_unverifiable_claims` to `to_dict()` is safe (additive). The `unverifiable_claims` key must continue to represent ONLY standard unverifiable for the safety gate to work correctly. If `recent_unverifiable_claims` are accidentally counted in `unverifiable_claims`, breaking news will still be hard-blocked — regression risk.

**Mitigation:** Unit test that `recent_unverifiable` verdicts do NOT increment `metadata.unverifiable_claims`.

### Risk 2: Parallel tracks modifying `fact_check_service.py`
Track A edits: `enrich_context()` signature/body (lines 502–623), `_search_exa()` payload (line 718), `_get_date_range_start()` (lines 786–790), `_extract_and_verify_claims()` prompt section (lines 1508–1560).
Track B edits: `_extract_and_verify_claims()` parsing section (lines 1584–1596), `verify_article()` counting section (lines 1278–1287), `_cove_single_claim()` prompts (lines 2357–2415), `_compute_confidence()` (lines 2456–2502), `_determine_risk_level()` (lines 2663–2667).

**Sections that BOTH tracks touch:** `_extract_and_verify_claims()` — Track A modifies the prompt (lines 1506–1558), Track B modifies the parsing (lines 1584–1596). These are non-overlapping line ranges in the same function. Safe but requires careful diff review.

**Sections unique to each track:**
- Track A only: `enrich_context()`, `_search_exa()`, `_get_date_range_start()`
- Track B only: `verify_article()`, `_cove_single_claim()`, `_compute_confidence()`, `_determine_risk_level()`

### Risk 3: `GenerateRequest` model change propagates to frontend
Adding `source_published_at: Optional[str] = None` to `GenerateRequest` is backward compatible (optional field with default). The frontend doesn't currently send this field, so behavior is unchanged until the frontend is updated. For Phase 4 to work without a frontend change, the backend can alternatively derive the published_at from the first `collected_articles` row matching `titulo_fonte`, but this adds a DB round-trip. The simpler approach is passing it from the frontend — but that is out of scope for a backend-only phase.

**Decision needed:** How does the backend know when the source article was published? Options:
1. Frontend adds `source_published_at` to `GenerateRequest` (requires minimal frontend change)
2. Backend reads `published_at` from DB using `titulo_fonte` or article ID as lookup key
3. Default to `datetime.utcnow()` when not provided, meaning the article is treated as breaking (most conservative/safe default for Phase 4 goal)

Option 3 is safest for Phase 4 scope: if `source_published_at` is not provided, treat the source as "just published now" (breaking tier). This means the temporal pipeline activates with the most permissive thresholds, which is the correct direction for the bug (over-blocking).

### Risk 4: Embedding cross-reference requires `AZURE_OPENAI_API_KEY`
If the key is not set (local dev), `EmbeddingService` raises `ValueError`. The method must degrade gracefully: if embedding fails → skip cross-reference, proceed to Exa as before. This is a NO-CRASH requirement.

### Risk 5: `_determine_risk_level()` escalates `unverifiable` to `high` at line 2664–2667
```python
if metadata.total_claims > 0 and metadata.unverifiable_claims >= 3:
    unverifiable_pct = metadata.unverifiable_claims / metadata.total_claims
    if unverifiable_pct > 0.40 and level in ("low", "medium"):
        level = "high"
```
After Phase 4, this ALSO needs to exclude `recent_unverifiable` for the same reason as the safety gate — otherwise risk level will still escalate to `high` for breaking news, which triggers a production-mode hard block. **This is the same fix as the safety gate, in `_determine_risk_level()`.**

### Risk 6: Feature flag `TEMPORAL_AWARENESS_ENABLED=false` must restore exact pre-Phase-4 behavior
All new temporal paths must be gated behind `if _get_temporal_awareness_enabled():`. When disabled: no `temporalidade` field in prompt, no date-scoped Exa, no embedding cross-reference, no `recent_unverifiable` verdict — all behavior is identical to current.

---

## 3. Technical Approach Per Task

### Task 4.0: Config additions (prerequisite, ~10 min)

**File:** `services/config.py`

Add to `AppConfig` dataclass (after `cove_enabled: bool = True` at line 63):
```python
# Temporal awareness (Phase 4)
temporal_awareness_enabled: bool = True
temporal_breaking_hours: int = 48
temporal_recent_days: int = 7
```

Add to `load_config()` (after `cove_enabled` loading at line 163):
```python
temporal_awareness_enabled=_bool_env("TEMPORAL_AWARENESS_ENABLED", True),
temporal_breaking_hours=_int_env("TEMPORAL_BREAKING_HOURS", 48),
temporal_recent_days=_int_env("TEMPORAL_RECENT_DAYS", 7),
```

Add lazy accessor in `fact_check_service.py` (after `_get_cove_enabled()` at line 53):
```python
def _get_temporal_awareness_enabled():
    return get_config().temporal_awareness_enabled

def _get_temporal_breaking_hours():
    return get_config().temporal_breaking_hours

def _get_temporal_recent_days():
    return get_config().temporal_recent_days
```

### Task 4.1: Temporal classification in claim extraction (Track A, ~30 min)

**File:** `services/fact_check_service.py`

**Step 1:** Add `temporalidade: str = "historico"` to `ExtractedClaim` dataclass (line ~90):
```python
@dataclass
class ExtractedClaim:
    text: str
    verdict: str = "unverifiable"
    source_evidence: str = ""
    source_reference: str = ""
    category: str = "fact"
    temporalidade: str = "historico"  # breaking | recente | historico
```

**Step 2:** Add `recent_unverifiable_claims: int = 0` to `VerificationMetadata` (line ~161, after `unverifiable_claims`):
```python
recent_unverifiable_claims: int = 0
```
And add to `to_dict()` return (line ~186):
```python
"recent_unverifiable_claims": self.recent_unverifiable_claims,
```

**Step 3:** Extend claim extraction prompt (after the JSON schema block at line ~1518). Insert a new field in the JSON schema for each claim:
```python
"temporalidade": "breaking|recente|historico"
```
And add classification rules at the end of the `Regras de classificacao` section (after line ~1559). Only add this block when `_get_temporal_awareness_enabled()` is True:
```
Classificacao temporal (adicional):
- "breaking": informacao de evento ocorrido nas ultimas 48 horas, ainda se desenvolvendo
- "recente": informacao dos ultimos 7 dias, contexto ja estabelecido mas recente
- "historico": contexto geral ou informacao estabelecida ha mais de 7 dias
```

**Step 4:** Parse `temporalidade` in the claims loop (lines 1584–1596):
```python
claims.append(ExtractedClaim(
    text=c.get("text", ""),
    verdict=verdict,
    source_evidence=c.get("source_evidence", ""),
    source_reference=c.get("source_reference", ""),
    category=c.get("category", "fact"),
    temporalidade=c.get("temporalidade", "historico") if _get_temporal_awareness_enabled() else "historico",
))
```

**Step 5:** In `verify_article()`, after the existing unverifiable count (line ~1278), add:
```python
metadata.recent_unverifiable_claims = 0  # Reset
if _get_temporal_awareness_enabled():
    metadata.recent_unverifiable_claims = sum(
        1 for c in claims
        if isinstance(c, ExtractedClaim) and c.verdict == "recent_unverifiable"
    )
    # Subtract recent_unverifiable from unverifiable_claims (split the count)
    metadata.unverifiable_claims = sum(
        1 for c in claims
        if isinstance(c, ExtractedClaim) and c.verdict == "unverifiable"
    )
```

**Step 6:** Update `_compute_confidence()` to handle `recent_unverifiable` (line ~2474):
After the existing `context_count` calculation, add:
```python
recent_unverifiable_count = sum(1 for c in factual_claims
    if (isinstance(c, ExtractedClaim) and c.verdict == "recent_unverifiable")
    or (isinstance(c, dict) and c.get("verdict") == "recent_unverifiable"))
# recent_unverifiable contributes 0.7 to grounded ratio (vs 0 for standard unverifiable)
effective_grounded = grounded_count + (context_count * 0.8) + (recent_unverifiable_count * 0.7)
```
Also update `_non_factual` to NOT include `recent_unverifiable` (it should be counted as factual).

**Step 7:** Update `_determine_risk_level()` (lines 2663–2667). Change the unverifiable escalation check to use only standard unverifiable:
```python
# Only standard unverifiable (not recent_unverifiable) escalates risk
std_unverifiable = metadata.unverifiable_claims  # post-Phase-4: this is already split
if metadata.total_claims > 0 and std_unverifiable >= 3:
    if std_unverifiable / metadata.total_claims > 0.40 and level in ("low", "medium"):
        level = "high"
```

### Task 4.2: Date-scoped Exa queries (Track A, ~30 min)

**File:** `services/fact_check_service.py`

**Step 1:** Add `source_published_at: Optional[str] = None` to `enrich_context()` signature (line 502). If not provided, default to `datetime.utcnow().isoformat()` (treat as breaking).

**Step 2:** Add a helper method to compute temporal tier:
```python
def _get_temporal_tier(self, published_at_iso: Optional[str]) -> str:
    """Classify source age into breaking|recente|historico."""
    if not _get_temporal_awareness_enabled():
        return "historico"
    if not published_at_iso:
        return "breaking"  # Unknown age → assume breaking (conservative)
    from datetime import datetime, timezone
    try:
        pub = datetime.fromisoformat(published_at_iso.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        if age_hours <= _get_temporal_breaking_hours():
            return "breaking"
        elif age_hours <= _get_temporal_recent_days() * 24:
            return "recente"
        else:
            return "historico"
    except Exception:
        return "breaking"  # Parse failure → assume breaking
```

**Step 3:** Replace the hardcoded `self._get_date_range_start()` in `_search_exa()` payload (line 718). The approach: pass an optional `date_range_start` parameter to `_search_exa()`:
```python
async def _search_exa(
    self,
    query: str,
    num_results: int = None,
    max_text: int = 2000,
    operation: str = 'enrichment_search',
    date_range_start: Optional[str] = None,  # NEW
) -> list:
```
When `date_range_start` is None, fall back to `self._get_date_range_start()` (existing behavior).

**Step 4:** In `enrich_context()`, compute the tier from `source_published_at` and pass appropriate `date_range_start` to each `_search_exa()` call:
```python
tier = self._get_temporal_tier(source_published_at)
date_range_start = self._get_tier_date_range(tier)  # New helper
search_tasks = [
    self._search_exa(q, ..., date_range_start=date_range_start)
    for q in queries[:num_queries]
]
```

**`_get_tier_date_range()` helper:**
```python
def _get_tier_date_range(self, tier: str) -> str:
    from datetime import datetime, timedelta
    if tier == "breaking":
        delta = timedelta(hours=_get_temporal_breaking_hours())
    elif tier == "recente":
        delta = timedelta(days=_get_temporal_recent_days())
    else:
        delta = timedelta(days=_get_exa_search_days())
    start = datetime.utcnow() - delta
    return start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
```

**Step 5:** Add `source_published_at` to the `enrich_context()` call in `generation_api.py` (line 765). Source:
```python
# Option: default to utcnow if not provided by frontend
source_published_at = getattr(request_data, 'source_published_at', None)
enrichment = await fact_checker.enrich_context(
    texto_base=request_data.texto_base,
    titulo_fonte=request_data.titulo_fonte,
    tags=request_data.tags,
    correlation_id=correlation_id,
    source_published_at=source_published_at,
)
```
And add to `GenerateRequest` model (line ~154):
```python
source_published_at: Optional[str] = Field(default=None, description="ISO datetime of source article publication")
```

### Task 4.3: Embedding cross-reference (Track B, ~45 min)

**File:** `services/fact_check_service.py` (new method)

**New method: `_cross_reference_with_embeddings()`**

Location: Add before `_cove_verify_claims()` (around line 2249).

```python
async def _cross_reference_with_embeddings(
    self,
    claim_text: str,
    min_similarity: float = 0.7,
    min_corroborating: int = 3,
    hours_window: int = None,
) -> bool:
    """
    Check if a claim is corroborated by 3+ independent collected articles.
    Uses existing article_embeddings table. Returns True if corroborated.
    Degrades gracefully on any error (returns False = no boost).
    """
    if not _get_temporal_awareness_enabled():
        return False
    if hours_window is None:
        hours_window = _get_temporal_breaking_hours()
    try:
        from services.embedding_service import EmbeddingService
        from services.database import get_db
        # 1. Embed the claim text
        embed_svc = EmbeddingService()
        claim_embedding = await embed_svc.generate_embedding(claim_text)
        # 2. Fetch recent article embeddings from DB (breaking window)
        db = get_db()
        articles = db.get_recent_articles_with_embeddings(hours_window)
        if len(articles) < min_corroborating:
            return False
        # 3. Compute cosine similarity in Python (no numpy required)
        corroborating = 0
        for article in articles:
            emb = article.get("embedding")
            if not emb:
                continue
            if isinstance(emb, str):
                import json
                emb = json.loads(emb)
            sim = self._cosine_sim(claim_embedding, emb)
            if sim >= min_similarity:
                corroborating += 1
                if corroborating >= min_corroborating:
                    return True
        return False
    except Exception as e:
        logger.warning(f"Embedding cross-reference failed (non-blocking): {e}")
        return False

@staticmethod
def _cosine_sim(a: list, b: list) -> float:
    """Pure-Python cosine similarity for 1536-dim vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
```

**New DB method: `get_recent_articles_with_embeddings(hours: int) -> List[dict]`**

Add to `services/database.py` in the article embeddings section (~line 2097):
```python
def get_recent_articles_with_embeddings(self, hours: int = 48) -> List[dict]:
    """Fetch articles with embeddings published in the last N hours."""
    query = """
        SELECT a.id, a.title, e.embedding
        FROM collected_articles a
        JOIN article_embeddings e ON a.id = e.article_id
        WHERE a.published_at >= DATEADD(hour, -%s, GETUTCDATE())
        ORDER BY a.published_at DESC
    """
    try:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (hours,))
            rows = cursor.fetchall()
            return [
                {"id": row[0], "title": row[1], "embedding": row[2]}
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error fetching recent embeddings: {e}")
        return []
```

**Integration into verification flow:** In `verify_article()` after claim extraction (around line 1286), for `breaking`-tier claims that are `unverifiable`, run cross-reference:
```python
if _get_temporal_awareness_enabled():
    for i, claim in enumerate(claims):
        if (isinstance(claim, ExtractedClaim)
                and claim.verdict == "unverifiable"
                and claim.temporalidade == "breaking"):
            corroborated = await self._cross_reference_with_embeddings(claim.text)
            if corroborated:
                # Downgrade: unverifiable → recent_unverifiable (softer)
                claims[i] = ExtractedClaim(
                    text=claim.text,
                    verdict="recent_unverifiable",
                    source_evidence=claim.source_evidence + " [embedding cross-reference]",
                    source_reference=claim.source_reference,
                    category=claim.category,
                    temporalidade=claim.temporalidade,
                )
```

**Important:** This cross-reference runs AFTER claim extraction but BEFORE confidence computation. The claims list is updated in-place before `_compute_confidence()` is called at line 1382.

### Task 4.4: Temporal CoVe question (Track B, ~20 min)

**File:** `services/fact_check_service.py`, `_cove_single_claim()` (lines 2330–2431)

**Only modify when `_get_temporal_awareness_enabled()` is True.**

In Call 1 (`prompt_qa` at line 2357), add one line after the existing questions template:
```python
temporal_question = (
    "\n4. Quando este evento foi reportado? A informacao e atual (ultimas 48h) ou contexto historico?"
    if _get_temporal_awareness_enabled() else ""
)
prompt_qa = f"""...
Responda em JSON:
```json
{{
  "questions": ["Pergunta 1?", "Pergunta 2?", "Pergunta 3?"{', "Quando este evento foi reportado?"' if _get_temporal_awareness_enabled() else ''}],
  "answers": ["Resposta 1", "Resposta 2", "Resposta 3"{', "Resposta temporal"' if _get_temporal_awareness_enabled() else ''}]
}}
```
```

In Call 2 (`prompt_verdict` at line 2393), add `recent_unverifiable` to the verdict options and rules:
```python
"final_verdict": "grounded|context|opinion|unverifiable|recent_unverifiable|fabricated"
```
And add the rule:
```
- **recent_unverifiable**: Informacao de evento recente (<48h) que nao pode ser verificada porque e muito nova, mas nao e incorreta ou desconexa
```

**Note:** CoVe is only invoked for claims already marked `fabricated` (line 2268). Temporal awareness in CoVe is valuable for correctly reclassifying breaking-news claims that were over-aggressively marked `fabricated`. The `recent_unverifiable` verdict option in CoVe Call 2 gives the LLM a more precise exit path.

### Task 4.5: Confidence softening + `recent_unverifiable` in safety gate (Track B, ~20 min)

**Already covered in Task 4.1 (confidence scoring) and Task 4.1 (safety gate split).**

The safety gate change in `evaluate_safety_gates()` is straightforward:
```python
# BEFORE:
unverifiable_claims = verification_data.get("unverifiable_claims", 0)
# AFTER (D-13):
unverifiable_claims = verification_data.get("unverifiable_claims", 0)
# recent_unverifiable excluded from hard block count
recent_unverifiable = verification_data.get("recent_unverifiable_claims", 0)
# All downstream checks on unverifiable_claims now use ONLY standard unverifiable
```

No change needed to the existing check at line 350 — it already reads `unverifiable_claims` which after Phase 4 will contain only standard unverifiable.

**D-15 (breaking news → `review` status):** Locate where `publication_status` is set in `generation_api.py`. Search around line 990–1050. When `recent_unverifiable_claims > 0`, override to `review`:
```python
if verification_data.get("recent_unverifiable_claims", 0) > 0:
    publication_status = "review"
```

---

## 4. Test Strategy

### 4.1 Existing Test Files

| File | What it tests |
|------|--------------|
| `tests/test_fact_check_improvements.py` | `_compute_confidence()`, `_compare_entities()`, CoVe, safety gates |
| `tests/test_generation_api.py` | `evaluate_safety_gates()`, `_build_schema_org()`, `_build_audit_data()` |
| `tests/test_safety_gates.py` | Safety gate logic (overlaps with above) |
| `tests/test_quality_criteria.py` | Quality loop criteria |

**Test fixture pattern** (from `test_fact_check_improvements.py`):
```python
@pytest.fixture
def service():
    return FactCheckService()
```
Tests use `AsyncMock` for LLM calls and `MagicMock` for DB. Pattern is established and should be followed.

### 4.2 New Tests Required

**File: `tests/test_phase4_temporal.py`** (new file)

**Module-level tests (no async):**
- `TestExtractedClaimTemporalField`: `ExtractedClaim` has `temporalidade` field, defaults to `"historico"`
- `TestTemporalTierClassification`: `_get_temporal_tier()` returns correct tier for 1h/25h/8d old sources
- `TestCosineSimPython`: `_cosine_sim()` matches known values (identity = 1.0, orthogonal ~0)

**Async tests (mock LLM + DB):**
- `TestClaimExtractionTemporalField`: Mock LLM returns JSON with `temporalidade`, verify `ExtractedClaim.temporalidade` is populated
- `TestClaimExtractionTemporalFallback`: LLM returns JSON WITHOUT `temporalidade`, verify defaults to `"historico"` (backward compat)
- `TestEmbeddingCrossReference`: Mock DB returns 3 high-similarity embeddings → `_cross_reference_with_embeddings()` returns True
- `TestEmbeddingCrossReferenceGracefulDegradation`: DB raises exception → returns False (no crash)
- `TestRecentUnverifiableConfidence`: `_compute_confidence()` with 3 `recent_unverifiable` claims out of 10 scores higher than same scenario with 3 standard `unverifiable`
- `TestSafetyGateExcludesRecentUnverifiable`: `evaluate_safety_gates()` with 4 `recent_unverifiable_claims` and `unverifiable_claims=0` does NOT trigger hard block
- `TestSafetyGateStillBlocksStandardUnverifiable`: 4 standard `unverifiable` still triggers hard block (regression check)
- `TestTemporalAwarenessFeatureFlag`: When `TEMPORAL_AWARENESS_ENABLED=false`, behavior is identical to pre-Phase-4 (no `temporalidade` in claims, standard unverifiable count, standard Exa range)

**Tests for `evaluate_safety_gates()` in `test_generation_api.py`** (extend existing file):
- Add `test_recent_unverifiable_not_blocked()`: many `recent_unverifiable`, zero `unverifiable` → no block
- Add `test_fabricated_still_blocks_with_temporal()`: `fabricated_claims >= 2` + `recent_unverifiable > 0` → still blocked (D-14)

### 4.3 Test Data

Temporal tier tests need datetime fixtures. Use `datetime.utcnow() - timedelta(hours=N)` with monkeypatch on `datetime.utcnow` or pass as ISO strings.

---

## 5. Dependencies and Ordering

### Strict ordering (sequential):

1. **Task 4.0 (config)** — Must complete first. All other tasks read `get_config().temporal_awareness_enabled` etc.
2. **Task 4.1 partial (dataclass changes)** — `ExtractedClaim.temporalidade` and `VerificationMetadata.recent_unverifiable_claims` must exist before any task that reads them.

### Parallel after prerequisites:

After 4.0 and 4.1 dataclass changes:
- **Track A** (Tasks 4.1 prompt + 4.2 Exa): Independent of Track B
- **Track B** (Tasks 4.3 embedding + 4.4 CoVe + 4.5 safety gate): Independent of Track A

### Track A internal ordering:
- 4.1 prompt changes must land before 4.2 (Exa scoping is only meaningful once claims are classified)
- But Exa scoping (4.2) uses `source_published_at` from `enrich_context()`, which is separate from claim temporalidade — can be done simultaneously as different functions

### Track B internal ordering:
- 4.3 (embedding cross-reference) must land before the verdict recount in `verify_article()` that reads `recent_unverifiable` counts — they are part of the same function
- 4.5 (safety gate) depends on `recent_unverifiable_claims` existing in the `to_dict()` output, which is part of 4.1

### Final integration (sequential after both tracks):
- Both tracks modify `_extract_and_verify_claims()`: Track A changes the prompt section, Track B changes the parsing section. **Merge must be reviewed carefully at this function boundary.**
- `generation_api.py` changes (add `source_published_at` to `GenerateRequest` + call site + D-15 publication_status) — can be done after both tracks as a cleanup step

### DB migration: NONE required
All changes use existing `article_embeddings` table. New DB method `get_recent_articles_with_embeddings()` is a read-only query on existing data. No schema migration needed.

---

## 6. Key Line Numbers Summary

| What | File | Lines |
|------|------|-------|
| `AppConfig` dataclass fields | `services/config.py` | 15–99 |
| `load_config()` loading | `services/config.py` | 120–183 |
| Lazy accessors in fact_check | `services/fact_check_service.py` | 38–66 |
| `ExtractedClaim` dataclass | `services/fact_check_service.py` | 84–90 |
| `VerificationMetadata` dataclass | `services/fact_check_service.py` | 136–161 |
| `VerificationMetadata.to_dict()` | `services/fact_check_service.py` | 163–201 |
| `enrich_context()` signature | `services/fact_check_service.py` | 502–508 |
| `_search_exa()` Exa payload | `services/fact_check_service.py` | 712–723 |
| `_get_date_range_start()` | `services/fact_check_service.py` | 786–790 |
| `verify_article()` claim counting | `services/fact_check_service.py` | 1270–1295 |
| `_extract_and_verify_claims()` prompt | `services/fact_check_service.py` | 1496–1559 |
| `_extract_and_verify_claims()` parsing | `services/fact_check_service.py` | 1584–1596 |
| CoVe `_cove_verify_claims()` | `services/fact_check_service.py` | 2249–2328 |
| CoVe `_cove_single_claim()` Call 1 | `services/fact_check_service.py` | 2352–2382 |
| CoVe `_cove_single_claim()` Call 2 | `services/fact_check_service.py` | 2384–2430 |
| `_compute_confidence()` claim grounding | `services/fact_check_service.py` | 2456–2502 |
| `_determine_risk_level()` unverifiable | `services/fact_check_service.py` | 2663–2667 |
| `evaluate_safety_gates()` | `functions/generation_api.py` | 237–411 |
| Unverifiable hard block | `functions/generation_api.py` | 350–355 |
| Unverifiable soft gate | `functions/generation_api.py` | 380–385 |
| `enrich_context()` call site | `functions/generation_api.py` | 763–770 |
| `verify_article()` call site | `functions/generation_api.py` | 919–925 |
| `GenerateRequest` model | `functions/generation_api.py` | 144–176 |
| Embedding section in DB | `services/database.py` | 1891–2097 |
| `cosine_similarity()` in clustering | `services/clustering_service.py` | 52–85 |

---

*Phase: 04-fact-check-accuracy*
*Research completed: 2026-04-02*
