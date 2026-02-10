"""
Generation API - Azure Functions endpoints for AI article generation.

Endpoints:
- POST /api/generate - Generate article from source text (4-phase anti-hallucination pipeline)
- POST /api/extract-topics - Extract topics from text
- POST /api/generate-tags - Generate tags for content
"""

import logging
import json
import re
import time
import hashlib
import asyncio
import uuid
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import azure.functions as func
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for article generation."""
    texto_base: str = Field(..., min_length=20, description="Source text content")
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

    @field_validator('texto_base', 'orientacao_lide', 'contexto', 'creditos', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Strip HTML tags and control characters from text inputs."""
        if not isinstance(v, str):
            return v
        v = re.sub(r'<[^>]+>', '', v)  # Strip HTML tags
        v = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', v)  # Strip control chars
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

    # --- HARD BLOCKS ---
    if risk_level == "critical":
        decision.publish_blocked = True
        decision.block_reasons.append("Nivel de risco CRITICO detectado")

    if confidence_score < 0.4 and verification_data.get("is_verified", False):
        decision.publish_blocked = True
        decision.block_reasons.append(f"Confianca muito baixa ({confidence_score:.0%})")

    if fabricated_claims >= 3:
        decision.publish_blocked = True
        decision.block_reasons.append(f"{fabricated_claims} afirmacoes fabricadas")
    elif fabricated_claims == 2 and confidence_score < 0.40:
        decision.publish_blocked = True
        decision.block_reasons.append(f"2 afirmacoes fabricadas com confianca baixa ({confidence_score:.0%})")

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

    if effective_expansion > 15:
        decision.publish_blocked = True
        decision.block_reasons.append(f"Expansao extrema: {effective_expansion:.1f}x")

    # --- SOFT GATES (human review) ---
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
    if output_entities and len(novel_entities) >= 3:
        if len(novel_entities) / len(output_entities) > 0.50:
            decision.human_review_required = True
            decision.review_reasons.append(
                f"{len(novel_entities)} entidades novas nao presentes na fonte"
            )

    if 10 < effective_expansion <= 15:
        decision.human_review_required = True
        decision.review_reasons.append(f"Expansao elevada: {effective_expansion:.1f}x")

    if risk_level == "high" and not decision.publish_blocked:
        decision.human_review_required = True
        decision.review_reasons.append("Nivel de risco ALTO")

    return decision


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
            return create_error_response(f"Validation error: {str(e)}", 400)

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
            try:
                fact_checker = get_fact_check_service()
                enrichment = await fact_checker.enrich_context(
                    texto_base=request_data.texto_base,
                    titulo_fonte=request_data.titulo_fonte,
                    tags=request_data.tags,
                )
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
            )
        except Exception as e:
            logger.error(f"[{correlation_id}] Phase 2 generation failed: {e}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Falha na geracao do artigo",
                    "details": str(e),
                }, ensure_ascii=False),
                status_code=502,
                mimetype="application/json",
            )

        phase_timings["generation_ms"] = int((time.time() - generation_start) * 1000)
        logger.info(f"[{correlation_id}] Phase 2 complete: article generated")

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
                )
                result["verification"] = verification.to_dict()
                logger.info(
                    f"[{correlation_id}] Phase 3 complete: confidence={verification.confidence_score:.3f}, "
                    f"risk={verification.risk_level}"
                )
            except Exception as e:
                logger.warning(f"[{correlation_id}] Phase 3 verification failed (non-blocking): {e}")
                result["verification"] = {
                    "is_verified": False,
                    "risk_level": "high",
                    "requires_human_review": True,
                    "warnings": [f"Verification failed: {str(e)[:100]}"],
                    "review_reasons": ["Verification pipeline error"],
                }
                # Ensure failed verification flags human review at top level
                result["human_review_required"] = True
                result["review_reasons"] = [
                    "Verificacao automatica falhou - revisao manual necessaria"
                ]
            phase_timings["verification_ms"] = int((time.time() - verification_start) * 1000)

        # ==============================================================
        # Publish safety gate: block critical-risk articles
        # ==============================================================
        # Use enrichment-adjusted source length for expansion ratio if available
        effective_source_len = source_len  # default to raw source length
        if enrichment and hasattr(enrichment, 'verified_chars') and enrichment.verified_chars > 0:
            effective_source_len = enrichment.verified_chars
        elif enrichment and isinstance(enrichment, dict) and enrichment.get('verified_chars', 0) > 0:
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
        result["structured_data"] = _build_schema_org(
            titulo=result.get("titulo", ""),
            linha_fina=result.get("linha_fina", ""),
            tags=result.get("tags_sugeridas", []),
            conteudo=result.get("conteudo", ""),
            categoria=request_data.categoria,
        )

        # Add correlation_id to result
        result["correlation_id"] = correlation_id

        total_ms = int((time.time() - pipeline_start) * 1000)
        phase_timings["total_ms"] = total_ms
        logger.info(f"[{correlation_id}] Full pipeline complete in {total_ms}ms")

        # ==============================================================
        # Audit Trail (fire-and-forget, non-blocking)
        # ==============================================================
        try:
            audit_data = _build_audit_data(
                request_data=request_data,
                result=result,
                enrichment=enrichment,
                phase_timings=phase_timings,
                total_ms=total_ms,
            )
            # Fire and forget - run in background thread
            asyncio.create_task(_persist_audit(audit_data))
        except Exception as e:
            logger.warning(f"[{correlation_id}] Audit trail prep failed (non-blocking): {e}")

        return create_success_response(result)

    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        return create_error_response(f"AI service error: {str(e)}", 503)
    except ValueError as e:
        logger.error(f"Invalid response from AI: {e}")
        return create_error_response(f"Invalid AI response: {str(e)}", 500)
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
            return create_error_response(f"Validation error: {str(e)}", 400)

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
            return create_error_response(f"Validation error: {str(e)}", 400)

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
) -> dict:
    """
    Build Schema.org/JSON-LD NewsArticle structured data.

    Frontend/WP plugin can inject this into <head> when publishing.
    The @id in mainEntityOfPage and image URL are typically filled by
    the WP plugin at publish time.

    Includes Google News 2026 recommended fields:
    - dateCreated, isAccessibleForFree
    - publisher.url, publisher.sameAs, publisher.logo dimensions
    - speakable (SpeakableSpecification)
    - image as ImageObject with dimensions
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": titulo[:110] if titulo else "",
        "description": linha_fina[:200] if linha_fina else "",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": "",
        },
        "datePublished": now_iso,
        "dateModified": now_iso,
        "dateCreated": now_iso,
        "isAccessibleForFree": True,
        "author": {
            "@type": "Organization",
            "name": "TMC",
            "url": "https://tmc.com.br",
        },
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
        },
        "inLanguage": "pt-BR",
        "articleSection": categoria or "Geral",
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
    if image_url:
        schema["image"] = {
            "@type": "ImageObject",
            "url": image_url,
            "width": 1200,
            "height": 630,
        }
    return schema


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
            results, count, _ = db.get_articles_with_urgency(
                page=1, limit=limit, tag=tag, category=categoria
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
        return create_error_response(f"Erro de validação: {str(e)}", 400)
    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        error_msg = str(e)
        if "API error" in error_msg or "timeout" in error_msg.lower():
            return create_error_response("Serviço de IA temporariamente indisponível. Tente novamente.", 503)
        return create_error_response(f"Erro no serviço de IA: {error_msg}", 503)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in merge_topics: {e}")
        return create_error_response("Erro ao processar resposta da IA. Tente novamente.", 500)
    except Exception as e:
        logger.exception(f"Unexpected error in merge_topics: {e}")
        # Provide more context in error message
        error_type = type(e).__name__
        return create_error_response(f"Erro inesperado ({error_type}): {str(e)[:200]}", 500)


def merge_topics_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for merge_topics_handler."""
    import asyncio
    return asyncio.run(merge_topics_handler(req))
