"""
Generation API - Azure Functions endpoints for AI article generation.

Endpoints:
- POST /api/generate - Generate article from source text (4-phase anti-hallucination pipeline)
- POST /api/extract-topics - Extract topics from text
- POST /api/generate-tags - Generate tags for content
"""

import logging
import os
import json
import re
import time
import hashlib
import asyncio
import uuid
import threading

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import azure.functions as func
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# Prompt Injection Defense Patterns (3C)
_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(?:all\s+)?(?:previous\s+|acima\s+)?instru[cç][oõ]es', re.IGNORECASE),
    re.compile(r'voc[eê]\s+(?:e|é)\s+agora\s+(?:um|uma)', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\s+a', re.IGNORECASE),
    re.compile(r'<\s*/?system', re.IGNORECASE),
    re.compile(r'INSTRUC[AÃ]O\s*:', re.IGNORECASE),
    re.compile(r'Human\s*:', re.IGNORECASE),
    re.compile(r'Assistant\s*:', re.IGNORECASE),
    re.compile(r'\[INST\]', re.IGNORECASE),
    re.compile(r'<<SYS>>', re.IGNORECASE),
    re.compile(r'esquec[ea]\s+tudo', re.IGNORECASE),
    re.compile(r'sua\s+nova\s+tarefa', re.IGNORECASE),
    re.compile(r'responda\s+apenas\s+com', re.IGNORECASE),
    re.compile(r'nao\s+siga\s+as\s+regras', re.IGNORECASE),
    re.compile(r'<!--.*?-->', re.IGNORECASE | re.DOTALL),
    re.compile(r'nova\s+instru[cç][aã]o', re.IGNORECASE),
]

# Default image for Schema.org (1B)
_DEFAULT_IMAGE_URL = "https://tmc.com.br/og-default.jpg"

# Phase 1.1: Hard minimum source thresholds
MIN_SOURCE_CHARS = int(os.environ.get("MIN_SOURCE_CHARS", "300"))
NOTA_ONLY_THRESHOLD = int(os.environ.get("NOTA_ONLY_THRESHOLD", "500"))
SHORT_SOURCE_THRESHOLD = int(os.environ.get("SHORT_SOURCE_THRESHOLD", "800"))

# Phase 1.2: Production safety mode
PRODUCTION_SAFETY_MODE = os.environ.get("PRODUCTION_SAFETY_MODE", "true").lower() == "true"

# Phase 2.3: Temporal decontamination
DECONTAMINATION_ENABLED = os.environ.get("DECONTAMINATION_ENABLED", "true").lower() == "true"

# Quality Loop Configuration
QUALITY_LOOP_ENABLED = os.environ.get("QUALITY_LOOP_ENABLED", "true").lower() == "true"
QUALITY_LOOP_MAX_ATTEMPTS = int(os.environ.get("QUALITY_LOOP_MAX_ATTEMPTS", "3"))
QUALITY_LOOP_MAX_CLAIM_SEARCHES = int(os.environ.get("QUALITY_LOOP_MAX_CLAIM_SEARCHES", "5"))
QUALITY_LOOP_FLESCH_THRESHOLD = float(os.environ.get("QUALITY_LOOP_FLESCH_THRESHOLD", "55"))
QUALITY_LOOP_CONFIDENCE_THRESHOLD = float(os.environ.get("QUALITY_LOOP_CONFIDENCE_THRESHOLD", "0.50"))
QUALITY_LOOP_NOVEL_ENTITY_THRESHOLD = float(os.environ.get("QUALITY_LOOP_NOVEL_ENTITY_THRESHOLD", "0.75"))
QUALITY_LOOP_UNVERIFIABLE_THRESHOLD = int(os.environ.get("QUALITY_LOOP_UNVERIFIABLE_THRESHOLD", "3"))
QUALITY_LOOP_UNVERIFIABLE_RATIO = float(os.environ.get("QUALITY_LOOP_UNVERIFIABLE_RATIO", "0.40"))

# Enrichment cache (TTL 5 minutes) - avoids redundant Exa calls on regen
_enrichment_cache = {}
_enrichment_cache_lock = threading.Lock()
_ENRICHMENT_CACHE_TTL = 300  # seconds


def _get_cached_enrichment(cache_key: str):
    with _enrichment_cache_lock:
        entry = _enrichment_cache.get(cache_key)
        if entry and (time.time() - entry["ts"]) < _ENRICHMENT_CACHE_TTL:
            logger.info(f"Enrichment cache HIT for key={cache_key[:8]}...")
            return entry["data"]
        return None


def _set_cached_enrichment(cache_key: str, enrichment):
    with _enrichment_cache_lock:
        if len(_enrichment_cache) > 50:
            _enrichment_cache.clear()
        _enrichment_cache[cache_key] = {"data": enrichment, "ts": time.time()}


# Sensitive Topic Detection (2B)
_SENSITIVE_TOPIC_PATTERNS = {
    "menor_de_idade": [r"\bmenor(?:es)?\b", r"\bcriancas?\b", r"\badolescente\b", r"\b\d{1,2}\s*anos\s*de\s*idade\b"],
    "suicidio": [r"\bsuicid", r"\btirou\s+(?:a\s+)?(?:propria\s+)?vida\b"],
    "violencia_sexual": [r"\bestupro\b", r"\babuso\s+sexual\b", r"\bassedio\s+sexual\b"],
}

_SENSITIVE_TOPIC_INSTRUCTIONS = {
    "menor_de_idade": "ATENCAO: Materia envolve menor de idade. NAO divulgue nome, escola ou dados identificaveis. Use 'adolescente', 'crianca' ou 'menor'. Proteja a identidade conforme ECA.",
    "suicidio": "ATENCAO: Materia envolve suicidio. NAO descreva metodo. NAO romantize o ato. Inclua ao final: 'Se voce precisa de ajuda, ligue para o CVV: 188 (24h).'",
    "violencia_sexual": "ATENCAO: Materia envolve violencia sexual. NAO identifique a vitima. Use linguagem cuidadosa. Inclua ao final: 'Denuncias: Disque 180 (violencia contra mulher) ou Disque 100 (criancas).'",
}


def _detect_sensitive_topics(texto: str) -> list:
    """Detect sensitive topics in source text. Returns list of instruction strings."""
    instructions = []
    texto_lower = texto.lower()
    for topic, patterns in _SENSITIVE_TOPIC_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, texto_lower):
                instructions.append(_SENSITIVE_TOPIC_INSTRUCTIONS[topic])
                break
    return instructions


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for article generation."""
    texto_base: str = Field(..., min_length=20, max_length=50000, description="Source text content")
    persona: str = Field(default="imparcial", description="Writer persona (legacy)")
    tom: str = Field(default="formal", description="Writing tone")
    tipo_materia: str = Field(default="destaque", description="Article type")
    orientacao_lide: Optional[str] = Field(default=None, description="Lead guidance")
    citacoes: Optional[list] = Field(default=None, description="Quotes to include")
    contexto: Optional[str] = Field(default=None, description="Background context")
    creditos: Optional[str] = Field(default=None, description="Source credits")
    tags: Optional[list] = Field(default=None, description="Tags for SEO")
    # New category-based fields
    categoria: Optional[str] = Field(default=None, description="Editorial category (esportes|entretenimento|politica|economia|geral)")
    modo_opinativo: bool = Field(default=False, description="Enable opinion mode for categories that allow it")
    # Anti-hallucination pipeline options
    titulo_fonte: Optional[str] = Field(default=None, description="Source article title (for better enrichment search)")
    skip_verification: bool = Field(default=False, description="Skip post-generation verification")
    skip_enrichment: bool = Field(default=False, description="Skip pre-generation enrichment")
    # Schema.org / SEO
    image_url: Optional[str] = Field(default=None, description="Article image URL for Schema.org")
    author_name: Optional[str] = Field(default=None, description="Nome do jornalista responsavel")
    author_url: Optional[str] = Field(default=None, description="URL do perfil do jornalista")

    @field_validator('texto_base', 'orientacao_lide', 'contexto', 'creditos', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Strip HTML tags, control characters, and prompt injection patterns from text inputs."""
        if not isinstance(v, str):
            return v
        v = re.sub(r'<[^>]+>', '', v)  # Strip HTML tags
        v = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', v)  # Strip control chars
        for pattern in _INJECTION_PATTERNS:
            v = pattern.sub('[FILTERED]', v)
        return v


class ExtractTopicsRequest(BaseModel):
    """Request model for topic extraction."""
    texto: str = Field(..., min_length=50, description="Text to analyze")


class GenerateTagsRequest(BaseModel):
    """Request model for tag generation."""
    texto: str = Field(..., min_length=50, description="Content to analyze")
    max_tags: int = Field(default=10, ge=1, le=20, description="Maximum tags")


class ArticleInput(BaseModel):
    """Article input for merge topics."""
    id: str = Field(..., description="Article identifier")
    title: str = Field(..., description="Article title")
    content: str = Field(default="", description="Article content")
    preview: str = Field(default="", description="Article preview/summary")
    source: str = Field(..., description="Source name")


