---
wave: 1
depends_on:
  - 04-PLAN-A-config-dataclass-foundation.md
files_modified:
  - FeedRSS/tmc-rss-collector/services/fact_check_service.py
  - FeedRSS/tmc-rss-collector/services/database.py
autonomous: true
---

# Plan C: Track B — Embedding Cross-Reference, Temporal CoVe, Confidence + Safety Gates

Adds embedding-based claim cross-reference (the PRIMARY breaking-news verification mechanism),
temporal CoVe question, `recent_unverifiable` confidence handling, and safety gate split.
Edits verification sections of fact_check_service.py (lines 1270-1400, 2249-2670) and
database.py (new query method). Does NOT touch enrichment or prompt sections.

## must_haves

- New `get_recent_articles_with_embeddings(hours)` method in `database.py`
- New `_cross_reference_with_embeddings()` method in FactCheckService (degrades gracefully on error)
- Static `_cosine_sim()` method for pure-Python cosine similarity (no numpy dependency)
- In `verify_article()`: breaking+unverifiable claims cross-referenced via embeddings; if 3+ sources corroborate, reclassified to `recent_unverifiable`
- Separate counting: `metadata.unverifiable_claims` = standard only, `metadata.recent_unverifiable_claims` = temporal only
- Post-CoVe recount also separates standard vs recent_unverifiable
- CoVe prompt includes temporal question and `recent_unverifiable` verdict option (when flag ON)
- `_compute_confidence()` gives `recent_unverifiable` claims 0.7 weight in grounded ratio
- `_determine_risk_level()` uses only standard `unverifiable_claims` for escalation (excludes recent_unverifiable)
- All temporal paths gated by `_get_temporal_awareness_enabled()`

## Tasks

<task id="C1" title="Add get_recent_articles_with_embeddings() to database.py">
<read_first>
- FeedRSS/tmc-rss-collector/services/database.py (lines 2015–2100 — article_embeddings CRUD section, existing query patterns)
- FeedRSS/tmc-rss-collector/services/database.py (lines 2560–2600 — get_articles_pending_clustering for pattern reference)
</read_first>
<action>
Add a new method to `DatabaseService` class in the article embeddings section (after `get_article_embedding()` around line 2097). Follow the exact pattern of existing DB methods:

```python
    def get_recent_articles_with_embeddings(self, hours: int = 48) -> list:
        """Fetch articles with embeddings published in the last N hours.

        Used by Phase 4 temporal cross-reference to find corroborating articles.
        Returns list of dicts with 'id', 'title', 'embedding' keys.
        Embedding is returned as raw JSON string — caller must json.loads().
        """
        query = """
            SELECT a.id, a.title, e.embedding
            FROM collected_articles a
            JOIN article_embeddings e ON a.id = e.article_id
            WHERE a.published_at >= DATEADD(hour, -%s, GETUTCDATE())
              AND a.is_deleted = 0
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
            logger.error(f"Error fetching recent embeddings (hours={hours}): {e}")
            return []
```

Note: Uses `%s` placeholder (pymssql parameterized query), NOT f-string. Includes `a.is_deleted = 0` to respect soft deletes.
</action>
<acceptance_criteria>
- `grep -c "def get_recent_articles_with_embeddings" FeedRSS/tmc-rss-collector/services/database.py` returns 1
- `grep "DATEADD(hour" FeedRSS/tmc-rss-collector/services/database.py` includes the new query
- `grep "is_deleted = 0" FeedRSS/tmc-rss-collector/services/database.py` includes the new query (pattern match)
- The method uses `%s` for parameterized query, NOT string interpolation
- The method returns `[]` on error (graceful degradation)
</acceptance_criteria>
</task>

<task id="C2" title="Add _cosine_sim() and _cross_reference_with_embeddings() to FactCheckService">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 2240–2260 — area before _cove_verify_claims, insertion point)
- FeedRSS/tmc-rss-collector/services/embedding_service.py (lines 90–115 — generate_embedding signature and error handling)
- FeedRSS/tmc-rss-collector/services/database.py (lines 2015–2030 — get_db() singleton pattern)
</read_first>
<action>
Add two methods to `FactCheckService` class. Place them BEFORE `_cove_verify_claims()` (around line 2249):

