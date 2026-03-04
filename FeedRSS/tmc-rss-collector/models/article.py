"""
Model Article - Representa um artigo coletado de um feed RSS.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
import json


class ArticleBase(BaseModel):
    """Campos base para Article."""
    title: str = Field(..., min_length=1, max_length=1000)
    content: Optional[str] = None
    preview: Optional[str] = Field(None, max_length=500)
    url: str = Field(..., min_length=10, max_length=2048)
    image_url: Optional[str] = Field(None, max_length=2048)
    author: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None


class ArticleCreate(ArticleBase):
    """Schema para criar um novo artigo."""
    source_id: UUID
    hash: str = Field(..., min_length=32, max_length=64)
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class Article(ArticleBase):
    """Schema completo do artigo (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    hash: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    # Campos extras para response (preenchidos via JOIN)
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    favicon: Optional[str] = None

    # Score (preenchido via LEFT JOIN com article_scores)
    score: Optional[int] = None
    score_classification: Optional[str] = None
    score_inesperado: Optional[int] = None
    score_impacto: Optional[int] = None
    score_busca_agora: Optional[int] = None
    score_conversa: Optional[int] = None

    model_config = {
        "from_attributes": True
    }

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        """Parse tags de JSON string para lista."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []

    def generate_preview(self, max_length: int = 500) -> str:
        """Gera preview a partir do content se nao existir."""
        if self.preview:
            return self.preview

        if not self.content:
            return self.title

        # Remover tags HTML basicas
        import re
        text = re.sub(r'<[^>]+>', '', self.content)
        text = ' '.join(text.split())  # Normalizar espacos

        if len(text) <= max_length:
            return text

        return text[:max_length-3] + '...'

    def to_frontend_format(self) -> dict:
        """
        Converte para formato esperado pelo frontend React.

        Formato esperado (baseado em mockData.js):
        {
            id: "uuid",
            title: "Titulo",
            source: "G1",
            sourceUrl: "https://g1.globo.com",
            favicon: "https://www.google.com/s2/favicons?domain=g1.globo.com&sz=32",
            category: "Politica",
            tags: ["economia", "governo"],
            publishedAt: "2025-01-07T10:30:00Z",
            preview: "Resumo...",
            content: "Conteudo completo...",
            url: "https://g1.globo.com/noticia/1"
        }
        """
        return {
            "id": str(self.id),
            "title": self.title,
            "source": self.source_name or "Unknown",
            "sourceUrl": self.source_url or "",
            "favicon": self.favicon or f"https://www.google.com/s2/favicons?domain=example.com&sz=32",
            "category": self.category,
            "tags": self.tags,
            "publishedAt": self.published_at.isoformat() if self.published_at else None,
            "preview": self.generate_preview(),
            "content": self.content,
            "url": self.url,
            "imageUrl": self.image_url,
            "author": self.author,
            "collectedAt": self.collected_at.isoformat() if self.collected_at else None,
            "score": self.score,
            "scoreClassification": self.score_classification,
            "scoreInesperado": self.score_inesperado,
            "scoreImpacto": self.score_impacto,
            "scoreBuscaAgora": self.score_busca_agora,
            "scoreConversa": self.score_conversa
        }


class ArticleListResponse(BaseModel):
    """Schema para resposta paginada de artigos."""
    items: List[Article]
    total: int
    page: int
    pages: int

    def to_frontend_format(self) -> dict:
        """Converte lista para formato frontend."""
        return {
            "items": [article.to_frontend_format() for article in self.items],
            "total": self.total,
            "page": self.page,
            "pages": self.pages
        }
