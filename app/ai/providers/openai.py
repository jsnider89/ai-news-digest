"""OpenAI provider implementation."""
from __future__ import annotations

import logging
from typing import Tuple

import requests

from .base import AIProvider, ProviderError, require_env, normalise_usage, DEFAULT_SYSTEM_PROMPT
from ..pipeline import ProviderConfig

logger = logging.getLogger("market_aggregator.ai")


class OpenAIProvider(AIProvider):
    """OpenAI API provider supporting GPT models including reasoning models."""

    chat_endpoint = "https://api.openai.com/v1/chat/completions"
    responses_endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        api_key = require_env("OPENAI_API_KEY")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def name(self) -> str:
        return f"OpenAI {self.config.model}"

    def generate(
        self, prompt: str, *, system_prompt: str | None = None, verbosity: str | None = None
    ) -> Tuple[str, dict | None]:
        system_content = system_prompt or DEFAULT_SYSTEM_PROMPT

        # GPT-5 models use the responses endpoint with reasoning support
        if self.config.model.startswith("gpt-5"):
            effective_verbosity = verbosity or self.config.verbosity or "medium"
            payload = {
                "model": self.config.model,
                "input": [
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_content}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    },
                ],
                "max_output_tokens": 16000,
                "text": {
                    "verbosity": effective_verbosity,
                },
            }
            if self.config.reasoning_effort:
                payload["reasoning"] = {"effort": self.config.reasoning_effort}
            endpoint = self.responses_endpoint
            usage_keys = {
                "prompt_key": "input_tokens",
                "completion_key": "output_tokens",
                "total_key": "total_tokens",
            }
        else:
            # Standard chat completions for GPT-4 and earlier
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 8000,
                "temperature": 0.7,
                "top_p": 0.9,
            }
            endpoint = self.chat_endpoint
            usage_keys = {
                "prompt_key": "prompt_tokens",
                "completion_key": "completion_tokens",
                "total_key": "total_tokens",
            }

        try:
            # Reasoning models (gpt-5) can take much longer to respond
            timeout = 300 if self.config.model.startswith("gpt-5") else 120
            logger.debug("Posting to %s with model %s (timeout=%ds)", endpoint, self.config.model, timeout)
            response = self._session.post(endpoint, json=payload, timeout=timeout)

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as exc:
                detail: str
                try:
                    detail = response.text
                except Exception:  # pragma: no cover - defensive fallback
                    detail = "<failed to read error body>"
                logger.error("HTTP error from %s: %s - %s", endpoint, response.status_code, detail)
                raise ProviderError(self.name(), f"HTTP {response.status_code}: {detail}", exc) from exc

            body = response.json()

            # Parse response based on endpoint
            if endpoint == self.responses_endpoint:
                output = body.get("output") or []
                # Find the message object (not reasoning)
                message = next((item for item in output if isinstance(item, dict) and item.get("type") == "message"), {})
                content_blocks = message.get("content") or []
                text_parts = []
                for block in content_blocks:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type")
                    if block_type in {"output_text", "text"}:
                        text = block.get("text")
                        if isinstance(text, str):
                            text_parts.append(text)
                content = "".join(text_parts)
            else:
                content = (
                    body.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

            if not content or not content.strip():
                raise ProviderError(self.name(), "Empty response from OpenAI")

            usage = normalise_usage(body.get("usage", {}), **usage_keys)
            return content, usage

        except ProviderError:
            raise
        except requests.exceptions.RequestException as exc:  # pragma: no cover - network
            logger.error("Network error for %s: %s - %s", self.name(), type(exc).__name__, str(exc))
            raise ProviderError(self.name(), f"Network error: {type(exc).__name__}: {str(exc)}", exc) from exc
        except Exception as exc:  # pragma: no cover - unexpected
            raise ProviderError(self.name(), str(exc), exc) from exc

    def cleanup(self) -> None:  # pragma: no cover - trivial
        self._session.close()
