from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import get_settings
from backend.core.database import (
    close_mongo_connection,
    connect_to_mongo,
    init_collections,
)
from backend.dependencies import auth as auth_deps
from backend.routes.auth import router as auth_router
from backend.routes.tenant import router as tenant_router
from backend.routes.invite import router as invite_router
from backend.routes.presence import router as presence_router
from backend.routes.expense import router as expense_router
from backend.routes.photo import router as photo_router
from backend.routes.task import router as task_router
from backend.routes.task_routes import router as task_routes_router
from backend.routes.presenza_routes import router as presenza_routes_router
from backend.routes.foto_routes import router as foto_routes_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    await connect_to_mongo()
    await init_collections()
    print(f"[APP] {settings.app_name} started in {settings.app_environment} mode")
    yield
    # Shutdown
    await close_mongo_connection()
    print("[APP] Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend per CantieriApp con FastAPI e MongoDB (Motor/PyMongo)",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(tenant_router)
app.include_router(invite_router)
app.include_router(presence_router)
app.include_router(expense_router)
app.include_router(photo_router)
app.include_router(task_router)
app.include_router(task_routes_router)
app.include_router(presenza_routes_router)
app.include_router(foto_routes_router)

# File statici (foto di avanzamento caricate via multipart)
Path("backend/uploads").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="backend/uploads"), name="uploads")


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "message": f"{settings.app_name} is running",
        "environment": settings.app_environment,
        "database": settings.database_name,
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    from backend.core.database import get_database

    try:
        db = get_database()
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}
