"""
Cost query service for the costs dashboard.

Separate module from database.py (already 3840 lines) per CLAUDE.md gotchas.
Imports get_db() and uses db.get_connection() for raw SQL queries.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, date
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Sentinel UUID for system operations (no user/source attribution)
SYSTEM_UUID = '00000000-0000-0000-0000-000000000000'

# ---------------------------------------------------------------------------
# In-memory TTL cache — persists across Function invocations within the same
# worker process (keeps Azure Functions warm). Invalidated on cold start.
# ---------------------------------------------------------------------------
_cost_cache: dict[str, tuple[Any, float]] = {}
_TTL_SHORT = 300    # 5 min — period-bound queries (overview, trends, breakdown, by-user, by-source)
_TTL_LONG  = 600    # 10 min — source estimate (static, not period-bound)


def _cache_get(key: str) -> Any:
    entry = _cost_cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        del _cost_cache[key]
        return None
    return value


def _cache_set(key: str, value: Any, ttl: int = _TTL_SHORT) -> None:
    _cost_cache[key] = (value, time.monotonic() + ttl)


def insert_api_usage_log(log_data: dict) -> bool:
    """
    Insert a non-LLM API usage log (Exa, embeddings).

    Non-blocking: runs in thread pool via run_in_executor.
    Errors are logged but never propagated.
    """
    try:
        def _do_insert():
            try:
                from services.database import get_db
                db = get_db()

                def _trunc(val, max_len):
                    if val and isinstance(val, str) and len(val) > max_len:
                        return val[:max_len]
                    return val

                query = """
                    INSERT INTO api_usage_log
                    (correlation_id, user_id, source_id, action_type, provider,
                     operation, request_count, input_units, cost_usd,
                     latency_ms, status, error_message, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (
                        _trunc(log_data.get('correlation_id'), 64),
                        log_data.get('user_id'),
                        log_data.get('source_id'),
                        _trunc(log_data.get('action_type'), 50),
                        _trunc(log_data.get('provider', 'unknown'), 30),
                        _trunc(log_data.get('operation', 'unknown'), 50),
                        log_data.get('request_count', 1),
                        log_data.get('input_units'),
                        log_data.get('cost_usd'),
                        log_data.get('latency_ms'),
                        _trunc(log_data.get('status', 'success'), 10),
                        _trunc(log_data.get('error_message'), 500),
                        _trunc(log_data.get('metadata'), 4000),
                    ))
                    conn.commit()
                return True
            except Exception as e:
                logger.warning(f"Failed to insert API usage log (non-blocking): {e}")
                return False

        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _do_insert)
        except RuntimeError:
            # No running event loop (sync context) — run directly
            _do_insert()
        return True
    except Exception:
        return False


def period_to_dates(period: str):
    """Convert period string to (start_date, end_date) tuple."""
    now = datetime.utcnow()
    end_date = now.date()

    if period == 'today':
        start_date = end_date
    elif period == '7d':
        start_date = end_date - timedelta(days=7)
    elif period == '30d':
        start_date = end_date - timedelta(days=30)
    elif period == '90d':
        start_date = end_date - timedelta(days=90)
    elif period == 'year':
        start_date = date(end_date.year, 1, 1)
    else:
        start_date = end_date - timedelta(days=30)

    return start_date, end_date


def _prev_period_dates(start_date, end_date):
    """Get the previous period of same length for delta comparison."""
    delta = (end_date - start_date).days or 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=delta - 1)
    return prev_start, prev_end


