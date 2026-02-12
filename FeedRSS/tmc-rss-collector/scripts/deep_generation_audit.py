"""
Deep Article Generation Quality Audit
Runs comprehensive tests against the live API across:
- Single article generation (multiple categories, types, tones)
- Combined article generation (merge-topics endpoint)
- Edge cases (short content, forced nota, opinion mode)

Usage:
  python scripts/deep_generation_audit.py --suite single
  python scripts/deep_generation_audit.py --suite combined
  python scripts/deep_generation_audit.py --suite edge
  python scripts/deep_generation_audit.py --suite all
"""

import argparse
import json
import os
import sys
import time
import requests
from datetime import datetime

API_BASE = "https://tmc-redacao-api-b7h3dyaxazfvdcez.eastus2-01.azurewebsites.net/api"
TIMEOUT = 120  # seconds per request

# ─── Test Article Content ───────────────────────────────────────────────

ARTICLES = {
    "economia_opep": {
        "id": "927aa45b-3407-48ca-8712-4a7a57ef69e1",
        "title": "Opep mantém projeção de produção de combustíveis líquidos no Brasil em 2026",
        "source": "CNN Brasil",
        "content": """A Organização dos Países Exportadores de Petróleo (Opep) manteve a projeção para a produção brasileira de combustíveis líquidos em 2026, estimando que a oferta total do país, incluindo biocombustíveis, crescerá 160 mil barris por dia (bpd), para uma média de 4,6 milhões de bpd, segundo relatório mensal divulgado nesta quarta-feira (11). No ano passado, a produção brasileira de líquidos aumentou cerca de 240 mil bpd, para a média de 4,4 milhões de bpd, estima a Opep. De acordo com a Opep, a produção de petróleo bruto subiu cerca de 239 mil bpd em dezembro, para uma média de 4 milhões de bpd, após uma recuperação da interrupção observada em novembro, enquanto a de líquidos de gás natural (NGLs) permaneceu "amplamente inalterada" e "praticamente estável", em cerca de 95 mil bpd. É estimado que a produção de biocombustíveis, principalmente etanol, tenha caído 10 mil bpd em comparação com o mês anterior, para uma média de 700 mil bpd, com dados preliminares de janeiro indicando uma tendência estável. O relatório informa que, em dezembro, a produção total de líquidos do Brasil subiu cerca de 20 mil bpd na comparação mensal, para uma média de 4,8 milhões de bpd, o que representa um aumento de 600 mil bpd em relação ao ano anterior. Para 2027, a Opep manteve a projeção para a produção brasileira de combustíveis líquidos e reafirmou a expectativa de que a produção aumente em cerca de 140 mil bpd na comparação anual, para uma média de 4,7 milhões de bpd. Segundo o relatório, a produção upstream deve aumentar com a expansão nos projetos Búzios (Franco), Bacalhau, Marlim e Wahoo, além do início das operações no campo de Búzios e no Cluster Pampo-Enchova. No cenário macroeconômico, a Opep reafirmou a projeção de crescimento do Produto Interno Bruto (PIB) do Brasil em 2% em 2026. Além disso, indicou aceleração para 2,2% em 2027, afirmando que, para o próximo ano, é esperado que o crescimento econômico continue aumentando, apoiado pela flexibilização monetária e pela continuidade da forte atividade doméstica.""",
    },
    "politica_flavio": {
        "id": "ea5df9ad-89ad-45da-9771-2b8c58f24368",
        "title": "Flávio nega racha com Tarcísio e Michelle e fala em 'desavença zero'",
        "source": "CNN Brasil",
        "content": """O senador Flávio Bolsonaro (PL), pré-candidato à Presidência da República, negou nesta quarta-feira (11), uma eventual desavença com o governador de São Paulo, Tarcísio de Freitas (Republicanos) e também com a ex-primeira-dama, Michelle Bolsonaro (PL) no contexto da escolha do seu nome para a eleição deste ano. "Da minha parte é desavença zero [com Tarcísio ou Michelle]. Meu nome está colocado, e todos pediam que o presidente escolhesse o nome, e ele escolheu. Agora a poeira já baixou", disse em entrevista durante o evento CEO Conference, do BTG Pactual. O senador reforçou que Tarcísio já manifestou publicamente o apoio à sua candidatura: "ele já manifestou que está com a gente, e eu nunca duvidei que estivesse". Na entrevista, Flávio afirmou que estará com o governador na próxima quinta-feira. "O Tarcísio, como sempre falei, eu sempre tive relação direta e transparente. Sou fã dele, acho que faz um baita governo em São Paulo. E tenho certeza que vai entrar de cabeça. Estarei com ele na próxima quinta-feira e estaremos mais alinhados que nunca", acrescentou. No caso de Michelle Bolsonaro, o senador disse ter muito "respeito" pela esposa do pai. Sobre ela entrar também para o mundo público da política na eleição, Flávio disse ter dúvidas ainda, mas que assim que tiver "oportunidade", para que os dois se "empenhem neste processo". "Com relação à Michelle tenho um grande respeito. Assim que tiver oportunidade estarei com ela, para pedir que a gente se empenhe neste processo, que não é do Flávio, mas do Brasil".""",
    },
    "internacional_suica": {
        "id": "aab1f357-b490-4407-9d85-0ae4350f7e92",
        "title": "Suíça vota em junho proposta que limita população a 10 milhões de habitantes",
        "source": "InfoMoney",
        "content": """Os suíços decidirão em junho se 10 milhões de habitantes é o máximo que o país comporta. A proposta — apoiada pelo Partido do Povo Suíço (SVP), de direita — irá a voto nacional depois que os defensores reuniram assinaturas suficientes, dentro do sistema de democracia direta da Suíça. Tanto o governo quanto o Parlamento são contra a chamada "iniciativa da sustentabilidade", que pretende limitar a população, praticamente barrando a imigração quando o número de 10 milhões for atingido. Ainda assim, a proposta tinha o apoio de cerca de 48% dos eleitores, segundo pesquisa de dezembro. A votação será em 14 de junho, anunciou o governo nesta quarta-feira. A população da Suíça cresceu cerca de 70% desde 1960, chegando a 9,1 milhões de habitantes, impulsionada sobretudo pela demanda por mão de obra e pela atração de altos salários e qualidade de vida. Os defensores da restrição argumentam que a imigração sem controle levou à sobrecarga da infraestrutura e à escassez de moradias. A iniciativa é especialmente controversa porque afetaria o acordo de livre circulação da Suíça com a União Europeia. Isso poderia cortar o acesso das empresas a talentos estrangeiros — considerados essenciais por muitos — e também ameaçar outros tratados conectados, que garantem aos exportadores suíços acesso ao mercado único do bloco. Parte do apoio elevado nas pesquisas reflete frustração econômica, especialmente com moradia e outros custos, combinada com sentimento anti-imigração no país. "O PIB per capita não cresceu nos últimos três anos e os salários reais caíram", disse Stefan Legge, professor da Universidade de St. Gallen. "Muita gente está em situação pior agora do que há três anos. E então você procura alguém para culpar." """,
    },
    "saude_smart": {
        "id": "926bc0ad-9238-4f67-a4e8-8db3748e1fd0",
        "title": "Smart 2.0 amplia opções no monitoramento contínuo de glicose",
        "source": "CNN Brasil",
        "content": """O monitoramento contínuo da glicose deixou de ser uma novidade e passou a integrar a rotina de quem convive com o diabetes. Nos últimos anos, diferentes sensores chegaram ao mercado com propostas variadas, ligadas ao tempo de uso, ao modo de leitura e ao nível de conforto no dia a dia. Com o lançamento do Smart 2.0, esse cenário ganha mais uma opção e amplia as escolhas disponíveis no país. Desenvolvido pela MedLevensohn, o Smart 2.0 entra nesse mercado com um sensor integrado em peça única, sem transmissor separado. O dispositivo realiza leituras automáticas da glicose a cada cinco minutos e envia os dados diretamente para o celular. Além disso, o modelo pode ser utilizado por até 15 dias consecutivos e permite aplicação no braço ou no abdômen, o que contribui para uma experiência mais discreta. Uma das principais diferenças entre os sensores de glicose está no modo de acesso às informações. Alguns modelos exigem a aproximação do celular ou de um leitor para visualizar os dados. Outros, como o Smart 2.0, fazem a transmissão automática via bluetooth, o que facilita o acompanhamento contínuo, inclusive durante a noite ou em atividades físicas. O tempo de uso também é um fator relevante na comparação. Enquanto parte dos sensores disponíveis funciona por cerca de 14 dias ou menos, o Smart 2.0 oferece autonomia de até 15 dias, reduzindo a necessidade de trocas frequentes. A presença de alarmes para episódios de hipo e hiperglicemia é outro ponto de atenção, já que esse recurso não está disponível em todos os modelos. Nesse contexto, o Smart 2.0 se posiciona como uma alternativa que reúne atributos buscados por usuários desse tipo de tecnologia, como leitura automática, autonomia estendida, alertas configuráveis e design integrado mais discreto.""",
    },
    "economia_selic": {
        "id": "0cbb7b74-f67b-42f8-9f0e-1333f1776223",
        "title": "Selic está pronta para cair de forma sustentável, diz presidente do BNDES",
        "source": "CNN Brasil",
        "content": """O presidente do BNDES (Banco Nacional de Desenvolvimento Econômico e Social), Aloizio Mercadante, defendeu a queda dos juros como forma de destravar investimentos em infraestrutura. A fala ocorreu na cerimônia de lançamento do Plano de Investimentos em Ampliação e Modernização de Aeroportos realizado nesta quarta-feira (11) no Palácio do Planalto, em Brasília. "A taxa Selic tem dificultado o investimento e penalizado empresas brasileiras. Por isso, os juros estão prontos para cair de forma sustentável e espero que acelerada para destravarmos investimentos no Brasil", afirmou Mercadante. O presidente do BNDES disse que pela percepção, inclusive do próprio Copom, as taxas de juros devem entrar em trajetória de queda. Após listar investimentos do atual governo em diferentes segmentos de infraestrutura, apesar dos juros elevados, Mercadante finalizou o discurso com um aceno ao presidente da República, Luiz Inácio Lula da Silva. O petista também estava presente no evento, mas não discursou. "Tem gente que acha que Brasil precisa de CEO, mas precisa de estadista. O Brasil precisa do Lula, como a África do Sul precisava do Mandela e a Índia, do Gandhi", afirmou Mercadante.""",
    },
    "tecnologia_sony": {
        "id": "530b65f0-300f-4e12-af71-9b38ccba9afe",
        "title": "Sony encerra a produção de gravadores de Blu-ray",
        "source": "TecMundo",
        "content": """A Sony anunciou na segunda-feira (9) sua saída do mercado de gravadores de Blu-ray, encerrando a produção do equipamento que ainda é comercializado no Japão. As últimas unidades serão entregues até o final de fevereiro. No início do ano passado, a gigante japonesa deixou de produzir os discos de Blu-ray graváveis destinados aos clientes corporativos, depois de aproximadamente 20 anos. Antes disso, em 2024, ela havia parado a produção da mídia física fornecida aos usuários domésticos. A Sony decidiu finalizar a produção dos aparelhos de gravação de discos Blu-ray por causa do streaming. Com a ampla oferta de conteúdos online, os consumidores têm se afastado cada vez mais das mídias físicas. No Japão, onde a marca continua a comercializar o produto, as vendas de gravadores Blu-ray atingiram pico de 6,39 milhões de unidades em 2011. Já no ano passado, as remessas do dispositivo caíram para apenas 620 mil aparelhos, menos de 10% do que há 15 anos. Essa queda brusca teria relação com a enorme adesão aos serviços de streaming, que permitem visualizar conteúdos em qualquer lugar. Dessa forma, a Sony vem reduzindo seus negócios de hardware ao longo dos anos. No mês passado, a big tech anunciou parceria com a TCL para a sua divisão de TVs, com a marca chinesa assumindo a produção dos televisores Bravia. Como parte da estratégia de acelerar sua expansão, a marca agora tem focado na área de entretenimento, concentrando esforços na produção de filmes e animes. Games e música são outros segmentos para os quais ela tem se voltado. Apesar do fim da produção dos dispositivos utilizados para a gravação de programas de TV, a Sony vai continuar fabricando os reprodutores de Blu-ray.""",
    },
    "politica_kim": {
        "id": "ccd3f8b6-61a9-4531-81c4-7358e5a08429",
        "title": "Influenciador é condenado a pagar R$ 20 mil a Kim Kataguiri",
        "source": "G1 - Principal",
        "content": """O Tribunal de Justiça de São Paulo (TJSP) condenou um influenciador depois de ele chamar o deputado federal Kim Kataguiri (União-SP) de "neonazista", "lixo humano" e "katabosta" nas redes sociais. Thiago dos Reis Pereira dos Santos, dono do canal "Plantão Brasil" no YouTube, terá que indenizar o parlamentar em R$ 20 mil por danos morais. Em nota ao g1, a defesa de Kataguiri criticou a associação do parlamentar com o nazismo: "em uma democracia, divergências ideológicas e críticas são normais e desejáveis. No presente caso, porém, foram proferidos xingamentos e feitas associações ligando o deputado ao nazismo, ideologia nefasta que, felizmente, é banida no Brasil. Qualquer pessoa que associe o deputado à ideologia nazista será responsabilizada." Reis tentou recorrer da decisão, mas o pedido foi negado em segunda instância pela 4ª Câmara de Direito Privado do TJSP. A defesa do influenciador argumentou que os termos usados por ele eram críticas e que Thiago estava exercendo seu direito à liberdade de expressão. O Tribunal, por outro lado, afirmou que as expressões ultrapassam a liberdade de expressão e que ofenderam a honra e a imagem do deputado. A defesa de Thiago também pediu a redução do valor da indenização, mas o TJSP manteve a quantia em R$ 20 mil. A justificativa é que o valor está equilibrado e é proporcional ao caso.""",
    },
    "economia_kraft": {
        "id": "69925a1a-b9f9-43c6-a02b-4c8ab4d9b11d",
        "title": "Kraft Heinz desiste de dividir empresa em duas",
        "source": "Folha - Mercado",
        "content": """A Kraft Heinz suspendeu a cisão da companhia em duas empresas separadas, abandonando um plano de desfazer a megafusão orquestrada por Warren Buffett e a 3G Capital há uma década. A decisão foi anunciada pelo novo CEO da empresa, Steve Cahillane, que assumiu o posto em dezembro do ano passado.""",
    },
    # Combined test articles
    "carnaval": {
        "id": "57a924fb-ecb1-45ea-9213-51d89ac49cb3",
        "title": "Carnaval 2026: veja as ruas interditadas em Campo Grande",
        "source": "G1 - Principal",
        "content": """A Agência Municipal de Transporte e Trânsito (Agetran) divulgou o cronograma de interdições para o Carnaval 2026 em Campo Grande. As mudanças começam no dia 11 de fevereiro e seguem até 21 de fevereiro. O objetivo é garantir a segurança de motoristas e foliões durante os desfiles e blocos em diferentes pontos da cidade. As interdições vão ocorrer principalmente nas regiões da Praça do Papa, Avenida Calógeras, Avenida Mato Grosso e ruas do Centro. A orientação é que os condutores fiquem atentos à sinalização provisória e sigam as orientações dos agentes de trânsito. Desfile das Escolas de Samba: Ensaios técnicos nos dias 11 e 12 de fevereiro, desfile oficial 16 e 17 de fevereiro, na Praça do Papa a partir das 19h. Blocos: Bloco Reggae (13-14/fev), Farofolia (13/fev), Só Love (13/fev), Cordão Valu (14 e 17/fev), Ipa Lelê (14-16/fev), Capivara Blasé (15-16/fev), Forrozeiros MS (21/fev), Eita (21/fev), Barra da Saia (16/fev), Subaquera (16/fev). Apuração das notas em 18 de fevereiro no Teatro de Arena do Horto Florestal.""",
    },
    "verao_clima": {
        "id": "5d8dbdd9-50ff-4dc0-aeed-fc70a2da5cf8",
        "title": "Verão no Clima chega a Mongaguá com shows e educação ambiental",
        "source": "G1 - Principal",
        "content": """Mongaguá será palco de mais uma etapa do projeto Verão no Clima no dia 14 de fevereiro, trazendo para a Avenida Governador Mário Covas Júnior, no Balneário Itaguaí, um centro de educação ambiental e cultura. O evento acontecerá ao lado da tradicional Plataforma de Pesca, um dos pontos mais emblemáticos da cidade, oferecendo uma programação que combina consciência ambiental com entretenimento de qualidade. As atividades começam às 8h30 com um mutirão de educação ambiental de 30 minutos. A partir das 9h, tem início a Arena Cultural, que funcionará até às 17h. O evento se destaca pela variedade de atividades físicas e culturais, começando com alongamento, seguido por ballet para crianças. A programação inclui aulas de dança, ritmos diversos e jazz na praia. O encerramento musical ficará por conta da Banda Celeste Campanari e da Banda Mangará, que trará o forró. O evento contará com organizações especializadas em preservação ambiental: Coopermar (coleta seletiva), Formiguinhas da Praia (limpeza de praias), Grupo de Escoteiros do Mar de Mongaguá e CREA/AMEA (sustentabilidade urbana). Destaque para a Sereia Blue com contação de histórias sobre lixo no mar. A tenda do Governo de São Paulo junto a Cetesb oferecerá informações sobre políticas públicas ambientais. A Sabesp realizará ativação sobre saneamento básico. A Circular Brain estará presente com experiências de educação ambiental e coleta de eletrônicos.""",
    },
    "construtora": {
        "id": "d0ae3ab8-0045-40ca-8bc4-a3eb4b85846a",
        "title": "Construtora é condenada a pagar R$ 1,5 milhão por danos morais após morte de funcionário",
        "source": "G1 - Principal",
        "content": """Uma construtora foi condenada, nesta segunda-feira (9), a pagar R$ 1,5 milhão de indenização por danos morais coletivos após um funcionário morrer enquanto trabalhava em obra de condomínio de luxo, em Jundiaí (SP). O acidente aconteceu em junho de 2023. A vítima foi atingida por uma caçamba com mais de uma tonelada de pedrisco que despencou de uma altura de dez metros. As investigações apontaram falhas na manutenção da caçamba, como a barra de suporte que não suportava o peso da carga. A indenização será revertida a entidades públicas de assistência social indicadas pelo Ministério Público do Trabalho. A Justiça também determinou que o grupo cumpra imediatamente 14 medidas de segurança em todas as obras. Caso as medidas não sejam cumpridas, a empresa será multada diariamente em R$ 50 mil. O Grupo Santa Ângela, a companhia condenada, informou que deverá se pronunciar.""",
    },
}


