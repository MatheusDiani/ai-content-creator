"""Condenser node that combines multiple research summaries into one."""

from src.llm import LLMClient
from src.models.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

CONDENSE_PROMPT = """You are an expert at synthesizing information from multiple sources.

Topic: {topic}

You have received research summaries from 3 different sources:

## arXiv (Academic Papers):
{arxiv_summary}

## Tavily (Web Search):
{tavily_summary}

## DuckDuckGo (General Web):
{duckduckgo_summary}

Your task is to create a single, cohesive summary in Portuguese (Brazilian) that:
1. Combines the most relevant insights from all sources
2. Eliminates redundancies
3. Presents a balanced view (academic + practical + general)
4. Is structured for easy understanding
5. Has 3-4 paragraphs maximum

Write the condensed summary:
"""


def condenser_node(state: GraphState) -> dict:
    """Condense multiple research summaries into a single cohesive summary.

    This node takes all research summaries and combines them into one
    comprehensive summary that captures the essence of all sources.

    Args:
        state: Current graph state with research summaries.

    Returns:
        Dictionary with condensed_summary and updated status.
    """
    logger.info("Condenser node processing research summaries")

    summaries_by_source = {s.source: s.content for s in state.research_summaries}

    arxiv_summary = summaries_by_source.get(
        "arxiv", "Nenhuma informação acadêmica disponível."
    )
    tavily_summary = summaries_by_source.get(
        "tavily", "Nenhuma informação web (Tavily) disponível."
    )
    duckduckgo_summary = summaries_by_source.get(
        "duckduckgo", "Nenhuma informação web (DuckDuckGo) disponível."
    )

    try:
        llm = LLMClient()
        prompt = CONDENSE_PROMPT.format(
            topic=state.topic,
            arxiv_summary=arxiv_summary,
            tavily_summary=tavily_summary,
            duckduckgo_summary=duckduckgo_summary,
        )

        condensed_summary = llm.generate(prompt, max_tokens=768)

        logger.info(
            f"Condensed summary generated ({len(condensed_summary)} chars)"
        )

        return {
            "condensed_summary": condensed_summary,
            "status": "Research condensed",
        }

    except Exception as e:
        logger.error(f"Condenser failed: {e}")
        # Fallback: concatenate summaries
        fallback = f"""
## Resumo Acadêmico (arXiv):
{arxiv_summary}

## Resumo Web (Tavily):
{tavily_summary}

## Resumo Geral (DuckDuckGo):
{duckduckgo_summary}
"""
        return {
            "condensed_summary": fallback.strip(),
            "status": "Condenser fallback used",
        }