def get_cost_overview(period: str = '30d', start_date_str: str = None, end_date_str: str = None) -> dict:
    """
    Get cost overview for dashboard cards.
    Returns totals by provider with delta vs previous period.
    If start_date_str and end_date_str are provided, they override the period.
    """
    _ck = f'overview:{period}:{start_date_str}:{end_date_str}'
    cached = _cache_get(_ck)
    if cached is not None:
        return cached
    try:
        from services.database import get_db
        db = get_db()
        if start_date_str and end_date_str:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        else:
            start_date, end_date = period_to_dates(period)
        prev_start, prev_end = _prev_period_dates(start_date, end_date)

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Current period LLM costs
            # Note: LIKE patterns passed as params to avoid pymssql %s placeholder conflicts
            cursor.execute("""
                SELECT
                    COUNT(*) as call_count,
                    ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as total_cost,
                    ISNULL(SUM(CASE WHEN model LIKE %s THEN 1 ELSE 0 END), 0) as sonnet_calls,
                    ISNULL(SUM(CASE WHEN model LIKE %s THEN 1 ELSE 0 END), 0) as haiku_calls
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
            """, ('%sonnet%', '%haiku%', str(start_date), str(end_date)))
            row = cursor.fetchone()
            llm_calls = row[0] or 0
            llm_cost = float(row[1] or 0)
            sonnet_calls = row[2] or 0
            haiku_calls = row[3] or 0

            # Current period Exa + embedding costs — single query, grouped by provider
            cursor.execute("""
                SELECT provider,
                       ISNULL(SUM(cost_usd), 0) as total_cost
                FROM api_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND provider IN ('exa', 'azure_openai_embedding')
                  AND status = 'success'
                GROUP BY provider
            """, (str(start_date), str(end_date)))
            exa_cost = 0.0
            embedding_cost = 0.0
            for api_row in cursor.fetchall():
                if api_row[0] == 'exa':
                    exa_cost = float(api_row[1] or 0)
                elif api_row[0] == 'azure_openai_embedding':
                    embedding_cost = float(api_row[1] or 0)

            total_cost = llm_cost + exa_cost + embedding_cost

            # Previous period LLM cost for delta
            cursor.execute("""
                SELECT ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0)
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
            """, (str(prev_start), str(prev_end)))
            prev_llm_cost = float(cursor.fetchone()[0] or 0)

            # Previous period API cost — single pass for all providers
            cursor.execute("""
                SELECT ISNULL(SUM(cost_usd), 0)
                FROM api_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND provider IN ('exa', 'azure_openai_embedding')
                  AND status = 'success'
            """, (str(prev_start), str(prev_end)))
            prev_api_cost = float(cursor.fetchone()[0] or 0)
            prev_total = prev_llm_cost + prev_api_cost

            delta_percent = 0.0
            if prev_total > 0:
                delta_percent = round(((total_cost - prev_total) / prev_total) * 100, 1)

            # Articles generated count + generation-only cost
            cursor.execute("""
                SELECT COUNT(DISTINCT correlation_id),
                       ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0)
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND action_type = 'generate_article' AND status = 'success'
                  AND correlation_id IS NOT NULL
            """, (str(start_date), str(end_date)))
            row = cursor.fetchone()
            articles_generated = row[0] or 0
            generation_cost = float(row[1] or 0)

            avg_cost_per_article = round(generation_cost / articles_generated, 4) if articles_generated > 0 else 0

            # Monthly projection (based on daily average in period).
            # +1 because SQL uses DATEADD(day,1,end_date) making both endpoints inclusive.
            days_in_period = max((end_date - start_date).days + 1, 1)
            daily_avg = total_cost / days_in_period
            projected_monthly = round(daily_avg * 30, 2)

            # Use 'custom' when caller supplied explicit date range so the
            # frontend doesn't mislabel the card with the default period name.
            effective_period = 'custom' if (start_date_str and end_date_str) else period
            result = {
                'total_cost': round(total_cost, 2),
                'delta_percent': delta_percent,
                'total_calls': llm_calls,
                'sonnet_calls': sonnet_calls,
                'haiku_calls': haiku_calls,
                'avg_cost_per_article': avg_cost_per_article,
                'articles_generated': articles_generated,
                'projected_monthly': projected_monthly,
                'provider_split': {
                    'llm': round(llm_cost, 2),
                    'exa': round(exa_cost, 4),
                    'embeddings': round(embedding_cost, 4),
                },
                'period': effective_period,
                'start_date': str(start_date),
                'end_date': str(end_date),
            }
            _cache_set(_ck, result)
            return result
    except Exception as e:
        logger.error(f"Error getting cost overview: {e}")
        return {
            'total_cost': 0, 'delta_percent': 0, 'total_calls': 0,
            'sonnet_calls': 0, 'haiku_calls': 0, 'avg_cost_per_article': 0,
            'articles_generated': 0, 'projected_monthly': 0,
            'provider_split': {'llm': 0, 'exa': 0, 'embeddings': 0},
            'period': period, 'start_date': '', 'end_date': '',
        }


