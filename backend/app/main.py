from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from redis.asyncio import Redis

from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.container import ServiceContainer
from backend.app.core.logging import setup_logging
from backend.app.core.telemetry import setup_telemetry, shutdown_telemetry
from backend.app.db.init_db import init_models
from backend.app.db.repository import ReviewRepository
from backend.app.db.session import get_session_factory
from backend.app.services.cache.embeddings import EmbeddingService
from backend.app.services.cache.semantic_cache import SemanticCache
from backend.app.services.github.client import GitHubApiClient
from backend.app.services.llm.circuit_breaker import CircuitBreaker
from backend.app.services.llm.claude_client import ClaudeReviewer
from backend.app.services.llm.ensemble import MultiModelEnsemble
from backend.app.services.llm.ollama_client import OllamaReviewer
from backend.app.services.llm.openai_client import OpenAIReviewer
from backend.app.services.llm.oss_client import HeuristicReviewer
from backend.app.services.rate_limit import RateLimiter
from backend.app.services.reports.html_report import HtmlReportService
from backend.app.services.review_service import ReviewService

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)

    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    github_client = GitHubApiClient(
        token=settings.github_token,
        base_url=settings.github_api_base_url,
        max_files=settings.github_pr_max_files,
        max_file_chars=settings.github_pr_max_file_chars,
    )

    # Auto-create tables when the database is reachable to prevent runtime 500s
    # in fresh local environments.
    with suppress(Exception):
        await init_models()

    session_factory = get_session_factory(settings.database_url)

    repository = ReviewRepository(session_factory)
    embedding_service = EmbeddingService(settings)
    semantic_cache = SemanticCache(
        redis_client=redis_client,
        embedding_service=embedding_service,
        ttl_seconds=settings.cache_ttl_seconds,
        similarity_threshold=settings.cache_similarity_threshold,
        index_max_items=settings.cache_index_max_items,
    )

    claude = ClaudeReviewer(settings)
    openai = OpenAIReviewer(settings)
    heuristic = HeuristicReviewer()
    circuit_breaker = CircuitBreaker(
        failure_threshold=settings.circuit_breaker_failure_threshold,
        recovery_seconds=settings.circuit_breaker_recovery_seconds,
    )

    # Use Ollama-only mode if configured
    if settings.use_ollama_only:
        # Use same model for all 3 roles to speed up (3x faster)
        single_model = OllamaReviewer(settings, settings.ollama_primary_model)
        primary_reviewer = single_model
        secondary_reviewer = single_model
        tertiary_reviewer = single_model
    else:
        primary_reviewer = claude
        secondary_reviewer = openai
        tertiary_reviewer = heuristic

    ensemble = MultiModelEnsemble(
        claude_reviewer=primary_reviewer,
        openai_reviewer=secondary_reviewer,
        heuristic_reviewer=tertiary_reviewer,
        circuit_breaker=circuit_breaker,
        ollama_mode=settings.use_ollama_only,
    )

    html_report_service = HtmlReportService()
    rate_limiter = RateLimiter(
        redis_client=redis_client,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    review_service = ReviewService(
        ensemble=ensemble,
        semantic_cache=semantic_cache,
        repository=repository,
        html_report_service=html_report_service,
    )

    app.state.container = ServiceContainer(
        redis=redis_client,
        repository=repository,
        github_client=github_client,
        semantic_cache=semantic_cache,
        ensemble=ensemble,
        rate_limiter=rate_limiter,
        html_report_service=html_report_service,
        review_service=review_service,
    )

    # Redis may be unavailable during startup in local dev.
    with suppress(Exception):
        await redis_client.ping()

    yield

    await github_client.aclose()
    await redis_client.aclose()
    shutdown_telemetry()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
setup_telemetry(app, settings)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }
