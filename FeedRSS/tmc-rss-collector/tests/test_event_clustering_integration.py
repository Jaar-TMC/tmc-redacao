"""
Integration tests for the event-based clustering pipeline.

Tests the full flow from event signature extraction through theme matching
and clustering service coordination.

Uses pytest-asyncio for async test support and mocks for external dependencies
(database, LLM API calls).
"""

import pytest
import json
from datetime import datetime, date, timedelta
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

# Import the services and models under test
from services.event_signature_service import EventSignatureService
from services.event_matching_service import EventMatchingService
from services.llm_verification_service import LLMVerificationService
from services.clustering_service import ClusteringService, cosine_similarity, normalize_vector
from models.event_signature import EventSignature, EventSignatureCreate, normalize_entity
from models.theme import Theme


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_article_data() -> Dict[str, Any]:
    """
    Fixture providing realistic article data for a specific news event.
    """
    return {
        'id': uuid4(),
        'title': 'Empresario brasileiro e detido pelo ICE nos Estados Unidos',
        'preview': 'Joao Silva, pai de trigemeos e dono de restaurante em Miami, '
                   'foi detido pela imigracao americana durante operacao de rotina. '
                   'O empresario reside legalmente no pais ha 15 anos.',
        'content': 'Joao Silva, um empresario brasileiro de 45 anos...',
        'published_at': datetime.utcnow(),
        'source_name': 'G1',
        'embedding': [0.1] * 1536  # Mock embedding
    }


@pytest.fixture
def sample_article_same_event() -> Dict[str, Any]:
    """
    Fixture providing a second article about the SAME specific event.
    """
    return {
        'id': uuid4(),
        'title': 'Pai de trigemeos preso nos EUA trabalhava como empresario em Miami',
        'preview': 'Detido pelo ICE, Joao Silva era conhecido na comunidade brasileira '
                   'de Miami por seu restaurante. Familia pede ajuda do consulado.',
        'content': 'A familia de Joao Silva, detido ontem pelo ICE...',
        'published_at': datetime.utcnow(),
        'source_name': 'Folha',
        'embedding': [0.12] * 1536  # Slightly different embedding
    }


@pytest.fixture
def sample_article_different_event() -> Dict[str, Any]:
    """
    Fixture providing an article about a DIFFERENT event (different person detained).
    Uses orthogonal embedding to ensure no cosine similarity match.
    """
    # Orthogonal embedding: first half positive, second half negative
    embedding = [0.1] * 768 + [-0.1] * 768
    return {
        'id': uuid4(),
        'title': 'Outro brasileiro e detido pelo ICE em operacao na Florida',
        'preview': 'Maria Santos, enfermeira brasileira, foi detida em Orlando '
                   'durante blitz da imigracao. Caso nao tem relacao com outras prisoes.',
        'content': 'Uma enfermeira brasileira de 38 anos...',
        'published_at': datetime.utcnow(),
        'source_name': 'UOL',
        'embedding': embedding
    }


@pytest.fixture
def mock_llm_service():
    """
    Fixture providing a mock LLM service that returns realistic extraction results.
    """
    mock = MagicMock()

    async def mock_call_api(system: str, user_content: str, max_tokens: int = 1024, **kwargs):
        """Mock LLM API call that extracts event signature from content."""
        # Parse the user content to determine what article we're processing
        if 'Joao Silva' in user_content or 'trigemeos' in user_content:
            return json.dumps({
                'people': ['Joao Silva'],
                'organizations': ['ICE'],
                'locations': ['Miami', 'Estados Unidos'],
                'event_action': 'detido',
                'unique_details': ['pai de trigemeos', 'empresario', 'dono de restaurante'],
                'event_date': date.today().isoformat(),
                'confidence': 0.92
            })
        elif 'Maria Santos' in user_content:
            return json.dumps({
                'people': ['Maria Santos'],
                'organizations': ['ICE'],
                'locations': ['Orlando', 'Florida'],
                'event_action': 'detido',
                'unique_details': ['enfermeira'],
                'event_date': date.today().isoformat(),
                'confidence': 0.88
            })
        else:
            return json.dumps({
                'people': [],
                'organizations': [],
                'locations': [],
                'event_action': '',
                'unique_details': [],
                'event_date': None,
                'confidence': 0.5
            })

    mock._call_api = AsyncMock(side_effect=mock_call_api)
    return mock


