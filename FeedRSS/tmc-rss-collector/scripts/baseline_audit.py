"""
Baseline Quality Audit Script
Generates 5 articles (one per category) and records quality metrics.
"""

import json
import time
import requests
from datetime import datetime

API_URL = "https://tmc-redacao-api-b7h3dyaxazfvdcez.eastus2-01.azurewebsites.net/api/generate"
TIMEOUT = 120  # seconds

PAYLOADS = [
    {
        "category_label": "Economia",
        "payload": {
            "texto_base": "O Banco Central decidiu manter a taxa Selic em 13,75% ao ano pela quinta reuniao consecutiva. O Comite de Politica Monetaria (Copom) avaliou que a inflacao acumulada em 12 meses ainda esta acima da meta de 3%. Analistas do mercado financeiro preveem que o primeiro corte nos juros podera ocorrer no segundo semestre. O ministro da Fazenda defendeu uma reducao mais rapida dos juros para estimular a economia e gerar empregos.",
            "tom": "formal",
            "tipo_materia": "destaque",
            "categoria": "economia",
            "skip_enrichment": False,
            "skip_verification": False,
        }
    },
    {
        "category_label": "Esportes",
        "payload": {
            "texto_base": "O Flamengo venceu o Palmeiras por 2 a 1 no Maracana pelo Campeonato Brasileiro. Gabigol marcou os dois gols da vitoria rubro-negra, sendo o segundo nos acrescimos. O tecnico Tite elogiou a entrega dos jogadores e disse que a equipe esta evoluindo a cada partida. Com o resultado, o Flamengo assumiu a lideranca do campeonato com 45 pontos. O proximo confronto sera contra o Corinthians, fora de casa.",
            "tom": "formal",
            "tipo_materia": "destaque",
            "categoria": "esportes",
            "skip_enrichment": False,
            "skip_verification": False,
        }
    },
    {
        "category_label": "Politica",
        "payload": {
            "texto_base": "A Camara dos Deputados aprovou em primeiro turno a reforma tributaria com 375 votos favoraveis e 113 contrarios. O texto preve a unificacao de cinco impostos em dois: o IBS e a CBS. A oposicao tentou obstruir a votacao, mas nao conseguiu votos suficientes. O relator incluiu uma emenda que beneficia a Zona Franca de Manaus. O presidente do Senado afirmou que a proposta sera analisada ainda este semestre.",
            "tom": "formal",
            "tipo_materia": "destaque",
            "categoria": "politica",
            "skip_enrichment": False,
            "skip_verification": False,
        }
    },
    {
        "category_label": "Entretenimento",
        "payload": {
            "texto_base": "A cantora Anitta anunciou uma nova turne mundial que passara por 30 cidades em 15 paises. O show tera producao inspirada na cultura brasileira, com cenografia que mistura elementos do carnaval e da floresta amazonica. Os ingressos para as apresentacoes no Brasil esgotaram em menos de duas horas. A artista tambem revelou uma parceria com a Nike para uma colecao de roupas esportivas.",
            "tom": "formal",
            "tipo_materia": "destaque",
            "categoria": "entretenimento",
            "skip_enrichment": False,
            "skip_verification": False,
        }
    },
    {
        "category_label": "Geral",
        "payload": {
            "texto_base": "Uma forte tempestade atingiu a regiao metropolitana de Sao Paulo na madrugada desta quarta-feira. A Defesa Civil registrou ventos de ate 90 km/h e acumulo de 80 mm de chuva em tres horas. Pelo menos 200 mil imoveis ficaram sem energia eletrica. A prefeitura decretou estado de emergencia e abriu 15 escolas como abrigos temporarios. O transito ficou paralisado nas principais vias da cidade.",
            "tom": "formal",
            "tipo_materia": "destaque",
            "categoria": "geral",
            "skip_enrichment": False,
            "skip_verification": False,
        }
    },
]


