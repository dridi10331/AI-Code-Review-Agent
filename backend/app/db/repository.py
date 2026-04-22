from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.models.db import ReviewRecord
from backend.app.models.review import ReviewHistoryItem, ReviewRequest, ReviewResponse


class ReviewRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_review(
        self,
        request: ReviewRequest,
        response: ReviewResponse,
        code_hash: str,
    ) -> None:
        async with self._session_factory() as session:
            record = ReviewRecord(
                id=response.review_id,
                user_id=request.user_id,
                repository=request.repository,
                file_path=request.file_path,
                language=request.language,
                code_hash=code_hash,
                summary=response.summary,
                overall_score=response.consensus_score,
                cache_hit=response.cache_hit,
                models_used=[item.model_dump() for item in response.model_results],
                request_payload=request.model_dump(),
                response_payload=response.model_dump(),
            )
            session.add(record)
            await session.commit()

    async def get_review(self, review_id: str) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            statement = select(ReviewRecord).where(ReviewRecord.id == review_id)
            result = await session.execute(statement)
            record = result.scalar_one_or_none()
            if record is None:
                return None
            return {
                "id": record.id,
                "user_id": record.user_id,
                "repository": record.repository,
                "file_path": record.file_path,
                "language": record.language,
                "summary": record.summary,
                "overall_score": record.overall_score,
                "cache_hit": record.cache_hit,
                "models_used": record.models_used,
                "request_payload": record.request_payload,
                "response_payload": record.response_payload,
                "created_at": record.created_at,
            }

    async def list_history(
        self,
        user_id: str | None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ReviewHistoryItem]:
        async with self._session_factory() as session:
            statement = (
                select(ReviewRecord)
                .order_by(desc(ReviewRecord.created_at))
                .limit(limit)
                .offset(offset)
            )
            if user_id:
                statement = statement.where(ReviewRecord.user_id == user_id)
            result = await session.execute(statement)
            records = result.scalars().all()
            return [
                ReviewHistoryItem(
                    review_id=item.id,
                    user_id=item.user_id,
                    repository=item.repository,
                    file_path=item.file_path,
                    overall_score=item.overall_score,
                    cache_hit=item.cache_hit,
                    created_at=item.created_at,
                )
                for item in records
            ]
