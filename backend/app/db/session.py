from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine_cache: dict[str, object] = {}
_session_factory_cache: dict[str, async_sessionmaker[AsyncSession]] = {}


def get_engine(database_url: str):
    """Create or retrieve cached async engine with optimal connection pooling settings.
    
    Args:
        database_url: SQLAlchemy async database URL
        
    Returns:
        Configured async engine with connection pooling
    """
    engine = _engine_cache.get(database_url)
    if engine is None:
        # pool_pre_ping: Test connections before using them (detects stale connections)
        # pool_size: Number of connections to maintain (default: 5)
        # max_overflow: Additional connections allowed when pool exhausted (default: 10)
        # echo_pool: Log pool checkout/checkin events for debugging (set to True if needed)
        engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=30,
            echo=False,
        )
        _engine_cache[database_url] = engine
    return engine


def get_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    session_factory = _session_factory_cache.get(database_url)
    if session_factory is None:
        engine = get_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        _session_factory_cache[database_url] = session_factory
    return session_factory
