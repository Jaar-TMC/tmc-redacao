# =============================================================================
# TMC - Script de Setup Google Cloud Platform (PowerShell)
# =============================================================================
# Este script configura toda a infraestrutura necessária para o projeto TMC
#
# Pré-requisitos:
#   1. gcloud CLI instalado: https://cloud.google.com/sdk/docs/install
#   2. Conta Google Cloud com billing habilitado
#   3. Executar: gcloud auth login
#
# Uso:
#   .\setup-gcp.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# =============================================================================
# CONFIGURAÇÕES - EDITE CONFORME NECESSÁRIO
# =============================================================================
$PROJECT_ID = "tmc-redacao"
$PROJECT_NAME = "TMC Ferramenta Redacao"
$REGION = "southamerica-east1"
$ZONE = "southamerica-east1-a"

# Cloud SQL
$DB_INSTANCE_NAME = "tmc-database"
$DB_NAME = "tmc"
$DB_USER = "tmc_app"
$DB_TIER = "db-f1-micro"

# Cloud Run
$CLOUD_RUN_SERVICE = "tmc-api"
$ARTIFACT_REPO = "tmc-images"
$VPC_CONNECTOR = "tmc-vpc-connector"

# =============================================================================
# FUNÇÕES
# =============================================================================
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[AVISO] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERRO] $msg" -ForegroundColor Red }

