/**
 * Mapa de acentuação para exibição de tags/temas no frontend.
 * Converte palavras sem acento para suas versões corretas em português.
 * Usado APENAS para display - os valores de filtro (tag slug) não são alterados.
 */

const ACCENT_MAP = {
  // -ção / -ções
  'eleicao': 'eleição', 'eleicoes': 'eleições',
  'educacao': 'educação', 'operacao': 'operação', 'operacoes': 'operações',
  'corrupcao': 'corrupção', 'inflacao': 'inflação', 'situacao': 'situação',
  'informacao': 'informação', 'comunicacao': 'comunicação', 'populacao': 'população',
  'legislacao': 'legislação', 'organizacao': 'organização', 'administracao': 'administração',
  'investigacao': 'investigação', 'negociacao': 'negociação', 'producao': 'produção',
  'construcao': 'construção', 'reducao': 'redução', 'atuacao': 'atuação',
  'avaliacao': 'avaliação', 'regulacao': 'regulação', 'tributacao': 'tributação',
  'classificacao': 'classificação', 'selecao': 'seleção', 'nacao': 'nação',
  'convocacao': 'convocação', 'federacao': 'federação', 'inovacao': 'inovação',
  'migracao': 'migração', 'imigracao': 'imigração', 'violacao': 'violação',
  'exportacao': 'exportação', 'importacao': 'importação', 'arrecadacao': 'arrecadação',
  'mineracao': 'mineração', 'extradicao': 'extradição', 'detencao': 'detenção',
  'prevencao': 'prevenção', 'protecao': 'proteção', 'intervencao': 'intervenção',
  'votacao': 'votação', 'aprovacao': 'aprovação', 'reeleicao': 'reeleição',
  'demarcacao': 'demarcação', 'privatizacao': 'privatização', 'vacinacao': 'vacinação',
  'licitacao': 'licitação', 'fiscalizacao': 'fiscalização', 'embarcacao': 'embarcação',
  'aplicacao': 'aplicação', 'habitacao': 'habitação', 'inundacao': 'inundação',
  'declaracao': 'declaração', 'manifestacao': 'manifestação', 'compensacao': 'compensação',
  'deportacao': 'deportação', 'extorsao': 'extorsão', 'preocupacao': 'preocupação',
  'recuperacao': 'recuperação', 'cooperacao': 'cooperação', 'colaboracao': 'colaboração',
  'preservacao': 'preservação', 'conservacao': 'conservação', 'desmatacao': 'desmatação',
  'desertificacao': 'desertificação', 'poluicao': 'poluição', 'destinacao': 'destinação',
  'participacao': 'participação', 'negacao': 'negação', 'acusacao': 'acusação',
  'condenacao': 'condenação', 'absolvicao': 'absolvição', 'apelacao': 'apelação',
  'notificacao': 'notificação', 'mobilizacao': 'mobilização', 'ocupacao': 'ocupação',

  // -são / -sões
  'demissao': 'demissão', 'concessao': 'concessão', 'pressao': 'pressão',
  'comissao': 'comissão', 'emissao': 'emissão', 'decisao': 'decisão',
  'prisao': 'prisão', 'invasao': 'invasão', 'expressao': 'expressão',
  'discussao': 'discussão', 'agressao': 'agressão', 'sessao': 'sessão',
  'televisao': 'televisão', 'extensao': 'extensão', 'expansao': 'expansão',
  'suspensao': 'suspensão', 'exclusao': 'exclusão', 'inclusao': 'inclusão',
  'explosao': 'explosão', 'revisao': 'revisão', 'previsao': 'previsão',
  'divisao': 'divisão', 'repercussao': 'repercussão', 'extorsao': 'extorsão',
  'dimensao': 'dimensão', 'adesao': 'adesão', 'permissao': 'permissão',
  'submissao': 'submissão', 'profissao': 'profissão', 'progressao': 'progressão',
  'recessao': 'recessão', 'sucessao': 'sucessão', 'possessao': 'possessão',
  'transmissao': 'transmissão', 'omissao': 'omissão', 'remissao': 'remissão',

  // -ência / -ância
  'violencia': 'violência', 'influencia': 'influência', 'experiencia': 'experiência',
  'presidencia': 'presidência', 'emergencia': 'emergência', 'frequencia': 'frequência',
  'audiencia': 'audiência', 'ocorrencia': 'ocorrência', 'referencia': 'referência',
  'concorrencia': 'concorrência', 'tendencia': 'tendência', 'inteligencia': 'inteligência',
  'eficiencia': 'eficiência', 'gerencia': 'gerência', 'competencia': 'competência',
  'potencia': 'potência', 'consciencia': 'consciência', 'agencia': 'agência',
  'dependencia': 'dependência', 'residencia': 'residência', 'previdencia': 'previdência',
  'permanencia': 'permanência', 'exigencia': 'exigência', 'urgencia': 'urgência',
  'carencia': 'carência', 'inadimplencia': 'inadimplência', 'decadencia': 'decadência',
  'procedencia': 'procedência', 'providencia': 'providência', 'equivalencia': 'equivalência',
  'reincidencia': 'reincidência', 'incidencia': 'incidência', 'prevalencia': 'prevalência',
  'cadencia': 'cadência', 'evidencia': 'evidência', 'existencia': 'existência',
  'resistencia': 'resistência', 'insistencia': 'insistência', 'persistencia': 'persistência',
  'abstinencia': 'abstinência', 'obediencia': 'obediência', 'desobediencia': 'desobediência',
  'seguranca': 'segurança', 'financas': 'finanças', 'crianca': 'criança',
  'criancas': 'crianças', 'mudanca': 'mudança', 'mudancas': 'mudanças',
  'lideranca': 'liderança', 'esperanca': 'esperança', 'cobranca': 'cobrança',
  'heranca': 'herança', 'tolerancia': 'tolerância', 'vigilancia': 'vigilância',
  'importancia': 'importância', 'distancia': 'distância', 'substancia': 'substância',
  'elegancia': 'elegância', 'estancia': 'estância', 'ambulancia': 'ambulância',

  // -ário / -ária / -ários
  'empresario': 'empresário', 'empresarios': 'empresários', 'empresaria': 'empresária',
  'funcionario': 'funcionário', 'funcionarios': 'funcionários', 'funcionaria': 'funcionária',
  'secretario': 'secretário', 'secretaria': 'secretária',
  'necessario': 'necessário', 'necessaria': 'necessária',
  'contrario': 'contrário', 'voluntario': 'voluntário',
  'salario': 'salário', 'salarios': 'salários',
  'primario': 'primário', 'secundario': 'secundário',
  'extraordinario': 'extraordinário', 'ordinario': 'ordinário',
  'tributario': 'tributário', 'tributaria': 'tributária',
  'tarifario': 'tarifário', 'tarifaria': 'tarifária',
  'alfandegario': 'alfandegário', 'alfandegaria': 'alfandegária',
  'monetario': 'monetário', 'monetaria': 'monetária',
  'orcamentario': 'orçamentário', 'orcamentaria': 'orçamentária',
  'bancario': 'bancário', 'bancaria': 'bancária',
  'imobiliario': 'imobiliário', 'imobiliaria': 'imobiliária',
  'previdenciario': 'previdenciário', 'previdenciaria': 'previdenciária',
  'inflacionario': 'inflacionário', 'inflacionaria': 'inflacionária',
  'beneficiario': 'beneficiário', 'mandatario': 'mandatário',
  'comentario': 'comentário', 'comentarios': 'comentários',
  'cenario': 'cenário', 'cenarios': 'cenários',
  'militario': 'militário', 'humanitario': 'humanitário', 'humanitaria': 'humanitária',
  'universitario': 'universitário', 'universitaria': 'universitária',
  'parlamentario': 'parlamentário', 'parlamentarios': 'parlamentários',
  'comunitario': 'comunitário', 'comunitaria': 'comunitária',
  'penitenciario': 'penitenciário', 'penitenciaria': 'penitenciária',
  'intermediario': 'intermediário', 'intermediaria': 'intermediária',
  'proprietario': 'proprietário', 'proprietaria': 'proprietária',

  // -ício / -ícia / -ércio
  'policia': 'polícia', 'justica': 'justiça',
  'noticia': 'notícia', 'noticias': 'notícias',
  'exercicio': 'exercício', 'servico': 'serviço', 'servicos': 'serviços',
  'inicio': 'início', 'beneficio': 'benefício', 'sacrificio': 'sacrifício',
  'comercio': 'comércio', 'negocio': 'negócio', 'negocios': 'negócios',
  'edificio': 'edifício', 'artificio': 'artifício', 'desperdicio': 'desperdício',

  // Proparoxítonas (-ico/-ica, -tico/-tica)
  'politica': 'política', 'politico': 'político', 'politicos': 'políticos',
  'publica': 'pública', 'publico': 'público', 'publicos': 'públicos',
  'republica': 'república', 'musica': 'música',
  'medico': 'médico', 'medica': 'médica', 'medicos': 'médicos',
  'economico': 'econômico', 'economica': 'econômica',
  'tecnologico': 'tecnológico', 'tecnologica': 'tecnológica',
  'eletronico': 'eletrônico', 'eletronica': 'eletrônica',
  'robotica': 'robótica', 'informatica': 'informática',
  'logistica': 'logística', 'estatistica': 'estatística',
  'classico': 'clássico', 'classica': 'clássica',
  'historico': 'histórico', 'historica': 'histórica',
  'estrategico': 'estratégico', 'estrategica': 'estratégica',
  'diagnostico': 'diagnóstico', 'prognostico': 'prognóstico',
  'domestico': 'doméstico', 'domestica': 'doméstica',
  'climatico': 'climático', 'climatica': 'climática',
  'energetico': 'energético', 'energetica': 'energética',
  'genetico': 'genético', 'genetica': 'genética',
  'pandemico': 'pandêmico', 'pandemica': 'pandêmica',
  'academico': 'acadêmico', 'academica': 'acadêmica',
  'democratico': 'democrático', 'democratica': 'democrática',
  'diplomatico': 'diplomático', 'diplomatica': 'diplomática',
  'burocratico': 'burocrático', 'burocratica': 'burocrática',
  'sistematico': 'sistemático', 'sistematica': 'sistemática',
  'especifico': 'específico', 'especifica': 'específica',
  'cientifico': 'científico', 'cientifica': 'científica',
  'fantastico': 'fantástico', 'fantastica': 'fantástica',
  'dramatico': 'dramático', 'dramatica': 'dramática',
  'pragmatico': 'pragmático', 'pragmatica': 'pragmática',
  'tragedia': 'tragédia', 'tragedias': 'tragédias',
  'catastrofico': 'catastrófico', 'catastrofica': 'catastrófica',
  'simbolico': 'simbólico', 'simbolica': 'simbólica',
  'pedagogico': 'pedagógico', 'pedagogica': 'pedagógica',

  // Outras proparoxítonas
  'petroleo': 'petróleo', 'exercito': 'exército',
  'transito': 'trânsito', 'nucleo': 'núcleo',
  'incendio': 'incêndio', 'incendios': 'incêndios',
  'fenomeno': 'fenômeno', 'fenomenos': 'fenômenos',
  'estadio': 'estádio', 'estadios': 'estádios',
  'arbitro': 'árbitro', 'titulo': 'título', 'titulos': 'títulos',
  'veiculo': 'veículo', 'veiculos': 'veículos',
  'obito': 'óbito', 'obitos': 'óbitos',
  'numero': 'número', 'numeros': 'números',
  'credito': 'crédito', 'debito': 'débito',
  'indice': 'índice', 'indices': 'índices',
  'analise': 'análise', 'analises': 'análises',
  'sindrome': 'síndrome', 'orgao': 'órgão', 'orgaos': 'órgãos',
  'ultimo': 'último', 'ultima': 'última',
  'valido': 'válido', 'valida': 'válida',
  'ilicito': 'ilícito', 'ilicita': 'ilícita',
  'licito': 'lícito', 'licita': 'lícita',
  'alcool': 'álcool', 'idolo': 'ídolo',
  'capitulo': 'capítulo', 'capitulos': 'capítulos',
  'calculo': 'cálculo', 'calculos': 'cálculos',
  'protocolo': 'protocolo', // no accent, just for completeness removal

  // -ão (not -ção/-são)
  'cidadao': 'cidadão', 'capitao': 'capitão',
  'orcamento': 'orçamento', 'orcamentos': 'orçamentos',
  'leilao': 'leilão', 'leiloes': 'leilões',
  'aviao': 'avião', 'avioes': 'aviões',
  'caminhao': 'caminhão', 'caminhoes': 'caminhões',

  // -ês / -esa / -eses
  'paises': 'países', 'portugues': 'português',
  'ingles': 'inglês', 'frances': 'francês',
  'japones': 'japonês', 'chines': 'chinês',
  'holandes': 'holandês', 'mes': 'mês',
  'tres': 'três', 'atraves': 'através',

  // -ível / -ável
  'impossivel': 'impossível', 'possivel': 'possível',
  'responsavel': 'responsável', 'vulneravel': 'vulnerável',
  'sustentavel': 'sustentável', 'renovavel': 'renovável',
  'favoravel': 'favorável', 'notavel': 'notável',
  'estavel': 'estável', 'instavel': 'instável',
  'inevitavel': 'inevitável', 'amigavel': 'amigável',
  'consideravel': 'considerável', 'admiravel': 'admirável',
  'deploravel': 'deplorável', 'miseravel': 'miserável',
  'razoavel': 'razoável', 'incontrolavel': 'incontrolável',

  // Palavras curtas / comuns (apenas as não-ambíguas)
  'apos': 'após', 'tambem': 'também', 'ate': 'até',
  'ja': 'já', 'so': 'só', 'pos': 'pós', 'pre': 'pré',
  'agua': 'água', 'area': 'área', 'areas': 'áreas',
  'aerea': 'aérea', 'aereo': 'aéreo',
  'saude': 'saúde', 'ciencia': 'ciência',

  // Geografia / Lugares
  'amazonia': 'amazônia', 'brasilia': 'brasília',
  'sao': 'são', 'maranhao': 'maranhão',
  'ceara': 'ceará', 'goias': 'goiás',
  'amapa': 'amapá', 'rondonia': 'rondônia',
  'parana': 'paraná', 'piaui': 'piauí',
  'america': 'américa', 'africa': 'áfrica',
  'asia': 'ásia', 'franca': 'frança',
  'libano': 'líbano', 'mexico': 'méxico',
  'peru': 'peru', // no accent
  'panama': 'panamá', 'canada': 'canadá',
};