def run_audit():
    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*80}")
    print(f"TMC Baseline Quality Audit - {timestamp}")
    print(f"{'='*80}\n")

    for i, item in enumerate(PAYLOADS, 1):
        category = item["category_label"]
        payload = item["payload"]

        print(f"[{i}/5] Generating article for category: {category}...")
        print(f"       Source text length: {len(payload['texto_base'])} chars")

        start_time = time.time()
        try:
            resp = requests.post(
                API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT,
            )
            elapsed = round(time.time() - start_time, 2)

            if resp.status_code == 200:
                data = resp.json()

                verification = data.get("verification", {})
                readability = data.get("readability", {})
                content = data.get("conteudo", "")

                record = {
                    "category": category,
                    "status_code": 200,
                    "content_length_chars": len(content),
                    "confidence_score": verification.get("confidence_score", None),
                    "risk_level": verification.get("risk_level", "unknown"),
                    "fabricated_claims": verification.get("fabricated_claims", 0),
                    "total_claims": verification.get("total_claims", 0),
                    "flesch_score": readability.get("flesch_score", None),
                    "publication_status": data.get("publication_status", "unknown"),
                    "slug_generated": "yes" if data.get("slug") else "no",
                    "publish_blocked": data.get("publish_blocked", False),
                    "human_review_required": data.get("human_review_required", False),
                    "regenerated": data.get("regenerated", False),
                    "response_time_seconds": elapsed,
                    "titulo": data.get("titulo", ""),
                    "enrichment_success": bool(
                        data.get("material_sufficiency", {}).get("verified_chars", 0)
                        > len(payload["texto_base"])
                    ),
                }

                print(f"       OK - {len(content)} chars, confidence={record['confidence_score']}, "
                      f"risk={record['risk_level']}, time={elapsed}s")
            else:
                elapsed = round(time.time() - start_time, 2)
                error_text = resp.text[:200]
                record = {
                    "category": category,
                    "status_code": resp.status_code,
                    "error": error_text,
                    "response_time_seconds": elapsed,
                    "content_length_chars": 0,
                    "confidence_score": None,
                    "risk_level": "error",
                    "fabricated_claims": 0,
                    "total_claims": 0,
                    "flesch_score": None,
                    "publication_status": "error",
                    "slug_generated": "no",
                    "publish_blocked": False,
                    "human_review_required": False,
                    "regenerated": False,
                    "enrichment_success": False,
                    "titulo": "",
                }
                print(f"       ERROR {resp.status_code}: {error_text}")

        except requests.exceptions.Timeout:
            elapsed = round(time.time() - start_time, 2)
            record = {
                "category": category,
                "status_code": 0,
                "error": f"Request timed out after {TIMEOUT}s",
                "response_time_seconds": elapsed,
                "content_length_chars": 0,
                "confidence_score": None,
                "risk_level": "timeout",
                "fabricated_claims": 0,
                "total_claims": 0,
                "flesch_score": None,
                "publication_status": "timeout",
                "slug_generated": "no",
                "publish_blocked": False,
                "human_review_required": False,
                "regenerated": False,
                "enrichment_success": False,
                "titulo": "",
            }
            print(f"       TIMEOUT after {elapsed}s")

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            record = {
                "category": category,
                "status_code": 0,
                "error": str(e)[:200],
                "response_time_seconds": elapsed,
                "content_length_chars": 0,
                "confidence_score": None,
                "risk_level": "error",
                "fabricated_claims": 0,
                "total_claims": 0,
                "flesch_score": None,
                "publication_status": "error",
                "slug_generated": "no",
                "publish_blocked": False,
                "human_review_required": False,
                "regenerated": False,
                "enrichment_success": False,
                "titulo": "",
            }
            print(f"       EXCEPTION: {e}")

        results.append(record)
        print()

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY TABLE")
    print(f"{'='*80}")
    header = f"{'Category':<16} {'Chars':>6} {'Confidence':>11} {'Risk':<14} {'Fabricated':>10} {'Flesch':>7} {'Status':<16} {'Slug':<5} {'Time(s)':>8}"
    print(header)
    print("-" * len(header))

    for r in results:
        conf = f"{r['confidence_score']:.3f}" if r['confidence_score'] is not None else "N/A"
        flesch = f"{r['flesch_score']:.1f}" if r['flesch_score'] is not None else "N/A"
        print(
            f"{r['category']:<16} "
            f"{r['content_length_chars']:>6} "
            f"{conf:>11} "
            f"{r['risk_level']:<14} "
            f"{r['fabricated_claims']:>10} "
            f"{flesch:>7} "
            f"{r['publication_status']:<16} "
            f"{r.get('slug_generated', 'no'):<5} "
            f"{r['response_time_seconds']:>8.1f}"
        )

    # Aggregate stats
    successful = [r for r in results if r["status_code"] == 200]
    if successful:
        avg_confidence = sum(r["confidence_score"] for r in successful if r["confidence_score"]) / len([r for r in successful if r["confidence_score"]]) if any(r["confidence_score"] for r in successful) else 0
        avg_time = sum(r["response_time_seconds"] for r in successful) / len(successful)
        avg_chars = sum(r["content_length_chars"] for r in successful) / len(successful)
        total_fabricated = sum(r["fabricated_claims"] for r in successful)
        blocked_count = sum(1 for r in successful if r["publish_blocked"])
        review_count = sum(1 for r in successful if r["human_review_required"])

        print(f"\n{'='*80}")
        print("AGGREGATE METRICS")
        print(f"{'='*80}")
        print(f"  Successful requests: {len(successful)}/5")
        print(f"  Average confidence:  {avg_confidence:.3f}")
        print(f"  Average time:        {avg_time:.1f}s")
        print(f"  Average content len: {avg_chars:.0f} chars")
        print(f"  Total fabricated:    {total_fabricated}")
        print(f"  Publish blocked:     {blocked_count}")
        print(f"  Human review needed: {review_count}")

    # Save results
    output = {
        "audit_type": "baseline_quality",
        "timestamp": timestamp,
        "api_endpoint": API_URL,
        "parameters": {
            "tom": "formal",
            "tipo_materia": "destaque",
            "skip_enrichment": False,
            "skip_verification": False,
        },
        "results": results,
        "aggregate": {
            "total_requests": 5,
            "successful": len(successful),
            "avg_confidence": round(avg_confidence, 4) if successful else None,
            "avg_response_time_s": round(avg_time, 2) if successful else None,
            "avg_content_length": round(avg_chars, 0) if successful else None,
            "total_fabricated_claims": total_fabricated if successful else None,
            "publish_blocked_count": blocked_count if successful else None,
            "human_review_count": review_count if successful else None,
        } if successful else {},
    }

    output_path = r"C:\Users\enzoc\OneDrive - jaarconsult.com.br\JaarConsult - Oficial - TMC\Projeto Ferramenta TMC\FeedRSS\tmc-rss-collector\scripts\baseline_audit_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_path}")
    return output


if __name__ == "__main__":
    run_audit()
