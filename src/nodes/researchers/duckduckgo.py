"""DuckDuckGo researcher node for general web search."""

from ddgs import DDGS

from src.llm import LLMClient
from src.models.content import ResearchSummary
from src.models.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

SUMMARIZE_PROMPT = """Summarize the following web search results into a concise paragraph
that captures the key insights relevant to the topic: "{topic}"

Search results:
{results}

Write a 2-3 paragraph summary in Portuguese (Brazilian) that synthesizes the main findings.
Focus on general knowledge, common perspectives, and widely-accepted information.
"""


def duckduckgo_researcher_node(state: GraphState) -> dict:
    """Search the web using DuckDuckGo and generate a summary.

    DuckDuckGo provides free, privacy-focused web search results
    without requiring an API key.

    Args:
        state: Current graph state with the topic.

    Returns:
        Dictionary with updated research_summaries and status.
    """
    topic = state.topic
    logger.info(f"DuckDuckGo researcher searching for: {topic}")

    try:
        # Search with DuckDuckGo
        # Search with DuckDuckGo
        with DDGS() as ddgs:
            search_results = list(ddgs.text(
                topic,
                region="br-pt",
                safesearch="moderate",
                max_results=3
            ))

        results = []
        raw_results = []

        for result in search_results:
            title = result.get("title", "")
            body = result.get("body", "")
            results.append(f"Title: {title}\nContent: {body}")
            raw_results.append(title)

        if not results:
            logger.warning(f"No DuckDuckGo results found for: {topic}")
            summary_content = (
                f"Nenhum resultado encontrado via DuckDuckGo para o tema: {topic}"
            )
        else:
            # Generate summary using LLM
            llm = LLMClient()
            prompt = SUMMARIZE_PROMPT.format(
                topic=topic,
                results="\n\n---\n\n".join(results),
            )
            summary_content = llm.generate(prompt, max_tokens=512)

        research_summary = ResearchSummary(
            source="duckduckgo",
            content=summary_content,
            raw_results=raw_results,
        )

        logger.info(f"DuckDuckGo research complete: {len(raw_results)} results found")

        return {
            "research_summaries": [research_summary],
            "status": "DuckDuckGo research complete",
        }

    except Exception as e:
        logger.error(f"DuckDuckGo research failed: {e}")
        return {
            "research_summaries": [
                ResearchSummary(
                    source="duckduckgo",
                    content=f"Erro na pesquisa DuckDuckGo: {str(e)}",
                    raw_results=[],
                )
            ],
            "status": "DuckDuckGo research failed",
        }