# ─── Test Definitions ───────────────────────────────────────────────────

SINGLE_TESTS = [
    {
        "name": "S1: Economia (destaque) - OPEP produção Brasil",
        "article_key": "economia_opep",
        "params": {"categoria": "economia", "tom": "formal", "tipo_materia": "destaque"},
    },
    {
        "name": "S2: Política (destaque) - Flávio Bolsonaro",
        "article_key": "politica_flavio",
        "params": {"categoria": "politica", "tom": "analitico", "tipo_materia": "destaque"},
    },
    {
        "name": "S3: Geral/Internacional (análise) - Suíça imigração",
        "article_key": "internacional_suica",
        "params": {"categoria": "geral", "tom": "conversacional", "tipo_materia": "analise"},
    },
    {
        "name": "S4: Geral/Saúde (destaque) - Smart 2.0 glicose",
        "article_key": "saude_smart",
        "params": {"categoria": "geral", "tom": "conversacional", "tipo_materia": "destaque"},
    },
    {
        "name": "S5: Economia (destaque) - Selic BNDES",
        "article_key": "economia_selic",
        "params": {"categoria": "economia", "tom": "didatico", "tipo_materia": "destaque"},
    },
    {
        "name": "S6: Geral/Tecnologia (coluna opinativa) - Sony Blu-ray",
        "article_key": "tecnologia_sony",
        "params": {"categoria": "entretenimento", "tom": "critico", "tipo_materia": "coluna", "modo_opinativo": True},
    },
    {
        "name": "S7: Política (destaque) - Kim Kataguiri processo",
        "article_key": "politica_kim",
        "params": {"categoria": "politica", "tom": "objetivo", "tipo_materia": "destaque"},
    },
]

