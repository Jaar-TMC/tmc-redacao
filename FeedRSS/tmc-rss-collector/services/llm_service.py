"""
LLM Service for TMC Redação

Handles AI-powered article generation using Claude Sonnet 4.5.
Supports both direct Anthropic API and Azure AI Services (Anthropic proxy).
"""

import os
import json
import logging
import re
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


def repair_json(json_str: str) -> str:
    """
    Attempt to repair common JSON errors from LLM responses.

    Args:
        json_str: Potentially malformed JSON string

    Returns:
        Repaired JSON string
    """
    # First, try to fix unescaped newlines within string values
    # This is a common issue when LLM generates markdown content

    # Process character by character to properly escape newlines inside strings
    result = []
    in_string = False
    escape_next = False
    i = 0

    while i < len(json_str):
        char = json_str[i]

        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            escape_next = True
            result.append(char)
            i += 1
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        if in_string:
            # Inside a string, escape literal newlines and tabs
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            else:
                result.append(char)
        else:
            result.append(char)

        i += 1

    json_str = ''.join(result)

    # Remove any trailing content after the main JSON object
    # Find matching braces
    brace_count = 0
    json_end = -1
    in_string = False
    escape_next = False

    for i, char in enumerate(json_str):
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break

    if json_end > 0:
        json_str = json_str[:json_end]

    # Fix trailing commas before ] or }
    json_str = re.sub(r',\s*]', ']', json_str)
    json_str = re.sub(r',\s*}', '}', json_str)

    # Fix missing commas between elements (common LLM error)
    # Pattern: }" followed by "{ without comma
    json_str = re.sub(r'}\s*"', '}, "', json_str)
    json_str = re.sub(r'}\s*{', '}, {', json_str)
    json_str = re.sub(r']\s*"', '], "', json_str)

    return json_str

# Configuration - Azure AI Services (Anthropic endpoint)
AZURE_AI_API_KEY = os.environ.get("AZURE_AI_API_KEY")
AZURE_AI_ENDPOINT = os.environ.get("AZURE_AI_ENDPOINT", "https://modelos-chave-jaar-resource.services.ai.azure.com/anthropic/v1/messages")

# Fallback to direct Anthropic API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"

# Model configuration
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 4096
MIN_ARTICLE_LENGTH = 2000  # TMC standard for columnists

# =============================================================================
# TMC EDITORIAL GUIDELINES - Category-Based System
# =============================================================================

# TMC General Guidelines (shared across all categories)
TMC_GENERAL_GUIDELINES = """
## DIRETRIZES GERAIS TMC

### Público-Alvo
Pessoas de 30 a 40 anos, heavy users de conteúdo digital, que consomem notícias em redes sociais, sites e newsletters.

### Linguagem
- Frases curtas, vocabulário simples e direto, sem infantilização
- Evitar jargões (politiquês, juridiquês, economês) - quando usar termos técnicos, explicar rapidamente
- Traduzir a informação para que todo mundo consiga compreender

### Princípios Editoriais
- Informação didática, sempre oferecendo contexto (por que isso importa)
- Títulos chamativos (não apelativos) que provoquem curiosidade - o texto deve entregar a resposta prometida
- Textos curtos / bullet points quando fizer sentido
- SEM torcida político-partidária
- Evitar adjetivos que representem juízo de valor em materiais informativos ("absurdo", "vergonhoso", "genial")
- Em colunas ou materiais opinativos, adjetivos valorativos estão liberados

### VETOS UNIVERSAIS (para TODAS as categorias)
- Ataques pessoais, preconceito ou estigmatização (raça, gênero, classe, corpo, saúde mental, religião)
- Body shaming, xenofobia, homofobia, machismo
- Exposição de dados íntimos sem autorização
- Transformar questões sensíveis (saúde mental, abuso, luto) em meme ou piada
- Sensacionalismo em acidentes e crimes ("cena chocante", "detalhes macabros")
"""

