"""
Deep Analysis: Article Generation Quality Test

This script:
1. Fetches real articles from the TMC database
2. Generates articles using the full pipeline (enrichment + generation + verification)
3. Outputs detailed results for manual Exa cross-verification

Usage: python scripts/test_article_quality.py
"""

import os
import sys
import json
import asyncio
import time
import logging
from pathlib import Path

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def fetch_test_articles(limit=6):
    """Fetch diverse articles from DB for testing."""
    from services.database import DatabaseService
    db = DatabaseService()

    test_cases = []

    # Fetch articles with different characteristics
    categories = ["politica", "esportes", "economia", "entretenimento", "geral"]

    for cat in categories:
        try:
            articles, count, _ = db.get_articles_with_urgency(
                page=1, limit=2, category=cat
            )
            for article in articles[:1]:  # 1 per category
                content = article.content or article.preview or ""
                if len(content.strip()) > 100:
                    test_cases.append({
                        "id": str(article.id),
                        "title": article.title,
                        "content": content,
                        "source": article.source_name if hasattr(article, 'source_name') else "Unknown",
                        "category": cat,
                        "content_length": len(content),
                        "tags": article.tags if hasattr(article, 'tags') and article.tags else [],
                    })
                    print(f"  [{cat}] {article.title[:80]}... ({len(content)} chars)")
        except Exception as e:
            print(f"  [{cat}] Error fetching: {e}")

    # Also fetch a very short article to test short-source handling
    try:
        articles, _, _ = db.get_articles_with_urgency(page=1, limit=50)
        for article in articles:
            content = article.content or article.preview or ""
            if 50 < len(content.strip()) < 200:
                test_cases.append({
                    "id": str(article.id),
                    "title": article.title,
                    "content": content,
                    "source": article.source_name if hasattr(article, 'source_name') else "Unknown",
                    "category": "short_source",
                    "content_length": len(content),
                    "tags": article.tags if hasattr(article, 'tags') and article.tags else [],
                })
                print(f"  [SHORT] {article.title[:80]}... ({len(content)} chars)")
                break
    except Exception as e:
        print(f"  [SHORT] Error: {e}")

    return test_cases


async def generate_article_full_pipeline(test_case: dict) -> dict:
    """Generate article using full 3-phase pipeline."""
    from services.llm_service import get_llm_service
    from services.fact_check_service import get_fact_check_service, is_fact_check_enabled

    llm = get_llm_service()
    result = {
        "test_case": test_case,
        "phases": {},
        "generated": None,
        "errors": [],
    }

    cat = test_case["category"] if test_case["category"] != "short_source" else "geral"
    tags = test_case.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except:
            tags = []

    # Phase 1: Enrichment
    enrichment = None
    enrichment_context = None
    enrichment_key_facts = None
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
                verified_chars = enrichment.verified_chars

            result["phases"]["enrichment"] = {
                "success": enrichment.success,
                "key_facts_count": len(enrichment.key_facts),
                "source_urls_count": len(enrichment.source_urls),
                "source_urls": enrichment.source_urls[:5],
                "key_facts": enrichment.key_facts[:10],
                "verified_chars": verified_chars,
                "duration_ms": phase1_ms,
            }
        except Exception as e:
            result["phases"]["enrichment"] = {"success": False, "error": str(e)}
            result["errors"].append(f"Enrichment: {e}")

    # Phase 2: Generation
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
        )
        phase2_ms = int((time.time() - t0) * 1000)

        result["generated"] = generated
        result["phases"]["generation"] = {
            "success": True,
            "titulo": generated.get("titulo", ""),
            "linha_fina": generated.get("linha_fina", ""),
            "content_length": len(generated.get("conteudo", "")),
            "tags_count": len(generated.get("tags_sugeridas", [])),
            "duration_ms": phase2_ms,
        }
    except Exception as e:
        result["phases"]["generation"] = {"success": False, "error": str(e)}
        result["errors"].append(f"Generation: {e}")
        return result

    # Phase 3: Verification
    if is_fact_check_enabled() and result["generated"]:
        try:
            t0 = time.time()
            fact_checker = get_fact_check_service()
            verification = await fact_checker.verify_article(
                texto_base=test_case["content"],
                generated_article=generated.get("conteudo", ""),
                enrichment=enrichment,
            )
            phase3_ms = int((time.time() - t0) * 1000)

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
                    {
                        "text": c.text,
                        "verdict": c.verdict,
                        "source_evidence": c.source_evidence,
                        "category": c.category,
                    }
                    for c in verification.claims
                ],
                "entity_comparison": verification.entity_comparison,
                "quote_verification": verification.quote_verification,
                "requires_human_review": verification.requires_human_review,
                "review_reasons": verification.review_reasons,
                "warnings": verification.warnings,
                "duration_ms": phase3_ms,
            }
        except Exception as e:
            result["phases"]["verification"] = {"success": False, "error": str(e)}
            result["errors"].append(f"Verification: {e}")

    return result