COMBINED_TESTS = [
    {
        "name": "C1: Eventos regionais (Carnaval + Verão no Clima)",
        "articles": ["carnaval", "verao_clima"],
    },
    {
        "name": "C2: Justiça/Condenações (Construtora + Influenciador)",
        "articles": ["construtora", "politica_kim"],
    },
]

EDGE_TESTS = [
    {
        "name": "E1: Short content (324 chars) - forced nota",
        "article_key": "economia_kraft",
        "params": {"categoria": "economia", "tom": "formal", "tipo_materia": "destaque"},
    },
    {
        "name": "E2: Esportes informal tone (reusing Flávio as proxy for esportes test)",
        "article_key": "politica_flavio",
        "params": {"categoria": "esportes", "tom": "informal", "tipo_materia": "destaque"},
    },
]


# ─── API Helpers ────────────────────────────────────────────────────────

def call_generate(article_key, extra_params=None):
    """Call /api/generate with a single article."""
    article = ARTICLES[article_key]
    payload = {
        "texto_base": article["content"],
        "titulo_fonte": article["title"],
        "tags": [],
    }
    if extra_params:
        payload.update(extra_params)

    start = time.time()
    try:
        resp = requests.post(f"{API_BASE}/generate", json=payload, timeout=TIMEOUT)
        elapsed_ms = int((time.time() - start) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            data["_meta"] = {
                "http_status": 200,
                "elapsed_ms": elapsed_ms,
                "article_key": article_key,
                "source_chars": len(article["content"]),
            }
            return data
        else:
            return {
                "_meta": {
                    "http_status": resp.status_code,
                    "elapsed_ms": elapsed_ms,
                    "article_key": article_key,
                    "error": resp.text[:500],
                }
            }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "_meta": {
                "http_status": 0,
                "elapsed_ms": elapsed_ms,
                "article_key": article_key,
                "error": str(e),
            }
        }


