"""
Model EventSignature - Assinatura unica de um evento jornalistico especifico.

Usado para clustering por evento: identifica o MESMO acontecimento,
nao apenas conceitos semanticos similares.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID, uuid4
import json
import hashlib
import re
import unicodedata


def normalize_entity(text: str) -> str:
    """
    Normaliza uma entidade para comparacao.

    - Remove acentos
    - Lowercase
    - Remove espacos extras
    - Remove pontuacao
    """
    if not text:
        return ""

    # Remove acentos usando NFD normalization
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    # Lowercase
    text = text.lower()

    # Remove pontuacao exceto hifen
    text = re.sub(r'[^\w\s-]', '', text)

    # Remove espacos extras
    text = ' '.join(text.split())

    return text.strip()


# Sinonimos comuns para matching de entidades
ENTITY_SYNONYMS = {
    # Paises
    'eua': 'estados unidos',
    'usa': 'estados unidos',
    'america': 'estados unidos',
    'brasil': 'brasil',
    'br': 'brasil',
    # Organizacoes comuns
    'policia federal': 'pf',
    'policia rodoviaria federal': 'prf',
    'supremo tribunal federal': 'stf',
    'tribunal superior eleitoral': 'tse',
    # Cidades
    'sp': 'sao paulo',
    'rj': 'rio de janeiro',
    'bh': 'belo horizonte',
    'df': 'brasilia',
    'poa': 'porto alegre',
}

# Reverse mapping
_REVERSE_SYNONYMS = {v: k for k, v in ENTITY_SYNONYMS.items()}
_REVERSE_SYNONYMS.update({k: k for k in ENTITY_SYNONYMS.keys()})


def get_canonical_entity(entity: str) -> str:
    """
    Retorna a forma canonica de uma entidade (aplicando sinonimos).

    Args:
        entity: Entidade normalizada

    Returns:
        Forma canonica da entidade
    """
    normalized = normalize_entity(entity)
    return ENTITY_SYNONYMS.get(normalized, normalized)


def entities_match(entity1: str, entity2: str) -> bool:
    """
    Verifica se duas entidades sao equivalentes.

    Considera:
    - Match exato apos normalizacao
    - Sinonimos (EUA = Estados Unidos)
    - Match parcial (Trump in Donald Trump)

    Args:
        entity1: Primeira entidade
        entity2: Segunda entidade

    Returns:
        True se as entidades sao equivalentes
    """
    if not entity1 or not entity2:
        return False

    norm1 = normalize_entity(entity1)
    norm2 = normalize_entity(entity2)

    # Match exato
    if norm1 == norm2:
        return True

    # Match por sinonimos
    canon1 = get_canonical_entity(norm1)
    canon2 = get_canonical_entity(norm2)
    if canon1 == canon2:
        return True

    # Match parcial (um contem o outro)
    # Ex: "trump" in "donald trump" ou "ice" in "ice usa"
    if len(norm1) >= 3 and len(norm2) >= 3:
        # Verifica se um e substring do outro (com word boundaries)
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        # Se todas as palavras de um estao contidas no outro
        if words1 and words2:
            if words1.issubset(words2) or words2.issubset(words1):
                return True

    return False


def calculate_entity_similarity(entities1: set, entities2: set) -> float:
    """
    Calcula similaridade entre dois conjuntos de entidades.

    Usa matching inteligente que considera sinonimos e substrings.

    Args:
        entities1: Primeiro conjunto de entidades normalizadas
        entities2: Segundo conjunto de entidades normalizadas

    Returns:
        Score de similaridade entre 0 e 1
    """
    if not entities1 or not entities2:
        return 0.0

    # Conta quantas entidades de entities1 tem match em entities2
    matches1 = 0
    for e1 in entities1:
        for e2 in entities2:
            if entities_match(e1, e2):
                matches1 += 1
                break

    # Conta quantas entidades de entities2 tem match em entities1
    matches2 = 0
    for e2 in entities2:
        for e1 in entities1:
            if entities_match(e2, e1):
                matches2 += 1
                break

    # Calcula similaridade como media das coberturas
    coverage1 = matches1 / len(entities1) if entities1 else 0
    coverage2 = matches2 / len(entities2) if entities2 else 0

    # Usa formula similar a Dice coefficient
    similarity = (coverage1 + coverage2) / 2

    return similarity


class EventSignatureBase(BaseModel):
    """Campos base da assinatura de evento."""

    # Entidades nomeadas (QUEM)
    people: List[str] = Field(
        default_factory=list,
        description="Nomes proprios de pessoas envolvidas no evento"
    )
    organizations: List[str] = Field(
        default_factory=list,
        description="Organizacoes especificas (ICE, STF, Petrobras)"
    )

    # Localizacao (ONDE)
    locations: List[str] = Field(
        default_factory=list,
        description="Locais especificos do evento"
    )

    # Acao do evento (O QUE)
    event_action: str = Field(
        default="",
        description="Verbo principal: detido, morreu, anunciou, venceu"
    )

    # Detalhes unicos para identificacao
    unique_details: List[str] = Field(
        default_factory=list,
        description="Detalhes unicos: pai de trigemeos, empresario, etc"
    )

    # Chave canonica para matching rapido
    canonical_key: Optional[str] = Field(
        None,
        max_length=500,
        description="Chave normalizada para busca: pessoa|org|acao|local|periodo"
    )

    # Contexto temporal
    event_date: Optional[date] = Field(
        None,
        description="Data do evento se mencionada no artigo"
    )

    # Confianca da extracao
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confianca da extracao (0.0 a 1.0)"
    )


class EventSignatureCreate(EventSignatureBase):
    """Schema para criar uma nova assinatura de evento."""

    article_id: UUID = Field(..., description="ID do artigo fonte")
    theme_id: Optional[UUID] = Field(None, description="ID do tema associado")

    def generate_canonical_key(self, reference_date: Optional[date] = None) -> str:
        """
        Gera chave canonica para matching rapido.

        Formato: {pessoa_principal}|{org_principal}|{acao}|{local}|{mes-ano}

        Exemplos:
        - "empresario-brasileiro|ice|detido|eua|2026-02"
        - "flamengo|null|venceu|maracana|2026-02"
        - "lula|stf|absolvido|brasilia|2026-02"
        """
        # Pessoa principal (primeira da lista ou "null")
        person = normalize_entity(self.people[0]) if self.people else "null"
        person = person.replace(' ', '-')[:50]  # Limita tamanho

        # Organizacao principal
        org = normalize_entity(self.organizations[0]) if self.organizations else "null"
        org = org.replace(' ', '-')[:30]

        # Acao normalizada
        action = normalize_entity(self.event_action) if self.event_action else "null"
        action = action.replace(' ', '-')[:20]

        # Local principal
        location = normalize_entity(self.locations[0]) if self.locations else "null"
        location = location.replace(' ', '-')[:30]

        # Periodo (mes-ano)
        if self.event_date:
            period = self.event_date.strftime("%Y-%m")
        elif reference_date:
            period = reference_date.strftime("%Y-%m")
        else:
            period = datetime.utcnow().strftime("%Y-%m")

        return f"{person}|{org}|{action}|{location}|{period}"


class EventSignatureUpdate(BaseModel):
    """Schema para atualizar uma assinatura (todos campos opcionais)."""

    people: Optional[List[str]] = None
    organizations: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    event_action: Optional[str] = None
    unique_details: Optional[List[str]] = None
    canonical_key: Optional[str] = None
    event_date: Optional[date] = None
    confidence: Optional[float] = None
    theme_id: Optional[UUID] = None


class EventSignature(EventSignatureBase):
    """Schema completo da assinatura (retornado do banco)."""

    id: UUID = Field(default_factory=uuid4)
    article_id: UUID
    theme_id: Optional[UUID] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True
    }

    @field_validator('people', 'organizations', 'locations', 'unique_details', mode='before')
    @classmethod
    def parse_json_list(cls, v):
        """Parse JSON string para lista."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []

    def get_all_entities(self) -> List[str]:
        """Retorna todas as entidades normalizadas para comparacao."""
        entities = []
        entities.extend(self.people or [])
        entities.extend(self.organizations or [])
        entities.extend(self.locations or [])
        return [normalize_entity(e) for e in entities if e]

    def get_entity_set(self) -> set:
        """Retorna set de entidades normalizadas."""
        return set(self.get_all_entities())

    def calculate_entity_overlap(self, other: 'EventSignature') -> float:
        """
        Calcula overlap de entidades com outra assinatura.

        Usa matching inteligente que considera:
        - Sinonimos (EUA = Estados Unidos)
        - Match parcial (Trump = Donald Trump)

        Args:
            other: Outra assinatura para comparar

        Returns:
            Score de overlap entre 0 e 1
        """
        entities1 = self.get_entity_set()
        entities2 = other.get_entity_set()

        if not entities1 or not entities2:
            return 0.0

        # Usa a nova funcao de similaridade inteligente
        similarity = calculate_entity_similarity(entities1, entities2)

        # Bonus se acao e a mesma ou similar
        action1 = normalize_entity(self.event_action) if self.event_action else ""
        action2 = normalize_entity(other.event_action) if other.event_action else ""

        if action1 and action2:
            # Match exato de acao
            if action1 == action2:
                similarity = min(1.0, similarity + 0.15)
            # Match parcial de acao (detido/preso, morreu/morto, etc.)
            elif entities_match(action1, action2):
                similarity = min(1.0, similarity + 0.10)
            # Acoes similares semanticamente
            elif _actions_are_similar(action1, action2):
                similarity = min(1.0, similarity + 0.10)

        return similarity


# Grupos de acoes semanticamente similares
_SIMILAR_ACTIONS = [
    {'detido', 'preso', 'presa', 'detida', 'aprisionado', 'aprisionada'},
    {'morreu', 'morto', 'morta', 'faleceu', 'falecido', 'obito'},
    {'anunciou', 'anunciado', 'anuncia', 'declarou', 'declara'},
    {'venceu', 'ganhou', 'ganha', 'vence', 'conquistou'},
    {'perdeu', 'perde', 'derrotado', 'derrotada'},
    {'fechou', 'fecha', 'encerrou', 'encerra', 'encerrado'},
]


def _actions_are_similar(action1: str, action2: str) -> bool:
    """Verifica se duas acoes sao semanticamente similares."""
    for group in _SIMILAR_ACTIONS:
        if action1 in group and action2 in group:
            return True
    return False

    def to_api_response(self) -> dict:
        """Converte para formato de resposta da API."""
        return {
            "id": str(self.id),
            "articleId": str(self.article_id),
            "themeId": str(self.theme_id) if self.theme_id else None,
            "people": self.people,
            "organizations": self.organizations,
            "locations": self.locations,
            "eventAction": self.event_action,
            "uniqueDetails": self.unique_details,
            "canonicalKey": self.canonical_key,
            "eventDate": self.event_date.isoformat() if self.event_date else None,
            "confidence": self.confidence,
            "extractedAt": self.extracted_at.isoformat() if self.extracted_at else None
        }


class EventSignatureResponse(BaseModel):
    """Schema para resposta de uma assinatura."""

    id: UUID
    article_id: UUID
    theme_id: Optional[UUID]
    people: List[str]
    organizations: List[str]
    locations: List[str]
    event_action: str
    unique_details: List[str]
    canonical_key: Optional[str]
    event_date: Optional[date]
    confidence: float
    extracted_at: datetime

    model_config = {
        "from_attributes": True
    }
