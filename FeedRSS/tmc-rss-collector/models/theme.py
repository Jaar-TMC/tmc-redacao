"""
Model Theme - Representa um tema semantico para clustering de artigos.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID, uuid4
import json


class ThemeBase(BaseModel):
    """Campos base para Theme."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-z0-9-]+$')


class ThemeCreate(ThemeBase):
    """Schema para criar um novo tema."""
    centroid: Optional[List[float]] = Field(None, description="Embedding centroid (1536 dimensions)")
    status: Literal['active', 'inactive'] = 'active'

    @field_validator('centroid')
    @classmethod
    def validate_centroid_dimensions(cls, v):
        """Valida que o centroid tem 1536 dimensoes (OpenAI ada-002)."""
        if v is not None and len(v) != 1536:
            raise ValueError(f'Centroid must have exactly 1536 dimensions, got {len(v)}')
        return v


class ThemeUpdate(BaseModel):
    """Schema para atualizar um tema (todos campos opcionais)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255, pattern=r'^[a-z0-9-]+$')
    centroid: Optional[List[float]] = Field(None, description="Embedding centroid (1536 dimensions)")
    status: Optional[Literal['active', 'inactive']] = None
    classification: Optional[Literal['A', 'B', 'C']] = None

    @field_validator('centroid')
    @classmethod
    def validate_centroid_dimensions(cls, v):
        """Valida que o centroid tem 1536 dimensoes (OpenAI ada-002)."""
        if v is not None and len(v) != 1536:
            raise ValueError(f'Centroid must have exactly 1536 dimensions, got {len(v)}')
        return v


class Theme(ThemeBase):
    """Schema completo do tema (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    centroid: Optional[List[float]] = Field(None, description="Embedding centroid (1536 dimensions)")
    article_count: int = Field(default=0, ge=0)
    avg_score: float = Field(default=0.0, ge=0.0)
    classification: Optional[Literal['A', 'B', 'C']] = None
    status: Literal['active', 'inactive'] = 'active'
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Event-based clustering fields
    canonical_event_key: Optional[str] = Field(
        None,
        max_length=500,
        description="Canonical key for event matching: pessoa|org|acao|local|periodo"
    )
    primary_entities: Optional[dict] = Field(
        None,
        description="Primary entities of the event: {people, organizations, locations, event_action}"
    )
    seed_article_id: Optional[UUID] = Field(
        None,
        description="ID of the seed article that started this theme"
    )

    model_config = {
        "from_attributes": True
    }

    @field_validator('centroid', mode='before')
    @classmethod
    def parse_centroid(cls, v):
        """Parse centroid de JSON string para lista."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    @field_validator('primary_entities', mode='before')
    @classmethod
    def parse_primary_entities(cls, v):
        """Parse primary_entities de JSON string para dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    def to_api_response(self, include_centroid: bool = False, include_event_data: bool = False) -> dict:
        """
        Converte para formato de resposta da API.

        Args:
            include_centroid: Se True, inclui o vetor centroid (pode ser grande).
                             Default False para economizar bandwidth.
            include_event_data: Se True, inclui dados de evento (canonical_key, entities).
        """
        response = {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "articleCount": self.article_count,
            "avgScore": round(self.avg_score, 2),
            "classification": self.classification,
            "status": self.status,
            "firstSeenAt": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "lastUpdatedAt": self.last_updated_at.isoformat() if self.last_updated_at else None
        }

        if include_centroid and self.centroid:
            response["centroid"] = self.centroid

        if include_event_data:
            response["canonicalEventKey"] = self.canonical_event_key
            response["primaryEntities"] = self.primary_entities
            response["seedArticleId"] = str(self.seed_article_id) if self.seed_article_id else None

        return response

    def get_event_summary(self) -> Optional[str]:
        """
        Get a human-readable summary of the event.

        Returns:
            Summary string like "Joao Silva detido em Miami" or None if no event data
        """
        if not self.primary_entities:
            return None

        people = self.primary_entities.get('people', [])
        orgs = self.primary_entities.get('organizations', [])
        locations = self.primary_entities.get('locations', [])
        action = self.primary_entities.get('event_action', '')

        # Build summary
        subject = people[0] if people else (orgs[0] if orgs else None)
        location = locations[0] if locations else None

        if not subject:
            return None

        parts = [subject]
        if action:
            parts.append(action)
        if location:
            parts.append(f"em {location}")

        return ' '.join(parts)


class ThemeResponse(BaseModel):
    """Schema para resposta de um unico tema."""
    id: UUID
    name: str
    slug: str
    article_count: int
    avg_score: float
    classification: Optional[str]
    status: str
    first_seen_at: datetime
    last_updated_at: datetime
    centroid: Optional[List[float]] = None

    model_config = {
        "from_attributes": True
    }


class ThemeListResponse(BaseModel):
    """Schema para resposta paginada de temas."""
    items: List[Theme]
    total: int
    page: int
    pages: int

    def to_api_response(self) -> dict:
        """Converte lista para formato de resposta da API."""
        return {
            "items": [theme.to_api_response() for theme in self.items],
            "total": self.total,
            "page": self.page,
            "pages": self.pages
        }
