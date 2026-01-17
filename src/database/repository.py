"""Content repository for MongoDB CRUD operations."""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo.collection import Collection

from src.database.connection import get_database
from src.models.content import ContentOutput, ResearchSummary
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ContentRepository:
    """Repository for managing content documents in MongoDB.

    Provides CRUD operations for storing and retrieving generated content.
    """

    COLLECTION_NAME = "contents"

    def __init__(self) -> None:
        """Initialize the repository with database connection."""
        self._db = get_database()
        self._collection: Collection = self._db[self.COLLECTION_NAME]
        logger.info(f"ContentRepository initialized with collection: {self.COLLECTION_NAME}")

    def save(self, content: ContentOutput) -> str:
        """Save a content document to the database.

        Args:
            content: ContentOutput model to save.

        Returns:
            String ID of the inserted document.
        """
        doc = content.to_mongo_dict()
        result = self._collection.insert_one(doc)
        doc_id = str(result.inserted_id)

        logger.info(f"Content saved with ID: {doc_id}")
        return doc_id

    def get_by_id(self, content_id: str) -> Optional[ContentOutput]:
        """Retrieve a content document by its ID.

        Args:
            content_id: String ID of the document.

        Returns:
            ContentOutput if found, None otherwise.
        """
        try:
            doc = self._collection.find_one({"_id": ObjectId(content_id)})
            if doc is None:
                return None

            return self._doc_to_model(doc)

        except Exception as e:
            logger.error(f"Failed to get content {content_id}: {e}")
            return None

    def get_history(self, limit: int = 10, skip: int = 0) -> list[ContentOutput]:
        """Retrieve content history, most recent first.

        Args:
            limit: Maximum number of documents to return.
            skip: Number of documents to skip (for pagination).

        Returns:
            List of ContentOutput models.
        """
        cursor = (
            self._collection.find()
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        contents = []
        for doc in cursor:
            try:
                contents.append(self._doc_to_model(doc))
            except Exception as e:
                logger.warning(f"Failed to parse document {doc.get('_id')}: {e}")

        logger.info(f"Retrieved {len(contents)} content documents")
        return contents

    def delete(self, content_id: str) -> bool:
        """Delete a content document by ID.

        Args:
            content_id: String ID of the document to delete.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            result = self._collection.delete_one({"_id": ObjectId(content_id)})
            deleted = result.deleted_count > 0

            if deleted:
                logger.info(f"Content {content_id} deleted")
            else:
                logger.warning(f"Content {content_id} not found for deletion")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete content {content_id}: {e}")
            return False

    def count(self) -> int:
        """Count total documents in the collection.

        Returns:
            Total document count.
        """
        return self._collection.count_documents({})

    def _doc_to_model(self, doc: dict) -> ContentOutput:
        """Convert a MongoDB document to ContentOutput model.

        Args:
            doc: MongoDB document dictionary.

        Returns:
            ContentOutput model instance.
        """
        # Parse research summaries
        research_summaries = [
            ResearchSummary(**rs) for rs in doc.get("research_summaries", [])
        ]

        # Parse created_at
        created_at = doc.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        return ContentOutput(
            topic=doc.get("topic", ""),
            final_content=doc.get("final_content", ""),
            condensed_summary=doc.get("condensed_summary", ""),
            research_summaries=research_summaries,
            iterations=doc.get("iterations", 1),
            final_score=doc.get("final_score", 5),
            created_at=created_at,
            mongo_id=str(doc.get("_id")),
        )
