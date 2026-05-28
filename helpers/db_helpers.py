import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_create_collection(
    db: AsyncIOMotorDatabase,
    collection_name: str,
    validator: dict | None = None,
):
    try:
        existing = await db.list_collection_names()
        if collection_name not in existing:
            if validator:
                await db.create_collection(collection_name, validator=validator)
            else:
                await db.create_collection(collection_name)
            logger.info(f"Collection '{collection_name}' created successfully.")
    except Exception as e:
        logger.error(f"Error creating collection '{collection_name}': {e}")
