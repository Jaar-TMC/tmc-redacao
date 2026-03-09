"""
TMC 10-Article Generation Audit — Comprehensive single-article generation test.

Tests the COMPLETE generation pipeline on 10 diverse RSS articles:
  Phase 1: Exa Enrichment
  Phase 2: LLM Generation + Temporal Decontamination
  Phase 3: Verification (claims + entities + quotes + CoVe)
  Phase 4: Quality Loop (evaluate criteria -> Exa verify claims -> regenerate -> re-verify)
  Phase 5: Safety Gates (hard blocks + soft gates)

Each article is processed individually (single-article mode) to test the most common
user workflow: selecting one RSS article and generating a journalistic piece.

Covers all 5 editorial categories with varying tones and article types.

Usage: python scripts/test_10_articles_audit.py
"""

import os
import sys
import json
import asyncio
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load local.settings.json
def load_local_settings():
    settings_path = Path(__file__).parent.parent / "local.settings.json"
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key, value in data.get("Values", {}).items():
                os.environ.setdefault(key, str(value))
        print(f"[OK] Loaded {len(data.get('Values', {}))} env vars from local.settings.json")
    else:
        print("[ERROR] local.settings.json not found")
        sys.exit(1)

load_local_settings()

# Override production safety mode for testing
os.environ.setdefault("PRODUCTION_SAFETY_MODE", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-audit-key-not-for-production")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("test_10_articles")


# ============================================
# 10 Test Configurations (diverse editorial coverage)
# ============================================

TEST_CONFIGS = [
    # 1. Esportes - informal tone
    {"category": "esportes", "tom": "informal", "tipo_materia": "destaque", "modo_opinativo": False},
    # 2. Esportes - emotional tone (column)
    {"category": "esportes", "tom": "emocional", "tipo_materia": "coluna", "modo_opinativo": True},
    # 3. Economia - didático
    {"category": "economia", "tom": "didatico", "tipo_materia": "destaque", "modo_opinativo": False},
    # 4. Economia - analítico
    {"category": "economia", "tom": "analitico", "tipo_materia": "analise", "modo_opinativo": False},
    # 5. Política - sóbrio
    {"category": "politica", "tom": "sobrio", "tipo_materia": "destaque", "modo_opinativo": False},
    # 6. Brasil (geral) - conversacional
    {"category": "geral", "tom": "conversacional", "tipo_materia": "destaque", "modo_opinativo": False},
    # 7. Brasil (geral) - informativo
    {"category": "geral", "tom": "informativo", "tipo_materia": "servico", "modo_opinativo": False},
    # 8. Entretenimento - leve
    {"category": "entretenimento", "tom": "leve", "tipo_materia": "destaque", "modo_opinativo": False},
    # 9. Entretenimento - criativo
    {"category": "entretenimento", "tom": "criativo", "tipo_materia": "destaque", "modo_opinativo": False},
    # 10. Geral - opinativo (column)
    {"category": "geral", "tom": "conversacional", "tipo_materia": "coluna", "modo_opinativo": True},
]


async def fetch_test_articles():
    """Fetch 10 diverse articles from DB for testing."""
    from services.database import DatabaseService
    db = DatabaseService()
    test_cases = []

    # Target categories with multiple articles each
    category_targets = {
        "esportes": 2,
        "economia": 2,
        "politica": 1,
        "geral": 2,       # Maps to Brasil, Segurança, etc.
        "entretenimento": 2,
        "cultura": 1,      # Fallback to geral if not enough
    }

    found_by_cat = {}

    for cat, needed in category_targets.items():
        found_by_cat[cat] = []
        try:
            articles, count, _ = db.get_articles_with_urgency(
                page=1, limit=10, category=cat
            )
            for article in articles:
                if len(found_by_cat[cat]) >= needed:
                    break
                content = article.content or article.preview or ""
                if len(content.strip()) > 500:  # Minimum viable content (above NOTA_ONLY_THRESHOLD)
                    found_by_cat[cat].append({
                        "title": article.title,
                        "content": content,
                        "source": getattr(article, 'source_name', 'Unknown'),
                        "category": cat if cat != "cultura" else "geral",
                        "content_length": len(content),
                        "tags": (article.tags if hasattr(article, 'tags') and article.tags else []),
                        "article_id": str(getattr(article, 'id', '')),
                    })
                    print(f"  [{cat.upper()}] {article.title[:70]}... ({len(content)} chars)")
        except Exception as e:
            print(f"  [{cat.upper()}] Error fetching: {e}")

    # Flatten and ensure we have exactly 10
    for cat, articles in found_by_cat.items():
        test_cases.extend(articles)

    # If we have less than 10, fetch more from any category
    if len(test_cases) < 10:
        try:
            articles, _, _ = db.get_articles_with_urgency(page=1, limit=20)
            for article in articles:
                if len(test_cases) >= 10:
                    break
                content = article.content or article.preview or ""
                existing_ids = {tc.get("article_id") for tc in test_cases}
                aid = str(getattr(article, 'id', ''))
                if aid not in existing_ids and len(content.strip()) > 500:
                    test_cases.append({
                        "title": article.title,
                        "content": content,
                        "source": getattr(article, 'source_name', 'Unknown'),
                        "category": getattr(article, 'classification', 'geral') or 'geral',
                        "content_length": len(content),
                        "tags": (article.tags if hasattr(article, 'tags') and article.tags else []),
                        "article_id": aid,
                    })
                    print(f"  [FILL] {article.title[:70]}... ({len(content)} chars)")
        except Exception as e:
            print(f"  [FILL] Error: {e}")

    test_cases = test_cases[:10]
    print(f"\n[OK] Fetched {len(test_cases)} test articles")
    return test_cases


async def run_full_pipeline(test_case: dict, config: dict) -> dict:
    """
    Run the COMPLETE pipeline on a single article with given editorial config.
    Replicates generate_article_handler exactly.
    """
    from services.llm_service import get_llm_service
    from services.fact_check_service import (
        get_fact_check_service, is_fact_check_enabled, compute_readability
    )
    from functions.generation_api import (
        evaluate_quality_criteria, build_corrective_instructions,
        evaluate_safety_gates, QUALITY_LOOP_ENABLED, QUALITY_LOOP_MAX_ATTEMPTS,
        QUALITY_LOOP_MAX_CLAIM_SEARCHES, DECONTAMINATION_ENABLED,
    )
    from services.fact_check_service import ExtractedClaim

    llm = get_llm_service()
    cat = config["category"]
    tom = config["tom"]
    tipo_materia = config["tipo_materia"]
    modo_opinativo = config["modo_opinativo"]
    tags = test_case.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []

    result = {
        "test_case": {
            "title": test_case["title"],
            "source_category": test_case["category"],
            "editorial_config": config,
            "content_length": test_case["content_length"],
            "source": test_case["source"],
        },
        "phases": {},
        "quality_loop": {},
        "safety_gates": {},
        "editorial_audit": {},
        "publication_status": None,
        "errors": [],
        "total_duration_ms": 0,
    }

    pipeline_start = time.time()

    # ============================================
    # Phase 1: Enrichment
    # ============================================
    enrichment = None
    enrichment_context = None
    enrichment_key_facts = None
    source_urls = []
    verified_chars = len(test_case["content"].strip())

    if is_fact_check_enabled():
        try:
            t0 = time.time()
            fact_checker = get_fact_check_service()
            enrichment = await fact_checker.enrich_context(
                texto_base=test_case["content"],
                titulo_fonte=test_case["title"],
                tags=tags,
            )
            phase1_ms = int((time.time() - t0) * 1000)

            if enrichment.success:
                enrichment_context = enrichment.context_text
                enrichment_key_facts = enrichment.key_facts
                source_urls = enrichment.source_urls
                verified_chars = enrichment.verified_chars

            result["phases"]["enrichment"] = {
                "success": enrichment.success,
                "key_facts_count": len(enrichment.key_facts),
                "source_urls_count": len(enrichment.source_urls),
                "verified_chars": verified_chars,
                "duration_ms": phase1_ms,
                "key_facts": enrichment.key_facts[:5],
                "source_urls": enrichment.source_urls[:3],
            }
        except Exception as e:
            result["phases"]["enrichment"] = {"success": False, "error": str(e)}
            result["errors"].append(f"Enrichment: {e}")

    # ============================================
    # Phase 2: Generation
    # ============================================
    generated = None
    try:
        t0 = time.time()
        generated = await llm.generate_article(
            texto_base=test_case["content"],
            tom=tom,
            tipo_materia=tipo_materia,
            categoria=cat,
            modo_opinativo=modo_opinativo,
            tags=tags,
            enrichment_context=enrichment_context,
            enrichment_key_facts=enrichment_key_facts,
            verified_chars=verified_chars,
            source_urls=source_urls,
        )
        phase2_ms = int((time.time() - t0) * 1000)

        result["phases"]["generation"] = {
            "success": True,
            "titulo": generated.get("titulo", ""),
            "titulo_curto": generated.get("titulo_curto", ""),
            "linha_fina": generated.get("linha_fina", ""),
            "content_length": len(generated.get("conteudo", "")),
            "resumo_count": len(generated.get("resumo", [])),
            "slug": generated.get("slug_sugerido", ""),
            "tags_count": len(generated.get("tags_sugeridas", [])),
            "tags": generated.get("tags_sugeridas", []),
            "duration_ms": phase2_ms,
        }
    except Exception as e:
        result["phases"]["generation"] = {"success": False, "error": str(e)}
        result["errors"].append(f"Generation: {e}")
        result["total_duration_ms"] = int((time.time() - pipeline_start) * 1000)
        return result

    # ============================================
    # Phase 2.3: Temporal Decontamination
    # ============================================
    if DECONTAMINATION_ENABLED and generated.get("conteudo"):
        try:
            from services.fact_check_service import decontaminate_article
            original_content = generated["conteudo"]
            enrichment_text = enrichment_context or ""
            cleaned, removals_count, removed = decontaminate_article(
                original_content, test_case["content"], enrichment_text
            )
            if cleaned != original_content:
                generated["conteudo"] = cleaned
                result["phases"]["decontamination"] = {
                    "applied": True,
                    "chars_removed": len(original_content) - len(cleaned),
                    "removals": removals_count,
                    "removed_items": removed[:5],
                }
            else:
                result["phases"]["decontamination"] = {"applied": False}
        except Exception as e:
            result["phases"]["decontamination"] = {"error": str(e)}

    # ============================================
    # Phase 3: Verification
    # ============================================
    verification_data = {}
    if is_fact_check_enabled() and generated:
        try:
            t0 = time.time()
            fact_checker = get_fact_check_service()
            verification = await fact_checker.verify_article(
                texto_base=test_case["content"],
                generated_article=generated.get("conteudo", ""),
                citacoes=None,
                enrichment=enrichment,
            )
            phase3_ms = int((time.time() - t0) * 1000)
            verification_data = verification.to_dict()

            result["phases"]["verification"] = {
                "success": True,
                "confidence_score": verification.confidence_score,
                "risk_level": verification.risk_level,
                "expansion_ratio": verification.expansion_ratio,
                "total_claims": verification.total_claims,
                "grounded_claims": verification.grounded_claims,
                "fabricated_claims": verification.fabricated_claims,
                "unverifiable_claims": verification.unverifiable_claims,
                "claims": [
                    {"text": c.text, "verdict": c.verdict, "category": c.category}
                    for c in verification.claims
                ],
                "novel_entities": verification.entity_comparison.get("novel_entities", []),
                "quote_verification_rate": getattr(verification, 'quote_verification', {}).get('verification_rate', None) if hasattr(verification, 'quote_verification') else None,
                "duration_ms": phase3_ms,
            }
        except Exception as e:
            result["phases"]["verification"] = {"success": False, "error": str(e)}
            result["errors"].append(f"Verification: {e}")

    # ============================================
    # Phase 4: Quality Loop
    # ============================================
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

    readability = {}
    if generated.get("conteudo"):
        try:
            readability = compute_readability(generated["conteudo"])
        except Exception as e:
            logger.warning(f"Readability failed: {e}")

    if (QUALITY_LOOP_ENABLED
            and is_fact_check_enabled()
            and verification_data.get("is_verified")):

        t0 = time.time()
        quality_eval = evaluate_quality_criteria(
            verification_data, readability,
            categoria=cat, tipo_materia=tipo_materia,
        )
        best_failures_count = len(quality_eval["failures"])

        attempt = 0
        while not quality_eval["all_passed"] and attempt < QUALITY_LOOP_MAX_ATTEMPTS:
            attempt += 1
            quality_loop_result["quality_loop_attempts"] = attempt
            logger.info(
                f"Quality Loop attempt {attempt}/{QUALITY_LOOP_MAX_ATTEMPTS}: "
                f"failures={[f['criterion'] for f in quality_eval['failures']]}"
            )

            # Exa verify fabricated claims
            exa_corrections = []
            fabrication_failure = next(
                (f for f in quality_eval["failures"] if f["criterion"] == "fabrication"), None
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
                        elif exa_result["verdict"] == "contradicted":
                            quality_loop_result["quality_loop_claims_corrected"] += 1
                            if exa_result.get("corrective_instruction"):
                                exa_corrections.append(exa_result["corrective_instruction"])
                        else:
                            quality_loop_result["quality_loop_claims_removed"] += 1
                            if exa_result.get("corrective_instruction"):
                                exa_corrections.append(exa_result["corrective_instruction"])
                except Exception as e:
                    logger.warning(f"Exa fabricated verification failed: {e}")

            # Exa verify unverifiable claims
            unverifiable_failure = next(
                (f for f in quality_eval["failures"] if f["criterion"] == "unverifiable"), None
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
                            evidence = exa_result.get("evidence", "")
                            unverifiable_corrections.append(
                                f'ATRIBUIR: "{claim_obj.text}" confirmada. Evidencia: {evidence[:200]}'
                            )
                        elif exa_result["verdict"] == "contradicted":
                            quality_loop_result["quality_loop_unverifiable_removed"] += 1
                            if exa_result.get("corrective_instruction"):
                                unverifiable_corrections.append(exa_result["corrective_instruction"])
                        else:
                            quality_loop_result["quality_loop_unverifiable_removed"] += 1
                            unverifiable_corrections.append(
                                f'REMOVER: "{claim_obj.text}" nao verificavel.'
                            )
                except Exception as e:
                    logger.warning(f"Exa unverifiable verification failed: {e}")

            all_exa_corrections = exa_corrections + unverifiable_corrections

            # Check if all confirmed
            non_claim_failures = [
                f for f in quality_eval["failures"]
                if f["criterion"] not in ("fabrication", "unverifiable")
            ]
            all_confirmed = (
                not exa_corrections
                and not any(c.startswith('REMOVER:') or c.startswith('CORRIGIR:') for c in unverifiable_corrections)
                and (quality_loop_result["quality_loop_claims_confirmed"] > 0
                     or quality_loop_result["quality_loop_unverifiable_verified"] > 0)
                and not non_claim_failures
            )
            if all_confirmed:
                quality_eval = {"all_passed": True, "failures": []}
                break

            # Regenerate with corrections
            corrective_prompt = build_corrective_instructions(
                quality_eval["failures"], all_exa_corrections
            )
            try:
                regen = await llm.generate_article(
                    texto_base=test_case["content"],
                    tom=tom,
                    tipo_materia=tipo_materia,
                    categoria=cat,
                    modo_opinativo=modo_opinativo,
                    tags=tags,
                    enrichment_context=enrichment_context,
                    enrichment_key_facts=enrichment_key_facts,
                    verified_chars=verified_chars,
                    sensitive_instructions=[corrective_prompt],
                    source_urls=source_urls,
                )

                fact_checker = get_fact_check_service()
                regen_verif = await fact_checker.verify_article(
                    texto_base=test_case["content"],
                    generated_article=regen.get("conteudo", ""),
                    enrichment=enrichment,
                )
                regen_verif_data = regen_verif.to_dict()
                regen_readability = compute_readability(regen.get("conteudo", ""))
                regen_eval = evaluate_quality_criteria(
                    regen_verif_data, regen_readability,
                    categoria=cat, tipo_materia=tipo_materia,
                )

                if regen_eval["all_passed"] or len(regen_eval["failures"]) < best_failures_count:
                    old_criteria = {f["criterion"] for f in quality_eval["failures"]}
                    new_criteria = {f["criterion"] for f in regen_eval["failures"]}
                    fixed = old_criteria - new_criteria
                    quality_loop_result["quality_loop_issues_fixed"].extend(list(fixed))

                    generated = regen
                    verification_data = regen_verif_data
                    readability = regen_readability
                    quality_eval = regen_eval
                    best_failures_count = len(regen_eval["failures"])
            except Exception as e:
                logger.warning(f"Quality Loop attempt {attempt} failed: {e}")
                break

        quality_loop_result["quality_loop_passed"] = quality_eval["all_passed"]
        quality_loop_ms = int((time.time() - t0) * 1000)
        quality_loop_result["duration_ms"] = quality_loop_ms

        if not quality_loop_result["quality_loop_passed"]:
            quality_loop_result["remaining_failures"] = [
                f["criterion"] for f in quality_eval["failures"]
            ]

    result["quality_loop"] = quality_loop_result
    result["readability"] = readability

    # ============================================
    # Phase 5: Safety Gates
    # ============================================
    if verification_data:
        content_length = len(generated.get("conteudo", ""))
        effective_source_len = verified_chars if verified_chars > 0 else len(test_case["content"])

        safety = evaluate_safety_gates(
            verification_data=verification_data,
            content_length=content_length,
            effective_source_len=effective_source_len,
        )

        result["safety_gates"] = {
            "publish_blocked": safety.publish_blocked,
            "block_reasons": safety.block_reasons,
            "human_review_required": safety.human_review_required,
            "review_reasons": safety.review_reasons,
        }

        if safety.publish_blocked:
            result["publication_status"] = "blocked"
        elif safety.human_review_required:
            result["publication_status"] = "draft_review"
        elif verification_data.get("is_verified"):
            result["publication_status"] = "ready_for_review"
        else:
            result["publication_status"] = "draft"

    # ============================================
    # Editorial Standards Audit
    # ============================================
    titulo = generated.get("titulo", "")
    titulo_curto = generated.get("titulo_curto", "")
    linha_fina = generated.get("linha_fina", "")
    resumo = generated.get("resumo", [])
    content = generated.get("conteudo", "")

    editorial = {
        "titulo_length": len(titulo),
        "titulo_ok": len(titulo) <= 75 and len(titulo) > 10,
        "titulo_curto_length": len(titulo_curto),
        "titulo_curto_ok": 0 < len(titulo_curto) <= 70,
        "linha_fina_length": len(linha_fina),
        "linha_fina_ok": len(linha_fina) <= 120 and len(linha_fina) > 10,
        "resumo_count": len(resumo),
        "resumo_ok": len(resumo) == 4,
        "content_length": len(content),
        "content_min_ok": len(content) >= 2000,
        "has_cta": "siga a tmc" in content.lower() or "whatsapp" in content.lower(),
        "has_bold": "**" in content,
        "has_subtitles": "##" in content,
        "slug": generated.get("slug_sugerido", ""),
        "slug_ok": bool(generated.get("slug_sugerido")),
    }

    # Check for banned words in non-opinion pieces
    if not modo_opinativo:
        banned_words = ["absurdo", "vergonhoso", "genial", "inacreditável", "chocante"]
        found_banned = [w for w in banned_words if w in content.lower()]
        editorial["banned_words_found"] = found_banned
        editorial["banned_words_ok"] = len(found_banned) == 0

    # Count bold highlights
    import re
    bold_count = len(re.findall(r'\*\*[^*]+\*\*', content))
    editorial["bold_count"] = bold_count
    editorial["bold_ok"] = 3 <= bold_count <= 25  # Enforced by _enforce_bold_limit post-processor

    editorial_pass_count = sum(1 for k, v in editorial.items() if k.endswith("_ok") and v)
    editorial_total_checks = sum(1 for k in editorial.keys() if k.endswith("_ok"))
    editorial["pass_rate"] = f"{editorial_pass_count}/{editorial_total_checks}"

    result["editorial_audit"] = editorial

    # Store generated content for review
    result["generated_article"] = {
        "titulo": titulo,
        "titulo_curto": titulo_curto,
        "linha_fina": linha_fina,
        "resumo": resumo,
        "conteudo_preview": content[:500] + "..." if len(content) > 500 else content,
        "conteudo_length": len(content),
        "slug": generated.get("slug_sugerido", ""),
        "tags": generated.get("tags_sugeridas", []),
    }

    result["total_duration_ms"] = int((time.time() - pipeline_start) * 1000)
    return result


def print_report(idx: int, r: dict, config: dict):
    """Print detailed report for one test case."""
    tc = r["test_case"]
    print(f"\n{'='*100}")
    print(f"  TEST #{idx+1}/10: [{config['category'].upper()}] {tc['title'][:70]}")
    print(f"  Config: tom={config['tom']} tipo={config['tipo_materia']} opinativo={config['modo_opinativo']}")
    print(f"{'='*100}")
    print(f"  Source: {tc['source']} | {tc['content_length']} chars | Duration: {r['total_duration_ms']}ms")

    # Enrichment
    e = r["phases"].get("enrichment", {})
    if e.get("success"):
        print(f"\n  [Phase 1] Enrichment: {e['key_facts_count']} facts, {e['source_urls_count']} URLs ({e['duration_ms']}ms)")
    else:
        print(f"\n  [Phase 1] Enrichment: {'FAILED' if 'error' in e else 'SKIPPED'}")

    # Generation
    g = r["phases"].get("generation", {})
    if g.get("success"):
        print(f"  [Phase 2] Generation: {g['content_length']} chars ({g['duration_ms']}ms)")
        print(f"            Title: {g['titulo']}")
        print(f"            Linha fina: {g.get('linha_fina', '')[:120]}")
    else:
        print(f"  [Phase 2] Generation: FAILED - {g.get('error', 'N/A')}")
        return

    # Decontamination
    d = r["phases"].get("decontamination", {})
    if d.get("applied"):
        print(f"  [Phase 2.3] Decontamination: removed {d['chars_removed']} chars ({d['removals']} items)")

    # Verification
    v = r["phases"].get("verification", {})
    if v.get("success"):
        risk_colors = {"low": "LOW", "medium": "MED", "high": "HIGH", "critical": "CRIT"}
        risk = v.get("risk_level", "?")
        print(f"  [Phase 3] Verification: conf={v['confidence_score']:.2f} risk={risk_colors.get(risk, risk)} ({v['duration_ms']}ms)")
        print(f"            Claims: {v['total_claims']} total | {v['grounded_claims']} grounded | {v['fabricated_claims']} fabricated | {v['unverifiable_claims']} unverif")
        if v.get("novel_entities"):
            print(f"            Novel entities: {', '.join(v['novel_entities'][:5])}")
        for c in v.get("claims", [])[:5]:
            icon = {"grounded": "OK", "fabricated": "XX", "unverifiable": "??", "opinion": "OP", "context": "CT"}.get(c["verdict"], "  ")
            print(f"            [{icon}] {c['text'][:95]}")
    else:
        print(f"  [Phase 3] Verification: {'FAILED' if 'error' in v else 'SKIPPED'}")

    # Quality Loop
    ql = r.get("quality_loop", {})
    if ql.get("quality_loop_attempts", 0) > 0:
        status = "PASSED" if ql["quality_loop_passed"] else "FAILED"
        print(f"  [Phase 4] Quality Loop: {status} after {ql['quality_loop_attempts']} attempt(s) ({ql.get('duration_ms', 0)}ms)")
        if ql.get("quality_loop_issues_fixed"):
            print(f"            Fixed: {ql['quality_loop_issues_fixed']}")
        print(f"            Fab: {ql['quality_loop_claims_confirmed']}confirmed {ql['quality_loop_claims_corrected']}corrected {ql['quality_loop_claims_removed']}removed")
        print(f"            Unv: {ql['quality_loop_unverifiable_verified']}verified {ql['quality_loop_unverifiable_removed']}removed")
    else:
        print(f"  [Phase 4] Quality Loop: {'FIRST-PASS OK' if ql.get('quality_loop_passed') else 'NOT RUN'}")

    # Safety Gates
    sg = r.get("safety_gates", {})
    pub = r.get("publication_status", "unknown")
    if sg.get("publish_blocked"):
        print(f"  [Phase 5] Safety: BLOCKED - {'; '.join(sg['block_reasons'])}")
    elif sg.get("human_review_required"):
        print(f"  [Phase 5] Safety: REVIEW - {'; '.join(sg['review_reasons'])}")
    else:
        print(f"  [Phase 5] Safety: PASSED")
    print(f"  >>> STATUS: {pub.upper()}")

    # Readability
    rd = r.get("readability", {})
    if rd:
        print(f"  Readability: Flesch={rd.get('flesch_score', 0):.1f} AvgSent={rd.get('avg_sentence_length', 0):.1f}w")

    # Editorial Audit
    ea = r.get("editorial_audit", {})
    if ea:
        print(f"\n  --- EDITORIAL AUDIT ({ea.get('pass_rate', '?')}) ---")
        print(f"  Title ({ea['titulo_length']}ch): {'PASS' if ea['titulo_ok'] else 'FAIL'} | Short ({ea['titulo_curto_length']}ch): {'PASS' if ea['titulo_curto_ok'] else 'FAIL'}")
        print(f"  Linha fina ({ea['linha_fina_length']}ch): {'PASS' if ea['linha_fina_ok'] else 'FAIL'} | Resumo ({ea['resumo_count']}pts): {'PASS' if ea['resumo_ok'] else 'FAIL'}")
        print(f"  Content ({ea['content_length']}ch): {'PASS' if ea['content_min_ok'] else 'FAIL <2000'} | CTA: {'PASS' if ea['has_cta'] else 'FAIL'} | Bold ({ea['bold_count']}): {'PASS' if ea['bold_ok'] else 'FAIL'}")
        if ea.get("banned_words_found"):
            print(f"  BANNED WORDS: {ea['banned_words_found']}")


def print_summary(all_results: list, configs: list, total_time: float):
    """Print aggregated summary across all 10 tests."""
    print(f"\n\n{'#'*100}")
    print(f"  AGGREGATE SUMMARY — 10-ARTICLE GENERATION AUDIT")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f}min)")
    print(f"{'#'*100}")

    # Success rates
    gen_success = sum(1 for r in all_results if r["phases"].get("generation", {}).get("success"))
    enrich_success = sum(1 for r in all_results if r["phases"].get("enrichment", {}).get("success"))
    verif_success = sum(1 for r in all_results if r["phases"].get("verification", {}).get("success"))
    ql_passed = sum(1 for r in all_results if r["quality_loop"].get("quality_loop_passed"))
    ql_needed = sum(1 for r in all_results if r["quality_loop"].get("quality_loop_attempts", 0) > 0)

    print(f"\n  PIPELINE SUCCESS RATES:")
    print(f"  Enrichment:    {enrich_success}/10")
    print(f"  Generation:    {gen_success}/10")
    print(f"  Verification:  {verif_success}/10")
    print(f"  Quality Loop:  {ql_passed}/10 passed ({ql_needed} needed correction)")

    # Publication status breakdown
    statuses = {}
    for r in all_results:
        s = r.get("publication_status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1
    print(f"\n  PUBLICATION STATUS:")
    for s, count in sorted(statuses.items(), key=lambda x: str(x[0])):
        print(f"    {s.upper()}: {count}")

    # Verification metrics (averages)
    confidences = [r["phases"]["verification"]["confidence_score"]
                   for r in all_results if r["phases"].get("verification", {}).get("success")]
    if confidences:
        print(f"\n  VERIFICATION METRICS (avg across successful):")
        print(f"    Avg confidence: {sum(confidences)/len(confidences):.2f}")

        total_claims = sum(r["phases"]["verification"]["total_claims"] for r in all_results if r["phases"].get("verification", {}).get("success"))
        grounded = sum(r["phases"]["verification"]["grounded_claims"] for r in all_results if r["phases"].get("verification", {}).get("success"))
        fabricated = sum(r["phases"]["verification"]["fabricated_claims"] for r in all_results if r["phases"].get("verification", {}).get("success"))
        unverif = sum(r["phases"]["verification"]["unverifiable_claims"] for r in all_results if r["phases"].get("verification", {}).get("success"))

        print(f"    Total claims: {total_claims}")
        print(f"    Grounded: {grounded} ({grounded/total_claims*100:.0f}%)" if total_claims else "")
        print(f"    Fabricated: {fabricated} ({fabricated/total_claims*100:.0f}%)" if total_claims else "")
        print(f"    Unverifiable: {unverif} ({unverif/total_claims*100:.0f}%)" if total_claims else "")

    # Risk level breakdown
    risks = {}
    for r in all_results:
        v = r["phases"].get("verification", {})
        if v.get("success"):
            rl = v.get("risk_level", "unknown")
            risks[rl] = risks.get(rl, 0) + 1
    if risks:
        print(f"    Risk levels: {dict(sorted(risks.items()))}")

    # Editorial audit summary
    editorial_checks = []
    for r in all_results:
        ea = r.get("editorial_audit", {})
        if ea:
            passed = sum(1 for k, v in ea.items() if k.endswith("_ok") and v)
            total = sum(1 for k in ea.keys() if k.endswith("_ok"))
            editorial_checks.append((passed, total))
    if editorial_checks:
        total_passed = sum(p for p, _ in editorial_checks)
        total_checks = sum(t for _, t in editorial_checks)
        print(f"\n  EDITORIAL STANDARDS:")
        print(f"    Overall: {total_passed}/{total_checks} ({total_passed/total_checks*100:.0f}%)")

    # Timing
    durations = [r["total_duration_ms"] for r in all_results]
    gen_durations = [r["phases"]["generation"]["duration_ms"] for r in all_results if r["phases"].get("generation", {}).get("success")]
    if durations:
        print(f"\n  TIMING:")
        print(f"    Avg pipeline: {sum(durations)/len(durations)/1000:.1f}s")
        print(f"    Min/Max pipeline: {min(durations)/1000:.1f}s / {max(durations)/1000:.1f}s")
    if gen_durations:
        print(f"    Avg generation: {sum(gen_durations)/len(gen_durations)/1000:.1f}s")

    # Category breakdown
    print(f"\n  CATEGORY BREAKDOWN:")
    for i, (r, c) in enumerate(zip(all_results, configs)):
        v = r["phases"].get("verification", {})
        ea = r.get("editorial_audit", {})
        conf = v.get("confidence_score", 0) if v.get("success") else 0
        risk = v.get("risk_level", "?") if v.get("success") else "?"
        status = r.get("publication_status", "?")
        duration = r["total_duration_ms"] / 1000
        editorial_rate = ea.get("pass_rate", "?")
        print(f"    #{i+1} [{c['category']:15s}] conf={conf:.2f} risk={risk:4s} status={status:15s} editorial={editorial_rate} ({duration:.1f}s)")


async def main():
    print(f"\n{'='*100}")
    print(f"  TMC 10-ARTICLE GENERATION AUDIT")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print(f"  Testing full pipeline: Enrichment -> Generation -> Decontamination -> Verification -> Quality Loop -> Safety")
    print(f"{'='*100}\n")

    # Fetch articles
    print("[1/3] Fetching 10 diverse test articles from database...")
    test_cases = await fetch_test_articles()

    if len(test_cases) < 10:
        print(f"[WARNING] Only found {len(test_cases)} articles (need 10). Adjusting test count.")

    # Ensure configs match available articles
    configs = TEST_CONFIGS[:len(test_cases)]

    # Run pipeline for each
    print(f"\n[2/3] Running full pipeline on {len(test_cases)} articles...\n")
    all_results = []
    total_start = time.time()

    for i, (test_case, config) in enumerate(zip(test_cases, configs)):
        print(f"\n--- Starting Test #{i+1}/10: [{config['category']}] {test_case['title'][:60]}... ---")
        try:
            result = await run_full_pipeline(test_case, config)
            all_results.append(result)
            print_report(i, result, config)
        except Exception as e:
            print(f"  [FATAL ERROR] Test #{i+1} failed: {e}")
            all_results.append({
                "test_case": {"title": test_case["title"], "source_category": test_case["category"],
                              "editorial_config": config, "content_length": test_case["content_length"],
                              "source": test_case["source"]},
                "phases": {}, "quality_loop": {}, "safety_gates": {},
                "editorial_audit": {}, "publication_status": "error",
                "errors": [str(e)], "total_duration_ms": 0,
            })

    total_time = time.time() - total_start

    # Summary
    print_summary(all_results, configs, total_time)

    # Save results
    print(f"\n[3/3] Saving results...")
    output_path = Path(__file__).parent / f"test_10_articles_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "audit_type": "10_article_generation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_duration_s": total_time,
            "configs": configs,
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"[OK] Results saved to {output_path}")

    # Return exit code based on results
    blocked = sum(1 for r in all_results if r.get("publication_status") == "blocked")
    errors = sum(1 for r in all_results if r.get("publication_status") == "error")
    if errors > 3:
        print(f"\n[FAIL] {errors} fatal errors. Pipeline needs investigation.")
        return 1
    elif blocked > 5:
        print(f"\n[WARN] {blocked}/10 articles blocked by safety gates. Review generation quality.")
        return 1
    else:
        gen_success = sum(1 for r in all_results if r["phases"].get("generation", {}).get("success"))
        print(f"\n[OK] Audit complete: {gen_success}/10 generated, {blocked} blocked, {errors} errors")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
