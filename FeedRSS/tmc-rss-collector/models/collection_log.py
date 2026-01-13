"""
Model CollectionLog - Representa um log de coleta.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4


class CollectionLogCreate(BaseModel):
    """Schema para criar um log de coleta."""
    source_id: Optional[UUID] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., pattern=r'^(success|partial|error)$')
    articles_found: int = 0
    articles_new: int = 0
    articles_duplicate: int = 0
    error_message: Optional[str] = None
    duration_ms: int = 0


class CollectionLog(CollectionLogCreate):
    """Schema completo do log (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    finished_at: Optional[datetime] = None

    # Campo extra para response (preenchido via JOIN)
    source_name: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

    def to_api_response(self) -> dict:
        """Converte para formato de resposta da API."""
        return {
            "id": str(self.id),
            "sourceId": str(self.source_id) if self.source_id else None,
            "sourceName": self.source_name,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "finishedAt": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "articlesFound": self.articles_found,
            "articlesNew": self.articles_new,
            "articlesDuplicate": self.articles_duplicate,
            "errorMessage": self.error_message,
            "durationMs": self.duration_ms
        }
