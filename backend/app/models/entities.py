# from __future__ import annotations

# from typing import TYPE_CHECKING, List, Optional
# from sqlmodel import SQLModel, Session, create_engine, select
# from datetime import datetime
# from typing import TYPE_CHECKING, List, Optional
# from sqlalchemy import JSON, Column
# from sqlmodel import Field, Relationship

from sqlmodel import SQLModel, Session, create_engine, select
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship
# # from sqlalchemy.orm import Mapped
# from datetime import datetime
# from sqlmodel import Field, Relationship, SQLModel
# from sqlmodel import SQLModel


# if TYPE_CHECKING:
#     pass


class Paper(SQLModel, table=True):
    __tablename__ = "paper"

    id: Optional[int] = Field(default=None, primary_key=True)
    arxiv_id: str = Field(index=True, unique=True)
    title: str
    authors: List[str] = Field(sa_column=Column(JSON, nullable=False, default=[]))
    institutions: List[str] = Field(sa_column=Column(JSON, nullable=False, default=[]))
    abstract: Optional[str] = None
    source_url: Optional[str] = None
    published_at: Optional[datetime] = Field(default=None, index=True)
    hf_listing_date: Optional[str] = Field(default=None, index=True)
    html_source: Optional[str] = None
    pdf_source_path: Optional[str] = None
    problem_summary: Optional[str] = None
    solution_summary: Optional[str] = None
    effect_summary: Optional[str] = None
    keywords: List[str] = Field(sa_column=Column(JSON, nullable=False, default=[]))
    breakthrough_score: Optional[float] = Field(default=None, index=True)
    breakthrough_label: Optional[bool] = Field(default=False, index=True)
    breakthrough_reason: Optional[str] = None
    llm_model: Optional[str] = None
    llm_version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    findings: List["Finding"] = Relationship(back_populates="paper")


class Finding(SQLModel, table=True):
    __tablename__ = "finding"

    id: Optional[int] = Field(default=None, primary_key=True)
    paper_id: int = Field(foreign_key="paper.id", index=True)
    claim_text: str
    experiment_design: Optional[str] = None
    evidence_snippet: Optional[str] = None
    metrics: List[str] = Field(sa_column=Column(JSON, nullable=False, default=[]))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    paper: Optional[Paper] = Relationship(back_populates="findings")


class KeywordStat(SQLModel, table=True):
    __tablename__ = "keywordstat"

    id: Optional[int] = Field(default=None, primary_key=True)
    keyword: str = Field(index=True)
    paper_count: int = Field(default=0)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)


class Subscriber(SQLModel, table=True):
    __tablename__ = "subscriber"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = Field(default=False, index=True)
    verify_token: Optional[str] = Field(default=None, index=True)