function Generate-Password {
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%"
    -join ((1..24) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
}

# =============================================================================
# INÍCIO
# =============================================================================
Write-Host ""
Write-Host "============================================================"
Write-Host "  TMC - Setup Google Cloud Platform"
Write-Host "============================================================"
Write-Host ""

# Verificar gcloud
try {
    $null = gcloud version 2>$null
    Write-Success "gcloud CLI encontrado"
} catch {
    Write-Err "gcloud CLI não encontrado!"
    Write-Host "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Verificar autenticação
$ACCOUNT = gcloud config get-value account 2>$null
if (-not $ACCOUNT) {
    Write-Warn "Não autenticado. Executando gcloud auth login..."
    gcloud auth login
}
Write-Success "Autenticado como: $ACCOUNT"

# =============================================================================
# 1. CRIAR OU SELECIONAR PROJETO
# =============================================================================
Write-Host ""
Write-Info "1. Configurando projeto..."

$projectExists = gcloud projects describe $PROJECT_ID 2>$null
if ($projectExists) {
    Write-Success "Projeto $PROJECT_ID já existe"
} else {
    Write-Info "Criando projeto $PROJECT_ID..."
    gcloud projects create $PROJECT_ID --name="$PROJECT_NAME"
    Write-Success "Projeto criado"
}

gcloud config set project $PROJECT_ID
Write-Success "Projeto definido: $PROJECT_ID"

# =============================================================================
# 2. HABILITAR BILLING
# =============================================================================
Write-Host ""
Write-Warn "2. AÇÃO MANUAL NECESSÁRIA:"
Write-Host "   Acesse: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
Write-Host "   E vincule uma conta de faturamento ao projeto."
Write-Host ""
Read-Host "Pressione ENTER após vincular o billing..."

# =============================================================================
# 3. HABILITAR APIs
# =============================================================================
Write-Host ""
Write-Info "3. Habilitando APIs necessárias..."

$APIS = @(
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "cloudscheduler.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com"
)

foreach ($api in $APIS) {
    Write-Info "  Habilitando $api..."
    gcloud services enable $api --quiet
}
Write-Success "Todas as APIs habilitadas"

# =============================================================================
# 4. CRIAR ARTIFACT REGISTRY
# =============================================================================
Write-Host ""
Write-Info "4. Criando Artifact Registry..."

$repoExists = gcloud artifacts repositories describe $ARTIFACT_REPO --location=$REGION 2>$null
if ($repoExists) {
    Write-Success "Repositório $ARTIFACT_REPO já existe"
} else {
    gcloud artifacts repositories create $ARTIFACT_REPO `
        --repository-format=docker `
        --location=$REGION `
        --description="Imagens Docker TMC"
    Write-Success "Repositório criado: $ARTIFACT_REPO"
}

# =============================================================================
# 5. CRIAR CLOUD SQL
# =============================================================================
Write-Host ""
Write-Info "5. Criando instância Cloud SQL..."

$instanceExists = gcloud sql instances describe $DB_INSTANCE_NAME 2>$null
if ($instanceExists) {
    Write-Success "Instância $DB_INSTANCE_NAME já existe"
} else {
    Write-Info "  Criando instância PostgreSQL (pode levar alguns minutos)..."
    $rootPassword = Generate-Password
    gcloud sql instances create $DB_INSTANCE_NAME `
        --database-version=POSTGRES_15 `
        --tier=$DB_TIER `
        --region=$REGION `
        --storage-size=10GB `
        --storage-auto-increase `
        --backup-start-time=03:00 `
        --availability-type=zonal `
        --root-password="$rootPassword"
    Write-Success "Instância Cloud SQL criada"
}

# Criar banco de dados
Write-Info "  Criando banco de dados $DB_NAME..."
try {
    gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE_NAME 2>$null
} catch {
    Write-Warn "Banco já existe"
}

# Gerar senha e criar usuário
$DB_PASSWORD = Generate-Password
Write-Info "  Criando usuário $DB_USER..."
try {
    gcloud sql users create $DB_USER `
        --instance=$DB_INSTANCE_NAME `
        --password="$DB_PASSWORD" 2>$null
} catch {
    Write-Warn "Usuário já existe"
}

Write-Success "Cloud SQL configurado"

# =============================================================================
# 6. CRIAR SECRETS
# =============================================================================
Write-Host ""
Write-Info "6. Configurando Secret Manager..."

Write-Info "  Criando secret: tmc-db-password"
try {
    $DB_PASSWORD | gcloud secrets create tmc-db-password --data-file=- 2>$null
} catch {
    $DB_PASSWORD | gcloud secrets versions add tmc-db-password --data-file=-
}

Write-Info "  Criando secret: tmc-anthropic-api-key"
try {
    "SUBSTITUA_PELA_CHAVE_REAL" | gcloud secrets create tmc-anthropic-api-key --data-file=- 2>$null
} catch {
    Write-Warn "Secret já existe"
}

Write-Success "Secrets configurados"
Write-Warn "IMPORTANTE: Atualize o secret tmc-anthropic-api-key com a chave real"

# =============================================================================
# 7. CRIAR SERVICE ACCOUNT
# =============================================================================
Write-Host ""
Write-Info "7. Criando Service Account..."

$SA_CLOUDRUN = "tmc-api-sa"
$SA_CLOUDRUN_EMAIL = "$SA_CLOUDRUN@$PROJECT_ID.iam.gserviceaccount.com"

$saExists = gcloud iam service-accounts describe $SA_CLOUDRUN_EMAIL 2>$null
if ($saExists) {
    Write-Success "Service Account $SA_CLOUDRUN já existe"
} else {
    gcloud iam service-accounts create $SA_CLOUDRUN `
        --display-name="TMC API Service Account"
    Write-Success "Service Account criada"
}

Write-Info "  Configurando permissões..."
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_CLOUDRUN_EMAIL" `
    --role="roles/cloudsql.client" --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_CLOUDRUN_EMAIL" `
    --role="roles/secretmanager.secretAccessor" --quiet

Write-Success "Permissões configuradas"

# =============================================================================
# 8. CRIAR VPC CONNECTOR
# =============================================================================
Write-Host ""
Write-Info "8. Criando VPC Connector..."

$vpcExists = gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR --region=$REGION 2>$null
if ($vpcExists) {
    Write-Success "VPC Connector já existe"
} else {
    gcloud compute networks vpc-access connectors create $VPC_CONNECTOR `
        --region=$REGION `
        --range="10.8.0.0/28" `
        --network=default
    Write-Success "VPC Connector criado"
}

# =============================================================================
# 9. OBTER INFORMAÇÕES
# =============================================================================
Write-Host ""
Write-Info "9. Obtendo informações de conexão..."

$DB_IP = gcloud sql instances describe $DB_INSTANCE_NAME --format="value(ipAddresses[0].ipAddress)"
$DB_CONNECTION_NAME = gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)"

Write-Success "Cloud SQL IP: $DB_IP"
Write-Success "Connection Name: $DB_CONNECTION_NAME"

# =============================================================================
# RESUMO
# =============================================================================
Write-Host ""
Write-Host "============================================================"
Write-Host "  SETUP CONCLUÍDO!"
Write-Host "============================================================"
Write-Host ""
Write-Host "RECURSOS CRIADOS:"
Write-Host "  - Projeto: $PROJECT_ID"
Write-Host "  - Cloud SQL: $DB_INSTANCE_NAME"
Write-Host "  - Banco: $DB_NAME"
Write-Host "  - Artifact Registry: $ARTIFACT_REPO"
Write-Host "  - VPC Connector: $VPC_CONNECTOR"
Write-Host "  - Service Account: $SA_CLOUDRUN_EMAIL"
Write-Host ""
Write-Host "CONEXÃO DO BANCO:"
Write-Host "  - Host: $DB_IP"
Write-Host "  - Database: $DB_NAME"
Write-Host "  - User: $DB_USER"
Write-Host "  - Password: (Secret Manager: tmc-db-password)"
Write-Host "  - Connection Name: $DB_CONNECTION_NAME"
Write-Host ""
Write-Host "PRÓXIMOS PASSOS:"
Write-Host "  1. Atualize o secret tmc-anthropic-api-key"
Write-Host "  2. Execute deploy.ps1 para deploy do backend"
Write-Host "  3. Execute deploy-frontend.ps1 para o frontend"
Write-Host ""
Write-Host "============================================================"

# Salvar variáveis
@"
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
"@ | Out-File -FilePath ".env.gcp" -Encoding utf8

Write-Success "Variáveis salvas em .env.gcp"