# Category-based editorial voices (replaces generic PERSONAS)
CATEGORIAS_EDITORIAIS = {
    "esportes": {
        "id": "esportes",
        "name": "Esportes",
        "description": "Cobertura esportiva com paixão e proximidade ao torcedor",
        "reference": "CazéTV",
        "allows_opinion": True,
        "default_tone": "informal",
        "available_tones": ["informal", "emocional", "sobrio"],
        "system_prompt_base": """Você é um redator esportivo brasileiro experiente.
Referência de estilo: CazéTV - proximidade com torcedor, paixão, humor com responsabilidade.

## CARACTERÍSTICAS
- Linguagem popular e descontraída, equilibrando diversão com responsabilidade
- Proximidade com o torcedor
- Paixão pelo esporte
- Humor em contextos apropriados

## PERMITIDO
- Gírias de forma moderada
- Expressões do universo esportivo ("jogo pegado", "clima de decisão")
- Explorar humor e brincar com situações de jogo
- Explorar bastidores e memes ligados a clubes e campeonatos
- Tom emocionado em gols, títulos, grandes momentos
- Assumir claramente quando o conteúdo for opinativo (coluna, comentário)

## VETADO
- Discurso e postura machistas (frequentes em coberturas esportivas)
- Humilhar atleta, clube ou torcedor
- Body shaming, xenofobia, homofobia
- Ofensas ou palavrões diretos
- Incitar rivalidade violenta entre torcidas
- Tratar eventos graves (acidentes com torcida, violência em estádio) como entretenimento
- Em casos de violência, acidentes ou mortes: adotar tom jornalístico sóbrio, sem piada""",
        "dos": [
            "Use gírias esportivas moderadamente",
            "Expressões como 'jogo pegado', 'clima de decisão'",
            "Humor em contextos apropriados",
            "Tom emocionado para grandes momentos",
            "Explore bastidores e memes de clubes"
        ],
        "donts": [
            "Discurso machista",
            "Humilhar atletas ou torcedores",
            "Body shaming, xenofobia, homofobia",
            "Incitar rivalidade violenta",
            "Piadas sobre acidentes ou violência"
        ]
    },
    "entretenimento": {
        "id": "entretenimento",
        "name": "Entretenimento",
        "description": "Cobertura leve, pop e divertida de cultura e celebridades",
        "reference": "The News + Pop",
        "allows_opinion": False,
        "default_tone": "informal",
        "available_tones": ["informal", "leve", "criativo"],
        "system_prompt_base": """Você é um redator de entretenimento brasileiro experiente.
Tom leve, pop e divertido, sem virar fofoca tóxica.

## CARACTERÍSTICAS
- Leve, criativo e referencial (citações de filmes, séries, músicas)
- Trocadilhos bem-humorados
- Linguagem próxima, estilo conversa informal
- Comunicação clara e objetiva

## FOCO EDITORIAL
- Lançamentos (filmes, séries, músicas, games)
- Bastidores de produções
- Shows e eventos
- Reality shows
- Cultura digital e tendências

## PERMITIDO
- Tom leve e criativo
- Referências pop (filmes, séries, músicas)
- Trocadilhos
- Linguagem próxima e conversacional

## VETADO
- Body shaming ou julgamento moral de vida pessoal ("ela engordou", "fulano se humilhou")
- Expor dados íntimos (informações pessoais, quadro de saúde sem autorização, informações de familiares)
- Transformar questões sensíveis (saúde mental, abuso, luto) em meme ou piada
- Fofoca tóxica ou invasiva""",
        "dos": [
            "Use tom leve e criativo",
            "Referências pop (filmes, séries, músicas)",
            "Trocadilhos bem-humorados",
            "Linguagem conversacional e próxima"
        ],
        "donts": [
            "Body shaming ou julgamento moral",
            "Expor dados íntimos não autorizados",
            "Fazer piada de questões sensíveis",
            "Fofoca tóxica ou invasiva"
        ]
    },
    "politica": {
        "id": "politica",
        "name": "Política",
        "description": "Cobertura política sóbria, direta e didática",
        "reference": "Sóbrio/Didático",
        "allows_opinion": True,
        "default_tone": "sobrio",
        "available_tones": ["sobrio", "didatico"],
        "system_prompt_base": """Você é um redator político brasileiro experiente.
Cobertura sóbria, direta e didática.

## CARACTERÍSTICAS
- Tom sóbrio e direto
- Explicações didáticas de termos técnicos
- Foco no impacto para o cidadão
- Contextualização sem torcida partidária

## OBRIGATÓRIO
- Explicar termos técnicos em linguagem simples ("Em resumo, o que está em jogo é...")
- Indicar sempre o impacto na vida das pessoas ("Na prática, isso pode mudar...")
- Usar perguntas-guia: "Por que isso importa?", "O que muda agora?"
- Títulos diretos com leve gancho de curiosidade, mas sóbrios
- Para denúncias e acusações, indicar sempre a fonte da informação

## VETADO
- Piadas, memes, trocadilhos ou emojis
- Preferência partidária
- Adjetivos valorativos em materiais informativos (apenas em colunas)
- Linguagem informal ou descontraída
- Sensacionalismo""",
        "dos": [
            "Explique termos técnicos ('Em resumo...')",
            "Indique impacto na vida das pessoas",
            "Use perguntas-guia ('Por que isso importa?')",
            "Títulos diretos e sóbrios",
            "Sempre cite a fonte para denúncias"
        ],
        "donts": [
            "Piadas, memes, trocadilhos, emojis",
            "Preferência partidária",
            "Adjetivos valorativos (exceto colunas)",
            "Linguagem informal"
        ]
    },
    "economia": {
        "id": "economia",
        "name": "Economia",
        "description": "Cobertura econômica traduzida para o cotidiano",
        "reference": "Traduzir para cotidiano",
        "allows_opinion": True,
        "default_tone": "didatico",
        "available_tones": ["didatico", "analitico"],
        "system_prompt_base": """Você é um redator econômico brasileiro experiente.
Sua missão é traduzir economia para o cotidiano do cidadão comum.

## CARACTERÍSTICAS
- Traduzir indicadores econômicos para impacto real
- Exemplos concretos e palpáveis
- Contextualização histórica e de tendências
- Dados sempre de fontes confiáveis

## OBRIGATÓRIO
- Traduzir indicadores para o cotidiano ("Com juros mais altos, fica mais caro financiar casa")
- Usar exemplos concretos (salário, aluguel, supermercado, crédito)
- Trazer contexto ("Esse movimento segue uma tendência...")
- Trazer sempre dados, cenários e análises de fontes confiáveis
- Explicar siglas e jargões (Selic, CDI, PIB...)

## VETADO
- Prometer resultados de investimento
- Tratar crise, desemprego e inflação com humor
- Usar siglas e jargões sem explicação
- Tons de pânico ("o país está quebrado")
- Sensacionalismo financeiro""",
        "dos": [
            "Traduza para o cotidiano ('Com juros mais altos...')",
            "Use exemplos concretos (salário, aluguel)",
            "Traga contexto e tendências",
            "Explique TODAS as siglas (Selic, CDI, PIB)",
            "Cite fontes confiáveis"
        ],
        "donts": [
            "Prometer resultados de investimento",
            "Humor sobre crise ou desemprego",
            "Siglas sem explicação",
            "Tom de pânico ou sensacionalismo"
        ]
    },
    "geral": {
        "id": "geral",
        "name": "Geral/Variedades",
        "description": "Cobertura de variedades com tom conversacional",
        "reference": "Conversacional",
        "allows_opinion": False,
        "default_tone": "conversacional",
        "available_tones": ["conversacional", "informativo"],
        "system_prompt_base": """Você é um redator brasileiro experiente em variedades e assuntos gerais.
Tom conversacional e próximo do leitor.

## CARACTERÍSTICAS
- Tom conversado ("Você provavelmente já passou por isso...")
- Perguntas retóricas para engajar
- Humor em temas neutros (hábitos, curiosidades)
- Linguagem acessível e próxima

## TEMAS COMUNS
- Saúde e bem-estar
- Ciência e tecnologia (divulgação)
- Comportamento
- Curiosidades
- Serviços úteis

## OBRIGATÓRIO
- Sempre citar a fonte em publicações de Saúde e Ciência
- Não dar dicas de saúde sem fonte médica

## PERMITIDO
- Tom conversacional ("Você provavelmente já passou por isso...")
- Perguntas retóricas
- Humor em temas neutros

## VETADO
- Fazer humor com tragédia, doença, violência, catástrofes
- Sensacionalismo em acidentes e crimes ("cena chocante", "detalhes macabros", "cenário de guerra")
- Expor vítimas além do necessário (nome, imagem, detalhes íntimos)
- Dicas de saúde sem fonte médica""",
        "dos": [
            "Tom conversacional e próximo",
            "Perguntas retóricas para engajar",
            "Humor em temas neutros",
            "SEMPRE cite fontes em saúde/ciência"
        ],
        "donts": [
            "Humor com tragédia ou violência",
            "Sensacionalismo em crimes/acidentes",
            "Exposição desnecessária de vítimas",
            "Dicas de saúde sem fonte médica"
        ]
    }
}

