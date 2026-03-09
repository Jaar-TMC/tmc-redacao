"""
API REST para gerenciamento de fontes RSS.
"""

import azure.functions as func
import json
import logging
from uuid import UUID
import asyncio

from services.database import get_db
from models import SourceCreate, SourceUpdate

logger = logging.getLogger(__name__)


async def list_sources_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/sources

    Lista todas as fontes RSS cadastradas.
    """
    try:
        db = get_db()
        sources = db.get_all_sources()

        response = {
            "items": [source.to_api_response() for source in sources],
            "total": len(sources)
        }

        return func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def get_source_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/sources/{id}

    Retorna uma fonte especifica pelo ID.
    """
    try:
        source_id = req.route_params.get('id')

        if not source_id:
            return func.HttpResponse(
                json.dumps({"error": "Source ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()
        source = db.get_source_by_id(source_id)

        if not source:
            return func.HttpResponse(
                json.dumps({"error": "Source not found"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(source.to_api_response(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting source: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def create_source_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/sources

    Cria uma nova fonte RSS.

    Body:
        {
            "name": "G1 - Politica",
            "url": "https://g1.globo.com/rss/g1/politica/",
            "category": "Politica",
            "frequency": "30min",
            "active": true
        }
    """
    try:
        # Parse body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validar campos obrigatorios
        if not body.get('name'):
            return func.HttpResponse(
                json.dumps({"error": "Name is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not body.get('url'):
            return func.HttpResponse(
                json.dumps({"error": "URL is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Criar model
        try:
            source_data = SourceCreate(
                name=body.get('name'),
                url=body.get('url'),
                favicon_url=body.get('favicon_url'),
                active=body.get('active', True),
                frequency=body.get('frequency', '1h'),
                category=body.get('category')
            )
        except ValueError as e:
            logger.warning(f"Source create validation error: {e}")
            return func.HttpResponse(
                json.dumps({"error": "Erro de validacao nos dados da fonte"}),
                status_code=400,
                mimetype="application/json"
            )

        # Inserir no banco
        db = get_db()
        source = db.create_source(source_data)

        return func.HttpResponse(
            json.dumps(source.to_api_response(), default=str),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating source: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def update_source_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/sources/{id}

    Atualiza uma fonte existente.
    """
    try:
        source_id = req.route_params.get('id')

        if not source_id:
            return func.HttpResponse(
                json.dumps({"error": "Source ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Parse body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Criar model de update
        try:
            update_data = SourceUpdate(
                name=body.get('name'),
                url=body.get('url'),
                favicon_url=body.get('favicon_url'),
                active=body.get('active'),
                frequency=body.get('frequency'),
                category=body.get('category')
            )
        except ValueError as e:
            logger.warning(f"Source update validation error: {e}")
            return func.HttpResponse(
                json.dumps({"error": "Erro de validacao nos dados da fonte"}),
                status_code=400,
                mimetype="application/json"
            )

        # Atualizar no banco
        db = get_db()
        source = db.update_source(source_id, update_data)

        if not source:
            return func.HttpResponse(
                json.dumps({"error": "Source not found"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(source.to_api_response(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error updating source: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def delete_source_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/sources/{id}

    Desativa uma fonte (soft delete).
    """
    try:
        source_id = req.route_params.get('id')

        if not source_id:
            return func.HttpResponse(
                json.dumps({"error": "Source ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()
        deleted = db.delete_source(source_id)

        if not deleted:
            return func.HttpResponse(
                json.dumps({"error": "Source not found"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({"message": "Source deactivated successfully"}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error deleting source: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def collect_source_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/sources/{id}/collect

    Dispara coleta manual de uma fonte especifica.
    """
    try:
        source_id = req.route_params.get('id')

        if not source_id:
            return func.HttpResponse(
                json.dumps({"error": "Source ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Importar handler de coleta
        from .rss_collector import collect_single_source_handler

        # Executar coleta
        result = await collect_single_source_handler(source_id)

        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.warning(f"Source collection error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Fonte nao encontrada"}),
            status_code=404,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error collecting source: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
