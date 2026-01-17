"""Review model for content evaluation."""

from pydantic import BaseModel, Field


class Review(BaseModel):
    """Model representing the review/critique of generated content.

    Attributes:
        score: Quality score from 1-10.
        clarity: Feedback on content clarity.
        tone: Feedback on tone of voice.
        errors: List of identified errors.
        suggestions: List of improvement suggestions.
    """

    score: int = Field(
        ge=1,
        le=10,
        description="Quality score from 1 (poor) to 10 (excellent)",
    )
    clarity: str = Field(
        description="Feedback on how clear and understandable the content is",
    )
    tone: str = Field(
        description="Feedback on the tone of voice and style",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of grammatical, factual, or structural errors found",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="List of actionable suggestions for improvement",
    )

    def is_acceptable(self, threshold: int = 7) -> bool:
        """Check if the review score meets the acceptance threshold.

        Args:
            threshold: Minimum acceptable score (default: 7).

        Returns:
            True if score >= threshold, False otherwise.
        """
        return self.score >= threshold

    def get_feedback_summary(self) -> str:
        """Generate a summary of all feedback for the prompt builder.

        Returns:
            Formatted string with all review feedback.
        """
        feedback_parts = [
            f"Score: {self.score}/10",
            f"Clarity: {self.clarity}",
            f"Tone: {self.tone}",
        ]

        if self.errors:
            feedback_parts.append(f"Errors: {'; '.join(self.errors)}")

        if self.suggestions:
            feedback_parts.append(f"Suggestions: {'; '.join(self.suggestions)}")

        return "\n".join(feedback_parts)
