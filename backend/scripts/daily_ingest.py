from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Iterable, List

import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "daily_ingest.log"

from rich.console import Console
from rich.progress import Progress
from sqlmodel import select

from app.core.config import settings
from app.db.session import init_db, session_scope
from app.models import Finding, KeywordStat, Paper
from app.services.arxiv_fetcher import ArxivFetcher
from app.services.hf_client import fetch_daily_identifiers
from app.services.llm_client import analyze_paper_with_llm

console = Console()


def configure_logging(debug: bool = False) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("daily_ingest")
    if logger.handlers:
        level = logging.DEBUG if debug else logging.INFO
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)
        logging.getLogger("arxiv_fetcher").setLevel(level)
        logging.getLogger("llm").setLevel(level)
        return logger

    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    arxiv_logger = logging.getLogger("arxiv_fetcher")
    arxiv_logger.setLevel(level)
    arxiv_logger.addHandler(handler)
    arxiv_logger.propagate = False

    llm_logger = logging.getLogger("llm")
    llm_logger.setLevel(level)
    llm_logger.addHandler(handler)
    llm_logger.propagate = False
    return logger


logger = logging.getLogger("daily_ingest")


def ensure_storage_dirs(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)


def upsert_keywords(session, keywords: Iterable[str]) -> None:
    unique_keywords = {kw.strip().lower() for kw in keywords if kw}
    for keyword in unique_keywords:
        record = session.exec(
            select(KeywordStat).where(KeywordStat.keyword == keyword)
        ).first()
        if record:
            record.paper_count += 1
            record.last_seen_at = datetime.utcnow()
        else:
            session.add(KeywordStat(keyword=keyword, paper_count=1))


def ingest_paper(arxiv_id: str, fetcher: ArxivFetcher, listing_date: date) -> None:
    #import pdb
    #pdb.set_trace()
    with session_scope() as session:
        existing = session.exec(select(Paper).where(Paper.arxiv_id == arxiv_id)).first()
        if existing:
            console.print(f"[yellow]Skipping existing paper {arxiv_id}")
            logger.info("Skipping existing paper %s", arxiv_id)
            return

    paper_data = fetcher.fetch(arxiv_id)
    logger.info(
        "Fetched arXiv content for %s (%s) via %s",
        arxiv_id,
        paper_data.title,
        paper_data.source,
    )
    analysis = analyze_paper_with_llm(paper_data)
    logger.info(
        "LLM analysis complete for %s | breakthrough=%s score=%.3f",
        arxiv_id,
        analysis.breakthrough_label,
        analysis.breakthrough_score,
    )

    with session_scope() as session:
        db_paper = Paper(
            arxiv_id=paper_data.arxiv_id,
            title=paper_data.title,
            authors=paper_data.authors,
            institutions=paper_data.institutions,
            abstract=paper_data.abstract,
            source_url=f"https://huggingface.co/papers/{paper_data.arxiv_id}",
            published_at=paper_data.published_at,
            hf_listing_date=listing_date.isoformat(),
            html_source=paper_data.raw_html,
            problem_summary=analysis.problem,
            solution_summary=analysis.solution,
            effect_summary=analysis.effect,
            keywords=analysis.keywords,
            breakthrough_score=analysis.breakthrough_score,
            breakthrough_label=analysis.breakthrough_label,
            breakthrough_reason=analysis.breakthrough_reason,
            llm_model=settings.deepseek_model if settings.deepseek_api_key else None,
            updated_at=datetime.utcnow(),
        )
        session.add(db_paper)
        session.flush()

        for finding in analysis.findings:
            session.add(
                Finding(
                    paper_id=db_paper.id,
                    claim_text=finding.claim_text,
                    experiment_design=finding.experiment_design,
                    evidence_snippet=finding.evidence_snippet,
                    metrics=[metric.__dict__ for metric in finding.metrics],
                )
            )

        upsert_keywords(session, analysis.keywords)
        console.print(
            f"[green]Stored {arxiv_id} | breakthrough={'yes' if analysis.breakthrough_label else 'no'}"
        )
        logger.info("Stored paper %s with %d findings", arxiv_id, len(analysis.findings))


def run_ingest(limit: int | None = None, target_date: date | None = None, debug: bool = False) -> None:
    configure_logging(debug=debug)
    init_db()
    ensure_storage_dirs(Path("storage"))
    if target_date is None:
        target_date = (datetime.utcnow() - timedelta(days=1)).date()
    console.print(f"[cyan]Fetching Hugging Face daily list for {target_date.isoformat()}[/cyan]")
    logger.info("Starting ingest for %s", target_date.isoformat())
    identifiers = fetch_daily_identifiers(target_date)
    if limit:
        identifiers = identifiers[:limit]
    if not identifiers:
        console.print("[red]No papers found on Hugging Face daily page")
        logger.warning("No identifiers found for %s", target_date.isoformat())
        return

    fetcher = ArxivFetcher()
    try:
        with Progress() as progress:
            task = progress.add_task("Ingesting papers", total=len(identifiers))
            for arxiv_id in identifiers:
                try:
                    ingest_paper(arxiv_id, fetcher, listing_date=target_date)
                except Exception as exc:  # noqa: BLE001
                    console.print(f"[red]Failed to ingest {arxiv_id}: {exc}")
                    logger.exception("Failed to ingest %s", arxiv_id)
                finally:
                    progress.advance(task)
    finally:
        fetcher.close()
        logger.info("Completed ingest for %s", target_date.isoformat())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest arXiv papers from Hugging Face daily feed")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of papers")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date in YYYY-MM-DD (defaults to yesterday UTC)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args()
    target = None
    if args.date:
        try:
            target = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            parser.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
    run_ingest(limit=args.limit, target_date=target, debug=args.debug)