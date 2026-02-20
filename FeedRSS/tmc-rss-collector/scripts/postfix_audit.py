"""
Post-Fix Quality Audit Script
Generates 5 articles across categories and compares with baseline.
"""

import requests
import json
import time
import re
from datetime import datetime

API_URL = "https://tmc-redacao-api-b7h3dyaxazfvdcez.eastus2-01.azurewebsites.net/api/generate"
TIMEOUT = 180

BASELINE = {
    "Economia": {"chars": 2312, "confidence": 0.649, "flesch": 41.8, "fabricated": 0},
    "Esportes": {"chars": 1671, "confidence": 0.864, "flesch": 47.5, "fabricated": 0},
    "Politica": {"chars": 1407, "confidence": 0.550, "flesch": 52.2, "fabricated": 0},
    "Entretenimento": {"chars": 1907, "confidence": 0.550, "flesch": 57.9, "fabricated": 0},
    "Geral": {"chars": 1886, "confidence": 0.433, "flesch": 50.3, "fabricated": 2},
}

PAYLOADS = [
    {
        "category": "Economia",
        "payload": {
            "texto_base": "O Banco Central decidiu manter a taxa Selic em 13,75% ao ano pela quinta reuniao consecutiva. O Comite de Politica Monetaria (Copom) avaliou que a inflacao acumulada em 12 meses ainda esta acima da meta de 3%. Analistas do mercado financeiro preveem que o primeiro corte nos juros podera ocorrer no segundo semestre. O ministro da Fazenda defendeu uma reducao mais rapida dos juros para estimular a economia e gerar empregos.",
            "tom": "formal",
            "tipo_materia": "destaque"
        }
    },
    {
        "category": "Esportes",
        "payload": {
            "texto_base": "O Flamengo venceu o Palmeiras por 2 a 1 no Maracana pelo Campeonato Brasileiro. Gabigol marcou os dois gols da vitoria rubro-negra, sendo o segundo nos acrescimos. O tecnico Tite elogiou a entrega dos jogadores e disse que a equipe esta evoluindo a cada partida. Com o resultado, o Flamengo assumiu a lideranca do campeonato com 45 pontos. O proximo confronto sera contra o Corinthians, fora de casa.",
            "tom": "formal",
            "tipo_materia": "destaque"
        }
    },
    {
        "category": "Politica",
        "payload": {
            "texto_base": "A Camara dos Deputados aprovou em primeiro turno a reforma tributaria com 375 votos favoraveis e 113 contrarios. O texto preve a unificacao de cinco impostos em dois: o IBS e a CBS. A oposicao tentou obstruir a votacao, mas nao conseguiu votos suficientes. O relator incluiu uma emenda que beneficia a Zona Franca de Manaus. O presidente do Senado afirmou que a proposta sera analisada ainda este semestre.",
            "tom": "formal",
            "tipo_materia": "destaque"
        }
    },
    {
        "category": "Entretenimento",
        "payload": {
            "texto_base": "A cantora Anitta anunciou uma nova turne mundial que passara por 30 cidades em 15 paises. O show tera producao inspirada na cultura brasileira, com cenografia que mistura elementos do carnaval e da floresta amazonica. Os ingressos para as apresentacoes no Brasil esgotaram em menos de duas horas. A artista tambem revelou uma parceria com a Nike para uma colecao de roupas esportivas.",
            "tom": "formal",
            "tipo_materia": "destaque"
        }
    },
    {
        "category": "Geral",
        "payload": {
            "texto_base": "Uma forte tempestade atingiu a regiao metropolitana de Sao Paulo na madrugada desta quarta-feira. A Defesa Civil registrou ventos de ate 90 km/h e acumulo de 80 mm de chuva em tres horas. Pelo menos 200 mil imoveis ficaram sem energia eletrica. A prefeitura decretou estado de emergencia e abriu 15 escolas como abrigos temporarios. O transito ficou paralisado nas principais vias da cidade.",
            "tom": "formal",
            "tipo_materia": "destaque"
        }
    }
]


