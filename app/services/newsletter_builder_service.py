"""Generate newsletter content using Agno."""

import json
import logging
import html
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

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

        source_urls = self._collect_source_urls(themes)
        prompt = self._build_prompt(
            title=title, themes=themes, language=language, source_urls=source_urls
        )
        run_result = agent.run(prompt)
        payload = self._extract_payload(run_result, source_urls=source_urls, language=language)

        return NewsletterDraft(
            title=payload["title"],
            html_content=payload["html_content"],
            text_content=payload["text_content"],
        )

    def _build_prompt(
        self, title: str, themes: List[str], language: str, source_urls: List[str]
    ) -> str:
        base_prompt = self._newsletter_prompt.compile(
            language=language,
            title=title,
            themes=", ".join(themes),
        )
        sources_block = (
            "Candidate sources gathered for this newsletter:\n"
            + "\n".join(f"- {url}" for url in source_urls)
            if source_urls
            else "No candidate sources were pre-fetched."
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
        return f"{base_prompt}\n\n{sources_block}{source_requirements}"

    def _extract_payload(
        self, run_result: Any, source_urls: List[str], language: str
    ) -> Dict[str, str]:
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

        html_content = str(payload["html_content"])
        text_content = str(payload["text_content"])
        has_link_in_html = "<a " in html_content and "href=" in html_content
        has_link_in_text = "http://" in text_content or "https://" in text_content

        if source_urls and (not has_link_in_html or not has_link_in_text):
            html_content, text_content = self._append_sources_section(
                html_content=html_content,
                text_content=text_content,
                source_urls=source_urls,
                language=language,
            )

        return {
            "title": str(payload["title"]),
            "html_content": html_content,
            "text_content": text_content,
        }

    def _collect_source_urls(self, themes: List[str]) -> List[str]:
        """Collect source URLs from DuckDuckGo before generation."""
        unique_urls: List[str] = []
        seen = set()

        try:
            from ddgs import DDGS
        except ImportError:
            logger.warning("ddgs not installed; skipping explicit source prefetch.")
            return unique_urls

        def _add_url(url: Optional[str]) -> None:
            if not url or not isinstance(url, str):
                return
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return
            normalized = url.strip()
            if normalized in seen:
                return
            seen.add(normalized)
            unique_urls.append(normalized)

        try:
            with DDGS() as ddgs:
                for theme in themes:
                    query = f"{theme} latest news"
                    for item in ddgs.news(query, max_results=3):
                        _add_url(item.get("url") or item.get("href"))
                    for item in ddgs.text(query, max_results=2):
                        _add_url(item.get("href") or item.get("url"))
                    if len(unique_urls) >= 8:
                        break
        except Exception as exc:
            logger.warning("Failed to prefetch newsletter sources: %s", exc)

        return unique_urls[:8]

    def _append_sources_section(
        self, html_content: str, text_content: str, source_urls: List[str], language: str
    ) -> tuple[str, str]:
        section_title = "Fontes" if language.lower().startswith("pt") else "Sources"
        html_links = "".join(
            f"<li><a href=\"{html.escape(url)}\" target=\"_blank\" rel=\"noopener noreferrer\">{html.escape(url)}</a></li>"
            for url in source_urls
        )
        html_section = f"<h2>{section_title}</h2><ul>{html_links}</ul>"
        text_section = f"{section_title}\n" + "\n".join(f"- {url}" for url in source_urls)

        merged_html = f"{html_content.rstrip()}\n{html_section}"
        merged_text = f"{text_content.rstrip()}\n\n{text_section}"
        return merged_html, merged_text