# Tones available per category
TONS_POR_CATEGORIA = {
    "esportes": {
        "informal": "Linguagem descontraída e próxima do torcedor, com gírias moderadas.",
        "emocional": "Tom emocionado e vibrante, ideal para grandes jogos e momentos históricos.",
        "sobrio": "Tom sério para coberturas de acidentes, violência ou temas sensíveis no esporte."
    },
    "entretenimento": {
        "informal": "Leve e conversacional, como uma conversa entre amigos.",
        "leve": "Descontraído e divertido, focando no lado positivo e interessante.",
        "criativo": "Mais elaborado, com referências pop e trocadilhos inteligentes."
    },
    "politica": {
        "sobrio": "Direto, sério e factual. Ideal para hard news política.",
        "didatico": "Explicativo, focando em contextualizar e traduzir termos técnicos."
    },
    "economia": {
        "didatico": "Foco em explicar e traduzir para o cotidiano do cidadão.",
        "analitico": "Mais aprofundado, com análise de cenários e tendências."
    },
    "geral": {
        "conversacional": "Próximo e engajador, como uma conversa com o leitor.",
        "informativo": "Mais direto e objetivo, focando na informação útil."
    }
}

# Legacy persona mapping for backwards compatibility
PERSONAS = {
    "imparcial": {
        "name": "Jornalista Imparcial",
        "description": """Você é um jornalista experiente e imparcial.
Sua escrita é factual, equilibrada e apresenta múltiplas perspectivas.
Evita adjetivos desnecessários e mantém distância editorial do assunto.
Usa linguagem clara e direta, sem opiniões pessoais."""
    },
    "especialista": {
        "name": "Especialista",
        "description": """Você é um especialista renomado na área do assunto.
Sua escrita demonstra profundo conhecimento técnico e autoridade.
Explica conceitos complexos de forma acessível quando necessário.
Usa terminologia específica da área com precisão."""
    },
    "colunista": {
        "name": "Colunista",
        "description": """Você é um colunista com voz própria e opinião formada.
Sua escrita é engajadora, com ponto de vista claro e argumentação forte.
Usa recursos retóricos para convencer o leitor.
Mantém estilo pessoal reconhecível."""
    },
    "influencer": {
        "name": "Influenciador Digital",
        "description": """Você é um influenciador digital que comunica de forma moderna.
Sua escrita é acessível, conversacional e conecta com o público jovem.
Usa linguagem atual sem ser informal demais.
Cria conexão emocional com o leitor."""
    }
}

# Tone descriptions
TONES = {
    "formal": "Use linguagem formal e profissional, adequada para veículos tradicionais.",
    "informal": "Use linguagem acessível e conversacional, mantendo credibilidade jornalística.",
    "tecnico": "Use vocabulário técnico especializado, com explicações quando necessário.",
    "persuasivo": "Use recursos retóricos para engajar e convencer o leitor.",
    "neutro": "Mantenha tom equilibrado e objetivo, sem posicionamento claro."
}

# Article type templates
ARTICLE_TYPES = {
    "destaque": "Matéria de destaque com estrutura de pirâmide invertida.",
    "coluna": "Coluna opinativa com argumentação estruturada.",
    "servico": "Matéria de serviço focada em utilidade para o leitor.",
    "analise": "Análise aprofundada com contexto e perspectivas.",
    "reportagem": "Reportagem completa com múltiplas fontes e ângulos."
}