def extract_metrics(category, response_json, elapsed_seconds):
    """Extract all metrics from the API response."""
    result = {
        "category": category,
        "response_time_seconds": round(elapsed_seconds, 1),
        "http_status": "200",
        "error": None,
        "raw_keys": list(response_json.keys()),
    }

    # Content - API returns "conteudo" (not "materia")
    conteudo = response_json.get("conteudo", "")
    result["content_length"] = len(conteudo) if conteudo else 0
    result["titulo"] = response_json.get("titulo", None)
    result["linha_fina"] = response_json.get("linha_fina", None)

    # Confidence & risk - API returns "verification" (not "verificacao")
    verification = response_json.get("verification", {})
    if not isinstance(verification, dict):
        verification = {}
    result["confidence"] = verification.get("confidence_score", None)
    result["risk_level"] = verification.get("risk_level", None)

    # Fabricated claims
    fab_claims = verification.get("fabricated_claims", [])
    if isinstance(fab_claims, list):
        result["fabricated_claims_count"] = len(fab_claims)
    elif isinstance(fab_claims, int):
        result["fabricated_claims_count"] = fab_claims
        fab_claims = []
    else:
        result["fabricated_claims_count"] = 0
        fab_claims = []
    result["fabricated_claims"] = fab_claims

    # Readability
    readability = response_json.get("readability", {})
    if not isinstance(readability, dict):
        readability = {}
    result["flesch_score"] = readability.get("flesch_score", None)
    result["avg_sentence_length"] = readability.get("avg_sentence_length", None)

    # Publication status
    result["publication_status"] = response_json.get("publication_status", None)

    # Slug - API returns "slug_sugerido"
    slug_val = response_json.get("slug_sugerido", None)
    result["slug_present"] = slug_val is not None and slug_val != ""
    result["slug_value"] = slug_val

    # Schema.org
    schema = response_json.get("schema_org", None)
    result["schema_org_present"] = schema is not None and schema != {} and schema != ""
    result["schema_org"] = schema

    # Tipo materia
    result["tipo_materia"] = response_json.get("tipo_materia", None)

    # Tags
    result["tags"] = response_json.get("tags_sugeridas", [])

    return result


