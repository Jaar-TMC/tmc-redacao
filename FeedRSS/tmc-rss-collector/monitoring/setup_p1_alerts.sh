#!/bin/bash
# ============================================================
# TMC Pipeline - P1 Alert Rules Setup
# ============================================================
# Prerequisites:
#   - Azure CLI logged in with Monitoring Contributor on tmc-rg
#   - Or run as subscription Owner/Contributor
#
# Resources created:
#   1. Action Group: tmc-critical (email notification)
#   2. Alert Rule: tmc-p1-fabrication-rate (fabrication > 2%)
#   3. Alert Rule: tmc-p1-verification-offline (verification failures > 10%)
# ============================================================

SUBSCRIPTION="e4d98671-d06b-4449-b551-3aa14439ff41"
RESOURCE_GROUP="tmc-rg"
APP_INSIGHTS_ID="/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/components/tmc-redacao-api"
LOCATION="eastus2"

# Change this to the actual alert recipient
ALERT_EMAIL="enzo.oliveira@jaarconsult.com.br"

echo "=== Step 1: Create Action Group (tmc-critical) ==="

az rest --method put \
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/tmc-critical?api-version=2023-09-01-preview" \
  --body "{
    \"location\": \"global\",
    \"properties\": {
      \"groupShortName\": \"tmc-crit\",
      \"enabled\": true,
      \"emailReceivers\": [
        {
          \"name\": \"tmc-tech-lead\",
          \"emailAddress\": \"$ALERT_EMAIL\",
          \"useCommonAlertSchema\": true
        }
      ]
    }
  }"

echo ""
echo "=== Step 2: Create P1 Alert - High Fabrication Rate ==="

# Alert fires when fabrication rate exceeds 2% over a 1-hour window
# Evaluated every 15 minutes
az rest --method put \
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/scheduledQueryRules/tmc-p1-fabrication-rate?api-version=2023-03-15-preview" \
  --body "{
    \"location\": \"$LOCATION\",
    \"properties\": {
      \"displayName\": \"P1: High Fabrication Rate (>2%)\",
      \"description\": \"CRITICAL: Article fabrication rate exceeds 2% over 1-hour window. Investigate LLM model changes or prompt regression. If sustained, check PRODUCTION_SAFETY_MODE and consider rollback.\",
      \"severity\": 1,
      \"enabled\": true,
      \"evaluationFrequency\": \"PT15M\",
      \"scopes\": [\"$APP_INSIGHTS_ID\"],
      \"windowSize\": \"PT1H\",
      \"criteria\": {
        \"allOf\": [
          {
            \"query\": \"traces | where message has '[QUALITY_SUMMARY]' | extend quality = parse_json(extract(@'\\\\[QUALITY_SUMMARY\\\\]\\\\s*(.*)', 1, message)) | extend fabricated = toint(quality.fabricated_claims) | summarize total = count(), with_fabrication = countif(fabricated > 0), fabrication_rate_pct = round(100.0 * countif(fabricated > 0) / count(), 1) | where total >= 3 and fabrication_rate_pct > 2.0\",
            \"timeAggregation\": \"Count\",
            \"dimensions\": [],
            \"operator\": \"GreaterThan\",
            \"threshold\": 0,
            \"failingPeriods\": {
              \"numberOfEvaluationPeriods\": 1,
              \"minFailingPeriodsToAlert\": 1
            }
          }
        ]
      },
      \"actions\": {
        \"actionGroups\": [
          \"/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/tmc-critical\"
        ]
      }
    }
  }"

echo ""
echo "=== Step 3: Create P1 Alert - Verification Pipeline Offline ==="

# Alert fires when verification failure rate exceeds 10% over 1-hour window
# This means the anti-hallucination safety net is degraded
az rest --method put \
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/scheduledQueryRules/tmc-p1-verification-offline?api-version=2023-03-15-preview" \
  --body "{
    \"location\": \"$LOCATION\",
    \"properties\": {
      \"displayName\": \"P1: Verification Pipeline Offline (>10% failures)\",
      \"description\": \"CRITICAL: Anti-hallucination verification pipeline failure rate exceeds 10%. All unverified articles need manual review. Check Exa API status and LLM availability.\",
      \"severity\": 1,
      \"enabled\": true,
      \"evaluationFrequency\": \"PT15M\",
      \"scopes\": [\"$APP_INSIGHTS_ID\"],
      \"windowSize\": \"PT1H\",
      \"criteria\": {
        \"allOf\": [
          {
            \"query\": \"traces | where message has 'Phase 3 verification' or message has 'verification failed' or message has '[QUALITY_SUMMARY]' | extend is_failure = (message has 'failed' or message has 'error') | extend is_quality = message has '[QUALITY_SUMMARY]' | summarize total_generations = countif(is_quality), verification_failures = countif(is_failure) | extend failure_rate_pct = round(100.0 * verification_failures / max_of(total_generations, 1), 1) | where total_generations >= 3 and failure_rate_pct > 10.0\",
            \"timeAggregation\": \"Count\",
            \"dimensions\": [],
            \"operator\": \"GreaterThan\",
            \"threshold\": 0,
            \"failingPeriods\": {
              \"numberOfEvaluationPeriods\": 1,
              \"minFailingPeriodsToAlert\": 1
            }
          }
        ]
      },
      \"actions\": {
        \"actionGroups\": [
          \"/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/tmc-critical\"
        ]
      }
    }
  }"

echo ""
echo "=== Done ==="
echo "Created:"
echo "  - Action Group: tmc-critical (emails $ALERT_EMAIL)"
echo "  - Alert: tmc-p1-fabrication-rate (Sev 1, every 15min, 1h window)"
echo "  - Alert: tmc-p1-verification-offline (Sev 1, every 15min, 1h window)"
echo ""
echo "Verify in Azure Portal: Monitor > Alerts > Alert rules"
