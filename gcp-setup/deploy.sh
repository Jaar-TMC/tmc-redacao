#!/bin/bash
# =============================================================================
# TMC - Script de Deploy para Google Cloud
# =============================================================================
# Este script faz o build e deploy da aplicação no Cloud Run
#
# Uso:
#   chmod +x deploy.sh
#   ./deploy.sh
# =============================================================================

set -e

# Carregar variáveis do setup
if [ -f .env.gcp ]; then
    source .env.gcp
else
    echo "Arquivo .env.gcp não encontrado. Execute setup-gcp.sh primeiro."
    exit 1
fi

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }

echo ""
echo "============================================================"
echo "  TMC - Deploy para Google Cloud Run"
echo "============================================================"
echo ""

# =============================================================================
# 1. BUILD DA IMAGEM DOCKER
# =============================================================================
log_info "1. Fazendo build da imagem Docker..."

IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REPO/$CLOUD_RUN_SERVICE:latest"

# Configurar Docker para usar Artifact Registry
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

# Build usando Cloud Build (recomendado) ou local
log_info "   Usando Cloud Build para construir a imagem..."
gcloud builds submit ../FeedRSS/tmc-rss-collector \
    --tag=$IMAGE_URL \
    --timeout=600

log_success "Imagem construída: $IMAGE_URL"

# =============================================================================
# 2. DEPLOY NO CLOUD RUN
# =============================================================================
log_info "2. Fazendo deploy no Cloud Run..."

gcloud run deploy $CLOUD_RUN_SERVICE \
    --image=$IMAGE_URL \
    --platform=managed \
    --region=$REGION \
    --service-account=$SA_CLOUDRUN_EMAIL \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --concurrency=80 \
    --vpc-connector=$VPC_CONNECTOR \
    --set-env-vars="DB_HOST=/cloudsql/$DB_CONNECTION_NAME" \
    --set-env-vars="DB_NAME=$DB_NAME" \
    --set-env-vars="DB_USER=$DB_USER" \
    --set-env-vars="DB_PORT=5432" \
    --set-secrets="DB_PASSWORD=tmc-db-password:latest" \
    --set-secrets="ANTHROPIC_API_KEY=tmc-anthropic-api-key:latest" \
    --add-cloudsql-instances=$DB_CONNECTION_NAME \
    --allow-unauthenticated

log_success "Deploy concluído"

# =============================================================================
# 3. OBTER URL DO SERVIÇO
# =============================================================================
CLOUD_RUN_URL=$(gcloud run services describe $CLOUD_RUN_SERVICE --region=$REGION --format="value(status.url)")

log_success "URL do serviço: $CLOUD_RUN_URL"

# =============================================================================
# 4. CONFIGURAR CLOUD SCHEDULER
# =============================================================================
log_info "3. Configurando Cloud Scheduler..."

# Verificar se job existe
if gcloud scheduler jobs describe tmc-rss-collector --location=$REGION &>/dev/null; then
    log_info "   Atualizando job existente..."
    gcloud scheduler jobs update http tmc-rss-collector \
        --location=$REGION \
        --schedule="*/15 * * * *" \
        --uri="$CLOUD_RUN_URL/api/collect" \
        --http-method=POST \
        --time-zone="America/Sao_Paulo" \
        --oidc-service-account-email=$SA_CLOUDRUN_EMAIL
else
    log_info "   Criando novo job..."
    gcloud scheduler jobs create http tmc-rss-collector \
        --location=$REGION \
        --schedule="*/15 * * * *" \
        --uri="$CLOUD_RUN_URL/api/collect" \
        --http-method=POST \
        --time-zone="America/Sao_Paulo" \
        --oidc-service-account-email=$SA_CLOUDRUN_EMAIL
fi

log_success "Cloud Scheduler configurado"

# =============================================================================
# RESUMO
# =============================================================================
echo ""
echo "============================================================"
echo "  DEPLOY CONCLUÍDO!"
echo "============================================================"
echo ""
echo "URL da API: $CLOUD_RUN_URL"
echo ""
echo "Endpoints disponíveis:"
echo "  - GET  $CLOUD_RUN_URL/api/health"
echo "  - GET  $CLOUD_RUN_URL/api/articles"
echo "  - GET  $CLOUD_RUN_URL/api/sources"
echo "  - GET  $CLOUD_RUN_URL/api/categories"
echo "  - POST $CLOUD_RUN_URL/api/generate"
echo ""
echo "Teste rápido:"
echo "  curl $CLOUD_RUN_URL/api/health"
echo ""
echo "============================================================"

# Atualizar .env.gcp com a URL
echo "CLOUD_RUN_URL=$CLOUD_RUN_URL" >> .env.gcp
