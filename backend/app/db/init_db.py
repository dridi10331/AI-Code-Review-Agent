import asyncio

from backend.app.core.config import get_settings
from backend.app.db.session import get_engine
from backend.app.models.db import Base


async def init_models() -> None:
    settings = get_settings()
    engine = get_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_models())
