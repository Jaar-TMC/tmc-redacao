"""
Model UserArticle - Representa uma materia criada pelo usuario.
Armazena artigos gerados pela ferramenta (rascunhos e publicados).
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID, uuid4
import json


class UserArticleBase(BaseModel):
    """Campos base para UserArticle."""
    title: str = Field(..., min_length=1, max_length=1000)
    linha_fina: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    preview: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)
    author_name: Optional[str] = Field(None, max_length=255)


class UserArticleCreate(UserArticleBase):
    """Schema para criar um novo artigo de usuario."""
    status: Literal['draft', 'published'] = 'draft'
    source_article_ids: List[str] = Field(default_factory=list)
    generation_config: Optional[dict] = None


class UserArticleUpdate(BaseModel):
    """Schema para atualizar um artigo de usuario (todos campos opcionais)."""
    title: Optional[str] = Field(None, max_length=1000)
    linha_fina: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    preview: Optional[str] = Field(None, max_length=500)
    status: Optional[Literal['draft', 'published']] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    author_name: Optional[str] = Field(None, max_length=255)
    source_article_ids: Optional[List[str]] = None
    generation_config: Optional[dict] = None


class UserArticle(UserArticleBase):
    """Schema completo do artigo de usuario (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    status: Literal['draft', 'published'] = 'draft'
    source_article_ids: List[str] = Field(default_factory=list)
    generation_config: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

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

    @field_validator('source_article_ids', mode='before')
    @classmethod
    def parse_source_ids(cls, v):
        """Parse source_article_ids de JSON string para lista."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []

    @field_validator('generation_config', mode='before')
    @classmethod
    def parse_generation_config(cls, v):
        """Parse generation_config de JSON string para dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

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

        Formato esperado (baseado em mockData.js myArticles):
        {
            id: "uuid",
            title: "Titulo",
            preview: "Resumo...",
            status: "draft" | "published",
            category: "Esportes",
            author: { id: "...", name: "Autor", avatar: null },
            createdAt: "2025-01-18T10:00:00Z",
            updatedAt: "2025-01-18T12:00:00Z",
            publishedAt: null,
            views: 0,
            tags: ["tag1", "tag2"],
            linhaFina: "Subtitle",
            content: "Full article content..."
        }
        """
        return {
            "id": str(self.id),
            "title": self.title,
            "preview": self.generate_preview(),
            "status": self.status,
            "category": self.category,
            "author": {
                "id": "default",
                "name": self.author_name or "Autor",
                "avatar": None
            },
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "publishedAt": self.published_at.isoformat() if self.published_at else None,
            "views": 0,  # Placeholder - could be tracked separately
            "tags": self.tags,
            "linhaFina": self.linha_fina,
            "content": self.content,
            "sourceArticleIds": self.source_article_ids,
            "generationConfig": self.generation_config
        }


class UserArticleListResponse(BaseModel):
    """Schema para resposta paginada de artigos de usuario."""
    items: List[UserArticle]
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
