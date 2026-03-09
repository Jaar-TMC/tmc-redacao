#!/bin/bash
# =============================================================================
# TMC - Script de Setup Google Cloud Platform
# =============================================================================
# Este script configura toda a infraestrutura necessária para o projeto TMC
#
# Pré-requisitos:
#   1. gcloud CLI instalado: https://cloud.google.com/sdk/docs/install
#   2. Conta Google Cloud com billing habilitado
#   3. Executar: gcloud auth login
#
# Uso:
#   chmod +x setup-gcp.sh
#   ./setup-gcp.sh
# =============================================================================

set -e  # Para execução em caso de erro

# =============================================================================
# CONFIGURAÇÕES - EDITE CONFORME NECESSÁRIO
# =============================================================================
PROJECT_ID="tmc-redacao"                    # ID do projeto GCP
PROJECT_NAME="TMC Ferramenta Redacao"       # Nome do projeto
REGION="southamerica-east1"                 # Região (São Paulo)
ZONE="southamerica-east1-a"                 # Zona

# Cloud SQL
DB_INSTANCE_NAME="tmc-database"
DB_NAME="tmc"
DB_USER="tmc_app"
DB_TIER="db-f1-micro"                       # db-f1-micro (barato) ou db-g1-small
DB_STORAGE="10GB"

# Cloud Run
CLOUD_RUN_SERVICE="tmc-api"
CLOUD_RUN_MEMORY="512Mi"
CLOUD_RUN_CPU="1"

# Artifact Registry
ARTIFACT_REPO="tmc-images"

# =============================================================================
# CORES PARA OUTPUT
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
log_error() { echo -e "${RED}[ERRO]${NC} $1"; }

# =============================================================================
# VERIFICAÇÕES INICIAIS
# =============================================================================
echo ""
echo "============================================================"
echo "  TMC - Setup Google Cloud Platform"
echo "============================================================"
echo ""

# Verificar se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI não encontrado!"
    echo "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

log_success "gcloud CLI encontrado"

# Verificar autenticação
ACCOUNT=$(gcloud config get-value account 2>/dev/null)
if [ -z "$ACCOUNT" ]; then
    log_warning "Não autenticado. Executando gcloud auth login..."
    gcloud auth login
fi
log_success "Autenticado como: $ACCOUNT"

# =============================================================================
# 1. CRIAR OU SELECIONAR PROJETO
# =============================================================================
echo ""
log_info "1. Configurando projeto..."

# Verificar se projeto existe
if gcloud projects describe $PROJECT_ID &>/dev/null; then
    log_success "Projeto $PROJECT_ID já existe"
else
    log_info "Criando projeto $PROJECT_ID..."
    gcloud projects create $PROJECT_ID --name="$PROJECT_NAME"
    log_success "Projeto criado"
fi

# Definir projeto como padrão
gcloud config set project $PROJECT_ID
log_success "Projeto definido: $PROJECT_ID"

# =============================================================================
# 2. HABILITAR BILLING (manual)
# =============================================================================
echo ""
log_warning "2. AÇÃO MANUAL NECESSÁRIA:"
echo "   Acesse: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo "   E vincule uma conta de faturamento ao projeto."
echo ""
read -p "Pressione ENTER após vincular o billing..."

# =============================================================================
# 3. HABILITAR APIs
# =============================================================================
echo ""
log_info "3. Habilitando APIs necessárias..."

APIS=(
    "run.googleapis.com"                 # Cloud Run
    "sqladmin.googleapis.com"            # Cloud SQL Admin
    "cloudscheduler.googleapis.com"      # Cloud Scheduler
    "secretmanager.googleapis.com"       # Secret Manager
    "cloudbuild.googleapis.com"          # Cloud Build
    "artifactregistry.googleapis.com"    # Artifact Registry
    "compute.googleapis.com"             # Compute Engine
    "servicenetworking.googleapis.com"   # Service Networking
    "vpcaccess.googleapis.com"           # VPC Access
)

