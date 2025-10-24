from fastapi import FastAPI, HTTPException, Request
from datetime import datetime, timezone
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

from .models import Event, EventBatch
from .service import EventService
from .store import SQLiteEventStore

# Setup Logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("event_aggregator.main")


# Initialize Services

event_store = SQLiteEventStore("events.db")
event_service = EventService(event_store)


# Lifespan Event (startup/shutdown)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Memulai layanan dan inisialisasi database...")
        await event_store.initialize()
        await event_service.start()
        logger.info("Layanan siap dan berjalan ✅")
        yield
    except Exception as e:
        logger.error(f"Galat saat startup: {e}")
        raise
    finally:
        logger.info("Menutup layanan...")
        await event_service.stop()
        logger.info("Layanan berhasil dimatikan")


# FastAPI App

app = FastAPI(
    title="Event Aggregator API",
    description="Layanan agregator event: idempotensi, deduplikasi, dan penyimpanan persisten",
    version="1.0.0",
    lifespan=lifespan
)
start_time = datetime.now(timezone.utc)

# Global Error Handler

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)},
    )


# Routes

@app.get("/")
async def root():
    return {"status": "ok", "message": "Event Aggregator berjalan"}


@app.post("/publish")
async def publish_events(events: EventBatch):
    """Terima satu atau beberapa event dalam batch dan proses."""
    try:
        if not events.events:
            raise HTTPException(status_code=400, detail="No events provided")

        result = await event_service.process_events(events.events)
        # Tetap gunakan field yang sama agar kompatibel dengan test/klien
        return {
            "status": "success",
            "processed_count": result["processed"],
            "duplicate_dropped": result["duplicates"],
            "message": f"Processed {result['processed']} events, dropped {result['duplicates']} duplicates"
        }
    except Exception as e:
        logger.error(f"Galat di /publish: {e}")
        raise HTTPException(status_code=400, detail=str(e))
@app.get("/events")
async def get_events(topic: str | None = None):
    events = await event_service.get_events(topic)
    if topic and not events:
        raise HTTPException(status_code=404, detail=f"No events found for topic '{topic}'")
    return {"status": "success", "count": len(events), "data": events}

@app.get("/stats")
async def get_stats():
    stats = await event_service.get_stats()
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
    stats["uptime"] = round(uptime, 2)
    return {"status": "success", "stats": stats}


# Entry Point

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=True)