def call_merge_topics(article_keys):
    """Call /api/merge-topics with multiple articles."""
    articles_payload = []
    for key in article_keys:
        article = ARTICLES[key]
        articles_payload.append({
            "id": article["id"],
            "title": article["title"],
            "source": article["source"],
            "content": article["content"],
        })

    start = time.time()
    try:
        resp = requests.post(
            f"{API_BASE}/merge-topics",
            json={"articles": articles_payload},
            timeout=TIMEOUT,
        )
        elapsed_ms = int((time.time() - start) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            data["_meta"] = {
                "http_status": 200,
                "elapsed_ms": elapsed_ms,
                "article_keys": article_keys,
            }
            return data
        else:
            return {
                "_meta": {
                    "http_status": resp.status_code,
                    "elapsed_ms": elapsed_ms,
                    "article_keys": article_keys,
                    "error": resp.text[:500],
                }
            }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "_meta": {
                "http_status": 0,
                "elapsed_ms": elapsed_ms,
                "article_keys": article_keys,
                "error": str(e),
            }
        }


# ─── Metric Extraction ─────────────────────────────────────────────────

def extract_metrics(result, test_name):
    """Extract standardized metrics from a generation result."""
    meta = result.get("_meta", {})
    if meta.get("http_status") != 200:
        return {
            "test": test_name,
            "status": "FAILED",
            "http_status": meta.get("http_status"),
            "error": meta.get("error", "unknown"),
            "elapsed_ms": meta.get("elapsed_ms", 0),
        }

    verification = result.get("verification", {}) or {}
    readability = result.get("readability", {}) or {}
    sufficiency = result.get("material_sufficiency", {}) or {}

    titulo = result.get("titulo", "")
    conteudo = result.get("conteudo", "")
    linha_fina = result.get("linha_fina", "")

    content_chars = len(conteudo)
    content_words = len(conteudo.split()) if conteudo else 0
    titulo_words = len(titulo.split()) if titulo else 0

    return {
        "test": test_name,
        "status": "OK",
        "http_status": 200,
        "elapsed_ms": meta.get("elapsed_ms", 0),
        "source_chars": meta.get("source_chars", 0),
        # Content quality
        "titulo": titulo,
        "titulo_words": titulo_words,
        "titulo_chars": len(titulo),
        "linha_fina": linha_fina,
        "linha_fina_chars": len(linha_fina) if linha_fina else 0,
        "content_chars": content_chars,
        "content_words": content_words,
        # Verification
        "confidence": verification.get("confidence_score", None),
        "risk_level": verification.get("risk_level", None),
        "fabricated_claims": verification.get("fabricated_claims", None),
        "unverifiable_claims": verification.get("unverifiable_claims", None),
        "total_claims": verification.get("total_claims", None),
        "expansion_ratio": verification.get("expansion_ratio", None),
        "novel_entities": len((verification.get("entity_comparison", {}) or {}).get("novel_entities", [])),
        # Readability
        "flesch_score": readability.get("flesch_score", None),
        "grade_level": readability.get("grade_level", None),
        "readability_words": readability.get("words", None),
        # Safety gates
        "publish_blocked": result.get("publish_blocked", False),
        "block_reason": result.get("block_reason", None),
        "human_review_required": result.get("human_review_required", False),
        "review_reasons": result.get("review_reasons", []),
        "publication_status": result.get("publication_status", None),
        # SEO / Structured data
        "has_schema_org": result.get("schema_org") is not None or result.get("structured_data") is not None,
        "has_slug": result.get("slug_sugerido") is not None and len(result.get("slug_sugerido", "")) > 0,
        "slug": result.get("slug_sugerido", ""),
        "tags_count": len(result.get("tags_sugeridas", [])),
        # Pipeline features
        "enrichment_degraded": result.get("enrichment_degraded", False),
        "regenerated": result.get("regenerated", False),
        "nota_forced": result.get("nota_forced", False),
        "sensitive_topics": result.get("sensitive_topics_detected", False),
        "correlation_id": result.get("correlation_id", None),
        # AI disclosure
        "has_ai_disclosure": result.get("ai_disclosure") is not None,
    }


def extract_merge_metrics(result, test_name):
    """Extract metrics from a merge-topics result."""
    meta = result.get("_meta", {})
    if meta.get("http_status") != 200:
        return {
            "test": test_name,
            "status": "FAILED",
            "http_status": meta.get("http_status"),
            "error": meta.get("error", "unknown"),
            "elapsed_ms": meta.get("elapsed_ms", 0),
        }

    groups = result.get("groups", [])
    exclusives = result.get("exclusives", [])
    quotes = result.get("quotes", [])
    summary = result.get("summary", "")

    return {
        "test": test_name,
        "status": "OK",
        "http_status": 200,
        "elapsed_ms": meta.get("elapsed_ms", 0),
        "num_groups": len(groups),
        "num_exclusives": len(exclusives),
        "num_quotes": len(quotes),
        "has_summary": len(summary) > 0 if summary else False,
        "summary_chars": len(summary) if summary else 0,
        "group_details": [
            {
                "id": g.get("id"),
                "label": g.get("label", ""),
                "num_versions": len(g.get("versions", [])),
                "recommended_version": next(
                    (v.get("id") for v in g.get("versions", []) if v.get("isRecommended")),
                    None,
                ),
            }
            for g in groups
        ],
    }


# ─── Report Generation ─────────────────────────────────────────────────

