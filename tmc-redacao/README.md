# TMC Redação

Plataforma de criação de conteúdo para jornalistas e criadores brasileiros.

## Sobre o Projeto

TMC Redação é uma aplicação web moderna desenvolvida para facilitar a criação, edição e gerenciamento de conteúdo jornalístico. A plataforma oferece recursos de assistência por IA, integração com fontes de notícias e ferramentas de análise de tendências.

## Tecnologias

- **React 19** - Biblioteca para construção de interfaces
- **Vite 7** - Build tool moderna e rápida
- **Tailwind CSS 4** - Framework CSS utility-first
- **React Router DOM 7** - Roteamento client-side
- **Lucide React** - Biblioteca de ícones
- **ESLint 9** - Linting e qualidade de código

## Funcionalidades

- Navegação e seleção de artigos de múltiplas fontes
- Criação de posts do zero com assistente de IA
- Criação de posts baseados em inspirações (wizard multi-etapas)
- Gerenciamento de matérias do usuário
- Configurações de fontes de notícias e Google Trends
- Interface responsiva e acessível (WCAG 2.1)
- Sistema de design com paleta de cores TMC

## Estrutura do Projeto

```
tmc-redacao/
├── src/
│   ├── assets/          # Recursos estáticos (logos, SVGs)
│   ├── components/      # Componentes reutilizáveis
│   │   ├── cards/       # Componentes de cartões
│   │   ├── layout/      # Componentes de layout
│   │   └── ui/          # Componentes UI atômicos
│   ├── context/         # Context API para estado global
│   ├── hooks/           # Custom hooks React
│   ├── pages/           # Páginas da aplicação
│   └── data/            # Dados mock
├── public/              # Arquivos públicos estáticos
└── dist/                # Build de produção
```

## Começando

### Pré-requisitos

- Node.js 18+
- npm ou yarn

### Instalação

```bash
# Clone o repositório
git clone https://github.com/TMC/tmc-redacao.git

# Entre na pasta do projeto
cd tmc-redacao

# Instale as dependências
npm install
```

### Desenvolvimento

```bash
# Inicie o servidor de desenvolvimento
npm run dev
```

Acesse http://localhost:5173 para visualizar a aplicação.

### Build para Produção

```bash
# Gere o build otimizado
npm run build

# Visualize o build localmente
npm run preview
```

### Linting

```bash
# Execute o linter
npm run lint
```

## Implantação

O projeto está configurado para deploy no Azure Static Web Apps com CI/CD automático via GitHub Actions.

### Requisitos para Deploy

- Conta no Azure
- Repositório no GitHub
- Arquivo `staticwebapp.config.json` configurado (incluído)

### Passos para Deploy

1. Crie um Azure Static Web App no portal do Azure
2. Conecte ao repositório GitHub
3. Configure o workflow (Azure cria automaticamente)
4. Push para branch main = deploy automático

## Configuração do Azure

O arquivo [staticwebapp.config.json](staticwebapp.config.json) já está configurado com:
- Fallback de navegação para SPAs
- Rotas para React Router
- Headers de segurança
- Tipos MIME configurados

## Paleta de Cores TMC

- **Primary Orange:** #E87722 - CTAs e destaques
- **Secondary Dark Green:** #1A4D2E - Navegação
- **Off-white:** #F5F5F0 - Fundo
- **Dark Gray:** #333333 - Textos
- **Alert Red:** #C41E3A - Indicadores ao vivo

## Scripts Disponíveis

- `npm run dev` - Inicia servidor de desenvolvimento
- `npm run build` - Gera build de produção
- `npm run preview` - Visualiza build localmente
- `npm run lint` - Executa linter ESLint

## Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## Licença

Este projeto é propriedade da TMC.

## Contato

Para mais informações, entre em contato com a equipe TMC.

---

Desenvolvido com tecnologias modernas para jornalistas brasileiros.
