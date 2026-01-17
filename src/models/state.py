"""Graph state model for LangGraph workflow."""

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from src.models.content import ResearchSummary
from src.models.review import Review


def merge_summaries(
    existing: list[ResearchSummary],
    new: list[ResearchSummary],
) -> list[ResearchSummary]:
    """Merge research summaries, avoiding duplicates by source.

    Args:
        existing: Current list of summaries.
        new: New summaries to add.

    Returns:
        Merged list of unique summaries.
    """
    existing_sources = {s.source for s in existing}
    merged = list(existing)
    for summary in new:
        if summary.source not in existing_sources:
            merged.append(summary)
            existing_sources.add(summary.source)
    return merged


def last_value(existing: str, new: str) -> str:
    """Keep the last value for status (handles parallel updates).

    Args:
        existing: Current status value.
        new: New status value.

    Returns:
        The new value (last wins).
    """
    return new


def merge_metrics(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge metrics dictionaries.

    Args:
        existing: Current metrics.
        new: New metrics to add.

    Returns:
        Merged metrics dictionary.
    """
    merged = dict(existing)
    merged.update(new)
    return merged


class GraphState(BaseModel):
    """Central state for the LangGraph workflow.

    This model tracks all data as it flows through the content generation
    pipeline, from initial topic to final reviewed content.

    Attributes:
        topic: The user's input topic/theme for content generation.
        research_summaries: Summaries from each research source.
        condensed_summary: Single condensed summary from all research.
        current_prompt: The current prompt template for the writer.
        draft: Current draft of the content.
        post_v1: First version of the post (before refinement).
        post_v2: Refined version of the post (if score <= 7).
        review: Latest review results (if any).
        nota_juiz: Extracted score from the judge (0-10).
        precisou_refinar: Whether the post needed refinement.
        iteration: Current iteration count.
        max_iterations: Maximum allowed iterations before forcing output.
        status: Current status message for UI updates.
        metrics: Metrics from each agent (tokens, latency).
    """

    topic: str = Field(description="User's input topic/theme")

    research_summaries: Annotated[
        list[ResearchSummary],
        merge_summaries,
    ] = Field(
        default_factory=list,
        description="Summaries from each research source",
    )

    condensed_summary: str = Field(
        default="",
        description="Condensed summary from all research",
    )

    current_prompt: str = Field(
        default="",
        description="Current prompt template for the writer node",
    )

    draft: str = Field(
        default="",
        description="Current draft of the content",
    )

    post_v1: str = Field(
        default="",
        description="First version of the post (before refinement)",
    )

    post_v2: Optional[str] = Field(
        default=None,
        description="Refined version of the post (if score <= 7)",
    )

    review: Optional[Review] = Field(
        default=None,
        description="Latest review results",
    )

    nota_juiz: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Extracted score from the judge (0-10)",
    )

    precisou_refinar: bool = Field(
        default=False,
        description="Whether the post needed refinement",
    )

    iteration: int = Field(
        default=0,
        ge=0,
        description="Current iteration count",
    )

    max_iterations: int = Field(
        default=3,
        ge=1,
        description="Maximum iterations before forcing output",
    )

    status: Annotated[str, last_value] = Field(
        default="initialized",
        description="Current status for UI updates",
    )

    metrics: Annotated[dict[str, Any], merge_metrics] = Field(
        default_factory=dict,
        description="Metrics from each agent (tokens, latency)",
    )

    def should_continue_refinement(self, score_threshold: int = 7) -> bool:
        """Determine if the workflow should continue refining.

        Args:
            score_threshold: Minimum acceptable score.

        Returns:
            True if refinement should continue, False otherwise.
        """
        if self.nota_juiz is None:
            return True

        if self.iteration >= self.max_iterations:
            return False

        return self.nota_juiz <= score_threshold

    def increment_iteration(self) -> "GraphState":
        """Return a new state with incremented iteration count.

        Returns:
            New GraphState with iteration incremented.
        """
        return self.model_copy(update={"iteration": self.iteration + 1})
