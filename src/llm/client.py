"""Hugging Face Inference API client."""

import os
import time
from typing import Optional

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from src.utils.env import get_secret
from src.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

# Modelos padrão
DEFAULT_MODEL = get_secret("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
JUDGE_MODEL = get_secret("JUDGE_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")


class LLMClient:
    """Client for interacting with Hugging Face Inference API.

    This client provides a simple interface for text generation using
    models hosted on Hugging Face's Inference API.

    Attributes:
        model_name: Name of the model to use.
        client: Hugging Face InferenceClient instance.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        is_judge: bool = False,
    ) -> None:
        """Initialize the LLM client.

        Args:
            model_name: Model to use. Defaults to env MODEL_NAME.
            api_key: HF API key. Defaults to env HUGGINGFACE_API_KEY.
            is_judge: If True, use the judge model (Qwen).
        """
        if is_judge:
            self.model_name = JUDGE_MODEL
        else:
            self.model_name = model_name or get_secret("MODEL_NAME", DEFAULT_MODEL)
        
        self._api_key = api_key or get_secret("HUGGINGFACE_API_KEY", "")

        if not self._api_key:
            logger.warning("HUGGINGFACE_API_KEY not set. API calls may fail.")

        self.client = InferenceClient(api_key=self._api_key)
        logger.info(f"LLMClient initialized with model: {self.model_name}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate text completion for the given prompt.

        Args:
            prompt: The user prompt to generate completion for.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0-1).
            system_prompt: Optional system prompt for context.

        Returns:
            Generated text response.

        Raises:
            Exception: If the API call fails.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        logger.info(f"Generating response for prompt ({len(prompt)} chars)")

        try:
            response = self.client.chat_completion(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content
            logger.info(f"Generated response ({len(content)} chars)")
            return content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate JSON-formatted text completion.

        Uses lower temperature for more deterministic JSON output.

        Args:
            prompt: The user prompt to generate completion for.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (default lower for JSON).
            system_prompt: Optional system prompt for context.

        Returns:
            Generated JSON text response.
        """
        json_system = (
            system_prompt or ""
        ) + "\n\nYou must respond ONLY with valid JSON. No markdown, no explanation."

        return self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=json_system.strip(),
        )
