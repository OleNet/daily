from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional

import feedparser
import httpx
import fitz
from selectolax.parser import HTMLParser
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings
from app.services.types import ArxivPaper, Section

ARXIV_ABS_API = "https://export.arxiv.org/api/query?search_query=id:{}&max_results=1"
ARXIV_HTML_URL = "https://arxiv.org/html/{}"
ARXIV_PDF_URL = "https://arxiv.org/pdf/{}"


class ArxivFetchError(Exception):
    pass


class ArxivFetcher:
    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
            # proxy 参数留空，让 httpx 自动读取系统环境变量 HTTP_PROXY/HTTPS_PROXY
        )
        self.logger = logging.getLogger("arxiv_fetcher")

    def close(self) -> None:
        self.client.close()

    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    def _get(self, url: str) -> httpx.Response:
        response = self.client.get(url)
        response.raise_for_status()
        return response

    def fetch_metadata(self, arxiv_id: str) -> tuple[str, List[str], str, Optional[datetime], List[str]]:
        response = self._get(ARXIV_ABS_API.format(arxiv_id))
        feed = feedparser.parse(response.text)
        if not feed.entries:
            raise ArxivFetchError(f"No metadata found for {arxiv_id}")
        entry = feed.entries[0]
        title = entry.title.strip()
        authors = [author.name.strip() for author in entry.authors]
        summary = entry.summary.strip()
        categories = [tag.term for tag in entry.tags] if "tags" in entry else []
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
        return title, authors, summary, published, categories

    def fetch_html(self, arxiv_id: str) -> Optional[str]:
        url = ARXIV_HTML_URL.format(arxiv_id)
        response = self.client.get(url)
        if response.status_code == 200 and "<html" in response.text.lower():
            self.logger.info("Loaded HTML for %s (%s)", arxiv_id, url)
            self.logger.debug(
                "HTML content preview for %s: %s",
                arxiv_id,
                response.text[:2000],
            )
            return response.text
        self.logger.warning("HTML unavailable for %s (%s) status=%s", arxiv_id, url, response.status_code)
        return None

    def fetch_pdf_text(self, arxiv_id: str) -> str:
        url = ARXIV_PDF_URL.format(arxiv_id)
        response = self._get(url)
        doc = fitz.open(stream=response.content, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        if not text.strip():
            raise ArxivFetchError(f"Unable to extract text from PDF {arxiv_id}")
        self.logger.info("Extracted PDF text for %s (%s)", arxiv_id, url)
        self.logger.debug(
            "PDF text preview for %s: %s",
            arxiv_id,
            text[:2000],
        )
        return text

    @staticmethod
    def parse_sections_from_html(html: str) -> List[Section]:
        parser = HTMLParser(html)
        sections: List[Section] = []
        # arXiv HTML uses div.ltx_section containing headings and paragraphs
        for section in parser.css("div.ltx_section"):
            heading_node = section.css_first("h2, h3, h4, h5, h6")
            heading = heading_node.text(strip=True) if heading_node else ""
            paragraphs = [p.text(strip=True) for p in section.css("p") if p.text(strip=True)]
            content = "\n".join(paragraphs)
            if heading or content:
                sections.append(Section(heading=heading, content=content))
        if not sections:
            # fallback: grab paragraphs in body
            paragraphs = [p.text(strip=True) for p in parser.css("p") if p.text(strip=True)]
            if paragraphs:
                sections.append(Section(heading="Body", content="\n".join(paragraphs)))
        return sections

    def extract_institutions(self, html: Optional[str], authors: List[str]) -> List[str]:
        if not html:
            return []
        parser = HTMLParser(html)
        institutions: List[str] = []
        for node in parser.css("span.ltx_role_affiliation, span.ltx_affiliation"):  # best-effort match
            text = node.text(strip=True)
            if text:
                institutions.append(text)
        if institutions:
            return sorted(set(institutions))
        # fallback heuristic: search for parentheses after author names
        raw_text = parser.text(separator="\n")
        pattern = re.compile(r"\(([^)]+University[^)]*)\)")
        guesses = pattern.findall(raw_text)
        return sorted(set(guesses)) if guesses else []

    def fetch(self, arxiv_id: str) -> ArxivPaper:
        title, authors, summary, published, categories = self.fetch_metadata(arxiv_id)
        html = self.fetch_html(arxiv_id)
        sections: List[Section]
        raw_text: Optional[str] = None
        if html:
            sections = self.parse_sections_from_html(html)
            source = ARXIV_HTML_URL.format(arxiv_id)
        else:
            raw_text = self.fetch_pdf_text(arxiv_id)
            sections = [Section(heading="Extracted", content=raw_text)]
            source = ARXIV_PDF_URL.format(arxiv_id)

        institutions = self.extract_institutions(html, authors) if html else []
        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            institutions=institutions,
            abstract=summary,
            published_at=published,
            categories=categories,
            sections=sections,
            raw_html=html,
            raw_text=raw_text,
            source=source,
        )


def fetch_arxiv_paper(arxiv_id: str) -> ArxivPaper:
    fetcher = ArxivFetcher()
    try:
        return fetcher.fetch(arxiv_id)
    finally:
        fetcher.close()