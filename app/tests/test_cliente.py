"""Test automatici per le rotte del Cliente (FASE 7 e FASE 8)."""

import uuid

from app.models.cantiere import Cantiere
from app.models.cliente import Cliente
from app.models.task import Task
from app.models.presence import Presence
from app.models.progress_photo import ProgressPhoto


def _create_cantiere(tenant_id: str) -> Cantiere:
    """Crea e salva un cantiere di test nel DB."""
    cantiere = Cantiere(
        organization_id=uuid.UUID(tenant_id),
        title="Cantiere Test",
        description="Cantiere di test",
        status="in_corso",
    )
    return cantiere


class TestCreateCliente:
    def test_create_cliente_success(self, client, sample_cliente_payload):
        response = client.post("/client/create", json=sample_cliente_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == sample_cliente_payload["full_name"]
        assert data["tenant_id"] == sample_cliente_payload["tenant_id"]
        assert data["code"].startswith("CANT-")
        assert data["is_active"] is True
        assert "id" in data

    def test_create_cliente_unique_code(self, client, sample_cliente_payload):
        # Crea due clienti con lo stesso tenant
        r1 = client.post("/client/create", json=sample_cliente_payload)
        r2 = client.post("/client/create", json=sample_cliente_payload)

        assert r1.status_code == 201
        assert r2.status_code == 201
        code1 = r1.json()["code"]
        code2 = r2.json()["code"]
        # I codici devono essere univoci
        assert code1 != code2

    def test_create_cliente_validation_error(self, client):
        response = client.post("/client/create", json={"full_name": "", "tenant_id": ""})

        assert response.status_code == 422
        assert "detail" in response.json()


class TestClientLogin:
    def test_login_success(self, client, sample_cliente_payload):
        # Crea un cliente
        created = client.post("/client/create", json=sample_cliente_payload).json()
        code = created["code"]

        response = client.post("/client/login", json={"code": code})

        assert response.status_code == 200
        data = response.json()
        assert data["token"]
        assert data["cliente_id"] == created["id"]

    def test_login_invalid_code(self, client):
        response = client.post("/client/login", json={"code": "CANT-000000"})

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_inactive_cliente(self, client, sample_cliente_payload):
        # Crea un cliente e disattivalo
        created = client.post("/client/create", json=sample_cliente_payload).json()
        code = created["code"]

        # Disattiva il cliente direttamente nel DB (stesso event loop del TestClient)
        async def _deactivate():
            cliente = await Cliente.get(uuid.UUID(created["id"]))
            assert cliente is not None
            cliente.is_active = False
            await cliente.save()

        client.portal.call(_deactivate)

        response = client.post("/client/login", json={"code": code})

        assert response.status_code == 401


class TestAssignCantiere:
    def test_assign_cantiere_success(self, client, sample_cliente_payload, sample_tenant_id):
        # Crea cliente
        cliente = client.post("/client/create", json=sample_cliente_payload).json()

        # Crea cantiere con lo stesso tenant
        cantiere = _create_cantiere(sample_tenant_id)

        async def _save():
            await cantiere.insert()

        client.portal.call(_save)

        response = client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(cantiere.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"
        assert data["cantiere_id"] == str(cantiere.id)
        assert data["code"].startswith("CANT-")

    def test_assign_cantiere_cliente_not_found(self, client, sample_tenant_id):
        cantiere = _create_cantiere(sample_tenant_id)

        async def _save():
            await cantiere.insert()

        client.portal.call(_save)

        random_cliente_id = str(uuid.uuid4())
        response = client.post(
            "/client/assign-cantiere",
            json={"cliente_id": random_cliente_id, "cantiere_id": str(cantiere.id)},
        )

        assert response.status_code == 404

    def test_assign_cantiere_not_found(self, client, sample_cliente_payload):
        cliente = client.post("/client/create", json=sample_cliente_payload).json()

        response = client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(uuid.uuid4())},
        )

        assert response.status_code == 404

    def test_assign_cantiere_tenant_mismatch(
        self, client, sample_cliente_payload, sample_tenant_id
    ):
        cliente = client.post("/client/create", json=sample_cliente_payload).json()

        # Crea cantiere con tenant diverso
        other_tenant = str(uuid.uuid4())
        cantiere = _create_cantiere(other_tenant)

        async def _save():
            await cantiere.insert()

        client.portal.call(_save)

        response = client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(cantiere.id)},
        )

        assert response.status_code == 403


