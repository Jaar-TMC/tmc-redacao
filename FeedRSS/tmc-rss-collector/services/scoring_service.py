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

SCORING_SYSTEM_PROMPT = """Voce e um editor experiente de jornalismo brasileiro, especializado em avaliar a relevancia editorial de noticias de qualquer categoria (politica, economia, esportes, cultura, tecnologia, saude, etc).

Sua tarefa e analisar artigos e classificar seu potencial editorial usando 4 sinais de relevancia jornalistica.

## OS 4 SINAIS DE RELEVANCIA

### 1. INESPERADO (Fato surpreendente?)
Avalia se a noticia traz algo que o leitor NAO esperava ver hoje.
- **yes**: Fato completamente inesperado, surpreendente, fora do comum
  - Exemplos: Renuncia de ministro, falencia de banco, morte de celebridade, descoberta cientifica, golpe de estado
- **partial**: Fato parcialmente inesperado, com elementos de surpresa
  - Exemplos: Aumento de juros maior que esperado, resultado eleitoral apertado, declaracao polemica de autoridade
- **no**: Fato esperado, rotineiro, previsivel
  - Exemplos: Reuniao agendada, balanco trimestral, previsao do tempo, evento cultural anunciado

### 2. IMPACTO (Afeta a vida do leitor?)
Avalia o impacto pratico na vida do cidadao/leitor.
- **high**: Impacto alto e direto na vida das pessoas
  - Exemplos: Aumento de precos, mudanca em impostos, surto de doenca, corte de empregos, nova lei aprovada
- **medium**: Impacto moderado - relevante mas nao urgente
  - Exemplos: Mudanca em politica publica, lancamento de produto, resultado de pesquisa, acordo comercial
- **low**: Impacto baixo - informacao interessante mas sem consequencia pratica
  - Exemplos: Curiosidade historica, evento cultural local, estatistica sem contexto, entrevista protocolar

### 3. BUSCA AGORA (Leitor vai buscar?)
Avalia se o leitor vai ativamente buscar mais informacoes sobre este assunto.
- **yes**: Leitor vai procurar imediatamente - noticia urgente/trending
  - Exemplos: Acidente grave, escandalo politico, vazamento de dados, morte de famoso, resultado de eleicao
- **maybe**: Leitor pode se interessar em saber mais
  - Exemplos: Nova tecnologia, especulacao de mercado, boato sobre celebridade, tendencia de comportamento
- **no**: Leitor provavelmente nao vai buscar ativamente
  - Exemplos: Rotina administrativa, comunicado oficial padrao, evento comum, fato sem novidade

### 4. CONVERSA (Leitor vai comentar?)
Avalia se a noticia vai gerar discussao nas redes sociais, com amigos, familia.
- **yes**: Noticia para conversar - vai gerar debates e discussoes
  - Exemplos: Polemica politica, declaracao controversa, crime chocante, resultado surpreendente, tema divisivo
- **maybe**: Noticia que pode gerar algum comentario ou compartilhamento, mas nao debate acalorado
  - Exemplos: Conquista esportiva, mudanca em servico popular, curiosidade interessante, novidade tecnologica
- **no**: Noticia que nao gera conversa - leia e siga em frente
  - Exemplos: Informacao factual sem polemica, rotina, comunicado tecnico, estatistica neutra

## FORMATO DE RESPOSTA

Responda APENAS com JSON valido no seguinte formato:
```json
{
  "sinal_inesperado": "yes|partial|no",
  "sinal_impacto": "high|medium|low",
  "sinal_busca_agora": "yes|maybe|no",
  "sinal_conversa": "yes|maybe|no",
  "justificativa": "Breve explicacao das classificacoes (max 200 caracteres)"
}
```

IMPORTANTE:
- Use APENAS os valores especificados para cada sinal
- NAO inclua comentarios ou texto fora do JSON
- A justificativa deve ser concisa e em portugues
- Considere o CONTEXTO BRASILEIRO e a relevancia para o publico geral"""


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

        # Truncate content if too long (keep first 5000 chars for better context)
        truncated_content = content[:5000] if content and len(content) > 5000 else (content or '')

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

        Uses a semaphore to allow concurrent LLM calls (up to max_concurrent)
        instead of purely sequential processing with sleeps.

        Args:
            articles: List of dicts with 'id', 'title', 'content' keys
            use_heuristic_fallback: If True, use heuristics when LLM fails
            batch_delay: Delay between API calls in seconds (rate limiting)
            max_concurrent: Maximum number of concurrent scoring calls

        Returns:
            List of ArticleScore objects (same length as input)
        """
        logger.info(f"Scoring batch of {len(articles)} articles (concurrency={max_concurrent})")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _score_one(article: Dict[str, Any]) -> ArticleScore:
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
                    return score
                except Exception as e:
                    logger.error(f"Error scoring article {article.get('id')}: {e}, using guaranteed fallback")
                    return self._create_default_score(
                        article_id, article.get('title', ''), article.get('content', '')
                    )

        results = await asyncio.gather(*[_score_one(a) for a in articles])

        logger.info(f"Batch scoring complete: {len(results)}/{len(articles)} scored")
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
            pending = await self._get_pending_articles(limit)

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
            saved = await self._save_scores(scores)

            logger.info(f"Processed {saved} articles for scoring")
            return saved

        except Exception as e:
            logger.error(f"Error processing pending articles: {e}")
            return 0

    async def _get_pending_articles(self, limit: int) -> List[Dict[str, Any]]:
        """
        Get articles that haven't been scored yet.

        Args:
            limit: Maximum number of articles to fetch

        Returns:
            List of article dicts with id, title, content
        """
        # Query for articles without scores (includes category for context-aware scoring)
        # This uses raw SQL since the method might not exist in DatabaseService
        query = """
            SELECT TOP %s a.id, a.title, a.content, a.category
            FROM collected_articles a
            LEFT JOIN article_scores s ON a.id = s.article_id
            WHERE s.id IS NULL
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

    async def _save_scores(self, scores: List[ArticleScore]) -> int:
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
            loop = asyncio.get_running_loop()
            # We're in an async context, need to handle differently
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.score_article(
                article_id, title, content, use_heuristic_fallback, category=category
            ))
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
