"""MongoDB connection management."""

import os
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

from src.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

_client: Optional[MongoClient] = None
_database: Optional[Database] = None


def get_database() -> Database:
    """Get the MongoDB database connection.

    Uses a singleton pattern to maintain a single connection.

    Returns:
        MongoDB database instance.

    Raises:
        ValueError: If MONGODB_URI is not configured.
    """
    global _client, _database

    if _database is not None:
        return _database

    uri = os.getenv("MONGODB_URI", "")
    db_name = os.getenv("MONGODB_DB_NAME", "content_writer")

    if not uri:
        logger.error("MONGODB_URI not configured")
        raise ValueError("MONGODB_URI environment variable is required")

    try:
        _client = MongoClient(uri)
        _database = _client[db_name]

        # Test connection
        _client.admin.command("ping")
        logger.info(f"Connected to MongoDB database: {db_name}")

        return _database

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


def close_connection() -> None:
    """Close the MongoDB connection."""
    global _client, _database

    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")
