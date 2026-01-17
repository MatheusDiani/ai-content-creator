"""Research nodes that gather information from different sources."""

from src.nodes.researchers.arxiv import arxiv_researcher_node
from src.nodes.researchers.duckduckgo import duckduckgo_researcher_node
from src.nodes.researchers.tavily import tavily_researcher_node

__all__ = [
    "arxiv_researcher_node",
    "tavily_researcher_node",
    "duckduckgo_researcher_node",
]