for api in "${APIS[@]}"; do
    log_info "  Habilitando $api..."
    gcloud services enable $api --quiet
done
log_success "Todas as APIs habilitadas"

# =============================================================================
# 4. CRIAR ARTIFACT REGISTRY
# =============================================================================
echo ""
log_info "4. Criando Artifact Registry..."

if gcloud artifacts repositories describe $ARTIFACT_REPO --location=$REGION &>/dev/null; then
    log_success "Repositório $ARTIFACT_REPO já existe"
else
    gcloud artifacts repositories create $ARTIFACT_REPO \
        --repository-format=docker \
        --location=$REGION \
        --description="Imagens Docker TMC"
    log_success "Repositório criado: $ARTIFACT_REPO"
fi

# =============================================================================
# 5. CRIAR CLOUD SQL (PostgreSQL)
# =============================================================================
echo ""
log_info "5. Criando instância Cloud SQL..."

if gcloud sql instances describe $DB_INSTANCE_NAME &>/dev/null; then
    log_success "Instância $DB_INSTANCE_NAME já existe"
else
    log_info "  Criando instância PostgreSQL (pode levar alguns minutos)..."
    gcloud sql instances create $DB_INSTANCE_NAME \
        --database-version=POSTGRES_15 \
        --tier=$DB_TIER \
        --region=$REGION \
        --storage-size=10GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --availability-type=zonal \
        --root-password="$(openssl rand -base64 24)"
    log_success "Instância Cloud SQL criada"
fi

# Criar banco de dados
log_info "  Criando banco de dados $DB_NAME..."
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE_NAME 2>/dev/null || log_warning "Banco já existe"

# Gerar senha segura para o usuário
DB_PASSWORD=$(openssl rand -base64 24)

# Criar usuário
log_info "  Criando usuário $DB_USER..."
gcloud sql users create $DB_USER \
    --instance=$DB_INSTANCE_NAME \
    --password="$DB_PASSWORD" 2>/dev/null || log_warning "Usuário já existe"

log_success "Cloud SQL configurado"

# =============================================================================
# 6. CRIAR SECRETS NO SECRET MANAGER
# =============================================================================
echo ""
log_info "6. Configurando Secret Manager..."

# Senha do banco
log_info "  Criando secret: tmc-db-password"
echo -n "$DB_PASSWORD" | gcloud secrets create tmc-db-password --data-file=- 2>/dev/null || \
    (echo -n "$DB_PASSWORD" | gcloud secrets versions add tmc-db-password --data-file=-)

# Placeholder para API Key Anthropic
log_info "  Criando secret: tmc-anthropic-api-key"
echo -n "SUBSTITUA_PELA_CHAVE_REAL" | gcloud secrets create tmc-anthropic-api-key --data-file=- 2>/dev/null || \
    log_warning "Secret já existe"

log_success "Secrets configurados"
log_warning "IMPORTANTE: Atualize o secret tmc-anthropic-api-key com a chave real da Anthropic"

# =============================================================================
# 7. CRIAR SERVICE ACCOUNTS
# =============================================================================
echo ""
log_info "7. Criando Service Accounts..."

# Service Account para Cloud Run
SA_CLOUDRUN="tmc-api-sa"
SA_CLOUDRUN_EMAIL="$SA_CLOUDRUN@$PROJECT_ID.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SA_CLOUDRUN_EMAIL &>/dev/null; then
    log_success "Service Account $SA_CLOUDRUN já existe"
else
    gcloud iam service-accounts create $SA_CLOUDRUN \
        --display-name="TMC API Service Account"
    log_success "Service Account criada: $SA_CLOUDRUN"
fi

# Permissões para Cloud Run SA
log_info "  Configurando permissões..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_CLOUDRUN_EMAIL" \
    --role="roles/cloudsql.client" --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_CLOUDRUN_EMAIL" \
    --role="roles/secretmanager.secretAccessor" --quiet

log_success "Permissões configuradas"

# =============================================================================
# 8. CRIAR VPC CONNECTOR (para Cloud Run -> Cloud SQL)
# =============================================================================
echo ""
log_info "8. Criando VPC Connector..."

VPC_CONNECTOR="tmc-vpc-connector"

if gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR --region=$REGION &>/dev/null; then
    log_success "VPC Connector $VPC_CONNECTOR já existe"
else
    gcloud compute networks vpc-access connectors create $VPC_CONNECTOR \
        --region=$REGION \
        --range="10.8.0.0/28" \
        --network=default
    log_success "VPC Connector criado"
fi

# =============================================================================
# 9. OBTER INFORMAÇÕES DE CONEXÃO
# =============================================================================
echo ""
log_info "9. Obtendo informações de conexão..."

# IP do Cloud SQL
DB_IP=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(ipAddresses[0].ipAddress)")
DB_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")

log_success "Cloud SQL IP: $DB_IP"
log_success "Connection Name: $DB_CONNECTION_NAME"

# =============================================================================
# 10. CRIAR CLOUD SCHEDULER JOB (após deploy do Cloud Run)
# =============================================================================
echo ""
log_info "10. Cloud Scheduler será configurado após o deploy do Cloud Run"
log_warning "Execute o seguinte comando após o deploy:"
echo ""
echo "gcloud scheduler jobs create http tmc-rss-collector \\"
echo "    --location=$REGION \\"
echo "    --schedule=\"*/15 * * * *\" \\"
echo "    --uri=\"https://\$CLOUD_RUN_URL/api/collect\" \\"
echo "    --http-method=POST \\"
echo "    --time-zone=\"America/Sao_Paulo\" \\"
echo "    --oidc-service-account-email=$SA_CLOUDRUN_EMAIL"
echo ""

# =============================================================================
# RESUMO FINAL
# =============================================================================
echo ""
echo "============================================================"
echo "  SETUP CONCLUÍDO!"
echo "============================================================"
echo ""
echo "RECURSOS CRIADOS:"
echo "  - Projeto: $PROJECT_ID"
echo "  - Cloud SQL: $DB_INSTANCE_NAME ($DB_TIER)"
echo "  - Banco: $DB_NAME"
echo "  - Artifact Registry: $ARTIFACT_REPO"
echo "  - VPC Connector: $VPC_CONNECTOR"
echo "  - Service Account: $SA_CLOUDRUN_EMAIL"
echo ""
echo "INFORMAÇÕES DE CONEXÃO DO BANCO:"
echo "  - Host: $DB_IP"
echo "  - Database: $DB_NAME"
echo "  - User: $DB_USER"
echo "  - Password: (armazenada no Secret Manager: tmc-db-password)"
echo "  - Connection Name: $DB_CONNECTION_NAME"
echo ""
echo "PRÓXIMOS PASSOS:"
echo "  1. Atualize o secret tmc-anthropic-api-key com sua chave Anthropic"
echo "  2. Faça o build e deploy da aplicação (veja deploy.sh)"
echo "  3. Configure o Cloud Scheduler após o deploy"
echo "  4. Configure o Firebase Hosting para o frontend"
echo ""
echo "============================================================"

# Salvar variáveis em arquivo para uso posterior
cat > .env.gcp << EOF
PROJECT_ID=$PROJECT_ID
REGION=$REGION
DB_INSTANCE_NAME=$DB_INSTANCE_NAME
DB_CONNECTION_NAME=$DB_CONNECTION_NAME
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_IP=$DB_IP
CLOUD_RUN_SERVICE=$CLOUD_RUN_SERVICE
ARTIFACT_REPO=$ARTIFACT_REPO
VPC_CONNECTOR=$VPC_CONNECTOR
SA_CLOUDRUN_EMAIL=$SA_CLOUDRUN_EMAIL
EOF

log_success "Variáveis salvas em .env.gcp"
