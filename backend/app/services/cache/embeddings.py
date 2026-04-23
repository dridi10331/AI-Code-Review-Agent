import hashlib
import math
import re
from collections.abc import Sequence

from openai import AsyncOpenAI

from backend.app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._dimension = settings.cache_embedding_dimension
        self._model = settings.openai_embedding_model
        # Force local embeddings when using Ollama-only mode
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key and not settings.use_ollama_only
            else None
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        if self._client:
            try:
                response = await self._client.embeddings.create(
                    model=self._model,
                    input=text[:12000],
                )
                vector = response.data[0].embedding
                return self._normalize(vector[: self._dimension])
            except Exception:
                # Fallback to deterministic local embedding when API is unavailable.
                pass

        return self._local_embedding(text)

    def cosine_similarity(self, vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        if not vec_a or not vec_b:
            return 0.0

        size = min(len(vec_a), len(vec_b))
        dot = sum(vec_a[i] * vec_b[i] for i in range(size))
        norm_a = math.sqrt(sum(value * value for value in vec_a[:size]))
        norm_b = math.sqrt(sum(value * value for value in vec_b[:size]))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _local_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())[:3000]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self._dimension
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            magnitude = 1.0 + (digest[3] / 255.0)
            vector[index] += sign * magnitude

        return self._normalize(vector)

    @staticmethod
    def _normalize(vector: Sequence[float]) -> list[float]:
        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0:
            return list(vector)
        return [component / norm for component in vector]
