"""
API REST para temas semanticos.
Endpoints para listar e consultar temas com classificacao A/B/C.
"""

import azure.functions as func
import json
import logging
from math import ceil
from uuid import UUID
from typing import Optional

from services.database import get_db
from services.clustering_service import get_clustering_service

logger = logging.getLogger(__name__)


async def list_themes_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/semantic-themes

    Lista temas semanticos com filtros e estatisticas de classificacao.

    Query Parameters:
        classification: str - Filtrar por classificacao ('A', 'B', 'C')
        status: str - Status do tema ('active', 'inactive') default: 'active'
        limit: int - Maximo de temas a retornar (default: 50, max: 100)
        page: int - Pagina para paginacao (default: 1)
        sort: str - Campo para ordenacao ('score', 'articles', 'recent') default: 'score'

    Returns:
        {
            "items": [
                {
                    "id": "uuid",
                    "name": "Theme Name",
                    "slug": "theme-name",
                    "classification": "A",
                    "score": 85.5,
                    "articleCount": 12,
                    "recentArticleCount": 5,
                    "trend": "up",
                    "isEmergent": true,
                    "representativeTags": ["tag1", "tag2"]
                }
            ],
            "stats": {
                "totalA": 15,
                "totalB": 42,
                "totalC": 28
            },
            "total": 85,
            "page": 1,
            "pages": 2
        }
    """
    try:
        # Parse query params
        classification = req.params.get('classification')
        status = req.params.get('status', 'active')
        limit = min(int(req.params.get('limit', '50')), 100)
        page = int(req.params.get('page', '1'))
        sort = req.params.get('sort', 'score')

        if page < 1:
            page = 1

        offset = (page - 1) * limit

        db = get_db()

        # Build query with filters
        conditions = ["status = %s"]
        params = [status]

        if classification and classification in ('A', 'B', 'C'):
            conditions.append("classification = %s")
            params.append(classification)

        where_clause = " AND ".join(conditions)

        # Determine sort order
        order_by = "avg_score DESC"
        if sort == 'articles':
            order_by = "article_count DESC"
        elif sort == 'recent':
            order_by = "last_updated_at DESC"

        # Main query for themes
        query = f"""
            SELECT
                t.id, t.name, t.slug, t.classification,
                COALESCE(t.avg_score, 0) as score,
                t.article_count,
                t.status, t.first_seen_at, t.last_updated_at
            FROM themes t
            WHERE {where_clause}
            ORDER BY {order_by}
            OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
        """

        # Count query for pagination
        count_query = f"""
            SELECT COUNT(*) FROM themes WHERE {where_clause}
        """

        # Stats query for classification distribution
        stats_query = """
            SELECT
                classification,
                COUNT(*) as count
            FROM themes
            WHERE status = 'active'
            GROUP BY classification
        """

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get total count
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Get classification stats
            cursor.execute(stats_query)
            stats_rows = cursor.fetchall()
            stats = {"totalA": 0, "totalB": 0, "totalC": 0}
            for row in stats_rows:
                if row[0] == 'A':
                    stats["totalA"] = row[1]
                elif row[0] == 'B':
                    stats["totalB"] = row[1]
                elif row[0] == 'C':
                    stats["totalC"] = row[1]

            # Get themes
            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()

            items = []
            for row in rows:
                theme_id = row[0]

                # Get recent article count (last 24h)
                recent_count = _get_recent_article_count(cursor, theme_id)

                # Get representative tags
                tags = _get_representative_tags(cursor, theme_id, limit=5)

                # Calculate trend based on recent activity
                trend = _calculate_trend(row[5], recent_count)

                # Determine if emergent (new theme with rapid growth)
                is_emergent = _is_theme_emergent(row[8], row[5], recent_count)

                items.append({
                    "id": str(theme_id),
                    "name": row[1],
                    "slug": row[2],
                    "classification": row[3],
                    "score": round(row[4], 2) if row[4] else 0,
                    "articleCount": row[5],
                    "recentArticleCount": recent_count,
                    "trend": trend,
                    "isEmergent": is_emergent,
                    "representativeTags": tags
                })

        pages = ceil(total / limit) if total > 0 else 1

        response = {
            "items": items,
            "stats": stats,
            "total": total,
            "page": page,
            "pages": pages
        }

        return func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": "Parâmetro inválido"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def get_theme_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/semantic-themes/{id}

    Retorna detalhes de um tema especifico incluindo seus artigos.

    Path Parameters:
        id: UUID do tema

    Query Parameters:
        articles_limit: int - Maximo de artigos a incluir (default: 10, max: 50)
        articles_page: int - Pagina de artigos (default: 1)

    Returns:
        {
            "id": "uuid",
            "name": "Theme Name",
            "slug": "theme-name",
            "classification": "A",
            "score": 85.5,
            "articleCount": 12,
            "recentArticleCount": 5,
            "trend": "up",
            "isEmergent": true,
            "representativeTags": ["tag1", "tag2"],
            "scoreBreakdown": {
                "avgInesperado": 18.5,
                "avgImpacto": 22.0,
                "avgBuscaAgora": 15.0,
                "avgConversa": 12.0
            },
            "articles": {
                "items": [...],
                "total": 12,
                "page": 1,
                "pages": 2
            },
            "createdAt": "2024-01-15T10:30:00Z",
            "updatedAt": "2024-01-15T14:45:00Z"
        }
    """
    try:
        theme_id = req.route_params.get('id')

        if not theme_id:
            return func.HttpResponse(
                json.dumps({"error": "Theme ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Parse query params
        articles_limit = min(int(req.params.get('articles_limit', '10')), 50)
        articles_page = int(req.params.get('articles_page', '1'))
        if articles_page < 1:
            articles_page = 1

        articles_offset = (articles_page - 1) * articles_limit

        db = get_db()
        theme = db.get_theme(UUID(theme_id))

        if not theme:
            return func.HttpResponse(
                json.dumps({"error": "Theme not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Get articles for this theme
        articles, articles_total = db.get_articles_by_theme(
            theme_id=UUID(theme_id),
            limit=articles_limit,
            offset=articles_offset
        )

        # Get additional statistics
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Recent article count
            recent_count = _get_recent_article_count(cursor, theme_id)

            # Representative tags
            tags = _get_representative_tags(cursor, theme_id, limit=10)

            # Score breakdown (average of each signal)
            score_breakdown = _get_score_breakdown(cursor, theme_id)

        # Calculate trend and emergent status
        trend = _calculate_trend(theme.get('article_count', 0), recent_count)
        is_emergent = _is_theme_emergent(
            theme.get('first_seen_at'),
            theme.get('article_count', 0),
            recent_count
        )

        articles_pages = ceil(articles_total / articles_limit) if articles_total > 0 else 1

        response = {
            "id": str(theme['id']),
            "name": theme['name'],
            "slug": theme['slug'],
            "classification": theme.get('classification'),
            "score": round(theme.get('avg_score', 0), 2),
            "articleCount": theme.get('article_count', 0),
            "recentArticleCount": recent_count,
            "trend": trend,
            "isEmergent": is_emergent,
            "representativeTags": tags,
            "scoreBreakdown": score_breakdown,
            "articles": {
                "items": [_article_to_response(a) for a in articles],
                "total": articles_total,
                "page": articles_page,
                "pages": articles_pages
            },
            "createdAt": theme.get('first_seen_at').isoformat() if theme.get('first_seen_at') else None,
            "updatedAt": theme.get('last_updated_at').isoformat() if theme.get('last_updated_at') else None
        }

        return func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": "Parâmetro inválido"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error getting theme: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


def _get_recent_article_count(cursor, theme_id) -> int:
    """Get count of articles added to theme in last 24 hours."""
    query = """
        SELECT COUNT(*)
        FROM article_themes
        WHERE theme_id = %s
        AND assigned_at >= DATEADD(hour, -24, GETUTCDATE())
    """
    try:
        cursor.execute(query, (str(theme_id),))
        return cursor.fetchone()[0]
    except Exception:
        return 0


def _get_representative_tags(cursor, theme_id, limit: int = 5) -> list:
    """Get most common tags from articles in this theme."""
    query = """
        SELECT TOP %s
            LOWER(LTRIM(RTRIM(t.value))) as tag,
            COUNT(*) as count
        FROM article_themes r
        JOIN collected_articles a ON r.article_id = a.id
        CROSS APPLY OPENJSON(a.tags) t
        WHERE r.theme_id = %s
        AND t.value IS NOT NULL
        AND LEN(t.value) > 2
        GROUP BY LOWER(LTRIM(RTRIM(t.value)))
        ORDER BY count DESC
    """
    try:
        cursor.execute(query, (limit, str(theme_id)))
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception:
        return []


def _get_score_breakdown(cursor, theme_id) -> dict:
    """Get average score breakdown for a theme."""
    query = """
        SELECT
            AVG(CAST(score_inesperado AS FLOAT)) as avg_inesperado,
            AVG(CAST(score_impacto AS FLOAT)) as avg_impacto,
            AVG(CAST(score_busca_agora AS FLOAT)) as avg_busca,
            AVG(CAST(score_conversa AS FLOAT)) as avg_conversa
        FROM article_scores s
        JOIN article_themes r ON s.article_id = r.article_id
        WHERE r.theme_id = %s
    """
    try:
        cursor.execute(query, (str(theme_id),))
        row = cursor.fetchone()
        if row:
            return {
                "avgInesperado": round(row[0] or 0, 1),
                "avgImpacto": round(row[1] or 0, 1),
                "avgBuscaAgora": round(row[2] or 0, 1),
                "avgConversa": round(row[3] or 0, 1)
            }
    except Exception:
        pass

    return {
        "avgInesperado": 0,
        "avgImpacto": 0,
        "avgBuscaAgora": 0,
        "avgConversa": 0
    }


def _calculate_trend(total_count: int, recent_count: int) -> str:
    """
    Calculate trend based on recent activity.

    Returns: 'up', 'down', or 'stable'
    """
    if total_count == 0:
        return 'stable'

    recent_ratio = recent_count / total_count if total_count > 0 else 0

    if recent_ratio > 0.3:  # More than 30% added recently
        return 'up'
    elif recent_ratio < 0.1 and total_count > 5:  # Less than 10% and established
        return 'down'
    else:
        return 'stable'


def _is_theme_emergent(created_at, total_count: int, recent_count: int) -> bool:
    """
    Determine if a theme is emergent (new and growing fast).

    Criteria:
    - Created in last 48 hours
    - Has at least 3 articles
    - More than 50% of articles added in last 24h
    """
    from datetime import datetime, timedelta

    if not created_at:
        return False

    # Check if created recently (within 48 hours)
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

    now = datetime.utcnow()
    if created_at.tzinfo:
        from datetime import timezone
        now = now.replace(tzinfo=timezone.utc)

    age_hours = (now - created_at).total_seconds() / 3600

    if age_hours > 48:
        return False

    # Check article count and growth
    if total_count < 3:
        return False

    growth_ratio = recent_count / total_count if total_count > 0 else 0
    return growth_ratio > 0.5


def _article_to_response(article) -> dict:
    """Convert Article to API response format."""
    return {
        "id": str(article.id),
        "title": article.title,
        "preview": article.preview,
        "url": article.url,
        "imageUrl": article.image_url,
        "source": article.source_name,
        "publishedAt": article.published_at.isoformat() if article.published_at else None,
        "similarityScore": getattr(article, 'similarity_score', None),
        "isSeed": getattr(article, 'is_seed', False)
    }


async def get_clustering_stats_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/clustering-stats

    Retorna metricas de qualidade do clustering atual.

    Returns:
        {
            "totalThemes": 15,
            "totalArticlesClustered": 120,
            "avgArticlesPerTheme": 8.0,
            "themesWithMultipleArticles": 12,
            "silhouetteScore": 0.65,
            "coverageRatio": 0.85,
            "singletonThemes": 3,
            "largestThemeSize": 25,
            "evaluatedAt": "2024-01-15T14:45:00Z",
            "qualityLevel": "good",
            "recommendations": [...]
        }
    """
    try:
        db = get_db()
        clustering_service = get_clustering_service(db_service=db)

        # Get clustering quality metrics
        metrics = clustering_service.evaluate_clustering_quality()

        if 'error' in metrics:
            return func.HttpResponse(
                json.dumps({"error": metrics['error']}),
                status_code=500,
                mimetype="application/json"
            )

        # Determine quality level based on metrics
        quality_level = _determine_quality_level(metrics)

        # Generate recommendations
        recommendations = _generate_recommendations(metrics)

        response = {
            "totalThemes": metrics.get('total_themes', 0),
            "totalArticlesClustered": metrics.get('total_articles_clustered', 0),
            "avgArticlesPerTheme": metrics.get('avg_articles_per_theme', 0.0),
            "themesWithMultipleArticles": metrics.get('themes_with_multiple_articles', 0),
            "silhouetteScore": metrics.get('silhouette_score'),
            "coverageRatio": metrics.get('coverage_ratio', 0.0),
            "singletonThemes": metrics.get('singleton_themes', 0),
            "largestThemeSize": metrics.get('largest_theme_size', 0),
            "evaluatedAt": metrics.get('evaluated_at'),
            "qualityLevel": quality_level,
            "recommendations": recommendations
        }

        return func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting clustering stats: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


def _determine_quality_level(metrics: dict) -> str:
    """
    Determine overall clustering quality level.

    Returns: 'excellent', 'good', 'fair', or 'poor'
    """
    silhouette = metrics.get('silhouette_score')
    coverage = metrics.get('coverage_ratio', 0)
    avg_articles = metrics.get('avg_articles_per_theme', 0)
    total_themes = metrics.get('total_themes', 0)

    if total_themes == 0:
        return 'none'

    score = 0

    # Silhouette score contribution (0-40 points)
    if silhouette is not None:
        if silhouette >= 0.5:
            score += 40
        elif silhouette >= 0.3:
            score += 30
        elif silhouette >= 0.1:
            score += 20
        elif silhouette >= 0:
            score += 10

    # Coverage contribution (0-30 points)
    if coverage >= 0.9:
        score += 30
    elif coverage >= 0.7:
        score += 25
    elif coverage >= 0.5:
        score += 15
    elif coverage >= 0.3:
        score += 10

    # Average articles per theme (0-30 points)
    if avg_articles >= 5:
        score += 30
    elif avg_articles >= 3:
        score += 25
    elif avg_articles >= 2:
        score += 15
    elif avg_articles >= 1.5:
        score += 10

    if score >= 80:
        return 'excellent'
    elif score >= 60:
        return 'good'
    elif score >= 40:
        return 'fair'
    else:
        return 'poor'


def _generate_recommendations(metrics: dict) -> list:
    """
    Generate recommendations based on clustering metrics.
    """
    recommendations = []

    silhouette = metrics.get('silhouette_score')
    coverage = metrics.get('coverage_ratio', 0)
    singleton_themes = metrics.get('singleton_themes', 0)
    total_themes = metrics.get('total_themes', 0)
    avg_articles = metrics.get('avg_articles_per_theme', 0)

    # Silhouette recommendations
    if silhouette is not None:
        if silhouette < 0.1:
            recommendations.append({
                "type": "warning",
                "message": "Silhouette score muito baixo. Considere ajustar o threshold de similaridade.",
                "action": "Aumentar CLUSTERING_SIMILARITY_THRESHOLD para criar clusters mais coesos."
            })
        elif silhouette < 0.3:
            recommendations.append({
                "type": "info",
                "message": "Silhouette score pode ser melhorado.",
                "action": "Revise os parametros de clustering ou considere re-clustering."
            })

    # Coverage recommendations
    if coverage < 0.5:
        recommendations.append({
            "type": "warning",
            "message": f"Baixa cobertura ({coverage:.1%}). Muitos artigos sem tema.",
            "action": "Execute o clustering engine para processar artigos pendentes."
        })
    elif coverage < 0.8:
        recommendations.append({
            "type": "info",
            "message": f"Cobertura moderada ({coverage:.1%}).",
            "action": "Verifique se ha artigos pendentes de embedding ou clustering."
        })

    # Singleton themes recommendations
    if total_themes > 0 and singleton_themes / total_themes > 0.5:
        recommendations.append({
            "type": "warning",
            "message": f"Muitos temas com apenas 1 artigo ({singleton_themes}/{total_themes}).",
            "action": "Considere reduzir o threshold de similaridade para agrupar mais artigos."
        })

    # Average articles recommendations
    if avg_articles < 2 and total_themes > 10:
        recommendations.append({
            "type": "info",
            "message": "Media de artigos por tema baixa.",
            "action": "Os temas podem estar muito fragmentados. Considere ajustar parametros."
        })

    if len(recommendations) == 0:
        recommendations.append({
            "type": "success",
            "message": "Clustering funcionando adequadamente.",
            "action": "Nenhuma acao necessaria no momento."
        })

    return recommendations
