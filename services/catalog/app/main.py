import contextlib
import logging

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import products

logger = logging.getLogger("catalog_service")
logging.basicConfig(level=logging.INFO)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are created dynamically
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
    title="PromptCart Catalog Service",
    description="Microservice 3/9 — Pricing and Catalog Management",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(products.router)


@app.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok", "service": "catalog"}