def print_single_report(metrics_list):
    """Print a formatted report for single article tests."""
    print("\n" + "=" * 80)
    print("SINGLE ARTICLE GENERATION - QUALITY REPORT")
    print("=" * 80)

    ok = [m for m in metrics_list if m["status"] == "OK"]
    failed = [m for m in metrics_list if m["status"] == "FAILED"]

    if failed:
        print(f"\n! {len(failed)} test(s) FAILED:")
        for m in failed:
            print(f"  - {m['test']}: HTTP {m['http_status']} — {m.get('error', '')[:100]}")

    if not ok:
        print("\nNo successful tests to report.")
        return

    print(f"\n[OK] {len(ok)} test(s) succeeded\n")

    # Per-test details
    for m in ok:
        blocked_str = " [BLOCKED]" if m["publish_blocked"] else ""
        review_str = " [REVIEW]" if m["human_review_required"] else ""
        regen_str = " [REGEN]" if m["regenerated"] else ""
        nota_str = " [NOTA FORCED]" if m["nota_forced"] else ""

        print(f"--- {m['test']}{blocked_str}{review_str}{regen_str}{nota_str} ---")
        print(f"  Title: {m['titulo']}")
        print(f"  Title length: {m['titulo_chars']} chars, {m['titulo_words']} words")
        print(f"  Linha fina: {m['linha_fina_chars']} chars")
        print(f"  Content: {m['content_chars']} chars, {m['content_words']} words (source: {m['source_chars']} chars)")
        print(f"  Confidence: {m['confidence']:.3f} | Risk: {m['risk_level']} | Flesch: {m['flesch_score']}")
        print(f"  Claims: {m['fabricated_claims']} fabricated / {m['unverifiable_claims']} unverifiable / {m['total_claims']} total")
        print(f"  Novel entities: {m['novel_entities']} | Expansion: {m['expansion_ratio']:.1f}x")
        print(f"  Schema.org: {'Y' if m['has_schema_org'] else 'N'} | Slug: {'Y' if m['has_slug'] else 'N'} ({m['slug'][:40]})")
        print(f"  Tags: {m['tags_count']} | AI disclosure: {'Y' if m['has_ai_disclosure'] else 'N'}")
        print(f"  Pub status: {m['publication_status']} | Latency: {m['elapsed_ms']}ms")
        if m["review_reasons"]:
            print(f"  Review reasons: {', '.join(m['review_reasons'])}")
        if m["block_reason"]:
            print(f"  Block reason: {m['block_reason']}")
        print()

    # Aggregated stats
    print("=" * 80)
    print("AGGREGATED METRICS")
    print("=" * 80)

    confs = [m["confidence"] for m in ok if m["confidence"] is not None]
    flesches = [m["flesch_score"] for m in ok if m["flesch_score"] is not None]
    lengths = [m["content_chars"] for m in ok]
    latencies = [m["elapsed_ms"] for m in ok]
    fabricated_total = sum(m["fabricated_claims"] or 0 for m in ok)
    fabrication_articles = sum(1 for m in ok if (m["fabricated_claims"] or 0) > 0)
    blocked_count = sum(1 for m in ok if m["publish_blocked"])
    review_count = sum(1 for m in ok if m["human_review_required"])
    schema_count = sum(1 for m in ok if m["has_schema_org"])
    slug_count = sum(1 for m in ok if m["has_slug"])
    regen_count = sum(1 for m in ok if m["regenerated"])
    sensitive_count = sum(1 for m in ok if m["sensitive_topics"])

    print(f"  Avg confidence:     {sum(confs)/len(confs):.3f} (min: {min(confs):.3f}, max: {max(confs):.3f})")
    print(f"  Avg Flesch:         {sum(flesches)/len(flesches):.1f} (min: {min(flesches):.1f}, max: {max(flesches):.1f})")
    print(f"  Avg content length: {sum(lengths)/len(lengths):.0f} chars (min: {min(lengths)}, max: {max(lengths)})")
    print(f"  Avg latency:        {sum(latencies)/len(latencies):.0f}ms (p95: {sorted(latencies)[int(len(latencies)*0.95)]:.0f}ms)")
    print(f"  Fabricated claims:  {fabricated_total} total across {fabrication_articles}/{len(ok)} articles ({100*fabrication_articles/len(ok):.0f}%)")
    print(f"  Blocked:            {blocked_count}/{len(ok)} ({100*blocked_count/len(ok):.0f}%)")
    print(f"  Human review:       {review_count}/{len(ok)} ({100*review_count/len(ok):.0f}%)")
    print(f"  Schema.org present: {schema_count}/{len(ok)} ({100*schema_count/len(ok):.0f}%)")
    print(f"  Slug present:       {slug_count}/{len(ok)} ({100*slug_count/len(ok):.0f}%)")
    print(f"  Regenerated:        {regen_count}/{len(ok)}")
    print(f"  Sensitive topics:   {sensitive_count}/{len(ok)}")


