"""
LLM Service for TMC Redação

Handles AI-powered article generation using Claude Sonnet 4.5.
"""

import os
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

# Configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20241022")
MAX_TOKENS = 4096
MIN_ARTICLE_LENGTH = 2000  # TMC standard for columnists

# Persona descriptions
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
    tipo_materia: str = "destaque"
) -> str:
    """
    Build the system prompt for article generation.

    Args:
        persona: Writer persona key
        tom: Writing tone key
        tipo_materia: Article type key

    Returns:
        Complete system prompt string
    """
    persona_info = PERSONAS.get(persona, PERSONAS["imparcial"])
    tone_info = TONES.get(tom, TONES["formal"])
    type_info = ARTICLE_TYPES.get(tipo_materia, ARTICLE_TYPES["destaque"])

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
   - Inclua subtítulos quando apropriado
   - Destaque citações importantes
   - Mantenha fluidez entre parágrafos

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
     "conteudo": "Corpo completo da matéria...",
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
    """Service class for LLM operations."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM service.

        Args:
            api_key: Anthropic API key (defaults to env var)
        """
        self.api_key = api_key or ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = ANTHROPIC_MODEL

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
        tags: Optional[list] = None
    ) -> dict:
        """
        Generate a journalistic article using Claude.

        Args:
            texto_base: Source text content
            persona: Writer persona (imparcial|especialista|colunista|influencer)
            tom: Writing tone (formal|informal|tecnico|persuasivo|neutro)
            tipo_materia: Article type (destaque|coluna|servico|analise|reportagem)
            orientacao_lide: Lead paragraph guidance
            citacoes: Quotes to include
            contexto: Background context
            creditos: Source credits
            tags: Tags for SEO targeting

        Returns:
            dict with titulo, linha_fina, conteudo, tags_sugeridas
        """
        logger.info(f"Generating article with persona={persona}, tom={tom}, tipo={tipo_materia}")

        system_prompt = get_system_prompt(persona, tom, tipo_materia)
        user_prompt = build_user_prompt(
            texto_base=texto_base,
            orientacao_lide=orientacao_lide,
            citacoes=citacoes,
            contexto=contexto,
            creditos=creditos,
            tags=tags
        )

        try:
            # Use sync client in async context (Anthropic SDK handles this)
            message = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            response_text = message.content[0].text
            logger.debug(f"Raw LLM response: {response_text[:500]}...")

            # Parse JSON response
            import json

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

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise RuntimeError(f"AI service error: {str(e)}")
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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            import json

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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            import json

            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
                return result.get("tags", [])[:max_tags]

            return []

        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            return []


# Singleton instance for easy import
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the LLM service singleton.

    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
