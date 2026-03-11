"""
AI Enrichment Service for RSS Articles

Provides AI-powered semantic categorization and SEO tag generation
for articles during the RSS collection pipeline.
"""

import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any

from models.article import ArticleCreate
from services.llm_service import LLMService, is_llm_configured, get_llm_service
from services.config import get_config

logger = logging.getLogger(__name__)

# Configuration from environment
AI_ENRICHMENT_ENABLED = os.environ.get("AI_ENRICHMENT_ENABLED", "true").lower() == "true"
AI_ENRICHMENT_BATCH_SIZE = int(os.environ.get("AI_ENRICHMENT_BATCH_SIZE", "5"))
AI_ENRICHMENT_MAX_ARTICLES_PER_SOURCE = int(os.environ.get("AI_ENRICHMENT_MAX_ARTICLES_PER_SOURCE", "20"))
AI_ENRICHMENT_TIMEOUT = int(os.environ.get("AI_ENRICHMENT_TIMEOUT", "60"))

# Valid categories for classification
VALID_CATEGORIES = [
    "Politica",
    "Economia",
    "Esportes",
    "Tecnologia",
    "Saude",
    "Cultura",
    "Entretenimento",
    "Internacional",
    "Brasil",
    "Ciencia",
    "Educacao",
    "Meio Ambiente",
    "Seguranca",
    "Celebridades"
]

# System prompt for AI classification (Portuguese for Brazilian content)
CLASSIFICATION_SYSTEM_PROMPT = """Você é um especialista em classificação de conteúdo jornalístico e SEO.

Sua tarefa é analisar artigos de notícias e:
1. Classificar cada artigo em UMA categoria válida
2. Gerar 5-8 tags SEO relevantes para cada artigo

## CATEGORIAS VÁLIDAS
Use EXATAMENTE uma destas categorias (sem acentos):
- Politica
- Economia
- Esportes
- Tecnologia
- Saude
- Cultura
- Entretenimento
- Internacional
- Brasil
- Ciencia
- Educacao
- Meio Ambiente
- Seguranca
- Celebridades

## REGRAS PARA TAGS
- Tags em português, sem acentos, minúsculas
- Termos pesquisáveis e relevantes para SEO
- Incluir: tema principal, entidades (pessoas, empresas, lugares), contexto
- Separar palavras compostas com hífen (ex: "meio-ambiente", "copa-do-mundo")

## FORMATO DE RESPOSTA
Responda APENAS com JSON válido no formato:
```json
{
  "classifications": [
    {"id": "0", "category": "Categoria", "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]},
    {"id": "1", "category": "Categoria", "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]}
  ]
}
```

IMPORTANTE: O campo "id" deve corresponder ao índice do artigo na lista fornecida."""


def _build_batch_prompt(articles: List[ArticleCreate]) -> str:
    """
    Build the user prompt for a batch of articles.

    Args:
        articles: List of articles to classify

    Returns:
        User prompt string with article details
    """
    prompt_parts = ["Classifique os seguintes artigos:\n"]

    for idx, article in enumerate(articles):
        # Use title and preview/content for classification
        content_preview = ""
        if article.content:
            content_preview = article.content[:500]
        elif article.preview:
            content_preview = article.preview

        prompt_parts.append(f"""
---
ARTIGO {idx}:
Título: {article.title}
Conteúdo: {content_preview}
Categoria original: {article.category or 'N/A'}
---""")

    prompt_parts.append("\nResponda com o JSON de classificações.")

    return "\n".join(prompt_parts)


def _normalize_category(category: str) -> Optional[str]:
    """
    Normalize and validate a category.

    Args:
        category: Category string from AI response

    Returns:
        Valid category or None if invalid
    """
    if not category:
        return None

    # Normalize: remove accents, title case
    normalized = category.strip().title()

    # Map common variations
    category_map = {
        "Política": "Politica",
        "Saúde": "Saude",
        "Ciência": "Ciencia",
        "Educação": "Educacao",
        "Segurança": "Seguranca",
        "Meio-Ambiente": "Meio Ambiente",
        "MeioAmbiente": "Meio Ambiente",
    }

    normalized = category_map.get(normalized, normalized)

    if normalized in VALID_CATEGORIES:
        return normalized

    return None


def _normalize_tags(tags: List[str]) -> List[str]:
    """
    Normalize tags: lowercase, no accents, clean format.

    Args:
        tags: List of tag strings

    Returns:
        Normalized tag list
    """
    if not tags:
        return []

    normalized = []
    for tag in tags:
        if not isinstance(tag, str):
            continue

        # Lowercase and strip
        clean_tag = tag.lower().strip()

        # Remove common accent characters
        accent_map = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'ü': 'u',
            'ç': 'c'
        }
        for accent, replacement in accent_map.items():
            clean_tag = clean_tag.replace(accent, replacement)

        # Only keep valid characters
        clean_tag = ''.join(c for c in clean_tag if c.isalnum() or c in '-_ ')
        clean_tag = clean_tag.strip()

        if clean_tag and len(clean_tag) >= 2:
            normalized.append(clean_tag)

    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in normalized:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return unique_tags[:8]  # Max 8 tags