def get_cost_by_action(start_date, end_date) -> dict:
    """Breakdown by action_type with call counts and costs."""
    _ck = f'breakdown:{start_date}:{end_date}'
    cached = _cache_get(_ck)
    if cached is not None:
        return cached
    try:
        from services.database import get_db
        db = get_db()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # LLM costs by action — keyed dict for O(1) merge with API rows
            cursor.execute("""
                SELECT
                    ISNULL(action_type, 'unknown') as action,
                    COUNT(*) as call_count,
                    ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as total_cost
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY action_type
            """, (str(start_date), str(end_date)))

            action_map = {}
            grand_total = 0.0
            for row in cursor.fetchall():
                action = row[0] or 'unknown'
                cost = float(row[2] or 0)
                action_map[action] = {
                    'action': action,
                    'call_count': row[1] or 0,
                    'total_cost': cost,
                }
                grand_total += cost

            # API costs by action — O(1) merge via dict lookup
            cursor.execute("""
                SELECT
                    ISNULL(action_type, 'unknown') as action,
                    COUNT(*) as call_count,
                    ISNULL(SUM(cost_usd), 0) as total_cost
                FROM api_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY action_type
            """, (str(start_date), str(end_date)))

            for row in cursor.fetchall():
                action = row[0] or 'unknown'
                cost = float(row[2] or 0)
                if action in action_map:
                    action_map[action]['call_count'] += row[1] or 0
                    action_map[action]['total_cost'] += cost
                else:
                    action_map[action] = {
                        'action': action,
                        'call_count': row[1] or 0,
                        'total_cost': cost,
                    }
                grand_total += cost

            # Calculate avg, pct, and round costs in a single pass
            items = []
            for item in action_map.values():
                item['total_cost'] = round(item['total_cost'], 4)
                item['avg_cost'] = round(item['total_cost'] / item['call_count'], 6) if item['call_count'] > 0 else 0
                item['pct_of_total'] = round((item['total_cost'] / grand_total * 100), 1) if grand_total > 0 else 0
                items.append(item)

            items.sort(key=lambda x: x['total_cost'], reverse=True)

            result = {'items': items, 'total_cost': round(grand_total, 2)}
            _cache_set(_ck, result)
            return result
    except Exception as e:
        logger.error(f"Error getting cost by action: {e}")
        return {'items': [], 'total_cost': 0}


