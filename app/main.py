"""
FastAPI application entry point - Personal Intelligence Hub.
"""
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import tasks
from app.routers import schedules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Personal Intelligence Hub",
    description="Multi-agent AI task and schedule management system.",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(schedules.router)

static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified (tasks + schedules).")
    except Exception as e:
        logger.error(f"Database startup error: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0", "agents": ["coordinator", "task_agent", "schedule_agent"]}

@app.get("/")
async def root():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Personal Intelligence Hub API", "docs": "/docs"}
