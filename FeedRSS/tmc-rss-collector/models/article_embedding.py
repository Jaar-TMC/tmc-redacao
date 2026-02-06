"""
Model ArticleEmbedding - Representa o embedding vetorial de um artigo.
Usado para busca semantica e clustering de temas.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
import json


class ArticleEmbeddingBase(BaseModel):
    """Campos base para ArticleEmbedding."""
    article_id: UUID
    embedding: List[float] = Field(..., description="Embedding vector (1536 dimensions for OpenAI ada-002)")
    model: str = Field(default="text-embedding-ada-002", max_length=100)

    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimensions(cls, v):
        """Valida que o embedding tem 1536 dimensoes (OpenAI ada-002)."""
        if len(v) != 1536:
            raise ValueError(f'Embedding must have exactly 1536 dimensions, got {len(v)}')
        return v


class ArticleEmbeddingCreate(ArticleEmbeddingBase):
    """Schema para criar um novo embedding de artigo."""
    pass


class ArticleEmbeddingUpdate(BaseModel):
    """Schema para atualizar um embedding (regenerar)."""
    embedding: Optional[List[float]] = Field(None, description="New embedding vector")
    model: Optional[str] = Field(None, max_length=100)
    theme_id: Optional[UUID] = Field(None, description="Assigned theme ID")
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimensions(cls, v):
        """Valida que o embedding tem 1536 dimensoes."""
        if v is not None and len(v) != 1536:
            raise ValueError(f'Embedding must have exactly 1536 dimensions, got {len(v)}')
        return v


class ArticleEmbedding(ArticleEmbeddingBase):
    """Schema completo do embedding de artigo (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    theme_id: Optional[UUID] = Field(None, description="Assigned semantic theme ID")
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Similarity to theme centroid")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }

    @field_validator('embedding', mode='before')
    @classmethod
    def parse_embedding(cls, v):
        """Parse embedding de JSON string para lista."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []

    def to_api_response(self, include_embedding: bool = False) -> dict:
        """
        Converte para formato de resposta da API.

        Args:
            include_embedding: Se True, inclui o vetor embedding (pode ser grande).
                              Default False para economizar bandwidth.
        """
        response = {
            "id": str(self.id),
            "articleId": str(self.article_id),
            "model": self.model,
            "themeId": str(self.theme_id) if self.theme_id else None,
            "similarityScore": round(self.similarity_score, 4) if self.similarity_score else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }

        if include_embedding:
            response["embedding"] = self.embedding
            response["dimensions"] = len(self.embedding) if self.embedding else 0

        return response

    def cosine_similarity(self, other_embedding: List[float]) -> float:
        """
        Calcula a similaridade de cosseno entre este embedding e outro.

        Args:
            other_embedding: Vetor de embedding para comparar

        Returns:
            Similaridade de cosseno (0.0 a 1.0)
        """
        import math

        if not self.embedding or not other_embedding:
            return 0.0

        if len(self.embedding) != len(other_embedding):
            raise ValueError("Embeddings must have the same dimensions")

        dot_product = sum(a * b for a, b in zip(self.embedding, other_embedding))
        norm_a = math.sqrt(sum(a * a for a in self.embedding))
        norm_b = math.sqrt(sum(b * b for b in other_embedding))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


class ArticleEmbeddingResponse(BaseModel):
    """Schema para resposta de um unico embedding (sem o vetor)."""
    id: UUID
    article_id: UUID
    model: str
    theme_id: Optional[UUID]
    similarity_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class ArticleEmbeddingListResponse(BaseModel):
    """Schema para resposta paginada de embeddings."""
    items: List[ArticleEmbedding]
    total: int
    page: int
    pages: int

    def to_api_response(self, include_embeddings: bool = False) -> dict:
        """Converte lista para formato de resposta da API."""
        return {
            "items": [emb.to_api_response(include_embedding=include_embeddings) for emb in self.items],
            "total": self.total,
            "page": self.page,
            "pages": self.pages
        }


class BulkEmbeddingCreate(BaseModel):
    """Schema para criar embeddings em lote."""
    embeddings: List[ArticleEmbeddingCreate] = Field(..., min_length=1, max_length=100)


class SemanticSearchRequest(BaseModel):
    """Schema para requisicao de busca semantica."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    theme_id: Optional[UUID] = Field(None, description="Filter by theme")


class SemanticSearchResult(BaseModel):
    """Schema para resultado de busca semantica."""
    article_id: UUID
    similarity_score: float
    theme_id: Optional[UUID]

    model_config = {
        "from_attributes": True
    }


class SemanticSearchResponse(BaseModel):
    """Schema para resposta de busca semantica."""
    query: str
    results: List[SemanticSearchResult]
    total: int
    threshold: float
