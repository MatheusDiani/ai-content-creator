"""Writer node that creates social media content from the condensed summary."""

from src.llm import LLMClient
from src.models.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

WRITER_PROMPT = """Você é um especialista em criar posts virais para LinkedIn.

Tema: {topic}

Resumo base:
{summary}

Crie um post para LinkedIn em português brasileiro seguindo estas regras:
1. Comece com um gancho que chame atenção
2. Use parágrafos curtos (1-2 frases cada)
3. Inclua insights práticos e acionáveis
4. Use emojis estrategicamente (não exagere)
5. Tom: profissional mas acessível
6. Não crie perguntas no final do post

IMPORTANTE: O post DEVE ter entre 150 e 200 palavras. NÃO ultrapasse 200 palavras. Seja conciso e direto.

Post para LinkedIn:"""


def writer_node(state: GraphState) -> dict:
    """Generate social media content from the condensed research summary.

    This node uses the condensed summary and current prompt to create
    engaging social media content.

    Args:
        state: Current graph state with condensed summary.

    Returns:
        Dictionary with draft, post_v1/v2, and updated status/iteration.
    """
    is_refinement = state.iteration > 0
    logger.info(
        f"Writer node generating content "
        f"(iteration {state.iteration + 1}, refinement={is_refinement})"
    )

    # Use custom prompt if available (from prompt_builder), otherwise use default
    prompt_template = state.current_prompt or WRITER_PROMPT

    try:
        llm = LLMClient()
        prompt = prompt_template.format(
            topic=state.topic,
            summary=state.condensed_summary,
        )

        draft = llm.generate(prompt, max_tokens=600, temperature=0.8)

        logger.info(f"Draft generated ({len(draft)} chars)")

        # Determine if this is V1 or V2
        result = {
            "draft": draft,
            "iteration": state.iteration + 1,
            "status": f"Draft generated (iteration {state.iteration + 1})",
        }

        # First iteration = post_v1, subsequent = post_v2
        if state.iteration == 0:
            result["post_v1"] = draft
            logger.info("Saved as post_v1")
        else:
            result["post_v2"] = draft
            logger.info("Saved as post_v2 (refined)")

        return result

    except Exception as e:
        logger.error(f"Writer failed: {e}")
        return {
            "draft": f"Error generating content: {str(e)}",
            "iteration": state.iteration + 1,
            "status": "Writer failed",
        }
