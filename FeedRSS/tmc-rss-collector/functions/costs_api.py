"""
Cost dashboard API endpoints.

All endpoints require admin role via @require_admin decorator.
Response format: direct JSON (no {success: true, data: ...} envelope).
Errors use {"error": "message"} consistent with all existing endpoints.
"""

import json
import logging
import azure.functions as func

logger = logging.getLogger(__name__)


def create_error_response(message: str, status_code: int = 400) -> func.HttpResponse:
    """Create a standardized error response."""
    return func.HttpResponse(
        json.dumps({"error": message}, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json"
    )


def create_success_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a standardized success response."""
    return func.HttpResponse(
        json.dumps(data, ensure_ascii=False, default=str),
        status_code=status_code,
        mimetype="application/json"
    )


async def costs_overview_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/costs/overview
    Params: period (today|7d|30d|90d|year, default 30d) OR start_date+end_date (YYYY-MM-DD)
    """
    try:
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')
        period = req.params.get('period', '30d')

        from services.cost_queries import get_cost_overview
        if start_date and end_date:
            data = get_cost_overview(period, start_date_str=start_date, end_date_str=end_date)
        else:
            if period not in ('today', '7d', '30d', '90d', 'year'):
                return create_error_response("Periodo invalido. Use: today, 7d, 30d, 90d, year", 400)
            data = get_cost_overview(period)
        return create_success_response(data)
    except Exception as e:
        logger.exception(f"Error in costs overview: {e}")
        return create_error_response("Internal server error", 500)


async def costs_trends_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/costs/trends
    Params: granularity (hour|day|week|month), start_date, end_date
    """
    try:
        period = req.params.get('period', '30d')
        granularity = req.params.get('granularity')
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')

        # If no explicit dates, derive from period
        if not start_date or not end_date:
            from services.cost_queries import period_to_dates
            s, e = period_to_dates(period)
            start_date = start_date or str(s)
            end_date = end_date or str(e)

        # Default granularity based on period
        if not granularity:
            if period == 'today':
                granularity = 'hour'
            elif period in ('7d', '30d'):
                granularity = 'day'
            elif period == '90d':
                granularity = 'week'
            else:
                granularity = 'month'

        if granularity not in ('hour', 'day', 'week', 'month'):
            return create_error_response("Granularidade invalida. Use: hour, day, week, month", 400)

        from services.cost_queries import get_cost_trends
        data = get_cost_trends(granularity, start_date, end_date)
        return create_success_response(data)
    except Exception as e:
        logger.exception(f"Error in costs trends: {e}")
        return create_error_response("Internal server error", 500)


async def costs_breakdown_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/costs/breakdown
    Params: period (or start_date+end_date), group_by (action|task|model)
    """
    try:
        period = req.params.get('period', '30d')
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')

        if not start_date or not end_date:
            from services.cost_queries import period_to_dates
            s, e = period_to_dates(period)
            start_date = start_date or str(s)
            end_date = end_date or str(e)

        from services.cost_queries import get_cost_by_action
        data = get_cost_by_action(start_date, end_date)
        return create_success_response(data)
    except Exception as e:
        logger.exception(f"Error in costs breakdown: {e}")
        return create_error_response("Internal server error", 500)


async def costs_by_user_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/costs/by-user
    Params: period (or start_date+end_date)
    """
    try:
        period = req.params.get('period', '30d')
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')

        if not start_date or not end_date:
            from services.cost_queries import period_to_dates
            s, e = period_to_dates(period)
            start_date = start_date or str(s)
            end_date = end_date or str(e)

        from services.cost_queries import get_cost_by_user
        data = get_cost_by_user(start_date, end_date)
        return create_success_response(data)
    except Exception as e:
        logger.exception(f"Error in costs by user: {e}")
        return create_error_response("Internal server error", 500)


async def costs_by_source_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/costs/by-source
    Params: period (or start_date+end_date)
    """
    try:
        period = req.params.get('period', '30d')
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')

        if not start_date or not end_date:
            from services.cost_queries import period_to_dates
            s, e = period_to_dates(period)
            start_date = start_date or str(s)
            end_date = end_date or str(e)

        from services.cost_queries import get_cost_by_source
        data = get_cost_by_source(start_date, end_date)
        return create_success_response(data)
    except Exception as e:
        logger.exception(f"Error in costs by source: {e}")
        return create_error_response("Internal server error", 500)


async def costs_source_estimate_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/costs/source-estimate
    No params required.
    """
    try:
        from services.cost_queries import get_source_cost_estimate
        data = get_source_cost_estimate()
        return create_success_response(data)
    except Exception as e:
        logger.exception(f"Error in source cost estimate: {e}")
        return create_error_response("Internal server error", 500)
