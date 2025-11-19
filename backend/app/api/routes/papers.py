from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_db
from app.api.schemas import FindingSchema, PaperSummarySchema
from app.models import Paper

router = APIRouter(tags=["papers"])


def serialize_paper(paper: Paper) -> PaperSummarySchema:
    return PaperSummarySchema(
        id=paper.id,
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=paper.authors,
        institutions=paper.institutions,
        published_at=paper.published_at,
        hf_listing_date=paper.hf_listing_date,
        abstract=paper.abstract,
        problem_summary=paper.problem_summary,
        solution_summary=paper.solution_summary,
        effect_summary=paper.effect_summary,
        keywords=paper.keywords,
        breakthrough_score=paper.breakthrough_score,
        breakthrough_label=paper.breakthrough_label,
        breakthrough_reason=paper.breakthrough_reason,
        findings=[
            FindingSchema(
                id=finding.id,
                claim_text=finding.claim_text,
                experiment_design=finding.experiment_design,
                evidence_snippet=finding.evidence_snippet,
                metrics=finding.metrics,
            )
            for finding in paper.findings
        ],
    )


@router.get("/papers/calendar", response_model=List[str])
def list_available_dates(db: Session = Depends(get_db)) -> List[str]:
    """获取所有有数据的日期列表 (必须在 /papers/{paper_id} 之前定义)"""
    statement = (
        select(Paper.hf_listing_date)
        .where(Paper.hf_listing_date.is_not(None))
        .group_by(Paper.hf_listing_date)
        .order_by(Paper.hf_listing_date.desc())
    )
    results = db.exec(statement).all()
    normalized: List[str] = []
    for value in results:
        if not value:
            continue
        text = value if isinstance(value, str) else str(value)
        # 确保返回标准的 YYYY-MM-DD 格式
        normalized.append(text[:10])
    # ensure unique while preserving order
    seen = set()
    deduped: List[str] = []
    for item in normalized:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


@router.get("/papers", response_model=List[PaperSummarySchema])
def list_papers(
    *,
    db: Session = Depends(get_db),
    target_date: Optional[str] = Query(None, description="Filter by ingest date (YYYY-MM-DD)"),
    breakthrough_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
) -> List[PaperSummarySchema]:
    statement = select(Paper).order_by(Paper.hf_listing_date.desc(), Paper.id.desc())
    if target_date:
        # 标准化日期格式,只取前10个字符 YYYY-MM-DD
        normalized_date = target_date[:10] if len(target_date) >= 10 else target_date
        statement = statement.where(Paper.hf_listing_date == normalized_date)
    if breakthrough_only:
        statement = statement.where(Paper.breakthrough_label.is_(True))
    papers = db.exec(statement.limit(limit)).all()
    return [serialize_paper(paper) for paper in papers]


@router.get("/papers/{paper_id}", response_model=PaperSummarySchema)
def get_paper(paper_id: int, db: Session = Depends(get_db)) -> PaperSummarySchema:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    # load findings relationship explicitly if lazy
    _ = paper.findings  # type: ignore[attr-defined]
    return serialize_paper(paper)