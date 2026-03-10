from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import routers
from src.routers.parse_router import router as parse_router
from src.routers.schema_router import router as schema_router
from src.routers.migration_router import router as migration_router
from src.routers.synthetic_router import router as synthetic_router
from src.routers.dashboard_router import router as dashboard_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with auto-migration on startup."""
    logger.info("Starting up BurstDB API...")

    try:
        from src.utils.migrations import migrator

        migrator.migrations_dir.mkdir(exist_ok=True)
        migrator.create_migrations_table()

        auto_migrate_on_startup = False
        if auto_migrate_on_startup:
            result = migrator.auto_migrate()
            if result["success"]:
                logger.info(f"Auto-migration completed: {result['message']}")
            else:
                logger.warning(f"Auto-migration issue: {result['message']}")
    except Exception as e:
        logger.error(f"Migration init failed: {e}")

    # Start the job manager so queued jobs are actually processed
    from src.utils.job_manager import job_manager
    job_manager.start()
    logger.info("Job manager started")

    yield

    # Graceful shutdown
    job_manager.stop()
    logger.info("Shutting down BurstDB API...")


# FastAPI app
app = FastAPI(
    title="BurstDB API",
    description="Synthetic data generation pipeline — parse schemas from SQL, Supabase, MongoDB, and Neo4j, then generate realistic mock data using SDV.",
    version="2.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(parse_router, prefix="/api/v1")
app.include_router(schema_router, prefix="/api/v1")
app.include_router(migration_router, prefix="/api/v1")
app.include_router(synthetic_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "BurstDB API",
        "version": "2.0.0",
        "endpoints": {
            "parse": "/api/v1/parse",
            "schemas": "/api/v1/schemas",
            "generate": "/api/v1/generate",
            "dashboard": "/api/v1/dashboard",
            "migrations": "/api/v1/migrations",
            "health": "/api/v1/health",
            "docs": "/docs",
        },
        "features": [
            "SQL Schema Parsing",
            "Supabase Integration",
            "MongoDB Schema Extraction",
            "Neo4j Graph Schema Extraction",
            "SDV Synthetic Data Generation",
            "Content Hash Deduplication",
        ],
    }


@app.get("/health")
async def health_check():
    """Global health check."""
    return {
        "status": "healthy",
        "service": "BurstDB API",
        "version": "2.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")