import contextlib
import logging

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import vendors

logger = logging.getLogger("vendor_management")
logging.basicConfig(level=logging.INFO)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are created (useful for rapid dev mode without Alembic)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing DB tables: {e}")

    yield

    # Clean up DB connections on shutdown
    await engine.dispose()


app = FastAPI(
    title="PromptCart Vendor Management",
    description="Microservice 2/9 — CRUD API for Dark Stores and Local Shopkeepers",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(vendors.router)


@app.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok", "service": "vendor-management"}
