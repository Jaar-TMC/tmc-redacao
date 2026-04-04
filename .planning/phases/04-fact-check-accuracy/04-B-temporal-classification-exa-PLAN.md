---
wave: 1
depends_on:
  - 04-PLAN-A-config-dataclass-foundation.md
files_modified:
  - FeedRSS/tmc-rss-collector/services/fact_check_service.py
autonomous: true
---

# Plan B: Track A — Temporal Claim Classification + Date-Scoped Exa

Adds temporal classification to claim extraction prompt (breaking/recente/historico)
and scopes Exa search date ranges per temporal tier. Edits enrichment + prompt sections
of fact_check_service.py (lines 500-790, 1496-1600). Does NOT touch verification sections.

## must_haves

- Claim extraction prompt includes `temporalidade` field with `breaking|recente|historico` classification rules (gated by `TEMPORAL_AWARENESS_ENABLED`)
- Claim parsing reads `temporalidade` from LLM JSON output, defaults to `"historico"` when missing or flag OFF
- `_extract_claims_simplified()` fallback also defaults `temporalidade = "historico"`
- `enrich_context()` accepts optional `source_published_at: Optional[str]` parameter
- `_get_temporal_tier()` helper classifies source age into `breaking|recente|historico`
- `_search_exa()` accepts optional `date_range_start` parameter; when provided, overrides `_get_date_range_start()`
- Breaking claims search Exa with 48h window; recente with 7d; historico with existing default

## Tasks

<task id="B1" title="Add _get_temporal_tier() helper method to FactCheckService">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 35–78 — lazy accessors and constants)
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 220–250 — class definition area for FactCheckService.__init__)
</read_first>
<action>
Add two new methods to the `FactCheckService` class. Place them right after `_get_date_range_start()` (around line 790).

Method 1 — temporal tier classification:
```python
    def _get_temporal_tier(self, published_at_iso: str = None) -> str:
        """Classify source article age into breaking|recente|historico.

        Args:
            published_at_iso: ISO 8601 datetime string of source article publication.
                If None or unparseable, defaults to 'breaking' (most permissive).
        """
        if not _get_temporal_awareness_enabled():
            return "historico"
        if not published_at_iso:
            return "breaking"  # Unknown age → assume breaking (conservative for Phase 4 goal)
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

Method 2 — tier-specific date range for Exa:
```python
    def _get_tier_date_range(self, tier: str) -> str:
        """Return Exa startPublishedDate for a given temporal tier."""
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
</action>
<acceptance_criteria>
- `grep -c "def _get_temporal_tier" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `grep -c "def _get_tier_date_range" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `grep "return \"breaking\"" FeedRSS/tmc-rss-collector/services/fact_check_service.py` shows at least 2 occurrences (None case + parse failure case)
- `grep "_get_temporal_breaking_hours()" FeedRSS/tmc-rss-collector/services/fact_check_service.py` shows usage in both methods
</acceptance_criteria>
</task>

<task id="B2" title="Add source_published_at parameter to enrich_context() and pass tier date range to _search_exa()">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 500–560 — enrich_context signature and body)
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 670–730 — _search_exa method signature and Exa payload)
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 784–790 — _get_date_range_start)
</read_first>
<action>
1. Extend `enrich_context()` signature (around line 502). Add `source_published_at` parameter:

Change from:
```python
    async def enrich_context(
        self,
        texto_base: str,
        titulo_fonte: Optional[str] = None,
        tags: Optional[list] = None,
        correlation_id: str = "",
    ) -> EnrichmentContext:
```
to:
```python
    async def enrich_context(
        self,
        texto_base: str,
        titulo_fonte: Optional[str] = None,
        tags: Optional[list] = None,
        correlation_id: str = "",
        source_published_at: Optional[str] = None,
    ) -> EnrichmentContext:
```

2. Inside `enrich_context()`, before the Exa search calls (around line 550), compute the temporal tier and tier-specific date range:

Add after the `correlation_id` logging line:
```python
        # Temporal tier for date-scoped Exa (Phase 4)
        temporal_tier = self._get_temporal_tier(source_published_at)
        tier_date_range = self._get_tier_date_range(temporal_tier) if _get_temporal_awareness_enabled() else None
        if _get_temporal_awareness_enabled():
            logger.info(f"[{correlation_id}] Temporal tier: {temporal_tier}, date range start: {tier_date_range}")
```

3. Extend `_search_exa()` signature to accept optional `date_range_start`:

Change from (around line 673):
```python
    async def _search_exa(
        self,
        query: str,
        num_results: int = None,
        max_text: int = 2000,
        operation: str = 'enrichment_search',
    ) -> list:
```
to:
```python
    async def _search_exa(
        self,
        query: str,
        num_results: int = None,
        max_text: int = 2000,
        operation: str = 'enrichment_search',
        date_range_start: Optional[str] = None,
    ) -> list:
```

4. In the Exa payload construction inside `_search_exa()` (around line 718), change:
```python
            "startPublishedDate": self._get_date_range_start(),
```
to:
```python
            "startPublishedDate": date_range_start if date_range_start else self._get_date_range_start(),
```

5. In `enrich_context()`, pass `tier_date_range` to all `_search_exa()` calls. Find every call to `self._search_exa(` within `enrich_context()` and add `date_range_start=tier_date_range`. The calls are typically in an `asyncio.gather` list (around line 556–559).

**D-06 (Recency boost) — DEFERRED:** D-06 says "prioritize Exa results closest to article publication date." This would require sorting Exa results by `publishedDate` descending within the tier window after fetching them. This is deferred to a follow-up iteration because: (a) Exa's API does not guarantee `publishedDate` in all results; (b) the date-scoped window already constrains results to the relevant period; (c) adding sort logic increases complexity for marginal benefit. If needed later, add a `results.sort(key=lambda r: r.get("publishedDate", ""), reverse=True)` after the Exa response parsing in `_search_exa()`.
</action>
<acceptance_criteria>
- `grep "source_published_at: Optional\[str\] = None" FeedRSS/tmc-rss-collector/services/fact_check_service.py` matches the enrich_context signature
- `grep "date_range_start: Optional\[str\] = None" FeedRSS/tmc-rss-collector/services/fact_check_service.py` matches the _search_exa signature
- `grep "date_range_start if date_range_start" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1 match (payload line)
- `grep "temporal_tier = self._get_temporal_tier" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1 match
- `grep "date_range_start=tier_date_range" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 1 match
</acceptance_criteria>
</task>

<task id="B3" title="Add temporal classification to claim extraction prompt and parsing">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 1496–1600 — _extract_and_verify_claims prompt construction and JSON schema)
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 1580–1600 — claim parsing loop)
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 1604–1662 — _extract_claims_simplified fallback)
</read_first>
<action>
1. In the claim extraction prompt JSON schema block (around line 1510–1519), add the `temporalidade` field to the per-claim JSON schema. The schema currently shows:
```json
{
  "text": "...",
  "verdict": "grounded|fabricated|unverifiable|inaccurate|opinion|context",
  "source_evidence": "...",
  "source_reference": "...",
  "category": "fact|statistic|quote|outcome|attribution|opinion"
}
```

When `_get_temporal_awareness_enabled()` is True, extend this to include:
```
  "temporalidade": "breaking|recente|historico"
```

The prompt template is a Python f-string or string concatenation. Add the temporalidade field conditionally:

```python
temporal_schema = (
    ',\n  "temporalidade": "breaking|recente|historico"'
    if _get_temporal_awareness_enabled() else ''
)
```
Insert `{temporal_schema}` after the `"category"` line in the JSON schema block.

2. Add temporal classification rules to the prompt. After the existing classification rules section (around line 1555–1559), append when enabled:

```python
temporal_rules = ""
if _get_temporal_awareness_enabled():
    temporal_rules = """

Classificacao temporal (para cada claim):
- "breaking": informacao de evento ocorrido nas ultimas 48 horas, ainda em desenvolvimento
- "recente": informacao dos ultimos 7 dias, contexto recente mas ja estabelecido
- "historico": contexto geral ou informacao estabelecida ha mais de 7 dias
Se nao conseguir determinar, use "historico"."""
```
Append `temporal_rules` to the prompt before sending to LLM.

3. In the claim parsing loop (around line 1584–1596), where `ExtractedClaim` is constructed, add:

```python
    temporalidade=c.get("temporalidade", "historico") if _get_temporal_awareness_enabled() else "historico",
```

4. In `_extract_claims_simplified()` fallback (around line 1650), ensure all claims default to `temporalidade="historico"`:

When constructing `ExtractedClaim` objects in the simplified path, add `temporalidade="historico"`.
</action>
<acceptance_criteria>
- `grep "temporalidade" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 5 matches (schema, rules, parsing, fallback, and dataclass field)
- `grep 'c.get("temporalidade", "historico")' FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1 match (parsing)
- `grep "Classificacao temporal" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1 match (prompt rules)
- `grep "_get_temporal_awareness_enabled()" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 3 matches (conditional insertions)
- The temporal rules text contains "breaking", "recente", and "historico" definitions
</acceptance_criteria>
</task>

## Verification

```bash
cd FeedRSS/tmc-rss-collector
python -c "
from services.fact_check_service import FactCheckService, ExtractedClaim

# Test temporal tier classification
svc = FactCheckService()

# Test helper methods exist
from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc)
breaking = (now - timedelta(hours=1)).isoformat()
recente = (now - timedelta(days=3)).isoformat()
historico = (now - timedelta(days=30)).isoformat()

tier_b = svc._get_temporal_tier(breaking)
tier_r = svc._get_temporal_tier(recente)
tier_h = svc._get_temporal_tier(historico)
tier_none = svc._get_temporal_tier(None)

assert tier_b == 'breaking', f'Expected breaking, got {tier_b}'
assert tier_r == 'recente', f'Expected recente, got {tier_r}'
assert tier_h == 'historico', f'Expected historico, got {tier_h}'
assert tier_none == 'breaking', f'Expected breaking for None, got {tier_none}'
print('Temporal tier classification: OK')

# Test tier date range returns ISO string
dr = svc._get_tier_date_range('breaking')
assert 'T' in dr, f'Expected ISO datetime, got {dr}'
print('Tier date range: OK')

print('ALL CHECKS PASSED')
"
```