/**
 * Adiciona acentos a um texto de exibição (theme name).
 * Preserva a capitalização original (Title Case, UPPER, lower).
 * Idempotente: se o texto já tem acentos, não altera.
 *
 * @param {string} text - Texto sem acentos (ex: "Empresario Brasileiro")
 * @returns {string} Texto com acentos (ex: "Empresário Brasileiro")
 */
export function addAccents(text) {
  if (!text) return text;

  return text.split(' ').map(word => {
    const lower = word.toLowerCase();
    const accented = ACCENT_MAP[lower];
    if (!accented) return word;

    // Preserve original casing
    if (word === word.toUpperCase()) {
      // ALL CAPS
      return accented.toUpperCase();
    }
    if (word[0] === word[0].toUpperCase()) {
      // Title Case
      return accented.charAt(0).toUpperCase() + accented.slice(1);
    }
    // lowercase
    return accented;
  }).join(' ');
}

/**
 * Converte um slug de tag para nome de exibição com acentos.
 * Ex: "sao-paulo" → "São Paulo"
 *
 * @param {string} slug - Slug da tag (ex: "sao-paulo")
 * @returns {string} Nome formatado com acentos (ex: "São Paulo")
 */
export function formatTagDisplay(slug) {
  if (!slug) return slug;

  const titleCase = slug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return addAccents(titleCase);
}

/**
 * Remove acentos de um texto para busca accent-insensitive.
 * Ex: "política econômica" → "politica economica"
 *
 * @param {string} text
 * @returns {string} Texto sem diacríticos, em lowercase
 */
export function normalizeForSearch(text) {
  if (!text) return '';
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

export default addAccents;
