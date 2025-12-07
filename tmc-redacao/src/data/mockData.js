// Mock Data para o TMC Redação

export const mockArticles = [
  {
    id: 1,
    title: "Governo anuncia novo pacote de medidas econômicas para 2024",
    source: "G1",
    sourceUrl: "https://g1.globo.com",
    favicon: "https://www.google.com/s2/favicons?domain=g1.globo.com&sz=32",
    category: "Política",
    tags: ["economia", "governo", "medidas"],
    publishedAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    preview: "O governo federal apresentou nesta quinta-feira um conjunto de medidas econômicas que visam estimular o crescimento e controlar a inflação nos próximos meses...",
    content: "O governo federal apresentou nesta quinta-feira um conjunto de medidas econômicas que visam estimular o crescimento e controlar a inflação nos próximos meses. Entre as principais propostas estão a redução de impostos para setores estratégicos e novos incentivos para investimentos em infraestrutura.",
    url: "https://g1.globo.com/economia/noticia/1"
  },
  {
    id: 2,
    title: "Brasil vence Argentina em clássico emocionante pelas Eliminatórias",
    source: "ESPN",
    sourceUrl: "https://espn.com.br",
    favicon: "https://www.google.com/s2/favicons?domain=espn.com.br&sz=32",
    category: "Esportes",
    tags: ["futebol", "seleção", "eliminatórias"],
    publishedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
    preview: "A seleção brasileira venceu a Argentina por 2 a 1 em partida válida pelas Eliminatórias da Copa do Mundo. Os gols foram marcados por Vinicius Jr e Rodrygo...",
    content: "A seleção brasileira venceu a Argentina por 2 a 1 em partida válida pelas Eliminatórias da Copa do Mundo. Os gols foram marcados por Vinicius Jr e Rodrygo. A partida foi disputada no Maracanã lotado.",
    url: "https://espn.com.br/futebol/1"
  },
  {
    id: 3,
    title: "Nova IA da OpenAI supera expectativas em testes de raciocínio",
    source: "TechCrunch",
    sourceUrl: "https://techcrunch.com",
    favicon: "https://www.google.com/s2/favicons?domain=techcrunch.com&sz=32",
    category: "Tecnologia",
    tags: ["IA", "OpenAI", "inovação"],
    publishedAt: new Date(Date.now() - 6 * 60 * 60 * 1000),
    preview: "A OpenAI revelou sua mais recente versão de inteligência artificial, que demonstrou capacidades surpreendentes em testes de raciocínio complexo...",
    content: "A OpenAI revelou sua mais recente versão de inteligência artificial, que demonstrou capacidades surpreendentes em testes de raciocínio complexo. O modelo conseguiu resolver problemas matemáticos avançados e apresentou melhorias significativas em compreensão de contexto.",
    url: "https://techcrunch.com/ai/1"
  },
  {
    id: 4,
    title: "Petrobras registra lucro recorde no terceiro trimestre",
    source: "Valor Econômico",
    sourceUrl: "https://valor.globo.com",
    favicon: "https://www.google.com/s2/favicons?domain=valor.globo.com&sz=32",
    category: "Economia",
    tags: ["petrobras", "lucro", "petróleo"],
    publishedAt: new Date(Date.now() - 8 * 60 * 60 * 1000),
    preview: "A Petrobras divulgou resultados do terceiro trimestre com lucro líquido de R$ 32,5 bilhões, superando as expectativas do mercado...",
    content: "A Petrobras divulgou resultados do terceiro trimestre com lucro líquido de R$ 32,5 bilhões, superando as expectativas do mercado. O resultado foi impulsionado pela alta do petróleo e aumento da produção.",
    url: "https://valor.globo.com/empresas/1"
  },
  {
    id: 5,
    title: "Mudanças climáticas aceleram derretimento de geleiras na Antártida",
    source: "BBC Brasil",
    sourceUrl: "https://bbc.com/portuguese",
    favicon: "https://www.google.com/s2/favicons?domain=bbc.com&sz=32",
    category: "Ciência",
    tags: ["clima", "meio ambiente", "aquecimento global"],
    publishedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
    preview: "Novo estudo publicado na revista Nature revela que o derretimento das geleiras antárticas está ocorrendo três vezes mais rápido do que o previsto...",
    content: "Novo estudo publicado na revista Nature revela que o derretimento das geleiras antárticas está ocorrendo três vezes mais rápido do que o previsto. Cientistas alertam para consequências no nível do mar global.",
    url: "https://bbc.com/portuguese/ciencia/1"
  },
  {
    id: 6,
    title: "Novo tratamento revolucionário contra o câncer é aprovado no Brasil",
    source: "Folha de S.Paulo",
    sourceUrl: "https://folha.uol.com.br",
    favicon: "https://www.google.com/s2/favicons?domain=folha.uol.com.br&sz=32",
    category: "Saúde",
    tags: ["saúde", "câncer", "medicina"],
    publishedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    preview: "A Anvisa aprovou um novo tratamento imunoterápico que promete revolucionar o combate a diversos tipos de câncer...",
    content: "A Anvisa aprovou um novo tratamento imunoterápico que promete revolucionar o combate a diversos tipos de câncer. O medicamento utiliza células do próprio paciente para combater tumores.",
    url: "https://folha.uol.com.br/saude/1"
  },
  {
    id: 7,
    title: "Dólar fecha em queda após decisão do Copom sobre juros",
    source: "InfoMoney",
    sourceUrl: "https://infomoney.com.br",
    favicon: "https://www.google.com/s2/favicons?domain=infomoney.com.br&sz=32",
    category: "Economia",
    tags: ["dólar", "juros", "copom"],
    publishedAt: new Date(Date.now() - 3 * 60 * 60 * 1000),
    preview: "O dólar comercial encerrou o pregão em queda de 1,2%, cotado a R$ 4,85, após o Banco Central manter a taxa Selic em 11,25%...",
    content: "O dólar comercial encerrou o pregão em queda de 1,2%, cotado a R$ 4,85, após o Banco Central manter a taxa Selic em 11,25%. Investidores reagiram positivamente à decisão.",
    url: "https://infomoney.com.br/mercados/1"
  },
  {
    id: 8,
    title: "Artistas brasileiros dominam indicações ao Grammy Latino",
    source: "UOL",
    sourceUrl: "https://uol.com.br",
    favicon: "https://www.google.com/s2/favicons?domain=uol.com.br&sz=32",
    category: "Entretenimento",
    tags: ["música", "grammy", "artistas"],
    publishedAt: new Date(Date.now() - 5 * 60 * 60 * 1000),
    preview: "Músicos brasileiros conquistaram um número recorde de indicações ao Grammy Latino deste ano, com destaque para categorias de MPB e pop...",
    content: "Músicos brasileiros conquistaram um número recorde de indicações ao Grammy Latino deste ano, com destaque para categorias de MPB e pop. Anitta e Liniker lideram as indicações.",
    url: "https://uol.com.br/entretenimento/1"
  }
];

