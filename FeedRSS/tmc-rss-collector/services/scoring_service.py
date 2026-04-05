"""
Scoring Service for TMC Redacao - Editorial A/B/C Classification.

Analyzes articles using Claude AI to classify them based on 4 editorial signals:
- Inesperado (Unexpected): Is this news surprising/unexpected?
- Impacto (Impact): Does it affect the reader's life?
- Busca Agora (Search Now): Will readers search for this topic?
- Conversa (Conversation): Will readers discuss this?

Scoring System:
| Signal         | Values              | Points     |
|---------------|---------------------|------------|
| inesperado    | yes/partial/no      | 25/12/0    |
| impacto       | high/medium/low     | 30/15/0    |
| busca_agora   | yes/maybe/no        | 25/12/0    |
| conversa      | yes/maybe/no        | 20/10/0    |

Classification:
- A: total_score >= 75 (High priority - front page material)
- B: total_score 35-74 (Medium priority - good content)
- C: total_score < 35 (Low priority - filler content)
"""

import os
import json
import logging
import asyncio
import re
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime

from models import (
    ArticleScore, ArticleScoreCreate, Article
)
from services.async_db import run_db
from services.config import get_config

logger = logging.getLogger(__name__)


# =============================================================================
# SCORING CONFIGURATION
# =============================================================================

# Point values for each signal
SCORE_INESPERADO = {'yes': 25, 'partial': 12, 'no': 0}
SCORE_IMPACTO = {'high': 30, 'medium': 15, 'low': 0}
SCORE_BUSCA_AGORA = {'yes': 25, 'maybe': 12, 'no': 0}
SCORE_CONVERSA = {'yes': 20, 'maybe': 10, 'no': 0}

# Classification thresholds
THRESHOLD_A = 75  # >= 75 = Class A
THRESHOLD_B = 35  # >= 35 = Class B, < 35 = Class C

# Max tokens for scoring response
SCORING_MAX_TOKENS = 1024


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

SCORING_SYSTEM_PROMPT = """Editor de jornalismo brasileiro. Classifique artigos com 4 sinais de relevancia editorial.

SINAIS:
1. inesperado - Fato surpreendente? yes=surpreendente, partial=parcialmente inesperado, no=rotineiro
2. impacto - Afeta a vida do leitor? high=impacto direto, medium=relevante mas nao urgente, low=sem consequencia pratica
3. busca_agora - Leitor vai buscar? yes=urgente/trending, maybe=pode interessar, no=nao vai buscar
4. conversa - Vai gerar discussao? yes=debates e polemicas, maybe=algum comentario, no=sem conversa

Responda APENAS JSON puro (sem markdown, sem backticks):
{"sinal_inesperado":"yes|partial|no","sinal_impacto":"high|medium|low","sinal_busca_agora":"yes|maybe|no","sinal_conversa":"yes|maybe|no","justificativa":"max 80 chars"}

Use APENAS os valores especificados. Considere contexto brasileiro."""


SCORING_USER_PROMPT_TEMPLATE = """Analise o seguinte artigo e classifique usando os 4 sinais de relevancia editorial:

## CATEGORIA
{category}

## TITULO
{title}

## CONTEUDO
{content}

---

Considere a categoria ao avaliar os sinais. O que e "inesperado" em Esportes pode ser rotineiro em Politica, e vice-versa. Calibre sua avaliacao para o contexto da categoria.

Classifique este artigo nos 4 sinais (inesperado, impacto, busca_agora, conversa) e retorne APENAS o JSON."""


# Batch scoring system prompt (compressed, expects multiple articles)
BATCH_SCORING_SYSTEM_PROMPT = """Editor de jornalismo brasileiro. Classifique MULTIPLOS artigos com 4 sinais de relevancia editorial.

SINAIS:
1. inesperado - Fato surpreendente? yes=surpreendente, partial=parcialmente inesperado, no=rotineiro
2. impacto - Afeta a vida do leitor? high=impacto direto, medium=relevante mas nao urgente, low=sem consequencia pratica
3. busca_agora - Leitor vai buscar? yes=urgente/trending, maybe=pode interessar, no=nao vai buscar
4. conversa - Vai gerar discussao? yes=debates e polemicas, maybe=algum comentario, no=sem conversa

Responda APENAS JSON puro (sem markdown, sem backticks):
{"scores":[{"id":"0","sinal_inesperado":"...","sinal_impacto":"...","sinal_busca_agora":"...","sinal_conversa":"...","justificativa":"max 80 chars"},{"id":"1",...}]}

Use APENAS os valores especificados. Considere contexto brasileiro. Retorne um score para CADA artigo."""

