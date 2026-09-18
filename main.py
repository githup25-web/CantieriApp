from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import pkgutil
from typing import Any

import uvicorn
from beanie import Document, init_beanie
from beanie.exceptions import CollectionWasNotInitialized
from fastapi import FastAPI, Request

from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.models.dead_letter import DeadLetter
from app.routes.auth import router as auth_router
from app.routes.cantiere import router as cantiere_router
from app.routes.cantiere_document import router as cantiere_document_router
from app.routes.events import router as events_router
from app.routes.expense import router as expense_router
from app.routes.fattura import router as fattura_router
from app.routes.health import router as health_router
from app.routes.invite import router as invite_router
from app.routes.notification import router as notification_router
from app.routes.organization import router as organization_router
from app.routes.presence import router as presence_router
from app.routes.preventivo import router as preventivo_router
from app.routes.progress_photo import router as progress_photo_router
from app.routes.task import router as task_router
from app.routes.cliente.area import router as cliente_area_router
from app.routes.cliente.cliente_routes import router as cliente_routes_router
from app.routes.cliente.feedback import router as cliente_feedback_router
from app.services.notification_service import register_notification_listeners
from app.scheduler.scheduler import scheduler_loop

settings = get_settings()

# Configure structured logging
logger = logging.getLogger("cantieriapp")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)

app = FastAPI(
    title="CantieriApp API",
    version="0.1.0",
    description="Backend iniziale per CantieriApp con FastAPI e MongoDB",
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(invite_router)
app.include_router(presence_router)
app.include_router(cliente_feedback_router)
app.include_router(cliente_area_router)
app.include_router(cliente_routes_router)
app.include_router(expense_router)
app.include_router(progress_photo_router)
app.include_router(task_router)
app.include_router(cantiere_router)
app.include_router(cantiere_document_router)
app.include_router(preventivo_router)
app.include_router(fattura_router)
app.include_router(notification_router)
app.include_router(events_router)


def _iter_all_model_classes(package_name: str) -> list[type[Document]]:
    """
    Importa automaticamente tutti i moduli in app/models e raccoglie tutte le classi
    che ereditano da beanie.Document.
    """
    package = importlib.import_module(package_name)

    document_classes: list[type[Document]] = []
    seen: set[type[Document]] = set()

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, Document):
                continue
            if obj is Document:
                continue
            if obj in seen:
                continue
            seen.add(obj)
            document_classes.append(obj)

    return document_classes


# Nota: in questo progetto lo scheduler è implementato in app/scheduler/scheduler.py
# e i job (incluso cleanup_dlq) vengono registrati automaticamente con @scheduled_job.


# Debug helper: log exception tracebacks to console (useful for critical-path tests)
@app.middleware("http")
async def debug_exceptions_middleware(request: Request, call_next):
    import traceback

    try:
        return await call_next(request)
    except Exception:
        traceback.print_exc()
        raise


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting CantieriApp backend in %s mode", settings.app_environment)
    await connect_to_mongo()

    # init_beanie su tutti i Document presenti in app/models/
    models = _iter_all_model_classes("app.models")

    # In alcuni progetti potrebbe esserci anche la necessità di includere esplicitamente DeadLetter
    # se non viene rilevato (ma in questo repo è in app/models/dead_letter.py).
    if DeadLetter not in models:
        models.append(DeadLetter)

    # connection_string: formatto come "mongodb_uri/db_name" come nel tuo setup attuale
    connection_string = f"{settings.mongo_uri}/{settings.mongo_db_name}"

    try:
        await init_beanie(connection_string=connection_string, document_models=models)
    except CollectionWasNotInitialized:
        # Se beanie segnala una race/collection non pronta, proviamo ancora una volta.
        # (In genere non dovrebbe succedere, ma richiesto esplicitamente nel task.)
        await init_beanie(connection_string=connection_string, document_models=models)

    await register_notification_listeners()

    # Avvio scheduler background (non deve crashare).
    # Il modulo app.scheduler.scheduler auto-loada i job in app.scheduler.jobs (cleanup_dlq incluso).
    asyncio.create_task(scheduler_loop())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    # Lo scheduler loop è un background task; chiudiamo solo la connessione Mongo.
    await close_mongo_connection()


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "message": "CantieriApp backend is running",
        "environment": settings.app_environment,
    }


# Compatibile con `uvicorn main:app --reload` (nessun guard __main__ necessario).
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
