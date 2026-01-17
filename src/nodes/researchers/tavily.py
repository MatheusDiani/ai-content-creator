"""Tavily researcher node for web search optimized for LLMs."""

import os
from typing import Optional

from dotenv import load_dotenv
from tavily import TavilyClient

from src.llm import LLMClient
from src.models.content import ResearchSummary
from src.models.state import GraphState
from src.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

SUMMARIZE_PROMPT = """Summarize the following web search results into a concise paragraph
that captures the key insights relevant to the topic: "{topic}"

Search results:
{results}

Write a 2-3 paragraph summary in Portuguese (Brazilian) that synthesizes the main findings.
Focus on current trends, practical applications, and actionable insights.
"""


def tavily_researcher_node(state: GraphState) -> dict:
    """Search the web using Tavily API and generate a summary.

    Tavily is optimized for LLM-friendly results, providing clean
    and relevant content for AI applications.

    Args:
        state: Current graph state with the topic.

    Returns:
        Dictionary with updated research_summaries and status.
    """
    topic = state.topic
    logger.info(f"Tavily researcher searching for: {topic}")

    api_key = os.getenv("TAVILY_API_KEY", "")

    if not api_key:
        logger.error("TAVILY_API_KEY not set")
        return {
            "research_summaries": [
                ResearchSummary(
                    source="tavily",
                    content="Erro: TAVILY_API_KEY não configurada",
                    raw_results=[],
                )
            ],
            "status": "Tavily research failed - no API key",
        }

    try:
        client = TavilyClient(api_key=api_key)

        # Search with Tavily
        response = client.search(
            query=topic,
            search_depth="advanced",
            max_results=5,
        )

        results = []
        raw_results = []

        for result in response.get("results", []):
            title = result.get("title", "")
            content = result.get("content", "")
            results.append(f"Title: {title}\nContent: {content}")
            raw_results.append(title)

        if not results:
            logger.warning(f"No Tavily results found for: {topic}")
            summary_content = f"Nenhum resultado encontrado via Tavily para o tema: {topic}"
        else:
            # Generate summary using LLM
            llm = LLMClient()
            prompt = SUMMARIZE_PROMPT.format(
                topic=topic,
                results="\n\n---\n\n".join(results),
            )
            summary_content = llm.generate(prompt, max_tokens=512)

        research_summary = ResearchSummary(
            source="tavily",
            content=summary_content,
            raw_results=raw_results,
        )

        logger.info(f"Tavily research complete: {len(raw_results)} results found")

        return {
            "research_summaries": [research_summary],
            "status": "Tavily research complete",
        }

    except Exception as e:
        logger.error(f"Tavily research failed: {e}")
        return {
            "research_summaries": [
                ResearchSummary(
                    source="tavily",
                    content=f"Erro na pesquisa Tavily: {str(e)}",
                    raw_results=[],
                )
            ],
            "status": "Tavily research failed",
        }