# Max articles per batch scoring call
SCORING_BATCH_SIZE = 5


# =============================================================================
# HEURISTIC FALLBACK
# =============================================================================

# Keywords that indicate high editorial value (multi-category)
HIGH_VALUE_KEYWORDS = {
    'inesperado': [
        # Geral
        'surpresa', 'surpreendente', 'inesperado', 'bomba', 'exclusivo', 'urgente',
        'breaking', 'inedito', 'chocante', 'revela', 'descobre', 'bombastico',
        # Politica/Economia
        'renuncia', 'demissao', 'demitido', 'afastado', 'cassado', 'preso',
        'falencia', 'quebra', 'golpe', 'impeachment', 'escandalo',
        # Saude/Ciencia
        'surto', 'pandemia', 'descoberta', 'cura', 'vacina', 'alerta',
        # Esportes
        'eliminacao', 'rebaixamento', 'titulo'
    ],
    'impacto': [
        # Economia
        'inflacao', 'juros', 'selic', 'dolar', 'desemprego', 'salario', 'preco',
        'aumento', 'reducao', 'imposto', 'tributo', 'gasolina', 'energia',
        # Politica/Direitos
        'lei', 'votacao', 'aprovado', 'aprovada', 'reforma', 'direito', 'proibido',
        # Saude
        'medicamento', 'tratamento', 'doenca', 'morte', 'mortes', 'vitimas',
        # Seguranca
        'violencia', 'crime', 'assalto', 'acidente', 'tragedia',
        # Esportes
        'campeao', 'titulo', 'rebaixado', 'classificado'
    ],
    'busca': [
        # Geral
        'ao vivo', 'tempo real', 'resultado', 'como', 'quando', 'onde',
        # Economia
        'cotacao', 'bolsa', 'mercado', 'investimento',
        # Politica
        'eleicao', 'candidato', 'pesquisa', 'apuracao',
        # Tecnologia
        'lancamento', 'novo', 'atualizacao', 'vazamento',
        # Esportes
        'gol', 'placar', 'jogo', 'contratacao'
    ],
    'conversa': [
        # Geral
        'polemica', 'polemico', 'controverso', 'discussao', 'debate',
        'critica', 'criticou', 'ataca', 'responde', 'rebate',
        # Politica
        'corrupcao', 'fraude', 'mentira', 'fake', 'acusacao',
        # Social
        'racismo', 'preconceito', 'assedio', 'discriminacao', 'injustica',
        # Comportamento
        'viral', 'treta', 'briga', 'conflito', 'provocacao'
    ]
}

# High-relevance terms that boost article importance (multi-category)
HIGH_RELEVANCE_TERMS = [
    # Politica - Instituicoes
    'governo', 'presidente', 'lula', 'bolsonaro', 'congresso', 'senado', 'stf',
    'ministro', 'prefeitura', 'governador',
    # Economia - Instituicoes
    'banco central', 'petrobras', 'vale', 'ibovespa', 'caixa', 'itau', 'bradesco',
    # Esportes - Times grandes
    'flamengo', 'corinthians', 'palmeiras', 'sao paulo', 'santos', 'gremio',
    'internacional', 'cruzeiro', 'atletico', 'fluminense', 'botafogo', 'vasco',
    'selecao', 'brasileirao', 'libertadores', 'copa do brasil',
    # Tecnologia - Empresas
    'google', 'apple', 'microsoft', 'meta', 'amazon', 'openai', 'nvidia',
    # Saude
    'sus', 'anvisa', 'ministerio da saude',
    # Cultura
    'globo', 'netflix', 'spotify'
]


