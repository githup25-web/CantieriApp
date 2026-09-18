"""Clean up test data from MongoDB for FASE 3 testing."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


async def clean():
    client = AsyncIOMotorClient(
        "mongodb://localhost:27017",
        uuidRepresentation="standard",
    )
    db = client["cantieriapp"]

    # Delete test users
    result_users = await db.users.delete_many({"email": {"$regex": "^test_"}})
    print(f"Deleted {result_users.deleted_count} test users")

    # Delete all tenants (they were created by tests)
    result_tenants = await db.tenants.delete_many({})
    print(f"Deleted {result_tenants.deleted_count} tenants")

    # Delete all memberships
    result_memberships = await db.memberships.delete_many({})
    print(f"Deleted {result_memberships.deleted_count} memberships")

    await client.close()
    print("Cleanup complete!")


if __name__ == "__main__":
    asyncio.run(clean())
