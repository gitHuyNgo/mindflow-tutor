#!/usr/bin/env python3
"""
Migration & Audit Tool for Legacy Sessions and OAuth Indexes.
- Enforces default-deny on legacy unowned sessions in MongoDB.
- Scans for sessions without a valid user_id and locks them to prevent hijacking.
- Creates TTL index on oauth_exchange_codes.
"""
import os
import sys
import argparse
import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration")


async def run_migration(assign_to_user_id: str = None, dry_run: bool = False):
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "mindflow")

    logger.info(f"Connecting to MongoDB at {mongo_url} (db: {db_name})...")
    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
    db = client[db_name]

    try:
        await db.command("ping")
        logger.info("MongoDB connection successful.")
    except Exception as e:
        logger.error(f"Cannot connect to MongoDB: {e}")
        return

    # 1. Audit unowned sessions
    unowned_query = {
        "$or": [
            {"user_id": None},
            {"user_id": ""},
            {"user_id": {"$exists": False}},
        ]
    }
    unowned_count = await db.conversations.count_documents(unowned_query)
    logger.info(f"Found {unowned_count} legacy unowned conversation sessions.")

    if unowned_count > 0:
        if dry_run:
            logger.info("[DRY RUN] No changes applied.")
        elif assign_to_user_id:
            logger.info(f"Migrating {unowned_count} sessions to user_id: '{assign_to_user_id}'...")
            res = await db.conversations.update_many(
                unowned_query,
                {
                    "$set": {
                        "user_id": assign_to_user_id,
                        "migrated_at": datetime.now(timezone.utc).isoformat(),
                        "migration_note": f"Assigned to {assign_to_user_id} via migration script",
                    }
                },
            )
            logger.info(f"Successfully reassigned {res.modified_count} sessions.")
        else:
            logger.info(f"Locking {unowned_count} unowned sessions (default-deny enforcement)...")
            res = await db.conversations.update_many(
                unowned_query,
                {
                    "$set": {
                        "is_legacy_unowned": True,
                        "locked": True,
                        "migrated_at": datetime.now(timezone.utc).isoformat(),
                        "migration_note": "Locked: unowned legacy session",
                    }
                },
            )
            logger.info(f"Successfully locked {res.modified_count} unowned sessions.")

    # 2. Ensure Database Indexes
    logger.info("Ensuring database indexes...")
    if not dry_run:
        # Conversations index by user_id and updated_at
        await db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
        await db.conversations.create_index("session_id", unique=True)

        # OAuth exchange codes TTL index
        await db.oauth_exchange_codes.create_index("expires_at", expireAfterSeconds=0)
        await db.oauth_exchange_codes.create_index("code_hash", unique=True)

        # Documents index
        await db.documents.create_index([("user_id", 1), ("id", 1)])
        logger.info("Indexes successfully verified and created.")

    client.close()
    logger.info("Migration complete.")


def main():
    parser = argparse.ArgumentParser(description="Migrate legacy unowned sessions and setup indexes.")
    parser.add_argument("--assign-to", dest="assign_to", default=None, help="User ID to assign unowned sessions to")
    parser.add_argument("--dry-run", action="store_true", help="Audit without modifying database")
    args = parser.parse_args()

    asyncio.run(run_migration(assign_to_user_id=args.assign_to, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
