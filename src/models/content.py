"""Content output model for the final generated content."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResearchSummary(BaseModel):
    """Model representing a research summary from a single source.

    Attributes:
        source: Name of the research source (arxiv, tavily, duckduckgo).
        content: The summarized content from this source.
        raw_results: Raw search results before summarization.
    """

    source: str = Field(description="Name of the research source")
    content: str = Field(description="Summarized content from this source")
    raw_results: list[str] = Field(
        default_factory=list,
        description="Raw search results before summarization",
    )


class ContentOutput(BaseModel):
    """Model representing the final output content.

    Attributes:
        topic: Original topic/theme requested.
        post_v1: First version of the post (always present).
        post_v2: Refined version (only if score <= 7).
        final_content: The best content (v2 if exists, else v1).
        condensed_summary: The condensed research summary.
        research_summaries: Individual summaries from each source.
        iterations: Number of refinement iterations taken.
        nota_juiz: Score from the judge (0-10).
        precisou_refinar: Whether refinement was needed.
        metrics: Metrics from each agent.
        created_at: Timestamp of creation.
        mongo_id: MongoDB document ID after saving.
    """

    topic: str = Field(description="Original topic/theme requested")
    
    post_v1: str = Field(
        default="",
        description="First version of the post",
    )
    
    post_v2: Optional[str] = Field(
        default=None,
        description="Refined version of the post (if score <= 7)",
    )
    
    final_content: str = Field(
        default="",
        description="The best content (v2 if exists, else v1)",
    )
    
    condensed_summary: str = Field(
        default="",
        description="The condensed research summary",
    )
    
    research_summaries: list[ResearchSummary] = Field(
        default_factory=list,
        description="Individual summaries from each research source",
    )
    
    iterations: int = Field(
        default=1,
        ge=1,
        description="Number of refinement iterations taken",
    )
    
    nota_juiz: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Score from the judge (0-10)",
    )
    
    precisou_refinar: bool = Field(
        default=False,
        description="Whether the post needed refinement",
    )
    
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Metrics from each agent (tokens, latency)",
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of content creation",
    )
    
    mongo_id: Optional[str] = Field(
        default=None,
        description="MongoDB document ID after saving",
    )

    def to_mongo_dict(self) -> dict:
        """Convert model to dictionary for MongoDB insertion.

        Returns:
            Dictionary representation for MongoDB.
        """
        data = self.model_dump(exclude={"mongo_id"})
        data["created_at"] = self.created_at.isoformat()
        return data
