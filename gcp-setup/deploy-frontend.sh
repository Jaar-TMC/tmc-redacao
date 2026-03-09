#!/bin/bash
# =============================================================================
# TMC - Deploy Frontend para Firebase Hosting
# =============================================================================
# Este script faz o build e deploy do frontend React no Firebase
#
# Pré-requisitos:
#   1. npm install -g firebase-tools
#   2. firebase login
#
# Uso:
#   chmod +x deploy-frontend.sh
#   ./deploy-frontend.sh
# =============================================================================

set -e

# Carregar variáveis
if [ -f .env.gcp ]; then
    source .env.gcp
fi

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[AVISO]${NC} $1"; }

FRONTEND_DIR="../tmc-redacao"

echo ""
echo "============================================================"
echo "  TMC - Deploy Frontend (Firebase Hosting)"
echo "============================================================"
echo ""

# =============================================================================
# 1. VERIFICAR FIREBASE CLI
# =============================================================================
if ! command -v firebase &> /dev/null; then
    log_warning "Firebase CLI não encontrado. Instalando..."
    npm install -g firebase-tools
fi

log_success "Firebase CLI encontrado"

# =============================================================================
# 2. LOGIN NO FIREBASE
# =============================================================================
log_info "Verificando autenticação Firebase..."
firebase login --interactive

# =============================================================================
# 3. INICIALIZAR FIREBASE (se necessário)
# =============================================================================
cd $FRONTEND_DIR

if [ ! -f "firebase.json" ]; then
    log_info "Inicializando Firebase Hosting..."

    # Criar firebase.json manualmente
    cat > firebase.json << 'EOF'
{
  "hosting": {
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      },
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp|ico)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "public, max-age=31536000, immutable"
          }
        ]
      }
    ]
  }
}
EOF
    log_success "firebase.json criado"
fi

# =============================================================================
# 4. ATUALIZAR URL DA API
# =============================================================================
log_info "Configurando URL da API..."

if [ -n "$CLOUD_RUN_URL" ]; then
    # Criar/atualizar .env.production
    echo "VITE_API_URL=$CLOUD_RUN_URL" > .env.production
    log_success "API URL configurada: $CLOUD_RUN_URL"
else
    log_warning "CLOUD_RUN_URL não definida. Verifique o arquivo .env.gcp"
    echo "Informe a URL da API (Cloud Run):"
    read CLOUD_RUN_URL
    echo "VITE_API_URL=$CLOUD_RUN_URL" > .env.production
fi

# =============================================================================
# 5. BUILD DO FRONTEND
# =============================================================================
log_info "Instalando dependências..."
npm install

log_info "Fazendo build de produção..."
npm run build

log_success "Build concluído"

# =============================================================================
# 6. DEPLOY PARA FIREBASE
# =============================================================================
log_info "Fazendo deploy para Firebase Hosting..."

firebase deploy --only hosting

log_success "Deploy concluído!"

# Obter URL do site
SITE_URL=$(firebase hosting:channel:list 2>/dev/null | grep -oP 'https://[^ ]+' | head -1 || echo "https://$PROJECT_ID.web.app")

echo ""
echo "============================================================"
echo "  FRONTEND DEPLOY CONCLUÍDO!"
echo "============================================================"
echo ""
echo "URL do site: https://$PROJECT_ID.web.app"
echo ""
echo "============================================================"
