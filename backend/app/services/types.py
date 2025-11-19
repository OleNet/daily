from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Section:
    heading: str
    content: str


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: List[str]
    institutions: List[str]
    abstract: str
    published_at: Optional[datetime]
    categories: List[str]
    sections: List[Section]
    raw_html: Optional[str]
    raw_text: Optional[str]
    source: str


@dataclass
class Metric:
    name: str
    dataset: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    baseline: Optional[float] = None
    delta: Optional[float] = None
    raw: Optional[str] = None


@dataclass
class FindingSummary:
    claim_text: str
    experiment_design: Optional[str]
    evidence_snippet: Optional[str]
    metrics: List[Metric]


@dataclass
class LLMAnalysis:
    problem: str
    solution: str
    effect: str
    keywords: List[str]
    breakthrough_score: float
    breakthrough_label: bool
    breakthrough_reason: str
    findings: List[FindingSummary]