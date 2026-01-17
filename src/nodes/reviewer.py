"""Reviewer (Judge) node that evaluates content quality using Qwen model."""

import re

from src.llm import LLMClient
from src.models.review import Review
from src.models.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

REVIEW_PROMPT = """Você é um especialista em viralização de conteúdo no LinkedIn.

Analise o post abaixo e avalie criticamente o que poderia ser melhorado para torná-lo mais viral e engajador. Não critique a falta de gifs, imagens, infográficos, etc. Não incentive criar perguntas no final do post.

POST ANALISADO:
{draft}

Forneça sua análise no seguinte formato:

NOTA GERAL: [0-10]

O QUE PODERIA MELHORAR:
- [liste sugestões específicas]
"""


def _extract_score(response: str) -> int:
    """Extract the first number from the response as the score.

    Args:
        response: Raw LLM response text.

    Returns:
        Extracted score (0-10), defaults to 5 if not found.
    """
    match = re.search(r'\d+', response)
    if match:
        score = int(match.group())
        return min(max(score, 0), 10)  # Clamp to 0-10
    return 5  # Default score if not found


def reviewer_node(state: GraphState) -> dict:
    """Evaluate the draft content and provide a structured review.

    This node acts as a judge, using Qwen model to analyze content
    for quality and provide a score and suggestions.

    Args:
        state: Current graph state with the draft.

    Returns:
        Dictionary with review, nota_juiz, precisou_refinar, and updated status.
    """
    logger.info(f"Reviewer node evaluating draft (iteration {state.iteration})")

    try:
        # Use Qwen model for judging
        llm = LLMClient(is_judge=True)
        prompt = REVIEW_PROMPT.format(draft=state.draft)

        response = llm.generate(
            prompt,
            max_tokens=800,
            system_prompt="Você é um revisor editorial especializado em viralização de conteúdo profissional.",
        )

        # Extract score via regex
        nota = _extract_score(response)
        precisou_refinar = nota <= 7

        logger.info(f"Review complete: nota={nota}/10, needs_refinement={precisou_refinar}")

        # Create Review object
        review = Review(
            score=nota,
            clarity=response,  # Store full response as clarity
            tone="Análise completa no campo clarity",
            errors=[],
            suggestions=[line.strip() for line in response.split('\n') if line.strip().startswith('-')],
        )

        return {
            "review": review,
            "nota_juiz": nota,
            "precisou_refinar": precisou_refinar,
            "status": f"Review complete: {nota}/10 - {'Needs refinement' if precisou_refinar else 'Approved!'}",
        }

    except Exception as e:
        logger.error(f"Reviewer failed: {e}")
        # Return a failing review to trigger retry
        return {
            "review": Review(
                score=5,
                clarity=f"Analysis error: {str(e)}",
                tone="Analysis not available",
                errors=["Automatic review failed"],
                suggestions=["Try again"],
            ),
            "nota_juiz": 5,
            "precisou_refinar": True,
            "status": "Review failed - retry suggested",
        }