def get_system_prompt(
    persona: str = "imparcial",
    tom: str = "formal",
    tipo_materia: str = "destaque",
    categoria: str = None,
    modo_opinativo: bool = False
) -> str:
    """
    Build the system prompt for article generation.

    Supports both the new category-based system and legacy persona system.

    Args:
        persona: Writer persona key (legacy, for backwards compatibility)
        tom: Writing tone key
        tipo_materia: Article type key
        categoria: Editorial category (esportes|entretenimento|politica|economia|geral)
        modo_opinativo: Whether opinion mode is enabled (for categories that allow it)

    Returns:
        Complete system prompt string
    """
    type_info = ARTICLE_TYPES.get(tipo_materia, ARTICLE_TYPES["destaque"])

    # Use category-based system if categoria is provided
    if categoria and categoria in CATEGORIAS_EDITORIAIS:
        return _build_category_prompt(categoria, tom, tipo_materia, modo_opinativo)

    # Legacy persona-based system (backwards compatibility)
    persona_info = PERSONAS.get(persona, PERSONAS["imparcial"])
    tone_info = TONES.get(tom, TONES["formal"])

    return f"""Você é um redator jornalístico brasileiro experiente.

## PERSONA
{persona_info['description']}

## TOM DE ESCRITA
{tone_info}

## TIPO DE MATÉRIA
{type_info}

## REGRAS OBRIGATÓRIAS

1. **Estrutura da Matéria:**
   - Título: Claro, informativo, 50-60 caracteres para SEO
   - Linha Fina: Resumo que complementa o título, 150-160 caracteres
   - Corpo: Mínimo {MIN_ARTICLE_LENGTH} caracteres, estrutura de pirâmide invertida

2. **Formatação:**
   - Use parágrafos curtos (3-4 linhas)
   - Inclua subtítulos quando apropriado (use ## para subtítulos)
   - Destaque citações importantes
   - Mantenha fluidez entre parágrafos

   **NEGRITO - REGRAS DE DESTAQUE (use **texto** em markdown):**
   O negrito guia a leitura e destaca informações-chave. Use com moderação (3-6 destaques por parágrafo longo).

   SEMPRE destaque:
   - **Protagonistas**: Nomes de pessoas, empresas, instituições, times na primeira menção
     Ex: "**Luiz Inácio Lula da Silva** anunciou que o **Ministério da Fazenda**..."
   - **Números impactantes**: Valores monetários, porcentagens, estatísticas, recordes
     Ex: "...aumento de **15%** nas exportações, totalizando **R$ 2,5 bilhões**..."
   - **Datas e prazos importantes**: Marcos temporais relevantes para a notícia
     Ex: "A medida entra em vigor em **1º de março de 2025**..."
   - **Locais-chave**: Cidades, países, regiões quando são centrais à notícia
     Ex: "O evento acontecerá em **São Paulo** e **Rio de Janeiro**..."
   - **Termos técnicos**: Na primeira menção, para facilitar identificação
     Ex: "O **PIB** (Produto Interno Bruto) cresceu..."
   - **Decisões e ações principais**: Verbos de impacto que definem a notícia
     Ex: "O governo **aprovou** a nova lei..." ou "A empresa **demitiu** 500 funcionários..."
   - **Citações importantes**: Frases de impacto entre aspas
     Ex: "Segundo o ministro, **'essa é a maior conquista da década'**..."

   NÃO use negrito em:
   - Artigos, preposições, conjunções isoladas
   - Informações secundárias ou de contexto
   - Parágrafos inteiros (apenas palavras/frases específicas)

3. **Qualidade:**
   - Português brasileiro correto e fluente
   - Evite repetições de palavras
   - Use verbos na voz ativa
   - Mantenha coerência e coesão

4. **SEO:**
   - Inclua palavras-chave naturalmente no texto
   - Use variações semânticas dos termos principais
   - Estruture para escaneabilidade

5. **Formato de Resposta:**
   Responda SEMPRE no seguinte formato JSON:
   ```json
   {{
     "titulo": "Título da matéria",
     "linha_fina": "Linha fina descritiva",
     "conteudo": "Corpo completo da matéria com **negritos** para destaques...",
     "tags_sugeridas": ["tag1", "tag2", "tag3"]
   }}
   ```"""


def _build_category_prompt(
    categoria: str,
    tom: str,
    tipo_materia: str,
    modo_opinativo: bool
) -> str:
    """
    Build the system prompt using TMC's category-based editorial guidelines.

    Args:
        categoria: Editorial category key
        tom: Writing tone key
        tipo_materia: Article type key
        modo_opinativo: Whether opinion mode is enabled

    Returns:
        Complete system prompt string
    """
    cat_info = CATEGORIAS_EDITORIAIS[categoria]
    type_info = ARTICLE_TYPES.get(tipo_materia, ARTICLE_TYPES["destaque"])

    # Get tone description for this category
    category_tones = TONS_POR_CATEGORIA.get(categoria, {})
    tone_desc = category_tones.get(tom, f"Tom {tom}")

    # Opinion mode section
    opinion_section = ""
    if modo_opinativo and cat_info.get("allows_opinion"):
        opinion_section = """

## MODO OPINATIVO ATIVADO
Este é um texto de OPINIÃO/COLUNA. Você pode e deve:
- Expressar ponto de vista claro sobre o tema
- Usar adjetivos valorativos para reforçar argumentos
- Construir argumentação com posicionamento definido
- Usar primeira pessoa quando apropriado
- Assumir claramente que é uma opinião/análise

IMPORTANTE: Mesmo com opinião, mantenha os vetos universais (sem preconceito, ataques pessoais, etc.)"""
    elif tipo_materia == "coluna" and cat_info.get("allows_opinion"):
        # Auto-enable opinion mode for column types in categories that allow it
        opinion_section = """

## COLUNA OPINATIVA
Este é um texto de COLUNA. Adjetivos valorativos e posicionamento estão liberados.
Mantenha os vetos universais (sem preconceito, ataques pessoais, etc.)"""

    return f"""{cat_info['system_prompt_base']}
{TMC_GENERAL_GUIDELINES}

## TOM DE ESCRITA: {tom.upper()}
{tone_desc}

## TIPO DE MATÉRIA
{type_info}
{opinion_section}

## REGRAS OBRIGATÓRIAS DE FORMATO

1. **Estrutura da Matéria:**
   - Título: Claro, informativo, 50-60 caracteres para SEO
   - Linha Fina: Resumo que complementa o título, 150-160 caracteres
   - Corpo: Mínimo {MIN_ARTICLE_LENGTH} caracteres, estrutura de pirâmide invertida

2. **Formatação:**
   - Use parágrafos curtos (3-4 linhas)
   - Inclua subtítulos quando apropriado (use ## para subtítulos)
   - Destaque citações importantes
   - Mantenha fluidez entre parágrafos

   **NEGRITO - REGRAS DE DESTAQUE (use **texto** em markdown):**
   O negrito guia a leitura e destaca informações-chave. Use com moderação (3-6 destaques por parágrafo longo).

   SEMPRE destaque:
   - **Protagonistas**: Nomes de pessoas, empresas, instituições, times na primeira menção
     Ex: "**Luiz Inácio Lula da Silva** anunciou que o **Ministério da Fazenda**..."
   - **Números impactantes**: Valores monetários, porcentagens, estatísticas, recordes
     Ex: "...aumento de **15%** nas exportações, totalizando **R$ 2,5 bilhões**..."
   - **Datas e prazos importantes**: Marcos temporais relevantes para a notícia
     Ex: "A medida entra em vigor em **1º de março de 2025**..."
   - **Locais-chave**: Cidades, países, regiões quando são centrais à notícia
     Ex: "O evento acontecerá em **São Paulo** e **Rio de Janeiro**..."
   - **Termos técnicos**: Na primeira menção, para facilitar identificação
     Ex: "O **PIB** (Produto Interno Bruto) cresceu..."
   - **Decisões e ações principais**: Verbos de impacto que definem a notícia
     Ex: "O governo **aprovou** a nova lei..." ou "A empresa **demitiu** 500 funcionários..."
   - **Citações importantes**: Frases de impacto entre aspas
     Ex: "Segundo o ministro, **'essa é a maior conquista da década'**..."

   NÃO use negrito em:
   - Artigos, preposições, conjunções isoladas
   - Informações secundárias ou de contexto
   - Parágrafos inteiros (apenas palavras/frases específicas)

3. **Qualidade:**
   - Português brasileiro correto e fluente
   - Evite repetições de palavras
   - Use verbos na voz ativa
   - Mantenha coerência e coesão

4. **SEO:**
   - Inclua palavras-chave naturalmente no texto
   - Use variações semânticas dos termos principais
   - Estruture para escaneabilidade

5. **Formato de Resposta:**
   Responda SEMPRE no seguinte formato JSON:
   ```json
   {{
     "titulo": "Título da matéria",
     "linha_fina": "Linha fina descritiva",
     "conteudo": "Corpo completo da matéria com **negritos** para destaques...",
     "tags_sugeridas": ["tag1", "tag2", "tag3"]
   }}
   ```"""


