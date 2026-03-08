import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

# Import your routers
from src.routers import schema_parse_router, migration_router
from src.routers.synthetic_router import router as synthetic_router
from src.routers.dashboard_router import router as dashboard_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with auto-migration on startup"""
    # Startup
    logger.info("Starting up application...")
    
    # Initialize migration system on startup
    try:
        from src.utils.migrations import migrator
        logger.info("Initializing migration system...")
        
        # Create migrations directory and tracking table
        migrator.migrations_dir.mkdir(exist_ok=True)
        migrator.create_migrations_table()
        
        # Auto-run migrations on startup (optional - you can disable this)
        auto_migrate_on_startup = False  # Set to False if you want manual control
        
        if auto_migrate_on_startup:
            logger.info("Running auto-migration on startup...")
            result = migrator.auto_migrate()
            
            if result["success"]:
                logger.info(f"Auto-migration completed: {result['message']}")
            else:
                logger.warning(f"Auto-migration had issues: {result['message']}")
        
    except Exception as e:
        logger.error(f"Migration initialization failed: {e}")
        # Don't fail startup due to migration issues
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Schema Parser API",
    description="API for parsing SQL schemas with migration support",
    version="1.1.0",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(schema_parse_router, prefix="/api/v1")
app.include_router(migration_router, prefix="/api/v1")
app.include_router(synthetic_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Schema Parser API with Migration Support",
        "version": "1.1.0",
        "endpoints": {
            "schema_parser": "/api/v1/parse",
            "migrations": "/api/v1/migrations",
            "health": "/api/v1/health",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "features": [
            "SQL Schema Parsing",
            "Duplicate Prevention",
            "Database Migrations",
            "Content Hash Deduplication",
            "Filename Storage"
        ]
    }

@app.get("/health")
async def health_check():
    """Global health check endpoint"""
    return {
        "status": "healthy",
        "service": "Schema Parser API",
        "version": "1.1.0",
        "components": {
            "schema_parser": "active",
            "migrations": "active",
            "database": "connected"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )