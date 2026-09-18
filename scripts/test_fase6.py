"""Test end-to-end della FASE 6 per il backend Motor.

Prerequisiti:
    MongoDB in esecuzione
    uvicorn backend.main:app --reload --port 8000

Utilizzo:
    python scripts/test_fase6.py

Copertura:
    - creazione e assegnazione task
    - RLS task tra tenant diversi
    - check-in, check-out e presenza duplicata
    - upload foto collegata al task corretto
    - RLS foto
    - eliminazione task
"""

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

BASE_URL = os.getenv("CANTIERIAPP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def make_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, Any]:
    """Effettua una richiesta HTTP JSON e restituisce status e body."""

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 204:
                return response.status, {}
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw_body)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw_body}


def require_status(status: int, expected: int, label: str, body: Any) -> None:
    if status != expected:
        raise AssertionError(f"{label}: expected {expected}, got {status}: {body}")


def generate_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"


def register_admin(label: str) -> tuple[str, str]:
    email = generate_email(label)
    status, body = make_request(
        "POST",
        "/auth/register",
        {
            "email": email,
            "password": "Admin123!",
            "full_name": f"{label} admin",
        },
    )
    require_status(status, 201, f"register {label}", body)
    return body["access_token"], body["tenant"]["id"]


def create_worker(admin_token: str) -> tuple[str, str]:
    worker_email = generate_email("fase6_worker")
    status, invite = make_request(
        "POST",
        "/invite/create",
        {"email": worker_email, "role": "worker"},
        token=admin_token,
    )
    require_status(status, 201, "create worker invite", invite)

    status, accepted = make_request(
        "POST",
        "/invite/accept",
        {
            "token": invite["token"],
            "full_name": "Phase 6 worker",
            "password": "Worker123!",
        },
    )
    require_status(status, 200, "accept worker invite", accepted)

    status, login = make_request(
        "POST",
        "/auth/login",
        {"email": worker_email, "password": "Worker123!"},
    )
    require_status(status, 200, "worker login", login)
    worker_token = login["access_token"]

    status, me = make_request("GET", "/auth/me", token=worker_token)
    require_status(status, 200, "worker profile", me)
    return worker_token, me["id"]


def main() -> None:
    print("FASE 6 - Task, presenze e foto")

    status, health = make_request("GET", "/health")
    require_status(status, 200, "health check", health)

    admin_token, tenant_id = register_admin("fase6_tenant_a")
    worker_token, worker_id = create_worker(admin_token)
    print("PASS: bootstrap admin and worker")

    status, task = make_request(
        "POST",
        "/tasks/",
        {"title": "Installazione impianto", "description": "Completare il cablaggio"},
        token=admin_token,
    )
    require_status(status, 201, "create task", task)
    task_id = task["id"]
    if task["tenantId"] != tenant_id or task["assignedTo"] is not None:
        raise AssertionError(f"create task returned an invalid tenant or assignment: {task}")
    print("PASS: create task")

    status, task = make_request(
        "PATCH",
        f"/tasks/{task_id}",
        {"assignedTo": worker_id},
        token=admin_token,
    )
    require_status(status, 200, "assign task", task)
    if task["assignedTo"] != worker_id:
        raise AssertionError(f"task assignment was not persisted: {task}")
    print("PASS: assign task")

    status, worker_tasks = make_request("GET", "/tasks/", token=worker_token)
    require_status(status, 200, "worker task list", worker_tasks)
    if not any(item["id"] == task_id for item in worker_tasks):
        raise AssertionError(f"assigned task missing from worker list: {worker_tasks}")
    print("PASS: worker sees assigned task")

    status, denied_task = make_request(
        "POST",
        "/tasks/",
        {"title": "Forbidden", "description": "Worker must not create tasks"},
        token=worker_token,
    )
    require_status(status, 403, "worker task creation RLS", denied_task)

    other_admin_token, _ = register_admin("fase6_tenant_b")
    status, foreign_task = make_request(
        "GET", f"/tasks/{task_id}", token=other_admin_token
    )
    require_status(status, 404, "cross-tenant task RLS", foreign_task)
    print("PASS: task RLS")

    status, presence = make_request(
        "POST",
        "/presences/check-in",
        {"notes": "Arrival"},
        token=worker_token,
    )
    require_status(status, 201, "check-in", presence)
    if presence["userId"] != worker_id or presence["checkIn"] is None:
        raise AssertionError(f"check-in did not create the expected presence: {presence}")

    status, duplicate_presence = make_request(
        "POST",
        "/presences/check-in",
        {"notes": "Duplicate"},
        token=worker_token,
    )
    require_status(status, 409, "duplicate check-in", duplicate_presence)

    status, presence = make_request(
        "POST",
        "/presences/check-out",
        {"notes": "Departure"},
        token=worker_token,
    )
    require_status(status, 200, "check-out", presence)
    if presence["checkOut"] is None or presence["notes"] != "Departure":
        raise AssertionError(f"check-out did not close the presence: {presence}")
    print("PASS: check-in, duplicate protection and check-out")

    photo_url = "https://example.test/fase6/progress.jpg"
    status, photo = make_request(
        "POST",
        "/photos/",
        {"taskId": task_id, "url": photo_url},
        token=worker_token,
    )
    require_status(status, 201, "upload progress photo", photo)
    photo_id = photo["id"]
    if photo["taskId"] != task_id or photo["url"] != photo_url:
        raise AssertionError(f"photo is not linked to the expected task: {photo}")

    status, photos = make_request(
        "GET", f"/photos/task/{task_id}", token=worker_token
    )
    require_status(status, 200, "list task photos", photos)
    if not any(item["id"] == photo_id and item["taskId"] == task_id for item in photos):
        raise AssertionError(f"task photo is missing or linked incorrectly: {photos}")

    status, foreign_photo = make_request(
        "POST",
        "/photos/",
        {"taskId": task_id, "url": "https://example.test/fase6/forbidden.jpg"},
        token=other_admin_token,
    )
    require_status(status, 404, "cross-tenant photo RLS", foreign_photo)
    print("PASS: progress photo link and RLS")

    status, deleted = make_request("DELETE", f"/tasks/{task_id}", token=admin_token)
    require_status(status, 204, "delete task", deleted)

    status, missing_task = make_request("GET", f"/tasks/{task_id}", token=admin_token)
    require_status(status, 404, "deleted task lookup", missing_task)
    print("PASS: delete task")

    print("ALL FASE 6 TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError) as exc:
        print(f"FASE 6 TEST FAILED: {exc}", file=sys.stderr)
        sys.exit(1)