def build_user_prompt(
    texto_base: str,
    orientacao_lide: Optional[str] = None,
    citacoes: Optional[list] = None,
    contexto: Optional[str] = None,
    creditos: Optional[str] = None,
    tags: Optional[list] = None
) -> str:
    """
    Build the user prompt with all provided content.

    Args:
        texto_base: Source text content
        orientacao_lide: Lead paragraph guidance
        citacoes: Quotes to include
        contexto: Background context
        creditos: Source credits
        tags: Tags for SEO targeting

    Returns:
        Complete user prompt string
    """
    prompt_parts = []

    prompt_parts.append(f"""## TEXTO-BASE PARA REESCRITA

{texto_base}

---

Por favor, reescreva o texto acima como uma matéria jornalística completa.""")

    if orientacao_lide:
        prompt_parts.append(f"""
## ORIENTAÇÃO PARA O LIDE
{orientacao_lide}""")

    if citacoes and len(citacoes) > 0:
        quotes_text = "\n".join([f'- "{q}"' for q in citacoes])
        prompt_parts.append(f"""
## CITAÇÕES PARA INCLUIR
{quotes_text}

Inclua essas citações naturalmente no texto.""")

    if contexto:
        prompt_parts.append(f"""
## CONTEXTO ADICIONAL
{contexto}""")

    if creditos:
        prompt_parts.append(f"""
## CRÉDITOS DA FONTE
{creditos}

Inclua a atribuição de créditos apropriadamente.""")

    if tags and len(tags) > 0:
        tags_text = ", ".join(tags)
        prompt_parts.append(f"""
## TAGS/PALAVRAS-CHAVE
{tags_text}

Incorpore esses termos naturalmente no texto para SEO.""")

    prompt_parts.append("""
---

Lembre-se:
- Mínimo 2000 caracteres no corpo da matéria
- Responda APENAS com o JSON no formato especificado
- Não inclua explicações fora do JSON""")

    return "\n".join(prompt_parts)


