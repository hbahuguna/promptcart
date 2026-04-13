import asyncio
import logging
import contextlib

from fastapi import FastAPI

from app.redis_listener import start_listener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator_main")

# Global handle for background worker cleanup
listener_task = None
stop_event = asyncio.Event()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global listener_task
    stop_event.clear()
    
    # Fire and forget the background redis polling task
    logger.info("Initializing Orchestrator Lifespan Events...")
    listener_task = asyncio.create_task(start_listener(stop_event))
    
    yield
    
    # Shutdown gracefully
    logger.info("Destroying Orchestrator Lifespan Events...")
    stop_event.set()
    if listener_task:
        listener_task.cancel()
        try:
            await list_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="PromptCart Conversation Orchestrator",
    description="Microservice 4/9 — Event Coordination and Intent Matching",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok", "service": "orchestrator"}
