// Mock Data para o TMC Redação
// NOTE: Most mock data has been migrated to use real API calls.
// Remaining data is used for AI generation settings and configuration pages.

export const toneOptions = [
  { id: "formal", name: "Formal", description: "Tom sério e profissional, adequado para notícias hard news" },
  { id: "informal", name: "Informal", description: "Tom mais leve e descontraído, ideal para matérias de entretenimento" },
  { id: "tecnico", name: "Técnico", description: "Linguagem especializada para conteúdo específico" },
  { id: "persuasivo", name: "Persuasivo", description: "Tom argumentativo para artigos de opinião" },
  { id: "neutro", name: "Neutro", description: "Tom imparcial para reportagens investigativas" }
];

// Backward-compatible aliases
export const mockTones = toneOptions;

export const personaOptions = [
  { id: "jornalista", name: "Jornalista Imparcial", description: "Abordagem objetiva e factual" },
  { id: "especialista", name: "Especialista", description: "Análise aprofundada com conhecimento técnico" },
  { id: "colunista", name: "Colunista", description: "Opinião fundamentada com estilo pessoal" },
  { id: "influencer", name: "Influencer", description: "Linguagem próxima e engajadora" }
];

// Backward-compatible alias
export const mockPersonas = personaOptions;

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

// Re-export for backward compatibility (moved to utils/formatters.js)
export { formatRelativeTime, formatNumber } from '../utils/formatters';