def print_combined_report(metrics_list):
    """Print report for combined/merge-topics tests."""
    print("\n" + "=" * 80)
    print("COMBINED ARTICLE GENERATION (MERGE-TOPICS) - REPORT")
    print("=" * 80)

    for m in metrics_list:
        if m["status"] == "FAILED":
            print(f"\n! {m['test']}: FAILED -- HTTP {m['http_status']} -- {m.get('error', '')[:100]}")
            continue

        print(f"\n--- {m['test']} ---")
        print(f"  Groups: {m['num_groups']} | Exclusives: {m['num_exclusives']} | Quotes: {m['num_quotes']}")
        print(f"  Summary: {'Y' if m['has_summary'] else 'N'} ({m['summary_chars']} chars)")
        print(f"  Latency: {m['elapsed_ms']}ms")
        for g in m.get("group_details", []):
            print(f"    Group '{g['label']}': {g['num_versions']} versions, recommended={g['recommended_version']}")


# ─── Main ───────────────────────────────────────────────────────────────

def run_single_tests():
    """Run all single article generation tests."""
    print(f"\nRunning {len(SINGLE_TESTS)} single article tests...\n")
    results = []
    raw_results = []

    for i, test in enumerate(SINGLE_TESTS):
        print(f"  [{i+1}/{len(SINGLE_TESTS)}] {test['name']}...", end=" ", flush=True)
        raw = call_generate(test["article_key"], test.get("params"))
        metrics = extract_metrics(raw, test["name"])
        results.append(metrics)
        raw_results.append({"test": test["name"], "raw": raw, "metrics": metrics})
        status = "OK" if metrics["status"] == "OK" else "FAIL"
        elapsed = metrics.get("elapsed_ms", 0)
        print(f"{status} ({elapsed}ms)")

    print_single_report(results)
    return results, raw_results