```python
    @staticmethod
    def _cosine_sim(a: list, b: list) -> float:
        """Pure-Python cosine similarity for 1536-dim vectors. No numpy required."""
        import math
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    async def _cross_reference_with_embeddings(
        self,
        claim_text: str,
        min_similarity: float = 0.7,
        min_corroborating: int = 3,
        hours_window: int = None,
    ) -> bool:
        """Check if a claim is corroborated by 3+ independent collected articles.

        Uses existing article_embeddings table. Returns True if corroborated.
        Degrades gracefully on any error (returns False = no boost).
        Cost: FREE — no external API calls, uses existing embedding infrastructure.

        Args:
            claim_text: The claim text to embed and compare.
            min_similarity: Cosine similarity threshold (default 0.7 per D-08).
            min_corroborating: Minimum articles required (default 3 per D-08).
            hours_window: Time window in hours (default: TEMPORAL_BREAKING_HOURS).
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

            # 2. Fetch recent article embeddings from DB
            db = get_db()
            articles = db.get_recent_articles_with_embeddings(hours_window)
            if len(articles) < min_corroborating:
                return False

            # 3. Compute cosine similarity in Python
            import json as _json
            corroborating = 0
            for article in articles:
                emb = article.get("embedding")
                if not emb:
                    continue
                if isinstance(emb, str):
                    emb = _json.loads(emb)
                sim = self._cosine_sim(claim_embedding, emb)
                if sim >= min_similarity:
                    corroborating += 1
                    if corroborating >= min_corroborating:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Embedding cross-reference failed (non-blocking): {e}")
            return False
```
</action>
<acceptance_criteria>
- `grep -c "def _cosine_sim" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `grep -c "def _cross_reference_with_embeddings" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `grep "import math" FeedRSS/tmc-rss-collector/services/fact_check_service.py` appears inside `_cosine_sim`
- `grep "non-blocking" FeedRSS/tmc-rss-collector/services/fact_check_service.py` appears in the except block
- `grep "return False" FeedRSS/tmc-rss-collector/services/fact_check_service.py` includes at least 3 occurrences in the cross-reference method (flag off, not enough articles, exception)
- The method does NOT import numpy
</acceptance_criteria>
</task>

<task id="C3" title="Integrate embedding cross-reference into verify_article() and split unverifiable counts">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 1265–1400 — verify_article claim counting, post-extraction processing, CoVe trigger, post-CoVe recount, and _compute_confidence call)
</read_first>
<action>
1. In `verify_article()`, after claim extraction and the existing unverifiable count (around line 1278–1285), add embedding cross-reference for breaking+unverifiable claims. The exact insertion point is AFTER claims are extracted and counted, but BEFORE `_compute_confidence()`:

```python
        # Phase 4: Embedding cross-reference for breaking news claims
        if _get_temporal_awareness_enabled():
            for i, claim in enumerate(claims):
                if (isinstance(claim, ExtractedClaim)
                        and claim.verdict == "unverifiable"
                        and claim.temporalidade == "breaking"):
                    corroborated = await self._cross_reference_with_embeddings(claim.text)
                    if corroborated:
                        claims[i] = ExtractedClaim(
                            text=claim.text,
                            verdict="recent_unverifiable",
                            source_evidence=claim.source_evidence + " [embedding cross-ref: 3+ sources]",
                            source_reference=claim.source_reference,
                            category=claim.category,
                            temporalidade=claim.temporalidade,
                        )
                        logger.info(f"Claim reclassified to recent_unverifiable via embedding cross-ref: {claim.text[:80]}")
```

2. After the cross-reference block, update the claim counts to properly split standard vs recent_unverifiable. Find the existing `metadata.unverifiable_claims = sum(...)` line and replace the counting section:

```python
        # Split unverifiable into standard vs recent (Phase 4)
        metadata.unverifiable_claims = sum(
            1 for c in claims
            if (isinstance(c, ExtractedClaim) and c.verdict == "unverifiable")
            or (isinstance(c, dict) and c.get("verdict") == "unverifiable")
        )
        metadata.recent_unverifiable_claims = sum(
            1 for c in claims
            if (isinstance(c, ExtractedClaim) and c.verdict == "recent_unverifiable")
            or (isinstance(c, dict) and c.get("verdict") == "recent_unverifiable")
        ) if _get_temporal_awareness_enabled() else 0
```