def get_cost_by_user(start_date, end_date) -> dict:
    """Per-user cost breakdown, JOINed with users table."""
    _ck = f'by_user:{start_date}:{end_date}'
    cached = _cache_get(_ck)
    if cached is not None:
        return cached
    try:
        from services.database import get_db
        db = get_db()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT TOP 100
                    ISNULL(CAST(l.user_id AS VARCHAR(36)), 'system') as uid,
                    ISNULL(u.name, 'Sistema (Automático)') as user_name,
                    u.email as user_email,
                    SUM(CASE WHEN l.action_type = 'generate_article' THEN 1 ELSE 0 END) as articles_generated,
                    SUM(CASE WHEN l.action_type = 'edit_article' THEN 1 ELSE 0 END) as edits,
                    SUM(CASE WHEN l.action_type IN ('fact_check_scan', 'deep_verify') THEN 1 ELSE 0 END) as scans,
                    ISNULL(SUM(ISNULL(l.input_cost_usd, 0) + ISNULL(l.output_cost_usd, 0)), 0) as total_cost
                FROM llm_usage_log l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE l.created_at >= %s AND l.created_at < DATEADD(day, 1, %s)
                  AND l.status = 'success'
                GROUP BY l.user_id, u.name, u.email
                ORDER BY total_cost DESC
            """, (str(start_date), str(end_date)))

            items = []
            system_cost = 0.0
            for row in cursor.fetchall():
                uid = row[0]
                cost = float(row[6] or 0)
                articles = row[3] or 0

                if uid == 'system' or uid is None or uid == SYSTEM_UUID:
                    system_cost += cost
                    continue

                items.append({
                    'user_id': uid,
                    'user_name': row[1] or 'Desconhecido',
                    'user_email': row[2] or '',
                    'articles_generated': articles,
                    'edits': row[4] or 0,
                    'scans': row[5] or 0,
                    'total_cost': round(cost, 2),
                    'cost_per_article': round(cost / articles, 4) if articles > 0 else 0,
                })

            result = {'items': items, 'system_cost': round(system_cost, 2)}
            _cache_set(_ck, result)
            return result
    except Exception as e:
        logger.error(f"Error getting cost by user: {e}")
        return {'items': [], 'system_cost': 0}


def get_cost_by_source(start_date, end_date) -> dict:
    """Per-source cost breakdown, JOINed with sources table."""
    _ck = f'by_source:{start_date}:{end_date}'
    cached = _cache_get(_ck)
    if cached is not None:
        return cached
    try:
        from services.database import get_db
        db = get_db()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT TOP 100
                    CAST(l.source_id AS VARCHAR(36)) as sid,
                    ISNULL(s.name, 'Desconhecida') as source_name,
                    s.category,
                    COUNT(*) as articles_collected,
                    ISNULL(SUM(ISNULL(l.input_cost_usd, 0) + ISNULL(l.output_cost_usd, 0)), 0) as total_cost
                FROM llm_usage_log l
                LEFT JOIN sources s ON l.source_id = s.id
                WHERE l.created_at >= %s AND l.created_at < DATEADD(day, 1, %s)
                  AND l.status = 'success'
                  AND l.source_id IS NOT NULL
                GROUP BY l.source_id, s.name, s.category
                ORDER BY total_cost DESC
            """, (str(start_date), str(end_date)))

            items = []
            for row in cursor.fetchall():
                cost = float(row[4] or 0)
                articles = row[3] or 0
                items.append({
                    'source_id': row[0],
                    'source_name': row[1] or 'Desconhecida',
                    'category': row[2] or '',
                    'articles_collected': articles,
                    'total_cost': round(cost, 4),
                    'cost_per_article': round(cost / articles, 6) if articles > 0 else 0,
                })

            result = {'items': items}
            _cache_set(_ck, result)
            return result
    except Exception as e:
        logger.error(f"Error getting cost by source: {e}")
        return {'items': []}


