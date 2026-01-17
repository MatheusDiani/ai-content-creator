"""Prompt Builder node that improves the writer prompt based on review feedback."""

from src.llm import LLMClient
from src.models.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMPT_BUILDER_TEMPLATE = """You are an expert at crafting prompts for content generation.

The previous content generation attempt received the following feedback:

## Review Feedback:
Score: {score}/10
Clarity: {clarity}
Tone: {tone}
Errors: {errors}
Suggestions: {suggestions}

## Previous Prompt Used:
{previous_prompt}

## Original Topic:
{topic}

Your task is to create an IMPROVED prompt that addresses the feedback.
The new prompt should:
1. Be specific about fixing the identified errors
2. Incorporate the suggestions
3. Improve clarity and tone as needed
4. Keep the same basic structure but with enhanced instructions

Write the improved prompt template (use {{topic}} and {{summary}} as placeholders):
"""

DEFAULT_INITIAL_PROMPT = """You are an expert social media content writer.

Topic: {topic}

Research Summary:
{summary}

Your task is to write engaging social media content in Portuguese (Brazilian) based on this research.

Guidelines:
1. Write in a conversational, engaging tone
2. Use clear and accessible language
3. Include actionable insights or takeaways
4. Structure with short paragraphs for readability
5. Add relevant emojis sparingly for visual appeal
6. End with a call-to-action or thought-provoking question

Write the social media post:
"""


def prompt_builder_node(state: GraphState) -> dict:
    """Improve the writer prompt based on review feedback.

    This node analyzes the review feedback and creates an improved
    prompt template for the next writing iteration.

    Args:
        state: Current graph state with review feedback.

    Returns:
        Dictionary with improved current_prompt and updated status.
    """
    logger.info(f"Prompt builder improving prompt (iteration {state.iteration})")

    if state.review is None:
        logger.warning("No review available, using default prompt")
        return {
            "current_prompt": DEFAULT_INITIAL_PROMPT,
            "status": "Using default prompt",
        }

    previous_prompt = state.current_prompt or DEFAULT_INITIAL_PROMPT

    try:
        llm = LLMClient()
        prompt = PROMPT_BUILDER_TEMPLATE.format(
            score=state.review.score,
            clarity=state.review.clarity,
            tone=state.review.tone,
            errors="; ".join(state.review.errors) if state.review.errors else "None",
            suggestions="; ".join(state.review.suggestions) if state.review.suggestions else "None",
            previous_prompt=previous_prompt,
            topic=state.topic,
        )

        improved_prompt = llm.generate(prompt, max_tokens=1024, temperature=0.5)

        # Ensure placeholders are preserved
        if "{topic}" not in improved_prompt:
            improved_prompt = improved_prompt.replace("{{topic}}", "{topic}")
        if "{summary}" not in improved_prompt:
            improved_prompt = improved_prompt.replace("{{summary}}", "{summary}")

        logger.info(f"Improved prompt generated ({len(improved_prompt)} chars)")

        return {
            "current_prompt": improved_prompt,
            "status": "Prompt improved for next iteration",
        }

    except Exception as e:
        logger.error(f"Prompt builder failed: {e}")
        # Add feedback directly to the previous prompt as a workaround
        enhanced_prompt = f"""
{previous_prompt}

IMPORTANT IMPROVEMENTS NEEDED:
- {state.review.clarity}
- {state.review.tone}
- Address these errors: {'; '.join(state.review.errors)}
- Consider: {'; '.join(state.review.suggestions)}
"""
        return {
            "current_prompt": enhanced_prompt,
            "status": "Prompt enhanced with feedback (fallback)",
        }