def run_audit():
    results = []
    print("=" * 80)
    print(f"POST-FIX QUALITY AUDIT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    for i, item in enumerate(PAYLOADS):
        cat = item["category"]
        payload = item["payload"]
        print(f"\n[{i+1}/5] Generating: {cat}...")
        print(f"  Payload size: {len(payload['texto_base'])} chars")

        start = time.time()
        try:
            resp = requests.post(API_URL, json=payload, timeout=TIMEOUT)
            elapsed = time.time() - start
            print(f"  HTTP {resp.status_code} in {elapsed:.1f}s")

            if resp.status_code == 200:
                data = resp.json()
                metrics = extract_metrics(cat, data, elapsed)
                print(f"  Title: {metrics.get('titulo', 'N/A')}")
                print(f"  Content: {metrics['content_length']} chars")
                print(f"  Confidence: {metrics['confidence']}")
                print(f"  Risk: {metrics['risk_level']}")
                print(f"  Fabricated: {metrics['fabricated_claims_count']}")
                print(f"  Flesch: {metrics['flesch_score']}")
                print(f"  Avg Sentence Length: {metrics['avg_sentence_length']}")
                print(f"  Slug: {'Yes' if metrics['slug_present'] else 'No'} -> {metrics['slug_value']}")
                print(f"  Schema.org: {'Yes' if metrics['schema_org_present'] else 'No'}")
                print(f"  Status: {metrics['publication_status']}")
                print(f"  Response keys: {metrics.get('raw_keys', [])}")
                results.append(metrics)
            else:
                elapsed = time.time() - start
                error_text = resp.text[:500]
                print(f"  ERROR: {error_text}")
                results.append({
                    "category": cat,
                    "http_status": str(resp.status_code),
                    "error": error_text,
                    "response_time_seconds": round(elapsed, 1),
                    "content_length": 0,
                    "confidence": None,
                    "risk_level": None,
                    "fabricated_claims_count": None,
                    "flesch_score": None,
                    "avg_sentence_length": None,
                    "publication_status": None,
                    "slug_present": False,
                    "slug_value": None,
                    "schema_org_present": False,
                    "schema_org": None,
                })
        except requests.exceptions.Timeout:
            elapsed = time.time() - start
            print(f"  TIMEOUT after {elapsed:.1f}s")
            results.append({
                "category": cat,
                "http_status": "TIMEOUT",
                "error": f"Timeout after {elapsed:.1f}s",
                "response_time_seconds": round(elapsed, 1),
                "content_length": 0,
                "confidence": None,
                "risk_level": None,
                "fabricated_claims_count": None,
                "flesch_score": None,
                "avg_sentence_length": None,
                "publication_status": None,
                "slug_present": False,
                "slug_value": None,
                "schema_org_present": False,
                "schema_org": None,
            })
        except Exception as e:
            elapsed = time.time() - start
            print(f"  EXCEPTION: {e}")
            results.append({
                "category": cat,
                "http_status": "ERROR",
                "error": str(e),
                "response_time_seconds": round(elapsed, 1),
                "content_length": 0,
                "confidence": None,
                "risk_level": None,
                "fabricated_claims_count": None,
                "flesch_score": None,
                "avg_sentence_length": None,
                "publication_status": None,
                "slug_present": False,
                "slug_value": None,
                "schema_org_present": False,
                "schema_org": None,
            })

    # Print comparison table
    print("\n")
    print("=" * 120)
    print("COMPARISON TABLE: BASELINE vs POST-FIX")
    print("=" * 120)

    header = f"{'Category':<16} | {'BL Chars':>8} {'PF Chars':>8} {'Delta':>7} | {'BL Conf':>7} {'PF Conf':>7} {'Delta':>7} | {'BL Flesch':>9} {'PF Flesch':>9} {'Delta':>7} | {'BL Fab':>6} {'PF Fab':>6} | {'Slug':>5} {'Schema':>7} | {'Time':>6}"
    print(header)
    print("-" * 130)

    for r in results:
        cat = r["category"]
        bl = BASELINE.get(cat, {})

        bl_chars = bl.get("chars", "N/A")
        pf_chars = r.get("content_length", 0) or "N/A"
        delta_chars = ""
        if isinstance(bl_chars, (int, float)) and isinstance(pf_chars, (int, float)):
            d = pf_chars - bl_chars
            delta_chars = f"{d:+d}"

        bl_conf = bl.get("confidence", "N/A")
        pf_conf = r.get("confidence") if r.get("confidence") is not None else "N/A"
        delta_conf = ""
        if isinstance(bl_conf, (int, float)) and isinstance(pf_conf, (int, float)):
            d = pf_conf - bl_conf
            delta_conf = f"{d:+.3f}"

        bl_flesch = bl.get("flesch", "N/A")
        pf_flesch = r.get("flesch_score") if r.get("flesch_score") is not None else "N/A"
        delta_flesch = ""
        if isinstance(bl_flesch, (int, float)) and isinstance(pf_flesch, (int, float)):
            d = pf_flesch - bl_flesch
            delta_flesch = f"{d:+.1f}"

        bl_fab = bl.get("fabricated", "N/A")
        pf_fab = r.get("fabricated_claims_count") if r.get("fabricated_claims_count") is not None else "N/A"

        slug = "Yes" if r.get("slug_present") else "No"
        schema = "Yes" if r.get("schema_org_present") else "No"
        time_s = f"{r.get('response_time_seconds', 'N/A')}s"

        # Convert all to str to avoid format issues
        print(f"{cat:<16} | {str(bl_chars):>8} {str(pf_chars):>8} {str(delta_chars):>7} | {str(bl_conf):>7} {str(pf_conf):>7} {str(delta_conf):>7} | {str(bl_flesch):>9} {str(pf_flesch):>9} {str(delta_flesch):>7} | {str(bl_fab):>6} {str(pf_fab):>6} | {slug:>5} {schema:>7} | {time_s:>6}")

    print("-" * 120)

    # Summary
    print("\nSUMMARY:")
    successful = [r for r in results if r.get("http_status") == "200"]
    failed = [r for r in results if r.get("http_status") != "200"]
    print(f"  Successful: {len(successful)}/5")
    print(f"  Failed: {len(failed)}/5")

    if successful:
        avg_chars = sum(r["content_length"] for r in successful) / len(successful)
        confs = [r["confidence"] for r in successful if r["confidence"] is not None]
        avg_conf = sum(confs) / len(confs) if confs else 0
        fleschs = [r["flesch_score"] for r in successful if r["flesch_score"] is not None]
        avg_flesch = sum(fleschs) / len(fleschs) if fleschs else 0
        total_fab = sum(r["fabricated_claims_count"] for r in successful if r["fabricated_claims_count"] is not None)
        slugs = sum(1 for r in successful if r.get("slug_present"))
        schemas = sum(1 for r in successful if r.get("schema_org_present"))
        avg_time = sum(r["response_time_seconds"] for r in successful) / len(successful)

        print(f"  Avg content length: {avg_chars:.0f} chars")
        print(f"  Avg confidence: {avg_conf:.3f}")
        print(f"  Avg Flesch score: {avg_flesch:.1f}")
        print(f"  Total fabricated claims: {total_fab}")
        print(f"  Slugs present: {slugs}/{len(successful)}")
        print(f"  Schema.org present: {schemas}/{len(successful)}")
        print(f"  Avg response time: {avg_time:.1f}s")

        # Baseline averages
        bl_avg_chars = sum(v["chars"] for v in BASELINE.values()) / len(BASELINE)
        bl_avg_conf = sum(v["confidence"] for v in BASELINE.values()) / len(BASELINE)
        bl_avg_flesch = sum(v["flesch"] for v in BASELINE.values()) / len(BASELINE)
        bl_total_fab = sum(v["fabricated"] for v in BASELINE.values())

        print(f"\n  BASELINE Averages: {bl_avg_chars:.0f} chars, {bl_avg_conf:.3f} conf, {bl_avg_flesch:.1f} flesch, {bl_total_fab} fab")
        print(f"  POSTFIX  Averages: {avg_chars:.0f} chars, {avg_conf:.3f} conf, {avg_flesch:.1f} flesch, {total_fab} fab")
        print(f"  DELTAS:            {avg_chars - bl_avg_chars:+.0f} chars, {avg_conf - bl_avg_conf:+.3f} conf, {avg_flesch - bl_avg_flesch:+.1f} flesch, {total_fab - bl_total_fab:+d} fab")

    # Save results
    output = {
        "audit_type": "post-fix",
        "timestamp": datetime.now().isoformat(),
        "api_endpoint": API_URL,
        "baseline": BASELINE,
        "results": results,
        "summary": {
            "successful": len(successful),
            "failed": len(failed),
            "avg_content_length": round(avg_chars, 0) if successful else None,
            "avg_confidence": round(avg_conf, 3) if successful else None,
            "avg_flesch": round(avg_flesch, 1) if successful else None,
            "total_fabricated": total_fab if successful else None,
            "slugs_present": slugs if successful else None,
            "schemas_present": schemas if successful else None,
            "avg_response_time": round(avg_time, 1) if successful else None,
        }
    }

    output_path = r"C:\Users\enzoc\OneDrive - jaarconsult.com.br\JaarConsult - Oficial - TMC\Projeto Ferramenta TMC\FeedRSS\tmc-rss-collector\scripts\postfix_audit_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    run_audit()
