"""Test automatici per le rotte delle Foto di Avanzamento (FASE 6)."""

from bson import ObjectId


class TestUploadFoto:
    def test_upload_foto_success(self, client, sample_cantiere_id, sample_worker_id):
        files = {"file": ("progresso.jpg", b"fake-image-bytes", "image/jpeg")}
        data = {
            "cantiere_id": sample_cantiere_id,
            "worker_id": sample_worker_id,
            "descrizione": "Foto avanzamento scavo",
        }

        response = client.post("/foto/upload", data=data, files=files)

        assert response.status_code == 201
        result = response.json()
        assert result["cantiere_id"] == sample_cantiere_id
        assert result["worker_id"] == sample_worker_id
        assert result["descrizione"] == "Foto avanzamento scavo"
        assert result["url"].startswith("/uploads/foto/")
        assert result["timestamp"] is not None

    def test_upload_foto_without_file(self, client, sample_cantiere_id, sample_worker_id):
        data = {
            "cantiere_id": sample_cantiere_id,
            "worker_id": sample_worker_id,
        }

        response = client.post("/foto/upload", data=data)

        assert response.status_code == 422
        assert "detail" in response.json()


class TestListFotoByCantiere:
    def test_list_foto_by_cantiere(self, client, sample_cantiere_id, sample_worker_id):
        # Carica 2 foto per lo stesso cantiere
        for i in range(2):
            files = {"file": (f"foto_{i}.jpg", b"fake-image-bytes", "image/jpeg")}
            data = {
                "cantiere_id": sample_cantiere_id,
                "worker_id": sample_worker_id,
                "descrizione": f"Foto {i}",
            }
            client.post("/foto/upload", data=data, files=files)

        response = client.get(f"/foto/by-cantiere/{sample_cantiere_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        descrizioni = {item["descrizione"] for item in data}
        assert descrizioni == {"Foto 0", "Foto 1"}

    def test_list_foto_by_cantiere_empty(self, client, sample_cantiere_id):
        response = client.get(f"/foto/by-cantiere/{sample_cantiere_id}")

        assert response.status_code == 200
        assert response.json() == []


class TestObjectIdSerialization:
    def test_foto_id_is_valid_objectid(self, client, sample_cantiere_id, sample_worker_id):
        files = {"file": ("progresso.jpg", b"fake-image-bytes", "image/jpeg")}
        data = {
            "cantiere_id": sample_cantiere_id,
            "worker_id": sample_worker_id,
        }

        created = client.post("/foto/upload", data=data, files=files).json()
        foto_id = created.get("_id") or created.get("id")

        assert ObjectId.is_valid(foto_id)
