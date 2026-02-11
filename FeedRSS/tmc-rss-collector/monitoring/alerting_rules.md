# TMC Pipeline - Alerting Rules

Configure these in Azure Monitor > Alerts (Application Insights resource).

---

## P1 Alerts (Immediate - PagerDuty/Teams)

### Alert 1: High Fabrication Rate
- **Condition**: Fabrication rate > 2% over 1-hour window
- **Severity**: Critical (Sev 1)
- **Frequency**: Every 15 minutes
- **Window**: 1 hour
- **Action**: Notify #tmc-alerts Teams channel + PagerDuty
- **KQL**: See `kql_queries.md` Query #2
- **Runbook**: If sustained, set `PRODUCTION_SAFETY_MODE=true` (should already be on). If already on, investigate LLM model changes or prompt regression. Rollback to previous deployment if needed.

### Alert 2: Verification Pipeline Offline
- **Condition**: Verification failure rate > 10% over 1-hour window
- **Severity**: Critical (Sev 1)
- **Frequency**: Every 15 minutes
- **Window**: 1 hour
- **Action**: Notify #tmc-alerts + PagerDuty
- **KQL**: See `kql_queries.md` Query #3
- **Runbook**: The anti-hallucination safety net is offline. All articles generated without verification should be manually reviewed. Check Exa API status and LLM availability. If Exa is down, articles still generate but in degraded mode (enrichment_degraded=true). If LLM is down, generation itself fails (503).

---

## P2 Alerts (4-hour - Teams notification)

### Alert 3: Low Average Confidence
- **Condition**: Average confidence drops below 0.60 over 4-hour window
- **Severity**: Warning (Sev 2)
- **Frequency**: Every 30 minutes
- **Window**: 4 hours
- **Action**: Notify #tmc-alerts Teams channel
- **KQL**:
```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(4h)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend confidence = todouble(quality.confidence_score)
| summarize avg_confidence = avg(confidence), total = count()
| where avg_confidence < 0.60 and total >= 5
```
- **Runbook**: Check if enrichment is failing (confidence drops without enrichment). Review recent articles for quality issues. May indicate LLM model quality regression.

### Alert 4: LLM Circuit Breaker Open
- **Condition**: Circuit breaker state change to "open"
- **Severity**: Warning (Sev 2)
- **Frequency**: Every 5 minutes
- **Window**: 5 minutes
- **Action**: Notify #tmc-alerts Teams channel
- **KQL**: See `kql_queries.md` Query #7
- **Runbook**: LLM provider may be experiencing outage. Article generation will fail until circuit half-opens. Check Anthropic/Azure AI status page. Wait for auto-recovery or switch provider via `LLM_MODEL` env var.

### Alert 5: Exa Enrichment Degradation
- **Condition**: Enrichment success rate < 80% over 4-hour window
- **Severity**: Warning (Sev 2)
- **Frequency**: Every 30 minutes
- **Window**: 4 hours
- **Action**: Notify #tmc-alerts
- **KQL**: See `kql_queries.md` Query #8
- **Runbook**: Exa API may be rate-limited or experiencing issues. Articles will still generate but in degraded mode. Confidence scores will be lower. Check Exa dashboard and API key quota.

---

## P3 Alerts (Daily - Email digest)

### Alert 6: High Response Time
- **Condition**: Average response time > 60s over 1-hour window
- **Severity**: Informational (Sev 3)
- **Frequency**: Every 1 hour
- **Window**: 1 hour
- **Action**: Email digest to engineering team
- **KQL**:
```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(1h)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend total_ms = toint(quality.total_ms)
| summarize avg_ms = avg(total_ms), p95_ms = percentile(total_ms, 95), total = count()
| where avg_ms > 60000
```

### Alert 7: Audit Trail Failures
- **Condition**: Any audit persist failures in last hour
- **Severity**: Informational (Sev 3)
- **Frequency**: Every 1 hour
- **Window**: 1 hour
- **Action**: Email digest
- **KQL**: See `kql_queries.md` Query #10

### Alert 8: High Block Rate
- **Condition**: Block rate > 20% over 24-hour window (may indicate overly strict gates)
- **Severity**: Informational (Sev 3)
- **Frequency**: Daily
- **Window**: 24 hours
- **Action**: Email digest
- **KQL**:
```kql
traces
| where message has "[QUALITY_SUMMARY]"
| where timestamp > ago(24h)
| extend quality = parse_json(extract(@"\[QUALITY_SUMMARY\]\s*(.*)", 1, message))
| extend blocked = tobool(quality.publish_blocked)
| summarize total = count(), blocked = countif(blocked)
| extend block_rate_pct = round(100.0 * blocked / total, 1)
| where block_rate_pct > 20 and total >= 10
```

---

## Azure Monitor Configuration

### Action Groups

1. **tmc-critical**: PagerDuty webhook + Teams #tmc-alerts + Email to tech-lead
2. **tmc-warning**: Teams #tmc-alerts + Email to engineering
3. **tmc-info**: Email digest to engineering (daily summary)

### Alert Rule Setup (Azure Portal)

1. Go to Application Insights > Alerts > New alert rule
2. Set Resource: your Application Insights instance
3. Condition: Custom log search (KQL)
4. Paste the relevant KQL query
5. Set threshold (number of results > 0)
6. Set evaluation frequency and window as specified above
7. Assign to appropriate action group
8. Set severity level

### Recommended Dashboard

Create an Azure Dashboard with these tiles:
- Daily fabrication rate (line chart, 30-day trend)
- Average confidence score (line chart, 30-day trend)
- Average Flesch score (line chart, 30-day trend)
- Block rate vs. review rate (stacked bar, 7-day)
- P95 latency (line chart, 7-day)
- Enrichment success rate (gauge, current 4h)
- Circuit breaker status (status indicator)