3. In the post-CoVe recount section (around lines 1344–1364), also recount `recent_unverifiable_claims`:

After the existing recount of `grounded_claims`, `fabricated_claims`, `unverifiable_claims`, add:
```python
            metadata.recent_unverifiable_claims = sum(
                1 for c in metadata.claims
                if (isinstance(c, ExtractedClaim) and c.verdict == "recent_unverifiable")
                or (isinstance(c, dict) and c.get("verdict") == "recent_unverifiable")
            ) if _get_temporal_awareness_enabled() else 0
```
</action>
<acceptance_criteria>
- `grep "recent_unverifiable" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 8 matches
- `grep "embedding cross-ref" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 1 match
- `grep "_cross_reference_with_embeddings" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 2 matches (definition + call)
- `grep "metadata.recent_unverifiable_claims = sum" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 2 matches (initial count + post-CoVe recount)
- The standard `metadata.unverifiable_claims` count only matches `verdict == "unverifiable"` (not "recent_unverifiable")
</acceptance_criteria>
</task>

<task id="C4" title="Add temporal question to CoVe and recent_unverifiable verdict option">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 2330–2435 — _cove_single_claim, prompt_qa and prompt_verdict)
</read_first>
<action>
1. In `_cove_single_claim()` Call 1 — Q&A prompt (around line 2357–2375). After the existing questions template, add a temporal question conditionally:

Find the prompt_qa construction. It asks for `COVE_QUESTIONS_PER_CLAIM` verification questions. When `_get_temporal_awareness_enabled()` is True, append an additional question to the prompt:

```python
        temporal_cove_instruction = ""
        if _get_temporal_awareness_enabled():
            temporal_cove_instruction = (
                "\nPergunta adicional obrigatoria: "
                '"Quando este evento foi reportado pela primeira vez? '
                'A informacao e atual (ultimas 48h) ou contexto historico?"'
            )
```

Insert `{temporal_cove_instruction}` at the end of the questions section in `prompt_qa`, after the existing question rules.

2. In `_cove_single_claim()` Call 2 — verdict prompt (around line 2393–2415). The current verdict options are:
```
"final_verdict": "grounded|context|opinion|unverifiable|fabricated"
```

When `_get_temporal_awareness_enabled()` is True, extend to:
```
"final_verdict": "grounded|context|opinion|unverifiable|recent_unverifiable|fabricated"
```

And add the classification rule:
```python
        temporal_verdict_rule = ""
        if _get_temporal_awareness_enabled():
            temporal_verdict_rule = (
                '\n- "recent_unverifiable": Informacao de evento recente (<48h) que nao pode ser '
                'verificada por ser muito nova, mas NAO e incorreta nem desconexa do tema'
            )
```

Insert `{temporal_verdict_rule}` after the existing verdict rules in `prompt_verdict`.

3. Update the verdict option string conditionally:
```python
        verdict_options = "grounded|context|opinion|unverifiable|fabricated"
        if _get_temporal_awareness_enabled():
            verdict_options = "grounded|context|opinion|unverifiable|recent_unverifiable|fabricated"
```
Use `verdict_options` variable in the prompt instead of the hardcoded string.
</action>
<acceptance_criteria>
- `grep "temporal_cove_instruction" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 2 matches
- `grep "recent_unverifiable" FeedRSS/tmc-rss-collector/services/fact_check_service.py` in the CoVe section shows the verdict option
- `grep "Quando este evento foi reportado" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1 match
- `grep "temporal_verdict_rule" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 2 matches
- The temporal additions are gated by `_get_temporal_awareness_enabled()`
</acceptance_criteria>
</task>

<task id="C5" title="Update _compute_confidence() to weight recent_unverifiable at 0.7">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 2437–2510 — _compute_confidence, claim grounding score section)
</read_first>
<action>
In `_compute_confidence()`, in the claim grounding score computation (around lines 2456–2502):

1. After the existing `context_count` calculation (which counts claims with verdict "context"), add:

```python
            recent_unverifiable_count = sum(
                1 for c in factual_claims
                if (isinstance(c, ExtractedClaim) and c.verdict == "recent_unverifiable")
                or (isinstance(c, dict) and c.get("verdict") == "recent_unverifiable")
            )
