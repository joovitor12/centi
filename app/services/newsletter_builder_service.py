"""Generate newsletter content using Agno."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.agent.prompts import get_langfuse_client
from app.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class NewsletterDraft:
    """Generated newsletter payload."""

    title: str
    html_content: str
    text_content: str


class NewsletterBuilderService:
    """Build newsletter content from user themes."""

    def __init__(self) -> None:
        self._model_id = settings.AGNO_MODEL_ID
        self._langfuse = get_langfuse_client()
        self._newsletter_prompt = self._langfuse.get_prompt(
            "newsletters/build_newsletter/user", label="production"
        )

    def build_newsletter(
        self,
        title: str,
        themes: List[str],
        language: str = "pt-BR",
    ) -> NewsletterDraft:
        """Generate newsletter content using Agno with OpenAI backend."""
        try:
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat
            from agno.tools.duckduckgo import DuckDuckGoTools
        except ImportError as exc:
            raise RuntimeError(
                "Agno is not installed in this environment. Run `uv sync` first."
            ) from exc

        model = OpenAIChat(id=self._model_id, api_key=settings.OPENAI_API_KEY)
        agent = Agent(
            model=model,
            description="Newsletter content assistant",
            instructions=[
                "You generate engaging newsletters with practical depth.",
                "Use DuckDuckGo search/news tools to gather recent and relevant facts for each theme before writing.",
                "Prefer recent, factual information and avoid speculation.",
                "For each theme section, include concrete details (what happened, why it matters, practical implications).",
                "Do not say that there are no highlights if you can find relevant web sources.",
                "Include a final 'Sources' section with the links you actually used while researching.",
                "In html_content, sources must be clickable links (<a href='...'>...</a>).",
                "In text_content, sources must be plain URLs.",
                "Always return valid JSON only.",
                "The JSON keys must be: title, html_content, text_content.",
                "html_content must be safe and use simple tags only.",
                "text_content must be a plain text version of the newsletter.",
            ],
            tools=[DuckDuckGoTools(enable_search=True, enable_news=True)],
            add_datetime_to_context=True,
            markdown=False,
        )

        prompt = self._build_prompt(title=title, themes=themes, language=language)
        run_result = agent.run(prompt)
        payload = self._extract_payload(run_result)

        return NewsletterDraft(
            title=payload["title"],
            html_content=payload["html_content"],
            text_content=payload["text_content"],
        )

    def _build_prompt(self, title: str, themes: List[str], language: str) -> str:
        base_prompt = self._newsletter_prompt.compile(
            language=language,
            title=title,
            themes=", ".join(themes),
        )
        source_requirements = (
            "\n\nHard requirements:\n"
            "1) Write a richer newsletter, not a shallow summary.\n"
            "2) For each theme, include at least two concrete points grounded in web research.\n"
            "3) Add a final section named 'Sources' (or 'Fontes' in pt-BR).\n"
            "4) The Sources/Fontes section must include at least 3 distinct URLs used in your research.\n"
            "5) In html_content, render sources as clickable links.\n"
            "6) In text_content, include the same URLs in plain text.\n"
            "7) Output must remain valid JSON with exactly: title, html_content, text_content.\n"
        )
        return f"{base_prompt}{source_requirements}"

    def _extract_payload(self, run_result: Any) -> Dict[str, str]:
        """Handle Agno response object formats safely."""
        raw_output: Optional[str] = None

        # Common attributes depending on Agno version.
        for attr in ("content", "output", "response"):
            if hasattr(run_result, attr):
                candidate = getattr(run_result, attr)
                if isinstance(candidate, str) and candidate.strip():
                    raw_output = candidate
                    break

        if raw_output is None and isinstance(run_result, str):
            raw_output = run_result

        if raw_output is None:
            raise RuntimeError("Agno returned an empty response.")

        raw_output = raw_output.strip()
        if raw_output.startswith("```"):
            # Defensive cleanup if model wraps JSON in fences.
            raw_output = raw_output.strip("`")
            raw_output = raw_output.replace("json", "", 1).strip()

        try:
            payload: Dict[str, Any] = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            logger.error("Agno returned non-JSON payload: %s", raw_output)
            raise RuntimeError("Agno did not return valid JSON content.") from exc

        for key in ("title", "html_content", "text_content"):
            if not payload.get(key):
                raise RuntimeError(f"Agno response is missing required key: {key}")

        return {
            "title": str(payload["title"]),
            "html_content": str(payload["html_content"]),
            "text_content": str(payload["text_content"]),
        }
