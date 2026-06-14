from fastapi import FastAPI
from app.core.config import get_settings
from app.api.v1 import users, linkedin
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(users.router, prefix="/api/v1")
app.include_router(linkedin.router, prefix="/api/v1/linkedin")
@app.get("/")
async def health_check():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "app": settings.app_name,
        "database": db_status,
    }
