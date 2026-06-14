from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass

# Request comes in
# → FastAPI sees Depends(get_db)
# → Calls get_db()
# → get_db() opens a session and yields it
# → FastAPI passes that session to your route as db
# → Your route runs, uses db to query/save
# → Route finishes
# → Control returns to get_db()
# → get_db() commits and closes the session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise