"""
Script para resetar temas e reclustering de artigos.

Este script:
1. Deleta todos os temas existentes e relacoes article_themes
2. Reseta primary_theme_id em collected_articles para NULL
3. Executa o pipeline de clustering para criar novos temas com a logica corrigida
"""

import pymssql
import json
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import re

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conexao com o banco de dados
DB_CONFIG = {
    'server': 'bi4ia-tmc.database.windows.net',
    'user': 'admjaar',
    'password': 'mbfb)Zxkxehpv%NQD8ba',
    'database': 'tmc'
}

# Configuracoes de clustering
CLUSTERING_SIMILARITY_THRESHOLD = 0.75
CLUSTERING_EMA_ALPHA = 0.1
EMBEDDING_DIMENSION = 1536

# Importar numpy para calculos de similaridade
try:
    import numpy as np
except ImportError:
    logger.error("NumPy nao esta instalado. Execute: pip install numpy")
    sys.exit(1)


def get_connection():
    """Obtem conexao com o banco de dados."""
    return pymssql.connect(
        server=DB_CONFIG['server'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        login_timeout=30,
        as_dict=False,
        charset='UTF-8'
    )


def reset_themes():
    """
    Reseta todos os temas e relacoes.

    Executa:
    - DELETE FROM article_themes;
    - DELETE FROM themes;
    - UPDATE collected_articles SET primary_theme_id = NULL;
    """
    logger.info("=" * 60)
    logger.info("INICIANDO RESET DE TEMAS")
    logger.info("=" * 60)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Contar registros antes
        cursor.execute("SELECT COUNT(*) FROM article_themes")
        article_themes_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM themes")
        themes_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM collected_articles WHERE primary_theme_id IS NOT NULL")
        articles_with_theme_count = cursor.fetchone()[0]

        logger.info(f"Registros atuais:")
        logger.info(f"  - article_themes: {article_themes_count}")
        logger.info(f"  - themes: {themes_count}")
        logger.info(f"  - artigos com primary_theme_id: {articles_with_theme_count}")

        # Deletar article_themes
        logger.info("\nDeletando article_themes...")
        cursor.execute("DELETE FROM article_themes")
        deleted_article_themes = cursor.rowcount
        logger.info(f"  Deletados: {deleted_article_themes}")

        # Deletar themes
        logger.info("\nDeletando themes...")
        cursor.execute("DELETE FROM themes")
        deleted_themes = cursor.rowcount
        logger.info(f"  Deletados: {deleted_themes}")

        # Resetar primary_theme_id
        logger.info("\nResetando primary_theme_id em collected_articles...")
        cursor.execute("UPDATE collected_articles SET primary_theme_id = NULL")
        updated_articles = cursor.rowcount
        logger.info(f"  Atualizados: {updated_articles}")

        conn.commit()

    logger.info("\n" + "=" * 60)
    logger.info("RESET CONCLUIDO COM SUCESSO")
    logger.info("=" * 60)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calcula similaridade cosseno entre dois vetores."""
    a = np.array(vec1, dtype=np.float64)
    b = np.array(vec2, dtype=np.float64)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = dot_product / (norm_a * norm_b)
    return float(max(0.0, min(1.0, similarity)))


def normalize_vector(vec: List[float]) -> List[float]:
    """Normaliza um vetor para comprimento unitario."""
    a = np.array(vec, dtype=np.float64)
    norm = np.linalg.norm(a)

    if norm == 0:
        return vec

    return (a / norm).tolist()


def generate_slug(name: str) -> str:
    """Gera um slug URL-friendly a partir de um nome."""
    accent_map = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n'
    }

    slug = name.lower()

    for accent, replacement in accent_map.items():
        slug = slug.replace(accent, replacement)

    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-+', '-', slug)

    return slug[:255]


def generate_temporary_name(article: Dict[str, Any]) -> str:
    """Gera um nome temporario para o tema a partir do artigo."""
    title = article.get('title', 'Unknown')
    name = title[:50].strip()
    name = re.sub(r'^[\d/\-\.]+\s*', '', name)
    name = re.sub(r'^[A-Z0-9]+:\s*', '', name)

    if not name:
        name = 'Tema sem nome'

    return name


def get_articles_pending_clustering(conn, limit: int = 500) -> List[Dict[str, Any]]:
    """Retorna artigos que possuem embedding (prontos para clustering)."""
    query = """
        SELECT TOP %s
            a.id, a.title, a.preview, e.embedding
        FROM collected_articles a
        JOIN article_embeddings e ON a.id = e.article_id
        ORDER BY a.collected_at DESC
    """

    cursor = conn.cursor()
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()

    return [
        {
            'id': row[0],
            'title': row[1],
            'preview': row[2],
            'embedding': json.loads(row[3]) if row[3] else None
        }
        for row in rows
    ]


def create_theme(conn, name: str, slug: str, centroid: List[float]) -> str:
    """Cria um novo tema e retorna o ID."""
    centroid_json = json.dumps(centroid)

    query = """
        INSERT INTO themes
        (name, slug, centroid, article_count, status)
        OUTPUT INSERTED.id
        VALUES (%s, %s, %s, 0, 'active')
    """

    cursor = conn.cursor()
    cursor.execute(query, (name, slug, centroid_json))
    row = cursor.fetchone()
    return str(row[0])


def add_article_to_theme(conn, article_id: str, theme_id: str, similarity_score: float, is_seed: bool = False):
    """Adiciona um artigo a um tema."""
    query = """
        INSERT INTO article_themes (article_id, theme_id, similarity_score, is_seed)
        VALUES (%s, %s, %s, %s)
    """

    cursor = conn.cursor()
    cursor.execute(query, (article_id, theme_id, similarity_score, is_seed))


def update_theme_centroid(conn, theme_id: str, new_centroid: List[float], article_count: int):
    """Atualiza o centroide e contagem de artigos de um tema."""
    centroid_json = json.dumps(new_centroid)

    query = """
        UPDATE themes
        SET centroid = %s, article_count = %s, last_updated_at = GETUTCDATE()
        WHERE id = %s
    """

    cursor = conn.cursor()
    cursor.execute(query, (centroid_json, article_count, theme_id))


def run_clustering():
    """
    Executa o pipeline de clustering para todos os artigos com embeddings.

    Algoritmo:
    1. Para cada artigo com embedding:
       a. Calcula similaridade cosseno com todos os centroides de temas existentes
       b. Se similaridade >= 0.75: adiciona ao tema existente
       c. Se similaridade < 0.75: cria novo tema com artigo como semente
    2. Atualiza centroide do tema (media movel exponencial, alpha=0.1)
    """
    logger.info("\n" + "=" * 60)
    logger.info("INICIANDO CLUSTERING DE ARTIGOS")
    logger.info("=" * 60)

    # Cache de temas em memoria
    theme_cache: Dict[str, Dict[str, Any]] = {}

    with get_connection() as conn:
        # Obter artigos com embeddings
        articles = get_articles_pending_clustering(conn, limit=1000)
        logger.info(f"Encontrados {len(articles)} artigos com embeddings")

        if not articles:
            logger.info("Nenhum artigo para processar")
            return

        processed = 0
        new_themes_created = 0

        for article in articles:
            article_id = str(article['id'])
            embedding = article.get('embedding')

            if embedding is None:
                logger.warning(f"Artigo {article_id} sem embedding, pulando")
                continue

            # Encontrar melhor tema correspondente
            best_theme_id = None
            best_similarity = 0.0

            for theme_id, theme_data in theme_cache.items():
                centroid = theme_data.get('centroid')
                if centroid is None:
                    continue

                try:
                    similarity = cosine_similarity(embedding, centroid)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_theme_id = theme_id
                except Exception as e:
                    logger.warning(f"Erro calculando similaridade para tema {theme_id}: {e}")
                    continue

            if best_similarity >= CLUSTERING_SIMILARITY_THRESHOLD and best_theme_id:
                # Adicionar ao tema existente
                add_article_to_theme(conn, article_id, best_theme_id, best_similarity)

                # Atualizar centroide com EMA
                old_centroid = np.array(theme_cache[best_theme_id]['centroid'], dtype=np.float64)
                new_emb = np.array(embedding, dtype=np.float64)
                updated_centroid = CLUSTERING_EMA_ALPHA * new_emb + (1 - CLUSTERING_EMA_ALPHA) * old_centroid
                updated_centroid = normalize_vector(updated_centroid.tolist())

                theme_cache[best_theme_id]['centroid'] = updated_centroid
                theme_cache[best_theme_id]['article_count'] += 1

                update_theme_centroid(
                    conn,
                    best_theme_id,
                    updated_centroid,
                    theme_cache[best_theme_id]['article_count']
                )

                logger.debug(f"Artigo {article_id[:8]}... adicionado ao tema {best_theme_id[:8]}... (sim={best_similarity:.4f})")
            else:
                # Criar novo tema
                name = generate_temporary_name(article)
                slug = generate_slug(name)
                centroid = normalize_vector(embedding)

                theme_id = create_theme(conn, name, slug, centroid)

                # Adicionar artigo ao novo tema como semente
                add_article_to_theme(conn, article_id, theme_id, 1.0, is_seed=True)

                # Atualizar cache
                theme_cache[theme_id] = {
                    'id': theme_id,
                    'name': name,
                    'centroid': centroid,
                    'article_count': 1
                }

                # Atualizar contagem no banco
                update_theme_centroid(conn, theme_id, centroid, 1)

                new_themes_created += 1
                logger.debug(f"Novo tema criado: '{name}' (ID: {theme_id[:8]}...)")

            processed += 1

            # Log de progresso
            if processed % 50 == 0:
                logger.info(f"Progresso: {processed}/{len(articles)} artigos processados, {new_themes_created} temas criados")

        conn.commit()

    logger.info("\n" + "=" * 60)
    logger.info("CLUSTERING CONCLUIDO")
    logger.info("=" * 60)
    logger.info(f"Artigos processados: {processed}")
    logger.info(f"Novos temas criados: {new_themes_created}")
    logger.info(f"Total de temas: {len(theme_cache)}")


def show_statistics():
    """Mostra estatisticas apos o clustering."""
    logger.info("\n" + "=" * 60)
    logger.info("ESTATISTICAS FINAIS")
    logger.info("=" * 60)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Total de temas
        cursor.execute("SELECT COUNT(*) FROM themes WHERE status = 'active'")
        total_themes = cursor.fetchone()[0]

        # Total de artigos clusterizados
        cursor.execute("SELECT COUNT(DISTINCT article_id) FROM article_themes")
        total_clustered = cursor.fetchone()[0]

        # Temas com mais artigos
        cursor.execute("""
            SELECT TOP 10 t.name, t.article_count
            FROM themes t
            WHERE t.status = 'active'
            ORDER BY t.article_count DESC
        """)
        top_themes = cursor.fetchall()

        # Distribuicao de tamanho de temas
        cursor.execute("""
            SELECT
                CASE
                    WHEN article_count = 1 THEN '1 artigo'
                    WHEN article_count BETWEEN 2 AND 5 THEN '2-5 artigos'
                    WHEN article_count BETWEEN 6 AND 10 THEN '6-10 artigos'
                    WHEN article_count > 10 THEN '10+ artigos'
                END as tamanho,
                COUNT(*) as quantidade
            FROM themes
            WHERE status = 'active'
            GROUP BY
                CASE
                    WHEN article_count = 1 THEN '1 artigo'
                    WHEN article_count BETWEEN 2 AND 5 THEN '2-5 artigos'
                    WHEN article_count BETWEEN 6 AND 10 THEN '6-10 artigos'
                    WHEN article_count > 10 THEN '10+ artigos'
                END
            ORDER BY quantidade DESC
        """)
        size_distribution = cursor.fetchall()

    logger.info(f"Total de temas ativos: {total_themes}")
    logger.info(f"Total de artigos clusterizados: {total_clustered}")

    logger.info("\nTop 10 temas por quantidade de artigos:")
    for name, count in top_themes:
        logger.info(f"  - {name[:50]}...: {count} artigos" if len(name) > 50 else f"  - {name}: {count} artigos")

    logger.info("\nDistribuicao de tamanho de temas:")
    for tamanho, quantidade in size_distribution:
        logger.info(f"  - {tamanho}: {quantidade} temas")


def main():
    """Funcao principal."""
    start_time = datetime.utcnow()

    logger.info("=" * 60)
    logger.info("SCRIPT DE RESET E RECLUSTERING DE TEMAS")
    logger.info(f"Inicio: {start_time.isoformat()}")
    logger.info("=" * 60)

    try:
        # Testar conexao
        logger.info("\nTestando conexao com o banco de dados...")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        logger.info("Conexao OK!")

        # Passo 1: Reset
        reset_themes()

        # Passo 2: Clustering
        run_clustering()

        # Passo 3: Estatisticas
        show_statistics()

    except Exception as e:
        logger.error(f"Erro durante execucao: {e}")
        raise

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    logger.info("\n" + "=" * 60)
    logger.info("SCRIPT FINALIZADO COM SUCESSO")
    logger.info(f"Duracao total: {duration:.2f} segundos")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