def run_combined_tests():
    """Run all combined article (merge-topics) tests."""
    print(f"\nRunning {len(COMBINED_TESTS)} combined article tests...\n")
    results = []
    raw_results = []

    for i, test in enumerate(COMBINED_TESTS):
        print(f"  [{i+1}/{len(COMBINED_TESTS)}] {test['name']}...", end=" ", flush=True)
        raw = call_merge_topics(test["articles"])
        metrics = extract_merge_metrics(raw, test["name"])
        results.append(metrics)
        raw_results.append({"test": test["name"], "raw": raw, "metrics": metrics})
        status = "OK" if metrics["status"] == "OK" else "FAIL"
        elapsed = metrics.get("elapsed_ms", 0)
        print(f"{status} ({elapsed}ms)")

    print_combined_report(results)
    return results, raw_results


def run_edge_tests():
    """Run edge case tests."""
    print(f"\nRunning {len(EDGE_TESTS)} edge case tests...\n")
    results = []
    raw_results = []

    for i, test in enumerate(EDGE_TESTS):
        print(f"  [{i+1}/{len(EDGE_TESTS)}] {test['name']}...", end=" ", flush=True)
        raw = call_generate(test["article_key"], test.get("params"))
        metrics = extract_metrics(raw, test["name"])
        results.append(metrics)
        raw_results.append({"test": test["name"], "raw": raw, "metrics": metrics})
        status = "OK" if metrics["status"] == "OK" else "FAIL"
        elapsed = metrics.get("elapsed_ms", 0)
        print(f"{status} ({elapsed}ms)")

    print_single_report(results)
    return results, raw_results


def main():
    parser = argparse.ArgumentParser(description="Deep Article Generation Quality Audit")
    parser.add_argument("--suite", choices=["single", "combined", "edge", "all"], default="all")
    parser.add_argument("--output", default=None, help="JSON output file path")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output or f"scripts/deep_audit_results_{timestamp}.json"

    print(f"Deep Generation Audit — {datetime.now().isoformat()}")
    print(f"API: {API_BASE}")
    print(f"Suite: {args.suite}")

    all_results = {}
    all_raw = {}

    if args.suite in ("single", "all"):
        single_metrics, single_raw = run_single_tests()
        all_results["single"] = single_metrics
        all_raw["single"] = single_raw

    if args.suite in ("combined", "all"):
        combined_metrics, combined_raw = run_combined_tests()
        all_results["combined"] = combined_metrics
        all_raw["combined"] = combined_raw

    if args.suite in ("edge", "all"):
        edge_metrics, edge_raw = run_edge_tests()
        all_results["edge"] = edge_metrics
        all_raw["edge"] = edge_raw

    # Save results
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "api_base": API_BASE,
        "suite": args.suite,
        "metrics": all_results,
        "raw_responses": all_raw,
    }

    # Make JSON serializable (handle sets, etc.)
    def default_serializer(obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=default_serializer)

    print(f"\nResults saved to: {output_file}")

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    total_tests = sum(len(v) for v in all_results.values())
    total_ok = sum(1 for v in all_results.values() for m in v if m["status"] == "OK")
    total_failed = total_tests - total_ok
    print(f"  Total tests: {total_tests}")
    print(f"  Passed: {total_ok}")
    print(f"  Failed: {total_failed}")


if __name__ == "__main__":
    main()
