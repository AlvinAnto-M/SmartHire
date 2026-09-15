"""
Embedding utilities supporting Google Generative AI embeddings and local fallback.
"""

from typing import List
import numpy as np
from ..config import GEMINI_API_KEY, EMBEDDING_MODEL_NAME, check_api_key

_embedding_instance = None

def get_embedding_model():
    """
    Returns an instance of LangChain compatible embedding class.
    Uses GoogleGenerativeAIEmbeddings when API key is provided,
    otherwise falls back to a deterministic fallback embedder.
    """
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance

    if check_api_key():
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            _embedding_instance = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL_NAME,
                google_api_key=GEMINI_API_KEY
            )
            return _embedding_instance
        except Exception:
            pass

    # Fallback embedding class for offline or demo usage without API key
    class FallbackEmbedding:
        """Deterministic keyword-frequency vectorizer ensuring offline testing works."""
        def __init__(self, dim=768):
            self.dim = dim

        def _vectorize(self, text: str) -> List[float]:
            vec = np.zeros(self.dim, dtype=np.float32)
            words = text.lower().split()
            if not words:
                return vec.tolist()
            for w in words:
                idx = abs(hash(w)) % self.dim
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec.tolist()

        def embed_query(self, text: str) -> List[float]:
            return self._vectorize(text)

        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            return [self._vectorize(t) for t in texts]

    _embedding_instance = FallbackEmbedding()
    return _embedding_instance

def embed_text(text: str) -> List[float]:
    """Generates embedding vector for a single query text."""
    model = get_embedding_model()
    return model.embed_query(text)

def embed_documents(texts: List[str]) -> List[List[float]]:
    """Generates embedding vectors for a list of document strings."""
    model = get_embedding_model()
    return model.embed_documents(texts)
