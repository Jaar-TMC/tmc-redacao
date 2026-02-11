# TMC Pipeline - Application Insights KQL Queries

Saved queries for monitoring the TMC article generation pipeline.
Import these into your Application Insights > Logs workspace.

---

## 1. Daily Quality Dashboard

Parses `[QUALITY_SUMMARY]` structured logs for daily metrics.

```kql
traces
| where message has "[QUALITY_SUMMARY]"
| extend quality_json = extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message)
| extend quality = parse_json(quality_json)
| extend
    confidence = todouble(quality.confidence_score),
    fabricated = toint(quality.fabricated_claims),
    flesch = todouble(quality.flesch_score),
    blocked = tobool(quality.publish_blocked),
    review = tobool(quality.human_review),
    total_ms = toint(quality.total_ms),
    enrichment_ok = tobool(quality.enrichment_success),
    regenerated = tobool(quality.regenerated),
    pub_status = tostring(quality.publication_status),
    categoria = tostring(quality.categoria)
| summarize
    total_requests = count(),
    avg_confidence = round(avg(confidence), 3),
    avg_flesch = round(avg(flesch), 1),
    avg_latency_ms = round(avg(total_ms), 0),
    total_fabricated = sum(fabricated),
    fabrication_rate = round(100.0 * countif(fabricated > 0) / count(), 1),
    block_rate = round(100.0 * countif(blocked) / count(), 1),
    review_rate = round(100.0 * countif(review) / count(), 1),
    enrichment_success_rate = round(100.0 * countif(enrichment_ok) / count(), 1),
    regen_rate = round(100.0 * countif(regenerated) / count(), 1)
    by bin(timestamp, 1d)
| order by timestamp desc
```

## 2. Fabrication Rate (1-hour rolling)

P1 alerting query: fabrication rate > 2% over 1h window.

```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(1h)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend fabricated = toint(quality.fabricated_claims)
| summarize
    total = count(),
    with_fabrication = countif(fabricated > 0),
    fabrication_rate_pct = round(100.0 * countif(fabricated > 0) / count(), 1)
| where fabrication_rate_pct > 2.0
```

## 3. Verification Pipeline Failure Rate

P1 alerting query: verification failures > 10% over 1h.

```kql
traces
| where timestamp > ago(1h)
| where message has "Phase 3 verification" or message has "verification failed" or message has "[QUALITY_SUMMARY]"
| extend is_failure = (message has "failed" or message has "error")
| extend is_quality = message has "[QUALITY_SUMMARY]"
| summarize
    total_generations = countif(is_quality),
    verification_failures = countif(is_failure)
| extend failure_rate_pct = round(100.0 * verification_failures / max_of(total_generations, 1), 1)
| where failure_rate_pct > 10.0
```

## 4. Safety Gate Block Rate

Tracks how many articles are blocked vs. total.

```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(24h)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend
    blocked = tobool(quality.publish_blocked),
    pub_status = tostring(quality.publication_status)
| summarize
    total = count(),
    blocked_count = countif(blocked),
    block_rate = round(100.0 * countif(blocked) / count(), 1),
    draft_review = countif(pub_status == "draft_review"),
    ready_for_review = countif(pub_status == "ready_for_review"),
    draft = countif(pub_status == "draft")
    by bin(timestamp, 1h)
| order by timestamp desc
```

## 5. Phase Timing Breakdown

Performance monitoring: time spent in each pipeline phase.

```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(24h)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend total_ms = toint(quality.total_ms)
| summarize
    count = count(),
    avg_total_ms = round(avg(total_ms), 0),
    p50_ms = round(percentile(total_ms, 50), 0),
    p95_ms = round(percentile(total_ms, 95), 0),
    p99_ms = round(percentile(total_ms, 99), 0),
    max_ms = max(total_ms)
    by bin(timestamp, 1h)
| order by timestamp desc
```

## 6. Confidence Score Distribution

Tracks confidence score trends to detect model degradation.

```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(7d)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend
    confidence = todouble(quality.confidence_score),
    categoria = tostring(quality.categoria)
| summarize
    avg_confidence = round(avg(confidence), 3),
    min_confidence = round(min(confidence), 3),
    below_060 = countif(confidence < 0.60),
    below_050 = countif(confidence < 0.50),
    total = count()
    by bin(timestamp, 1d), categoria
| order by timestamp desc, categoria
```

## 7. Circuit Breaker State Changes

Detect when LLM or Exa circuit breakers open/close.

```kql
traces
| where message has "circuit" and (message has "open" or message has "close" or message has "half")
| project timestamp, message, severityLevel
| order by timestamp desc
| take 50
```

## 8. Enrichment Degradation

Monitors Exa enrichment success rate for early detection of API issues.

```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(4h)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend enrichment_ok = tobool(quality.enrichment_success)
| summarize
    total = count(),
    enrichment_success = countif(enrichment_ok),
    enrichment_failed = countif(not(enrichment_ok)),
    success_rate = round(100.0 * countif(enrichment_ok) / count(), 1)
    by bin(timestamp, 1h)
| where success_rate < 80
| order by timestamp desc
```

## 9. Rate Limiting Activity

Monitors 429 responses to detect capacity issues.

```kql
requests
| where timestamp > ago(24h)
| where resultCode == "429"
| summarize
    count = count()
    by bin(timestamp, 15m), name
| order by timestamp desc
```

## 10. Audit Trail Failures

Monitors audit persist failures (data loss risk).

```kql
traces
| where message has "Audit persist" and (message has "failed" or message has "timed out")
| project timestamp, message, severityLevel
| order by timestamp desc
| take 50
```

## 11. Error Rate by Endpoint

General error monitoring across all endpoints.

```kql
requests
| where timestamp > ago(24h)
| where toint(resultCode) >= 500
| summarize
    errors = count(),
    error_rate = round(100.0 * count() / max_of(1, count()), 1)
    by name, bin(timestamp, 1h)
| order by timestamp desc
```

## 12. Category-wise Quality

Quality metrics broken down by editorial category.

```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(7d)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend
    categoria = tostring(quality.categoria),
    confidence = todouble(quality.confidence_score),
    flesch = todouble(quality.flesch_score),
    fabricated = toint(quality.fabricated_claims),
    blocked = tobool(quality.publish_blocked)
| summarize
    total = count(),
    avg_confidence = round(avg(confidence), 3),
    avg_flesch = round(avg(flesch), 1),
    fabrication_rate = round(100.0 * countif(fabricated > 0) / count(), 1),
    block_rate = round(100.0 * countif(blocked) / count(), 1)
    by categoria
| order by total desc
```
