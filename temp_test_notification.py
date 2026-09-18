import asyncio
from fastapi.testclient import TestClient

import main as m
from app.core.config import get_settings
from app.core.database import connect_to_mongo
from app.core.security import create_access_token
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.user import User

from beanie import init_beanie


async def run():
    settings = get_settings()
    await connect_to_mongo()
    await init_beanie(
        connection_string=f"{settings.mongo_uri}/{settings.mongo_db_name}",
        document_models=[User, Membership, Notification],
    )

    # cleanup (best-effort)
    try:
        await Notification.find_all().delete()
    except Exception:
        pass
    try:
        await Membership.find_all().delete()
    except Exception:
        pass
    try:
        await User.find_all().delete()
    except Exception:
        pass

    # seed users
    u1 = User(email="u1@example.com", full_name="U1", hashed_password="x", organization_id=None)
    u2 = User(email="u2@example.com", full_name="U2", hashed_password="x", organization_id=None)
    await u1.insert()
    await u2.insert()

    # deterministic org: use u1.id
    # User.organization_id is typed as str | None in the backend, so store it as string.
    org_uuid = u1.id
    u1.organization_id = str(org_uuid)
    u2.organization_id = str(org_uuid)
    await u1.save()
    await u2.save()

    # seed memberships (Membership.organization_id is UUID)
    await Membership(user_id=u1.id, organization_id=org_uuid).insert()
    await Membership(user_id=u2.id, organization_id=org_uuid).insert()

    # seed notifications
    n1 = Notification(
        recipient_user_id=u1.id,
        organization_id=org_uuid,
        type="preventivo.status_changed",
        entity_id=u1.id,
        payload={"foo": "bar"},
        is_read=False,
    )
    await n1.insert()

    n2 = Notification(
        recipient_user_id=u2.id,
        organization_id=org_uuid,
        type="fattura.created",
        entity_id=u2.id,
        payload={"baz": "qux"},
        is_read=False,
    )
    await n2.insert()

    client = TestClient(m.app)

    token_u1 = create_access_token(str(u1.id))
    headers_u1 = {"Authorization": f"Bearer {token_u1}"}

    print("== GET /notification/my (u1) ==")
    resp = client.get("/notification/my", headers=headers_u1)
    print("status:", resp.status_code)
    print(resp.json())

    print("== POST /notification/{id}/read (authorized: u1 reads n1) ==")
    resp_read_ok = client.post(f"/notification/{n1.id}/read", headers=headers_u1)
    print("status:", resp_read_ok.status_code)
    print(resp_read_ok.json())

    print("== POST /notification/{id}/read (forbidden: u2 tries to read n1) ==")
    token_u2 = create_access_token(str(u2.id))
    headers_u2 = {"Authorization": f"Bearer {token_u2}"}
    resp_read_forbidden = client.post(f"/notification/{n1.id}/read", headers=headers_u2)
    print("status:", resp_read_forbidden.status_code)
    print(resp_read_forbidden.json())


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(run())