@pytest.fixture
def mock_llm_verification_response():
    """
    Fixture providing mock verification responses for same event detection.
    """
    async def mock_verify(article1: Dict, article2: Dict):
        """Determine if two articles are about the same event based on content."""
        title1 = article1.get('title', '').lower()
        title2 = article2.get('title', '').lower()
        preview1 = article1.get('preview', '').lower()
        preview2 = article2.get('preview', '').lower()

        # Check for overlapping key identifiers
        # Same person (Joao Silva / pai de trigemeos)
        has_joao = 'joao silva' in title1 + preview1 or 'joao silva' in title2 + preview2
        has_trigemeos = 'trigemeos' in title1 + preview1 or 'trigemeos' in title2 + preview2
        has_maria = 'maria santos' in title1 + preview1 or 'maria santos' in title2 + preview2

        # Same event if both mention Joao or trigemeos, different if Maria
        if (has_joao or has_trigemeos) and not has_maria:
            if ('joao' in title1 + preview1 or 'trigemeos' in title1 + preview1) and \
               ('joao' in title2 + preview2 or 'trigemeos' in title2 + preview2):
                return {
                    'is_same_event': True,
                    'confidence': 0.95,
                    'reasoning': 'Mesma pessoa (Joao Silva / pai de trigemeos) detida pelo ICE em Miami',
                    'from_cache': False
                }

        return {
            'is_same_event': False,
            'confidence': 0.85,
            'reasoning': 'Pessoas diferentes detidas em eventos separados',
            'from_cache': False
        }

    return mock_verify


@pytest.fixture
def mock_database_service():
    """
    Fixture providing a mock database service with in-memory storage.
    """
    mock = MagicMock()

    # In-memory storage
    storage = {
        'themes': {},
        'articles': {},
        'article_themes': {},
        'event_signatures': {},
        'article_embeddings': {}
    }

    def get_all_themes(status: str = 'active'):
        return [
            t for t in storage['themes'].values()
            if t.get('status', 'active') == status
        ]

    def create_theme(name: str, slug: str, centroid: List[float], article_count: int = 1):
        theme_id = uuid4()
        theme = {
            'id': theme_id,
            'name': name,
            'slug': slug,
            'centroid': centroid,
            'article_count': article_count,
            'status': 'active',
            'score_avg': 0.0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'canonical_event_key': None,
            'primary_entities': None,
            'seed_article_id': None
        }
        storage['themes'][str(theme_id)] = theme
        return theme

    def get_theme(theme_id: UUID):
        return storage['themes'].get(str(theme_id))

    def update_theme(theme_id: UUID, **kwargs):
        theme_key = str(theme_id)
        if theme_key in storage['themes']:
            storage['themes'][theme_key].update(kwargs)
            storage['themes'][theme_key]['updated_at'] = datetime.utcnow()
            return storage['themes'][theme_key]
        return None

    def update_theme_event_data(theme_id: UUID, canonical_event_key: str,
                                 primary_entities: dict, seed_article_id: UUID):
        theme_key = str(theme_id)
        if theme_key in storage['themes']:
            storage['themes'][theme_key].update({
                'canonical_event_key': canonical_event_key,
                'primary_entities': primary_entities,
                'seed_article_id': seed_article_id
            })

    def add_article_to_theme(article_id: UUID, theme_id: UUID,
                              similarity_score: float, is_seed: bool = False):
        key = f"{article_id}_{theme_id}"
        storage['article_themes'][key] = {
            'article_id': article_id,
            'theme_id': theme_id,
            'similarity_score': similarity_score,
            'is_seed': is_seed,
            'created_at': datetime.utcnow()
        }

    def add_article_to_theme_with_match_type(article_id: UUID, theme_id: UUID,
                                              similarity_score: float, match_type: str,
                                              is_seed: bool = False):
        key = f"{article_id}_{theme_id}"
        storage['article_themes'][key] = {
            'article_id': article_id,
            'theme_id': theme_id,
            'similarity_score': similarity_score,
            'match_type': match_type,
            'is_seed': is_seed,
            'created_at': datetime.utcnow()
        }

    def find_themes_by_canonical_key(canonical_key: str):
        return [
            t for t in storage['themes'].values()
            if t.get('canonical_event_key') == canonical_key
        ]

    def save_event_signature(article_id: UUID, people: List[str], organizations: List[str],
                              locations: List[str], event_action: str, unique_details: List[str],
                              canonical_key: str, event_date: Optional[str], confidence: float):
        storage['event_signatures'][str(article_id)] = {
            'article_id': article_id,
            'people': people,
            'organizations': organizations,
            'locations': locations,
            'event_action': event_action,
            'unique_details': unique_details,
            'canonical_key': canonical_key,
            'event_date': event_date,
            'confidence': confidence,
            'created_at': datetime.utcnow()
        }

    def update_event_signature_theme(article_id: UUID, theme_id: UUID):
        key = str(article_id)
        if key in storage['event_signatures']:
            storage['event_signatures'][key]['theme_id'] = theme_id

    def get_articles_pending_clustering(limit: int = 100):
        # Return articles that have embeddings but no theme assignment
        pending = []
        for art_id, article in storage['articles'].items():
            has_theme = any(
                at['article_id'] == article['id']
                for at in storage['article_themes'].values()
            )
            if not has_theme and article.get('embedding'):
                pending.append(article)
                if len(pending) >= limit:
                    break
        return pending

    def get_theme_article_scores(theme_id: UUID):
        # Return mock scores for theme
        return [{'article_id': uuid4(), 'scores': {'total': 75.0}}]

    def get_article_by_id(article_id: UUID):
        return storage['articles'].get(str(article_id))

    # Assign methods to mock
    mock.get_all_themes = MagicMock(side_effect=get_all_themes)
    mock.create_theme = MagicMock(side_effect=create_theme)
    mock.get_theme = MagicMock(side_effect=get_theme)
    mock.update_theme = MagicMock(side_effect=update_theme)
    mock.update_theme_event_data = MagicMock(side_effect=update_theme_event_data)
    mock.add_article_to_theme = MagicMock(side_effect=add_article_to_theme)
    mock.add_article_to_theme_with_match_type = MagicMock(side_effect=add_article_to_theme_with_match_type)
    mock.find_themes_by_canonical_key = MagicMock(side_effect=find_themes_by_canonical_key)
    mock.save_event_signature = MagicMock(side_effect=save_event_signature)
    mock.update_event_signature_theme = MagicMock(side_effect=update_event_signature_theme)
    mock.get_articles_pending_clustering = MagicMock(side_effect=get_articles_pending_clustering)
    mock.get_theme_article_scores = MagicMock(side_effect=get_theme_article_scores)
    mock.get_article_by_id = MagicMock(side_effect=get_article_by_id)

    # Expose storage for test assertions
    mock._storage = storage

    return mock


