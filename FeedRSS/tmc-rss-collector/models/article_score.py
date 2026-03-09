"""
Model ArticleScore - Representa a pontuacao de relevancia de um artigo.
Baseado nos 4 sinais: Inesperado, Impacto, Busca Agora, Conversa.
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID, uuid4


# Tipos para os sinais
SinalInesperado = Literal['yes', 'partial', 'no']
SinalImpacto = Literal['high', 'medium', 'low']
SinalBuscaAgora = Literal['yes', 'maybe', 'no']
SinalConversa = Literal['yes', 'maybe', 'no']
Classification = Literal['A', 'B', 'C']
ScoredBy = Literal['ai', 'manual']


class ArticleScoreBase(BaseModel):
    """Campos base para ArticleScore."""
    # Sinais qualitativos
    sinal_inesperado: SinalInesperado = Field(..., description="Fato inesperado? (yes/partial/no)")
    sinal_impacto: SinalImpacto = Field(..., description="Impacto na vida do leitor (high/medium/low)")
    sinal_busca_agora: SinalBuscaAgora = Field(..., description="Leitor vai buscar agora? (yes/maybe/no)")
    sinal_conversa: SinalConversa = Field(..., description="Leitor vai comentar? (yes/maybe/no)")

    # Scores numericos (max varies per signal, total 0-100)
    score_inesperado: int = Field(..., ge=0, le=25, description="Pontuacao Inesperado (0-25)")
    score_impacto: int = Field(..., ge=0, le=30, description="Pontuacao Impacto (0-30)")
    score_busca_agora: int = Field(..., ge=0, le=25, description="Pontuacao Busca Agora (0-25)")
    score_conversa: int = Field(..., ge=0, le=20, description="Pontuacao Conversa (0-20)")


class ArticleScoreCreate(ArticleScoreBase):
    """Schema para criar um novo score de artigo."""
    article_id: UUID
    scored_by: ScoredBy = 'ai'

    @model_validator(mode='after')
    def calculate_total_and_classification(self):
        """Calcula total_score e classification automaticamente."""
        # Estes serao calculados no model completo
        return self


class ArticleScoreUpdate(BaseModel):
    """Schema para atualizar um score (todos campos opcionais)."""
    sinal_inesperado: Optional[SinalInesperado] = None
    sinal_impacto: Optional[SinalImpacto] = None
    sinal_busca_agora: Optional[SinalBuscaAgora] = None
    sinal_conversa: Optional[SinalConversa] = None
    score_inesperado: Optional[int] = Field(None, ge=0, le=25)
    score_impacto: Optional[int] = Field(None, ge=0, le=30)
    score_busca_agora: Optional[int] = Field(None, ge=0, le=25)
    score_conversa: Optional[int] = Field(None, ge=0, le=20)
    scored_by: Optional[ScoredBy] = None


class ArticleScore(ArticleScoreBase):
    """Schema completo do score de artigo (retornado do banco)."""
    id: UUID = Field(default_factory=uuid4)
    article_id: UUID
    total_score: int = Field(default=0, ge=0, le=100, description="Soma dos 4 scores (0-100)")
    classification: Classification = Field(default='C', description="Classificacao A/B/C baseada no total")
    scored_by: ScoredBy = 'ai'
    reasoning: Optional[str] = Field(default=None, description="Justificativa da classificacao (gerada pela IA)")
    scored_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }

    @model_validator(mode='after')
    def calculate_derived_fields(self):
        """Calcula total_score e classification baseado nos scores individuais."""
        # Calcular total
        self.total_score = (
            self.score_inesperado +
            self.score_impacto +
            self.score_busca_agora +
            self.score_conversa
        )

        # Calcular classificacao
        # A: 75-100, B: 35-74, C: 0-34
        if self.total_score >= 75:
            self.classification = 'A'
        elif self.total_score >= 35:  # Threshold B: 35-74 (unificado com scoring_service.py)
            self.classification = 'B'
        else:
            self.classification = 'C'

        return self

    def to_api_response(self) -> dict:
        """Converte para formato de resposta da API."""
        return {
            "id": str(self.id),
            "articleId": str(self.article_id),
            "sinais": {
                "inesperado": self.sinal_inesperado,
                "impacto": self.sinal_impacto,
                "buscaAgora": self.sinal_busca_agora,
                "conversa": self.sinal_conversa
            },
            "scores": {
                "inesperado": self.score_inesperado,
                "impacto": self.score_impacto,
                "buscaAgora": self.score_busca_agora,
                "conversa": self.score_conversa,
                "total": self.total_score
            },
            "classification": self.classification,
            "reasoning": self.reasoning,
            "scoredBy": self.scored_by,
            "scoredAt": self.scored_at.isoformat() if self.scored_at else None
        }

    @classmethod
    def from_ai_response(cls, article_id: UUID, ai_response: dict) -> 'ArticleScore':
        """
        Cria um ArticleScore a partir da resposta da IA.

        Esperado formato da IA:
        {
            "sinal_inesperado": "yes",
            "sinal_impacto": "high",
            "sinal_busca_agora": "yes",
            "sinal_conversa": "yes",
            "score_inesperado": 25,
            "score_impacto": 20,
            "score_busca_agora": 25,
            "score_conversa": 15
        }
        """
        return cls(
            article_id=article_id,
            sinal_inesperado=ai_response.get('sinal_inesperado', 'no'),
            sinal_impacto=ai_response.get('sinal_impacto', 'low'),
            sinal_busca_agora=ai_response.get('sinal_busca_agora', 'no'),
            sinal_conversa=ai_response.get('sinal_conversa', 'no'),
            score_inesperado=ai_response.get('score_inesperado', 0),
            score_impacto=ai_response.get('score_impacto', 0),
            score_busca_agora=ai_response.get('score_busca_agora', 0),
            score_conversa=ai_response.get('score_conversa', 0),
            scored_by='ai'
        )


class ArticleScoreResponse(BaseModel):
    """Schema para resposta de um unico score."""
    id: UUID
    article_id: UUID
    sinal_inesperado: str
    sinal_impacto: str
    sinal_busca_agora: str
    sinal_conversa: str
    score_inesperado: int
    score_impacto: int
    score_busca_agora: int
    score_conversa: int
    total_score: int
    classification: str
    scored_by: str
    scored_at: datetime

    model_config = {
        "from_attributes": True
    }


class ArticleScoreListResponse(BaseModel):
    """Schema para resposta paginada de scores."""
    items: List[ArticleScore]
    total: int
    page: int
    pages: int

    def to_api_response(self) -> dict:
        """Converte lista para formato de resposta da API."""
        return {
            "items": [score.to_api_response() for score in self.items],
            "total": self.total,
            "page": self.page,
            "pages": self.pages
        }
