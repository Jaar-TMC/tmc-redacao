"""
Test Gemini 2.5 Flash on all 3 Haiku replacement tasks:
1. Classification (article → category + tags)
2. Scoring (article → 4 editorial signals)
3. Theme naming (article titles → theme name)

Uses the same prompts as production to verify compatible output.
"""

import asyncio
import json
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "vertex-sa-key.json")
os.environ.setdefault("GCP_PROJECT_ID", "projeto-ia-tmc-redacao")
os.environ.setdefault("GCP_REGION", "us-central1")

from services.gemini_service import GeminiService

# ─── Test Data ────────────────────────────────────────────────────────
SAMPLE_ARTICLE_TITLE = "Governo anuncia pacote de R$ 50 bilhoes para infraestrutura"
SAMPLE_ARTICLE_CONTENT = (
    "O governo federal anunciou nesta quarta-feira um pacote de investimentos "
    "de R$ 50 bilhoes para infraestrutura, com foco em rodovias, ferrovias e "
    "portos. O ministro da Fazenda destacou que os recursos virao de parcerias "
    "publico-privadas e do novo marco de garantias. A expectativa e gerar "
    "200 mil empregos diretos nos proximos dois anos. Especialistas apontam "
    "que o pacote pode acelerar o crescimento do PIB em 0,5 ponto percentual."
)

SAMPLE_TITLES_FOR_THEME = [
    "Governo anuncia pacote de R$ 50 bilhoes para infraestrutura",
    "Novo PAC preve investimentos recordes em rodovias e ferrovias",
    "Ministro da Fazenda detalha plano de parcerias publico-privadas",
    "Setor de construcao civil celebra anuncio de investimentos federais",
]


# ─── Classification Test ──────────────────────────────────────────────
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

