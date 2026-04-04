---
wave: 0
depends_on: []
files_modified:
  - FeedRSS/tmc-rss-collector/services/config.py
  - FeedRSS/tmc-rss-collector/services/fact_check_service.py
autonomous: true
---

# Plan A: Config + Dataclass Foundation

All Phase 4 tasks depend on temporal awareness config fields and extended dataclass fields.
This plan adds the env vars, lazy accessors, and structural fields that downstream plans consume.

## must_haves

- `AppConfig` has `temporal_awareness_enabled`, `temporal_breaking_hours`, `temporal_recent_days` fields
- `load_config()` loads all three from env vars with correct defaults (True, 48, 7)
- `fact_check_service.py` has lazy accessors `_get_temporal_awareness_enabled()`, `_get_temporal_breaking_hours()`, `_get_temporal_recent_days()`
- `ExtractedClaim` dataclass has `temporalidade: str = "historico"` field
- `VerificationMetadata` dataclass has `recent_unverifiable_claims: int = 0` field
- `VerificationMetadata.to_dict()` includes `"recent_unverifiable_claims"` key
- `ExtractedClaim` serialization in `to_dict()` includes `"temporalidade"` key

## Tasks

<task id="A1" title="Add temporal config fields to AppConfig and load_config()">
<read_first>
- FeedRSS/tmc-rss-collector/services/config.py (full file — 230 lines)
</read_first>
<action>
1. In the `AppConfig` frozen dataclass, after the line `decontamination_enabled: bool = True` (around line 64), add:

```python
    # Temporal awareness (Phase 4 — breaking news fact-check)
    temporal_awareness_enabled: bool = True
    temporal_breaking_hours: int = 48
    temporal_recent_days: int = 7
```

2. In `load_config()`, after the line `decontamination_enabled=_bool_env("DECONTAMINATION_ENABLED", True),` (around line 164), add:

```python
        temporal_awareness_enabled=_bool_env("TEMPORAL_AWARENESS_ENABLED", True),
        temporal_breaking_hours=_int_env("TEMPORAL_BREAKING_HOURS", 48),
        temporal_recent_days=_int_env("TEMPORAL_RECENT_DAYS", 7),
```
</action>
<acceptance_criteria>
- `grep -c "temporal_awareness_enabled: bool = True" FeedRSS/tmc-rss-collector/services/config.py` returns 1
- `grep -c "temporal_breaking_hours: int = 48" FeedRSS/tmc-rss-collector/services/config.py` returns 1
- `grep -c "temporal_recent_days: int = 7" FeedRSS/tmc-rss-collector/services/config.py` returns 1
- `grep -c 'TEMPORAL_AWARENESS_ENABLED' FeedRSS/tmc-rss-collector/services/config.py` returns 1
- `grep -c 'TEMPORAL_BREAKING_HOURS' FeedRSS/tmc-rss-collector/services/config.py` returns 1
- `grep -c 'TEMPORAL_RECENT_DAYS' FeedRSS/tmc-rss-collector/services/config.py` returns 1
- `cd FeedRSS/tmc-rss-collector && python -c "from services.config import load_config; c = load_config(); print(c.temporal_awareness_enabled, c.temporal_breaking_hours, c.temporal_recent_days)"` prints `True 48 7`
</acceptance_criteria>
</task>

<task id="A2" title="Add lazy accessors for temporal config in fact_check_service.py">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 35–68 — existing lazy accessors block)
</read_first>
<action>
After the line `EXA_TIMEOUT = int(os.environ.get("EXA_TIMEOUT_SECONDS", "15"))` (line 67), add:

```python

# Temporal awareness (Phase 4)
def _get_temporal_awareness_enabled():
    return get_config().temporal_awareness_enabled

def _get_temporal_breaking_hours():
    return get_config().temporal_breaking_hours

def _get_temporal_recent_days():
    return get_config().temporal_recent_days
```
</action>
<acceptance_criteria>
- `grep -c "_get_temporal_awareness_enabled" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 1
- `grep -c "_get_temporal_breaking_hours" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 1
- `grep -c "_get_temporal_recent_days" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns at least 1
- Each function calls `get_config()` (already imported at file top)
</acceptance_criteria>
</task>

<task id="A3" title="Add temporalidade field to ExtractedClaim and recent_unverifiable_claims to VerificationMetadata">
<read_first>
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 80–205 — dataclass definitions and to_dict)
</read_first>
<action>
1. In `ExtractedClaim` dataclass (around line 90), after `category: str = "fact"`, add:

```python
    temporalidade: str = "historico"  # breaking | recente | historico
```

2. In `VerificationMetadata` dataclass (around line 145), after `unverifiable_claims: int = 0`, add:

```python
    recent_unverifiable_claims: int = 0
```

3. In `VerificationMetadata.to_dict()`, in the claims serialization loop (around line 168), extend the claim dict to include temporalidade:

Change the `ExtractedClaim` serialization block from:
```python
                claims_list.append({
                    "text": c.text,
                    "verdict": c.verdict,
                    "source_evidence": c.source_evidence,
                    "source_reference": c.source_reference,
                    "category": c.category,
                })
```
to:
```python
                claims_list.append({
                    "text": c.text,
                    "verdict": c.verdict,
                    "source_evidence": c.source_evidence,
                    "source_reference": c.source_reference,
                    "category": c.category,
                    "temporalidade": c.temporalidade,
                })
```

4. In the `to_dict()` return dict (around line 186), after `"unverifiable_claims": self.unverifiable_claims,`, add:

```python
            "recent_unverifiable_claims": self.recent_unverifiable_claims,
```
</action>
<acceptance_criteria>
- `grep -c 'temporalidade: str = "historico"' FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `grep -c "recent_unverifiable_claims: int = 0" FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `grep -c '"temporalidade": c.temporalidade' FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `grep -c '"recent_unverifiable_claims": self.recent_unverifiable_claims' FeedRSS/tmc-rss-collector/services/fact_check_service.py` returns 1
- `cd FeedRSS/tmc-rss-collector && python -c "from services.fact_check_service import ExtractedClaim; c = ExtractedClaim(text='test'); print(c.temporalidade)"` prints `historico`
- `cd FeedRSS/tmc-rss-collector && python -c "from services.fact_check_service import VerificationMetadata; m = VerificationMetadata(); d = m.to_dict(); print('recent_unverifiable_claims' in d, d['recent_unverifiable_claims'])"` prints `True 0`
</acceptance_criteria>
</task>

## Verification

```bash
cd FeedRSS/tmc-rss-collector
python -c "
from services.config import load_config
c = load_config()
assert c.temporal_awareness_enabled == True
assert c.temporal_breaking_hours == 48
assert c.temporal_recent_days == 7
print('Config OK')

from services.fact_check_service import ExtractedClaim, VerificationMetadata
claim = ExtractedClaim(text='test')
assert claim.temporalidade == 'historico'
meta = VerificationMetadata()
assert meta.recent_unverifiable_claims == 0
d = meta.to_dict()
assert 'recent_unverifiable_claims' in d
print('Dataclass OK')
print('ALL CHECKS PASSED')
"
```