async def _classify_batch(
    llm: LLMService,
    articles: List[ArticleCreate],
    timeout: int = AI_ENRICHMENT_TIMEOUT
) -> Dict[str, Dict[str, Any]]:
    """
    Classify a batch of articles using LLM.

    Args:
        llm: LLMService instance
        articles: Batch of articles to classify
        timeout: Timeout in seconds

    Returns:
        Dict mapping article index to classification result
    """
    user_prompt = _build_batch_prompt(articles)

    try:
        response_text = await asyncio.wait_for(
            llm._call_api(
                system=CLASSIFICATION_SYSTEM_PROMPT,
                user_content=user_prompt,
                max_tokens=1024,
                model=get_config().classification_model,
                task_type='classification'
            ),
            timeout=timeout
        )

        # Parse JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end <= json_start:
            logger.warning("No valid JSON found in AI response")
            return {}

        result = json.loads(response_text[json_start:json_end])
        classifications = result.get("classifications", [])

        # Build mapping by ID
        mapping = {}
        for item in classifications:
            article_id = str(item.get("id", ""))
            category = _normalize_category(item.get("category", ""))
            tags = _normalize_tags(item.get("tags", []))

            if article_id:
                mapping[article_id] = {
                    "category": category,
                    "tags": tags
                }

        return mapping

    except asyncio.TimeoutError:
        logger.warning(f"AI classification timed out after {timeout}s")
        return {}
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI response JSON: {e}")
        return {}
    except Exception as e:
        logger.warning(f"AI classification error: {e}")
        return {}


async def enrich_articles_with_ai(
    articles: List[ArticleCreate],
    max_articles: int = AI_ENRICHMENT_MAX_ARTICLES_PER_SOURCE,
    batch_size: int = AI_ENRICHMENT_BATCH_SIZE
) -> List[ArticleCreate]:
    """
    Enrich articles with AI-generated categories and tags.

    This function processes articles in batches, calling the LLM to generate
    semantic categories and SEO-optimized tags. On failure, articles retain
    their original RSS metadata.

    Args:
        articles: List of ArticleCreate objects to enrich
        max_articles: Maximum articles to process per source
        batch_size: Articles per API call

    Returns:
        List of ArticleCreate with enriched category and tags
    """
    # Check if feature is enabled
    if not AI_ENRICHMENT_ENABLED:
        logger.debug("AI enrichment is disabled")
        return articles

    # Check if LLM is configured
    if not is_llm_configured():
        logger.warning("LLM not configured, skipping AI enrichment")
        return articles

    if not articles:
        return articles

    # Limit articles to process
    articles_to_process = articles[:max_articles]
    articles_skipped = articles[max_articles:]

    if articles_skipped:
        logger.info(f"AI enrichment: processing {len(articles_to_process)} articles, skipping {len(articles_skipped)}")

    try:
        llm = get_llm_service()
    except Exception as e:
        logger.warning(f"Failed to initialize LLM service: {e}")
        return articles

    total_enriched = 0

    # Build all batches upfront
    batches = []
    for batch_start in range(0, len(articles_to_process), batch_size):
        batch_end = min(batch_start + batch_size, len(articles_to_process))
        batches.append(articles_to_process[batch_start:batch_end])

    # Process all batches concurrently (up to 3 concurrent LLM calls)
    semaphore = asyncio.Semaphore(3)

    async def _process_batch(batch_idx: int, batch: list) -> Dict[str, Dict[str, Any]]:
        async with semaphore:
            logger.debug(f"AI enrichment: processing batch {batch_idx + 1} ({len(batch)} articles)")
            return await _classify_batch(llm, batch)

    batch_results = await asyncio.gather(
        *[_process_batch(i, b) for i, b in enumerate(batches)],
        return_exceptions=True
    )

    # Apply classifications to articles in order
    enriched_articles = []
    for batch, result in zip(batches, batch_results):
        if isinstance(result, Exception):
            logger.warning(f"AI enrichment batch failed: {result}")
            classifications = {}
        else:
            classifications = result

        for idx, article in enumerate(batch):
            batch_idx_str = str(idx)

            if batch_idx_str in classifications:
                classification = classifications[batch_idx_str]

                # Apply category if valid
                if classification.get("category"):
                    article.category = classification["category"]
                    total_enriched += 1

                # Apply tags if present
                if classification.get("tags"):
                    article.tags = classification["tags"]

            enriched_articles.append(article)

    # Add skipped articles unchanged
    enriched_articles.extend(articles_skipped)

    logger.info(f"AI enrichment completed: {total_enriched}/{len(articles_to_process)} articles enriched")

    return enriched_articles


def is_ai_enrichment_enabled() -> bool:
    """Check if AI enrichment feature is enabled and configured."""
    return AI_ENRICHMENT_ENABLED and is_llm_configured()