def _heuristic_score_article(title: str, content: str) -> Dict[str, Any]:
    """
    Fallback heuristic scoring when LLM is unavailable.

    Uses keyword matching to estimate editorial relevance.
    This is less accurate than AI but provides a reasonable fallback.

    Args:
        title: Article title
        content: Article content (may be truncated)

    Returns:
        Dict with signals and scores
    """
    text = f"{title} {content or ''}".lower()

    # Count keyword matches for each signal
    inesperado_matches = sum(1 for kw in HIGH_VALUE_KEYWORDS['inesperado'] if kw in text)
    impacto_matches = sum(1 for kw in HIGH_VALUE_KEYWORDS['impacto'] if kw in text)
    busca_matches = sum(1 for kw in HIGH_VALUE_KEYWORDS['busca'] if kw in text)
    conversa_matches = sum(1 for kw in HIGH_VALUE_KEYWORDS['conversa'] if kw in text)

    # Check for high-relevance terms (boost relevance for major entities/institutions)
    relevance_boost = any(term in text for term in HIGH_RELEVANCE_TERMS)

    # Determine signals based on keyword counts
    if inesperado_matches >= 2:
        sinal_inesperado = 'yes'
    elif inesperado_matches >= 1:
        sinal_inesperado = 'partial'
    else:
        sinal_inesperado = 'no'

    if impacto_matches >= 2 or (impacto_matches >= 1 and relevance_boost):
        sinal_impacto = 'high'
    elif impacto_matches >= 1:
        sinal_impacto = 'medium'
    else:
        sinal_impacto = 'low'

    if busca_matches >= 2 or (busca_matches >= 1 and relevance_boost):
        sinal_busca_agora = 'yes'
    elif busca_matches >= 1:
        sinal_busca_agora = 'maybe'
    else:
        sinal_busca_agora = 'no'

    if conversa_matches >= 2 or (conversa_matches >= 1 and relevance_boost):
        sinal_conversa = 'yes'
    elif conversa_matches >= 1:
        sinal_conversa = 'maybe'
    else:
        sinal_conversa = 'no'

    return {
        'sinal_inesperado': sinal_inesperado,
        'sinal_impacto': sinal_impacto,
        'sinal_busca_agora': sinal_busca_agora,
        'sinal_conversa': sinal_conversa,
        'justificativa': 'Classificado por heuristica (LLM indisponivel)'
    }


# =============================================================================
# SCORING SERVICE
# =============================================================================

