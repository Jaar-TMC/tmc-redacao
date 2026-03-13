"""
Quality test: Gemini 2.5 Flash on diverse real-world articles.
Tests classification accuracy, scoring consistency, and theme naming quality.
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "vertex-sa-key.json")
os.environ.setdefault("GCP_PROJECT_ID", "projeto-ia-tmc-redacao")
os.environ.setdefault("GCP_REGION", "us-central1")

from services.gemini_service import GeminiService

# ─── Diverse Test Articles ────────────────────────────────────────────
ARTICLES = [
    {
        "id": "1",
        "title": "STF decide que redes sociais devem remover conteudo ilegal em 24 horas",
        "content": "O Supremo Tribunal Federal decidiu por 8 votos a 3 que plataformas digitais como Instagram, X e TikTok devem remover conteudos ilegais em ate 24 horas apos notificacao judicial. A decisao estabelece um novo marco regulatorio para a internet no Brasil. Ministros destacaram que a medida equilibra liberdade de expressao com protecao de direitos fundamentais. Empresas de tecnologia criticaram o prazo considerado curto.",
        "expected_category": "Politica",
        "original_category": "Geral",
    },
    {
        "id": "2",
        "title": "Corinthians vence Palmeiras por 3 a 1 no Derby e assume lideranca do Brasileirao",
        "content": "O Corinthians goleou o Palmeiras por 3 a 1 na Neo Quimica Arena em partida valida pela 10a rodada do Campeonato Brasileiro. Yuri Alberto marcou dois gols e Memphis Depay completou o placar. Com o resultado, o Timao assume a lideranca com 25 pontos, dois a frente do Flamengo. O tecnico Ramón Diaz celebrou a atuacao coletiva.",
        "expected_category": "Esportes",
        "original_category": "Esportes",
    },
    {
        "id": "3",
        "title": "Novo antibiotico brasileiro mostra 95% de eficacia contra superbacterias",
        "content": "Pesquisadores da USP e da Fiocruz desenvolveram um antibiotico inedito que demonstrou 95% de eficacia contra superbacterias resistentes em ensaios clinicos de fase 2. A molecula, derivada de compostos da Mata Atlantica, ataca um mecanismo unico da parede celular bacteriana. O estudo foi publicado na Nature Medicine e pode revolucionar o tratamento de infeccoes hospitalares. A ANVISA deve avaliar o pedido de uso emergencial em 2027.",
        "expected_category": "Saude",
        "original_category": "Ciencia",
    },
    {
        "id": "4",
        "title": "Dolar fecha a R$ 5,82 apos Copom elevar Selic para 15,25% ao ano",
        "content": "O dolar comercial recuou 1,2% e fechou cotado a R$ 5,82 nesta quarta-feira, apos o Comite de Politica Monetaria do Banco Central elevar a taxa Selic em 0,50 ponto percentual, para 15,25% ao ano. A decisao veio em linha com as expectativas do mercado. Analistas do Itau BBA projetam que o ciclo de alta deve se encerrar em junho, com a Selic em 15,75%. A Bolsa de Valores fechou em alta de 0,8%.",
        "expected_category": "Economia",
        "original_category": "Economia",
    },
    {
        "id": "5",
        "title": "Incendio de grandes proporcoes atinge favela em Sao Paulo e deixa 200 desabrigados",
        "content": "Um incendio de grandes proporcoes atingiu a comunidade de Paraisopolis, zona sul de Sao Paulo, na madrugada desta quinta-feira. O Corpo de Bombeiros mobilizou 15 viaturas e levou 4 horas para controlar as chamas. Pelo menos 200 pessoas ficaram desabrigadas e 3 foram hospitalizadas com queimaduras leves. A Defesa Civil investiga as causas. A prefeitura montou abrigos emergenciais em escolas da regiao.",
        "expected_category": "Seguranca",
        "original_category": "Cidades",
    },
    {
        "id": "6",
        "title": "Brasil lanca satelite de monitoramento ambiental em parceria com a NASA",
        "content": "O Brasil lancou com sucesso o satelite Amazonia-2, desenvolvido em parceria com a NASA e o INPE, para monitoramento em tempo real do desmatamento na Amazonia. O equipamento usa sensores de radar que funcionam mesmo sob cobertura de nuvens, superando limitacoes dos sistemas anteriores. O lancamento ocorreu na base de Alcantara, no Maranhao, marcando o retorno do programa espacial brasileiro apos 5 anos.",
        "expected_category": "Meio Ambiente",
        "original_category": "Tecnologia",
    },
    {
        "id": "7",
        "title": "MEC anuncia programa de bolsas integrais para cursos de inteligencia artificial",
        "content": "O Ministerio da Educacao lancou o programa IA Brasil, que oferecera 50 mil bolsas integrais para cursos de graduacao e pos-graduacao em inteligencia artificial. As bolsas cobrirao mensalidades em universidades publicas e privadas credenciadas. O programa prioriza estudantes de baixa renda e moradores de regioes Norte e Nordeste. As inscricoes abrem em julho pelo portal do MEC.",
        "expected_category": "Educacao",
        "original_category": "Geral",
    },
    {
        "id": "8",
        "title": "Apple anuncia chip M5 Ultra com desempenho 3x superior ao M4 para Macs",
        "content": "A Apple apresentou nesta segunda-feira o chip M5 Ultra, prometendo desempenho ate 3 vezes superior ao M4 em tarefas de machine learning e edicao de video. O novo processador sera utilizado nos Mac Studio e Mac Pro com lancamento previsto para setembro. O chip conta com 80 nucleos de GPU e 128 GB de memoria unificada. Analistas da Bloomberg estimam que o produto deve impulsionar as vendas de Macs em 20%.",
        "expected_category": "Tecnologia",
        "original_category": "Tecnologia",
    },
]

# ─── Prompts (same as production) ─────────────────────────────────────
CLASSIFICATION_SYSTEM = """Você é um especialista em classificação de conteúdo jornalístico e SEO.
Sua tarefa é analisar artigos de notícias e:
1. Classificar cada artigo em UMA categoria válida
2. Gerar 5-8 tags SEO relevantes para cada artigo

## CATEGORIAS VÁLIDAS
- Politica
- Economia
- Esportes
- Saude
- Educacao
- Tecnologia
- Meio Ambiente
- Seguranca
- Cultura
- Internacional
- Ciencia
- Variedades
- Transporte
- Energia

## REGRAS PARA TAGS
- Tags em português, sem acentos, minúsculas
- Termos pesquisáveis e relevantes para SEO
- Incluir nomes próprios quando relevante
- Gerar entre 5 e 8 tags

Responda APENAS com JSON valido puro (sem markdown, sem backticks, sem explicacao):
{"classifications": [{"id": "0", "category": "Categoria", "tags": ["tag1", "tag2"]}]}"""

SCORING_SYSTEM = """Voce e um editor experiente de jornalismo brasileiro, especializado em avaliar a relevancia editorial de noticias.

## OS 4 SINAIS DE RELEVANCIA
1. INESPERADO - A noticia surpreende o leitor mediano? (yes=25pts, partial=12pts, no=0pts)
2. IMPACTO - Afeta muitas pessoas diretamente? (high=30pts, medium=15pts, low=0pts)
3. BUSCA_AGORA - As pessoas vao buscar isso no Google agora? (yes=25pts, maybe=12pts, no=0pts)
4. CONVERSA - As pessoas vao comentar isso no almoco/redes sociais? (yes=20pts, maybe=10pts, no=0pts)

## FORMATO DE RESPOSTA
Responda APENAS com JSON valido:
{"sinal_inesperado": "yes|partial|no", "sinal_impacto": "high|medium|low", "sinal_busca_agora": "yes|maybe|no", "sinal_conversa": "yes|maybe|no", "justificativa": "Breve explicacao em 1-2 frases"}
NAO use markdown. NAO use backticks. Apenas JSON puro."""

THEME_NAMING_SYSTEM = """Voce e um especialista em curadoria editorial.
Sua tarefa e criar um nome curto e descritivo para um agrupamento tematico de noticias.

