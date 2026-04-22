from dataclasses import dataclass

from redis.asyncio import Redis

from backend.app.db.repository import ReviewRepository
from backend.app.services.cache.semantic_cache import SemanticCache
from backend.app.services.github.client import GitHubApiClient
from backend.app.services.llm.ensemble import MultiModelEnsemble
from backend.app.services.rate_limit import RateLimiter
from backend.app.services.reports.html_report import HtmlReportService
from backend.app.services.review_service import ReviewService


@dataclass
class ServiceContainer:
    redis: Redis
    repository: ReviewRepository
    github_client: GitHubApiClient
    semantic_cache: SemanticCache
    ensemble: MultiModelEnsemble
    rate_limiter: RateLimiter
    html_report_service: HtmlReportService
    review_service: ReviewService
