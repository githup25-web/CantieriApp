import asyncio
from uuid import uuid4

import httpx
from beanie import init_beanie

from app.core.config import get_settings
from app.core.database import connect_to_mongo
from app.core.events import dispatcher
from app.core.security import create_access_token
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.user import User


async def seed():
    await connect_to_mongo()
    settings = get_settings()
    await init_beanie(
        connection_string=f"{settings.mongo_uri}/{settings.mongo_db_name}",
        document_models=[User, Membership, Notification],
    )

    # cleanup notifications/users/memberships for test emails (best effort)
    for email in ["nt_u1@example.com", "nt_u2@example.com", "nt_u3@example.com"]:
        u = await User.find_one(User.email == email)
        if u:
            await Notification.find(Notification.recipient_user_id == u.id).delete()
            await u.delete()

    await Membership.find_all().delete()
    await Notification.find_all().delete()

    org_uuid = uuid4()

    # User.organization_id is stored/typed as str | None in the backend => always store as string
    u1 = User(
        email="nt_u1@example.com",
        full_name="NT U1",
        hashed_password="x",
        organization_id=str(org_uuid),
        device_token="dummy_device_token",
    )
    u2 = User(
        email="nt_u2@example.com",
        full_name="NT U2",
        hashed_password="x",
        organization_id=str(org_uuid),
        device_token=None,
    )
    u3 = User(
        email="nt_u3@example.com",
        full_name="NT U3",
        hashed_password="x",
        organization_id=str(uuid4()),
        device_token=None,
    )

    await u1.insert()
    await u2.insert()
    await u3.insert()

    await Membership(user_id=u1.id, organization_id=org_uuid).insert()
    await Membership(user_id=u2.id, organization_id=org_uuid).insert()

    # Seed notifications
    n_org = Notification(
        recipient_user_id=u1.id,
        organization_id=org_uuid,
        type="preventivo.status_changed",
        entity_id=None,
        payload={"seed": True},
        is_read=False,
    )
    await n_org.insert()

    n_other = Notification(
        recipient_user_id=u3.id,
        organization_id=u3.id,  # unrelated org
        type="fattura.created",
        entity_id=None,
        payload={"seed": True},
        is_read=False,
    )
    await n_other.insert()

    return u1, u2, u3, n_org.id, org_uuid


async def run_tests():
    u1, u2, u3, notif_id, org_uuid = await seed()

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        token_u1 = create_access_token(str(u1.id))
        token_u2 = create_access_token(str(u2.id))
        token_u3 = create_access_token(str(u3.id))

        headers_u1 = {"Authorization": f"Bearer {token_u1}"}
        headers_u2 = {"Authorization": f"Bearer {token_u2}"}
        headers_u3 = {"Authorization": f"Bearer {token_u3}"}

        print("\n1) Beanie initialization (seed ok) - proceeding to API tests")

        print("\n0) Auth headers debug")
        print("u1 token head:", token_u1[:25] + "..." if token_u1 else None)
        print("headers_u1:", headers_u1)

        print("\n2) GET /notification/my (u1)")
        r = await client.get("/notification/my", headers=headers_u1)
        print("status:", r.status_code)
        try:
            print("body:", r.json())
        except Exception:
            print("body(text):", r.text)

        print("\n3) POST /notification/{id}/read (authorized u1)")
        try:
            r2 = await client.post(f"/notification/{notif_id}/read", headers=headers_u1)
            print("status:", r2.status_code)
            try:
                print("body:", r2.json())
            except Exception:
                print("body(text):", r2.text)
        except Exception as exc:
            print("POST read failed with exception:", repr(exc))
            return

        n = await Notification.get(notif_id)
        print("DB is_read:", getattr(n, "is_read", None))

        print("\n4) POST /notification/{id}/read (forbidden u2)")
        r3 = await client.post(f"/notification/{notif_id}/read", headers=headers_u2)
        print("status:", r3.status_code)
        try:
            print("body:", r3.json())
        except Exception:
            print("body(text):", r3.text)

        print("\n5) Event-driven creation: simulate dispatcher dispatch")
        before = len(await Notification.find_all().to_list())

        await dispatcher.dispatch(
            "preventivo.status_changed",
            {"organization_id": org_uuid, "recipient_user_id": u1.id, "entity_id": str(uuid4()), "data": {"k": "v"}},
        )
        await dispatcher.dispatch(
            "fattura.created",
            {"organization_id": org_uuid, "recipient_user_id": u2.id, "entity_id": str(uuid4()), "data": {"k": "v"}},
        )
        await dispatcher.dispatch(
            "task.assigned",
            {"organization_id": org_uuid, "recipient_user_id": u1.id, "entity_id": str(uuid4()), "data": {"k": "v"}},
        )
        await asyncio.sleep(0.2)

        after = len(await Notification.find_all().to_list())
        print("Notifications count before/after:", before, after)

        print("\n6) Push scheduling (best-effort, should not crash)")
        await dispatcher.dispatch(
            "preventivo.pdf_uploaded",
            {"organization_id": org_uuid, "recipient_user_id": u1.id, "entity_id": str(uuid4()), "data": {}},
        )
        print("Dispatched preventivo.pdf_uploaded.")

asyncio.run(run_tests())
