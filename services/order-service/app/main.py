import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
from app import events
from app.routers import orders

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB natively bridging relations before running event loops
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Connect Redis
    await events.init_redis()
    
    yield
    
    # Cleanup
    await events.close_redis()

app = FastAPI(title="Order Service", lifespan=lifespan)
app.include_router(orders.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
