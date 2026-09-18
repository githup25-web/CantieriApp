from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.core.config import get_settings

settings = get_settings()

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Initialize MongoDB connection using Motor."""
    global client, db
    client = AsyncIOMotorClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=5000,
        maxPoolSize=10,
        uuidRepresentation="standard",
    )
    db = client[settings.database_name]
    # Verify connection
    await client.admin.command("ping")
    print(f"[DB] Connected to MongoDB: {settings.database_name}")


async def close_mongo_connection() -> None:
    """Close MongoDB connection gracefully."""
    global client
    if client is not None:
        client.close()
        client = None
        print("[DB] MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get the current database instance."""
    if db is None:
        raise RuntimeError(
            "Database not initialized. Call connect_to_mongo() first."
        )
    return db


def get_collection(collection_name: str):
    """Get a MongoDB collection from the current database."""
    database = get_database()
    return database[collection_name]


async def init_collections() -> None:
    """Create collections and indexes for the application."""
    database = get_database()

    # MongoDB create_index creates the collection if it doesn't exist.
    # Indexes are created with background=True to avoid blocking.

    # Users collection indexes
    await database.users.create_index("email", unique=True, background=True)
    await database.users.create_index("tenantId", background=True)

    # Tenants collection indexes
    await database.tenants.create_index("slug", unique=True, background=True)

    # FASE 6: tasks isolati per tenant e assegnatario.
    await database.tasks.create_index(
        [("tenantId", 1), ("assignedTo", 1), ("createdAt", -1)],
        background=True,
    )

    # FASE 6: una sola presenza giornaliera per utente e tenant.
    await database.presences.create_index(
        [("tenantId", 1), ("userId", 1), ("date", 1)],
        unique=True,
        partialFilterExpression={
            "tenantId": {"$exists": True},
            "userId": {"$exists": True},
            "date": {"$exists": True},
        },
        background=True,
    )

    # Expenses collection indexes
    await database.expenses.create_index(
        [("cantiereId", 1), ("tenantId", 1)], background=True
    )

    # FASE 6: foto di avanzamento legate a un task del tenant.
    await database.progress_photos.create_index(
        [("tenantId", 1), ("taskId", 1), ("createdAt", -1)],
        background=True,
    )

    # Invites collection indexes
    await database.invites.create_index([("email", 1), ("tenantId", 1)], background=True)
    await database.invites.create_index("token", unique=True, background=True)
    # RLS index: query invites by tenantId + status
    await database.invites.create_index(
        [("tenantId", 1), ("status", 1)], background=True
    )

    print("[DB] Collections and indexes verified")