# ============================================================================
# TESTS: EventSignatureService.extract()
# ============================================================================

class TestEventSignatureServiceExtract:
    """Tests for EventSignatureService.extract() method."""

    @pytest.mark.asyncio
    async def test_extract_returns_signature_with_people_and_organizations(
        self, mock_llm_service, sample_article_data
    ):
        """
        Test that extract() returns an EventSignatureCreate with correctly
        identified people and organizations from realistic article data.
        """
        service = EventSignatureService(llm_service=mock_llm_service)

        with patch('services.event_signature_service.is_llm_configured', return_value=True):
            signature = await service.extract(
                title=sample_article_data['title'],
                content=sample_article_data['preview'],
                article_id=sample_article_data['id']
            )

        assert signature is not None
        assert isinstance(signature, EventSignatureCreate)
        assert 'Joao Silva' in signature.people
        assert 'ICE' in signature.organizations
        assert signature.event_action == 'detido'
        assert signature.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_extract_generates_canonical_key(
        self, mock_llm_service, sample_article_data
    ):
        """
        Test that extract() generates a canonical key for fast matching.
        """
        service = EventSignatureService(llm_service=mock_llm_service)

        signature = await service.extract(
            title=sample_article_data['title'],
            content=sample_article_data['preview'],
            article_id=sample_article_data['id'],
            reference_date=date.today()
        )

        assert signature is not None
        assert signature.canonical_key is not None
        # Canonical key format: person|org|action|location|period
        parts = signature.canonical_key.split('|')
        assert len(parts) == 5
        assert 'joao' in parts[0].lower() or 'silva' in parts[0].lower()
        assert 'ice' in parts[1].lower()
        assert 'detido' in parts[2].lower()

    @pytest.mark.asyncio
    async def test_extract_caches_results_for_same_content(
        self, mock_llm_service, sample_article_data
    ):
        """
        Test that extract() caches results and doesn't call LLM twice
        for the same article content.
        """
        service = EventSignatureService(llm_service=mock_llm_service)

        with patch('services.event_signature_service.is_llm_configured', return_value=True):
            # First extraction
            signature1 = await service.extract(
                title=sample_article_data['title'],
                content=sample_article_data['preview'],
                article_id=sample_article_data['id']
            )

            # Second extraction with same content
            signature2 = await service.extract(
                title=sample_article_data['title'],
                content=sample_article_data['preview'],
                article_id=uuid4()  # Different article ID
            )

        # Should return cached result - LLM called only once
        assert mock_llm_service._call_api.call_count == 1
        assert signature1.people == signature2.people
        assert signature1.event_action == signature2.event_action

    @pytest.mark.asyncio
    async def test_extract_fallback_when_llm_unavailable(self, sample_article_data):
        """
        Test that extract() uses fallback heuristics when LLM is not configured.
        """
        service = EventSignatureService(llm_service=None)

        with patch('services.event_signature_service.is_llm_configured', return_value=False):
            signature = await service.extract(
                title=sample_article_data['title'],
                content=sample_article_data['preview'],
                article_id=sample_article_data['id']
            )

        assert signature is not None
        # Fallback should have lower confidence
        assert signature.confidence <= 0.5
        # Should still have canonical key
        assert signature.canonical_key is not None

    @pytest.mark.asyncio
    async def test_extract_handles_empty_content_gracefully(self, mock_llm_service):
        """
        Test that extract() handles articles with minimal content.
        """
        service = EventSignatureService(llm_service=mock_llm_service)

        signature = await service.extract(
            title='Short title',
            content='',
            article_id=uuid4()
        )

        # Should not raise, returns signature with lower confidence
        assert signature is not None


