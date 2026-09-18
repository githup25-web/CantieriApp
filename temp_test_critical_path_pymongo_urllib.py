import asyncio
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt

from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.models.cantiere import Cantiere
from app.models.expense import Expense
from app.models.event_queue import EventQueue
from app.models.event_record import EventRecord
from app.models.fattura import Fattura
from app.models.membership import Membership
from app.models.presence import Presence
from app.models.user import User


async def init_beanie_only_for_events() -> None:
    """
    This script does beanie initialization so we can query EventRecord/EventQueue
    without using pymongo directly.
    """
    from beanie import init_beanie

    settings = get_settings()
    await init_beanie(
        connection_string=f"{settings.mongo_uri}/{settings.mongo_db_name}",
        document_models=[
            User,
            Membership,
            Cantiere,
            Expense,
            Fattura,
            Presence,
            # event persistence/queue
            EventRecord,
            EventQueue,
        ],
    )


def _request(method: str, url: str, token: str | None, body: dict | None = None, content_type: str = "application/json"):
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers["Content-Type"] = content_type

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, method=method, headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8") if resp is not None else ""
            if resp_body:
                return resp.status, json.loads(resp_body)
            return resp.status, None
    except urllib.error.HTTPError as exc:
        raw = b""
        try:
            raw = exc.read() or b""
        except Exception:
            pass
        err_body = raw.decode("utf-8", errors="replace") if raw else ""
        try:
            parsed = json.loads(err_body) if err_body else None
        except Exception:
            parsed = None
        if parsed is None:
            parsed = {"__raw": err_body}
        return exc.code, parsed


async def _wait_for_event_record(event_name: str, predicate, *, timeout_s: float = 15.0, poll_s: float = 0.3):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        recs = await EventRecord.find(EventRecord.event_name == event_name).to_list()
        for r in recs:
            if predicate(r):
                return r
        await asyncio.sleep(poll_s)
    return None


async def _wait_for_queue_pending(event_instance_id: str, *, timeout_s: float = 15.0, poll_s: float = 0.3):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        item = await EventQueue.find_one(EventQueue.event_instance_id == event_instance_id)
        if item is not None and item.state == "pending":
            return item
        await asyncio.sleep(poll_s)
    return None


async def main():
    settings = get_settings()
    base_url = "http://127.0.0.1:8000"

    await connect_to_mongo()
    try:
        await init_beanie_only_for_events()

        # Cleanup only event collections for isolation
        await EventRecord.find_all().delete()
        await EventQueue.find_all().delete()

        org_uuid = uuid4()
        user_id = uuid4()
        cantiere_id = uuid4()

        # Seed auth + org checks
        user = User(
            id=user_id,
            email=f"cp_{uuid4()}@example.com",
            full_name="CriticalPathUser",
            is_active=True,
            is_superuser=False,
            organization_id=str(org_uuid),
            hashed_password="x",
            device_token=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await user.insert()

        membership = Membership(
            id=uuid4(),
            user_id=user_id,
            organization_id=org_uuid,
            role="worker",
        )
        await membership.insert()

        cantiere = Cantiere(
            id=cantiere_id,
            organization_id=org_uuid,
            title="CP Cantiere",
            description=None,
            assigned_worker_id=None,
            status="planned",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await cantiere.insert()

        # JWT creation (no app.core.security import)
        exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        token = jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        # 1) POST /fattura/create
        status_f, fattura_resp = _request(
            "POST",
            f"{base_url}/fattura/create",
            token,
            body={"cantiere_id": str(cantiere_id), "amount": 123.45},
        )
        if status_f not in (200, 201):
            raise AssertionError(f"fattura/create failed: {status_f} {fattura_resp}")
        fattura_id = fattura_resp["id"]

        # 2) POST /expense/create
        expense_form = {
            "category": "materials",
            "amount": "10.5",
            "description": "test expense",
            "cantiere_id": str(cantiere_id),
        }
        form_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/x-www-form-urlencoded"}
        expense_body = __import__("urllib.parse").parse.urlencode(expense_form).encode("utf-8")
        req = urllib.request.Request(
            url=f"{base_url}/expense/create",
            method="POST",
            headers=form_headers,
            data=expense_body,
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            exp_status = resp.status
            exp_text = resp.read().decode("utf-8")
        if exp_status not in (200, 201):
            raise AssertionError(f"expense/create failed: {exp_status} {exp_text}")
        expense_resp = json.loads(exp_text)
        expense_id = str(expense_resp["id"])

        # 3) POST /presence/clock-in
        status_p, presence_resp = _request(
            "POST",
            f"{base_url}/presence/clock-in",
            token,
            body={"cantiere_id": str(cantiere_id), "gps_lat": 45.0, "gps_lon": 9.0},
        )
        if status_p not in (200, 201):
            raise AssertionError(f"presence/clock-in failed: {status_p} {presence_resp}")
        presence_id = presence_resp["id"]

        # Validate fattura.created
        def pred_f(rec: EventRecord):
            d = (rec.payload or {}).get("data") or {}
            return str(d.get("fattura_id")) == str(fattura_id)

        r_f = await _wait_for_event_record("fattura.created", pred_f)
        assert r_f is not None, "Missing EventRecord for fattura.created"
        fiid = r_f.event_instance_id

        q_f = await _wait_for_queue_pending(fiid)
        assert q_f is not None, "Missing pending EventQueue for fattura.created"

        # Validate spesa.created
        def pred_e(rec: EventRecord):
            d = (rec.payload or {}).get("data") or {}
            return str(d.get("expense_id")) == str(expense_id)

        r_e = await _wait_for_event_record("spesa.created", pred_e)
        assert r_e is not None, "Missing EventRecord for spesa.created"
        eiid = r_e.event_instance_id

        q_e = await _wait_for_queue_pending(eiid)
        assert q_e is not None, "Missing pending EventQueue for spesa.created"

        # Validate presenza.created
        def pred_p(rec: EventRecord):
            d = (rec.payload or {}).get("data") or {}
            return str(d.get("presence_id")) == str(presence_id)

        r_p = await _wait_for_event_record("presenza.created", pred_p)
        assert r_p is not None, "Missing EventRecord for presenza.created"
        piid = r_p.event_instance_id

        q_p = await _wait_for_queue_pending(piid)
        assert q_p is not None, "Missing pending EventQueue for presenza.created"

        # Final assertions
        assert q_f.state == "pending"
        assert q_e.state == "pending"
        assert q_p.state == "pending"

        print("CRITICAL-PATH TEST (Motor/Beanie) : PASS")
        print("event_instance_ids:", {"fattura": fiid, "expense": eiid, "presence": piid})
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
