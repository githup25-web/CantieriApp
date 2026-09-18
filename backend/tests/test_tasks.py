"""Test automatici per le rotte dei Task di cantiere (FASE 6)."""

from bson import ObjectId


def _create_task_payload(cantiere_id: str, titolo: str = "Scavo fondazioni") -> dict:
    return {
        "cantiere_id": cantiere_id,
        "titolo": titolo,
        "descrizione": "Scavo e predisposizione fondazioni",
        "assegnato_a": "worker_test_001",
        "stato": "in_attesa",
    }


class TestCreateTask:
    def test_create_task_success(self, client, sample_cantiere_id):
        payload = _create_task_payload(sample_cantiere_id)
        response = client.post("/tasks/create", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["cantiere_id"] == sample_cantiere_id
        assert data["titolo"] == payload["titolo"]
        assert data["descrizione"] == payload["descrizione"]
        assert data["assegnato_a"] == payload["assegnato_a"]
        assert data["stato"] == "in_attesa"
        assert "_id" in data or "id" in data

    def test_create_task_validation_error(self, client):
        payload = {"cantiere_id": "", "titolo": "", "descrizione": "", "assegnato_a": ""}
        response = client.post("/tasks/create", json=payload)

        assert response.status_code == 422
        assert "detail" in response.json()


class TestListTasksByCantiere:
    def test_list_tasks_by_cantiere(self, client, sample_cantiere_id):
        # Crea 2 task per lo stesso cantiere
        client.post("/tasks/create", json=_create_task_payload(sample_cantiere_id, "Task A"))
        client.post("/tasks/create", json=_create_task_payload(sample_cantiere_id, "Task B"))

        response = client.get(f"/tasks/by-cantiere/{sample_cantiere_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {item["titolo"] for item in data}
        assert titles == {"Task A", "Task B"}

    def test_list_tasks_by_cantiere_empty(self, client, sample_cantiere_id):
        response = client.get(f"/tasks/by-cantiere/{sample_cantiere_id}")

        assert response.status_code == 200
        assert response.json() == []


class TestUpdateTask:
    def test_update_task_success(self, client, sample_cantiere_id):
        created = client.post(
            "/tasks/create", json=_create_task_payload(sample_cantiere_id)
        ).json()
        task_id = created.get("_id") or created.get("id")

        response = client.patch(
            f"/tasks/update/{task_id}",
            json={"stato": "in_corso", "titolo": "Scavo completato"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["stato"] == "in_corso"
        assert data["titolo"] == "Scavo completato"

    def test_update_task_not_found(self, client):
        response = client.patch(
            "/tasks/update/666f6f62617262617a000000",
            json={"stato": "completato"},
        )

        assert response.status_code == 404

    def test_update_task_invalid_id(self, client):
        response = client.patch(
            "/tasks/update/not-a-valid-objectid",
            json={"stato": "completato"},
        )

        assert response.status_code == 400


class TestObjectIdSerialization:
    def test_task_id_is_valid_objectid(self, client, sample_cantiere_id):
        created = client.post(
            "/tasks/create", json=_create_task_payload(sample_cantiere_id)
        ).json()
        task_id = created.get("_id") or created.get("id")

        assert ObjectId.is_valid(task_id)