class TestGetCantieri:
    def test_get_cantieri_unauthorized(self, client):
        response = client.get("/client/cantieri")

        assert response.status_code == 401

    def test_get_cantieri_success(
        self, client, sample_cliente_payload, sample_tenant_id
    ):
        # Crea cliente
        cliente = client.post("/client/create", json=sample_cliente_payload).json()

        # Crea cantiere
        cantiere = _create_cantiere(sample_tenant_id)

        async def _save():
            await cantiere.insert()

        client.portal.call(_save)

        # Assegna cantiere al cliente
        client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(cantiere.id)},
        )

        # Login per ottenere token
        login = client.post("/client/login", json={"code": cliente["code"]}).json()
        token = login["token"]

        response = client.get(
            "/client/cantieri", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(cantiere.id)
        assert data[0]["title"] == "Cantiere Test"

    def test_get_cantieri_empty(self, client, sample_cliente_payload):
        # Crea cliente senza cantieri
        cliente = client.post("/client/create", json=sample_cliente_payload).json()

        login = client.post("/client/login", json={"code": cliente["code"]}).json()
        token = login["token"]

        response = client.get(
            "/client/cantieri", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json() == []


class TestAreaCantieri:
    """FASE 8: /cliente/area/cantieri (lista cantieri del cliente)."""

    def _setup_cliente_con_cantiere(self, client, sample_cliente_payload, sample_tenant_id):
        """Helper: crea cliente, cantiere, assegna, login. Ritorna token + cantiere."""
        cliente = client.post("/client/create", json=sample_cliente_payload).json()

        cantiere = _create_cantiere(sample_tenant_id)
        async def _save():
            await cantiere.insert()
        client.portal.call(_save)

        client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(cantiere.id)},
        )

        login = client.post("/client/login", json={"code": cliente["code"]}).json()
        token = login["token"]
        return token, cantiere

    def test_area_cantieri_unauthorized(self, client):
        response = client.get("/cliente/area/cantieri")
        assert response.status_code == 401

    def test_area_cantieri_success(
        self, client, sample_cliente_payload, sample_tenant_id
    ):
        token, cantiere = self._setup_cliente_con_cantiere(
            client, sample_cliente_payload, sample_tenant_id
        )
        response = client.get(
            "/cliente/area/cantieri", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(cantiere.id)
        assert data[0]["nome_cantiere"] == "Cantiere Test"
        assert data[0]["titolo"] == "Cantiere Test"
        assert data[0]["stato"] == "in_corso"
        assert data[0]["status"] == "in_corso"
        assert data[0]["percentuale_avanzamento"] == 0

    def test_area_cantieri_empty(self, client, sample_cliente_payload):
        cliente = client.post("/client/create", json=sample_cliente_payload).json()
        login = client.post("/client/login", json={"code": cliente["code"]}).json()
        token = login["token"]

        response = client.get(
            "/cliente/area/cantieri", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json() == []


class TestAreaAvanzamento:
    """FASE 8: /cliente/area/avanzamento (task + percentuale)."""

    def test_area_avanzamento_unauthorized(self, client):
        response = client.get("/cliente/area/avanzamento")
        assert response.status_code == 401

    def test_area_avanzamento_con_task(
        self, client, sample_cliente_payload, sample_tenant_id
    ):
        cliente = client.post("/client/create", json=sample_cliente_payload).json()
        cantiere = _create_cantiere(sample_tenant_id)
        async def _save_cantiere():
            await cantiere.insert()
        client.portal.call(_save_cantiere)

        client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(cantiere.id)},
        )

        # Crea task nel cantiere
        task = Task(
            cantiere_id=cantiere.id,
            organization_id=uuid.UUID(sample_tenant_id),
            title="Scavo",
            description="Scavo fondazioni",
            status="done",
            progress=100,
        )
        async def _save_task():
            await task.insert()
        client.portal.call(_save_task)

        login = client.post("/client/login", json={"code": cliente["code"]}).json()
        token = login["token"]

        response = client.get(
            "/cliente/area/avanzamento", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["progress_percentuale"] == 100
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Scavo"
        assert data["tasks"][0]["status"] == "done"
        assert data["tasks"][0]["completed"] is True


class TestAreaFoto:
    """FASE 8: /cliente/area/foto."""

    def test_area_foto_unauthorized(self, client):
        response = client.get("/cliente/area/foto")
        assert response.status_code == 401

    def test_area_foto_con_dati(
        self, client, sample_cliente_payload, sample_tenant_id
    ):
        cliente = client.post("/client/create", json=sample_cliente_payload).json()
        cantiere = _create_cantiere(sample_tenant_id)
        async def _save_cantiere():
            await cantiere.insert()
        client.portal.call(_save_cantiere)

        client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(cantiere.id)},
        )

        # Crea foto nel cantiere
        photo = ProgressPhoto(
            user_id=uuid.UUID(sample_tenant_id),
            organization_id=uuid.UUID(sample_tenant_id),
            cantiere_id=cantiere.id,
            stage="fondamenta",
            url="/uploads/foto1.jpg",
            description="Foto scavo",
        )
        async def _save_photo():
            await photo.insert()
        client.portal.call(_save_photo)

        login = client.post("/client/login", json={"code": cliente["code"]}).json()
        token = login["token"]

        response = client.get(
            "/cliente/area/foto", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "foto" in data
        assert len(data["foto"]) == 1
        assert data["foto"][0]["url"] == "/uploads/foto1.jpg"


class TestAreaPresenze:
    """FASE 8: /cliente/area/presenze."""

    def test_area_presenze_unauthorized(self, client):
        response = client.get("/cliente/area/presenze")
        assert response.status_code == 401

    def test_area_presenze_con_dati(
        self, client, sample_cliente_payload, sample_tenant_id
    ):
        cliente = client.post("/client/create", json=sample_cliente_payload).json()
        cantiere = _create_cantiere(sample_tenant_id)
        async def _save_cantiere():
            await cantiere.insert()
        client.portal.call(_save_cantiere)

        client.post(
            "/client/assign-cantiere",
            json={"cliente_id": cliente["id"], "cantiere_id": str(cantiere.id)},
        )

        # Crea presenza nel cantiere
        presence = Presence(
            user_id=uuid.UUID(sample_tenant_id),
            organization_id=uuid.UUID(sample_tenant_id),
            cantiere_id=cantiere.id,
            type="entrata",
            gps_lat=45.0,
            gps_lon=9.0,
        )
        async def _save_presence():
            await presence.insert()
        client.portal.call(_save_presence)

        login = client.post("/client/login", json={"code": cliente["code"]}).json()
        token = login["token"]

        response = client.get(
            "/cliente/area/presenze", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "presenze" in data
        assert len(data["presenze"]) == 1
        assert data["presenze"][0]["type"] == "entrata"
