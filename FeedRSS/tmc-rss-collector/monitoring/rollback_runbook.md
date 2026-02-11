# TMC Pipeline - Rollback & Emergency Procedures

## Quick Reference

| Emergency | Action | Command/Setting |
|---|---|---|
| Fabricated articles publishing | Block all publishes | `PRODUCTION_SAFETY_MODE=true` (should already be on) |
| LLM completely down | Disable generation | LLM circuit breaker auto-activates |
| Exa API down | Degraded mode (auto) | `FACT_CHECK_ENRICHMENT_ENABLED=false` to skip entirely |
| Verification producing false positives | Disable verification | `FACT_CHECK_VERIFICATION_ENABLED=false` |
| All pipelines broken | Full rollback | Azure deployment slot swap |

---

## 1. Feature Flags (Instant - No Deployment)

These environment variables can be changed in Azure Portal > Function App > Configuration without redeploying.

### Disable entire anti-hallucination pipeline
```
FACT_CHECK_ENABLED=false
```
- Effect: Skips enrichment AND verification. Articles generated raw.
- Risk: No fabrication detection. Use only if pipeline is blocking ALL articles.
- Restore: `FACT_CHECK_ENABLED=true`

### Disable enrichment only (keep verification)
```
FACT_CHECK_ENRICHMENT_ENABLED=false
```
- Effect: Skips Exa web search pre-enrichment. Verification still runs but with less context.
- Risk: Confidence scores will be lower. Articles may be shorter.
- Use when: Exa API is down or rate-limited.
- Restore: `FACT_CHECK_ENRICHMENT_ENABLED=true`

### Disable verification only (keep enrichment)
```
FACT_CHECK_VERIFICATION_ENABLED=false
```
- Effect: Skips post-generation claim/entity verification. No confidence scores.
- Risk: Fabrications not detected. Manual review becomes critical.
- Use when: Verification is producing too many false positives (>10% false block rate).
- Restore: `FACT_CHECK_VERIFICATION_ENABLED=true`

### Relax safety gates (emergency only)
```
PRODUCTION_SAFETY_MODE=false
```
- Effect: Reverts to legacy gates (3+ fabricated = block instead of 2+, confidence floor 0.40 instead of 0.50).
- Risk: More fabricated content may pass through.
- Use when: Production gates blocking >20% of articles incorrectly.
- Restore: `PRODUCTION_SAFETY_MODE=true`

### Disable decontamination
```
DECONTAMINATION_ENABLED=false
```
- Effect: Skips temporal decontamination check.
- Risk: Articles may contain outdated temporal references.
- Use when: Decontamination is incorrectly modifying valid content.
- Restore: `DECONTAMINATION_ENABLED=true`

### Disable auto-regeneration
```
MAX_REGENERATION_ATTEMPTS=0
```
- Effect: Disables automatic re-generation on fabrication detection.
- Risk: Articles with fabrications will require manual intervention.
- Use when: Auto-regen is consuming excessive LLM tokens or producing worse results.
- Restore: `MAX_REGENERATION_ATTEMPTS=1`

---

## 2. Deployment Rollback (Azure Slots)

### Swap to Previous Version
```bash
# List deployment slots
az functionapp deployment slot list \
  --name tmc-rss-collector \
  --resource-group tmc-production \
  --output table

# Swap staging (previous version) with production
az functionapp deployment slot swap \
  --name tmc-rss-collector \
  --resource-group tmc-production \
  --slot staging \
  --target-slot production
```

### Rollback to Specific Deployment
```bash
# List recent deployments
az functionapp deployment list \
  --name tmc-rss-collector \
  --resource-group tmc-production \
  --output table

# Redeploy a specific commit
az functionapp deployment source config-zip \
  --name tmc-rss-collector \
  --resource-group tmc-production \
  --src <path-to-previous-zip>
```

---

## 3. Database Rollback

### generation_audit_trail table
If migration 004 causes issues:
```sql
-- The audit trail is write-only and non-critical
-- Dropping it does not affect article generation
DROP TABLE IF EXISTS generation_audit_trail;
```
Note: Generation continues without audit trail; only observability is lost.

---

## 4. Emergency Scenarios

### Scenario A: Fabricated article published
1. **Immediate**: Unpublish the article from WordPress
2. **Investigate**: Check audit trail for the correlation_id
   ```sql
   SELECT * FROM generation_audit_trail
   WHERE correlation_id = '<id>'
   ORDER BY created_at DESC;
   ```
3. **Root cause**: Review verification data - was fabrication detected but not blocked?
4. **Mitigate**: Tighten safety gates if needed:
   - Lower `REGEN_FABRICATION_THRESHOLD` from 2 to 1
   - Set `PRODUCTION_SAFETY_MODE=true` if not already

### Scenario B: All articles being blocked
1. **Check**: Is this expected? (e.g., LLM model changed, sources are very short)
2. **Diagnose**: Check quality summary logs for patterns
   ```
   Look at confidence scores, fabrication counts, expansion ratios
   ```
3. **Quick fix**: `PRODUCTION_SAFETY_MODE=false` to relax gates temporarily
4. **Proper fix**: Adjust specific thresholds, not the global mode

### Scenario C: LLM provider outage
1. **Auto-handled**: Circuit breaker opens after consecutive failures
2. **Health endpoint**: `/api/health` will report `degraded` with `llm_service: circuit_open`
3. **Recovery**: Circuit half-opens automatically after cooldown period
4. **Manual override**: Restart function app to reset circuit breaker state
   ```bash
   az functionapp restart --name tmc-rss-collector --resource-group tmc-production
   ```

### Scenario D: Database connection issues
1. **Health endpoint**: `/api/health` returns 503 with `database: disconnected`
2. **Check**: Azure SQL status in portal
3. **Check**: Connection string env vars (SQL_SERVER, SQL_DATABASE, etc.)
4. **Check**: Firewall rules allow Function App's outbound IPs
5. **Increase timeout**: `SQL_QUERY_TIMEOUT=60` (default is 30)

### Scenario E: Rate limiting too aggressive
1. **Symptom**: Users seeing 429 errors frequently
2. **Adjust**:
   ```
   RATE_LIMIT_GENERATE=1.0     (was 0.5 - doubles allowed rate)
   RATE_LIMIT_BURST_GENERATE=5  (was 3 - allows more burst)
   ```
3. **Note**: Restart required for rate limiter changes to take effect

---

## 5. Monitoring After Rollback

After any rollback action, verify:

1. **Health check**: `curl https://api.tmc.com.br/api/health`
2. **Generate test**: Send a test article through the pipeline
3. **Metrics**: Check `/api/metrics` for error counters
4. **Logs**: Monitor Application Insights for 15 minutes
5. **Alert**: Confirm alerting rules still fire correctly
