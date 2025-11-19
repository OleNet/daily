from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
import re
from typing import List, Optional

import httpx
from selectolax.parser import HTMLParser

from app.core.config import settings

PAPER_HREF_PATTERN = re.compile(r"/papers/(?P<identifier>\d{4}\.\d{4,5})(?:v\d+)?")


class HuggingFaceDailyClient:
    def __init__(self) -> None:
        self.base_url = settings.hf_daily_url.rstrip("/") + "/"
        self.session = httpx.Client(
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
            proxy=None,  # Disable proxy
        )
        self.logger = logging.getLogger("hf")

    def fetch_identifiers(self, target_date: date) -> List[str]:
        url = f"{self.base_url}{target_date.isoformat()}"
        response = self.session.get(url)
        response.raise_for_status()
        final_url = str(response.request.url)
        if final_url.rstrip("/") != url.rstrip("/"):
            self.logger.info("Hugging Face redirected %s -> %s", url, final_url)
        parser = HTMLParser(response.text)
        identifiers: List[str] = []
        for node in parser.css("a"):
            href = node.attributes.get("href")
            if not href:
                continue
            match = PAPER_HREF_PATTERN.search(href)
            if match:
                identifiers.append(match.group("identifier"))
        return sorted(set(identifiers))

    def close(self) -> None:
        self.session.close()


def fetch_daily_identifiers(target_date: Optional[date] = None) -> List[str]:
    client = HuggingFaceDailyClient()
    try:
        if target_date is None:
            target_date = (datetime.utcnow() - timedelta(days=1)).date()
        try:
            return client.fetch_identifiers(target_date)
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network dependent
            if exc.response.status_code == 404:
                client.logger.warning(
                    "Hugging Face returned 404 for %s; no daily page available yet",
                    target_date.isoformat(),
                )
                return []
            raise
    finally:
        client.close()