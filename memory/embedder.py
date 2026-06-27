from functools import lru_cache

import numpy as np

from app.config import settings


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model)


def embed(texts: list[str]) -> np.ndarray:
    """Embed a list of texts, returning a 2D array of shape (N, dim)."""
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def embed_single(text: str) -> list[float]:
    """Embed a single text string, returning a plain float list."""
    return embed([text])[0].tolist()