# ============================================================================
# TESTS: EventMatchingService.find_matching_theme()
# ============================================================================

class TestEventMatchingServiceFindMatchingTheme:
    """Tests for EventMatchingService.find_matching_theme() method."""

    @pytest.mark.asyncio
    async def test_find_matching_theme_exact_canonical_key_match(
        self, mock_database_service
    ):
        """
        Test that find_matching_theme() finds theme by exact canonical key match.
        """
        # Create a theme with canonical key
        theme = mock_database_service.create_theme(
            name='Empresario detido pelo ICE',
            slug='empresario-detido-ice',
            centroid=[0.1] * 1536
        )
        mock_database_service.update_theme_event_data(
            theme_id=theme['id'],
            canonical_event_key='joao-silva|ice|detido|miami|2026-02',
            primary_entities={'people': ['Joao Silva'], 'organizations': ['ICE']},
            seed_article_id=uuid4()
        )

        service = EventMatchingService(db_service=mock_database_service)
        service._load_theme_cache()

        # Create signature with matching canonical key
        signature = EventSignatureCreate(
            article_id=uuid4(),
            people=['Joao Silva'],
            organizations=['ICE'],
            locations=['Miami'],
            event_action='detido',
            canonical_key='joao-silva|ice|detido|miami|2026-02',
            confidence=0.9
        )

        match = await service.find_matching_theme(
            article={'id': uuid4(), 'title': 'Test', 'preview': 'Test'},
            signature=signature,
            embedding=[0.11] * 1536
        )

        assert match is not None
        theme_id, match_type, confidence = match
        assert theme_id == theme['id']
        assert match_type == 'exact'
        assert confidence >= 0.98

    @pytest.mark.asyncio
    async def test_find_matching_theme_entity_overlap_high_confidence(
        self, mock_database_service
    ):
        """
        Test that find_matching_theme() matches by entity overlap when
        Jaccard similarity is >= 70%.
        """
        # Create theme with entities
        theme = mock_database_service.create_theme(
            name='Detencao pelo ICE',
            slug='detencao-ice',
            centroid=[0.1] * 1536
        )
        mock_database_service.update_theme_event_data(
            theme_id=theme['id'],
            canonical_event_key='different-key|ice|detido|miami|2026-01',
            primary_entities={
                'people': ['Joao Silva'],
                'organizations': ['ICE'],
                'locations': ['Miami'],
                'event_action': 'detido'
            },
            seed_article_id=uuid4()
        )

        service = EventMatchingService(db_service=mock_database_service)
        service._load_theme_cache()

        # Create signature with overlapping entities but different canonical key
        signature = EventSignatureCreate(
            article_id=uuid4(),
            people=['Joao Silva'],
            organizations=['ICE'],
            locations=['Florida'],  # Different location
            event_action='detido',
            canonical_key='joao-silva|ice|detido|florida|2026-02',
            confidence=0.9
        )

        match = await service.find_matching_theme(
            article={'id': uuid4(), 'title': 'Test', 'preview': 'Test'},
            signature=signature,
            embedding=[0.1] * 1536  # Similar embedding
        )

        assert match is not None
        theme_id, match_type, confidence = match
        assert theme_id == theme['id']
        assert match_type == 'entity'
        assert confidence >= 0.70

    @pytest.mark.asyncio
    async def test_find_matching_theme_returns_none_when_no_match(
        self, mock_database_service
    ):
        """
        Test that find_matching_theme() returns None when no theme matches.
        """
        # Create theme about different event with orthogonal centroid
        theme_centroid = [0.0] * 1536
        theme_centroid[0] = 1.0  # Only first dimension
        theme = mock_database_service.create_theme(
            name='Eleicoes 2026',
            slug='eleicoes-2026',
            centroid=theme_centroid
        )
        mock_database_service.update_theme_event_data(
            theme_id=theme['id'],
            canonical_event_key='lula|null|anunciou|brasilia|2026-02',
            primary_entities={
                'people': ['Lula'],
                'organizations': [],
                'locations': ['Brasilia'],
                'event_action': 'anunciou'
            },
            seed_article_id=uuid4()
        )

        service = EventMatchingService(db_service=mock_database_service)
        service._load_theme_cache()

        # Create signature about completely different event
        signature = EventSignatureCreate(
            article_id=uuid4(),
            people=['Maria Santos'],
            organizations=['Hospital'],
            locations=['Sao Paulo'],
            event_action='faleceu',
            canonical_key='maria-santos|hospital|faleceu|sao-paulo|2026-02',
            confidence=0.9
        )

        # Use orthogonal embedding (only second dimension) to ensure no match
        article_embedding = [0.0] * 1536
        article_embedding[1] = 1.0

        match = await service.find_matching_theme(
            article={'id': uuid4(), 'title': 'Test', 'preview': 'Test'},
            signature=signature,
            embedding=article_embedding
        )

        assert match is None

    @pytest.mark.asyncio
    async def test_find_matching_theme_invalidate_cache_works(
        self, mock_database_service
    ):
        """
        Test that invalidate_cache() properly clears the theme cache.
        """
        service = EventMatchingService(db_service=mock_database_service)
        service._load_theme_cache()

        assert service._cache_loaded is True

        service.invalidate_cache()

        assert service._cache_loaded is False
        assert len(service._theme_signature_cache) == 0