def get_cost_trends(granularity: str, start_date, end_date) -> dict:
    """Time series cost data at given granularity."""
    _ck = f'trends:{granularity}:{start_date}:{end_date}'
    cached = _cache_get(_ck)
    if cached is not None:
        return cached
    try:
        from services.database import get_db
        db = get_db()

        # Pre-built static queries per granularity to avoid f-string SQL interpolation.
        # All date expressions are hardcoded constants — no user input reaches SQL.
        _LLM_QUERIES = {
            'hour': """
                SELECT
                    CAST(DATEADD(HOUR, DATEDIFF(HOUR, 0, created_at), 0) AS VARCHAR(16)) as period,
                    ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as llm_cost
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CAST(DATEADD(HOUR, DATEDIFF(HOUR, 0, created_at), 0) AS VARCHAR(16))
                ORDER BY period
            """,
            'day': """
                SELECT
                    CONVERT(VARCHAR(10), created_at, 120) as period,
                    ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as llm_cost
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CONVERT(VARCHAR(10), created_at, 120)
                ORDER BY period
            """,
            'week': """
                SELECT
                    CONVERT(VARCHAR(10), DATEADD(wk, DATEDIFF(wk, '19000101', created_at), '19000101'), 120) as period,
                    ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as llm_cost
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CONVERT(VARCHAR(10), DATEADD(wk, DATEDIFF(wk, '19000101', created_at), '19000101'), 120)
                ORDER BY period
            """,
            'month': """
                SELECT
                    CONVERT(VARCHAR(7), created_at, 120) as period,
                    ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as llm_cost
                FROM llm_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CONVERT(VARCHAR(7), created_at, 120)
                ORDER BY period
            """,
        }

        _API_QUERIES = {
            'hour': """
                SELECT
                    CAST(DATEADD(HOUR, DATEDIFF(HOUR, 0, created_at), 0) AS VARCHAR(16)) as period,
                    provider,
                    ISNULL(SUM(cost_usd), 0) as api_cost
                FROM api_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CAST(DATEADD(HOUR, DATEDIFF(HOUR, 0, created_at), 0) AS VARCHAR(16)), provider
                ORDER BY period
            """,
            'day': """
                SELECT
                    CONVERT(VARCHAR(10), created_at, 120) as period,
                    provider,
                    ISNULL(SUM(cost_usd), 0) as api_cost
                FROM api_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CONVERT(VARCHAR(10), created_at, 120), provider
                ORDER BY period
            """,
            'week': """
                SELECT
                    CONVERT(VARCHAR(10), DATEADD(wk, DATEDIFF(wk, '19000101', created_at), '19000101'), 120) as period,
                    provider,
                    ISNULL(SUM(cost_usd), 0) as api_cost
                FROM api_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CONVERT(VARCHAR(10), DATEADD(wk, DATEDIFF(wk, '19000101', created_at), '19000101'), 120), provider
                ORDER BY period
            """,
            'month': """
                SELECT
                    CONVERT(VARCHAR(7), created_at, 120) as period,
                    provider,
                    ISNULL(SUM(cost_usd), 0) as api_cost
                FROM api_usage_log
                WHERE created_at >= %s AND created_at < DATEADD(day, 1, %s)
                  AND status = 'success'
                GROUP BY CONVERT(VARCHAR(7), created_at, 120), provider
                ORDER BY period
            """,
        }

        # Default to 'month' if granularity not in allowlist
        safe_granularity = granularity if granularity in _LLM_QUERIES else 'month'

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # LLM costs
            cursor.execute(
                _LLM_QUERIES[safe_granularity],
                (str(start_date), str(end_date)),
            )

            period_data = {}
            for row in cursor.fetchall():
                period_data[row[0]] = {
                    'date': row[0],
                    'llm': round(float(row[1] or 0), 4),
                    'exa': 0,
                    'embeddings': 0,
                }

            # API costs (Exa + embeddings)
            cursor.execute(
                _API_QUERIES[safe_granularity],
                (str(start_date), str(end_date)),
            )

            for row in cursor.fetchall():
                period_key = row[0]
                provider = row[1]
                cost = round(float(row[2] or 0), 6)

                if period_key not in period_data:
                    period_data[period_key] = {
                        'date': period_key,
                        'llm': 0,
                        'exa': 0,
                        'embeddings': 0,
                    }

                if provider == 'exa':
                    period_data[period_key]['exa'] = cost
                elif provider == 'azure_openai_embedding':
                    period_data[period_key]['embeddings'] = cost

            # Build final data with totals
            data = []
            for entry in sorted(period_data.values(), key=lambda x: x['date']):
                entry['total'] = round(entry['llm'] + entry['exa'] + entry['embeddings'], 4)
                data.append(entry)

            result = {'granularity': granularity, 'data': data}
            _cache_set(_ck, result)
            return result
    except Exception as e:
        logger.error(f"Error getting cost trends: {e}")
        return {'granularity': granularity, 'data': []}


