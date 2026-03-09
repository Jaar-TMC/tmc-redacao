"""
Script de teste de integracao para 5 materias.
Executa scoring e clustering com as correcoes aplicadas.
"""

import asyncio
import sys
import os

# Adicionar diretorio ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymssql
import json
from datetime import datetime
from uuid import uuid4
import numpy as np

# IDs das 5 materias de teste
ARTICLE_IDS = [
    'd25b1964-a470-4f3c-b1da-595617cb4148',
    '73d8e2f7-a82c-48dc-b45d-247901202a60',
    '3eae40b4-3231-4ffe-9e8e-5712cfff1704',
    '9286a5d7-6fe6-4dad-b551-ef71da1e14c0',
    '587b8f7a-9db8-4d2c-88c3-53a41689c441'
]

# Conexao com o banco
def get_connection():
    server = os.environ.get("SQL_SERVER", "")
    database = os.environ.get("SQL_DATABASE", "")
    username = os.environ.get("SQL_USERNAME", "")
    password = os.environ.get("SQL_PASSWORD", "")
    return pymssql.connect(
        server=server,
        database=database,
        user=username,
        password=password,
        as_dict=True
    )


def get_articles():
    """Busca as 5 materias de teste com seus dados completos."""
    conn = get_connection()
    cursor = conn.cursor()

    articles = []
    for aid in ARTICLE_IDS:
        cursor.execute('''
            SELECT ca.id, ca.title, ca.content, ae.embedding
            FROM collected_articles ca
            LEFT JOIN article_embeddings ae ON ca.id = ae.article_id
            WHERE ca.id = %s
        ''', (aid,))
        art = cursor.fetchone()
        if art:
            articles.append(art)

    conn.close()
    return articles


def score_article_heuristic(title, content):
    """
    Scoring heuristico baseado nas keywords atualizadas.
    Simula o que o scoring_service faz quando nao ha IA.
    """
    text = f"{title} {content or ''}".lower()

    # Keywords expandidas (conforme correcao aplicada)
    keywords = {
        'inesperado': ['surpresa', 'surpreendente', 'bomba', 'exclusivo', 'urgente',
                       'inesperado', 'chocante', 'renuncia', 'impeachment', 'escandalo',
                       'falencia', 'morte', 'descoberta', 'golpe', 'crise'],
        'impacto': ['aumento', 'preco', 'imposto', 'salario', 'emprego', 'desemprego',
                    'inflacao', 'juros', 'surto', 'pandemia', 'lei', 'direito',
                    'aposentado', 'pensionista', 'consumidor', 'banco'],
        'busca': ['como', 'quando', 'onde', 'resultado', 'placar', 'ao vivo',
                  'acidente', 'vazamento', 'eleicao', 'votacao', 'prisao'],
        'conversa': ['polemica', 'controverso', 'debate', 'opiniao', 'critica',
                     'briga', 'treta', 'divisao', 'racismo', 'corrupcao',
                     'politica', 'governo', 'presidente']
    }

    # Contar matches
    scores = {}
    for signal, words in keywords.items():
        count = sum(1 for w in words if w in text)
        if count >= 2:
            scores[signal] = 'high'
        elif count >= 1:
            scores[signal] = 'medium'
        else:
            scores[signal] = 'low'

    # Calcular pontuacao
    score_map = {
        'inesperado': {'high': 25, 'medium': 12, 'low': 0},
        'impacto': {'high': 30, 'medium': 15, 'low': 0},
        'busca': {'high': 25, 'medium': 12, 'low': 0},
        'conversa': {'high': 20, 'medium': 10, 'low': 0}
    }

    result = {
        'sinal_inesperado': 'yes' if scores['inesperado'] == 'high' else ('partial' if scores['inesperado'] == 'medium' else 'no'),
        'sinal_impacto': 'high' if scores['impacto'] == 'high' else ('medium' if scores['impacto'] == 'medium' else 'low'),
        'sinal_busca_agora': 'yes' if scores['busca'] == 'high' else ('maybe' if scores['busca'] == 'medium' else 'no'),
        'sinal_conversa': 'yes' if scores['conversa'] == 'high' else 'no',
        'score_inesperado': score_map['inesperado'][scores['inesperado']],
        'score_impacto': score_map['impacto'][scores['impacto']],
        'score_busca_agora': score_map['busca'][scores['busca']],
        'score_conversa': score_map['conversa'][scores['conversa']],
    }

    result['total_score'] = (
        result['score_inesperado'] +
        result['score_impacto'] +
        result['score_busca_agora'] +
        result['score_conversa']
    )

    # Classificacao com threshold corrigido (35)
    if result['total_score'] >= 75:
        result['classification'] = 'A'
    elif result['total_score'] >= 35:  # Threshold B ajustado para 35
        result['classification'] = 'B'
    else:
        result['classification'] = 'C'

    return result


def save_score(article_id, score_result):
    """Salva o score no banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()

    score_id = str(uuid4())

    cursor.execute('''
        INSERT INTO article_scores (
            id, article_id,
            sinal_inesperado, sinal_impacto, sinal_busca_agora, sinal_conversa,
            score_inesperado, score_impacto, score_busca_agora, score_conversa,
            total_score, classification, scored_by, reasoning, scored_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, GETUTCDATE()
        )
    ''', (
        score_id, str(article_id),
        score_result['sinal_inesperado'], score_result['sinal_impacto'],
        score_result['sinal_busca_agora'], score_result['sinal_conversa'],
        score_result['score_inesperado'], score_result['score_impacto'],
        score_result['score_busca_agora'], score_result['score_conversa'],
        score_result['total_score'], score_result['classification'],
        'heuristic_test', 'Teste de integracao com keywords expandidas'
    ))

    # Marcar artigo como tendo score
    cursor.execute('''
        UPDATE collected_articles SET has_score = 1 WHERE id = %s
    ''', (str(article_id),))

    conn.commit()
    conn.close()
    return score_id


def cosine_similarity(vec1, vec2):
    """Calcula similaridade cosseno entre dois vetores."""
    a = np.array(vec1, dtype=np.float64)
    b = np.array(vec2, dtype=np.float64)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def cluster_articles(articles):
    """
    Executa clustering das materias com threshold corrigido (0.50).
    Retorna dict com agrupamentos.
    """
    THRESHOLD = 0.50  # CORRIGIDO de 0.58 para 0.50

    clusters = []  # Lista de clusters, cada cluster eh lista de article_ids
    centroids = []  # Centroid de cada cluster

    for art in articles:
        if not art['embedding']:
            continue

        embedding = json.loads(art['embedding']) if isinstance(art['embedding'], str) else art['embedding']

        # Encontrar melhor cluster
        best_cluster_idx = None
        best_similarity = 0.0

        for idx, centroid in enumerate(centroids):
            sim = cosine_similarity(embedding, centroid)
            if sim > best_similarity:
                best_similarity = sim
                best_cluster_idx = idx

        if best_similarity >= THRESHOLD and best_cluster_idx is not None:
            # Adicionar ao cluster existente
            clusters[best_cluster_idx].append({
                'id': art['id'],
                'title': art['title'],
                'similarity': best_similarity
            })
            # Atualizar centroid com EMA (alpha = 0.15)
            old_c = np.array(centroids[best_cluster_idx])
            new_c = 0.15 * np.array(embedding) + 0.85 * old_c
            centroids[best_cluster_idx] = new_c.tolist()
        else:
            # Criar novo cluster
            clusters.append([{
                'id': art['id'],
                'title': art['title'],
                'similarity': 1.0
            }])
            centroids.append(embedding)

    return clusters


def main():
    print('=' * 70)
    print('TESTE DE INTEGRACAO - SCORING E CLUSTERING')
    print('=' * 70)
    print(f'Data: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    # 1. Buscar artigos
    print('[1/4] Buscando artigos de teste...')
    articles = get_articles()
    print(f'      Encontrados: {len(articles)} artigos')

    # 2. Executar scoring
    print('\n[2/4] Executando SCORING (heuristico com keywords expandidas)...')
    print('-' * 70)

    scores = []
    for i, art in enumerate(articles, 1):
        score = score_article_heuristic(art['title'], art['content'])
        scores.append(score)

        # Salvar no banco
        save_score(art['id'], score)

        print(f'\nMateria {i}: {art["title"][:55]}...')
        print(f'  Sinais: inesp={score["sinal_inesperado"]}, imp={score["sinal_impacto"]}, '
              f'busca={score["sinal_busca_agora"]}, conv={score["sinal_conversa"]}')
        print(f'  Scores: {score["score_inesperado"]}+{score["score_impacto"]}+'
              f'{score["score_busca_agora"]}+{score["score_conversa"]} = {score["total_score"]}')
        print(f'  Classificacao: {score["classification"]}')

    # 3. Executar clustering
    print('\n' + '-' * 70)
    print('[3/4] Executando CLUSTERING (threshold 0.50)...')
    print('-' * 70)

    clusters = cluster_articles(articles)

    print(f'\nResultado: {len(clusters)} cluster(s) formado(s)')

    for i, cluster in enumerate(clusters, 1):
        print(f'\n  Cluster {i} ({len(cluster)} artigos):')
        for art in cluster:
            title = art['title'][:50] if len(art['title']) > 50 else art['title']
            print(f'    - {title}... (sim: {art["similarity"]:.3f})')

    # 4. Resumo
    print('\n' + '=' * 70)
    print('[4/4] RESUMO DO TESTE')
    print('=' * 70)

    class_counts = {'A': 0, 'B': 0, 'C': 0}
    for s in scores:
        class_counts[s['classification']] += 1

    print(f'\nSCORING:')
    print(f'  Classe A (>=75): {class_counts["A"]} materias')
    print(f'  Classe B (35-74): {class_counts["B"]} materias')
    print(f'  Classe C (<35): {class_counts["C"]} materias')

    print(f'\nCLUSTERING (threshold 0.50):')
    print(f'  Total de clusters: {len(clusters)}')
    print(f'  Clusters com 1 artigo: {sum(1 for c in clusters if len(c) == 1)}')
    print(f'  Clusters com 2+ artigos: {sum(1 for c in clusters if len(c) > 1)}')

    # Matriz de similaridade
    print('\n  Matriz de similaridade:')
    for i, art1 in enumerate(articles):
        if not art1['embedding']:
            continue
        emb1 = json.loads(art1['embedding']) if isinstance(art1['embedding'], str) else art1['embedding']
        sims = []
        for j, art2 in enumerate(articles):
            if not art2['embedding']:
                sims.append('----')
                continue
            emb2 = json.loads(art2['embedding']) if isinstance(art2['embedding'], str) else art2['embedding']
            if i == j:
                sims.append('1.00')
            else:
                sim = cosine_similarity(emb1, emb2)
                sims.append(f'{sim:.2f}')
        print(f'    M{i+1}: {" ".join(sims)}')

    print('\n' + '=' * 70)
    print('TESTE CONCLUIDO!')
    print('=' * 70)


if __name__ == '__main__':
    main()