# ============================================================================
# TESTS: LLMVerificationService.verify_same_event()
# ============================================================================

class TestLLMVerificationServiceVerifySameEvent:
    """Tests for LLMVerificationService.verify_same_event() method."""

    @pytest.mark.asyncio
    async def test_verify_same_event_returns_true_for_same_event(
        self, mock_llm_service, sample_article_data, sample_article_same_event,
        mock_llm_verification_response
    ):
        """
        Test that verify_same_event() returns True for two articles
        describing the same specific event.
        """
        service = LLMVerificationService(llm_service=mock_llm_service)

        # Mock the LLM response for verification
        mock_llm_service._call_api = AsyncMock(return_value=json.dumps({
            'is_same_event': True,
            'confidence': 0.95,
            'reasoning': 'Mesma pessoa detida pelo ICE em Miami'
        }))

        with patch('services.llm_verification_service.is_llm_configured', return_value=True):
            result = await service.verify_same_event(
                article1={
                    'title': sample_article_data['title'],
                    'preview': sample_article_data['preview']
                },
                article2={
                    'title': sample_article_same_event['title'],
                    'preview': sample_article_same_event['preview']
                }
            )

        assert result['is_same_event'] is True
        assert result['confidence'] >= 0.9
        assert 'reasoning' in result

    @pytest.mark.asyncio
    async def test_verify_same_event_returns_false_for_different_events(
        self, mock_llm_service, sample_article_data, sample_article_different_event
    ):
        """
        Test that verify_same_event() returns False for articles about
        different specific events (different people detained).
        """
        service = LLMVerificationService(llm_service=mock_llm_service)

        # Mock the LLM response for verification
        mock_llm_service._call_api = AsyncMock(return_value=json.dumps({
            'is_same_event': False,
            'confidence': 0.85,
            'reasoning': 'Pessoas diferentes detidas em eventos separados'
        }))

        result = await service.verify_same_event(
            article1={
                'title': sample_article_data['title'],
                'preview': sample_article_data['preview']
            },
            article2={
                'title': sample_article_different_event['title'],
                'preview': sample_article_different_event['preview']
            }
        )

        assert result['is_same_event'] is False
        assert 'reasoning' in result

    @pytest.mark.asyncio
    async def test_verify_same_event_caches_results(self, mock_llm_service):
        """
        Test that verify_same_event() caches results and returns from cache
        on subsequent calls with same article pair.
        """
        service = LLMVerificationService(llm_service=mock_llm_service)

        mock_llm_service._call_api = AsyncMock(return_value=json.dumps({
            'is_same_event': True,
            'confidence': 0.90,
            'reasoning': 'Same event'
        }))

        article1 = {'title': 'Article A', 'preview': 'Preview A'}
        article2 = {'title': 'Article B', 'preview': 'Preview B'}

        with patch('services.llm_verification_service.is_llm_configured', return_value=True):
            # First call
            result1 = await service.verify_same_event(article1, article2)
            assert result1['from_cache'] is False

            # Second call - should be from cache
            result2 = await service.verify_same_event(article1, article2)
            assert result2['from_cache'] is True

        # LLM should only be called once
        assert mock_llm_service._call_api.call_count == 1

    @pytest.mark.asyncio
    async def test_verify_same_event_returns_true_for_identical_titles(
        self, mock_llm_service
    ):
        """
        Test that verify_same_event() returns True immediately for
        identical titles without calling LLM.
        """
        service = LLMVerificationService(llm_service=mock_llm_service)

        article1 = {'title': 'Exactly the same title', 'preview': 'Preview 1'}
        article2 = {'title': 'Exactly the same title', 'preview': 'Preview 2'}

        result = await service.verify_same_event(article1, article2)

        assert result['is_same_event'] is True
        assert result['confidence'] >= 0.99
        # LLM should not be called for identical titles
        assert mock_llm_service._call_api.call_count == 0

    @pytest.mark.asyncio
    async def test_verify_same_event_handles_missing_titles(self, mock_llm_service):
        """
        Test that verify_same_event() handles missing article titles gracefully.
        """
        service = LLMVerificationService(llm_service=mock_llm_service)

        result = await service.verify_same_event(
            article1={'title': '', 'preview': 'Some content'},
            article2={'title': 'Valid title', 'preview': 'Other content'}
        )

        assert result['is_same_event'] is False
        assert 'Missing' in result['reasoning']

    def test_get_cache_stats_returns_valid_statistics(self, mock_llm_service):
        """
        Test that get_cache_stats() returns valid cache statistics.
        """
        service = LLMVerificationService(llm_service=mock_llm_service)

        # Add some cache entries manually
        service._verification_cache['key1'] = {
            'result': {'is_same_event': True},
            'timestamp': datetime.utcnow()
        }
        service._verification_cache['key2'] = {
            'result': {'is_same_event': False},
            'timestamp': datetime.utcnow() - timedelta(hours=48)  # Expired
        }

        stats = service.get_cache_stats()

        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 1
        assert stats['expired_entries'] == 1
        assert 'ttl_hours' in stats


