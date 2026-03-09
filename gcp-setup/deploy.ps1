# =============================================================================
# TMC - Script de Deploy para Google Cloud (PowerShell)
# =============================================================================
# Uso: .\deploy.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# Carregar variáveis
if (Test-Path ".env.gcp") {
    Get-Content ".env.gcp" | ForEach-Object {
        if ($_ -match "^(.+)=(.+)$") {
            Set-Variable -Name $matches[1] -Value $matches[2] -Scope Script
        }
    }
} else {
    Write-Host "Arquivo .env.gcp não encontrado. Execute setup-gcp.ps1 primeiro." -ForegroundColor Red
    exit 1
}

function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }

Write-Host ""
Write-Host "============================================================"
Write-Host "  TMC - Deploy para Google Cloud Run"
Write-Host "============================================================"
Write-Host ""

# =============================================================================
# 1. BUILD DA IMAGEM
# =============================================================================
Write-Info "1. Fazendo build da imagem Docker..."

$IMAGE_URL = "$REGION-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REPO/${CLOUD_RUN_SERVICE}:latest"

gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

Write-Info "   Usando Cloud Build..."
gcloud builds submit "..\FeedRSS\tmc-rss-collector" `
    --tag=$IMAGE_URL `
    --timeout=600

Write-Success "Imagem construída: $IMAGE_URL"

# =============================================================================
# 2. DEPLOY NO CLOUD RUN
# =============================================================================
Write-Info "2. Fazendo deploy no Cloud Run..."

gcloud run deploy $CLOUD_RUN_SERVICE `
    --image=$IMAGE_URL `
    --platform=managed `
    --region=$REGION `
    --service-account=$SA_CLOUDRUN_EMAIL `
    --memory=512Mi `
    --cpu=1 `
    --min-instances=0 `
    --max-instances=10 `
    --timeout=300 `
    --concurrency=80 `
    --vpc-connector=$VPC_CONNECTOR `
    --set-env-vars="DB_HOST=/cloudsql/$DB_CONNECTION_NAME" `
    --set-env-vars="DB_NAME=$DB_NAME" `
    --set-env-vars="DB_USER=$DB_USER" `
    --set-env-vars="DB_PORT=5432" `
    --set-secrets="DB_PASSWORD=tmc-db-password:latest" `
    --set-secrets="ANTHROPIC_API_KEY=tmc-anthropic-api-key:latest" `
    --add-cloudsql-instances=$DB_CONNECTION_NAME `
    --allow-unauthenticated

Write-Success "Deploy concluído"

# =============================================================================
# 3. OBTER URL
# =============================================================================
$CLOUD_RUN_URL = gcloud run services describe $CLOUD_RUN_SERVICE --region=$REGION --format="value(status.url)"
Write-Success "URL do serviço: $CLOUD_RUN_URL"

# =============================================================================
# 4. CONFIGURAR SCHEDULER
# =============================================================================
Write-Info "3. Configurando Cloud Scheduler..."

$jobExists = gcloud scheduler jobs describe tmc-rss-collector --location=$REGION 2>$null
if ($jobExists) {
    Write-Info "   Atualizando job existente..."
    gcloud scheduler jobs update http tmc-rss-collector `
        --location=$REGION `
        --schedule="*/15 * * * *" `
        --uri="$CLOUD_RUN_URL/api/collect" `
        --http-method=POST `
        --time-zone="America/Sao_Paulo" `
        --oidc-service-account-email=$SA_CLOUDRUN_EMAIL
} else {
    Write-Info "   Criando novo job..."
    gcloud scheduler jobs create http tmc-rss-collector `
        --location=$REGION `
        --schedule="*/15 * * * *" `
        --uri="$CLOUD_RUN_URL/api/collect" `
        --http-method=POST `
        --time-zone="America/Sao_Paulo" `
        --oidc-service-account-email=$SA_CLOUDRUN_EMAIL
}

Write-Success "Cloud Scheduler configurado"

# =============================================================================
# RESUMO
# =============================================================================
Write-Host ""
Write-Host "============================================================"
Write-Host "  DEPLOY CONCLUÍDO!"
Write-Host "============================================================"
Write-Host ""
Write-Host "URL da API: $CLOUD_RUN_URL"
Write-Host ""
Write-Host "Teste: curl $CLOUD_RUN_URL/api/health"
Write-Host ""
Write-Host "============================================================"

# Salvar URL
Add-Content -Path ".env.gcp" -Value "CLOUD_RUN_URL=$CLOUD_RUN_URL"