class LLMService:
    """Service class for LLM operations using direct HTTP calls."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        """
        Initialize the LLM service.

        Supports Azure AI Services (Anthropic endpoint) or direct Anthropic API.

        Args:
            api_key: API key (defaults to AZURE_AI_API_KEY or ANTHROPIC_API_KEY)
            endpoint: API endpoint URL
        """
        # Prioritize Azure AI Services configuration
        if AZURE_AI_API_KEY:
            self.api_key = api_key or AZURE_AI_API_KEY
            self.endpoint = endpoint or AZURE_AI_ENDPOINT
            self.use_azure = True
            logger.info(f"Using Azure AI Services endpoint: {self.endpoint}")
        elif ANTHROPIC_API_KEY:
            self.api_key = api_key or ANTHROPIC_API_KEY
            self.endpoint = ANTHROPIC_ENDPOINT
            self.use_azure = False
            logger.info("Using direct Anthropic API")
        else:
            raise ValueError("Neither AZURE_AI_API_KEY nor ANTHROPIC_API_KEY configured")

        self.model = ANTHROPIC_MODEL
        self.http_client = httpx.AsyncClient(timeout=120.0)

    def _get_headers(self) -> dict:
        """Get headers for API request."""
        if self.use_azure:
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "anthropic-version": "2023-06-01"
            }
        else:
            return {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }

    async def _call_api(self, system: str, user_content: str, max_tokens: int = MAX_TOKENS) -> str:
        """Make API call and return response text."""
        headers = self._get_headers()

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [
                {"role": "user", "content": user_content}
            ]
        }

        logger.info(f"Calling API: {self.endpoint} with model {self.model}")

        response = await self.http_client.post(
            self.endpoint,
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"API error {response.status_code}: {error_text}")
            raise RuntimeError(f"AI service error: {error_text}")

        result = response.json()
        return result["content"][0]["text"]

    async def generate_article(
        self,
        texto_base: str,
        persona: str = "imparcial",
        tom: str = "formal",
        tipo_materia: str = "destaque",
        orientacao_lide: Optional[str] = None,
        citacoes: Optional[list] = None,
        contexto: Optional[str] = None,
        creditos: Optional[str] = None,
        tags: Optional[list] = None,
        categoria: Optional[str] = None,
        modo_opinativo: bool = False
    ) -> dict:
        """
        Generate a journalistic article using Claude.

        Supports both the new category-based system and legacy persona system.

        Args:
            texto_base: Source text content
            persona: Writer persona - legacy (imparcial|especialista|colunista|influencer)
            tom: Writing tone (varies by category or legacy: formal|informal|tecnico|persuasivo|neutro)
            tipo_materia: Article type (destaque|coluna|servico|analise|reportagem)
            orientacao_lide: Lead paragraph guidance
            citacoes: Quotes to include
            contexto: Background context
            creditos: Source credits
            tags: Tags for SEO targeting
            categoria: Editorial category (esportes|entretenimento|politica|economia|geral) - NEW
            modo_opinativo: Enable opinion mode for categories that allow it - NEW

        Returns:
            dict with titulo, linha_fina, conteudo, tags_sugeridas
        """
        if categoria:
            logger.info(f"Generating article with categoria={categoria}, tom={tom}, tipo={tipo_materia}, opinativo={modo_opinativo}")
        else:
            logger.info(f"Generating article with persona={persona}, tom={tom}, tipo={tipo_materia}")

        system_prompt = get_system_prompt(
            persona=persona,
            tom=tom,
            tipo_materia=tipo_materia,
            categoria=categoria,
            modo_opinativo=modo_opinativo
        )
        user_prompt = build_user_prompt(
            texto_base=texto_base,
            orientacao_lide=orientacao_lide,
            citacoes=citacoes,
            contexto=contexto,
            creditos=creditos,
            tags=tags
        )

        try:
            response_text = await self._call_api(system_prompt, user_prompt, MAX_TOKENS)
            logger.debug(f"Raw LLM response: {response_text[:500]}...")

            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)

                # Validate required fields
                if not all(key in result for key in ["titulo", "linha_fina", "conteudo"]):
                    raise ValueError("Response missing required fields")

                # Ensure tags_sugeridas exists
                if "tags_sugeridas" not in result:
                    result["tags_sugeridas"] = []

                # Validate minimum length
                content_length = len(result["conteudo"])
                if content_length < MIN_ARTICLE_LENGTH:
                    logger.warning(f"Article length {content_length} below minimum {MIN_ARTICLE_LENGTH}")

                logger.info(f"Article generated successfully. Length: {content_length} chars")
                return result
            else:
                raise ValueError("No valid JSON found in response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid AI response format: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in generate_article: {e}")
            raise

    def generate_article_sync(self, **kwargs) -> dict:
        """
        Synchronous wrapper for generate_article.

        Use this in non-async contexts (like Azure Functions with sync triggers).
        """
        import asyncio

        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, need to handle differently
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.generate_article(**kwargs))
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self.generate_article(**kwargs))

    async def extract_topics(self, texto: str) -> list:
        """
        Extract topics/key points from text using AI.

        Args:
            texto: Source text to analyze

        Returns:
            List of topics with type and content
        """
        system = "Você é um assistente especializado em análise de texto jornalístico."
        prompt = f"""Analise o seguinte texto e extraia os principais tópicos/pontos-chave.

TEXTO:
{texto}

Para cada tópico identificado, classifique como:
- fato: Informação factual objetiva
- contexto: Informação de contexto/background
- citacao: Declaração ou citação de fonte
- dado: Número, estatística ou dado quantitativo
- opiniao: Opinião ou análise

Responda em JSON:
```json
{{
  "topics": [
    {{"type": "fato", "content": "..."}},
    {{"type": "contexto", "content": "..."}}
  ]
}}
```"""

        try:
            response_text = await self._call_api(system, prompt, 2048)

            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                return result.get("topics", [])

            return []

        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return []

    async def generate_tags(self, texto: str, max_tags: int = 10) -> list:
        """
        Generate relevant tags for content.

        Args:
            texto: Content to analyze
            max_tags: Maximum number of tags

        Returns:
            List of tag strings
        """
        system = "Você é um especialista em SEO e categorização de conteúdo."
        prompt = f"""Analise o seguinte texto e sugira tags relevantes para SEO e categorização.

TEXTO:
{texto}

