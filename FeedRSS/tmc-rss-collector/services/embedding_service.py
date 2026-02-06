"""
Embedding Service for TMC RSS Collector

Generates vector embeddings for articles using Azure OpenAI's text-embedding-3-small model.
Supports batch processing for efficient API usage.
"""

import os
import logging
import asyncio
from typing import List, Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

# Configuration - Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.environ.get(
    "AZURE_OPENAI_ENDPOINT",
    "https://modelos-chave-jaar-resource.cognitiveservices.azure.com"
)
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small default

# Batch processing limits
MAX_BATCH_SIZE = 50  # Azure OpenAI allows up to 2048, but 50 is safer for article content
MAX_TEXT_LENGTH = 8000  # First 8000 characters of title + content
EMBEDDING_TIMEOUT = 120  # seconds


class EmbeddingService:
    """Service for generating text embeddings using Azure OpenAI API."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        """
        Initialize the Embedding service.

        Args:
            api_key: Azure OpenAI API key (defaults to AZURE_OPENAI_API_KEY env var)
            endpoint: Azure OpenAI endpoint (defaults to AZURE_OPENAI_ENDPOINT env var)

        Raises:
            ValueError: If no API key is configured
        """
        self.api_key = api_key or AZURE_OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not configured")

        self.base_endpoint = (endpoint or AZURE_OPENAI_ENDPOINT).rstrip('/')
        self.deployment = AZURE_OPENAI_DEPLOYMENT
        self.api_version = AZURE_OPENAI_API_VERSION

        # Build the full endpoint URL for Azure OpenAI
        self.endpoint = (
            f"{self.base_endpoint}/openai/deployments/{self.deployment}"
            f"/embeddings?api-version={self.api_version}"
        )

        self.http_client = httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT)

        logger.info(f"EmbeddingService initialized with Azure OpenAI deployment: {self.deployment}")

    def _get_headers(self) -> dict:
        """Get headers for Azure OpenAI API request."""
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

    def _prepare_text(self, title: str, content: Optional[str] = None) -> str:
        """
        Prepare text for embedding by combining title and content.

        Args:
            title: Article title
            content: Article content (optional)

        Returns:
            Combined text, truncated to MAX_TEXT_LENGTH
        """
        if content:
            # Combine title and content with separator
            text = f"{title}\n\n{content}"
        else:
            text = title

        # Truncate to max length
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]

        return text.strip()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector (1536 dimensions)

        Raises:
            RuntimeError: If API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        embeddings = await self.generate_embeddings_batch([text])
        return embeddings[0]

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = MAX_BATCH_SIZE
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Processes texts in batches of up to 50 per API call for efficiency.

        Args:
            texts: List of texts to generate embeddings for
            batch_size: Maximum texts per API call (default: 50)

        Returns:
            List of embedding vectors, one per input text

        Raises:
            RuntimeError: If API call fails
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty texts and track indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text.strip())
                valid_indices.append(i)
            else:
                logger.warning(f"Skipping empty text at index {i}")

        if not valid_texts:
            raise ValueError("All texts are empty")

        all_embeddings = [None] * len(texts)  # Pre-allocate with None
        batch_size = min(batch_size, MAX_BATCH_SIZE)

        # Process in batches
        for batch_start in range(0, len(valid_texts), batch_size):
            batch_end = min(batch_start + batch_size, len(valid_texts))
            batch_texts = valid_texts[batch_start:batch_end]
            batch_indices = valid_indices[batch_start:batch_end]

            logger.debug(
                f"Processing embedding batch {batch_start // batch_size + 1}: "
                f"{len(batch_texts)} texts"
            )

            try:
                batch_embeddings = await self._call_embedding_api(batch_texts)

                # Map embeddings back to original indices
                for idx, embedding in zip(batch_indices, batch_embeddings):
                    all_embeddings[idx] = embedding

            except Exception as e:
                logger.error(f"Embedding batch failed: {e}")
                raise

        # Replace None values with empty embeddings for skipped texts
        for i in range(len(all_embeddings)):
            if all_embeddings[i] is None:
                all_embeddings[i] = [0.0] * EMBEDDING_DIMENSIONS

        return all_embeddings

    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """
        Make API call to Azure OpenAI embeddings endpoint.

        Args:
            texts: List of texts (max 50)

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If API call fails
        """
        headers = self._get_headers()

        # Azure OpenAI uses deployment name in URL, not in payload
        payload = {
            "input": texts
        }

        logger.info(f"Calling Azure OpenAI Embeddings API for {len(texts)} texts")

        try:
            response = await self.http_client.post(
                self.endpoint,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Azure OpenAI API error {response.status_code}: {error_text}")
                raise RuntimeError(f"Azure OpenAI API error: {error_text}")

            result = response.json()

            # Extract embeddings, sorted by index to maintain order
            data = result.get("data", [])
            data_sorted = sorted(data, key=lambda x: x.get("index", 0))
            embeddings = [item["embedding"] for item in data_sorted]

            # Log usage info
            usage = result.get("usage", {})
            logger.info(
                f"Embeddings generated: {len(embeddings)} vectors, "
                f"tokens used: {usage.get('total_tokens', 'N/A')}"
            )

            return embeddings

        except httpx.TimeoutException:
            logger.error(f"Azure OpenAI API timeout after {EMBEDDING_TIMEOUT}s")
            raise RuntimeError("Azure OpenAI API request timed out")
        except Exception as e:
            logger.error(f"Azure OpenAI API request failed: {e}")
            raise

    async def process_pending_articles(
        self,
        db_service: Any,
        limit: int = 50
    ) -> int:
        """
        Process articles that don't have embeddings yet.

        Fetches articles without embeddings from the database,
        generates embeddings, and updates the records.

        Args:
            db_service: DatabaseService instance for database operations
            limit: Maximum number of articles to process (default: 50)

        Returns:
            Number of articles successfully processed

        Note:
            This method requires the database to have:
            - has_embedding column on collected_articles table
            - embedding column to store the vector
        """
        logger.info(f"Processing up to {limit} articles without embeddings")

        try:
            # Get articles without embeddings
            articles = await self._get_articles_without_embeddings(db_service, limit)

            if not articles:
                logger.info("No articles pending embedding generation")
                return 0

            logger.info(f"Found {len(articles)} articles to process")

            # Prepare texts for embedding
            texts = []
            article_ids = []
            for article in articles:
                text = self._prepare_text(
                    article.get("title", ""),
                    article.get("content")
                )
                texts.append(text)
                article_ids.append(article.get("id"))

            # Generate embeddings in batches
            embeddings = await self.generate_embeddings_batch(texts)

            # Update articles with embeddings
            updated_count = await self._update_article_embeddings(
                db_service,
                article_ids,
                embeddings
            )

            logger.info(f"Successfully updated {updated_count} articles with embeddings")
            return updated_count

        except Exception as e:
            logger.error(f"Error processing pending articles: {e}")
            raise

    async def _get_articles_without_embeddings(
        self,
        db_service: Any,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch articles that don't have embeddings yet.

        Args:
            db_service: DatabaseService instance
            limit: Maximum number of articles to fetch

        Returns:
            List of article dicts with id, title, content
        """
        query = """
            SELECT TOP (%s) id, title, content
            FROM collected_articles
            WHERE has_embedding = 0 OR has_embedding IS NULL
            ORDER BY collected_at DESC
        """

        # Run synchronously since pymssql is not async
        def _fetch():
            with db_service.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                return [
                    {"id": row[0], "title": row[1], "content": row[2]}
                    for row in rows
                ]

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fetch)

    async def _update_article_embeddings(
        self,
        db_service: Any,
        article_ids: List[str],
        embeddings: List[List[float]]
    ) -> int:
        """
        Update articles with their generated embeddings.

        Args:
            db_service: DatabaseService instance
            article_ids: List of article UUIDs
            embeddings: List of embedding vectors

        Returns:
            Number of articles updated
        """
        import json

        update_query = """
            UPDATE collected_articles
            SET embedding = %s, has_embedding = 1, embedding_updated_at = GETUTCDATE()
            WHERE id = %s
        """

        def _update():
            updated = 0
            with db_service.get_connection() as conn:
                cursor = conn.cursor()
                for article_id, embedding in zip(article_ids, embeddings):
                    try:
                        # Store embedding as JSON string
                        embedding_json = json.dumps(embedding)
                        cursor.execute(update_query, (embedding_json, str(article_id)))
                        updated += 1
                    except Exception as e:
                        logger.error(f"Failed to update article {article_id}: {e}")
                        continue
                conn.commit()
            return updated

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _update)

    async def generate_article_embedding(
        self,
        title: str,
        content: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding for an article using title and content.

        Convenience method that prepares the text and generates embedding.

        Args:
            title: Article title
            content: Article content (optional)

        Returns:
            Embedding vector (1536 dimensions)
        """
        text = self._prepare_text(title, content)
        return await self.generate_embedding(text)

    async def close(self):
        """Close the HTTP client connection."""
        await self.http_client.aclose()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            if hasattr(self, 'http_client') and self.http_client:
                # Can't await in __del__, so just attempt sync close
                pass
        except Exception:
            pass


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the EmbeddingService singleton.

    Returns:
        EmbeddingService instance

    Raises:
        ValueError: If AZURE_OPENAI_API_KEY is not configured
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def is_embedding_configured() -> bool:
    """Check if embedding service is properly configured."""
    return bool(AZURE_OPENAI_API_KEY)
