"""
TMC Full Pipeline Audit — Tests the COMPLETE generation pipeline including Quality Loop + Safety Gates.

Unlike test_article_quality.py (which only runs Phases 1-3), this script replicates
exactly what generate_article_handler does:
  Phase 1: Exa Enrichment
  Phase 2: LLM Generation + Temporal Decontamination
  Phase 3: Verification (claims + entities + quotes + CoVe)
  Phase 4: Quality Loop (evaluate criteria → Exa verify claims → regenerate → re-verify)
  Phase 5: Safety Gates (hard blocks + soft gates)

Usage: python scripts/full_pipeline_audit.py
"""

import os
import sys
import json
import asyncio
import time
import logging
from pathlib import Path
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
                os.environ[key] = str(value)
        print(f"[OK] Loaded {len(data.get('Values', {}))} env vars from local.settings.json")
    else:
        print("[ERROR] local.settings.json not found")
        sys.exit(1)

load_local_settings()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("full_pipeline_audit")


async def fetch_test_articles():
    """Fetch 5 diverse articles from DB (one per category)."""
    from services.database import DatabaseService
    db = DatabaseService()
    test_cases = []
    categories = ["politica", "esportes", "economia", "entretenimento", "geral"]

    for cat in categories:
        try:
            articles, count, _ = db.get_articles_with_urgency(page=1, limit=5, category=cat)
            for article in articles:
                content = article.content or article.preview or ""
                if len(content.strip()) > 150:
                    test_cases.append({
                        "title": article.title,
                        "content": content,
                        "source": getattr(article, 'source_name', 'Unknown'),
                        "category": cat,
                        "content_length": len(content),
                        "tags": (article.tags if hasattr(article, 'tags') and article.tags else []),
                    })
                    print(f"  [{cat.upper()}] {article.title[:80]}... ({len(content)} chars)")
                    break
        except Exception as e:
            print(f"  [{cat.upper()}] Error: {e}")

    return test_cases