```

2. Modify the `effective_grounded` calculation. Find the line that computes the grounded ratio numerator (currently something like `grounded_count + (context_count * 0.8)`). Add the recent_unverifiable contribution:

Change from:
```python
            effective_grounded = grounded_count + (context_count * 0.8)
```
to:
```python
            effective_grounded = grounded_count + (context_count * 0.8) + (recent_unverifiable_count * 0.7)
```

This gives `recent_unverifiable` claims a 0.7 weight in the grounded ratio (D-12), vs 0.0 for standard `unverifiable` and 0.8 for `context`.

3. Ensure `recent_unverifiable` is NOT in the `_non_factual` set. The set is `{"opinion", "editorial"}`. `recent_unverifiable` should be treated as factual for counting purposes (it goes in the denominator). No change needed if it's not in the set already.
</action>
<acceptance_criteria>
- `grep "recent_unverifiable_count" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 2 matches (count + usage)
- `grep "recent_unverifiable_count \* 0.7" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1 match
- `grep "effective_grounded = grounded_count" FeedRSS/tmc-rss-collector/services/fact_check_service.py` includes `recent_unverifiable_count * 0.7`
- The `_non_factual` set does NOT contain "recent_unverifiable"
</acceptance_criteria>
</task>

<task id="C6" title="Update _determine_risk_level() to exclude recent_unverifiable from escalation">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 2655–2675 — _determine_risk_level, unverifiable escalation check)
</read_first>
<action>
In `_determine_risk_level()`, find the unverifiable escalation block (around lines 2663–2667):

```python
        if metadata.total_claims > 0 and metadata.unverifiable_claims >= 3:
            unverifiable_pct = metadata.unverifiable_claims / metadata.total_claims
            if unverifiable_pct > 0.40 and level in ("low", "medium"):
                level = "high"
```

This block already uses `metadata.unverifiable_claims` which, after the Plan C Task C3 changes, contains ONLY standard unverifiable (not recent_unverifiable). So this block does NOT need modification IF Task C3 correctly splits the count.

However, add a comment for clarity:

```python
        # Only standard unverifiable escalates risk — recent_unverifiable (Phase 4)
        # is excluded because breaking news claims are naturally sparse on verification
        if metadata.total_claims > 0 and metadata.unverifiable_claims >= 3:
            unverifiable_pct = metadata.unverifiable_claims / metadata.total_claims
            if unverifiable_pct > 0.40 and level in ("low", "medium"):
                level = "high"
```

Verify that `metadata.unverifiable_claims` at this point in the flow has already been split (it is — `_determine_risk_level` is called after `_compute_confidence` which is after the count split in `verify_article`).
</action>
<acceptance_criteria>
- `grep "recent_unverifiable" FeedRSS/tmc-rss-collector/services/fact_check_service.py` near `_determine_risk_level` shows the explanatory comment
- The `_determine_risk_level()` method reads `metadata.unverifiable_claims` (which is standard-only after C3)
- No reference to `metadata.recent_unverifiable_claims` in this method (it should NOT read it for escalation)
</acceptance_criteria>
</task>

## Verification

```bash
cd FeedRSS/tmc-rss-collector
python -c "
from services.fact_check_service import FactCheckService, ExtractedClaim, VerificationMetadata

# Test _cosine_sim
sim = FactCheckService._cosine_sim([1, 0, 0], [1, 0, 0])
assert abs(sim - 1.0) < 0.001, f'Identity sim should be 1.0, got {sim}'

sim_orth = FactCheckService._cosine_sim([1, 0, 0], [0, 1, 0])
assert abs(sim_orth) < 0.001, f'Orthogonal sim should be 0.0, got {sim_orth}'

sim_zero = FactCheckService._cosine_sim([0, 0, 0], [1, 0, 0])
assert sim_zero == 0.0, f'Zero vector sim should be 0.0, got {sim_zero}'

print('Cosine similarity: OK')

# Test VerificationMetadata has recent_unverifiable_claims in to_dict
m = VerificationMetadata()
m.recent_unverifiable_claims = 5
d = m.to_dict()
assert d['recent_unverifiable_claims'] == 5, f'Expected 5, got {d[\"recent_unverifiable_claims\"]}'
assert d['unverifiable_claims'] == 0, 'Standard unverifiable should be 0'
print('VerificationMetadata split: OK')

print('ALL CHECKS PASSED')
"
```