class ScoringService:
    """
    Service for scoring articles using Claude AI.

    Analyzes articles based on 4 editorial signals and assigns
    A/B/C classification for editorial prioritization.
    """

    def __init__(self, llm_service=None, db_service=None):
        """
        Initialize the scoring service.

        Args:
            llm_service: Optional LLMService instance (will use singleton if not provided)
            db_service: Optional DatabaseService instance (will use singleton if not provided)
        """
        self._llm_service = llm_service
        self._db_service = db_service

    @property
    def llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            from services.llm_service import get_llm_service, is_llm_configured
            if is_llm_configured():
                self._llm_service = get_llm_service()
        return self._llm_service

    @property
    def db_service(self):
        """Lazy load database service."""
        if self._db_service is None:
            from services.database import get_db
            self._db_service = get_db()
        return self._db_service

    def _calculate_scores(self, signals: Dict[str, str]) -> Tuple[Dict[str, int], int, str]:
        """
        Calculate numeric scores and classification from signals.

        Args:
            signals: Dict with sinal_inesperado, sinal_impacto, sinal_busca_agora, sinal_conversa

        Returns:
            Tuple of (scores_dict, total_score, classification)
        """
        score_inesperado = SCORE_INESPERADO.get(signals.get('sinal_inesperado', 'no'), 0)
        score_impacto = SCORE_IMPACTO.get(signals.get('sinal_impacto', 'low'), 0)
        score_busca_agora = SCORE_BUSCA_AGORA.get(signals.get('sinal_busca_agora', 'no'), 0)
        score_conversa = SCORE_CONVERSA.get(signals.get('sinal_conversa', 'no'), 0)

        total_score = score_inesperado + score_impacto + score_busca_agora + score_conversa

        if total_score >= THRESHOLD_A:
            classification = 'A'
        elif total_score >= THRESHOLD_B:
            classification = 'B'
        else:
            classification = 'C'

        scores = {
            'score_inesperado': score_inesperado,
            'score_impacto': score_impacto,
            'score_busca_agora': score_busca_agora,
            'score_conversa': score_conversa
        }

        return scores, total_score, classification

    async def _analyze_with_llm(self, title: str, content: str, category: str = '') -> Optional[Dict[str, Any]]:
        """
        Analyze article using Claude AI.

        Args:
            title: Article title
            content: Article content
            category: Article category (e.g. "Politica", "Esportes")

        Returns:
            Dict with AI analysis or None if LLM unavailable
        """
        if not self.llm_service:
            logger.warning("LLM service not available, will use heuristic fallback")
            return None

        # Truncate content for scoring (2000 chars is enough for editorial signals)
        truncated_content = content[:2000] if content and len(content) > 2000 else (content or '')

        user_prompt = SCORING_USER_PROMPT_TEMPLATE.format(
            title=title,
            content=truncated_content,
            category=category or 'Nao especificada'
        )

        try:
            response_text = await self.llm_service._call_api(
                SCORING_SYSTEM_PROMPT,
                user_prompt,
                SCORING_MAX_TOKENS,
                model=get_config().scoring_model,
                task_type='scoring'
            )

            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)

                # Validate required fields
                required = ['sinal_inesperado', 'sinal_impacto', 'sinal_busca_agora', 'sinal_conversa']
                if all(k in result for k in required):
                    return result
                else:
                    logger.warning(f"LLM response missing required fields: {result}")
                    return None
            else:
                logger.warning(f"No valid JSON in LLM response: {response_text[:200]}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM scoring response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling LLM for scoring: {e}")
            return None

    def _build_batch_scoring_prompt(self, articles: List[Dict[str, Any]]) -> str:
        """
        Build a user prompt for batch scoring multiple articles in a single LLM call.

        Args:
            articles: List of dicts with 'title', 'content', 'category' keys

        Returns:
            Formatted user prompt string
        """
        parts = ["Classifique estes artigos:\n"]

        for idx, article in enumerate(articles):
            content = article.get('content', '') or ''
            truncated = content[:2000]
            category = article.get('category', '') or 'Nao especificada'
            title = article.get('title', '')

            parts.append(f"""ARTIGO {idx}:
Categoria: {category}
Titulo: {title}
Conteudo: {truncated}
""")

        parts.append("""Responda em JSON puro:
{"scores":[{"id":"0","sinal_inesperado":"...","sinal_impacto":"...","sinal_busca_agora":"...","sinal_conversa":"...","justificativa":"max 80 chars"},...]}\n""")

        return "\n".join(parts)

    async def _analyze_batch_with_llm(self, articles: List[Dict[str, Any]]) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Analyze a batch of articles using a single LLM call.

        Args:
            articles: List of article dicts with 'title', 'content', 'category'

        Returns:
            Dict mapping article index (str) to signal dict, or None if LLM unavailable
        """
        if not self.llm_service:
            logger.warning("LLM service not available for batch scoring")
            return None

        if not articles:
            return {}

        user_prompt = self._build_batch_scoring_prompt(articles)

        # Scale max_tokens by batch size (each article ~150 tokens output + overhead)
        batch_max_tokens = min(200 * len(articles) + 100, 2048)

        try:
            response_text = await self.llm_service._call_api(
                BATCH_SCORING_SYSTEM_PROMPT,
                user_prompt,
                batch_max_tokens,
                model=get_config().scoring_model,
                task_type='scoring'
            )

            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end <= json_start:
                logger.warning(f"No valid JSON in batch scoring response: {response_text[:200]}")
                return None

            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)

            scores_list = result.get('scores', [])
            if not scores_list:
                logger.warning("Batch scoring response has empty 'scores' array")
                return None

            # Build mapping by article index
            required_fields = ['sinal_inesperado', 'sinal_impacto', 'sinal_busca_agora', 'sinal_conversa']
            mapping = {}

            for item in scores_list:
                article_id = str(item.get('id', ''))
                if article_id and all(k in item for k in required_fields):
                    mapping[article_id] = {
                        'sinal_inesperado': item['sinal_inesperado'],
                        'sinal_impacto': item['sinal_impacto'],
                        'sinal_busca_agora': item['sinal_busca_agora'],
                        'sinal_conversa': item['sinal_conversa'],
                        'justificativa': item.get('justificativa', '')
                    }
                else:
                    logger.warning(f"Batch scoring: article {article_id} missing required fields, will fallback")

            logger.info(f"Batch scoring parsed {len(mapping)}/{len(articles)} articles successfully")
            return mapping

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse batch scoring response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling LLM for batch scoring: {e}")
            return None

    async def score_article(
        self,
        article_id: UUID,
        title: str,
        content: str,
        use_heuristic_fallback: bool = True,
        category: str = ''
    ) -> ArticleScore:
        """
        Score a single article.

        Args:
            article_id: UUID of the article
            title: Article title
            content: Article content
            use_heuristic_fallback: If True, use heuristics when LLM fails
            category: Article category for context-aware scoring

        Returns:
            ArticleScore with classification
        """
        logger.info(f"Scoring article {article_id}: {title[:50]}...")

        # Try AI analysis first
        ai_result = await self._analyze_with_llm(title, content, category=category)

        if ai_result:
            signals = ai_result
            scored_by = 'ai'
            logger.info(f"Article {article_id} scored by AI")
        elif use_heuristic_fallback:
            signals = _heuristic_score_article(title, content)
            scored_by = 'manual'  # 'manual' indicates heuristic fallback
            logger.info(f"Article {article_id} scored by heuristic fallback")
        else:
            raise RuntimeError("LLM unavailable and heuristic fallback disabled")

        # Calculate numeric scores and classification
        scores, total_score, classification = self._calculate_scores(signals)

        # Extract reasoning/justificativa from AI response
        reasoning = signals.get('justificativa', None)

        # Create ArticleScore object
        score = ArticleScore(
            article_id=article_id,
            sinal_inesperado=signals['sinal_inesperado'],
            sinal_impacto=signals['sinal_impacto'],
            sinal_busca_agora=signals['sinal_busca_agora'],
            sinal_conversa=signals['sinal_conversa'],
            score_inesperado=scores['score_inesperado'],
            score_impacto=scores['score_impacto'],
            score_busca_agora=scores['score_busca_agora'],
            score_conversa=scores['score_conversa'],
            total_score=total_score,
            classification=classification,
            scored_by=scored_by,
            reasoning=reasoning,
            scored_at=datetime.utcnow()
        )

        logger.info(
            f"Article {article_id} classified as {classification} "
            f"(total={total_score}, i={signals['sinal_inesperado']}, "
            f"p={signals['sinal_impacto']}, b={signals['sinal_busca_agora']}, c={signals['sinal_conversa']})"
        )

        return score

    def _create_default_score(self, article_id: UUID, title: str, content: str) -> ArticleScore:
        """
        Create a guaranteed default score using heuristic.
        This NEVER fails — if even heuristic breaks, returns a baseline C score.

        Args:
            article_id: UUID of the article
            title: Article title
            content: Article content

        Returns:
            ArticleScore with at minimum a C classification
        """
        try:
            signals = _heuristic_score_article(title, content or '')
            scores, total_score, classification = self._calculate_scores(signals)
            return ArticleScore(
                article_id=article_id,
                sinal_inesperado=signals['sinal_inesperado'],
                sinal_impacto=signals['sinal_impacto'],
                sinal_busca_agora=signals['sinal_busca_agora'],
                sinal_conversa=signals['sinal_conversa'],
                score_inesperado=scores['score_inesperado'],
                score_impacto=scores['score_impacto'],
                score_busca_agora=scores['score_busca_agora'],
                score_conversa=scores['score_conversa'],
                total_score=total_score,
                classification=classification,
                scored_by='manual',
                reasoning='Classificado por heuristica (fallback garantido)',
                scored_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Even heuristic scoring failed for {article_id}, using baseline C: {e}")
            return ArticleScore(
                article_id=article_id,
                sinal_inesperado='no',
                sinal_impacto='low',
                sinal_busca_agora='no',
                sinal_conversa='no',
                score_inesperado=0,
                score_impacto=0,
                score_busca_agora=0,
                score_conversa=0,
                total_score=0,
                classification='C',
                scored_by='manual',
                reasoning='Score padrao C (fallback de emergencia)',
                scored_at=datetime.utcnow()
            )

    async def score_articles_batch(
        self,
        articles: List[Dict[str, Any]],
        use_heuristic_fallback: bool = True,
        batch_delay: float = 0.3,
        max_concurrent: int = 5
    ) -> List[ArticleScore]:
        """
        Score multiple articles in batch. GUARANTEED to return a score for every article.

        Uses batch LLM calls (SCORING_BATCH_SIZE articles per call) to reduce API costs.
        Falls back to individual scoring for articles that fail batch parsing,
        and to heuristic scoring if LLM is entirely unavailable.

        Args:
            articles: List of dicts with 'id', 'title', 'content' keys
            use_heuristic_fallback: If True, use heuristics when LLM fails
            batch_delay: Delay between API calls in seconds (rate limiting)
            max_concurrent: Maximum number of concurrent scoring calls

        Returns:
            List of ArticleScore objects (same length as input)
        """
        logger.info(f"Scoring batch of {len(articles)} articles (batch_size={SCORING_BATCH_SIZE}, concurrency={max_concurrent})")

        # Build ordered result list (same length as input)
        results: List[Optional[ArticleScore]] = [None] * len(articles)

        # Chunk articles into batches of SCORING_BATCH_SIZE
        batches = []
        for i in range(0, len(articles), SCORING_BATCH_SIZE):
            batch = articles[i:i + SCORING_BATCH_SIZE]
            batches.append((i, batch))  # (start_index, batch_articles)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _score_batch(start_idx: int, batch: List[Dict[str, Any]]) -> List[Tuple[int, Optional[Dict[str, Any]]]]:
            """
            Score a batch via single LLM call. Returns list of (global_index, signals_or_None).
            """
            async with semaphore:
                batch_mapping = await self._analyze_batch_with_llm(batch)

                per_article_results = []
                for local_idx, article in enumerate(batch):
                    global_idx = start_idx + local_idx
                    signals = None

                    if batch_mapping and str(local_idx) in batch_mapping:
                        signals = batch_mapping[str(local_idx)]

                    per_article_results.append((global_idx, signals))

                return per_article_results

        # Run all batches concurrently
        batch_results = await asyncio.gather(
            *[_score_batch(start_idx, batch) for start_idx, batch in batches],
            return_exceptions=True
        )

        # Collect articles that need individual fallback scoring
        fallback_indices = []

        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Batch scoring call failed: {batch_result}")
                # Mark all articles in this failed batch for individual fallback
                # We need to figure out which indices — scan batches
                continue

            for global_idx, signals in batch_result:
                article = articles[global_idx]
                article_id = article['id'] if isinstance(article['id'], UUID) else UUID(str(article['id']))

                if signals:
                    # Batch succeeded for this article — build ArticleScore
                    try:
                        scores, total_score, classification = self._calculate_scores(signals)
                        results[global_idx] = ArticleScore(
                            article_id=article_id,
                            sinal_inesperado=signals['sinal_inesperado'],
                            sinal_impacto=signals['sinal_impacto'],
                            sinal_busca_agora=signals['sinal_busca_agora'],
                            sinal_conversa=signals['sinal_conversa'],
                            score_inesperado=scores['score_inesperado'],
                            score_impacto=scores['score_impacto'],
                            score_busca_agora=scores['score_busca_agora'],
                            score_conversa=scores['score_conversa'],
                            total_score=total_score,
                            classification=classification,
                            scored_by='ai',
                            reasoning=signals.get('justificativa'),
                            scored_at=datetime.utcnow()
                        )
                        logger.info(
                            f"Article {article_id} classified as {classification} "
                            f"(total={total_score}, batch)"
                        )
                    except Exception as e:
                        logger.error(f"Error building score from batch result for {article_id}: {e}")
                        fallback_indices.append(global_idx)
                else:
                    # Batch missed this article — needs individual fallback
                    fallback_indices.append(global_idx)

        # Also collect indices from entirely failed batches
        for batch_result, (start_idx, batch) in zip(batch_results, batches):
            if isinstance(batch_result, Exception):
                for local_idx in range(len(batch)):
                    global_idx = start_idx + local_idx
                    if results[global_idx] is None and global_idx not in fallback_indices:
                        fallback_indices.append(global_idx)

        # Individual fallback scoring for articles that failed batch parsing
        if fallback_indices:
            logger.info(f"Falling back to individual scoring for {len(fallback_indices)} articles")

            async def _score_one_fallback(global_idx: int) -> None:
                article = articles[global_idx]
                article_id = article['id'] if isinstance(article['id'], UUID) else UUID(str(article['id']))
                async with semaphore:
                    try:
                        score = await self.score_article(
                            article_id=article_id,
                            title=article['title'],
                            content=article.get('content', ''),
                            use_heuristic_fallback=use_heuristic_fallback,
                            category=article.get('category', '')
                        )
                        results[global_idx] = score
                    except Exception as e:
                        logger.error(f"Individual fallback failed for {article_id}: {e}, using guaranteed fallback")
                        results[global_idx] = self._create_default_score(
                            article_id, article.get('title', ''), article.get('content', '')
                        )

            await asyncio.gather(*[_score_one_fallback(idx) for idx in fallback_indices])

        # Final safety: fill any remaining None slots with heuristic fallback
        for i, result in enumerate(results):
            if result is None:
                article = articles[i]
                article_id = article['id'] if isinstance(article['id'], UUID) else UUID(str(article['id']))
                logger.warning(f"Article {article_id} still unscored after all attempts, using guaranteed fallback")
                results[i] = self._create_default_score(
                    article_id, article.get('title', ''), article.get('content', '')
                )

        scored_count = sum(1 for r in results if r is not None)
        logger.info(f"Batch scoring complete: {scored_count}/{len(articles)} scored")
        return list(results)

    async def process_pending_articles(
        self,
        limit: int = 20,
        use_heuristic_fallback: bool = True
    ) -> int:
        """
        Process articles that haven't been scored yet.

        Fetches articles from the database where has_score = 0,
        scores them, and saves the results.

        Args:
            limit: Maximum number of articles to process
            use_heuristic_fallback: If True, use heuristics when LLM fails

        Returns:
            Number of articles processed
        """
        logger.info(f"Processing up to {limit} pending articles for scoring")

        try:
            # Get pending articles from database
            # Note: This assumes database has get_articles_pending_score method
            # If not available, we query collected_articles where has_score = 0
            pending = await run_db(self._get_pending_articles, limit)

            if not pending:
                logger.info("No pending articles to score")
                return 0

            logger.info(f"Found {len(pending)} pending articles")

            # Score the batch
            scores = await self.score_articles_batch(
                pending,
                use_heuristic_fallback=use_heuristic_fallback,
                batch_delay=0.5
            )

            # Save scores to database
            saved = await run_db(self._save_scores, scores)

            logger.info(f"Processed {saved} articles for scoring")
            return saved

        except Exception as e:
            logger.error(f"Error processing pending articles: {e}")
            return 0

    def _get_pending_articles(self, limit: int) -> List[Dict[str, Any]]:
        """
        Get articles that haven't been scored yet.

        Args:
            limit: Maximum number of articles to fetch

        Returns:
            List of article dicts with id, title, content
        """
        # Query for articles without scores (includes category for context-aware scoring)
        # This uses raw SQL since the method might not exist in DatabaseService
        # 2-minute buffer avoids race condition with inline scoring during RSS collection
        query = """
            SELECT TOP %s a.id, a.title, a.content, a.category
            FROM collected_articles a
            LEFT JOIN article_scores s ON a.id = s.article_id
            WHERE s.id IS NULL
              AND a.collected_at < DATEADD(MINUTE, -2, GETUTCDATE())
            ORDER BY a.collected_at DESC
        """

        with self.db_service.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            return [
                {
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'category': row[3] or ''
                }
                for row in rows
            ]

    def _save_scores(self, scores: List[ArticleScore]) -> int:
        """
        Save article scores to database.

        Pre-serializes all parameters outside the DB connection, then executes
        all INSERTs and denormalization UPDATEs in a single transaction.

        Args:
            scores: List of ArticleScore objects to save

        Returns:
            Number of scores saved successfully
        """
        if not scores:
            return 0

        insert_query = """
            INSERT INTO article_scores
            (article_id, sinal_inesperado, sinal_impacto, sinal_busca_agora, sinal_conversa,
             score_inesperado, score_impacto, score_busca_agora, score_conversa,
             total_score, classification, scored_by, reasoning, scored_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        denorm_query = """UPDATE collected_articles
                          SET total_score = %s, classification = %s
                          WHERE id = %s"""

        # Pre-serialize all parameters outside the DB connection
        insert_params = []
        denorm_params = []
        for score in scores:
            aid = str(score.article_id)
            insert_params.append((
                aid,
                score.sinal_inesperado,
                score.sinal_impacto,
                score.sinal_busca_agora,
                score.sinal_conversa,
                score.score_inesperado,
                score.score_impacto,
                score.score_busca_agora,
                score.score_conversa,
                score.total_score,
                score.classification,
                score.scored_by,
                score.reasoning,
                score.scored_at
            ))
            denorm_params.append((score.total_score, score.classification, aid))

        saved = 0
        with self.db_service.get_connection() as conn:
            cursor = conn.cursor()

            # Batch INSERT scores
            for params in insert_params:
                try:
                    cursor.execute(insert_query, params)
                    saved += 1
                except Exception as e:
                    logger.error(f"Error saving score for article {params[0]}: {e}")
                    continue

            # Batch UPDATE denormalized columns
            for params in denorm_params:
                try:
                    cursor.execute(denorm_query, params)
                except Exception as e:
                    logger.warning(f"Failed to sync denormalized score for {params[2]}: {e}")

            conn.commit()

        return saved

    def score_article_sync(
        self,
        article_id: UUID,
        title: str,
        content: str,
        use_heuristic_fallback: bool = True,
        category: str = ''
    ) -> ArticleScore:
        """
        Synchronous wrapper for score_article.

        Use this in non-async contexts (like Azure Functions with sync triggers).

        Args:
            article_id: UUID of the article
            title: Article title
            content: Article content
            use_heuristic_fallback: If True, use heuristics when LLM fails
            category: Article category for context-aware scoring

        Returns:
            ArticleScore with classification
        """
        try:
            asyncio.get_running_loop()
            # Already in async context — run in thread with its own event loop
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(
                    asyncio.run,
                    self.score_article(article_id, title, content, use_heuristic_fallback, category=category)
                ).result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self.score_article(
                article_id, title, content, use_heuristic_fallback, category=category
            ))