def print_article_report(idx: int, result: dict):
    """Print detailed report for a single article test."""
    tc = result["test_case"]
    print(f"\n{'='*80}")
    print(f"TEST #{idx+1}: [{tc['category'].upper()}] {tc['title'][:70]}")
    print(f"{'='*80}")
    print(f"Source: {tc['source']} | Content: {tc['content_length']} chars")

    # Phase 1
    e = result["phases"].get("enrichment", {})
    if e.get("success"):
        print(f"\n[Phase 1 - Enrichment] OK ({e.get('duration_ms', 0)}ms)")
        print(f"  Key facts: {e.get('key_facts_count', 0)} | Sources: {e.get('source_urls_count', 0)} | Verified chars: {e.get('verified_chars', 0)}")
        if e.get("key_facts"):
            print("  Facts found:")
            for f in e["key_facts"][:5]:
                print(f"    - {f[:120]}")
    else:
        print(f"\n[Phase 1 - Enrichment] FAILED: {e.get('error', 'unknown')}")

    # Phase 2
    g = result["phases"].get("generation", {})
    if g.get("success"):
        print(f"\n[Phase 2 - Generation] OK ({g.get('duration_ms', 0)}ms)")
        print(f"  Title: {g.get('titulo', '')}")
        print(f"  Subtitle: {g.get('linha_fina', '')}")
        print(f"  Content: {g.get('content_length', 0)} chars | Tags: {g.get('tags_count', 0)}")
    else:
        print(f"\n[Phase 2 - Generation] FAILED: {g.get('error', 'unknown')}")

    # Phase 3
    v = result["phases"].get("verification", {})
    if v.get("success"):
        risk_emoji = {"low": "GREEN", "medium": "YELLOW", "high": "RED", "critical": "CRITICAL"}
        risk = v.get("risk_level", "unknown")
        print(f"\n[Phase 3 - Verification] OK ({v.get('duration_ms', 0)}ms)")
        print(f"  Confidence: {v.get('confidence_score', 0):.3f} | Risk: [{risk_emoji.get(risk, '?')}] {risk}")
        print(f"  Expansion ratio: {v.get('expansion_ratio', 0):.1f}x")
        print(f"  Claims: {v.get('total_claims', 0)} total | {v.get('grounded_claims', 0)} grounded | {v.get('fabricated_claims', 0)} FABRICATED | {v.get('unverifiable_claims', 0)} unverifiable")
        print(f"  Human review: {v.get('requires_human_review', True)}")

        if v.get("review_reasons"):
            print("  Review reasons:")
            for r in v["review_reasons"]:
                print(f"    ! {r}")

        if v.get("warnings"):
            print("  Warnings:")
            for w in v["warnings"]:
                print(f"    ! {w}")

        # Print fabricated claims
        fabricated = [c for c in v.get("claims", []) if c.get("verdict") == "fabricated"]
        if fabricated:
            print(f"\n  >>> FABRICATED CLAIMS ({len(fabricated)}) <<<")
            for c in fabricated:
                print(f"    CLAIM: {c['text'][:150]}")
                print(f"    EVIDENCE: {c.get('source_evidence', 'none')[:150]}")
                print()

        # Print unverifiable claims
        unverifiable = [c for c in v.get("claims", []) if c.get("verdict") == "unverifiable"]
        if unverifiable:
            print(f"\n  >>> UNVERIFIABLE CLAIMS ({len(unverifiable)}) <<<")
            for c in unverifiable[:5]:
                print(f"    CLAIM: {c['text'][:150]}")

        # Novel entities
        novel = v.get("entity_comparison", {}).get("novel_entities", [])
        if novel:
            print(f"\n  >>> NOVEL ENTITIES (not in source): {', '.join(novel[:10])}")

        # Unverified quotes
        unv_quotes = v.get("quote_verification", {}).get("unverified_quotes", [])
        if unv_quotes:
            print(f"\n  >>> UNVERIFIED QUOTES ({len(unv_quotes)}):")
            for q in unv_quotes[:3]:
                print(f"    \"{q[:100]}\"")
    else:
        print(f"\n[Phase 3 - Verification] FAILED: {v.get('error', 'unknown')}")

    # Print generated content snippet
    if result.get("generated"):
        conteudo = result["generated"].get("conteudo", "")
        print(f"\n--- GENERATED CONTENT (first 500 chars) ---")
        print(conteudo[:500])
        print("...")