Gere até {max_tags} tags em português, em formato de hashtag (sem o #), relevantes para:
- SEO
- Categorização
- Temas principais
- Entidades mencionadas

Responda em JSON:
```json
{{
  "tags": ["tag1", "tag2", "tag3"]
}}
```"""

        try:
            response_text = await self._call_api(system, prompt, 1024)

            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                return result.get("tags", [])[:max_tags]

            return []

        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            return []

    async def merge_topics(self, articles: list) -> dict:
        """
        Merge and group topics from multiple articles about the same story.

        Analyzes articles together and organizes content by story element
        rather than by source, identifying common themes, exclusive content,
        and notable quotes.

        Args:
            articles: List of article dicts with keys:
                - id: Article identifier
                - title: Article title
                - content: Full article content
                - source: Source name

        Returns:
            dict with:
                - groups: Grouped story elements with versions from each source
                - exclusives: Content unique to one source
                - quotes: Extracted declarations with attribution
                - summary: Overview of the analysis
        """
        if not articles or len(articles) < 1:
            return {
                "groups": [],
                "exclusives": [],
                "quotes": [],
                "summary": {"mainTopic": "", "totalElements": 0, "commonElements": 0, "exclusiveCount": 0}
            }

        # Limit to 3 articles maximum
        if len(articles) > 3:
            logger.warning(f"Merge topics received {len(articles)} articles, limiting to 3")
            articles = articles[:3]

        logger.info(f"Merging topics from {len(articles)} articles")

        prompt = get_merge_topics_prompt(articles)

        try:
            # Use 8192 tokens for merge_topics - complex output needs more space
            response_text = await self._call_api(MERGE_TOPICS_SYSTEM, prompt, 8192)
            logger.debug(f"Merge topics response: {response_text[:500]}...")

            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]

                # Try to repair common JSON errors from LLM
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.warning("Initial JSON parse failed, attempting repair...")
                    repaired_json = repair_json(json_str)
                    result = json.loads(repaired_json)

                # Validate structure
                if "groups" not in result:
                    result["groups"] = []
                if "exclusives" not in result:
                    result["exclusives"] = []
                if "quotes" not in result:
                    result["quotes"] = []
                if "summary" not in result:
                    result["summary"] = {
                        "mainTopic": "",
                        "totalElements": len(result.get("groups", [])),
                        "commonElements": len(result.get("groups", [])),
                        "exclusiveCount": len(result.get("exclusives", []))
                    }

                # Validar e corrigir grupos com apenas 1 versão
                # Regra: grupos devem ter 2+ versões, senão vão para exclusives
                valid_groups = []
                moved_count = 0
                for group in result.get('groups', []):
                    versions = group.get('versions', [])
                    if len(versions) >= 2:
                        # Grupo válido - manter
                        valid_groups.append(group)
                    elif len(versions) == 1:
                        # Grupo inválido - converter para exclusive
                        version = versions[0]
                        exclusive = {
                            "id": f"exc-from-{group.get('id', 'unknown')}",
                            "type": group.get('type', 'fato'),
                            "content": version.get('content', ''),
                            "source": version.get('source', ''),
                            "articleId": version.get('articleId', ''),
                            "wordCount": version.get('wordCount', 0)
                        }
                        result['exclusives'].append(exclusive)
                        moved_count += 1
                        logger.info(f"Grupo '{group.get('id')}' movido para exclusives (apenas 1 versão)")

                if moved_count > 0:
                    result['groups'] = valid_groups
                    # Atualizar summary
                    result['summary']['commonElements'] = len(valid_groups)
                    result['summary']['exclusiveCount'] = len(result['exclusives'])
                    logger.info(f"Post-processing: {moved_count} grupos com 1 versão movidos para exclusives")

                logger.info(f"Merged {len(result['groups'])} groups, {len(result['exclusives'])} exclusives, {len(result['quotes'])} quotes")
                return result
            else:
                logger.error("No valid JSON found in merge topics response")
                raise ValueError("No valid JSON found in response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse merge topics response as JSON: {e}")
            raise ValueError(f"Invalid AI response format: {str(e)}")
        except Exception as e:
            logger.error(f"Error in merge_topics: {e}")
            raise

    async def edit_article(
        self,
        current_article: dict,
        instruction: str,
        edit_scope: str = "full",
        categoria: Optional[str] = None,
        tom: Optional[str] = None
    ) -> dict:
        """
        Edit an existing article based on user instructions.

        Args:
            current_article: Dict with current article data
                - titulo/title: Article title
                - linha_fina/linhaFina: Subtitle/lead
                - conteudo/content: Article body
                - tags: List of tags
            instruction: User's editing instruction (e.g., "Melhore o SEO do título")
            edit_scope: Scope of edit (full|title|linha_fina|content|tags)
            categoria: Optional editorial category for tone guidance
            tom: Optional tone setting

        Returns:
            dict with:
                - titulo: Edited title
                - linha_fina: Edited subtitle
                - conteudo: Edited content
                - tags: Edited tags
                - changes_summary: Description of changes made
        """
        logger.info(f"Editing article with instruction: {instruction[:100]}...")

        # Build system prompt with optional category/tone context
        system_prompt = EDIT_ARTICLE_SYSTEM
        if categoria and categoria in CATEGORIAS_EDITORIAIS:
            cat_info = CATEGORIAS_EDITORIAIS[categoria]
            system_prompt += f"\n\n## CATEGORIA EDITORIAL: {cat_info['name']}\n{cat_info['system_prompt_base'][:500]}..."
        if tom:
            system_prompt += f"\n\n## TOM DE ESCRITA: {tom}"

        user_prompt = get_edit_article_prompt(current_article, instruction, edit_scope)

        try:
            response_text = await self._call_api(system_prompt, user_prompt, MAX_TOKENS)
            logger.debug(f"Edit article response: {response_text[:500]}...")

            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]

                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.warning("Initial JSON parse failed, attempting repair...")
                    repaired_json = repair_json(json_str)
                    result = json.loads(repaired_json)

                # Ensure all required fields exist
                if "titulo" not in result:
                    result["titulo"] = current_article.get('titulo', current_article.get('title', ''))
                if "linha_fina" not in result:
                    result["linha_fina"] = current_article.get('linha_fina', current_article.get('linhaFina', ''))
                if "conteudo" not in result:
                    result["conteudo"] = current_article.get('conteudo', current_article.get('content', ''))
                if "tags" not in result:
                    result["tags"] = current_article.get('tags', [])
                if "changes_summary" not in result:
                    result["changes_summary"] = "Artigo editado conforme instrução."

                logger.info(f"Article edited successfully. Changes: {result['changes_summary']}")
                return result
            else:
                logger.error("No valid JSON found in edit article response")
                raise ValueError("No valid JSON found in response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse edit article response as JSON: {e}")
            raise ValueError(f"Invalid AI response format: {str(e)}")
        except Exception as e:
            logger.error(f"Error in edit_article: {e}")
            raise


# Singleton instance for easy import
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the LLM service singleton.

    Returns:
        LLMService instance

    Raises:
        ValueError: If neither AZURE_AI_API_KEY nor ANTHROPIC_API_KEY is configured
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def is_llm_configured() -> bool:
    """Check if LLM service is properly configured."""
    return bool(AZURE_AI_API_KEY or ANTHROPIC_API_KEY)


# Merge Topics Prompts
MERGE_TOPICS_SYSTEM = """Você é um editor jornalístico experiente especializado em análise comparativa de matérias.
Sua tarefa é analisar múltiplas matérias sobre o mesmo assunto e organizar o conteúdo por ELEMENTO DA HISTÓRIA, não por fonte.

Você deve:
1. Identificar os elementos principais da história (fato principal, contexto, reações, declarações, etc.)
2. Agrupar versões semelhantes de cada elemento vindas de diferentes fontes
3. Identificar conteúdo exclusivo de cada fonte
4. Extrair citações com atribuição de fonte
5. Recomendar a melhor versão de cada elemento"""


# Edit Article System Prompt
EDIT_ARTICLE_SYSTEM = """Você é um editor de texto jornalístico especializado.
Sua tarefa é editar artigos existentes seguindo instruções específicas do usuário.

## REGRAS IMPORTANTES:
1. MANTENHA a estrutura básica do artigo (título, linha fina, conteúdo, tags)
2. APENAS modifique o que foi solicitado na instrução
3. PRESERVE informações factuais a menos que seja pedido para alterá-las
4. MANTENHA o tom e estilo consistentes com o original, a menos que seja pedido para mudar
5. Se a instrução for sobre SEO, foque em títulos mais chamativos e palavras-chave relevantes
6. Se a instrução for sobre tom, ajuste a linguagem mantendo a informação
7. Se a instrução for sobre tamanho, resuma ou expanda conforme pedido

## FORMATO DE RESPOSTA:
Responda SEMPRE em JSON válido com a estrutura:
```json
{
  "titulo": "Título editado",
  "linha_fina": "Linha fina editada",
  "conteudo": "Conteúdo editado...",
  "tags": ["tag1", "tag2"],
  "changes_summary": "Breve descrição das alterações feitas"
}
```
"""


def get_edit_article_prompt(current_article: dict, instruction: str, edit_scope: str) -> str:
    """
    Build the prompt for editing an article.

    Args:
        current_article: Dict with current article data (titulo, linha_fina, conteudo, tags)
        instruction: User's editing instruction
        edit_scope: Scope of edit (full|title|linha_fina|content|tags)

    Returns:
        User prompt string
    """
    scope_guidance = {
        "full": "Você pode editar TODOS os campos conforme necessário.",
        "title": "Foque APENAS no título. Mantenha os outros campos inalterados.",
        "linha_fina": "Foque APENAS na linha fina. Mantenha os outros campos inalterados.",
        "content": "Foque APENAS no conteúdo/corpo. Mantenha título, linha fina e tags inalterados.",
        "tags": "Foque APENAS nas tags. Mantenha título, linha fina e conteúdo inalterados."
    }

    return f"""## ARTIGO ATUAL

**Título:** {current_article.get('titulo', current_article.get('title', ''))}

**Linha Fina:** {current_article.get('linha_fina', current_article.get('linhaFina', ''))}

**Conteúdo:**
{current_article.get('conteudo', current_article.get('content', ''))}

**Tags:** {', '.join(current_article.get('tags', []))}

---

## INSTRUÇÃO DE EDIÇÃO
{instruction}

## ESCOPO
{scope_guidance.get(edit_scope, scope_guidance['full'])}

---

Por favor, edite o artigo conforme a instrução acima e retorne o resultado em JSON.
Inclua um campo "changes_summary" descrevendo brevemente o que foi alterado."""


def get_merge_topics_prompt(articles: list) -> str:
    """
    Build the prompt for merging topics from multiple articles.

    Args:
        articles: List of article dicts with id, title, content, source

    Returns:
        User prompt string
    """
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"""
--- MATÉRIA {i} ---
ID: {article.get('id')}
FONTE: {article.get('source')}
TÍTULO: {article.get('title')}
CONTEÚDO:
{article.get('content', article.get('preview', ''))}
"""

    return f"""Analise as seguintes matérias sobre o mesmo assunto e organize por elemento da história:

{articles_text}

---

Para cada ELEMENTO DA HISTÓRIA identificado, agrupe as versões de diferentes fontes.
Identifique também conteúdo EXCLUSIVO (presente em apenas uma fonte) e CITAÇÕES.

Responda EXCLUSIVAMENTE em JSON válido no seguinte formato:
```json
{{
  "groups": [
    {{
      "id": "group-1",
      "type": "fato|contexto|reacao|dado|analise|consequencia",
      "label": "FATO PRINCIPAL",
      "versions": [
        {{
          "id": "v1",
          "articleId": "article-id-original",
          "content": "Texto completo desta versão...",
          "source": "Nome da Fonte",
          "wordCount": 45,
          "isRecommended": true
        }}
      ],
      "aiSuggestion": {{
        "recommendedId": "v1",
        "reason": "Versão mais completa com mais detalhes"
      }}
    }}
  ],
  "exclusives": [
    {{
      "id": "exc-1",
      "type": "fato|contexto|reacao|dado",
      "content": "Conteúdo exclusivo...",
      "source": "Fonte única",
      "articleId": "article-id",
      "wordCount": 30
    }}
  ],
  "quotes": [
    {{
      "id": "quote-1",
      "text": "Declaração entre aspas...",
      "speaker": "Nome do declarante",
      "role": "Cargo/função",
      "source": "Fonte que publicou",
      "articleId": "article-id"
    }}
  ],
  "summary": {{
    "mainTopic": "Resumo do assunto principal em uma frase",
    "totalElements": 5,
    "commonElements": 3,
    "exclusiveCount": 2
  }}
}}
```

IMPORTANTE:
- Use os IDs originais dos artigos em articleId
- Mantenha a integridade das citações originais
- Agrupe APENAS conteúdo que trata do MESMO fato/elemento
- REGRA DE NÃO-DUPLICAÇÃO: Cada elemento vai para "groups" OU "exclusives", NUNCA ambos:
  * Se um elemento tem versões de 2+ fontes diferentes → vai para "groups" (para escolher entre versões)
  * Se um elemento aparece em apenas 1 fonte → vai para "exclusives" (NÃO crie grupo com 1 versão)
- Se as matérias tratam de assuntos DIFERENTES sem elementos em comum, coloque tudo em "exclusives"
- Recomende a versão mais completa e bem escrita de cada grupo"""
