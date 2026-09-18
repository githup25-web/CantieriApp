"""Test automatici per le rotte delle Presenze di cantiere (FASE 6)."""

from bson import ObjectId


def _checkin_payload(cantiere_id: str, worker_id: str) -> dict:
    return {
        "worker_id": worker_id,
        "cantiere_id": cantiere_id,
    }


def _checkout_payload(cantiere_id: str, worker_id: str) -> dict:
    return {
        "worker_id": worker_id,
        "cantiere_id": cantiere_id,
    }


class TestCheckin:
    def test_checkin_success(self, client, sample_cantiere_id, sample_worker_id):
        payload = _checkin_payload(sample_cantiere_id, sample_worker_id)
        response = client.post("/presenze/checkin", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["worker_id"] == sample_worker_id
        assert data["cantiere_id"] == sample_cantiere_id
        assert data["checkin"] is not None
        assert data["checkout"] is None

    def test_checkin_validation_error(self, client):
        response = client.post("/presenze/checkin", json={"worker_id": "", "cantiere_id": ""})

        assert response.status_code == 422
        assert "detail" in response.json()


class TestCheckout:
    def test_checkout_success(self, client, sample_cantiere_id, sample_worker_id):
        # Prima il check-in
        client.post(
            "/presenze/checkin",
            json=_checkin_payload(sample_cantiere_id, sample_worker_id),
        )

        # Poi il check-out
        response = client.post(
            "/presenze/checkout",
            json=_checkout_payload(sample_cantiere_id, sample_worker_id),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["worker_id"] == sample_worker_id
        assert data["cantiere_id"] == sample_cantiere_id
        assert data["checkin"] is not None
        assert data["checkout"] is not None

    def test_checkout_no_open_presence(self, client, sample_cantiere_id, sample_worker_id):
        response = client.post(
            "/presenze/checkout",
            json=_checkout_payload(sample_cantiere_id, sample_worker_id),
        )

        assert response.status_code == 404
        assert "detail" in response.json()


class TestListPresenzeByCantiere:
    def test_list_presenze_by_cantiere(self, client, sample_cantiere_id, sample_worker_id):
        # Crea 2 presenze per lo stesso cantiere
        client.post(
            "/presenze/checkin",
            json=_checkin_payload(sample_cantiere_id, sample_worker_id),
        )
        client.post(
            "/presenze/checkin",
            json=_checkin_payload(sample_cantiere_id, "worker_test_002"),
        )

        response = client.get(f"/presenze/by-cantiere/{sample_cantiere_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        workers = {item["worker_id"] for item in data}
        assert workers == {"worker_test_001", "worker_test_002"}

    def test_list_presenze_by_cantiere_empty(self, client, sample_cantiere_id):
        response = client.get(f"/presenze/by-cantiere/{sample_cantiere_id}")

        assert response.status_code == 200
        assert response.json() == []


class TestObjectIdSerialization:
    def test_presenza_id_is_valid_objectid(self, client, sample_cantiere_id, sample_worker_id):
        created = client.post(
            "/presenze/checkin",
            json=_checkin_payload(sample_cantiere_id, sample_worker_id),
        ).json()
        presenza_id = created.get("_id") or created.get("id")

        assert ObjectId.is_valid(presenza_id)
