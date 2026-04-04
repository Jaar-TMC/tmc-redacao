"""
Script de Re-clustering com novos parametros otimizados.
Threshold: 0.58 (era 0.62)
EMA Alpha: 0.25 (era 0.1)
"""

import os
import pymssql
import json
import math
from datetime import datetime
from uuid import uuid4
import re

# Configuracoes otimizadas
SIMILARITY_THRESHOLD = 0.58
EMA_ALPHA = 0.25

def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(max(0.0, min(1.0, dot / (norm_a * norm_b))))

def normalize_vector(vec):
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]

def generate_slug(name):
    slug = name.lower()
    # Remove acentos comuns
    replacements = [
        ('á', 'a'), ('à', 'a'), ('ã', 'a'), ('â', 'a'),
        ('é', 'e'), ('ê', 'e'), ('í', 'i'), ('ó', 'o'),
        ('ô', 'o'), ('õ', 'o'), ('ú', 'u'), ('ç', 'c')
    ]
    for old, new in replacements:
        slug = slug.replace(old, new)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-+', '-', slug)
    return slug[:255]

def extract_theme_name(title):
    name = re.sub(r'^[\d/\-\.]+\s*', '', title)
    name = re.sub(r'^[A-Z0-9]+:\s*', '', name)
    delimiters = [': ', ' - ', ' | ', '; ']
    for delim in delimiters:
        if delim in name:
            parts = name.split(delim, 1)
            if len(parts[0]) >= 10:
                name = parts[0]
                break
    name = name[:80].strip()
    name = re.sub(r'[,;:\.]+ *$', '', name)
    return name if len(name) >= 3 else 'Tema sem nome'


def main():
    # Conectar
    server = os.environ.get("SQL_SERVER", "")
    database = os.environ.get("SQL_DATABASE", "")
    username = os.environ.get("SQL_USERNAME", "")
    password = os.environ.get("SQL_PASSWORD", "")
    conn = pymssql.connect(
        server=server,
        database=database,
        user=username,
        password=password,
        as_dict=True
    )
    cursor = conn.cursor()

    print('=' * 60)
    print('RE-CLUSTERING COM THRESHOLD 0.58')
    print('=' * 60)
    start = datetime.now()

    # Buscar artigos com embedding (JOIN com article_embeddings)
    print('\n[1/4] Buscando artigos com embedding...')
    cursor.execute('''
        SELECT ca.id, ca.title, ae.embedding
        FROM collected_articles ca
        INNER JOIN article_embeddings ae ON ca.id = ae.article_id
        WHERE ae.embedding IS NOT NULL
        ORDER BY ca.collected_at DESC
    ''')
    articles = cursor.fetchall()
    print(f'      Encontrados: {len(articles)} artigos')

    # Cache de temas
    themes_cache = {}

    stats = {
        'processed': 0,
        'added_to_existing': 0,
        'new_themes': 0,
        'errors': 0
    }

    print('\n[2/4] Processando artigos...')

    for i, article in enumerate(articles):
        try:
            article_id = article['id']
            title = article['title'] or 'Sem titulo'
            embedding_json = article['embedding']

            if not embedding_json:
                continue

            embedding = json.loads(embedding_json) if isinstance(embedding_json, str) else embedding_json

            # Encontrar melhor tema
            best_theme_id = None
            best_similarity = 0.0

            for theme_id, theme_data in themes_cache.items():
                similarity = cosine_similarity(embedding, theme_data['centroid'])
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_theme_id = theme_id

            if best_similarity >= SIMILARITY_THRESHOLD and best_theme_id:
                # Adicionar ao tema existente
                theme_data = themes_cache[best_theme_id]

                # Atualizar centroid com EMA
                old_centroid = theme_data['centroid']
                new_centroid = [
                    EMA_ALPHA * n + (1 - EMA_ALPHA) * o
                    for o, n in zip(old_centroid, embedding)
                ]
                theme_data['centroid'] = normalize_vector(new_centroid)
                theme_data['article_count'] += 1

                # Inserir relacao
                cursor.execute('''
                    INSERT INTO article_themes (id, article_id, theme_id, similarity_score, is_seed)
                    VALUES (%s, %s, %s, %s, 0)
                ''', (str(uuid4()), str(article_id), best_theme_id, best_similarity))

                # Atualizar article_count no banco
                cursor.execute('''
                    UPDATE themes SET article_count = %s WHERE id = %s
                ''', (theme_data['article_count'], best_theme_id))

                stats['added_to_existing'] += 1
            else:
                # Criar novo tema
                theme_id = str(uuid4())
                theme_name = extract_theme_name(title)
                theme_slug = generate_slug(theme_name)
                centroid = normalize_vector(embedding)

                cursor.execute('''
                    INSERT INTO themes (id, name, slug, centroid, article_count, status, first_seen_at, last_updated_at)
                    VALUES (%s, %s, %s, %s, 1, 'active', GETUTCDATE(), GETUTCDATE())
                ''', (theme_id, theme_name, theme_slug, json.dumps(centroid)))

                # Inserir relacao (seed)
                cursor.execute('''
                    INSERT INTO article_themes (id, article_id, theme_id, similarity_score, is_seed)
                    VALUES (%s, %s, %s, 1.0, 1)
                ''', (str(uuid4()), str(article_id), theme_id))

                # Adicionar ao cache
                themes_cache[theme_id] = {
                    'centroid': centroid,
                    'article_count': 1,
                    'name': theme_name
                }

                stats['new_themes'] += 1

            stats['processed'] += 1

            if (i + 1) % 50 == 0:
                print(f'      Processados: {i+1}/{len(articles)}')
                conn.commit()

        except Exception as e:
            stats['errors'] += 1
            if stats['errors'] <= 5:
                print(f'      Erro: {str(e)[:80]}')

    # Commit final
    conn.commit()

    print(f'\n[3/4] Processamento concluido!')
    print(f'      Processados: {stats["processed"]}')
    print(f'      Novos temas: {stats["new_themes"]}')
    print(f'      Agrupados: {stats["added_to_existing"]}')
    print(f'      Erros: {stats["errors"]}')

    # Estatisticas finais
    print('\n[4/4] Gerando estatisticas finais...')
    cursor.execute('''
        SELECT
            COUNT(*) as total_themes,
            SUM(CASE WHEN article_count > 1 THEN 1 ELSE 0 END) as multi_article,
            AVG(CAST(article_count as FLOAT)) as avg_articles,
            MAX(article_count) as max_articles
        FROM themes WHERE status = 'active'
    ''')
    final_stats = cursor.fetchone()

    print(f'\n[RESULTADO FINAL]:')
    print(f'   Total de temas criados: {final_stats["total_themes"]}')
    print(f'   Temas com multiplos artigos: {final_stats["multi_article"]}')
    print(f'   Media artigos/tema: {final_stats["avg_articles"]:.2f}')
    print(f'   Maior tema: {final_stats["max_articles"]} artigos')

    # Top 15 temas
    cursor.execute('''
        SELECT name, article_count FROM themes
        WHERE status = 'active' AND article_count > 1
        ORDER BY article_count DESC
    ''')
    top_themes = cursor.fetchall()[:15]
    print(f'\n[TOP 15 TEMAS]:')
    for t in top_themes:
        print(f'   {t["article_count"]:3d} art | {t["name"][:50]}')

    elapsed = (datetime.now() - start).total_seconds()
    print(f'\n   Tempo total: {elapsed:.1f}s')

    conn.close()
    print('\n' + '=' * 60)
    print('RE-CLUSTERING CONCLUIDO!')
    print('=' * 60)


if __name__ == '__main__':
    main()
