from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class MetricSchema(BaseModel):
    name: str
    dataset: Optional[str] = None
    value: Optional[float | str] = None
    unit: Optional[str] = None
    baseline: Optional[float | str] = None
    delta: Optional[float | str] = None
    raw: Optional[str] = None


class FindingSchema(BaseModel):
    id: int
    claim_text: str
    experiment_design: Optional[str]
    evidence_snippet: Optional[str]
    metrics: List[MetricSchema] = []


class PaperSummarySchema(BaseModel):
    id: int
    arxiv_id: str
    title: str
    authors: List[str]
    institutions: List[str]
    published_at: Optional[datetime]
    hf_listing_date: Optional[str]
    abstract: Optional[str]
    problem_summary: Optional[str]
    solution_summary: Optional[str]
    effect_summary: Optional[str]
    keywords: List[str]
    breakthrough_score: Optional[float]
    breakthrough_label: Optional[bool]
    breakthrough_reason: Optional[str]
    findings: List[FindingSchema] = []


class KeywordStatSchema(BaseModel):
    keyword: str
    paper_count: int
    last_seen_at: datetime


class SubscriberCreateSchema(BaseModel):
    email: EmailStr


class SubscriberResponseSchema(BaseModel):
    email: EmailStr
    verified: bool
    created_at: datetime