async def run_full_pipeline(test_case: dict) -> dict:
    """
    Run the COMPLETE pipeline replicating generate_article_handler:
    Enrichment → Generation → Temporal Decontamination → Verification → Quality Loop → Safety Gates
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
    cat = test_case["category"]
    tags = test_case.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []

    result = {
        "test_case": {
            "title": test_case["title"],
            "category": cat,
            "content_length": test_case["content_length"],
            "source": test_case["source"],
        },
        "phases": {},
        "quality_loop": {},
        "safety_gates": {},
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
                "key_facts": enrichment.key_facts[:8],
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
            tom="formal" if cat in ["politica", "economia"] else "informal",
            tipo_materia="destaque",
            categoria=cat,
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
            "slug": generated.get("slug_sugerido", ""),
            "tags_count": len(generated.get("tags_sugeridas", [])),
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
                "requires_human_review": verification.requires_human_review,
                "review_reasons": verification.review_reasons,
                "warnings": verification.warnings,
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
        quality_eval = evaluate_quality_criteria(verification_data, readability)
        best_result_content = generated.get("conteudo", "")
        best_verification = dict(verification_data)
        best_failures_count = len(quality_eval["failures"])

        attempt = 0
        while not quality_eval["all_passed"] and attempt < QUALITY_LOOP_MAX_ATTEMPTS:
            attempt += 1
            quality_loop_result["quality_loop_attempts"] = attempt
            logger.info(
                f"Quality Loop attempt {attempt}/{QUALITY_LOOP_MAX_ATTEMPTS}: "
                f"failures={[f['criterion'] for f in quality_eval['failures']]}"
            )

            # Step 1a: Exa verify fabricated claims
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

            # Step 1b: Exa verify unverifiable claims (NEW — our fix)
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

            # Regenerate
            corrective_prompt = build_corrective_instructions(quality_eval["failures"], all_exa_corrections)
            try:
                regen = await llm.generate_article(
                    texto_base=test_case["content"],
                    tom="formal" if cat in ["politica", "economia"] else "informal",
                    tipo_materia="destaque",
                    categoria=cat,
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
                regen_eval = evaluate_quality_criteria(regen_verif_data, regen_readability)

                if regen_eval["all_passed"] or len(regen_eval["failures"]) < best_failures_count:
                    old_criteria = {f["criterion"] for f in quality_eval["failures"]}
                    new_criteria = {f["criterion"] for f in regen_eval["failures"]}
                    fixed = old_criteria - new_criteria
                    quality_loop_result["quality_loop_issues_fixed"].extend(list(fixed))

                    generated = regen
                    verification_data = regen_verif_data
                    readability = regen_readability
                    quality_eval = regen_eval
                    best_result_content = regen.get("conteudo", "")
                    best_verification = dict(regen_verif_data)
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

    # Store generated content for audit
    result["generated_article"] = {
        "titulo": generated.get("titulo", ""),
        "titulo_curto": generated.get("titulo_curto", ""),
        "linha_fina": generated.get("linha_fina", ""),
        "resumo": generated.get("resumo", []),
        "conteudo": generated.get("conteudo", ""),
        "slug": generated.get("slug_sugerido", ""),
        "tags": generated.get("tags_sugeridas", []),
    }

    result["total_duration_ms"] = int((time.time() - pipeline_start) * 1000)
    return result


def print_report(idx: int, r: dict):
    """Print detailed report for one article."""
    tc = r["test_case"]
    print(f"\n{'='*90}")
    print(f"  TEST #{idx+1}: [{tc['category'].upper()}] {tc['title'][:75]}")
    print(f"{'='*90}")
    print(f"  Source: {tc['source']} | {tc['content_length']} chars | Duration: {r['total_duration_ms']}ms")

    # Enrichment
    e = r["phases"].get("enrichment", {})
    if e.get("success"):
        print(f"\n  [Phase 1] Enrichment: {e['key_facts_count']} facts, {e['source_urls_count']} URLs ({e['duration_ms']}ms)")
    else:
        print(f"\n  [Phase 1] Enrichment: FAILED - {e.get('error', 'N/A')}")

    # Generation
    g = r["phases"].get("generation", {})
    if g.get("success"):
        print(f"  [Phase 2] Generation: {g['content_length']} chars ({g['duration_ms']}ms)")
        print(f"            Title: {g['titulo']}")
        print(f"            Linha fina: {g['linha_fina'][:120]}")
    else:
        print(f"  [Phase 2] Generation: FAILED - {g.get('error', 'N/A')}")
        return

    # Decontamination
    d = r["phases"].get("decontamination", {})
    if d.get("applied"):
        print(f"  [Phase 2.3] Decontamination: removed {d['chars_removed']} chars")

    # Verification
    v = r["phases"].get("verification", {})
    if v.get("success"):
        risk_map = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "CRITICAL"}
        risk = v.get("risk_level", "unknown")
        print(f"  [Phase 3] Verification: confidence={v['confidence_score']:.2f} risk={risk_map.get(risk, risk)} ({v['duration_ms']}ms)")
        print(f"            Claims: {v['total_claims']} total | {v['grounded_claims']} grounded | {v['fabricated_claims']} fabricated | {v['unverifiable_claims']} unverifiable")

        # Detail claims
        for c in v.get("claims", []):
            verdict_icon = {
                "grounded": "OK", "fabricated": "XX", "unverifiable": "??",
                "opinion": "OP", "context": "CT", "inaccurate": "!!"
            }
            print(f"            [{verdict_icon.get(c['verdict'], '  ')}] {c['text'][:100]}")
    else:
        print(f"  [Phase 3] Verification: FAILED - {v.get('error', 'N/A')}")

    # Quality Loop
    ql = r.get("quality_loop", {})
    if ql.get("quality_loop_attempts", 0) > 0:
        status = "PASSED" if ql["quality_loop_passed"] else "FAILED"
        print(f"  [Phase 4] Quality Loop: {status} after {ql['quality_loop_attempts']} attempt(s)")
        print(f"            Fixed: {ql.get('quality_loop_issues_fixed', [])}")
        print(f"            Fabricated: {ql['quality_loop_claims_confirmed']} confirmed, {ql['quality_loop_claims_corrected']} corrected, {ql['quality_loop_claims_removed']} removed")
        print(f"            Unverifiable: {ql['quality_loop_unverifiable_verified']} verified, {ql['quality_loop_unverifiable_removed']} removed")
        if ql.get("remaining_failures"):
            print(f"            Remaining: {ql['remaining_failures']}")
    else:
        if ql.get("quality_loop_passed"):
            print(f"  [Phase 4] Quality Loop: SKIPPED (all criteria passed on first try)")
        else:
            print(f"  [Phase 4] Quality Loop: NOT RUN")

    # Safety Gates
    sg = r.get("safety_gates", {})
    pub = r.get("publication_status", "unknown")
    if sg.get("publish_blocked"):
        print(f"  [Phase 5] Safety: BLOCKED - {'; '.join(sg['block_reasons'])}")
    elif sg.get("human_review_required"):
        print(f"  [Phase 5] Safety: REVIEW REQUIRED - {'; '.join(sg['review_reasons'])}")
    else:
        print(f"  [Phase 5] Safety: PASSED")
    print(f"  >>> PUBLICATION STATUS: {pub.upper()}")

    # Readability
    rd = r.get("readability", {})
    if rd:
        print(f"  Readability: Flesch={rd.get('flesch_score', 0):.1f} AvgSentLen={rd.get('avg_sentence_length', 0):.1f}")

    # Editorial Standards Check
    ga = r.get("generated_article", {})
    lf = ga.get("linha_fina", "")
    resumo = ga.get("resumo", [])
    content = ga.get("conteudo", "")
    titulo = ga.get("titulo", "")
    titulo_curto = ga.get("titulo_curto", "")

    print(f"\n  --- EDITORIAL STANDARDS AUDIT ---")
    # Titulo
    titulo_len = len(titulo)
    titulo_ok = titulo_len <= 75
    print(f"  Titulo ({titulo_len} chars): {'PASS' if titulo_ok else 'FAIL >75'} — {titulo[:80]}")

    # Titulo curto
    tc_len = len(titulo_curto)
    tc_ok = tc_len <= 70 and tc_len > 0
    print(f"  Titulo Curto ({tc_len} chars): {'PASS' if tc_ok else 'FAIL'} — {titulo_curto[:75]}")

    # Linha Fina (max 120 chars, no CTA suffix)
    lf_len = len(lf)
    lf_ok = lf_len <= 120
    cta_suffixes = ["confira.", "entenda.", "saiba mais.", "veja."]
    has_cta_suffix = any(lf.lower().rstrip().endswith(s) for s in cta_suffixes)
    print(f"  Linha Fina ({lf_len} chars): {'PASS' if lf_ok else 'FAIL >120'} | CTA suffix: {'FAIL' if has_cta_suffix else 'PASS (none)'}")
    print(f"    \"{lf[:130]}\"")

    # Resumo (4 bullet points)
    resumo_ok = isinstance(resumo, list) and len(resumo) >= 3
    print(f"  Resumo: {len(resumo)} bullet points — {'PASS' if resumo_ok else 'FAIL <3'}")
    for bp in resumo[:5]:
        print(f"    - {bp[:100]}")

    # CTA WhatsApp
    cta_text = "siga a tmc no whatsapp"
    has_cta = cta_text in content.lower()
    print(f"  CTA WhatsApp: {'PASS' if has_cta else 'FAIL (not found)'}")

    # Content preview
    if content:
        print(f"\n  --- CONTENT PREVIEW (first 400 chars) ---")
        for line in content[:400].split('\n'):
            print(f"  {line}")
        print(f"  ...")


async def main():
    print("=" * 90)
    print("  TMC FULL PIPELINE AUDIT — Quality Loop + Safety Gates + Unverifiable Fix")
    print("=" * 90)
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Fetch articles
    print("[1/3] Fetching test articles (1 per category)...")
    test_cases = await fetch_test_articles()
    print(f"\n  Found {len(test_cases)} test cases\n")

    if not test_cases:
        print("ERROR: No test articles found!")
        return

    # Run full pipeline
    print("[2/3] Running FULL pipeline for each article (this may take several minutes)...")
    all_results = []

    for i, tc in enumerate(test_cases):
        print(f"\n  --- [{i+1}/{len(test_cases)}] {tc['category'].upper()}: {tc['title'][:60]}...")
        try:
            result = await run_full_pipeline(tc)
            all_results.append(result)
        except Exception as e:
            logger.error(f"CRITICAL ERROR on {tc['title'][:40]}: {e}", exc_info=True)
            all_results.append({
                "test_case": {"title": tc["title"], "category": tc["category"],
                              "content_length": tc["content_length"], "source": tc.get("source", "?")},
                "phases": {}, "quality_loop": {}, "safety_gates": {},
                "publication_status": "error", "errors": [str(e)],
                "total_duration_ms": 0,
            })

    # Print reports
    print("\n\n" + "=" * 90)
    print("  DETAILED RESULTS")
    print("=" * 90)
    for i, r in enumerate(all_results):
        print_report(i, r)

    # Summary
    print("\n\n" + "=" * 90)
    print("  SUMMARY")
    print("=" * 90)

    total = len(all_results)
    generated_ok = sum(1 for r in all_results if r["phases"].get("generation", {}).get("success"))
    verified_ok = sum(1 for r in all_results if r["phases"].get("verification", {}).get("success"))

    statuses = {}
    for r in all_results:
        s = r.get("publication_status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1

    total_claims = sum(r["phases"].get("verification", {}).get("total_claims", 0) for r in all_results)
    grounded = sum(r["phases"].get("verification", {}).get("grounded_claims", 0) for r in all_results)
    fabricated = sum(r["phases"].get("verification", {}).get("fabricated_claims", 0) for r in all_results)
    unverifiable = sum(r["phases"].get("verification", {}).get("unverifiable_claims", 0) for r in all_results)

    confidences = [
        r["phases"].get("verification", {}).get("confidence_score", 0)
        for r in all_results if r["phases"].get("verification", {}).get("success")
    ]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0

    ql_ran = sum(1 for r in all_results if r.get("quality_loop", {}).get("quality_loop_attempts", 0) > 0)
    ql_passed = sum(1 for r in all_results if r.get("quality_loop", {}).get("quality_loop_passed"))
    unverif_verified = sum(r.get("quality_loop", {}).get("quality_loop_unverifiable_verified", 0) for r in all_results)
    unverif_removed = sum(r.get("quality_loop", {}).get("quality_loop_unverifiable_removed", 0) for r in all_results)

    print(f"\n  Articles: {total} tested | {generated_ok} generated | {verified_ok} verified")
    print(f"  Publication statuses: {statuses}")
    blocked = statuses.get("blocked", 0)
    print(f"\n  >>> {'ALL ARTICLES PUBLISHABLE' if blocked == 0 else f'{blocked} ARTICLE(S) BLOCKED'} <<<")
    print(f"\n  Claims: {total_claims} total | {grounded} grounded ({grounded/max(total_claims,1)*100:.0f}%) | {fabricated} fabricated ({fabricated/max(total_claims,1)*100:.0f}%) | {unverifiable} unverifiable ({unverifiable/max(total_claims,1)*100:.0f}%)")
    print(f"  Avg confidence: {avg_conf:.3f}")
    print(f"  Quality Loop: {ql_ran} triggered, {ql_passed}/{total} passed")
    print(f"  Unverifiable fix: {unverif_verified} verified by Exa, {unverif_removed} removed/corrected")

    # Editorial standards
    ed_lf_ok = sum(1 for r in all_results if len(r.get("generated_article", {}).get("linha_fina", "")) <= 120)
    ed_resumo_ok = sum(1 for r in all_results if len(r.get("generated_article", {}).get("resumo", [])) >= 3)
    ed_cta_ok = sum(1 for r in all_results if "siga a tmc no whatsapp" in r.get("generated_article", {}).get("conteudo", "").lower())
    ed_titulo_ok = sum(1 for r in all_results if 0 < len(r.get("generated_article", {}).get("titulo", "")) <= 75)
    ed_tc_ok = sum(1 for r in all_results if 0 < len(r.get("generated_article", {}).get("titulo_curto", "")) <= 70)

    print(f"\n  Editorial Standards:")
    print(f"    Titulo <=75 chars: {ed_titulo_ok}/{total}")
    print(f"    Titulo Curto <=70 chars: {ed_tc_ok}/{total}")
    print(f"    Linha Fina <=120 chars: {ed_lf_ok}/{total}")
    print(f"    Resumo (>=3 bullets): {ed_resumo_ok}/{total}")
    print(f"    CTA WhatsApp: {ed_cta_ok}/{total}")

    ed_all_ok = ed_lf_ok == total and ed_resumo_ok == total and ed_cta_ok == total

    # PRODUCTION READINESS VERDICT
    print(f"\n  {'='*60}")
    if blocked == 0 and fabricated == 0 and avg_conf >= 0.6 and ed_all_ok:
        print(f"  VERDICT: PRODUCTION READY")
        print(f"  All articles pass safety gates + editorial standards with high confidence.")
    elif blocked == 0 and avg_conf >= 0.5:
        print(f"  VERDICT: PRODUCTION READY (with review)")
        issues = []
        if not ed_all_ok:
            if ed_lf_ok < total: issues.append(f"Linha Fina >120 chars: {total - ed_lf_ok}")
            if ed_resumo_ok < total: issues.append(f"Missing resumo: {total - ed_resumo_ok}")
            if ed_cta_ok < total: issues.append(f"Missing CTA: {total - ed_cta_ok}")
        print(f"  All articles publishable. Issues: {', '.join(issues) if issues else 'None'}")
    else:
        print(f"  VERDICT: NEEDS IMPROVEMENT")
        issues = []
        if blocked > 0:
            issues.append(f"{blocked} article(s) blocked")
        if fabricated > 0:
            issues.append(f"{fabricated} fabricated claim(s)")
        if avg_conf < 0.5:
            issues.append(f"low avg confidence ({avg_conf:.2f})")
        if not ed_all_ok:
            if ed_lf_ok < total: issues.append(f"Linha Fina >120 chars: {total - ed_lf_ok}")
            if ed_resumo_ok < total: issues.append(f"Missing resumo: {total - ed_resumo_ok}")
            if ed_cta_ok < total: issues.append(f"Missing CTA: {total - ed_cta_ok}")
        print(f"  Issues: {', '.join(issues)}")
    print(f"  {'='*60}")

    # Save results
    output_path = Path(__file__).parent / f"full_pipeline_audit_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "summary": {
                "total": total, "generated_ok": generated_ok, "verified_ok": verified_ok,
                "publication_statuses": statuses,
                "total_claims": total_claims, "grounded": grounded,
                "fabricated": fabricated, "unverifiable": unverifiable,
                "avg_confidence": avg_conf,
                "quality_loop_triggered": ql_ran, "quality_loop_passed": ql_passed,
                "unverifiable_verified_by_exa": unverif_verified,
                "unverifiable_removed": unverif_removed,
                "editorial": {
                    "titulo_ok": ed_titulo_ok,
                    "titulo_curto_ok": ed_tc_ok,
                    "linha_fina_ok": ed_lf_ok,
                    "resumo_ok": ed_resumo_ok,
                    "cta_ok": ed_cta_ok,
                    "all_editorial_ok": ed_all_ok,
                },
            },
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n  Results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
