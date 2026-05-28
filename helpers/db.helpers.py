import logging
from pymongo.asynchronous.database import AsyncDatabase

# Initizalize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_create_collection(db: AsyncDatabase, collection_name: str, validator: dict):
    """
    Creates a collection with the given validator if it doesn't exist.
    """
    try:
        existing = await db.list_collection_names()
        if collection_name not in existing:
            await db.create_collection(collection_name, validator=validator)
            logger.info(f"Collection: '{collection_name}' created succesfully!")
    except Exception as e:
        logger.error(f"Error at trying to create collection '{collection_name}': {e}")
