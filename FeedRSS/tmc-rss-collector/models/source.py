"""
Model Source - Representa uma fonte RSS cadastrada.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID, uuid4


class SourceBase(BaseModel):
    """Campos base para Source."""
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=10, max_length=2048)
    favicon_url: Optional[str] = Field(None, max_length=2048)
    active: bool = True
    frequency: str = Field(default="1h", pattern=r'^(15min|30min|1h|2h|6h)$')
    category: Optional[str] = Field(None, max_length=100)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class SourceCreate(SourceBase):
    """Schema para criar uma nova fonte."""
    pass


class SourceUpdate(BaseModel):
    """Schema para atualizar uma fonte (todos campos opcionais)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, min_length=10, max_length=2048)
    favicon_url: Optional[str] = Field(None, max_length=2048)
    active: Optional[bool] = None
    frequency: Optional[str] = Field(None, pattern=r'^(15min|30min|1h|2h|6h)$')
    category: Optional[str] = Field(None, max_length=100)


class Source(SourceBase):
    """Schema completo da fonte (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    last_fetch: Optional[datetime] = None
    last_error: Optional[str] = None
    articles_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

    def should_fetch(self, now: Optional[datetime] = None) -> bool:
        """
        Verifica se a fonte deve ser coletada agora baseado na frequencia.

        Args:
            now: Datetime atual (usa UTC se nao fornecido)

        Returns:
            True se deve coletar, False caso contrario
        """
        if now is None:
            now = datetime.utcnow()

        # Primeira coleta: sempre executar
        if self.last_fetch is None:
            return True

        # Mapear frequencia para intervalo
        intervals = {
            '15min': timedelta(minutes=15),
            '30min': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '2h': timedelta(hours=2),
            '6h': timedelta(hours=6),
        }

        interval = intervals.get(self.frequency, timedelta(hours=1))
        elapsed = now - self.last_fetch

        return elapsed >= interval

    def get_base_url(self) -> str:
        """Extrai a URL base do site a partir da URL do feed."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def to_api_response(self) -> dict:
        """Converte para formato de resposta da API."""
        return {
            "id": str(self.id),
            "name": self.name,
            "url": self.url,
            "favicon": self.favicon_url or f"https://www.google.com/s2/favicons?domain={self.get_base_url()}&sz=32",
            "active": self.active,
            "frequency": self.frequency,
            "category": self.category,
            "lastFetch": self.last_fetch.isoformat() if self.last_fetch else None,
            "lastError": self.last_error,
            "articlesCount": self.articles_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }
