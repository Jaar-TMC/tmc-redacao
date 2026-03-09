# TMC - Setup Google Cloud Platform

Scripts para configurar toda a infraestrutura do TMC no Google Cloud.

## Pré-requisitos

### 1. Instalar Google Cloud CLI

**Windows (PowerShell como Admin):**
```powershell
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe
```

**Mac:**
```bash
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
```

### 2. Autenticar no Google Cloud

```bash
gcloud auth login
```

### 3. Instalar Firebase CLI (para frontend)

```bash
npm install -g firebase-tools
firebase login
```

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `setup-gcp.sh` | Cria toda a infraestrutura (Cloud SQL, Secrets, VPC, etc.) |
| `deploy.sh` | Faz deploy do backend no Cloud Run |
| `deploy-frontend.sh` | Faz deploy do frontend no Firebase Hosting |

## Uso

### Passo 1: Configurar Infraestrutura

```bash
cd gcp-setup
chmod +x setup-gcp.sh
./setup-gcp.sh
```

Este script irá:
- Criar o projeto GCP
- Habilitar APIs necessárias
- Criar instância Cloud SQL (PostgreSQL)
- Criar banco de dados e usuário
- Configurar Secret Manager
- Criar Service Accounts
- Configurar VPC Connector

### Passo 2: Configurar Chave Anthropic

Após o setup, atualize o secret com sua chave real:

```bash
echo -n "sk-ant-xxxxx" | gcloud secrets versions add tmc-anthropic-api-key --data-file=-
```

### Passo 3: Deploy do Backend

```bash
chmod +x deploy.sh
./deploy.sh
```

Este script irá:
- Fazer build da imagem Docker
- Deploy no Cloud Run
- Configurar Cloud Scheduler (coleta a cada 15min)

### Passo 4: Deploy do Frontend

```bash
chmod +x deploy-frontend.sh
./deploy-frontend.sh
```

## Configurações Editáveis

No arquivo `setup-gcp.sh`, você pode ajustar:

```bash
PROJECT_ID="tmc-redacao"           # Nome do projeto
REGION="southamerica-east1"        # Região (São Paulo)
DB_TIER="db-f1-micro"              # Tamanho do banco (db-f1-micro ou db-g1-small)
```

## Custos Estimados

| Serviço | Custo/mês |
|---------|-----------|
| Cloud Run | $10-20 |
| Cloud SQL (db-f1-micro) | $10-15 |
| Cloud Scheduler | $0.30 |
| Firebase Hosting | $0 (grátis) |
| **Total** | **$20-35** |

## Comandos Úteis

```bash
# Ver logs do Cloud Run
gcloud run services logs read tmc-api --region=southamerica-east1

# Conectar ao banco de dados
gcloud sql connect tmc-database --user=tmc_app --database=tmc

# Ver status dos jobs agendados
gcloud scheduler jobs list --location=southamerica-east1

# Executar coleta manualmente
gcloud scheduler jobs run tmc-rss-collector --location=southamerica-east1

# Ver secrets
gcloud secrets list

# Atualizar secret
echo -n "novo-valor" | gcloud secrets versions add tmc-db-password --data-file=-
```

## Estrutura Criada

```
Google Cloud Project: tmc-redacao
├── Cloud Run: tmc-api
│   └── Imagem: southamerica-east1-docker.pkg.dev/tmc-redacao/tmc-images/tmc-api
├── Cloud SQL: tmc-database
│   └── Database: tmc
│   └── User: tmc_app
├── Cloud Scheduler: tmc-rss-collector (*/15 * * * *)
├── Secret Manager
│   ├── tmc-db-password
│   └── tmc-anthropic-api-key
├── VPC Connector: tmc-vpc-connector
├── Artifact Registry: tmc-images
└── Firebase Hosting: tmc-redacao.web.app
```

## Troubleshooting

### Erro: "Billing not enabled"
Acesse https://console.cloud.google.com/billing e vincule uma conta de faturamento.

### Erro: "Permission denied"
```bash
gcloud auth login
gcloud config set project tmc-redacao
```

### Erro: "Cloud SQL connection failed"
Verifique se o VPC Connector está configurado corretamente:
```bash
gcloud compute networks vpc-access connectors describe tmc-vpc-connector --region=southamerica-east1
```

### Ver logs de erro
```bash
gcloud run services logs read tmc-api --region=southamerica-east1 --limit=50
```