# =============================================================================
# SINGLETON & UTILITIES
# =============================================================================

_scoring_service: Optional[ScoringService] = None


def get_scoring_service() -> ScoringService:
    """
    Get or create the scoring service singleton.

    Returns:
        ScoringService instance
    """
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service


def calculate_classification(total_score: int) -> str:
    """
    Calculate classification letter from total score.

    Args:
        total_score: Total score (0-100)

    Returns:
        Classification letter: 'A', 'B', or 'C'
    """
    if total_score >= THRESHOLD_A:
        return 'A'
    elif total_score >= THRESHOLD_B:
        return 'B'
    else:
        return 'C'


def get_score_breakdown(classification: str) -> Dict[str, Any]:
    """
    Get typical score ranges for a classification.

    Args:
        classification: 'A', 'B', or 'C'

    Returns:
        Dict with min/max scores and description
    """
    breakdowns = {
        'A': {
            'min': 75,
            'max': 100,
            'description': 'Alta prioridade - material de capa',
            'color': '#22c55e'  # green
        },
        'B': {
            'min': 35,
            'max': 74,
            'description': 'Media prioridade - bom conteudo',
            'color': '#eab308'  # yellow
        },
        'C': {
            'min': 0,
            'max': 34,
            'description': 'Baixa prioridade - conteudo complementar',
            'color': '#ef4444'  # red
        }
    }
    return breakdowns.get(classification, breakdowns['C'])
