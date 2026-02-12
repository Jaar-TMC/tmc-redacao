# ============================================================
# TMC Pipeline - P1 Alert Rules Setup (PowerShell)
# ============================================================
# Prerequisites:
#   - Azure CLI logged in with Monitoring Contributor on tmc-rg
#   - Or run as subscription Owner/Contributor
#
# Usage: .\setup_p1_alerts.ps1
# ============================================================

$SUBSCRIPTION = "e4d98671-d06b-4449-b551-3aa14439ff41"
$RESOURCE_GROUP = "tmc-rg"
$APP_INSIGHTS_ID = "/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/components/tmc-redacao-api"
$LOCATION = "eastus2"
$ALERT_EMAIL = "enzo.oliveira@jaarconsult.com.br"

# --- Step 0: Grant permissions (run as Owner) ---
Write-Host "=== Step 0: Grant Monitoring Contributor (run as Owner) ===" -ForegroundColor Yellow
Write-Host "az role assignment create --assignee $ALERT_EMAIL --role 'Monitoring Contributor' --scope /subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP"
Write-Host ""

# --- Step 1: Create Action Group ---
Write-Host "=== Step 1: Create Action Group (tmc-critical) ===" -ForegroundColor Cyan

$actionGroupBody = @{
    location = "global"
    properties = @{
        groupShortName = "tmc-crit"
        enabled = $true
        emailReceivers = @(
            @{
                name = "tmc-tech-lead"
                emailAddress = $ALERT_EMAIL
                useCommonAlertSchema = $true
            }
        )
    }
} | ConvertTo-Json -Depth 5

az rest --method put `
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/tmc-critical?api-version=2023-09-01-preview" `
    --body $actionGroupBody

Write-Host ""

# --- Step 2: P1 Alert - High Fabrication Rate ---
Write-Host "=== Step 2: Create P1 Alert - High Fabrication Rate ===" -ForegroundColor Cyan

$fabricationQuery = "traces | where message has '[QUALITY_SUMMARY]' | extend quality = parse_json(extract(@'\[QUALITY_SUMMARY\]\s*(.*)', 1, message)) | extend fabricated = toint(quality.fabricated_claims) | summarize total = count(), with_fabrication = countif(fabricated > 0), fabrication_rate_pct = round(100.0 * countif(fabricated > 0) / count(), 1) | where total >= 3 and fabrication_rate_pct > 2.0"

$fabricationBody = @{
    location = $LOCATION
    properties = @{
        displayName = "P1: High Fabrication Rate (>2%)"
        description = "CRITICAL: Article fabrication rate exceeds 2% over 1-hour window. Investigate LLM model changes or prompt regression."
        severity = 1
        enabled = $true
        evaluationFrequency = "PT15M"
        scopes = @($APP_INSIGHTS_ID)
        windowSize = "PT1H"
        criteria = @{
            allOf = @(
                @{
                    query = $fabricationQuery
                    timeAggregation = "Count"
                    dimensions = @()
                    operator = "GreaterThan"
                    threshold = 0
                    failingPeriods = @{
                        numberOfEvaluationPeriods = 1
                        minFailingPeriodsToAlert = 1
                    }
                }
            )
        }
        actions = @{
            actionGroups = @(
                "/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/tmc-critical"
            )
        }
    }
} | ConvertTo-Json -Depth 10

az rest --method put `
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/scheduledQueryRules/tmc-p1-fabrication-rate?api-version=2023-03-15-preview" `
    --body $fabricationBody

Write-Host ""

# --- Step 3: P1 Alert - Verification Pipeline Offline ---
Write-Host "=== Step 3: Create P1 Alert - Verification Pipeline Offline ===" -ForegroundColor Cyan

$verificationQuery = "traces | where message has 'Phase 3 verification' or message has 'verification failed' or message has '[QUALITY_SUMMARY]' | extend is_failure = (message has 'failed' or message has 'error') | extend is_quality = message has '[QUALITY_SUMMARY]' | summarize total_generations = countif(is_quality), verification_failures = countif(is_failure) | extend failure_rate_pct = round(100.0 * verification_failures / max_of(total_generations, 1), 1) | where total_generations >= 3 and failure_rate_pct > 10.0"

$verificationBody = @{
    location = $LOCATION
    properties = @{
        displayName = "P1: Verification Pipeline Offline (>10% failures)"
        description = "CRITICAL: Anti-hallucination verification pipeline failure rate exceeds 10%. All unverified articles need manual review."
        severity = 1
        enabled = $true
        evaluationFrequency = "PT15M"
        scopes = @($APP_INSIGHTS_ID)
        windowSize = "PT1H"
        criteria = @{
            allOf = @(
                @{
                    query = $verificationQuery
                    timeAggregation = "Count"
                    dimensions = @()
                    operator = "GreaterThan"
                    threshold = 0
                    failingPeriods = @{
                        numberOfEvaluationPeriods = 1
                        minFailingPeriodsToAlert = 1
                    }
                }
            )
        }
        actions = @{
            actionGroups = @(
                "/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/actionGroups/tmc-critical"
            )
        }
    }
} | ConvertTo-Json -Depth 10

az rest --method put `
    --url "https://management.azure.com/subscriptions/$SUBSCRIPTION/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/scheduledQueryRules/tmc-p1-verification-offline?api-version=2023-03-15-preview" `
    --body $verificationBody

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "Created:"
Write-Host "  - Action Group: tmc-critical (emails $ALERT_EMAIL)"
Write-Host "  - Alert: tmc-p1-fabrication-rate (Sev 1, every 15min, 1h window)"
Write-Host "  - Alert: tmc-p1-verification-offline (Sev 1, every 15min, 1h window)"
Write-Host ""
Write-Host "Verify in Azure Portal: Monitor > Alerts > Alert rules"
