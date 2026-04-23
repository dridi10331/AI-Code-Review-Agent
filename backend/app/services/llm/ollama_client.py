"""Ollama LLM client for free local code review."""

import httpx

from backend.app.core.config import Settings
from backend.app.models.review import ModelReview, ReviewerRole
from backend.app.services.llm.base import BaseReviewer, parse_model_response


class OllamaReviewer(BaseReviewer):
    """Reviewer using Ollama local models."""

    def __init__(self, settings: Settings, model_name: str) -> None:
        self.model_name = model_name
        self.base_url = settings.ollama_base_url
        self.timeout = settings.ollama_timeout

    async def review(self, prompt: str, role: ReviewerRole = "primary") -> ModelReview:
        """Send review request to Ollama and parse response."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.9,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                raw_text = data.get("response", "")
                return parse_model_response(
                    text=raw_text,
                    model_name=self.model_name,
                    role=role,
                    fallback_score=5.2,
                )

        except httpx.TimeoutException:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary=f"Ollama model {self.model_name} timed out.",
                findings=[],
                score=0.0,
                success=False,
                error="timeout",
            )
        except httpx.HTTPStatusError as e:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary=f"Ollama HTTP error: {e.response.status_code}",
                findings=[],
                score=0.0,
                success=False,
                error=f"http_{e.response.status_code}",
            )
        except Exception as e:
            return ModelReview(
                model_name=self.model_name,
                role=role,
                summary=f"Ollama error: {str(e)}",
                findings=[],
                score=0.0,
                success=False,
                error=str(e),
            )
