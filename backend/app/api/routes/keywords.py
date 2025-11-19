from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import get_db
from app.api.schemas import KeywordStatSchema
from app.models import KeywordStat

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.get("/stats", response_model=List[KeywordStatSchema])
def keyword_stats(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> List[KeywordStatSchema]:
    statement = select(KeywordStat).order_by(KeywordStat.paper_count.desc()).limit(limit)
    result = db.exec(statement).all()
    return [
        KeywordStatSchema(
            keyword=item.keyword,
            paper_count=item.paper_count,
            last_seen_at=item.last_seen_at,
        )
        for item in result
    ]