def get_source_cost_estimate() -> dict:
    """Average cost per active source for what-if calculator."""
    cached = _cache_get('source_estimate')
    if cached is not None:
        return cached
    try:
        from services.database import get_db
        db = get_db()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Active sources count
            cursor.execute("SELECT COUNT(*) FROM sources WHERE active = 1 AND is_deleted = 0")
            active_sources = cursor.fetchone()[0] or 0

            # Avg articles collected per source per day (last 7 days).
            # TOP 2000 on the inner scan caps the number of rows read before grouping,
            # preventing a full table scan on large collected_articles tables.
            cursor.execute("""
                SELECT CAST(AVG(CAST(daily_count AS FLOAT)) AS FLOAT)
                FROM (
                    SELECT source_id, CONVERT(DATE, published_at) as d, COUNT(*) as daily_count
                    FROM (SELECT TOP 2000 source_id, published_at
                          FROM collected_articles
                          WHERE published_at >= DATEADD(day, -7, GETUTCDATE())
                            AND is_deleted = 0
                          ORDER BY published_at DESC) recent
                    GROUP BY source_id, CONVERT(DATE, published_at)
                ) sub
            """)
            avg_articles_per_source_per_day = round(float(cursor.fetchone()[0] or 20), 1)

            # Avg pipeline cost per article (classification + scoring + embedding)
            cursor.execute("""
                SELECT AVG(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0))
                FROM llm_usage_log
                WHERE action_type IN ('system_rss', 'system_scoring', 'system_embedding')
                  AND created_at >= DATEADD(day, -7, GETUTCDATE())
                  AND status = 'success'
            """)
            avg_cost_per_article_pipeline = round(float(cursor.fetchone()[0] or 0.002), 6)

            # Avg cost per generated article — single aggregate with HAVING, avoids nested subquery
            cursor.execute("""
                SELECT AVG(per_article_cost)
                FROM (
                    SELECT TOP 500
                        SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)) as per_article_cost
                    FROM llm_usage_log
                    WHERE action_type = 'generate_article'
                      AND created_at >= DATEADD(day, -7, GETUTCDATE())
                      AND status = 'success'
                      AND correlation_id IS NOT NULL
                    GROUP BY correlation_id
                ) sub
            """)
            avg_cost_per_generated_article = round(float(cursor.fetchone()[0] or 0.18), 4)

            # Distinct generated articles (last 7 days) — reuse same connection
            cursor.execute("""
                SELECT COUNT(DISTINCT correlation_id)
                FROM llm_usage_log
                WHERE action_type = 'generate_article'
                  AND created_at >= DATEADD(day, -7, GETUTCDATE())
                  AND status = 'success'
                  AND correlation_id IS NOT NULL
            """)
            total_generated = cursor.fetchone()[0] or 0
            avg_articles_generated_per_source = round(total_generated / max(active_sources, 1) / 7, 2)

            # Total daily pipeline cost
            total_daily_pipeline_cost = round(
                active_sources * avg_articles_per_source_per_day * avg_cost_per_article_pipeline, 2
            )

            result = {
                'avg_articles_per_source_per_day': avg_articles_per_source_per_day,
                'avg_cost_per_article_pipeline': avg_cost_per_article_pipeline,
                'avg_cost_per_generated_article': avg_cost_per_generated_article,
                'avg_articles_generated_per_source': avg_articles_generated_per_source,
                'active_sources': active_sources,
                'total_daily_pipeline_cost': total_daily_pipeline_cost,
            }
            _cache_set('source_estimate', result, ttl=_TTL_LONG)
            return result
    except Exception as e:
        logger.error(f"Error getting source cost estimate: {e}")
        return {
            'avg_articles_per_source_per_day': 0,
            'avg_cost_per_article_pipeline': 0,
            'avg_cost_per_generated_article': 0,
            'avg_articles_generated_per_source': 0,
            'active_sources': 0,
            'total_daily_pipeline_cost': 0,
        }