Responda APENAS com JSON válido no formato:
{"classifications": [{"id": "0", "category": "Categoria", "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]}]}"""


# ─── Scoring Test ─────────────────────────────────────────────────────
SCORING_SYSTEM = """Voce e um editor experiente de jornalismo brasileiro, especializado em avaliar a relevancia editorial de noticias.

## OS 4 SINAIS DE RELEVANCIA
1. INESPERADO - A noticia surpreende? (yes=25pts, partial=12pts, no=0pts)
2. IMPACTO - Afeta muitas pessoas? (high=30pts, medium=15pts, low=0pts)
3. BUSCA_AGORA - As pessoas vao buscar isso? (yes=25pts, maybe=12pts, no=0pts)
4. CONVERSA - As pessoas vao comentar? (yes=20pts, maybe=10pts, no=0pts)

## FORMATO DE RESPOSTA
Responda APENAS com JSON valido:
{"sinal_inesperado": "yes|partial|no", "sinal_impacto": "high|medium|low", "sinal_busca_agora": "yes|maybe|no", "sinal_conversa": "yes|maybe|no", "justificativa": "Breve explicacao"}"""


# ─── Theme Naming Test ────────────────────────────────────────────────
THEME_NAMING_SYSTEM = """Voce e um especialista em curadoria editorial.
Sua tarefa e criar um nome curto e descritivo para um agrupamento tematico de noticias.

Regras:
- Nome deve ter no maximo 50 caracteres
- Use palavras-chave que descrevam o tema principal
- Seja especifico (nao use termos genericos)
- Em portugues brasileiro, sem acentos
- Formato: substantivo + complemento"""


async def run_tests():
    svc = GeminiService(
        service_account_path=os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        project_id=os.environ["GCP_PROJECT_ID"],
        region=os.environ["GCP_REGION"],
    )

    print("=" * 60)
    print("Gemini 2.5 Flash — Task Replacement Tests")
    print("=" * 60)

    results = {"classification": False, "scoring": False, "theme_naming": False}

    # ─── Test 1: Classification ───────────────────────────────────────
    print("\n--- TEST 1: Classification ---")
    try:
        user_prompt = (
            f"Classifique os seguintes artigos:\n\n"
            f"--- ARTIGO 0:\nTítulo: {SAMPLE_ARTICLE_TITLE}\n"
            f"Conteúdo: {SAMPLE_ARTICLE_CONTENT[:500]}\n"
            f"Categoria original: Geral\n---"
        )
        resp = await svc.call_api(
            system=CLASSIFICATION_SYSTEM,
            user_content=user_prompt,
            max_tokens=1024,
            model="gemini-2.5-flash",
            task_type="classification",
        )
        # Extract JSON
        start = resp.find("{")
        end = resp.rfind("}") + 1
        data = json.loads(resp[start:end])
        cls = data["classifications"][0]
        print(f"  Category: {cls['category']}")
        print(f"  Tags:     {cls['tags']}")
        assert cls["category"] in [
            "Politica", "Economia", "Esportes", "Saude", "Educacao",
            "Tecnologia", "Meio Ambiente", "Seguranca", "Cultura",
            "Internacional", "Ciencia", "Variedades", "Transporte", "Energia",
        ], f"Invalid category: {cls['category']}"
        assert len(cls["tags"]) >= 3, f"Too few tags: {cls['tags']}"
        print("  PASS")
        results["classification"] = True
    except Exception as e:
        print(f"  FAIL: {e}")
        print(f"  Raw response: {resp[:300] if 'resp' in dir() else 'N/A'}")

    # ─── Test 2: Scoring ──────────────────────────────────────────────
    print("\n--- TEST 2: Scoring ---")
    try:
        user_prompt = (
            f"Analise o seguinte artigo e classifique usando os 4 sinais "
            f"de relevancia editorial:\n\n"
            f"## CATEGORIA\nEconomia\n\n"
            f"## TITULO\n{SAMPLE_ARTICLE_TITLE}\n\n"
            f"## CONTEUDO\n{SAMPLE_ARTICLE_CONTENT}"
        )
        resp = await svc.call_api(
            system=SCORING_SYSTEM,
            user_content=user_prompt,
            max_tokens=1024,
            model="gemini-2.5-flash",
            task_type="scoring",
        )
        start = resp.find("{")
        end = resp.rfind("}") + 1
        data = json.loads(resp[start:end])
        print(f"  inesperado:  {data['sinal_inesperado']}")
        print(f"  impacto:     {data['sinal_impacto']}")
        print(f"  busca_agora: {data['sinal_busca_agora']}")
        print(f"  conversa:    {data['sinal_conversa']}")
        print(f"  justif:      {data['justificativa'][:100]}")
        # Validate signal values
        assert data["sinal_inesperado"] in ("yes", "partial", "no")
        assert data["sinal_impacto"] in ("high", "medium", "low")
        assert data["sinal_busca_agora"] in ("yes", "maybe", "no")
        assert data["sinal_conversa"] in ("yes", "maybe", "no")
        assert len(data["justificativa"]) > 5
        print("  PASS")
        results["scoring"] = True
    except Exception as e:
        print(f"  FAIL: {e}")
        print(f"  Raw response: {resp[:300] if 'resp' in dir() else 'N/A'}")

    # ─── Test 3: Theme Naming ─────────────────────────────────────────
    print("\n--- TEST 3: Theme Naming ---")
    try:
        titles = "\n".join(f"- {t}" for t in SAMPLE_TITLES_FOR_THEME)
        user_prompt = (
            f"Analise os titulos abaixo e crie um nome para este "
            f"agrupamento tematico:\n\n{titles}\n\n"
            f"Responda APENAS com o nome do tema (maximo 50 caracteres):"
        )
        resp = await svc.call_api(
            system=THEME_NAMING_SYSTEM,
            user_content=user_prompt,
            max_tokens=100,
            model="gemini-2.5-flash",
            task_type="theme_naming",
        )
        theme_name = resp.strip().strip("\"'")[:200]
        print(f"  Theme name: '{theme_name}'")
        assert len(theme_name) > 3, "Theme name too short"
        assert len(theme_name) <= 60, f"Theme name too long: {len(theme_name)} chars"
        print("  PASS")
        results["theme_naming"] = True
    except Exception as e:
        print(f"  FAIL: {e}")
        print(f"  Raw response: {resp[:300] if 'resp' in dir() else 'N/A'}")

    # ─── Summary ──────────────────────────────────────────────────────
    await svc.close()

    print("\n" + "=" * 60)
    print("RESULTS:")
    all_pass = True
    for task, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {task:20} {status}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\nAll tests passed! Gemini 2.5 Flash is ready to replace Haiku.")
    else:
        print("\nSome tests failed. Check the output above.")

    return all_pass


if __name__ == "__main__":
    ok = asyncio.run(run_tests())
    sys.exit(0 if ok else 1)
