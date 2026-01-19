// Mock Data para o TMC Redação
// NOTE: Most mock data has been migrated to use real API calls.
// Remaining mock data is used for AI generation settings and future features.

export const mockTones = [
  { id: "formal", name: "Formal", description: "Tom sério e profissional, adequado para notícias hard news" },
  { id: "informal", name: "Informal", description: "Tom mais leve e descontraído, ideal para matérias de entretenimento" },
  { id: "tecnico", name: "Técnico", description: "Linguagem especializada para conteúdo específico" },
  { id: "persuasivo", name: "Persuasivo", description: "Tom argumentativo para artigos de opinião" },
  { id: "neutro", name: "Neutro", description: "Tom imparcial para reportagens investigativas" }
];

export const mockPersonas = [
  { id: "jornalista", name: "Jornalista Imparcial", description: "Abordagem objetiva e factual" },
  { id: "especialista", name: "Especialista", description: "Análise aprofundada com conhecimento técnico" },
  { id: "colunista", name: "Colunista", description: "Opinião fundamentada com estilo pessoal" },
  { id: "influencer", name: "Influencer", description: "Linguagem próxima e engajadora" }
];

export const mockExcludedTerms = [
  "BBB",
  "Reality Show",
  "Celebridades",
  "Fofoca",
  "Famosos"
];

export const mockMonitoredTopics = [
  { id: 1, topic: "Tecnologia", addedAt: new Date("2024-11-20"), trendsFound: 45 },
  { id: 2, topic: "Inteligência Artificial", addedAt: new Date("2024-11-18"), trendsFound: 32 },
  { id: 3, topic: "Eleições", addedAt: new Date("2024-11-15"), trendsFound: 78 },
  { id: 4, topic: "Economia Brasil", addedAt: new Date("2024-11-10"), trendsFound: 56 }
];

// Helper function to format relative time
export const formatRelativeTime = (date) => {
  if (!date) return "nunca";

  const now = new Date();
  const dateObj = date instanceof Date ? date : new Date(date);

  if (isNaN(dateObj.getTime())) return "nunca";

  const diffInSeconds = Math.floor((now - dateObj) / 1000);

  if (diffInSeconds < 60) return "agora mesmo";
  if (diffInSeconds < 3600) return `há ${Math.floor(diffInSeconds / 60)} min`;
  if (diffInSeconds < 86400) return `há ${Math.floor(diffInSeconds / 3600)}h`;
  if (diffInSeconds < 604800) return `há ${Math.floor(diffInSeconds / 86400)} dias`;
  return dateObj.toLocaleDateString("pt-BR");
};

// Helper function to format numbers in Brazilian format
export const formatNumber = (num) => {
  return new Intl.NumberFormat('pt-BR').format(num);
};

// Mock Data para Minhas Matérias (future feature)
export const myArticles = [
  {
    id: 101,
    title: "Análise: Como a Inteligência Artificial está transformando o jornalismo brasileiro",
    preview: "Uma investigação profunda sobre o impacto da IA nas redações do país, desde a curadoria de notícias até a criação assistida de conteúdo. Conversamos com especialistas e profissionais da área para entender os desafios e oportunidades dessa revolução tecnológica.",
    status: "published",
    category: "Tecnologia",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000),
    publishedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000),
    views: 12450,
    tags: ["IA", "jornalismo", "tecnologia", "inovação"]
  },
  {
    id: 102,
    title: "Reforma Tributária: Entenda as mudanças que afetam sua empresa",
    preview: "Um guia completo sobre as alterações propostas pela reforma tributária e como elas impactam diferentes setores da economia brasileira.",
    status: "draft",
    category: "Economia",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    publishedAt: null,
    views: 0,
    tags: ["economia", "impostos", "reforma", "empresas"]
  },
  {
    id: 103,
    title: "Flamengo vence Palmeiras e assume liderança do Brasileiro",
    preview: "Com gols de Gabigol e Pedro, o Rubro-Negro venceu o rival paulista por 3 a 1 no Maracanã e chegou aos 65 pontos na competição.",
    status: "published",
    category: "Esportes",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    publishedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    views: 8920,
    tags: ["futebol", "brasileirão", "flamengo", "palmeiras"]
  },
  {
    id: 104,
    title: "Clima extremo: Brasil registra recordes de temperatura em novembro",
    preview: "Análise científica sobre o aumento das temperaturas e seus impactos na agricultura, saúde pública e infraestrutura das cidades brasileiras.",
    status: "draft",
    category: "Ciência",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    publishedAt: null,
    views: 0,
    tags: ["clima", "aquecimento global", "ciência", "meio ambiente"]
  },
  {
    id: 105,
    title: "Eleições 2024: Candidatos apresentam propostas para educação",
    preview: "Um panorama completo das propostas dos principais candidatos à presidência para o setor educacional, incluindo investimentos, currículos e valorização de professores.",
    status: "published",
    category: "Política",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 18 * 24 * 60 * 60 * 1000),
    publishedAt: new Date(Date.now() - 18 * 24 * 60 * 60 * 1000),
    views: 15780,
    tags: ["política", "eleições", "educação", "propostas"]
  },
  {
    id: 106,
    title: "Novos tratamentos para depressão mostram resultados promissores",
    preview: "Pesquisadores brasileiros desenvolvem terapias inovadoras que combinam medicação, tecnologia e acompanhamento personalizado para tratamento de transtornos mentais.",
    status: "draft",
    category: "Saúde",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 6 * 60 * 60 * 1000),
    publishedAt: null,
    views: 0,
    tags: ["saúde", "saúde mental", "tratamento", "pesquisa"]
  },
  {
    id: 107,
    title: "Cinema brasileiro conquista prêmios internacionais",
    preview: "Produções nacionais se destacam em festivais ao redor do mundo, mostrando a força da cinematografia brasileira e abrindo portas para novos talentos.",
    status: "published",
    category: "Entretenimento",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 11 * 24 * 60 * 60 * 1000),
    publishedAt: new Date(Date.now() - 11 * 24 * 60 * 60 * 1000),
    views: 6340,
    tags: ["cinema", "cultura", "prêmios", "entretenimento"]
  },
  {
    id: 108,
    title: "Startups brasileiras recebem investimentos recordes em 2024",
    preview: "O ecossistema de inovação nacional atrai bilhões em investimentos e coloca o Brasil entre os principais hubs de tecnologia da América Latina.",
    status: "published",
    category: "Tecnologia",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000),
    publishedAt: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000),
    views: 9560,
    tags: ["startups", "investimentos", "tecnologia", "inovação"]
  },
  {
    id: 109,
    title: "Mercado imobiliário apresenta sinais de recuperação",
    preview: "Após período de retração, setor imobiliário mostra crescimento nas vendas e lançamentos, impulsionado por novas linhas de crédito e redução de juros.",
    status: "draft",
    category: "Economia",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
    publishedAt: null,
    views: 0,
    tags: ["imóveis", "mercado", "economia", "crédito"]
  },
  {
    id: 110,
    title: "Educação digital: Como as escolas estão se adaptando à nova realidade",
    preview: "Reportagem especial sobre a transformação digital nas instituições de ensino e os desafios de inclusão tecnológica no Brasil.",
    status: "draft",
    category: "Educação",
    author: {
      id: "user1",
      name: "João Silva",
      avatar: "https://i.pravatar.cc/150?u=joao"
    },
    createdAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000),
    updatedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
    publishedAt: null,
    views: 0,
    tags: ["educação", "tecnologia", "digital", "escolas"]
  }
];