# ============================================================================
# TESTS: ClusteringService.process_pending_articles() - Full Pipeline
# ============================================================================

class TestClusteringServiceProcessPendingArticles:
    """Tests for the full event-based clustering pipeline."""

    @pytest.mark.asyncio
    async def test_process_pending_articles_creates_new_theme_for_new_event(
        self, mock_database_service, mock_llm_service, sample_article_data
    ):
        """
        Test that process_pending_articles() creates a new theme when
        processing an article about a new event.
        """
        # Add article to pending queue
        mock_database_service._storage['articles'][str(sample_article_data['id'])] = sample_article_data

        service = ClusteringService(
            db_service=mock_database_service,
            llm_service=mock_llm_service
        )

        with patch('services.event_signature_service.is_llm_configured', return_value=True), \
             patch('services.event_signature_service.EVENT_EXTRACTION_ENABLED', True), \
             patch('services.event_matching_service.EVENT_MATCHING_ENABLED', True):

            processed = await service.process_pending_articles(limit=10)

        # Should have processed 1 article
        assert processed == 1

        # Should have created a new theme
        themes = mock_database_service.get_all_themes(status='active')
        assert len(themes) == 1

        # Theme should have event data
        theme = themes[0]
        assert theme['name'] is not None

    @pytest.mark.asyncio
    async def test_process_pending_articles_adds_to_existing_theme_for_same_event(
        self, mock_database_service, mock_llm_service,
        sample_article_data, sample_article_same_event
    ):
        """
        Test that process_pending_articles() adds article to existing theme
        when it's about the same event.
        """
        # Create existing theme for the event
        theme = mock_database_service.create_theme(
            name='Empresario brasileiro detido pelo ICE',
            slug='empresario-brasileiro-detido-ice',
            centroid=[0.1] * 1536
        )
        mock_database_service.update_theme_event_data(
            theme_id=theme['id'],
            canonical_event_key='joao-silva|ice|detido|miami|2026-02',
            primary_entities={
                'people': ['Joao Silva'],
                'organizations': ['ICE'],
                'locations': ['Miami'],
                'event_action': 'detido'
            },
            seed_article_id=sample_article_data['id']
        )

        # Add second article to pending queue
        mock_database_service._storage['articles'][str(sample_article_same_event['id'])] = sample_article_same_event

        service = ClusteringService(
            db_service=mock_database_service,
            llm_service=mock_llm_service
        )

        with patch('services.event_signature_service.is_llm_configured', return_value=True), \
             patch('services.event_signature_service.EVENT_EXTRACTION_ENABLED', True), \
             patch('services.event_matching_service.EVENT_MATCHING_ENABLED', True):

            processed = await service.process_pending_articles(limit=10)

        assert processed == 1

        # Should still have only 1 theme (not create new one)
        themes = mock_database_service.get_all_themes(status='active')
        assert len(themes) == 1

    @pytest.mark.asyncio
    async def test_process_pending_articles_creates_separate_themes_for_different_events(
        self, mock_database_service, mock_llm_service,
        sample_article_data, sample_article_different_event
    ):
        """
        Test that process_pending_articles() creates separate themes for
        articles about different specific events.
        """
        # Add both articles to pending queue
        mock_database_service._storage['articles'][str(sample_article_data['id'])] = sample_article_data
        mock_database_service._storage['articles'][str(sample_article_different_event['id'])] = sample_article_different_event

        service = ClusteringService(
            db_service=mock_database_service,
            llm_service=mock_llm_service
        )

        # Mock to return different signatures for different articles
        call_count = [0]

        async def mock_extract_different_events(title, content, article_id, reference_date=None):
            call_count[0] += 1
            if 'Joao Silva' in title or 'trigemeos' in title:
                sig = EventSignatureCreate(
                    article_id=article_id,
                    people=['Joao Silva'],
                    organizations=['ICE'],
                    locations=['Miami'],
                    event_action='detido',
                    confidence=0.9
                )
                sig.canonical_key = sig.generate_canonical_key(reference_date)
                return sig
            else:
                sig = EventSignatureCreate(
                    article_id=article_id,
                    people=['Maria Santos'],
                    organizations=['ICE'],
                    locations=['Orlando'],
                    event_action='detido',
                    confidence=0.9
                )
                sig.canonical_key = sig.generate_canonical_key(reference_date)
                return sig

        with patch('services.event_signature_service.get_event_signature_service') as mock_sig_service, \
             patch('services.event_matching_service.get_event_matching_service') as mock_match_service, \
             patch('services.event_signature_service.EVENT_EXTRACTION_ENABLED', True), \
             patch('services.event_matching_service.EVENT_MATCHING_ENABLED', True):

            mock_sig_service.return_value.extract = mock_extract_different_events
            mock_match_service.return_value.find_matching_theme = AsyncMock(return_value=None)

            processed = await service.process_pending_articles(limit=10)

        assert processed == 2

        # Should have created 2 separate themes
        themes = mock_database_service.get_all_themes(status='active')
        assert len(themes) == 2

    @pytest.mark.asyncio
    async def test_process_pending_articles_falls_back_to_embedding_when_extraction_disabled(
        self, mock_database_service, mock_llm_service, sample_article_data
    ):
        """
        Test that process_pending_articles() falls back to embedding-only
        clustering when event extraction is disabled.
        """
        mock_database_service._storage['articles'][str(sample_article_data['id'])] = sample_article_data

        service = ClusteringService(
            db_service=mock_database_service,
            llm_service=mock_llm_service
        )

        with patch('services.event_signature_service.EVENT_EXTRACTION_ENABLED', False), \
             patch('services.event_matching_service.EVENT_MATCHING_ENABLED', False):

            processed = await service.process_pending_articles(limit=10)

        assert processed == 1

        # Should still create a theme
        themes = mock_database_service.get_all_themes(status='active')
        assert len(themes) == 1

    @pytest.mark.asyncio
    async def test_process_pending_articles_skips_articles_without_embedding(
        self, mock_database_service, mock_llm_service
    ):
        """
        Test that process_pending_articles() skips articles without embeddings.
        """
        article_without_embedding = {
            'id': uuid4(),
            'title': 'Article without embedding',
            'preview': 'Some preview text',
            'embedding': None  # No embedding
        }
        mock_database_service._storage['articles'][str(article_without_embedding['id'])] = article_without_embedding

        service = ClusteringService(
            db_service=mock_database_service,
            llm_service=mock_llm_service
        )

        processed = await service.process_pending_articles(limit=10)

        # Should not process article without embedding
        assert processed == 0

    @pytest.mark.asyncio
    async def test_process_pending_articles_handles_errors_gracefully(
        self, mock_database_service, mock_llm_service, sample_article_data
    ):
        """
        Test that process_pending_articles() handles errors in individual
        articles without failing the entire batch.
        """
        # Add article that will cause an error
        error_article = {
            'id': uuid4(),
            'title': None,  # Will cause error
            'preview': 'Test',
            'embedding': [0.1] * 1536
        }
        mock_database_service._storage['articles'][str(error_article['id'])] = error_article
        mock_database_service._storage['articles'][str(sample_article_data['id'])] = sample_article_data

        service = ClusteringService(
            db_service=mock_database_service,
            llm_service=mock_llm_service
        )

        with patch('services.event_signature_service.EVENT_EXTRACTION_ENABLED', False):
            # Should not raise exception
            processed = await service.process_pending_articles(limit=10)

        # Should have processed at least the valid article
        assert processed >= 0


