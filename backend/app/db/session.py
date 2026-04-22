from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine_cache: dict[str, object] = {}
_session_factory_cache: dict[str, async_sessionmaker[AsyncSession]] = {}


def get_engine(database_url: str):
    engine = _engine_cache.get(database_url)
    if engine is None:
        engine = create_async_engine(database_url, pool_pre_ping=True)
        _engine_cache[database_url] = engine
    return engine


def get_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    session_factory = _session_factory_cache.get(database_url)
    if session_factory is None:
        engine = get_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        _session_factory_cache[database_url] = session_factory
    return session_factory