async def aggregate_daily_costs(target_date: date) -> dict:
    """
    Aggregate raw logs into daily_cost_summary and daily_cost_detail.
    Called by daily timer at 00:30 UTC for yesterday's data.
    Uses MERGE/UPSERT pattern for idempotency.
    """
    try:
        from services.database import get_db
        db = get_db()

        date_str = str(target_date)
        next_date_str = str(target_date + timedelta(days=1))

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # MERGE into daily_cost_summary from LLM logs
            cursor.execute("""
                MERGE daily_cost_summary AS target
                USING (
                    SELECT
                        CONVERT(DATE, created_at) as date,
                        ISNULL(provider, 'unknown') as provider,
                        ISNULL(action_type, 'unknown') as action_type,
                        COUNT(*) as call_count,
                        ISNULL(SUM(input_tokens), 0) as total_input_tokens,
                        ISNULL(SUM(output_tokens), 0) as total_output_tokens,
                        ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as total_cost_usd,
                        AVG(latency_ms) as avg_latency_ms
                    FROM llm_usage_log
                    WHERE created_at >= %s AND created_at < %s
                    GROUP BY CONVERT(DATE, created_at), provider, action_type
                ) AS source
                ON target.date = source.date
                   AND target.provider = source.provider
                   AND target.action_type = source.action_type
                WHEN MATCHED THEN UPDATE SET
                    call_count = source.call_count,
                    total_input_tokens = source.total_input_tokens,
                    total_output_tokens = source.total_output_tokens,
                    total_cost_usd = source.total_cost_usd,
                    avg_latency_ms = source.avg_latency_ms
                WHEN NOT MATCHED THEN INSERT
                    (date, provider, action_type, call_count, total_input_tokens,
                     total_output_tokens, total_cost_usd, avg_latency_ms)
                VALUES (source.date, source.provider, source.action_type, source.call_count,
                        source.total_input_tokens, source.total_output_tokens,
                        source.total_cost_usd, source.avg_latency_ms);
            """, (date_str, next_date_str))

            # MERGE API usage into daily_cost_summary
            cursor.execute("""
                MERGE daily_cost_summary AS target
                USING (
                    SELECT
                        CONVERT(DATE, created_at) as date,
                        provider,
                        ISNULL(action_type, 'unknown') as action_type,
                        COUNT(*) as call_count,
                        0 as total_input_tokens,
                        0 as total_output_tokens,
                        ISNULL(SUM(cost_usd), 0) as total_cost_usd,
                        AVG(latency_ms) as avg_latency_ms
                    FROM api_usage_log
                    WHERE created_at >= %s AND created_at < %s
                    GROUP BY CONVERT(DATE, created_at), provider, action_type
                ) AS source
                ON target.date = source.date
                   AND target.provider = source.provider
                   AND target.action_type = source.action_type
                WHEN MATCHED THEN UPDATE SET
                    call_count = source.call_count,
                    total_cost_usd = source.total_cost_usd
                WHEN NOT MATCHED THEN INSERT
                    (date, provider, action_type, call_count, total_input_tokens,
                     total_output_tokens, total_cost_usd, avg_latency_ms)
                VALUES (source.date, source.provider, source.action_type, source.call_count,
                        0, 0, source.total_cost_usd, source.avg_latency_ms);
            """, (date_str, next_date_str))

            # MERGE into daily_cost_detail (LLM)
            cursor.execute("""
                MERGE daily_cost_detail AS target
                USING (
                    SELECT
                        CONVERT(DATE, created_at) as date,
                        ISNULL(provider, 'unknown') as provider,
                        ISNULL(model, '') as model,
                        ISNULL(task_type, '') as task_type,
                        ISNULL(action_type, 'unknown') as action_type,
                        ISNULL(user_id, '00000000-0000-0000-0000-000000000000') as user_id,
                        ISNULL(source_id, '00000000-0000-0000-0000-000000000000') as source_id,
                        COUNT(*) as call_count,
                        ISNULL(SUM(input_tokens), 0) as total_input_tokens,
                        ISNULL(SUM(output_tokens), 0) as total_output_tokens,
                        ISNULL(SUM(ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)), 0) as total_cost_usd,
                        AVG(latency_ms) as avg_latency_ms
                    FROM llm_usage_log
                    WHERE created_at >= %s AND created_at < %s
                    GROUP BY CONVERT(DATE, created_at), provider, model, task_type, action_type, user_id, source_id
                ) AS source
                ON target.date = source.date
                   AND target.provider = source.provider
                   AND target.model = source.model
                   AND target.task_type = source.task_type
                   AND target.action_type = source.action_type
                   AND target.user_id = source.user_id
                   AND target.source_id = source.source_id
                WHEN MATCHED THEN UPDATE SET
                    call_count = source.call_count,
                    total_input_tokens = source.total_input_tokens,
                    total_output_tokens = source.total_output_tokens,
                    total_cost_usd = source.total_cost_usd,
                    avg_latency_ms = source.avg_latency_ms
                WHEN NOT MATCHED THEN INSERT
                    (date, provider, model, task_type, action_type, user_id, source_id,
                     call_count, total_input_tokens, total_output_tokens, total_cost_usd, avg_latency_ms)
                VALUES (source.date, source.provider, source.model, source.task_type, source.action_type,
                        source.user_id, source.source_id, source.call_count, source.total_input_tokens,
                        source.total_output_tokens, source.total_cost_usd, source.avg_latency_ms);
            """, (date_str, next_date_str))

            # MERGE API usage into daily_cost_detail
            cursor.execute("""
                MERGE daily_cost_detail AS target
                USING (
                    SELECT
                        CONVERT(DATE, created_at) as date,
                        provider,
                        '' as model,
                        '' as task_type,
                        ISNULL(action_type, 'unknown') as action_type,
                        ISNULL(user_id, '00000000-0000-0000-0000-000000000000') as user_id,
                        ISNULL(source_id, '00000000-0000-0000-0000-000000000000') as source_id,
                        COUNT(*) as call_count,
                        0 as total_input_tokens,
                        0 as total_output_tokens,
                        ISNULL(SUM(cost_usd), 0) as total_cost_usd,
                        AVG(latency_ms) as avg_latency_ms
                    FROM api_usage_log
                    WHERE created_at >= %s AND created_at < %s
                    GROUP BY CONVERT(DATE, created_at), provider, action_type, user_id, source_id
                ) AS source
                ON target.date = source.date
                   AND target.provider = source.provider
                   AND target.model = source.model
                   AND target.task_type = source.task_type
                   AND target.action_type = source.action_type
                   AND target.user_id = source.user_id
                   AND target.source_id = source.source_id
                WHEN MATCHED THEN UPDATE SET
                    call_count = source.call_count,
                    total_cost_usd = source.total_cost_usd
                WHEN NOT MATCHED THEN INSERT
                    (date, provider, model, task_type, action_type, user_id, source_id,
                     call_count, total_input_tokens, total_output_tokens, total_cost_usd, avg_latency_ms)
                VALUES (source.date, source.provider, source.model, source.task_type, source.action_type,
                        source.user_id, source.source_id, source.call_count, 0, 0,
                        source.total_cost_usd, source.avg_latency_ms);
            """, (date_str, next_date_str))

            conn.commit()

        logger.info(f"Daily cost aggregation complete for {date_str}")
        return {'status': 'ok', 'date': date_str}

    except Exception as e:
        logger.error(f"Error aggregating daily costs for {target_date}: {e}")
        return {'status': 'error', 'error': str(e)}
