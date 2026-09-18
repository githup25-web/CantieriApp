
"""Fixture condivise per i test di FASE 6.

Utilizza un database MongoDB separato `cantieri_test` per non
interferire con i dati di sviluppo.
"""

import asyncio
import os
import sys
from pathlib import Path

# Imposta il DB di test PRIMA di importare l'app
os.environ["DATABASE_NAME"] = "cantieri_test"

# Aggiunge la root del progetto al path per importare `backend.*`
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

from backend.main import app

TEST_DB_NAME = "cantieri_test"
TEST_MONGO_URI = "mongodb://localhost:27017"

# Collezioni usate dai servizi FASE 6
COLLECTIONS = [
    "cantiere_tasks",
    "presenze",
    "foto_avanzamento",
]

# Directory upload foto di test
UPLOAD_DIR = Path("backend/uploads/foto")


def _clean_db():
    """Pulisce le collezioni di test (bloccante, per uso in fixture)."""
    client = AsyncIOMotorClient(TEST_MONGO_URI)
    db = client[TEST_DB_NAME]

    async def _clean():
        for name in COLLECTIONS:
            await db[name].delete_many({})

    asyncio.run(_clean())
    client.close()


@pytest.fixture(scope="session")
def client():
    """TestClient con il lifespan attivo (connessione MongoDB)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_collections():
    """Pulisce le collezioni di test prima e dopo ogni test."""
    _clean_db()

    yield

    _clean_db()

    # Pulizia file upload generati dai test
    if UPLOAD_DIR.exists():
        for f in UPLOAD_DIR.iterdir():
            if f.is_file():
                f.unlink()


@pytest.fixture
def sample_cantiere_id() -> str:
    """ID cantiere di esempio per i test."""
    return "cantiere_test_001"


@pytest.fixture
def sample_worker_id() -> str:
    """ID worker di esempio per i test."""
    return "worker_test_001"
