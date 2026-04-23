import json
from datetime import UTC, datetime

from redis.asyncio import Redis

from backend.app.models.review import ReviewResponse
from backend.app.services.cache.embeddings import EmbeddingService
from backend.app.utils.hashing import normalized_code_hash


class SemanticCache:
    def __init__(
        self,
        redis_client: Redis,
        embedding_service: EmbeddingService,
        ttl_seconds: int,
        similarity_threshold: float,
        index_max_items: int = 1500,
    ) -> None:
        self._redis = redis_client
        self._embedding_service = embedding_service
        self._ttl_seconds = ttl_seconds
        self._similarity_threshold = similarity_threshold
        self._index_key_prefix = "semantic_cache:index"
        self._index_max_items = index_max_items

    def _index_key(self, language: str) -> str:
        lang = (language or "text").strip().lower() or "text"
        return f"{self._index_key_prefix}:{lang}"

    async def lookup(self, code: str, language: str) -> tuple[ReviewResponse | None, float]:
        exact_hash = normalized_code_hash(code, language)
        exact_key = f"semantic_cache:exact:{exact_hash}"
        cache_id = await self._redis.get(exact_key)
        if cache_id:
            response = await self._load_response(cache_id)
            if response:
                response.cache_hit = True
                return response, 1.0

        # Include language in the semantic vector so identical snippets in
        # different languages don't get treated as exact semantic matches.
        query_embedding = await self._embedding_service.embed(f"{language}\n{code}")
        # Use a per-language capped index so lookup time doesn't grow unbounded.
        candidate_ids = await self._redis.zrevrange(self._index_key(language), 0, self._index_max_items - 1)

        best_similarity = 0.0
        best_cache_id: str | None = None

        for cache_id in candidate_ids:
            item_key = f"semantic_cache:item:{cache_id}"
            item_payload = await self._redis.hget(item_key, "embedding")
            if not item_payload:
                continue
            try:
                vector = json.loads(item_payload)
            except json.JSONDecodeError:
                continue
            similarity = self._embedding_service.cosine_similarity(query_embedding, vector)
            if similarity > best_similarity:
                best_similarity = similarity
                best_cache_id = cache_id

        if best_cache_id and best_similarity >= self._similarity_threshold:
            response = await self._load_response(best_cache_id)
            if response:
                response.cache_hit = True
                return response, best_similarity

        return None, best_similarity

    async def store(self, code: str, language: str, response: ReviewResponse) -> None:
        cache_id = response.review_id
        item_key = f"semantic_cache:item:{cache_id}"
        exact_hash = normalized_code_hash(code, language)
        exact_key = f"semantic_cache:exact:{exact_hash}"

        embedding = await self._embedding_service.embed(f"{language}\n{code}")
        payload = {
            "embedding": json.dumps(embedding),
            "response": json.dumps(response.model_dump(mode="json"), default=str),
            "created_at": datetime.now(UTC).isoformat(),
        }

        await self._redis.hset(item_key, mapping=payload)
        await self._redis.expire(item_key, self._ttl_seconds)
        index_key = self._index_key(language)
        await self._redis.zadd(index_key, {cache_id: datetime.now(UTC).timestamp()})
        count = await self._redis.zcard(index_key)
        if count > self._index_max_items:
            await self._redis.zremrangebyrank(index_key, 0, count - self._index_max_items - 1)
        await self._redis.set(exact_key, cache_id, ex=self._ttl_seconds)

    async def _load_response(self, cache_id: str) -> ReviewResponse | None:
        item_key = f"semantic_cache:item:{cache_id}"
        response_payload = await self._redis.hget(item_key, "response")
        if not response_payload:
            return None
        try:
            data = json.loads(response_payload)
        except json.JSONDecodeError:
            return None
        return ReviewResponse.model_validate(data)
