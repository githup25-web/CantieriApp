"""Fixture condivise per i test di FASE 7 (Cliente).

Utilizza un database MongoDB separato `cantieriapp_test` per non
interferire con i dati di sviluppo.
"""

import asyncio
import os
import sys
from pathlib import Path

# Imposta il DB di test PRIMA di importare l'app
os.environ["MONGO_DB_NAME"] = "cantieriapp_test"

# Aggiunge la root del progetto al path per importare `app.*` e `main`
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

from main import app

TEST_DB_NAME = "cantieriapp_test"
TEST_MONGO_URI = "mongodb://localhost:27017"

# Collezioni usate dai servizi FASE 7 e FASE 8
COLLECTIONS = [
    "clienti",
    "cliente_access_codes",
    "cantieri",
    "tasks",
    "presences",
    "progress_photos",
    "notifications",
    "expenses",
    "cantiere_documents",
    "event_records",
    "users",
    "organizations",
    "memberships",
]


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
    """TestClient con il lifespan attivo (connessione MongoDB + Beanie)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_collections():
    """Pulisce le collezioni di test prima e dopo ogni test."""
    _clean_db()

    yield

    _clean_db()


@pytest.fixture
def sample_tenant_id() -> str:
    """UUID tenant di esempio per i test."""
    import uuid

    return str(uuid.uuid4())


@pytest.fixture
def sample_cliente_payload(sample_tenant_id: str) -> dict:
    """Payload di esempio per la creazione di un cliente."""
    return {
        "full_name": "Mario Rossi",
        "tenant_id": sample_tenant_id,
    }
