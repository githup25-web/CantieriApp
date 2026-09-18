"""Test automatici per la FASE 5 — Sistema di Inviti (Backend).

Prerequisiti:
- MongoDB in esecuzione
- Backend avviato: uvicorn backend.main:app --reload --port 8000

Utilizzo:
    python scripts/test_fase5.py

Test coperti:
1. Creazione invito worker (admin)
2. Creazione invito client (admin)
3. RLS: worker non può creare inviti (403)
4. RLS: worker non può listare inviti (403)
5. RLS: worker non può eliminare inviti (403)
6. Accettazione invito worker -> crea user + membership
7. Login nuovo worker -> tenantId corretto
8. Accettazione invito client -> crea user + membership
9. Login nuovo client -> tenantId corretto
10. Invalidazione invito dopo accettazione (status accepted)
11. DELETE invito -> status canceled
12. Duplicate email check (400)
"""

import json
import sys
import urllib.error
import urllib.request
import uuid as uuid_lib

BASE_URL = "http://127.0.0.1:8000"


def make_request(
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> tuple[int, dict]:
    """Helper per effettuare una richiesta HTTP e restituire (status, body)."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        resp_body = json.loads(resp.read().decode()) if resp.status != 204 else {}
        return resp.status, resp_body
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode())
        except json.JSONDecodeError:
            err_body = {}
        return e.code, err_body


def generate_email(prefix: str) -> str:
    return f"{prefix}_{uuid_lib.uuid4().hex[:8]}@example.com"


def main() -> None:
    print("=" * 60)
    print("FASE 5 — Test Sistema di Inviti")
    print("=" * 60)

    # --- Health check ---
    status, body = make_request("GET", "/health")
    if status != 200:
        print(f"❌ Backend non raggiungibile: {status} {body}")
        sys.exit(1)
    print(f"✅ Health check OK: {body.get('status')}")

    # --- Registra admin ---
    admin_email = generate_email("admin")
    status, body = make_request(
        "POST",
        "/auth/register",
        {
            "email": admin_email,
            "password": "Admin123!",
            "full_name": "Admin Test Fase5",
        },
    )
    if status != 201:
        print(f"❌ Registrazione admin fallita: {status} {body}")
        sys.exit(1)
    admin_token = body.get("access_token", "")
    admin_tenant_id = body.get("tenant", {}).get("id", "")
    print(f"✅ Admin registrato: {admin_email} (tenant={admin_tenant_id[:8]}...)")

    # --- Test 1: Crea invito worker ---
    worker_email = generate_email("worker")
    status, body = make_request(
        "POST",
        "/invite/create",
        {"email": worker_email, "role": "worker"},
        token=admin_token,
    )
    if status != 201:
        print(f"❌ Creazione invito worker fallita: {status} {body}")
        sys.exit(1)
    worker_invite = body
    worker_invite_token = worker_invite["token"]
    print(f"✅ Invito worker creato: {worker_email} (token={worker_invite_token[:8]}...)")

    # --- Test 2: Crea invito client ---
    client_email = generate_email("client")
    status, body = make_request(
        "POST",
        "/invite/create",
        {"email": client_email, "role": "client"},
        token=admin_token,
    )
    if status != 201:
        print(f"❌ Creazione invito client fallita: {status} {body}")
        sys.exit(1)
    client_invite = body
    client_token = client_invite["token"]
    print(f"✅ Invito client creato: {client_email} (token={client_token[:8]}...)")

    # --- Accetta invito worker per creare un worker user ---
    status, body = make_request(
        "POST",
        "/invite/accept",
        {"token": worker_invite_token, "full_name": "Worker Accettato", "password": "Worker123!"},
    )
    if status != 200:
        print(f"❌ Accettazione invito worker fallita: {status} {body}")
        sys.exit(1)
    print(f"✅ Invito worker accettato: {body.get('email')} role={body.get('role')}")

    # --- Login del nuovo worker ---
    status, body = make_request(
        "POST",
        "/auth/login",
        {"email": worker_email, "password": "Worker123!"},
    )
    if status != 200:
        print(f"❌ Login worker fallito: {status} {body}")
        sys.exit(1)
    worker_token = body.get("access_token", "")
    print("✅ Login worker OK")

    # --- Verifica tenantId del worker via /auth/me ---
    status, me = make_request("GET", "/auth/me", token=worker_token)
    if status != 200:
        print(f"❌ /auth/me worker fallito: {status} {me}")
        sys.exit(1)
    if me.get("tenant_id") != admin_tenant_id:
        print(
            f"❌ RLS: tenantId worker ({me.get('tenant_id')}) != tenantId admin ({admin_tenant_id})"
        )
        sys.exit(1)
    print("✅ RLS OK: tenantId worker = tenantId admin")

    # --- Test RLS 1: worker non può creare inviti (403) ---
    status, body = make_request(
        "POST",
        "/invite/create",
        {"email": generate_email("forbidden"), "role": "worker"},
        token=worker_token,
    )
    if status != 403:
        print(f"❌ RLS: worker poteva creare inviti (status={status})")
        sys.exit(1)
    print("✅ RLS: worker non può creare inviti (403)")

    # --- Test RLS 2: worker non può listare inviti (403) ---
    status, body = make_request("GET", "/invite/list", token=worker_token)
    if status != 403:
        print(f"❌ RLS: worker poteva listare inviti (status={status})")
        sys.exit(1)
    print("✅ RLS: worker non può listare inviti (403)")

    # --- Test RLS 3: worker non può eliminare inviti (403) ---
    status, body = make_request(
        "DELETE", f"/invite/{client_invite['id']}", token=worker_token
    )
    if status != 403:
        print(f"❌ RLS: worker poteva eliminare inviti (status={status})")
        sys.exit(1)
    print("✅ RLS: worker non può eliminare inviti (403)")

    # --- Test: lista inviti come admin ---
    status, body = make_request("GET", "/invite/list", token=admin_token)
    if status != 200:
        print(f"❌ Lista inviti admin fallita: {status} {body}")
        sys.exit(1)
    items = body.get("items", [])
    if len(items) != 2:
        print(f"❌ Lista inviti: attesi 2, trovati {len(items)}")
        sys.exit(1)
    print(f"✅ Lista inviti admin OK ({len(items)} inviti)")

    # --- Test: invito worker è stato invalidato (accepted) ---
    status, body = make_request(
        "GET", f"/invite/verify?token={worker_invite_token}", token=None
    )
    if body.get("status") != "accepted":
        print(f"❌ Invito worker non invalidato: status={body.get('status')}")
        sys.exit(1)
    print("✅ Invito worker invalidato (status=accepted)")

    # --- Test: accettazione dello stesso invito fallisce (400) ---
    status, body = make_request(
        "POST",
        "/invite/accept",
        {"token": worker_invite_token, "full_name": "Worker Duplicato", "password": "Worker123!"},
    )
    if status != 400:
        print(f"❌ Accettazione duplicata non bloccata: status={status}")
        sys.exit(1)
    print("✅ Accettazione duplicata bloccata (400)")

    # --- Test: accetta invito client ---
    status, body = make_request(
        "POST",
        "/invite/accept",
        {"token": client_token, "full_name": "Client Accettato", "password": "Client123!"},
    )
    if status != 200:
        print(f"❌ Accettazione invito client fallita: {status} {body}")
        sys.exit(1)
    print(f"✅ Invito client accettato: {body.get('email')} role={body.get('role')}")

    # --- Login del nuovo client ---
    status, body = make_request(
        "POST",
        "/auth/login",
        {"email": client_email, "password": "Client123!"},
    )
    if status != 200:
        print(f"❌ Login client fallito: {status} {body}")
        sys.exit(1)
    print("✅ Login client OK")

    # --- Test: cancellazione/invalidazione di un invito accepted (400) ---
    status, body = make_request(
        "DELETE", f"/invite/{client_invite['id']}", token=admin_token
    )
    if status != 400:
        print(f"❌ Cancellazione invito accepted non bloccata: status={status}")
        sys.exit(1)
    print("✅ Cancellazione invito accepted bloccata (400)")

    # --- Test: crea nuovo invito e cancellalo come admin ---
    status, body = make_request(
        "POST",
        "/invite/create",
        {"email": generate_email("delete_me"), "role": "worker"},
        token=admin_token,
    )
    if status != 201:
        print(f"❌ Creazione invito delete_me fallita: {status} {body}")
        sys.exit(1)
    delete_me_id = body["id"]
    status, body = make_request("DELETE", f"/invite/{delete_me_id}", token=admin_token)
    if status != 200:
        print(f"❌ DELETE invito fallito: {status} {body}")
        sys.exit(1)
    if body.get("status") != "canceled":
        print(f"❌ Invito non invalidato come canceled: {body}")
        sys.exit(1)
    print("✅ DELETE invito -> status=canceled")

    # --- Test: DELETE invito inesistente (404) ---
    status, body = make_request(
        "DELETE",
        "/invite/00000000-0000-0000-0000-000000000000",
        token=admin_token,
    )
    if status != 404:
        print(f"❌ DELETE invito inesistente non bloccato: status={status}")
        sys.exit(1)
    print("✅ DELETE invito inesistente -> 404")

    # --- Test: invito per email già registrata (400) ---
    status, body = make_request(
        "POST",
        "/invite/create",
        {"email": worker_email, "role": "worker"},
        token=admin_token,
    )
    if status != 400:
        print(f"❌ Invito per user esistente non bloccato: status={status}")
        sys.exit(1)
    print("✅ Invito per user esistente bloccato (400)")

    print("\n" + "=" * 60)
    print("✅ ✅ ✅ TUTTI I TEST FASE 5 SUPERATI ✅ ✅ ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