async def main():
    print("=" * 80)
    print("TMC ARTICLE GENERATION - DEEP QUALITY ANALYSIS")
    print("=" * 80)
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: Fetch test articles
    print("[1/3] Fetching test articles from database...")
    test_cases = await fetch_test_articles(limit=6)
    print(f"\nFound {len(test_cases)} test cases\n")

    if not test_cases:
        print("ERROR: No test articles found!")
        return

    # Step 2: Generate articles
    print("[2/3] Running full pipeline for each article...")
    all_results = []

    for i, tc in enumerate(test_cases):
        print(f"\n--- Processing {i+1}/{len(test_cases)}: {tc['title'][:60]}...")
        try:
            result = await generate_article_full_pipeline(tc)
            all_results.append(result)
        except Exception as e:
            print(f"  CRITICAL ERROR: {e}")
            all_results.append({"test_case": tc, "phases": {}, "errors": [str(e)]})

    # Step 3: Print reports
    print("\n\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)

    for i, result in enumerate(all_results):
        print_article_report(i, result)

    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(all_results)
    successful = sum(1 for r in all_results if r["phases"].get("generation", {}).get("success"))
    verified = sum(1 for r in all_results if r["phases"].get("verification", {}).get("success"))

    total_fabricated = sum(
        r["phases"].get("verification", {}).get("fabricated_claims", 0)
        for r in all_results
    )
    total_grounded = sum(
        r["phases"].get("verification", {}).get("grounded_claims", 0)
        for r in all_results
    )
    total_unverifiable = sum(
        r["phases"].get("verification", {}).get("unverifiable_claims", 0)
        for r in all_results
    )
    total_claims = sum(
        r["phases"].get("verification", {}).get("total_claims", 0)
        for r in all_results
    )

    avg_confidence = 0
    confidence_scores = [
        r["phases"].get("verification", {}).get("confidence_score", 0)
        for r in all_results
        if r["phases"].get("verification", {}).get("success")
    ]
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

    risk_counts = {}
    for r in all_results:
        risk = r["phases"].get("verification", {}).get("risk_level", "unknown")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    print(f"\nArticles tested: {total}")
    print(f"Successfully generated: {successful}/{total}")
    print(f"Successfully verified: {verified}/{total}")
    print(f"\nClaims Analysis:")
    print(f"  Total claims: {total_claims}")
    print(f"  Grounded: {total_grounded} ({total_grounded/max(total_claims,1)*100:.0f}%)")
    print(f"  Fabricated: {total_fabricated} ({total_fabricated/max(total_claims,1)*100:.0f}%)")
    print(f"  Unverifiable: {total_unverifiable} ({total_unverifiable/max(total_claims,1)*100:.0f}%)")
    print(f"\nAverage confidence: {avg_confidence:.3f}")
    print(f"Risk levels: {risk_counts}")

    # Save full results to JSON
    output_path = Path(__file__).parent / f"quality_test_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        # Convert results to serializable format
        serializable = []
        for r in all_results:
            s = {
                "test_case": r["test_case"],
                "phases": r["phases"],
                "errors": r["errors"],
            }
            if r.get("generated"):
                s["generated"] = r["generated"]
            serializable.append(s)

        json.dump({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "summary": {
                "total": total,
                "successful": successful,
                "verified": verified,
                "total_claims": total_claims,
                "grounded_claims": total_grounded,
                "fabricated_claims": total_fabricated,
                "unverifiable_claims": total_unverifiable,
                "avg_confidence": avg_confidence,
                "risk_counts": risk_counts,
            },
            "results": serializable,
        }, f, ensure_ascii=False, indent=2)

    print(f"\nFull results saved to: {output_path}")

    # Print articles + titles for Exa verification
    print("\n\n" + "=" * 80)
    print("ARTICLES FOR INDEPENDENT EXA VERIFICATION")
    print("(Use these titles to cross-check with Exa web search)")
    print("=" * 80)

    for i, r in enumerate(all_results):
        if r.get("generated"):
            print(f"\n{i+1}. GENERATED: {r['generated'].get('titulo', 'N/A')}")
            print(f"   ORIGINAL:  {r['test_case']['title']}")
            print(f"   CATEGORY:  {r['test_case']['category']}")
            # Extract key claims for verification
            claims = r["phases"].get("verification", {}).get("claims", [])
            fabricated = [c for c in claims if c.get("verdict") == "fabricated"]
            if fabricated:
                print(f"   FABRICATED CLAIMS TO CHECK:")
                for c in fabricated:
                    print(f"     -> {c['text'][:120]}")


if __name__ == "__main__":
    asyncio.run(main())