Regras:
- Nome deve ter no maximo 50 caracteres
- Use palavras-chave que descrevam o tema principal
- Seja especifico (nao use termos genericos como 'noticias do dia')
- Em portugues brasileiro, sem acentos
- Formato: substantivo + complemento (ex: 'Crise no transporte publico de SP')"""

def extract_json(text: str) -> dict:
    """Extract and parse JSON from LLM response, with basic repair."""
    import re
    # Strip markdown code fences first
    cleaned = re.sub(r'```json\s*', '', text)
    cleaned = re.sub(r'```\s*', '', cleaned)
    cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start < 0 or end <= 0:
        raise ValueError(f"No JSON found in: {text[:200]}")
    raw = cleaned[start:end]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try fixing common issues: trailing commas
        fixed = re.sub(r',\s*}', '}', raw)
        fixed = re.sub(r',\s*]', ']', fixed)
        return json.loads(fixed)


VALID_CATEGORIES = {
    "Politica", "Economia", "Esportes", "Saude", "Educacao",
    "Tecnologia", "Meio Ambiente", "Seguranca", "Cultura",
    "Internacional", "Ciencia", "Variedades", "Transporte", "Energia",
}

SIGNAL_VALUES = {
    "sinal_inesperado": {"yes", "partial", "no"},
    "sinal_impacto": {"high", "medium", "low"},
    "sinal_busca_agora": {"yes", "maybe", "no"},
    "sinal_conversa": {"yes", "maybe", "no"},
}

POINT_MAP = {
    "sinal_inesperado": {"yes": 25, "partial": 12, "no": 0},
    "sinal_impacto": {"high": 30, "medium": 15, "low": 0},
    "sinal_busca_agora": {"yes": 25, "maybe": 12, "no": 0},
    "sinal_conversa": {"yes": 20, "maybe": 10, "no": 0},
}


def compute_score(signals: dict) -> int:
    total = 0
    for sig, val_map in POINT_MAP.items():
        total += val_map.get(signals.get(sig, "no"), 0)
    return total


def classify_score(score: int) -> str:
    if score >= 75:
        return "A"
    elif score >= 35:
        return "B"
    return "C"


async def run_quality_test():
    svc = GeminiService(
        service_account_path=os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        project_id=os.environ["GCP_PROJECT_ID"],
        region=os.environ["GCP_REGION"],
    )

    print("=" * 70)
    print("QUALITY TEST: Gemini 2.5 Flash — 8 Diverse Articles")
    print("=" * 70)

    # ─── Test 1: BATCH Classification ─────────────────────────────────
    print("\n" + "=" * 70)
    print("TEST 1: CLASSIFICATION (batch of 8 articles)")
    print("=" * 70)

    batch_prompt = "Classifique os seguintes artigos:\n\n"
    for a in ARTICLES:
        batch_prompt += (
            f"--- ARTIGO {a['id']}:\n"
            f"Título: {a['title']}\n"
            f"Conteúdo: {a['content'][:500]}\n"
            f"Categoria original: {a['original_category']}\n---\n\n"
        )

    t0 = time.time()
    resp = await svc.call_api(
        system=CLASSIFICATION_SYSTEM,
        user_content=batch_prompt,
        max_tokens=2048,
        model="gemini-2.5-flash",
        task_type="classification",
    )
    cls_time = time.time() - t0

    try:
        cls_data = extract_json(resp)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        print(f"  Raw response (first 600 chars):\n{resp[:600]}")
        cls_data = {"classifications": []}

    correct = 0
    total = len(ARTICLES)
    print(f"\n{'ID':>3} {'Expected':>15} {'Got':>15} {'Match':>6} Tags")
    print("-" * 70)
    for cls in cls_data["classifications"]:
        art = next((a for a in ARTICLES if str(a["id"]) == str(cls["id"])), None)
        if not art:
            continue
        expected = art["expected_category"]
        got = cls["category"]
        match = got == expected
        if match:
            correct += 1
        tags_str = ", ".join(cls["tags"][:5])
        valid = got in VALID_CATEGORIES
        flag = "OK" if match else ("~" if valid else "BAD")
        print(f"{cls['id']:>3} {expected:>15} {got:>15} {flag:>6} [{tags_str}]")

    accuracy = correct / total * 100
    print(f"\nAccuracy: {correct}/{total} ({accuracy:.0f}%) in {cls_time:.1f}s")

    # ─── Test 2: SCORING (each article individually) ──────────────────
    print("\n" + "=" * 70)
    print("TEST 2: SCORING (8 articles individually)")
    print("=" * 70)

    scoring_results = []
    total_score_time = 0

    for art in ARTICLES:
        user_prompt = (
            f"Analise o seguinte artigo e classifique usando os 4 sinais "
            f"de relevancia editorial:\n\n"
            f"## CATEGORIA\n{art['expected_category']}\n\n"
            f"## TITULO\n{art['title']}\n\n"
            f"## CONTEUDO\n{art['content']}"
        )
        t0 = time.time()
        resp = await svc.call_api(
            system=SCORING_SYSTEM,
            user_content=user_prompt,
            max_tokens=1024,
            model="gemini-2.5-flash",
            task_type="scoring",
        )
        elapsed = time.time() - t0
        total_score_time += elapsed

        try:
            data = extract_json(resp)
        except json.JSONDecodeError:
            print(f"  JSON error for article {art['id']}: {resp[:200]}")
            continue

        score = compute_score(data)
        grade = classify_score(score)

        # Validate signals
        valid = all(
            data.get(sig) in vals
            for sig, vals in SIGNAL_VALUES.items()
        )

        scoring_results.append({
            "id": art["id"],
            "title": art["title"][:50],
            "score": score,
            "grade": grade,
            "signals": data,
            "valid": valid,
            "time": elapsed,
        })

    print(f"\n{'ID':>3} {'Grade':>5} {'Score':>5} {'Inesp':>7} {'Impac':>7} {'Busca':>7} {'Conv':>7} {'Valid':>5} Title")
    print("-" * 100)
    for r in scoring_results:
        s = r["signals"]
        print(
            f"{r['id']:>3} {r['grade']:>5} {r['score']:>5} "
            f"{s['sinal_inesperado']:>7} {s['sinal_impacto']:>7} "
            f"{s['sinal_busca_agora']:>7} {s['sinal_conversa']:>7} "
            f"{'OK' if r['valid'] else 'BAD':>5} {r['title']}"
        )

    all_valid = all(r["valid"] for r in scoring_results)
    scores = [r["score"] for r in scoring_results]
    grades = [r["grade"] for r in scoring_results]
    print(f"\nAll signals valid: {all_valid}")
    print(f"Score range: {min(scores)}-{max(scores)}")
    print(f"Grade distribution: A={grades.count('A')} B={grades.count('B')} C={grades.count('C')}")
    print(f"Total time: {total_score_time:.1f}s (avg {total_score_time/len(ARTICLES):.1f}s/article)")

    # ─── Test 3: THEME NAMING ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("TEST 3: THEME NAMING (3 theme groups)")
    print("=" * 70)

    theme_groups = [
        {
            "name": "Politics/Tech regulation",
            "titles": [ARTICLES[0]["title"], "Senado debate nova lei de regulacao de redes sociais", "Governo cria comite para fiscalizar plataformas digitais"],
        },
        {
            "name": "Economy/Selic",
            "titles": [ARTICLES[3]["title"], "Mercado reage a alta da Selic com otimismo moderado", "Inflacao de alimentos pressiona decisao do Copom"],
        },
        {
            "name": "Science/Environment",
            "titles": [ARTICLES[2]["title"], ARTICLES[5]["title"], "Pesquisadores mapeiam 500 novas especies na Amazonia"],
        },
    ]

    for group in theme_groups:
        titles = "\n".join(f"- {t}" for t in group["titles"])
        user_prompt = (
            f"Analise os titulos abaixo e crie um nome para este "
            f"agrupamento tematico:\n\n{titles}\n\n"
            f"Responda APENAS com o nome do tema (maximo 50 caracteres):"
        )
        t0 = time.time()
        resp = await svc.call_api(
            system=THEME_NAMING_SYSTEM,
            user_content=user_prompt,
            max_tokens=100,
            model="gemini-2.5-flash",
            task_type="theme_naming",
        )
        elapsed = time.time() - t0
        theme_name = resp.strip().strip("\"'")[:200]
        chars = len(theme_name)
        ok = 3 < chars <= 50
        print(f"  [{group['name']:25}] -> '{theme_name}' ({chars} chars, {elapsed:.1f}s) {'OK' if ok else 'TOO LONG/SHORT'}")

    # ─── Summary ──────────────────────────────────────────────────────
    await svc.close()

    print("\n" + "=" * 70)
    print("QUALITY SUMMARY")
    print("=" * 70)
    print(f"  Classification: {correct}/{total} correct ({accuracy:.0f}%)")
    print(f"  Scoring: {'All valid' if all_valid else 'SOME INVALID'} | Range {min(scores)}-{max(scores)} | A:{grades.count('A')} B:{grades.count('B')} C:{grades.count('C')}")
    print(f"  Theme naming: See above")

    if accuracy >= 75 and all_valid:
        print("\n  VERDICT: Gemini 2.5 Flash quality is ACCEPTABLE for production")
    else:
        print("\n  VERDICT: Quality issues detected - review before deploying")


if __name__ == "__main__":
    asyncio.run(run_quality_test())