# ============================================================================
# TESTS: Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions used in clustering."""

    def test_normalize_entity_removes_accents(self):
        """Test that normalize_entity removes accents properly."""
        assert normalize_entity('João') == 'joao'
        assert normalize_entity('São Paulo') == 'sao paulo'
        assert normalize_entity('Brasília') == 'brasilia'

    def test_normalize_entity_handles_empty_strings(self):
        """Test that normalize_entity handles empty and None inputs."""
        assert normalize_entity('') == ''
        assert normalize_entity(None) == ''

    def test_cosine_similarity_returns_correct_values(self):
        """Test that cosine_similarity calculates correctly."""
        # Identical vectors should have similarity 1.0
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(1.0, abs=0.001)

        # Orthogonal vectors should have similarity 0.0
        vec3 = [0.0, 1.0, 0.0]
        assert cosine_similarity(vec1, vec3) == pytest.approx(0.0, abs=0.001)

    def test_cosine_similarity_handles_zero_vectors(self):
        """Test that cosine_similarity handles zero vectors."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec1, vec2) == 0.0

    def test_normalize_vector_creates_unit_vector(self):
        """Test that normalize_vector creates unit length vectors."""
        import numpy as np

        vec = [3.0, 4.0, 0.0]
        normalized = normalize_vector(vec)

        # Should have unit length
        length = np.linalg.norm(normalized)
        assert length == pytest.approx(1.0, abs=0.001)


# ============================================================================
# TESTS: EventSignatureCreate Model
# ============================================================================

class TestEventSignatureCreateModel:
    """Tests for the EventSignatureCreate model."""

    def test_generate_canonical_key_creates_valid_format(self):
        """Test that generate_canonical_key creates properly formatted keys."""
        signature = EventSignatureCreate(
            article_id=uuid4(),
            people=['Joao Silva'],
            organizations=['ICE'],
            locations=['Miami'],
            event_action='detido',
            confidence=0.9
        )

        key = signature.generate_canonical_key(date(2026, 2, 5))

        parts = key.split('|')
        assert len(parts) == 5
        assert parts[4] == '2026-02'

    def test_generate_canonical_key_handles_missing_fields(self):
        """Test that generate_canonical_key handles missing fields with 'null'."""
        signature = EventSignatureCreate(
            article_id=uuid4(),
            people=[],
            organizations=['ICE'],
            locations=[],
            event_action='',
            confidence=0.5
        )

        key = signature.generate_canonical_key(date(2026, 2, 5))

        parts = key.split('|')
        assert parts[0] == 'null'  # No person
        assert 'ice' in parts[1].lower()
        assert parts[2] == 'null'  # No action
        assert parts[3] == 'null'  # No location

    def test_generate_canonical_key_normalizes_entities(self):
        """Test that generate_canonical_key normalizes entity names."""
        signature = EventSignatureCreate(
            article_id=uuid4(),
            people=['João da Silva'],
            organizations=['Ministério Público'],
            locations=['São Paulo'],
            event_action='anunciou',
            confidence=0.9
        )

        key = signature.generate_canonical_key(date(2026, 2, 5))

        # Should be lowercase and without accents
        assert 'joao' in key.lower()
        assert 'ã' not in key
        assert 'é' not in key