export const mockGoogleTrends = [
  { id: 1, topic: "Eleições 2024", growth: "+450%", searches: "500K+" },
  { id: 2, topic: "Black Friday", growth: "+320%", searches: "350K+" },
  { id: 3, topic: "Copa do Brasil", growth: "+280%", searches: "280K+" },
  { id: 4, topic: "Bitcoin", growth: "+180%", searches: "150K+" },
  { id: 5, topic: "iPhone 16", growth: "+150%", searches: "120K+" }
];

export const mockTwitterTrends = [
  { id: 1, hashtag: "#ForaBolsonaro", mentions: "125K" },
  { id: 2, hashtag: "#LulaPresidente", mentions: "98K" },
  { id: 3, hashtag: "#Flamengo", mentions: "85K" },
  { id: 4, hashtag: "#BBB24", mentions: "72K" },
  { id: 5, hashtag: "#ClimateAction", mentions: "45K" }
];

export const mockFeedThemes = [
  { id: 1, theme: "Dólar", count: 24, trend: "up" },
  { id: 2, theme: "Petrobras", count: 18, trend: "up" },
  { id: 3, theme: "Brasil vs Argentina", count: 15, trend: "stable" },
  { id: 4, theme: "Selic", count: 12, trend: "up" },
  { id: 5, theme: "OpenAI", count: 10, trend: "up" },
  { id: 6, theme: "Inflação", count: 8, trend: "down" },
  { id: 7, theme: "Copa do Mundo", count: 7, trend: "stable" },
  { id: 8, theme: "Anvisa", count: 5, trend: "stable" }
];

export const mockSources = [
  { id: 1, name: "G1", url: "g1.globo.com", favicon: "https://www.google.com/s2/favicons?domain=g1.globo.com&sz=32", active: true, frequency: "1h", lastFetch: new Date(Date.now() - 15 * 60 * 1000) },
  { id: 2, name: "Folha de S.Paulo", url: "folha.uol.com.br", favicon: "https://www.google.com/s2/favicons?domain=folha.uol.com.br&sz=32", active: true, frequency: "30min", lastFetch: new Date(Date.now() - 30 * 60 * 1000) },
  { id: 3, name: "ESPN Brasil", url: "espn.com.br", favicon: "https://www.google.com/s2/favicons?domain=espn.com.br&sz=32", active: true, frequency: "1h", lastFetch: new Date(Date.now() - 45 * 60 * 1000) },
  { id: 4, name: "TechCrunch", url: "techcrunch.com", favicon: "https://www.google.com/s2/favicons?domain=techcrunch.com&sz=32", active: false, frequency: "2h", lastFetch: new Date(Date.now() - 2 * 60 * 60 * 1000) },
  { id: 5, name: "Valor Econômico", url: "valor.globo.com", favicon: "https://www.google.com/s2/favicons?domain=valor.globo.com&sz=32", active: true, frequency: "1h", lastFetch: new Date(Date.now() - 20 * 60 * 1000) }
];

export const mockCategories = [
  { id: 1, name: "Política", count: 45 },
  { id: 2, name: "Economia", count: 38 },
  { id: 3, name: "Esportes", count: 32 },
  { id: 4, name: "Tecnologia", count: 28 },
  { id: 5, name: "Entretenimento", count: 24 },
  { id: 6, name: "Saúde", count: 18 },
  { id: 7, name: "Ciência", count: 15 },
  { id: 8, name: "Educação", count: 12 }
];

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
  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);

  if (diffInSeconds < 60) return "agora mesmo";
  if (diffInSeconds < 3600) return `há ${Math.floor(diffInSeconds / 60)} min`;
  if (diffInSeconds < 86400) return `há ${Math.floor(diffInSeconds / 3600)}h`;
  if (diffInSeconds < 604800) return `há ${Math.floor(diffInSeconds / 86400)} dias`;
  return date.toLocaleDateString("pt-BR");
};

// Helper function to format numbers in Brazilian format
export const formatNumber = (num) => {
  return new Intl.NumberFormat('pt-BR').format(num);
};

// Mock Data para Minhas Matérias
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
