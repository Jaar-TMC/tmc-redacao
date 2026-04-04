---
plan: 04-B-temporal-classification-exa
phase: 04-fact-check-accuracy
status: complete
---

# Plan B Summary: Temporal Classification + Date-Scoped Exa

## What was built
- _get_temporal_tier() classifies source age into breaking|recente|historico
- _get_tier_date_range() returns Exa startPublishedDate per temporal tier
- enrich_context() accepts source_published_at and passes tier-scoped date range to Exa
- Claim extraction prompt includes temporal classification rules (when flag enabled)
- Claim parsing reads temporalidade from LLM output, defaults to "historico"

## Key files modified
- FeedRSS/tmc-rss-collector/services/fact_check_service.py

## Verification
All temporal tier classifications correct. Date ranges generated properly.
