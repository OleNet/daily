"""Normalize paper.hf_listing_date to YYYY-MM-DD strings.

Run this once after updating the schema so Historical Explorer
uses the correct Hugging Face listing date.

Usage:
    python migrate_hf_listing_date.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from sqlmodel import Session, select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import engine  # noqa: E402
from app.models import Paper  # noqa: E402

console = Console()


def normalize(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # Already normalized
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return text
        try:
            parsed = datetime.fromisoformat(text.replace("Z", ""))
            return parsed.date().isoformat()
        except ValueError:
            pass
        # Fallback: take first 10 chars if they look like a date
        candidate = text[:10]
        if len(candidate) == 10 and candidate[4] == "-" and candidate[7] == "-":
            return candidate
        raise ValueError(f"Unrecognized date string: {text!r}")
    if isinstance(value, datetime):
        return value.date().isoformat()
    raise TypeError(f"Unsupported hf_listing_date type: {type(value)}")


def migrate() -> None:
    updated = 0
    skipped = 0
    with Session(engine) as session:
        papers = session.exec(select(Paper)).all()
        for paper in papers:
            try:
                normalized = normalize(paper.hf_listing_date)
            except (TypeError, ValueError) as exc:  # noqa: BLE001
                console.print(f"[red]Skipping {paper.arxiv_id}: {exc}")
                skipped += 1
                continue
            if normalized and paper.hf_listing_date != normalized:
                console.print(
                    f"[cyan]{paper.arxiv_id}[/cyan] {paper.hf_listing_date!r} -> {normalized}")
                paper.hf_listing_date = normalized
                updated += 1
        session.commit()
    console.print(f"[green]Migration complete. Updated {updated} papers; skipped {skipped}.")


if __name__ == "__main__":
    migrate()