"""Embedding service for generating vector embeddings."""

import logging
from typing import List, Optional
import asyncio
import numpy as np

# Try to import sentence-transformers for local embeddings
try:
    from sentence_transformers import SentenceTransformer
    LOCAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    LOCAL_EMBEDDINGS_AVAILABLE = False

# Try to import OpenAI for fallback
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate and manage vector embeddings for document chunks.

    Default local model is BGE-M3: 1024-dim, multilingual, and the current
    SOTA for retrieval quality among open-source embedding models. This matters
    for SkuPhase because Nigerian curriculum/past-paper text mixes British
    English terminology with local examples; BGE-M3 retrieves far more
    accurately than the old all-MiniLM-L6-v2 (384-dim) without any API cost.
    all-MiniLM-L6-v2 is kept as a lightweight fallback when BGE-M3 cannot load.
    """

    # Primary local model - BGE-M3 (multilingual, 1024-dim, retrieval SOTA)
    LOCAL_MODEL = "BAAI/bge-m3"
    LOCAL_DIMENSION = 1024

    # Lightweight fallback local model
    FALLBACK_LOCAL_MODEL = "all-MiniLM-L6-v2"
    FALLBACK_LOCAL_DIMENSION = 384

    # OpenAI fallback model (only used if explicitly requested + key provided)
    OPENAI_MODEL = "text-embedding-3-small"
    OPENAI_DIMENSION = 1536

    def __init__(
        self,
        use_local: bool = True,
        openai_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize embedding service.

        Args:
            use_local: Use local embeddings (default: True for cost savings)
            openai_api_key: OpenAI API key for fallback (optional)
            model_name: Override the local SentenceTransformer model
        """
        self.model_name = model_name or self.LOCAL_MODEL
        self.use_local = use_local and LOCAL_EMBEDDINGS_AVAILABLE

        if self.use_local:
            try:
                logger.info(f"Initializing local embedding model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                if self.model_name == self.FALLBACK_LOCAL_MODEL:
                    self.dimension = self.FALLBACK_LOCAL_DIMENSION
                else:
                    self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"✅ Local embedding service ready with {self.dimension} dimensions")
            except Exception as e:
                if self.model_name != self.FALLBACK_LOCAL_MODEL and LOCAL_EMBEDDINGS_AVAILABLE:
                    logger.warning(
                        f"Failed to load {self.model_name} ({e}); falling back to "
                        f"{self.FALLBACK_LOCAL_MODEL}"
                    )
                    self.model = SentenceTransformer(self.FALLBACK_LOCAL_MODEL)
                    self.dimension = self.FALLBACK_LOCAL_DIMENSION
                    logger.info(
                        f"✅ Local embedding service ready (fallback) with "
                        f"{self.dimension} dimensions"
                    )
                else:
                    raise
        elif OPENAI_AVAILABLE and openai_api_key:
            # Initialize OpenAI client for fallback
            self.client = AsyncOpenAI(api_key=openai_api_key)
            self.dimension = self.OPENAI_DIMENSION
            logger.info(f"OpenAI embedding service ready with {self.dimension} dimensions")
        else:
            raise ValueError(
                "No embedding service available. "
                "Install sentence-transformers or provide OpenAI API key."
            )
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text chunk.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            ValueError: If embedding fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            if self.use_local:
                # Local embedding generation (synchronous, but fast)
                # Run in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None,
                    lambda: self.model.encode(text, convert_to_numpy=True)
                )
                logger.debug(f"Generated local embedding for text ({len(text)} chars)")
                return embedding.tolist()
            else:
                # OpenAI embedding generation
                response = await self.client.embeddings.create(
                    model=self.OPENAI_MODEL,
                    input=text,
                    encoding_format="float",
                )
                embedding = response.data[0].embedding
                logger.debug(f"Generated OpenAI embedding for text ({len(text)} chars)")
                return embedding
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise ValueError(f"Embedding generation failed: {str(e)}")
    
    async def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple text chunks (batch).
        
        Uses local model for efficient batch processing.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per batch (ignored for local model)
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If batch fails
        """
        if not texts:
            return []
        
        try:
            if self.use_local:
                # Local batch processing (very efficient)
                logger.info(f"Generating embeddings for {len(texts)} texts using local model")
                
                # Run in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
                )
                
                logger.info(f"✅ Generated {len(embeddings)} local embeddings successfully")
                return embeddings.tolist()
            else:
                # OpenAI batch processing (existing logic)
                all_embeddings = []
                
                if batch_size > 2048:
                    batch_size = 2048
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    logger.info(f"Generating embeddings for batch {i//batch_size + 1} ({len(batch)} texts)")
                    
                    response = await self.client.embeddings.create(
                        model=self.OPENAI_MODEL,
                        input=batch,
                        encoding_format="float",
                    )
                    
                    # Sort by index to match input order
                    embeddings = sorted(response.data, key=lambda x: x.index)
                    all_embeddings.extend([e.embedding for e in embeddings])
                    
                    # Add small delay between batches to avoid rate limits
                    if i + batch_size < len(texts):
                        await asyncio.sleep(0.1)
                
                logger.info(f"Generated {len(all_embeddings)} OpenAI embeddings successfully")
                return all_embeddings
                
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise ValueError(f"Batch embedding failed: {str(e)}")
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate embedding vector.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(embedding, list):
            return False
        
        if len(embedding) != self.dimension:
            return False
        
        # Check all elements are floats
        return all(isinstance(x, (int, float)) for x in embedding)
    
    async def similarity_search(
        self,
        query: str,
        embeddings: List[List[float]],
        top_k: int = 5,
    ) -> List[tuple[int, float]]:
        """
        Find most similar embeddings to a query using cosine similarity.
        
        Args:
            query: Query text
            embeddings: List of embeddings to search
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        if not embeddings:
            return []
        
        # Generate query embedding
        query_embedding = await self.embed_text(query)
        
        # Calculate cosine similarities
        similarities = []
        for idx, embedding in enumerate(embeddings):
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append((idx, similarity))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Convert to numpy arrays for efficient computation
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # Dot product
        dot_product = np.dot(v1, v2)
        
        # Magnitudes
        mag1 = np.linalg.norm(v1)
        mag2 = np.linalg.norm(v2)
        
        # Avoid division by zero
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        # Cosine similarity
        return float(dot_product / (mag1 * mag2))
    
    def get_dimension(self) -> int:
        """Return embedding dimension for database schema."""
        return self.dimension
