"""arXiv researcher node for academic paper search."""

import arxiv

from src.llm import LLMClient
from src.models.content import ResearchSummary
from src.models.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

SUMMARIZE_PROMPT = """Summarize the following academic paper information into a concise paragraph 
that captures the key insights relevant to the topic: "{topic}"

Papers found:
{papers}

Write a 2-3 paragraph summary in Portuguese (Brazilian) that synthesizes the main findings 
and concepts from these papers. Focus on practical applications and key takeaways.
"""


def arxiv_researcher_node(state: GraphState) -> dict:
    """Search arXiv for academic papers and generate a summary.

    This node searches arXiv for papers related to the topic and uses
    the LLM to generate a synthesized summary.

    Args:
        state: Current graph state with the topic.

    Returns:
        Dictionary with updated research_summaries and status.
    """
    topic = state.topic
    logger.info(f"arXiv researcher searching for: {topic}")

    try:
        # Search arXiv
        search = arxiv.Search(
            query=topic,
            max_results=3,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        papers = []
        raw_results = []

        for result in search.results():
            paper_info = f"Title: {result.title}\nSummary: {result.summary[:500]}..."
            papers.append(paper_info)
            raw_results.append(result.title)

        if not papers:
            logger.warning(f"No arXiv papers found for: {topic}")
            summary_content = f"Nenhum paper acadêmico encontrado no arXiv para o tema: {topic}"
        else:
            # Generate summary using LLM
            llm = LLMClient()
            prompt = SUMMARIZE_PROMPT.format(
                topic=topic,
                papers="\n\n---\n\n".join(papers),
            )
            summary_content = llm.generate(prompt, max_tokens=512)

        research_summary = ResearchSummary(
            source="arxiv",
            content=summary_content,
            raw_results=raw_results,
        )

        logger.info(f"arXiv research complete: {len(raw_results)} papers found")

        return {
            "research_summaries": [research_summary],
            "status": "arXiv research complete",
        }

    except Exception as e:
        logger.error(f"arXiv research failed: {e}")
        return {
            "research_summaries": [
                ResearchSummary(
                    source="arxiv",
                    content=f"Erro na pesquisa arXiv: {str(e)}",
                    raw_results=[],
                )
            ],
            "status": "arXiv research failed",
        }
