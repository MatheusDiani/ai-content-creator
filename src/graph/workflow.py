"""LangGraph workflow definition for the content writer pipeline."""

import os
from typing import Literal

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from src.models.state import GraphState
from src.nodes.condenser import condenser_node
from src.nodes.prompt_builder import prompt_builder_node
from src.nodes.researchers.arxiv import arxiv_researcher_node
from src.nodes.researchers.duckduckgo import duckduckgo_researcher_node
from src.nodes.researchers.tavily import tavily_researcher_node
from src.nodes.reviewer import reviewer_node
from src.nodes.writer import writer_node
from src.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


def should_continue(state: GraphState) -> Literal["end", "improve"]:
    """Determine if the workflow should continue refining or end.

    Args:
        state: Current graph state.

    Returns:
        "end" if content is acceptable (nota > 7) or max iterations reached,
        "improve" if refinement should continue (nota <= 7).
    """
    score_threshold = int(os.getenv("MIN_SCORE_THRESHOLD", "7"))

    if state.nota_juiz is None:
        logger.warning("No score found, continuing to improve")
        return "improve"

    # Nota > 7 = aprovado, nota <= 7 = precisa refinar
    if state.nota_juiz > score_threshold:
        logger.info(
            f"Content approved with score {state.nota_juiz}/10 (threshold: >{score_threshold})"
        )
        return "end"

    max_iterations = int(os.getenv("MAX_ITERATIONS", "2"))
    if state.iteration >= max_iterations:
        logger.warning(
            f"Max iterations ({max_iterations}) reached, forcing end"
        )
        return "end"

    logger.info(
        f"Score {state.nota_juiz} <= {score_threshold}, improving (iteration {state.iteration})"
    )
    return "improve"


# Mapping of researcher names to their nodes
RESEARCHER_NODES = {
    "arxiv": ("arxiv_researcher", arxiv_researcher_node),
    "tavily": ("tavily_researcher", tavily_researcher_node),
    "duckduckgo": ("duckduckgo_researcher", duckduckgo_researcher_node),
}


def create_workflow(researchers: list[str] | None = None) -> StateGraph:
    """Create and compile the content writer workflow.

    Args:
        researchers: List of researcher names to use. 
                    Options: 'arxiv', 'tavily', 'duckduckgo'.
                    If None, uses all researchers.

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Default to all researchers if not specified
    if researchers is None:
        researchers = ["tavily", "duckduckgo", "arxiv"]
    
    # Filter to only valid researchers
    valid_researchers = [r for r in researchers if r in RESEARCHER_NODES]
    if not valid_researchers:
        valid_researchers = ["tavily"]  # Fallback to at least one
    
    logger.info(f"Creating workflow with researchers: {valid_researchers}")

    # Initialize the graph with our state
    workflow = StateGraph(GraphState)

    # Add researcher nodes dynamically
    researcher_node_names = []
    for researcher in valid_researchers:
        node_name, node_func = RESEARCHER_NODES[researcher]
        workflow.add_node(node_name, node_func)
        researcher_node_names.append(node_name)

    # Add other nodes
    workflow.add_node("condenser", condenser_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("prompt_builder", prompt_builder_node)

    # Set entry point to first researcher
    workflow.set_entry_point(researcher_node_names[0])

    # Connect all researchers to condenser
    for node_name in researcher_node_names:
        workflow.add_edge(node_name, "condenser")

    # Add parallel edges from START for additional researchers
    for node_name in researcher_node_names[1:]:
        workflow.add_edge("__start__", node_name)

    # Condenser → Writer → Reviewer
    workflow.add_edge("condenser", "writer")
    workflow.add_edge("writer", "reviewer")

    # Conditional edge: Reviewer decides next step
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "end": END,
            "improve": "prompt_builder",
        },
    )

    # Prompt Builder loops back to Writer
    workflow.add_edge("prompt_builder", "writer")

    # Compile the graph
    compiled = workflow.compile()
    logger.info("Workflow compiled successfully")

    return compiled


def run_workflow(topic: str, researchers: list[str] | None = None) -> GraphState:
    """Execute the content writer workflow for a given topic.

    Args:
        topic: The topic to generate content about.
        researchers: List of researcher names to use.

    Returns:
        Final GraphState with generated content.
    """
    logger.info(f"Running workflow for topic: {topic}")

    workflow = create_workflow(researchers)
    initial_state = GraphState(topic=topic)

    # Run the workflow
    final_state = workflow.invoke(initial_state)

    logger.info(
        f"Workflow complete: score={final_state.get('nota_juiz', 'N/A')}, "
        f"iterations={final_state.get('iteration', 0)}"
    )

    return GraphState(**final_state)


def stream_workflow(topic: str, researchers: list[str] | None = None):
    """Stream the workflow execution, yielding node names as they complete.

    Args:
        topic: The topic to generate content about.
        researchers: List of researcher names to use.

    Yields:
        Tuple of (node_name, state_update) for each completed node.
    """
    logger.info(f"Streaming workflow for topic: {topic}")

    workflow = create_workflow(researchers)
    initial_state = GraphState(topic=topic)

    final_state = None
    
    # Stream the workflow
    for event in workflow.stream(initial_state):
        for node_name, state_update in event.items():
            logger.info(f"Node completed: {node_name}")
            yield node_name, state_update
            final_state = state_update

    return final_state
