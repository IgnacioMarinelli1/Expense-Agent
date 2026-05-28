import os
import logging
import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI")
        if not uri:
            raise ValueError("MONGO_URI environment variable is not set.")
        uri = uri.strip().strip("'").strip('"')
        logger.info("Initializing MongoDB Motor client...")
        _client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where())
    return _client

def get_db() -> AsyncIOMotorDatabase:
    db_name = os.getenv("MONGO_DB_NAME", "expense_agent_db")
    return get_client()[db_name]

async def verify_connection() -> bool:
    try:
        await get_client().admin.command("ping")
        logger.info("Successfully connected to MongoDB!")
        return True
    except Exception as e:
        logger.error(f"MongoDB ping failed: {e}")
        return False

def close_connection():
    global _client
    if _client is not None:
        logger.info("Closing MongoDB connection...")
        _client.close()
        _client = None