class MergeTopicsRequest(BaseModel):
    """Request model for merging topics from multiple articles."""
    articles: list = Field(..., min_length=1, max_length=3, description="Articles to merge (max 3)")


def create_error_response(message: str, status_code: int = 400) -> func.HttpResponse:
    """Create a standardized error response."""
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json"
    )


def create_success_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a standardized success response."""
    return func.HttpResponse(
        json.dumps(data, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json"
    )


# Safety Gate Models

@dataclass
class SafetyDecision:
    """Result of evaluating publish safety gates."""
    publish_blocked: bool = False
    block_reasons: list = field(default_factory=list)
    human_review_required: bool = False
    review_reasons: list = field(default_factory=list)


def evaluate_safety_gates(
    verification_data: dict,
    content_length: int,
    effective_source_len: int,
    prior_human_review: bool = False,
    prior_review_reasons: list = None,
) -> SafetyDecision:
    """
    Evaluate publish safety gates based on verification results.

    Pure function - no side effects. Determines whether an article should be
    blocked, sent for human review, or allowed to publish.

    Production mode (PRODUCTION_SAFETY_MODE=true) tightens thresholds:
    - Confidence floor: 0.50 (was 0.40)
    - 2+ fabricated → block (was: only block if confidence < 0.40)
    - 1 fabricated + confidence < 0.50 → block

    Args:
        verification_data: Verification result dict from fact_check_service
        content_length: Length of generated article in chars
        effective_source_len: Effective source length (enrichment-adjusted)
        prior_human_review: Whether human review was already flagged (e.g. verification failure)
        prior_review_reasons: Existing review reasons to carry forward

    Returns:
        SafetyDecision with publish_blocked, block_reasons, human_review_required, review_reasons
    """
    decision = SafetyDecision()

    risk_level = verification_data.get("risk_level", "high")
    confidence_score = verification_data.get("confidence_score", 0.0)
    fabricated_claims = verification_data.get("fabricated_claims", 0)
    unverifiable_claims = verification_data.get("unverifiable_claims", 0)
    total_claims = verification_data.get("total_claims", 0)
    expansion_ratio = verification_data.get("expansion_ratio", 0.0)

    # Carry over prior review flags
    if prior_human_review:
        decision.human_review_required = True
    if prior_review_reasons:
        decision.review_reasons = list(prior_review_reasons)

    # Load publication-readiness floors from config
    from services.config import get_config
    _cfg = get_config()
    publish_confidence_floor = _cfg.publish_confidence_floor  # 0.65
    publish_grounded_floor = _cfg.publish_grounded_floor      # 0.70
    publish_max_expansion = _cfg.publish_max_expansion          # 8.0

    # Production vs legacy confidence floor (for hard block)
    confidence_floor = 0.50 if PRODUCTION_SAFETY_MODE else 0.40

    # Compute grounded ratio (context claims count as partial grounded — they are
    # factually correct enrichment-sourced info, not hallucination)
    grounded_claims = verification_data.get("grounded_claims", 0)
    context_claims = verification_data.get("context_claims", 0)
    effective_grounded = grounded_claims + (context_claims * 0.8)
    grounded_ratio = effective_grounded / total_claims if total_claims > 0 else 0.0

    # --- HARD BLOCKS ---
    if risk_level == "critical":
        decision.publish_blocked = True
        decision.block_reasons.append("Nivel de risco CRITICO detectado")

    # Production: "high" risk is also a hard block (articles must be publication-ready)
    if PRODUCTION_SAFETY_MODE and risk_level == "high":
        decision.publish_blocked = True
        decision.block_reasons.append("Nivel de risco ALTO (bloqueado em modo producao)")

    if confidence_score < confidence_floor and verification_data.get("is_verified", False):
        decision.publish_blocked = True
        decision.block_reasons.append(f"Confianca muito baixa ({confidence_score:.0%})")

    # Publication-readiness floors (absolute minimums)
    if PRODUCTION_SAFETY_MODE and verification_data.get("is_verified", False):
        if confidence_score < publish_confidence_floor:
            if not decision.publish_blocked:
                decision.publish_blocked = True
                decision.block_reasons.append(
                    f"Confianca {confidence_score:.0%} abaixo do piso de publicacao ({publish_confidence_floor:.0%})"
                )
        if total_claims > 0 and grounded_ratio < publish_grounded_floor:
            if not any("grounded" in r.lower() for r in decision.block_reasons):
                decision.publish_blocked = True
                decision.block_reasons.append(
                    f"Apenas {grounded_ratio:.0%} claims fundamentados (minimo {publish_grounded_floor:.0%})"
                )

    if PRODUCTION_SAFETY_MODE:
        # Production: stricter fabrication gates
        if fabricated_claims >= 2:
            decision.publish_blocked = True
            decision.block_reasons.append(f"{fabricated_claims} afirmacoes fabricadas")
        elif fabricated_claims == 1 and confidence_score < 0.50:
            decision.publish_blocked = True
            decision.block_reasons.append(
                f"1 afirmacao fabricada com confianca insuficiente ({confidence_score:.0%})"
            )
    else:
        # Legacy mode
        if fabricated_claims >= 3:
            decision.publish_blocked = True
            decision.block_reasons.append(f"{fabricated_claims} afirmacoes fabricadas")
        elif fabricated_claims == 2 and confidence_score < 0.40:
            decision.publish_blocked = True
            decision.block_reasons.append(
                f"2 afirmacoes fabricadas com confianca baixa ({confidence_score:.0%})"
            )

    if total_claims > 0 and unverifiable_claims >= 3:
        if unverifiable_claims / total_claims > 0.40:
            decision.publish_blocked = True
            decision.block_reasons.append(
                f"{unverifiable_claims}/{total_claims} afirmacoes inverificaveis"
            )

    # Recalculate expansion ratio with effective source
    if effective_source_len > 0:
        effective_expansion = content_length / effective_source_len
    else:
        effective_expansion = expansion_ratio

    # Tighter expansion limit in production
    expansion_hard_limit = publish_max_expansion if PRODUCTION_SAFETY_MODE else 15
    if effective_expansion > expansion_hard_limit:
        decision.publish_blocked = True
        decision.block_reasons.append(f"Expansao extrema: {effective_expansion:.1f}x (limite: {expansion_hard_limit}x)")

    # --- SOFT GATES (human review) ---
    if PRODUCTION_SAFETY_MODE:
        # Production: 1 fabricated + confidence >= 0.50 → human review
        if fabricated_claims == 1 and confidence_score >= 0.50 and not decision.publish_blocked:
            decision.human_review_required = True
            decision.review_reasons.append("1 afirmacao possivelmente fabricada")
    else:
        if fabricated_claims == 2 and confidence_score >= 0.40 and not decision.publish_blocked:
            decision.human_review_required = True
            decision.review_reasons.append("2 afirmacoes possivelmente fabricadas")

    if total_claims > 0 and unverifiable_claims >= 2:
        if unverifiable_claims / total_claims > 0.30:
            decision.human_review_required = True
            decision.review_reasons.append(
                f"{unverifiable_claims} afirmacoes inverificaveis"
            )

    entity_comparison = verification_data.get("entity_comparison", {})
    novel_entities = entity_comparison.get("novel_entities", [])
    output_entities = entity_comparison.get("output_entities", [])
    if output_entities and len(novel_entities) >= 4:
        novel_ratio = len(novel_entities) / len(output_entities)
        # Skip novel entity gate when confidence is high — verification already
        # confirmed claims are well-grounded, so novel entities are likely
        # legitimate enrichment/context rather than hallucination
        if novel_ratio > 0.60 and confidence_score < 0.80:
            decision.human_review_required = True
            decision.review_reasons.append(
                f"{len(novel_entities)} entidades novas nao presentes na fonte"
            )

    if not PRODUCTION_SAFETY_MODE:
        # Legacy: softer expansion warnings
        if 10 < effective_expansion <= 15:
            decision.human_review_required = True
            decision.review_reasons.append(f"Expansao elevada: {effective_expansion:.1f}x")

        if risk_level == "high" and not decision.publish_blocked:
            decision.human_review_required = True
            decision.review_reasons.append("Nivel de risco ALTO")

    return decision


def evaluate_quality_criteria(
    verification_data: dict,
    readability_data: dict,
    categoria: str = "",
    tipo_materia: str = "",
) -> dict:
    """
    Evaluate all quality criteria for the Quality Loop.

    Pure function. Returns which criteria passed/failed with details.

    Args:
        verification_data: From fact_check_service verify_article
        readability_data: From compute_readability
        categoria: Article category (for adjusting thresholds)
        tipo_materia: Article type (for adjusting thresholds)

    Returns:
        dict with all_passed (bool), failures (list of criterion dicts)
    """
    failures = []

    # 1. Fabrication check
    fabricated = verification_data.get("fabricated_claims", 0)
    fabricated_claims_list = [
        c for c in verification_data.get("claims", [])
        if (isinstance(c, dict) and c.get("verdict") == "fabricated")
    ]
    if fabricated >= 1:
        failures.append({
            "criterion": "fabrication",
            "detail": f"{fabricated} afirmacao(oes) fabricada(s)",
            "claims": fabricated_claims_list,
        })

    # 2. Readability check (category-aware threshold)
    flesch = readability_data.get("flesch_score", 100)
    # Technical/analytical/opinion content has naturally lower readability
    flesch_threshold = QUALITY_LOOP_FLESCH_THRESHOLD
    if tipo_materia in ("analise", "editorial", "coluna") or categoria in ("economia", "politica"):
        flesch_threshold = max(45.0, QUALITY_LOOP_FLESCH_THRESHOLD - 10)
    if flesch < flesch_threshold:
        avg_sent = readability_data.get("avg_sentence_length", 0)
        failures.append({
            "criterion": "readability",
            "detail": f"Flesch {flesch} abaixo do minimo {flesch_threshold} (media frase: {avg_sent:.0f} palavras)",
            "instruction": (
                "URGENTE - LEGIBILIDADE MUITO BAIXA. Siga TODAS estas regras:\n"
                "1. QUEBRE toda frase com mais de 15 palavras em DUAS frases separadas\n"
                "2. SUBSTITUA palavras longas (4+ silabas): implementar→usar, significativo→grande, consequentemente→por isso, regulamentacao→regra, disponibilizar→oferecer, infraestrutura→estrutura\n"
                "3. REESCREVA toda frase em voz passiva para voz ativa: 'foi aprovado pelo Senado' → 'O Senado aprovou'\n"
                "4. ELIMINE oracoes subordinadas com 'que', 'o qual', 'sendo que' - faca frases separadas\n"
                "5. CADA paragrafo deve ter NO MAXIMO 2-3 frases curtas\n"
                "6. META: media de 12 palavras por frase, MAXIMO ABSOLUTO 18 palavras"
            ),
        })

    # 3. Confidence check
    confidence = verification_data.get("confidence_score", 1.0)
    is_verified = verification_data.get("is_verified", False)
    if is_verified and confidence < QUALITY_LOOP_CONFIDENCE_THRESHOLD:
        failures.append({
            "criterion": "confidence",
            "detail": f"Confianca {confidence:.0%} abaixo do minimo {QUALITY_LOOP_CONFIDENCE_THRESHOLD:.0%}",
            "instruction": (
                "Restrinja-se APENAS ao material-fonte. "
                "NAO adicione informacoes externas que nao possam ser verificadas."
            ),
        })

    # 4. Novel entities check
    entity_data = verification_data.get("entity_comparison", {})
    novel = entity_data.get("novel_entities", [])
    output_entities = entity_data.get("output_entities", [])
    if output_entities and len(novel) >= 5:
        ratio = len(novel) / len(output_entities)
        if ratio > QUALITY_LOOP_NOVEL_ENTITY_THRESHOLD:
            failures.append({
                "criterion": "novel_entities",
                "detail": f"{len(novel)}/{len(output_entities)} entidades novas ({ratio:.0%})",
                "instruction": (
                    "NAO introduza nomes de pessoas, lugares ou organizacoes "
                    "que nao estejam no texto-fonte original. "
                    f"Entidades problematicas: {', '.join(novel[:5])}"
                ),
            })

    # 5. Unverifiable claims check
    total_claims = verification_data.get("total_claims", 0)
    unverifiable = verification_data.get("unverifiable_claims", 0)
    unverifiable_claims_list = [
        c for c in verification_data.get("claims", [])
        if (isinstance(c, dict) and c.get("verdict") == "unverifiable")
    ]
    if total_claims > 0 and unverifiable >= QUALITY_LOOP_UNVERIFIABLE_THRESHOLD:
        unverifiable_ratio = unverifiable / total_claims
        if unverifiable_ratio > QUALITY_LOOP_UNVERIFIABLE_RATIO:
            failures.append({
                "criterion": "unverifiable",
                "detail": f"{unverifiable}/{total_claims} afirmacoes inverificaveis ({unverifiable_ratio:.0%})",
                "claims": unverifiable_claims_list,
                "instruction": (
                    "Remova ou reescreva afirmacoes que nao podem ser verificadas pelas fontes. "
                    "Prefira OMITIR do que afirmar sem fonte. "
                    "Se a informacao e importante, atribua a uma fonte especifica ('segundo [Fonte]')."
                ),
            })

    # 6. Bold count - NO LONGER in quality loop (post-processed by _enforce_bold_limit)
    # Bold enforcement is handled programmatically after generation since LLMs
    # cannot reliably count bold instances while generating text.

    return {
        "all_passed": len(failures) == 0,
        "failures": failures,
    }


def build_corrective_instructions(
    failures: list,
    exa_corrections: list = None,
) -> str:
    """
    Build a corrective instruction prompt from quality loop failures.

    Combines Exa-verified corrections with readability/confidence instructions
    into a single prompt section injected into regeneration.

    Args:
        failures: List of failure dicts from evaluate_quality_criteria
        exa_corrections: List of corrective instruction strings from Exa claim verification

    Returns:
        Formatted instruction string for LLM regeneration prompt
    """
    parts = ["\n\n## CORRECAO OBRIGATORIA\n"]
    parts.append("A versao anterior teve problemas que DEVEM ser corrigidos:\n")

    # Exa-verified corrections first (most specific)
    if exa_corrections:
        for correction in exa_corrections:
            parts.append(f"- {correction}")

    # General instructions from other criteria
    for failure in failures:
        instruction = failure.get("instruction")
        if instruction:
            parts.append(f"- {instruction}")

    parts.append(
        "\nReescreva o artigo corrigindo TODOS os problemas acima. "
        "NAO invente informacoes para substituir as removidas. "
        "Se nao ha informacao suficiente, escreva um texto MAIS CURTO."
    )

    return "\n".join(parts)


# Azure Function Handlers

async def generate_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate article using AI with 3-phase anti-hallucination pipeline.

    Phase 1: Enrichment (Exa web search for verified context)
    Phase 2: Generation (hardened prompts + dynamic length)
    Phase 3: Verification (claim extraction, entity comparison, quote checking)

    POST /api/generate
    Body: GenerateRequest JSON
    Returns: {titulo, linha_fina, conteudo, tags_sugeridas, verification?: {...}}
    """
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Generate article request received")
    pipeline_start = time.time()

    # Phase 4.6: Metrics instrumentation
    try:
        from services.metrics import Metrics
        Metrics.get().increment("generation.requests")
    except Exception:
        pass
    phase_timings = {}

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = GenerateRequest(**body)
        except Exception as e:
            logger.warning(f"Generate request validation error: {e}")
            return create_error_response("Erro de validacao nos dados enviados", 400)

        # Force safety in production mode
        if PRODUCTION_SAFETY_MODE:
            request_data.skip_verification = False
            request_data.skip_enrichment = False

        # Phase 1.1: Hard minimum source threshold
        source_char_count = len(request_data.texto_base.strip())
        nota_forced = False
        if source_char_count < MIN_SOURCE_CHARS:
            logger.warning(
                f"[{correlation_id}] Source too short: {source_char_count} chars "
                f"(minimum {MIN_SOURCE_CHARS})"
            )
            return create_error_response(
                f"Texto-base muito curto ({source_char_count} caracteres). "
                f"Minimo necessario: {MIN_SOURCE_CHARS} caracteres.",
                422
            )

        if source_char_count < NOTA_ONLY_THRESHOLD and request_data.tipo_materia != "nota":
            logger.info(
                f"[{correlation_id}] Source below nota threshold ({source_char_count} < "
                f"{NOTA_ONLY_THRESHOLD}), forcing tipo_materia=nota"
            )
            request_data.tipo_materia = "nota"
            nota_forced = True

        # Short source: force simpler article types to limit expansion
        if (source_char_count < SHORT_SOURCE_THRESHOLD
                and request_data.tipo_materia in ("destaque", "reportagem", "analise")):
            logger.info(
                f"[{correlation_id}] Short source ({source_char_count} < {SHORT_SOURCE_THRESHOLD}), "
                f"downgrading tipo_materia from {request_data.tipo_materia} to servico"
            )
            request_data.tipo_materia = "servico"

        # Import services (lazy to avoid startup issues)
        from services.llm_service import get_llm_service
        from services.fact_check_service import (
            get_fact_check_service, is_fact_check_enabled
        )

        try:
            llm = get_llm_service()
        except ValueError as e:
            logger.error(f"[{correlation_id}] LLM service not configured: {e}")
            return create_error_response(
                "AI service not configured. Please set AZURE_AI_API_KEY or ANTHROPIC_API_KEY.",
                503
            )

        # ==============================================================
        # Phase 1: Enrichment (non-blocking, try/except)
        # ==============================================================
        enrichment = None
        enrichment_context = None
        enrichment_key_facts = None
        verified_chars = len(request_data.texto_base.strip())

        if is_fact_check_enabled() and not request_data.skip_enrichment:
            enrichment_start = time.time()
            cache_input = f"{request_data.titulo_fonte or ''}:{(request_data.texto_base or '')[:500]}"
            enrichment_cache_key = hashlib.md5(cache_input.encode()).hexdigest()
            cached = _get_cached_enrichment(enrichment_cache_key)
            if cached:
                enrichment = cached
                if enrichment.success:
                    enrichment_context = enrichment.context_text
                    enrichment_key_facts = enrichment.key_facts if enrichment.key_facts else None
                    verified_chars = enrichment.verified_chars
                    logger.info(f"[{correlation_id}] Phase 1 from cache, verified_chars={verified_chars}")
            else:
                try:
                    fact_checker = get_fact_check_service()
                    enrichment = await fact_checker.enrich_context(
                        texto_base=request_data.texto_base,
                        titulo_fonte=request_data.titulo_fonte,
                        tags=request_data.tags,
                        correlation_id=correlation_id,
                    )
                    _set_cached_enrichment(enrichment_cache_key, enrichment)
                    if enrichment.success:
                        enrichment_context = enrichment.context_text
                        enrichment_key_facts = enrichment.key_facts if enrichment.key_facts else None
                        verified_chars = enrichment.verified_chars
                        logger.info(
                            f"[{correlation_id}] Phase 1 complete: {len(enrichment.key_facts or [])} facts, "
                            f"{len(enrichment.source_urls)} sources, "
                            f"verified_chars={verified_chars}, "
                            f"context_only={'yes' if not enrichment.key_facts else 'no'}"
                        )
                    else:
                        logger.info(
                            f"[{correlation_id}] Phase 1: no enrichment (urls={len(enrichment.source_urls)}, "
                            f"context_len={len(enrichment.context_text)})"
                        )
                except Exception as e:
                    logger.warning(f"[{correlation_id}] Phase 1 enrichment failed (non-blocking): {e}")
            phase_timings["enrichment_ms"] = int((time.time() - enrichment_start) * 1000)

        # Extract source URLs for hyperlink generation
        enrichment_source_urls = enrichment.source_urls if enrichment and getattr(enrichment, "source_urls", None) else []

        # ==============================================================
        # Sensitive Topic Detection (2B)
        # ==============================================================
        sensitive_instructions = _detect_sensitive_topics(request_data.texto_base)

        # ==============================================================
        # Phase 2: Generation (blocking - same core as before)
        # ==============================================================
        generation_start = time.time()
        try:
            result = await llm.generate_article(
                texto_base=request_data.texto_base,
                persona=request_data.persona,
                tom=request_data.tom,
                tipo_materia=request_data.tipo_materia,
                orientacao_lide=request_data.orientacao_lide,
                citacoes=request_data.citacoes,
                contexto=request_data.contexto,
                creditos=request_data.creditos,
                tags=request_data.tags,
                categoria=request_data.categoria,
                modo_opinativo=request_data.modo_opinativo,
                enrichment_context=enrichment_context,
                enrichment_key_facts=enrichment_key_facts,
                verified_chars=verified_chars,
                sensitive_instructions=sensitive_instructions,
                correlation_id=correlation_id,
                source_urls=enrichment_source_urls,
            )
        except Exception as e:
            logger.error(f"[{correlation_id}] Phase 2 generation failed: {e}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Falha na geracao do artigo",
                }, ensure_ascii=False),
                status_code=502,
                mimetype="application/json",
            )

        phase_timings["generation_ms"] = int((time.time() - generation_start) * 1000)
        logger.info(f"[{correlation_id}] Phase 2 complete: article generated")

        # Phase 1.1: Add nota_forced indicator to response
        if nota_forced:
            result["nota_forced"] = True
            result["nota_disclaimer"] = (
                f"Texto-base com apenas {source_char_count} caracteres. "
                f"Tipo forçado para 'nota' por segurança editorial."
            )

        # ==============================================================
        # Phase 2.3: Temporal Decontamination (post-generation, pre-verification)
        # ==============================================================
        if DECONTAMINATION_ENABLED and result.get("conteudo"):
            try:
                from services.fact_check_service import decontaminate_article
                enrichment_text = enrichment_context or ""
                cleaned, removals_count, removed = decontaminate_article(
                    result["conteudo"],
                    request_data.texto_base,
                    enrichment_text,
                )
                if removals_count > 0:
                    result["conteudo"] = cleaned
                    result["decontamination"] = {
                        "removals": removals_count,
                        "patterns_removed": removed,
                    }
                    logger.info(
                        f"[{correlation_id}] Decontamination: removed {removals_count} "
                        f"temporal patterns: {removed}"
                    )
            except Exception as e:
                logger.warning(f"[{correlation_id}] Decontamination failed (non-blocking): {e}")

        # ==============================================================
        # Sufficiency check: flag if material was insufficient for 2000+
        # ==============================================================
        source_len = len(request_data.texto_base.strip())
        content_len = len(result.get("conteudo", ""))
        similar_articles = []

        if content_len < 2000 and source_len < 1500:
            # Material was insufficient for a full article
            # Try to find similar articles in database for merge suggestion
            try:
                similar_articles = await _find_similar_articles(
                    request_data.tags,
                    request_data.titulo_fonte,
                    request_data.categoria,
                )
            except Exception as e:
                logger.warning(f"Similar articles search failed: {e}")

            result["material_sufficiency"] = {
                "sufficient": False,
                "source_chars": source_len,
                "verified_chars": verified_chars,
                "generated_chars": content_len,
                "recommendation": (
                    "Material insuficiente para materia completa (2000+ chars). "
                    "Sugerimos unir com materias similares para uma cobertura mais completa."
                ),
                "similar_articles": similar_articles,
            }
            logger.info(
                f"[{correlation_id}] Material insufficient: source={source_len}, "
                f"verified={verified_chars}, generated={content_len}, "
                f"similar_found={len(similar_articles)}"
            )
        else:
            result["material_sufficiency"] = {
                "sufficient": True,
                "source_chars": source_len,
                "verified_chars": verified_chars,
                "generated_chars": content_len,
            }

        # ==============================================================
        # Phase 3: Verification (non-blocking, try/except)
        # ==============================================================
        if is_fact_check_enabled() and not request_data.skip_verification:
            verification_start = time.time()
            try:
                fact_checker = get_fact_check_service()
                verification = await fact_checker.verify_article(
                    texto_base=request_data.texto_base,
                    generated_article=result.get("conteudo", ""),
                    citacoes=request_data.citacoes,
                    enrichment=enrichment,
                    correlation_id=correlation_id,
                )
                result["verification"] = verification.to_dict()
                logger.info(
                    f"[{correlation_id}] Phase 3 complete: confidence={verification.confidence_score:.3f}, "
                    f"risk={verification.risk_level}"
                )
            except Exception as e:
                # Phase 4.4: Verification failure as error (alert operations team)
                logger.error(
                    f"[{correlation_id}] Phase 3 verification FAILED (safety net offline): {e}",
                    exc_info=True
                )
                result["verification"] = {
                    "is_verified": False,
                    "risk_level": "high",
                    "requires_human_review": True,
                    "warnings": ["Verificacao automatica falhou"],
                    "review_reasons": ["Verification pipeline error"],
                    "pipeline_error": True,
                }
                # Pipeline error = block article (no unverified content in production)
                result["publish_blocked"] = True
                result["human_review_required"] = True
                result["review_reasons"] = [
                    "Verificacao automatica falhou - revisao manual necessaria"
                ]
            phase_timings["verification_ms"] = int((time.time() - verification_start) * 1000)

        # ==============================================================
        # Phase 4: Quality Loop (replaces Phase 2.1 auto-regeneration)
        # Evaluates quality criteria, uses Exa to verify/correct claims,
        # and regenerates until all criteria pass (max 3 attempts).
        # ==============================================================
        from services.fact_check_service import compute_readability, ExtractedClaim

        quality_loop_result = {
            "quality_loop_passed": True,
            "quality_loop_attempts": 0,
            "quality_loop_issues_fixed": [],
            "quality_loop_claims_corrected": 0,
            "quality_loop_claims_removed": 0,
            "quality_loop_claims_confirmed": 0,
            "quality_loop_unverifiable_verified": 0,
            "quality_loop_unverifiable_removed": 0,
        }

        # Compute initial readability
        readability = {}
        if result.get("conteudo"):
            try:
                readability = compute_readability(result["conteudo"])
                result["readability"] = readability
            except Exception as e:
                logger.warning(f"[{correlation_id}] Readability measurement failed: {e}")

        if (QUALITY_LOOP_ENABLED
                and is_fact_check_enabled()
                and not request_data.skip_verification
                and result.get("verification", {}).get("is_verified")):

            quality_loop_start = time.time()
            verification_data = result.get("verification", {})
            quality_eval = evaluate_quality_criteria(
                verification_data, readability,
                categoria=request_data.categoria, tipo_materia=request_data.tipo_materia,
            )
            best_result = dict(result)
            best_failures_count = len(quality_eval["failures"])

            attempt = 0
            while not quality_eval["all_passed"] and attempt < QUALITY_LOOP_MAX_ATTEMPTS:
                attempt += 1
                quality_loop_result["quality_loop_attempts"] = attempt
                logger.info(
                    f"[{correlation_id}] Quality Loop attempt {attempt}/{QUALITY_LOOP_MAX_ATTEMPTS}: "
                    f"failures={[f['criterion'] for f in quality_eval['failures']]}"
                )

                # Step 1: Exa claim verification for fabricated claims
                exa_corrections = []
                fabrication_failure = next(
                    (f for f in quality_eval["failures"] if f["criterion"] == "fabrication"),
                    None,
                )
                if fabrication_failure:
                    try:
                        fact_checker = get_fact_check_service()
                        claims_to_check = fabrication_failure.get("claims", [])[:QUALITY_LOOP_MAX_CLAIM_SEARCHES]

                        for claim_dict in claims_to_check:
                            claim_obj = ExtractedClaim(
                                text=claim_dict.get("text", ""),
                                verdict=claim_dict.get("verdict", "fabricated"),
                            )
                            exa_result = await fact_checker.verify_claim_with_exa(claim_obj)

                            if exa_result["verdict"] == "confirmed":
                                quality_loop_result["quality_loop_claims_confirmed"] += 1
                                logger.info(f"[{correlation_id}] Claim CONFIRMED by Exa: {claim_obj.text[:60]}")
                            elif exa_result["verdict"] == "contradicted":
                                quality_loop_result["quality_loop_claims_corrected"] += 1
                                if exa_result.get("corrective_instruction"):
                                    exa_corrections.append(exa_result["corrective_instruction"])
                                logger.info(f"[{correlation_id}] Claim CONTRADICTED by Exa: {claim_obj.text[:60]}")
                            else:  # inconclusive
                                quality_loop_result["quality_loop_claims_removed"] += 1
                                if exa_result.get("corrective_instruction"):
                                    exa_corrections.append(exa_result["corrective_instruction"])
                                logger.info(f"[{correlation_id}] Claim INCONCLUSIVE: {claim_obj.text[:60]}")
                    except Exception as e:
                        logger.warning(f"[{correlation_id}] Exa claim verification failed: {e}")

                # Step 1b: Exa verification for unverifiable claims
                unverifiable_failure = next(
                    (f for f in quality_eval["failures"] if f["criterion"] == "unverifiable"),
                    None,
                )
                unverifiable_corrections = []
                if unverifiable_failure:
                    try:
                        fact_checker = get_fact_check_service()
                        unverifiable_to_check = unverifiable_failure.get("claims", [])[:QUALITY_LOOP_MAX_CLAIM_SEARCHES]

                        for claim_dict in unverifiable_to_check:
                            claim_obj = ExtractedClaim(
                                text=claim_dict.get("text", ""),
                                verdict=claim_dict.get("verdict", "unverifiable"),
                            )
                            exa_result = await fact_checker.verify_claim_with_exa(claim_obj)

                            if exa_result["verdict"] == "confirmed":
                                quality_loop_result["quality_loop_unverifiable_verified"] += 1
                                # Claim is actually verifiable - tell LLM to add attribution
                                evidence = exa_result.get("evidence", "")
                                unverifiable_corrections.append(
                                    f'ATRIBUIR: "{claim_obj.text}" foi confirmada por fontes externas. '
                                    f'Adicione atribuicao explicita (ex: "segundo fontes"). Evidencia: {evidence[:200]}'
                                )
                                logger.info(f"[{correlation_id}] Unverifiable CONFIRMED by Exa: {claim_obj.text[:60]}")
                            elif exa_result["verdict"] == "contradicted":
                                quality_loop_result["quality_loop_unverifiable_removed"] += 1
                                if exa_result.get("corrective_instruction"):
                                    unverifiable_corrections.append(exa_result["corrective_instruction"])
                                logger.info(f"[{correlation_id}] Unverifiable CONTRADICTED by Exa: {claim_obj.text[:60]}")
                            else:  # inconclusive
                                quality_loop_result["quality_loop_unverifiable_removed"] += 1
                                unverifiable_corrections.append(
                                    f'REMOVER: "{claim_obj.text}" nao pode ser verificada por nenhuma fonte. '
                                    f'Omita esta informacao ou reescreva usando APENAS dados do texto-base.'
                                )
                                logger.info(f"[{correlation_id}] Unverifiable INCONCLUSIVE: {claim_obj.text[:60]}")
                    except Exception as e:
                        logger.warning(f"[{correlation_id}] Exa unverifiable claim verification failed: {e}")

                # Combine all Exa corrections
                all_exa_corrections = exa_corrections + unverifiable_corrections

                # If ALL problematic claims were confirmed by Exa and no other failures remain, skip regeneration
                non_claim_failures = [
                    f for f in quality_eval["failures"]
                    if f["criterion"] not in ("fabrication", "unverifiable")
                ]
                all_confirmed = (
                    not exa_corrections  # no fabricated corrections needed
                    and not any(  # no unverifiable removals needed
                        c.startswith('REMOVER:') or c.startswith('CORRIGIR:')
                        for c in unverifiable_corrections
                    )
                    and (quality_loop_result["quality_loop_claims_confirmed"] > 0
                         or quality_loop_result["quality_loop_unverifiable_verified"] > 0)
                    and not non_claim_failures
                )
                if all_confirmed:
                    logger.info(f"[{correlation_id}] All claims confirmed by Exa, skipping regeneration")
                    quality_eval = {"all_passed": True, "failures": []}
                    break

                # Step 2: Build corrective instructions
                corrective_prompt = build_corrective_instructions(
                    quality_eval["failures"], all_exa_corrections
                )

                # Step 3: Regenerate with corrective instructions
                regen_sensitive = list(sensitive_instructions or [])
                regen_sensitive.append(corrective_prompt)

                try:
                    regen_result = await llm.generate_article(
                        texto_base=request_data.texto_base,
                        persona=request_data.persona,
                        tom=request_data.tom,
                        tipo_materia=request_data.tipo_materia,
                        orientacao_lide=request_data.orientacao_lide,
                        citacoes=request_data.citacoes,
                        contexto=request_data.contexto,
                        creditos=request_data.creditos,
                        tags=request_data.tags,
                        categoria=request_data.categoria,
                        modo_opinativo=request_data.modo_opinativo,
                        enrichment_context=enrichment_context,
                        enrichment_key_facts=enrichment_key_facts,
                        verified_chars=verified_chars,
                        sensitive_instructions=regen_sensitive,
                        correlation_id=correlation_id,
                    )

                    # Step 4: Re-verify
                    fact_checker = get_fact_check_service()
                    regen_verification = await fact_checker.verify_article(
                        texto_base=request_data.texto_base,
                        generated_article=regen_result.get("conteudo", ""),
                        citacoes=request_data.citacoes,
                        enrichment=enrichment,
                        correlation_id=correlation_id,
                    )
                    regen_result["verification"] = regen_verification.to_dict()

                    # Compute readability for regenerated version
                    regen_readability = compute_readability(regen_result.get("conteudo", ""))
                    regen_result["readability"] = regen_readability

                    # Re-evaluate quality
                    regen_eval = evaluate_quality_criteria(
                        regen_result["verification"], regen_readability,
                        categoria=request_data.categoria, tipo_materia=request_data.tipo_materia,
                    )

                    # Accept if better (fewer failures) or all passed
                    if regen_eval["all_passed"] or len(regen_eval["failures"]) < best_failures_count:
                        # Track which issues were fixed
                        old_criteria = {f["criterion"] for f in quality_eval["failures"]}
                        new_criteria = {f["criterion"] for f in regen_eval["failures"]}
                        fixed = old_criteria - new_criteria
                        quality_loop_result["quality_loop_issues_fixed"].extend(list(fixed))

                        result = regen_result
                        readability = regen_readability
                        quality_eval = regen_eval
                        best_result = dict(result)
                        best_failures_count = len(regen_eval["failures"])
                        logger.info(
                            f"[{correlation_id}] Quality Loop attempt {attempt} improved: "
                            f"fixed={fixed}, remaining={new_criteria}"
                        )
                    else:
                        logger.info(
                            f"[{correlation_id}] Quality Loop attempt {attempt} did not improve "
                            f"({len(regen_eval['failures'])} >= {best_failures_count}), keeping best"
                        )

                except Exception as e:
                    logger.warning(f"[{correlation_id}] Quality Loop attempt {attempt} failed: {e}")
                    break

            quality_loop_result["quality_loop_passed"] = quality_eval["all_passed"]

            # If loop didn't pass after all attempts, block publication
            if not quality_loop_result["quality_loop_passed"]:
                result = best_result
                remaining = [f['criterion'] for f in quality_eval['failures']]
                logger.warning(
                    f"[{correlation_id}] Quality Loop exhausted {attempt} attempts, "
                    f"using best version. Remaining: {remaining}"
                )
                # Block if critical quality criteria still fail
                critical_failures = [c for c in remaining if c in ("fabrication", "confidence", "unverifiable")]
                if critical_failures:
                    result["publish_blocked"] = True
                    result["block_reason"] = (
                        f"Quality Loop falhou apos {attempt} tentativas: {', '.join(critical_failures)}"
                    )
                    logger.warning(
                        f"[{correlation_id}] PUBLISH BLOCKED by Quality Loop: {critical_failures}"
                    )
                else:
                    # Non-critical failures (readability, novel_entities) → flag for review
                    result["human_review_required"] = True
                    result.setdefault("review_reasons", [])
                    result["review_reasons"].append(
                        f"Quality Loop nao passou: {', '.join(remaining)}"
                    )

            result["quality_loop"] = quality_loop_result
            result["regenerated"] = quality_loop_result["quality_loop_attempts"] > 0
            phase_timings["quality_loop_ms"] = int((time.time() - quality_loop_start) * 1000)
            logger.info(
                f"[{correlation_id}] Quality Loop complete: passed={quality_loop_result['quality_loop_passed']}, "
                f"attempts={quality_loop_result['quality_loop_attempts']}, "
                f"fixed={quality_loop_result['quality_loop_issues_fixed']}"
            )
        else:
            # Quality loop not applicable (disabled, no verification, etc.)
            result["quality_loop"] = quality_loop_result

        # Ensure readability human review flag is set (even if quality loop didn't run)
        if readability and readability.get("flesch_score", 100) < 42:
            if "human_review_required" not in result:
                result["human_review_required"] = False
            if "review_reasons" not in result:
                result["review_reasons"] = []
            result["human_review_required"] = True
            result["review_reasons"] = list(result.get("review_reasons", []))
            if not any("Legibilidade" in r for r in result["review_reasons"]):
                result["review_reasons"].append(
                    f"Legibilidade baixa (Flesch {readability['flesch_score']})"
                )

        # ==============================================================
        # Phase 3.5: Content Length Enforcement (type-aware)
        # ==============================================================
        if result.get("conteudo"):
            from services.llm_service import get_dynamic_length_requirement
            min_chars, _, _ = get_dynamic_length_requirement(
                request_data.texto_base,
                verified_chars=verified_chars,
                tipo_materia=request_data.tipo_materia,
            )
            actual_len = len(result["conteudo"])
            if actual_len < int(min_chars * 0.70):
                if "seo_quality" not in result:
                    result["seo_quality"] = {}
                result["seo_quality"]["length_warning"] = (
                    f"Artigo tipo '{request_data.tipo_materia}' com {actual_len} caracteres, "
                    f"abaixo de 70% do minimo esperado ({min_chars} chars). Considere expandir."
                )

        # ==============================================================
        # Publish safety gate: block critical-risk articles
        # ==============================================================
        # Use RAW source length for expansion ratio - enrichment should NOT hide
        # the fact that the original source was too short. This prevents a 63-char
        # source from being inflated to 5000+ verified_chars and passing expansion gates.
        # The enrichment provides CONTEXT, not SOURCE material.
        effective_source_len = source_len  # Always use raw source length
        # Only use enrichment-adjusted length if it's < 2x the raw source
        # (indicates enrichment confirmed existing content, not fabricated new context)
        if enrichment and hasattr(enrichment, 'verified_chars') and enrichment.verified_chars > 0:
            if enrichment.verified_chars <= source_len * 2:
                effective_source_len = enrichment.verified_chars
        elif enrichment and isinstance(enrichment, dict) and enrichment.get('verified_chars', 0) > 0:
            if enrichment['verified_chars'] <= source_len * 2:
                effective_source_len = enrichment['verified_chars']

        safety = evaluate_safety_gates(
            verification_data=result.get("verification", {}),
            content_length=len(result.get("conteudo", "")),
            effective_source_len=effective_source_len,
            prior_human_review=result.get("human_review_required", False),
            prior_review_reasons=list(result.get("review_reasons", [])),
        )
        result["publish_blocked"] = safety.publish_blocked
        result["block_reason"] = "; ".join(safety.block_reasons) if safety.publish_blocked else ""
        result["human_review_required"] = safety.human_review_required
        result["review_reasons"] = safety.review_reasons
        if safety.publish_blocked:
            logger.warning(f"[{correlation_id}] PUBLISH BLOCKED: {result['block_reason']}")
        elif safety.human_review_required:
            logger.info(f"[{correlation_id}] HUMAN REVIEW: {'; '.join(safety.review_reasons)}")

        # ==============================================================
        # Entity-Informed Tags (enrich tags from verified entities)
        # ==============================================================
        if result.get("verification", {}).get("entity_comparison"):
            entity_data = result["verification"]["entity_comparison"]
            entity_tags = _extract_entity_tags(
                entity_data.get("source_entities", []),
                entity_data.get("common_entities", []),
                result.get("tags_sugeridas", []),
            )
            result["tags_sugeridas"] = _merge_tags(
                result.get("tags_sugeridas", []), entity_tags
            )

        # ==============================================================
        # Schema.org / JSON-LD structured data
        # ==============================================================
        entity_data = result.get("verification", {}).get("entity_comparison")
        schema_org_data = _build_schema_org(
            titulo=result.get("titulo", ""),
            linha_fina=result.get("linha_fina", ""),
            tags=result.get("tags_sugeridas", []),
            conteudo=result.get("conteudo", ""),
            categoria=request_data.categoria,
            image_url=request_data.image_url if hasattr(request_data, 'image_url') else None,
            correlation_id=correlation_id,
            entities=entity_data.get("common_entities", []) if entity_data else None,
            author_name=request_data.author_name,
            author_url=request_data.author_url,
        )
        result["structured_data"] = schema_org_data  # backward compat
        result["schema_org"] = schema_org_data        # canonical key

        # ==============================================================
        # Phase 4.7: Graceful Degradation When Exa Down
        # ==============================================================
        if enrichment and not enrichment.success:
            result["enrichment_degraded"] = True
            if "verification" in result and isinstance(result["verification"], dict):
                result["verification"]["enrichment_degraded"] = True
                warnings = result["verification"].get("warnings", [])
                warnings.append(
                    "Enrichment indisponivel: verificacao baseada apenas no texto-base"
                )
                result["verification"]["warnings"] = warnings

        # ClaimReview Schema (1C)
        claim_review = _build_claim_review(
            verification_data=result.get("verification"),
            article_url=f"https://tmc.com.br/artigo/{correlation_id}" if correlation_id else "",
        )
        if claim_review:
            result["claim_review"] = claim_review

        # AI Disclosure (1D)
        result["ai_disclosure"] = {
            "ai_assisted": True,
            "disclosure_text": (
                "Esta materia foi gerada com auxilio de inteligencia artificial e revisada pela equipe editorial TMC."
                if result.get("human_review_required")
                else "Esta materia foi gerada com auxilio de inteligencia artificial."
            ),
        }

        # Sensitive topics (2B)
        if sensitive_instructions:
            result["sensitive_topics_detected"] = True
            result["sensitive_instructions"] = sensitive_instructions

        # ==============================================================
        # Phase 5.1: Publication Status
        # ==============================================================
        if result.get("publish_blocked"):
            result["publication_status"] = "blocked"
        elif result.get("human_review_required"):
            result["publication_status"] = "draft_review"
        elif result.get("verification", {}).get("is_verified"):
            result["publication_status"] = "ready_for_review"
        else:
            result["publication_status"] = "draft"
        result["can_auto_publish"] = False  # Conservative default

        # Add enrichment source URLs to result for frontend hyperlink display
        result["source_urls"] = enrichment_source_urls

        # Add correlation_id to result
        result["correlation_id"] = correlation_id

        total_ms = int((time.time() - pipeline_start) * 1000)
        phase_timings["total_ms"] = total_ms
        result["phase_timings"] = phase_timings
        logger.info(f"[{correlation_id}] Full pipeline complete in {total_ms}ms")

        # ==============================================================
        # Phase 5.2: Quality Summary Logging
        # ==============================================================
        try:
            v = result.get("verification", {})
            r = result.get("readability", {})
            quality_summary = {
                "correlation_id": correlation_id,
                "categoria": request_data.categoria,
                "tipo_materia": request_data.tipo_materia,
                "source_chars": source_len,
                "verified_chars": verified_chars,
                "generated_chars": content_len,
                "confidence_score": v.get("confidence_score", 0),
                "risk_level": v.get("risk_level", "unknown"),
                "fabricated_claims": v.get("fabricated_claims", 0),
                "total_claims": v.get("total_claims", 0),
                "flesch_score": r.get("flesch_score", 0),
                "publish_blocked": result.get("publish_blocked", False),
                "human_review": result.get("human_review_required", False),
                "publication_status": result.get("publication_status"),
                "enrichment_success": bool(enrichment and enrichment.success),
                "regenerated": result.get("regenerated", False),
                "total_ms": total_ms,
            }
            logger.info(f"[QUALITY_SUMMARY] {json.dumps(quality_summary)}")
        except Exception:
            pass  # Quality logging should never break the pipeline

        # Phase 4.6: Record pipeline metrics
        try:
            from services.metrics import Metrics
            m = Metrics.get()
            m.observe("generation.total_ms", total_ms)
            if result.get("publish_blocked"):
                m.increment("generation.blocked")
            if result.get("verification", {}).get("pipeline_error"):
                m.increment("verification.failures")
        except Exception:
            pass

        # ==============================================================
        # Audit Trail (awaited with timeout, non-blocking on failure)
        # ==============================================================
        try:
            audit_data = _build_audit_data(
                request_data=request_data,
                result=result,
                enrichment=enrichment,
                phase_timings=phase_timings,
                total_ms=total_ms,
            )
            try:
                await asyncio.wait_for(_persist_audit(audit_data), timeout=2.0)
            except asyncio.TimeoutError:
                # Phase 4.3: Audit failures as errors (surface in Application Insights)
                logger.error(f"[{correlation_id}] Audit persist timed out after 2s")
            except Exception as e:
                logger.error(f"[{correlation_id}] Audit persist failed: {e}", exc_info=True)
        except Exception as e:
            logger.warning(f"[{correlation_id}] Audit trail prep failed (non-blocking): {e}")

        # Ensure titulo_curto is present in response
        if "titulo_curto" not in result:
            result["titulo_curto"] = result.get("titulo_curto", "")

        # Ensure resumo (bullet points) is present in response
        if "resumo" not in result:
            result["resumo"] = []

        return create_success_response(result)

    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        return create_error_response("Erro no servico de IA", 503)
    except ValueError as e:
        logger.error(f"Invalid response from AI: {e}")
        return create_error_response("Resposta invalida do servico de IA", 500)
    except Exception as e:
        logger.exception(f"Unexpected error in generate_article: {e}")
        return create_error_response("Internal server error", 500)


