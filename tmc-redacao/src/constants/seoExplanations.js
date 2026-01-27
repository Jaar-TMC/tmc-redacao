/**
 * SEO Explanations - Educational content for each SEO metric (Portuguese)
 *
 * Every metric in the SEO panel includes educational explanations to help users understand:
 * 1. O que (What) - the metric measures
 * 2. Por que (Why) - it matters for SEO
 * 3. Como (How) - to improve it
 * 4. Exemplos - of good vs. bad
 */

export const SEO_EXPLANATIONS = {
  // ═══════════════════════════════════════════════════════════════
  // CATEGORY 1: CONTENT QUALITY (30 pts)
  // ═══════════════════════════════════════════════════════════════

  contentQuality: {
    categoryName: 'Qualidade do Conteúdo',
    categoryDescription: 'Avalia a profundidade, estrutura e legibilidade do seu artigo. Conteúdo de alta qualidade é o fator #1 de ranqueamento no Google.',
    whyItMatters: 'O Google prioriza conteúdo que responde completamente às perguntas dos leitores. Artigos superficiais ou mal estruturados têm taxas de rejeição altas, sinalizando ao Google que não são úteis.',
    icon: 'FileText',
    maxPoints: 30,

    metrics: {
      wordCountDepth: {
        name: 'Extensão e Profundidade',
        maxPoints: 10,
        description: 'Mede se o artigo tem o tamanho ideal para o tipo de conteúdo.',
        whyItMatters: 'Estudos mostram que artigos nas primeiras posições do Google têm em média 1.447 palavras. Porém, mais importante que quantidade é a PROFUNDIDADE - cobrir o assunto completamente.',
        howToImprove: [
          'Para notícias: 300-800 palavras (foco na informação essencial)',
          'Para reportagens: 1.000-3.000 palavras (contexto e análise)',
          'Para análises: 1.500-4.000 palavras (profundidade técnica)',
          'Para opinião: 400-1.200 palavras (argumentação concisa)'
        ],
        examples: {
          good: 'Notícia com 500 palavras que responde quem, o quê, quando, onde, por quê e como',
          bad: 'Notícia com 200 palavras que deixa perguntas sem resposta'
        },
        tip: 'Não adicione palavras desnecessárias só para aumentar o tamanho. O Google detecta "enchimento" de conteúdo.',
        scoring: {
          10: 'Dentro do range ideal para o tipo de artigo',
          7: 'Dentro do range aceitável',
          4: 'Ligeiramente fora do range',
          2: 'Muito fora do ideal',
          0: 'Extremamente curto ou extenso demais'
        }
      },

      contentStructure: {
        name: 'Estrutura do Conteúdo',
        maxPoints: 10,
        description: 'Avalia a organização do texto: introdução, subtítulos, parágrafos e elementos visuais.',
        whyItMatters: '79% dos leitores "escaneiam" o conteúdo antes de decidir ler. Artigos bem estruturados retêm leitores por mais tempo (dwell time), um forte sinal de qualidade para o Google.',
        howToImprove: [
          'Comece com um parágrafo de resumo (responda a pergunta principal)',
          'Use subtítulos (H2, H3) a cada 300-400 palavras',
          'Mantenha parágrafos curtos (3-4 frases no máximo)',
          'Inclua listas com marcadores para informações sequenciais',
          'Use citações em destaque para declarações importantes'
        ],
        examples: {
          good: 'Artigo com introdução clara, 3 subtítulos organizando o conteúdo, parágrafos curtos e uma lista de pontos-chave',
          bad: 'Bloco único de texto sem divisões, parágrafos de 10+ linhas'
        },
        tip: 'Estrutura "Pirâmide Invertida": informação mais importante primeiro, detalhes depois.',
        subMetrics: {
          hasIntroduction: { name: 'Introdução resumida', points: 2, description: 'Primeiro parágrafo resume o artigo' },
          hasSubheadings: { name: 'Subtítulos (H2/H3)', points: 2, description: 'Mínimo 2 subtítulos para organização' },
          hasConclusion: { name: 'Conclusão', points: 2, description: 'Parágrafo final com fechamento' },
          shortParagraphs: { name: 'Parágrafos curtos', points: 2, description: 'Máximo 150 palavras por parágrafo' },
          hasList: { name: 'Listas', points: 1, description: 'Listas com marcadores ou numeradas' },
          hasQuotes: { name: 'Citações', points: 1, description: 'Citações em destaque (blockquote)' }
        }
      },

      readability: {
        name: 'Legibilidade e Clareza',
        maxPoints: 10,
        description: 'Mede quão fácil é ler e entender o texto, usando a fórmula Flesch adaptada para Português.',
        whyItMatters: 'Textos difíceis de ler aumentam a taxa de rejeição. O Google favorece conteúdo acessível que a maioria das pessoas consegue entender rapidamente.',
        howToImprove: [
          'Use frases curtas (máximo 20 palavras por frase)',
          'Prefira voz ativa ("O presidente anunciou") à passiva ("Foi anunciado pelo presidente")',
          'Evite jargões técnicos sem explicação',
          'Use palavras de transição (porém, além disso, por outro lado)',
          'Varie o início das frases (não comece várias com "O", "A", etc.)'
        ],
        scoreInterpretation: {
          '80-100': 'Muito Fácil - Qualquer pessoa entende',
          '60-79': 'Fácil - Ideal para jornalismo',
          '40-59': 'Moderado - Aceitável para análises técnicas',
          '20-39': 'Difícil - Apenas especialistas entendem',
          '0-19': 'Muito Difícil - Academicamente denso'
        },
        examples: {
          good: 'A Petrobras registrou lucro recorde de R$ 188 bilhões em 2022. O resultado supera em 76% o ano anterior.',
          bad: 'O conglomerado energético brasileiro de capital misto, cuja participação acionária majoritária pertence à União, reportou resultados financeiros superlativos no exercício fiscal.'
        },
        tip: 'Escreva como se estivesse explicando para alguém que não é especialista no assunto.',
        subMetrics: {
          fleschScore: { name: 'Score Flesch', points: 4, description: 'Fórmula de legibilidade adaptada para PT-BR' },
          sentenceLength: { name: 'Tamanho das frases', points: 2, description: 'Média ideal: até 20 palavras/frase' },
          passiveVoice: { name: 'Voz passiva', points: 2, description: 'Menos de 10% de voz passiva' },
          transitionWords: { name: 'Palavras de transição', points: 2, description: 'Uso de conectivos para fluidez' }
        }
      }
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // CATEGORY 2: ON-PAGE OPTIMIZATION (25 pts)
  // ═══════════════════════════════════════════════════════════════

  onPageOptimization: {
    categoryName: 'Otimização On-Page',
    categoryDescription: 'Elementos técnicos que ajudam o Google a entender e ranquear seu conteúdo: título, meta description, palavras-chave e URL.',
    whyItMatters: 'São os primeiros elementos que o Google analisa para determinar sobre o que é seu artigo e se ele é relevante para uma busca específica.',
    icon: 'Target',
    maxPoints: 25,

    metrics: {
      titleOptimization: {
        name: 'Otimização do Título',
        maxPoints: 8,
        description: 'Avalia se o título tem o tamanho ideal, contém a palavra-chave e é atrativo para cliques.',
        whyItMatters: 'O título é o fator #1 que determina se alguém clica no seu link nos resultados de busca. Um título otimizado pode aumentar seu CTR (taxa de cliques) em até 20%.',
        howToImprove: [
          'Mantenha entre 50-60 caracteres (Google corta títulos maiores)',
          'Coloque a palavra-chave principal nas primeiras 3 palavras',
          'Use "power words": exclusivo, urgente, revelado, surpreendente',
          'Inclua números quando relevante (5 motivos, 10 dicas)',
          'Crie urgência ou curiosidade sem ser clickbait'
        ],
        examples: {
          good: 'Corinthians anuncia contratação de Depay; veja valores | 56 chars',
          bad: 'Uma notícia muito importante sobre uma possível contratação que pode mudar o futebol brasileiro | 94 chars - CORTADO!'
        },
        subMetrics: {
          length: { name: 'Tamanho', description: '50-60 caracteres é o ideal para exibição completa no Google', points: 2 },
          keywordPosition: { name: 'Posição da Palavra-chave', description: 'Palavra-chave nas primeiras 3 palavras tem mais peso para SEO', points: 2 },
          powerWords: { name: 'Palavras de Impacto', description: 'Palavras que geram emoção e aumentam cliques', points: 1 },
          numbers: { name: 'Números', description: 'Títulos com números têm 36% mais cliques', points: 1 },
          emotional: { name: 'Apelo Emocional', description: 'Títulos que provocam curiosidade ou emoção performam melhor', points: 1 },
          uniqueness: { name: 'Originalidade', description: 'Evite títulos genéricos usados por todos os concorrentes', points: 1 }
        },
        tip: 'Teste seu título: "Eu clicaria neste resultado?" Se não, reescreva.'
      },

      metaDescription: {
        name: 'Meta Description (Linha Fina)',
        maxPoints: 7,
        description: 'O texto que aparece abaixo do título nos resultados de busca. É seu "anúncio" para convencer o leitor a clicar.',
        whyItMatters: 'Embora não seja diretamente um fator de ranking, uma meta description bem escrita aumenta o CTR, que É um fator de ranking. Uma boa meta description pode dobrar seus cliques.',
        howToImprove: [
          'Use 150-160 caracteres (Google corta após isso)',
          'Inclua a palavra-chave naturalmente',
          'Seja diferente do título - complemente, não repita',
          'Inclua um "gancho" ou call-to-action',
          'Resuma o valor que o leitor vai obter'
        ],
        examples: {
          good: 'Memphis Depay assina com o Corinthians por 2 anos. Atacante holandês chega com salário de R$ 3 milhões mensais e promete "títulos". | 152 chars',
          bad: 'Leia mais sobre futebol. | 25 chars - MUITO CURTO!'
        },
        subMetrics: {
          length: { name: 'Tamanho', description: '150-160 caracteres ideal', points: 2 },
          keyword: { name: 'Palavra-chave', description: 'Incluir palavra-chave principal', points: 2 },
          cta: { name: 'Call-to-Action', description: 'Convite ou gancho para clicar', points: 1 },
          unique: { name: 'Diferente do Título', description: 'Complementa, não repete', points: 1 },
          complete: { name: 'Frase Completa', description: 'Termina com pontuação adequada', points: 1 }
        },
        tip: 'Pense na meta description como o trailer de um filme - deve fazer querer ver mais.'
      },

      keywordStrategy: {
        name: 'Estratégia de Palavras-chave',
        maxPoints: 5,
        description: 'Avalia o uso estratégico de palavras-chave no conteúdo, incluindo variações semânticas (LSI).',
        whyItMatters: 'O Google usa palavras-chave para entender o tema do seu artigo. Uma densidade de 1-2.5% é ideal - menos parece irrelevante, mais parece spam.',
        howToImprove: [
          'Use a palavra-chave principal no primeiro parágrafo',
          'Mantenha densidade entre 1-2.5% (1-2 vezes a cada 100 palavras)',
          'Use sinônimos e variações (LSI keywords)',
          'Distribua naturalmente pelo texto',
          'Não force - se parecer artificial, está errado'
        ],
        lsiExplanation: {
          what: 'LSI (Latent Semantic Indexing) são palavras relacionadas que ajudam o Google a entender o contexto.',
          example: 'Se a palavra-chave é "Corinthians", LSI seriam: Timão, Fiel, Parque São Jorge, Neo Química Arena, torcida alvinegra',
          benefit: 'Usar LSI mostra ao Google que seu conteúdo é completo e autoritativo sobre o assunto.'
        },
        examples: {
          good: 'Artigo sobre "eleições 2024" que também menciona: urna eletrônica, TSE, candidatos, votos, campanha, segundo turno',
          bad: 'Artigo que repete "eleições 2024" 30 vezes em 500 palavras (keyword stuffing)'
        },
        subMetrics: {
          primaryDensity: { name: 'Densidade primária', description: 'Palavra-chave principal 1-2.5%', points: 2 },
          lsiKeywords: { name: 'Palavras LSI', description: 'Palavras semanticamente relacionadas', points: 1 },
          keywordVariations: { name: 'Variações/sinônimos', description: 'Uso de sinônimos naturais', points: 1 },
          naturalPlacement: { name: 'Distribuição natural', description: 'Não forçado ou repetitivo', points: 1 }
        },
        tip: 'Escreva naturalmente primeiro, depois verifique se a densidade está adequada.'
      },

      urlSlug: {
        name: 'URL/Slug',
        maxPoints: 5,
        description: 'A parte da URL que identifica a página. Deve ser curta, descritiva e conter a palavra-chave.',
        whyItMatters: 'URLs claras ajudam tanto o Google quanto os usuários a entenderem o conteúdo da página antes de clicar. URLs limpas têm maior CTR.',
        howToImprove: [
          'Mantenha abaixo de 60 caracteres',
          'Inclua a palavra-chave principal',
          'Remova "stop words" (de, do, da, o, a, um, para)',
          'Use hífens para separar palavras',
          'Evite números de ID ou caracteres especiais'
        ],
        examples: {
          good: '/corinthians-anuncia-depay-valores-contrato',
          bad: '/post?id=12345&category=esportes&date=2024-01-15'
        },
        subMetrics: {
          length: { name: 'Tamanho', description: 'Máximo 60 caracteres', points: 1 },
          keywordPresent: { name: 'Palavra-chave', description: 'Contém a keyword principal', points: 2 },
          noStopWords: { name: 'Sem stop words', description: 'Mínimo de preposições e artigos', points: 1 },
          readability: { name: 'Legibilidade', description: 'Fácil de ler e entender', points: 1 }
        },
        tip: 'A URL deve fazer sentido mesmo sem o título - "alguém entenderia o assunto só pela URL?"'
      }
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // CATEGORY 3: E-E-A-T SIGNALS (20 pts)
  // ═══════════════════════════════════════════════════════════════

  eeatSignals: {
    categoryName: 'E-E-A-T',
    categoryFullName: 'Experiência, Expertise, Autoridade, Confiança',
    categoryDescription: 'Framework do Google para avaliar a qualidade e credibilidade do conteúdo e do autor.',
    whyItMatters: 'Após atualizações recentes, o Google prioriza fortemente conteúdo que demonstra E-E-A-T. É especialmente crítico para temas de saúde, finanças e notícias (YMYL - Your Money Your Life).',
    icon: 'Shield',
    maxPoints: 20,

    metrics: {
      experience: {
        name: 'Experiência (Experience)',
        maxPoints: 5,
        description: 'Indica que o autor tem experiência real e prática com o assunto.',
        whyItMatters: 'O Google quer mostrar conteúdo de pessoas que realmente vivenciaram ou investigaram o assunto, não apenas compilaram informações de outras fontes.',
        howToImprove: [
          'Inclua detalhes específicos que só quem vivenciou saberia',
          'Use linguagem de reportagem: "nossa equipe apurou", "em entrevista exclusiva"',
          'Cite testemunhos ou entrevistas realizadas',
          'Descreva o processo de apuração quando relevante',
          'Inclua fotos ou vídeos originais'
        ],
        patterns: [
          '"Segundo apuração da reportagem..."',
          '"Em entrevista exclusiva ao [veículo]..."',
          '"Nossa equipe esteve presente no local..."',
          '"Testemunhas relataram que..."'
        ],
        examples: {
          good: 'Segundo apuração do TMC, fontes do clube confirmaram que a negociação está em estágio avançado. A reportagem teve acesso ao esboço do contrato.',
          bad: 'Rumores na internet indicam que pode haver uma contratação.'
        },
        subMetrics: {
          firstPersonAccount: { name: 'Relato em primeira mão', description: 'Indica reportagem própria ou presencial', points: 2 },
          specificDetails: { name: 'Detalhes específicos', description: 'Informações que demonstram conhecimento direto', points: 2 },
          originalInsights: { name: 'Insights originais', description: 'Análise ou informação não genérica', points: 1 }
        },
        tip: 'Mostre que você fez a reportagem, não apenas copiou de outros veículos.'
      },

      expertise: {
        name: 'Expertise (Especialização)',
        maxPoints: 5,
        description: 'Demonstra conhecimento profundo e especializado no assunto.',
        whyItMatters: 'O Google prefere conteúdo de especialistas. Em jornalismo, isso significa fontes qualificadas e análise fundamentada.',
        howToImprove: [
          'Cite pelo menos 2 fontes credíveis no artigo',
          'Inclua dados estatísticos de institutos reconhecidos',
          'Entreviste especialistas (analistas, profissionais, acadêmicos)',
          'Use terminologia correta do campo',
          'Inclua byline do autor (quando aplicável)'
        ],
        sourceTypes: [
          'Fontes oficiais: governo, polícia, tribunais',
          'Especialistas: analistas, professores, profissionais',
          'Dados: IBGE, institutos de pesquisa, relatórios oficiais',
          'Protagonistas: pessoas diretamente envolvidas no fato'
        ],
        examples: {
          good: 'Segundo o economista João Silva, professor da USP, "a inflação deve ceder nos próximos meses". Dados do IBGE mostram queda de 0,2% em dezembro.',
          bad: 'Especialistas acreditam que a economia vai melhorar. (Quais especialistas? Que dados?)'
        },
        subMetrics: {
          authorByline: { name: 'Autoria identificada', description: 'Artigo assinado por autor', points: 1 },
          sourcesCited: { name: 'Fontes citadas', description: 'Mínimo 2 fontes credíveis', points: 2 },
          technicalAccuracy: { name: 'Precisão técnica', description: 'Uso correto de terminologia', points: 2 }
        },
        tip: 'Nomeie suas fontes sempre que possível. "Fontes anônimas" têm menos peso.'
      },

      authority: {
        name: 'Autoridade (Authoritativeness)',
        maxPoints: 5,
        description: 'Mostra que o veículo/autor é reconhecido como referência no assunto.',
        whyItMatters: 'O Google avalia se seu site é citado e referenciado por outros. Para artigos individuais, fontes oficiais e institucionais aumentam a autoridade.',
        howToImprove: [
          'Cite fontes oficiais (governo, órgãos públicos, federações)',
          'Inclua declarações de porta-vozes oficiais',
          'Referencie dados de instituições reconhecidas',
          'Mencione documentos oficiais quando relevante',
          'Link para fontes primárias'
        ],
        authorityIndicators: [
          'Declarações de ministérios, secretarias, prefeituras',
          'Dados do IBGE, Banco Central, IPEA',
          'Posicionamentos de federações (CBF, Conmebol)',
          'Documentos judiciais, boletins policiais',
          'Notas oficiais de empresas e instituições'
        ],
        examples: {
          good: 'A Polícia Civil confirmou, em nota oficial, que três suspeitos foram presos. Segundo o delegado responsável pelo caso, Dr. Carlos Mendes...',
          bad: 'Dizem que houve prisões, mas ainda não há confirmação.'
        },
        subMetrics: {
          officialSources: { name: 'Fontes oficiais', description: 'Citação de órgãos governamentais/institucionais', points: 2 },
          expertQuotes: { name: 'Citações de especialistas', description: 'Declarações de profissionais qualificados', points: 2 },
          institutionalRefs: { name: 'Referências institucionais', description: 'Menção a instituições reconhecidas', points: 1 }
        },
        tip: 'Sempre que possível, vá direto à fonte oficial ao invés de citar outros veículos.'
      },

      trust: {
        name: 'Confiança (Trustworthiness)',
        maxPoints: 5,
        description: 'O mais importante dos 4 pilares. Avalia se o conteúdo é preciso, honesto e confiável.',
        whyItMatters: 'Confiança é a base do E-E-A-T. Um artigo pode ter experiência e expertise, mas se não for confiável, não será ranqueado. O Google verifica se os fatos são verificáveis.',
        howToImprove: [
          'Inclua múltiplos pontos de vista em assuntos controversos',
          'Nomeie suas fontes (transparência)',
          'Evite títulos sensacionalistas que não correspondem ao conteúdo',
          'Corrija erros rapidamente quando identificados',
          'Separe claramente fatos de opiniões'
        ],
        trustSignals: [
          'Fontes nomeadas (não anônimas)',
          'Múltiplas perspectivas apresentadas',
          'Fatos verificáveis com fontes citadas',
          'Título preciso (não clickbait)',
          'Transparência sobre limitações ou incertezas'
        ],
        examples: {
          good: 'O deputado José Santos (PT) defende o projeto. Já a oposição, representada por Maria Lima (PL), argumenta que "a proposta é inconstitucional".',
          bad: 'ABSURDO! Projeto DESTRUIRÁ a economia brasileira, dizem críticos.'
        },
        subMetrics: {
          factualClaims: { name: 'Afirmações verificáveis', description: 'Fatos que podem ser checados', points: 2 },
          balancedPerspective: { name: 'Múltiplos pontos de vista', description: 'Apresenta diferentes perspectivas', points: 1 },
          transparentSourcing: { name: 'Fontes transparentes', description: 'Fontes identificadas, não anônimas', points: 1 },
          noClickbait: { name: 'Sem clickbait', description: 'Título corresponde ao conteúdo', points: 1 }
        },
        tip: 'Se você não consegue verificar uma informação, diga isso explicitamente no texto.'
      }
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // CATEGORY 4: TECHNICAL EXCELLENCE (15 pts)
  // ═══════════════════════════════════════════════════════════════

  technicalExcellence: {
    categoryName: 'Excelência Técnica',
    categoryDescription: 'Elementos técnicos que melhoram a experiência do usuário e ajudam o Google a indexar seu conteúdo.',
    whyItMatters: 'Links internos mantêm leitores no site, links externos mostram pesquisa, e imagens otimizadas melhoram engajamento e acessibilidade.',
    icon: 'Settings',
    maxPoints: 15,

    metrics: {
      internalLinks: {
        name: 'Links Internos',
        maxPoints: 5,
        description: 'Links para outros artigos do seu próprio site.',
        whyItMatters: 'Links internos: 1) Mantêm leitores no site mais tempo, 2) Distribuem "autoridade SEO" entre páginas, 3) Ajudam o Google a entender a estrutura do site.',
        howToImprove: [
          'Inclua 2-4 links internos por artigo',
          'Use texto âncora descritivo (não "clique aqui")',
          'Linke para artigos relacionados ao tema',
          'Distribua links ao longo do texto (não só no final)',
          'Priorize links para conteúdo evergreen'
        ],
        examples: {
          good: 'Como explicamos na [análise sobre o mercado de transferências], o Corinthians tem investido pesado...',
          bad: 'Para mais informações, [clique aqui].'
        },
        subMetrics: {
          hasInternalLinks: { name: 'Possui links internos', description: 'Mínimo 2 links para outros artigos', points: 2 },
          relevantAnchors: { name: 'Âncoras descritivas', description: 'Texto do link descreve o destino', points: 2 },
          distribution: { name: 'Distribuição', description: 'Links espalhados pelo texto', points: 1 }
        },
        tip: 'Pense: "Que outros artigos nossos ajudariam este leitor?"'
      },

      externalLinks: {
        name: 'Referências Externas',
        maxPoints: 5,
        description: 'Links para fontes externas confiáveis que fundamentam suas afirmações.',
        whyItMatters: 'Links para fontes autoritativas mostram ao Google que você fez pesquisa e aumentam a credibilidade do seu conteúdo.',
        howToImprove: [
          'Linke para a fonte primária de dados e estatísticas',
          'Prefira sites .gov.br, .edu.br, .org.br',
          'Linke para relatórios e documentos oficiais',
          'Use "nofollow" para links de menor confiança',
          'Não linke para concorrentes diretos desnecessariamente'
        ],
        trustedDomains: [
          'Sites governamentais (.gov.br)',
          'Instituições educacionais (.edu.br)',
          'Organizações (.org.br)',
          'Agências de notícias (Reuters, AP, AFP)',
          'Veículos de referência (com moderação)'
        ],
        examples: {
          good: 'Segundo dados do [IBGE](link), a inflação acumulada...',
          bad: 'Artigo sem nenhuma referência externa para dados citados.'
        },
        subMetrics: {
          hasExternalRefs: { name: 'Possui referências externas', description: 'Mínimo 1 link externo relevante', points: 2 },
          qualitySources: { name: 'Fontes de qualidade', description: 'Links para sites autoritativos', points: 2 },
          relevance: { name: 'Relevância', description: 'Links contextuais e úteis', points: 1 }
        },
        tip: 'Sempre que citar um número ou estatística, linke para a fonte original.'
      },

      mediaOptimization: {
        name: 'Otimização de Mídia',
        maxPoints: 5,
        description: 'Uso e otimização de imagens para SEO e acessibilidade.',
        whyItMatters: 'Artigos com imagens têm 94% mais visualizações. Imagens otimizadas aparecem no Google Images e melhoram a acessibilidade.',
        howToImprove: [
          'Inclua pelo menos 1 imagem relevante',
          'Use alt text descritivo (não "imagem1.jpg")',
          'Adicione legendas explicativas',
          'Otimize o tamanho do arquivo (sem perder qualidade)',
          'Use nomes de arquivo descritivos'
        ],
        altTextGuide: {
          what: 'Alt text descreve a imagem para usuários com deficiência visual e para o Google.',
          example: 'Alt ruim: "foto". Alt bom: "Memphis Depay durante apresentação no Corinthians, vestindo a camisa 94"',
          benefit: 'Imagens com bom alt text aparecem nas buscas de imagem do Google.'
        },
        examples: {
          good: 'Imagem com alt="Gráfico mostrando a evolução do PIB brasileiro de 2020 a 2024" e legenda explicativa',
          bad: 'Imagem sem alt text e sem legenda'
        },
        subMetrics: {
          hasImages: { name: 'Possui imagens', description: 'Mínimo 1 imagem relevante', points: 2 },
          hasAltText: { name: 'Alt text', description: 'Todas as imagens têm alt text', points: 1 },
          imageRelevance: { name: 'Relevância', description: 'Alt text é descritivo', points: 1 },
          captions: { name: 'Legendas', description: 'Imagens têm legendas explicativas', points: 1 }
        },
        tip: 'Descreva a imagem como se estivesse explicando para alguém que não pode vê-la.'
      }
    }
  },

  // ═══════════════════════════════════════════════════════════════
  // CATEGORY 5: AI & SERP OPTIMIZATION (10 pts)
  // ═══════════════════════════════════════════════════════════════

  aiSerpOptimization: {
    categoryName: 'IA & SERP',
    categoryFullName: 'Otimização para IA e SERP',
    categoryDescription: 'Preparação do conteúdo para aparecer em Featured Snippets e AI Overviews do Google.',
    whyItMatters: 'O Google está mudando: AI Overviews mostram resumos gerados por IA antes dos resultados tradicionais. Conteúdo otimizado para isso ganha visibilidade extra.',
    icon: 'Sparkles',
    maxPoints: 10,

    metrics: {
      featuredSnippet: {
        name: 'Pronto para Featured Snippet',
        maxPoints: 5,
        description: 'Otimização para aparecer no "posição zero" do Google - a caixa de resposta acima dos resultados.',
        whyItMatters: 'Featured Snippets recebem ~8% de todos os cliques. Aparecer ali estabelece seu site como fonte autoritativa.',
        howToImprove: [
          'Comece com uma resposta direta de 40-60 palavras no primeiro parágrafo',
          'Use o formato de pergunta/resposta quando apropriado',
          'Inclua listas numeradas ou com marcadores',
          'Adicione tabelas para dados comparativos',
          'Estruture com subtítulos claros (H2, H3)'
        ],
        snippetFormats: {
          paragraph: 'Resposta direta em 40-60 palavras para perguntas "O que é", "Por que", "Como"',
          list: 'Listas numeradas para processos passo-a-passo ou rankings',
          table: 'Tabelas para comparações ou dados estruturados'
        },
        examples: {
          good: 'O que é inflação? A inflação é o aumento generalizado e contínuo dos preços de bens e serviços em uma economia. É medida por índices como IPCA e IGP-M, e afeta o poder de compra da população. [42 palavras - ideal!]',
          bad: 'Neste artigo vamos falar sobre um tema muito importante para a economia que afeta a vida de todos os brasileiros e que tem sido muito discutido... [introdução vaga sem resposta direta]'
        },
        subMetrics: {
          directAnswer: { name: 'Resposta direta', description: 'Primeiro parágrafo responde a pergunta', points: 2 },
          hasList: { name: 'Lista estruturada', description: 'Contém listas numeradas ou marcadores', points: 1 },
          hasTable: { name: 'Tabela', description: 'Dados apresentados em tabela', points: 1 },
          conciseAnswer: { name: 'Resposta concisa', description: 'Resposta de 40-60 palavras', points: 1 }
        },
        tip: 'Responda a pergunta implícita do título logo no primeiro parágrafo.'
      },

      aiOverview: {
        name: 'Otimizado para AI Overview',
        maxPoints: 5,
        description: 'Preparação para ser citado nas respostas geradas por IA do Google.',
        whyItMatters: 'AI Overviews são o futuro da busca. O Google seleciona trechos de sites confiáveis para compor resumos. Ser citado = visibilidade massiva.',
        howToImprove: [
          'Escreva fatos verificáveis e objetivos (não opiniões)',
          'Use estrutura clara: quem, o quê, quando, onde, por quê',
          'Inclua números, datas e nomes específicos',
          'Evite linguagem vaga ou ambígua',
          'Mantenha um tom neutro e informativo'
        ],
        aiPreferences: {
          likes: [
            'Fatos verificáveis com fontes',
            'Informações atualizadas',
            'Estrutura lógica e clara',
            'Dados específicos (números, datas)',
            'Linguagem objetiva'
          ],
          avoids: [
            'Opiniões sem fundamentação',
            'Clickbait e sensacionalismo',
            'Informações vagas ou ambíguas',
            'Conteúdo desatualizado',
            'Especulações apresentadas como fatos'
          ]
        },
        examples: {
          good: 'O PIB brasileiro cresceu 2,9% em 2023, segundo dados do IBGE divulgados em março de 2024. O resultado superou a expectativa do mercado, que projetava alta de 2,5%.',
          bad: 'A economia brasileira teve um desempenho surpreendente que pode indicar uma melhora significativa no cenário econômico.'
        },
        subMetrics: {
          clearStructure: { name: 'Estrutura clara', description: 'Fluxo lógico de informações', points: 2 },
          factualStatements: { name: 'Fatos verificáveis', description: 'Informações objetivas e checáveis', points: 1 },
          conciseSummary: { name: 'Resumível', description: 'Conteúdo pode ser resumido facilmente', points: 1 },
          noMisleading: { name: 'Sem sensacionalismo', description: 'Tom neutro e informativo', points: 1 }
        },
        tip: 'Escreva como se estivesse criando uma entrada de enciclopédia: fatos, não opiniões.'
      }
    }
  }
};

// ═══════════════════════════════════════════════════════════════
// HELPER FUNCTION TO GET EXPLANATION BY METRIC KEY
// ═══════════════════════════════════════════════════════════════

export const getExplanation = (categoryKey, metricKey) => {
  const category = SEO_EXPLANATIONS[categoryKey];
  if (!category) return null;

  if (metricKey) {
    return category.metrics?.[metricKey] || null;
  }

  return category;
};

// ═══════════════════════════════════════════════════════════════
// QUICK TIPS FOR EACH SCORE RANGE
// ═══════════════════════════════════════════════════════════════

export const SCORE_TIPS = {
  excellent: {
    range: '80-100',
    message: 'Excelente! Seu artigo está bem otimizado para SEO.',
    suggestions: [
      'Mantenha a qualidade do conteúdo',
      'Considere adicionar mais links internos para outros artigos',
      'Atualize o artigo periodicamente para manter relevância'
    ]
  },
  good: {
    range: '60-79',
    message: 'Bom trabalho! Algumas melhorias podem elevar seu score.',
    suggestions: [
      'Verifique se o título e meta description estão otimizados',
      'Adicione mais fontes e citações para aumentar E-E-A-T',
      'Considere incluir listas ou subtítulos para melhor estrutura'
    ]
  },
  regular: {
    range: '40-59',
    message: 'Seu artigo precisa de atenção em algumas áreas.',
    suggestions: [
      'Expanda o conteúdo com mais detalhes e contexto',
      'Adicione fontes oficiais e citações de especialistas',
      'Melhore a estrutura com subtítulos e parágrafos menores'
    ]
  },
  critical: {
    range: '0-39',
    message: 'Atenção: várias áreas precisam de melhoria significativa.',
    suggestions: [
      'Revise completamente o título e meta description',
      'Adicione muito mais conteúdo substancial',
      'Inclua fontes, citações e elementos de autoridade',
      'Estruture melhor o texto com introdução, desenvolvimento e conclusão'
    ]
  }
};

export const getScoreTips = (score) => {
  if (score >= 80) return SCORE_TIPS.excellent;
  if (score >= 60) return SCORE_TIPS.good;
  if (score >= 40) return SCORE_TIPS.regular;
  return SCORE_TIPS.critical;
};

export default SEO_EXPLANATIONS;