async def extract_topics_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Extract topics from text using AI.

    POST /api/extract-topics
    Body: {texto: string}
    Returns: {topics: [{type, content}, ...]}
    """
    logger.info("Extract topics request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = ExtractTopicsRequest(**body)
        except Exception as e:
            logger.warning(f"Extract topics validation error: {e}")
            return create_error_response("Erro de validacao nos dados enviados", 400)

        # Import LLM service
        from services.llm_service import get_llm_service

        try:
            llm = get_llm_service()
        except ValueError as e:
            return create_error_response(
                "AI service not configured. Please set AZURE_AI_API_KEY or ANTHROPIC_API_KEY.",
                503
            )

        # Extract topics
        topics = await llm.extract_topics(request_data.texto)

        return create_success_response({"topics": topics})

    except Exception as e:
        logger.exception(f"Error in extract_topics: {e}")
        return create_error_response("Internal server error", 500)


async def generate_tags_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate tags for content using AI.

    POST /api/generate-tags
    Body: {texto: string, max_tags?: number}
    Returns: {tags: [string, ...]}
    """
    logger.info("Generate tags request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = GenerateTagsRequest(**body)
        except Exception as e:
            logger.warning(f"Generate tags validation error: {e}")
            return create_error_response("Erro de validacao nos dados enviados", 400)

        # Import LLM service
        from services.llm_service import get_llm_service

        try:
            llm = get_llm_service()
        except ValueError as e:
            return create_error_response(
                "AI service not configured. Please set AZURE_AI_API_KEY or ANTHROPIC_API_KEY.",
                503
            )

        # Generate tags
        tags = await llm.generate_tags(request_data.texto, request_data.max_tags)

        return create_success_response({"tags": tags})

    except Exception as e:
        logger.exception(f"Error in generate_tags: {e}")
        return create_error_response("Internal server error", 500)


def _extract_entity_tags(
    source_entities: list,
    common_entities: list,
    existing_tags: list,
) -> list:
    """
    Extract tags from verified entities (common between source and output).

    Prioritizes common_entities (verified in both source AND output).
    Normalizes, filters numbers/percentages, deduplicates vs existing.

    Returns up to 8 entity-derived tags.
    """
    existing_lower = {t.lower().strip() for t in existing_tags}
    entity_tags = []
    seen = set()

    # Prioritize common entities (verified)
    for entity in common_entities:
        tag = entity.strip()
        tag_lower = tag.lower()
        # Skip numbers, percentages, monetary values, dates
        if re.match(r'^[\d.,\s%R$]+$', tag):
            continue
        if re.match(r'^\d', tag):
            continue
        if len(tag) < 3:
            continue
        if tag_lower in existing_lower or tag_lower in seen:
            continue
        seen.add(tag_lower)
        entity_tags.append(tag)

    # Then source entities not yet included
    for entity in source_entities:
        if len(entity_tags) >= 8:
            break
        tag = entity.strip()
        tag_lower = tag.lower()
        if re.match(r'^[\d.,\s%R$]+$', tag):
            continue
        if re.match(r'^\d', tag):
            continue
        if len(tag) < 3:
            continue
        if tag_lower in existing_lower or tag_lower in seen:
            continue
        seen.add(tag_lower)
        entity_tags.append(tag)

    return entity_tags[:8]


def _merge_tags(existing: list, entity_tags: list, max_tags: int = 12) -> list:
    """
    Merge existing tags with entity-derived tags.

    Preserves order (existing first), deduplicates, respects max.
    """
    merged = list(existing)
    existing_lower = {t.lower().strip() for t in merged}

    for tag in entity_tags:
        if len(merged) >= max_tags:
            break
        if tag.lower().strip() not in existing_lower:
            merged.append(tag)
            existing_lower.add(tag.lower().strip())

    return merged


def _build_schema_org(
    titulo: str,
    linha_fina: str,
    tags: list = None,
    conteudo: str = "",
    categoria: str = None,
    image_url: str = None,
    correlation_id: str = "",
    entities: list = None,
    author_name: str = None,
    author_url: str = None,
) -> dict:
    """
    Build Schema.org/JSON-LD NewsArticle structured data.

    Frontend/WP plugin can inject this into <head> when publishing.
    The @id in mainEntityOfPage uses correlation_id when available,
    otherwise left empty for WP plugin to fill at publish time.

    Includes Google News 2026 recommended fields:
    - dateCreated, isAccessibleForFree, creativeWorkStatus
    - publisher.url, publisher.sameAs, publisher.logo, publishingPrinciples
    - speakable (SpeakableSpecification)
    - image always present (fallback to default)
    - about/mentions from verified entities
    - author as [Person, SoftwareApplication] with worksFor Organization
    - copyrightHolder, copyrightYear, isPartOf
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Author with fallback (1A)
    author_obj = {
        "@type": "Person",
        "name": author_name or "Redacao TMC",
        "jobTitle": "Jornalista",
        "url": author_url or "https://tmc.com.br/equipe",
        "worksFor": {
            "@type": "Organization",
            "name": "TMC",
            "url": "https://tmc.com.br",
        },
    }
    if author_name:
        author_obj["sameAs"] = []

    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": titulo[:110] if titulo else "",
        "description": linha_fina[:300] if linha_fina else "",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://tmc.com.br/artigo/{correlation_id}" if correlation_id else "",
        },
        "datePublished": now_iso,
        "dateModified": now_iso,
        "dateCreated": now_iso,
        "isAccessibleForFree": True,
        "creativeWorkStatus": "Assistido por IA",
        # Author: Person + SoftwareApplication co-author (1D)
        "author": [
            author_obj,
            {
                "@type": "SoftwareApplication",
                "name": "TMC AI",
                "description": "Assistente de redacao com inteligencia artificial",
            },
        ],
        "publisher": {
            "@type": "Organization",
            "name": "TMC",
            "url": "https://tmc.com.br",
            "sameAs": [
                "https://twitter.com/tmcnoticias",
                "https://instagram.com/tmcnoticias",
            ],
            "logo": {
                "@type": "ImageObject",
                "url": "https://tmc.com.br/logo.png",
                "width": 600,
                "height": 60,
            },
            "publishingPrinciples": "https://tmc.com.br/politica-editorial",
        },
        "inLanguage": "pt-BR",
        "articleSection": categoria or "Geral",
        # Copyright (1E)
        "copyrightHolder": {"@type": "Organization", "name": "TMC"},
        "copyrightYear": datetime.now(timezone.utc).year,
        # isPartOf (1E)
        "isPartOf": {
            "@type": "WebSite",
            "name": "TMC",
            "url": "https://tmc.com.br",
        },
    }
    if conteudo:
        schema["articleBody"] = conteudo[:5000]
        schema["wordCount"] = len(conteudo.split())
        # SpeakableSpecification for voice assistants
        schema["speakable"] = {
            "@type": "SpeakableSpecification",
            "cssSelector": ["article", ".article-body", ".entry-content"],
        }
    if tags:
        schema["keywords"] = ", ".join(tags[:10])

    # Image always present with fallback (1B)
    img_url = image_url or _DEFAULT_IMAGE_URL
    schema["image"] = {
        "@type": "ImageObject",
        "url": img_url,
        "width": 1200,
        "height": 630,
        "caption": titulo[:110] if titulo else "",
        "creditText": "TMC",
    }
    schema["thumbnailUrl"] = img_url

    if entities:
        schema["about"] = [{"@type": "Thing", "name": e} for e in entities[:5]]
        schema["mentions"] = [{"@type": "Thing", "name": e} for e in entities[:10]]
    return schema


def _build_claim_review(
    verification_data: dict,
    article_url: str = "",
    publisher_name: str = "TMC",
) -> Optional[dict]:
    """Build ClaimReview JSON-LD when verification data available with confidence > 0.6."""
    if not verification_data:
        return None
    confidence = verification_data.get("confidence_score", 0)
    if confidence < 0.6:
        return None
    claims = verification_data.get("claims", [])
    reviewed_claim = next((c for c in claims if c.get("verdict") == "grounded"), None)
    if not reviewed_claim:
        return None
    if confidence >= 0.8:
        rating_value, rating_name = 5, "Verdadeiro"
    elif confidence >= 0.7:
        rating_value, rating_name = 4, "Verdadeiro com ressalvas"
    elif confidence >= 0.6:
        rating_value, rating_name = 3, "Parcialmente verdadeiro"
    else:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "ClaimReview",
        "url": article_url,
        "claimReviewed": reviewed_claim.get("text", "")[:300],
        "datePublished": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "author": {
            "@type": "Organization",
            "name": publisher_name,
            "url": "https://tmc.com.br",
        },
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": rating_value,
            "bestRating": 5,
            "worstRating": 1,
            "alternateName": rating_name,
        },
    }


def _build_audit_data(
    request_data,
    result: dict,
    enrichment,
    phase_timings: dict,
    total_ms: int,
) -> dict:
    """Build audit trail data dict from generation pipeline results."""
    verification = result.get("verification", {})

    # Hash system prompt for tracking prompt version changes
    prompt_hash = ""
    try:
        from services.llm_service import get_system_prompt
        sys_prompt = get_system_prompt(
            persona=request_data.persona,
            tom=request_data.tom,
            tipo_materia=request_data.tipo_materia,
            categoria=request_data.categoria,
        )
        prompt_hash = hashlib.sha256(sys_prompt.encode()).hexdigest()[:16]
    except Exception:
        pass

    # Determine safety gate decision
    if result.get("publish_blocked"):
        safety_decision = "blocked"
    elif result.get("human_review_required"):
        safety_decision = "human_review"
    else:
        safety_decision = "allowed"

    # Build enrichment summary (not full text, just metadata)
    enrichment_summary = None
    if enrichment:
        enrichment_summary = {
            "success": getattr(enrichment, "success", False),
            "key_facts_count": len(getattr(enrichment, "key_facts", []) or []),
            "source_urls_count": len(getattr(enrichment, "source_urls", []) or []),
            "source_urls": getattr(enrichment, "source_urls", []) or [],
            "verified_chars": getattr(enrichment, "verified_chars", 0),
        }

    return {
        "correlation_id": result.get("correlation_id"),
        "request_payload": {
            "categoria": request_data.categoria,
            "tom": request_data.tom,
            "tipo_materia": request_data.tipo_materia,
            "persona": request_data.persona,
            "source_len": len(request_data.texto_base.strip()),
            "titulo_fonte": request_data.titulo_fonte,
        },
        "system_prompt_hash": prompt_hash,
        "user_prompt_text": result.pop("_user_prompt", None),
        "raw_llm_response": result.pop("_raw_response", None),
        "enrichment_result": enrichment_summary,
        "verification_result": verification,
        "cove_applied": verification.get("cove_applied", False),
        "cove_reclassified": verification.get("cove_reclassified", 0),
        "safety_gate_decision": safety_decision,
        "confidence_score": verification.get("confidence_score", 0.0),
        "risk_level": verification.get("risk_level", "unknown"),
        "publish_blocked": result.get("publish_blocked", False),
        "block_reason": result.get("block_reason"),
        "phase_timings": phase_timings,
        "total_duration_ms": total_ms,
    }


async def _persist_audit(audit_data: dict):
    """Persist audit data to database (fire-and-forget)."""
    try:
        from services.database import DatabaseService
        db = DatabaseService()
        await asyncio.to_thread(db.insert_generation_audit, audit_data)
    except Exception as e:
        logger.warning(f"Audit trail persist failed (non-blocking): {e}")


async def _find_similar_articles(
    tags: Optional[list] = None,
    titulo_fonte: Optional[str] = None,
    categoria: Optional[str] = None,
    limit: int = 5,
) -> list:
    """
    Find similar articles in the database for merge suggestion.

    Searches by tags overlap. Returns lightweight article summaries
    the frontend can use to suggest merging.
    """
    if not tags or len(tags) == 0:
        return []

    try:
        from services.database import DatabaseService
        db = DatabaseService()

        # Search by the most specific tag (first tag is usually most relevant)
        articles_found = []
        seen_ids = set()

        for tag in tags[:3]:
            results, count, _ = await asyncio.to_thread(
                db.get_articles_with_urgency, page=1, limit=limit, tag=tag, category=categoria
            )
            for article in results:
                article_id = str(article.id)
                if article_id not in seen_ids:
                    seen_ids.add(article_id)
                    # Only suggest articles with substantial content
                    content = article.content or article.preview or ""
                    if len(content.strip()) > 200:
                        articles_found.append({
                            "id": article_id,
                            "title": article.title,
                            "source": article.source_name if hasattr(article, 'source_name') else "",
                            "preview": (content[:200] + "...") if len(content) > 200 else content,
                            "content_length": len(content),
                            "published_at": article.published_at.isoformat() if article.published_at else None,
                        })

            if len(articles_found) >= limit:
                break

        return articles_found[:limit]

    except Exception as e:
        logger.warning(f"Similar articles search failed: {e}")
        return []


# Synchronous wrappers for Azure Functions (if needed)

def generate_article_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for generate_article_handler."""
    import asyncio
    return asyncio.run(generate_article_handler(req))


def extract_topics_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for extract_topics_handler."""
    import asyncio
    return asyncio.run(extract_topics_handler(req))


def generate_tags_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for generate_tags_handler."""
    import asyncio
    return asyncio.run(generate_tags_handler(req))


async def merge_topics_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Merge topics from multiple articles into story-centric structure.

    POST /api/merge-topics
    Body: {articles: [{id, title, content, source}, ...]}  (max 3)
    Returns: {groups, exclusives, quotes, summary}
    """
    logger.info("Merge topics request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        if 'articles' not in body or not isinstance(body['articles'], list):
            return create_error_response("'articles' array is required", 400)

        articles = body['articles']

        if len(articles) == 0:
            return create_error_response("At least one article is required", 400)

        if len(articles) > 3:
            return create_error_response("Maximum 3 articles allowed per merge", 400)

        # Validate each article has required fields
        for i, article in enumerate(articles):
            if not article.get('id'):
                return create_error_response(f"Article {i+1} missing 'id' field", 400)
            if not article.get('source'):
                return create_error_response(f"Article {i+1} missing 'source' field", 400)
            if not article.get('title'):
                return create_error_response(f"Article {i+1} missing 'title' field", 400)
            # Use content or preview - one must exist with minimum length
            content_text = article.get('content') or article.get('preview') or ''
            if not content_text or len(content_text.strip()) < 50:
                return create_error_response(
                    f"Article {i+1} ('{article.get('title', 'Unknown')[:50]}...') must have 'content' or 'preview' with at least 50 characters. Current length: {len(content_text.strip())} chars",
                    400
                )

        # Prepare articles for LLM
        prepared_articles = []
        for article in articles:
            prepared_articles.append({
                'id': str(article['id']),
                'title': article['title'],
                'content': article.get('content') or article.get('preview', ''),
                'source': article['source']
            })

        # Import LLM service
        from services.llm_service import get_llm_service

        try:
            llm = get_llm_service()
        except ValueError as e:
            return create_error_response(
                "AI service not configured. Please set AZURE_AI_API_KEY or ANTHROPIC_API_KEY.",
                503
            )

        # Merge topics
        result = await llm.merge_topics(prepared_articles)

        logger.info(f"Merge topics completed: {len(result.get('groups', []))} groups")
        return create_success_response(result)

    except ValueError as e:
        logger.error(f"Validation error in merge_topics: {e}")
        return create_error_response("Erro de validacao nos dados enviados", 400)
    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        return create_error_response("Erro no servico de IA", 503)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in merge_topics: {e}")
        return create_error_response("Erro ao processar resposta da IA. Tente novamente.", 500)
    except Exception as e:
        logger.exception(f"Unexpected error in merge_topics: {e}")
        return create_error_response("Erro interno do servidor", 500)


def merge_topics_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for merge_topics_handler."""
    import asyncio
    return asyncio.run(merge_topics_handler(req))
