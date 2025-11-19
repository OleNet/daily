from __future__ import annotations

import json
import logging
from typing import List, Optional

from openai import OpenAI

from app.core.config import settings
from app.services.types import ArxivPaper, FindingSummary, LLMAnalysis, Metric

SYSTEM_PROMPT = """你是一位面向科研工作者的中文助手，负责阅读并总结最新的学术论文。务必按照给定的 JSON 结构输出结果，全程使用简体中文，保持准确、专业、凝练。"""

USER_PROMPT_TEMPLATE = """
论文元数据：
- arXiv ID：{arxiv_id}
- 标题：{title}
- 作者：{authors}
- 机构：{institutions}
- 摘要：{abstract}
- 分类标签：{categories}

正文片段（截取自 HTML/PDF）：
{sections}

任务要求（全部使用简体中文）：
1. 用 1-2 句话概述论文要解决的核心问题（problem 字段）。
2. 用 1-2 句话提炼论文提出的主要方案或方法（solution 字段）。
3. 描述论文的主要效果/成果，包含关键量化指标或相对提升（effect 字段，尽量列出数值）。
4. 至少整理 1 条核心结论（findings 数组）。每条需包含：
   - claim_text：一句话总结结论。
   - experiment_design：简述支撑该结论的实验设计（数据集/任务/设置）。
   - evidence_snippet：引用原文或描述中的关键句（可直接引用英文原句）。
   - metrics：列出相关量化指标，使用对象数组，字段包括 name/dataset/value/unit/baseline/delta/raw（缺失可置 null）。
5. 生成 5-8 个关键词（keywords 数组，全部小写，必要时可用连字符）。
6. 评估 breakthrough_score（0-1 之间的浮点数），参考因素：是否来自头部机构、是否提出全新方法、指标提升幅度、潜在影响力。
7. 当且仅当 breakthrough_score ≥ {threshold} 时将 breakthrough_label 设为 true。
8. 在 breakthrough_reason 中用不超过 30 个汉字解释判定理由。

返回 JSON 结构如下：
{{
  "problem": "……",
  "solution": "……",
  "effect": "……",
  "findings": [
    {{
      "claim_text": "……",
      "experiment_design": "……",
      "evidence_snippet": "……",
      "metrics": [
        {{
          "name": "…",
          "dataset": "…",
          "value": …,
          "unit": "…",
          "baseline": …,
          "delta": …,
          "raw": "原始描述"
        }}
      ]
    }}
  ],
  "keywords": ["…"],
  "breakthrough_score": 0.x,
  "breakthrough_label": true/false,
  "breakthrough_reason": "……"
}}
"""


def _format_sections(sections: List[str]) -> str:
    return "\n".join(sections)


def build_prompt(paper: ArxivPaper, context_sections: Optional[List[str]] = None) -> str:
    section_texts = []
    for section in paper.sections[:12]:  # keep prompt size manageable
        heading = f"[{section.heading}]" if section.heading else ""
        content = section.content.strip()
        if not content:
            continue
        section_texts.append(f"{heading}\n{content}")
    if not section_texts and paper.raw_text:
        section_texts.append(paper.raw_text[:5000])
    if context_sections:
        section_texts.extend(context_sections)
    return USER_PROMPT_TEMPLATE.format(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=", ".join(paper.authors),
        institutions=", ".join(paper.institutions) or "unknown",
        abstract=paper.abstract,
        categories=", ".join(paper.categories),
        sections=_format_sections(section_texts),
        threshold=settings.breakthrough_threshold,
    )


def _strip_code_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines:
            # drop opening fence
            lines = lines[1:]
        for idx, line in enumerate(lines):
            if line.strip().startswith("```"):
                lines = lines[:idx]
                break
        content = "\n".join(lines).strip()
    return content


logger = logging.getLogger("llm")


def call_deepseek(prompt: str) -> Optional[dict]:
    if not settings.deepseek_api_key:
        logger.warning("DeepSeek API key not configured; using heuristic fallback.")
        return None
    logger.debug("DeepSeek prompt: %s", prompt)
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    if not response or not response.choices:
        logger.error("DeepSeek returned no choices for prompt")
        return None
    content = response.choices[0].message.content or ""
    content = _strip_code_fence(content)
    logger.debug("DeepSeek raw response: %s", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.exception("Failed to decode DeepSeek JSON response: %s", content[:1000])
        return None


def parse_metrics(raw_metrics: List[dict]) -> List[Metric]:
    metrics: List[Metric] = []
    for item in raw_metrics:
        metrics.append(
            Metric(
                name=item.get("name", ""),
                dataset=item.get("dataset"),
                value=item.get("value"),
                unit=item.get("unit"),
                baseline=item.get("baseline"),
                delta=item.get("delta"),
                raw=item.get("raw"),
            )
        )
    return metrics


def parse_llm_analysis(payload: dict) -> LLMAnalysis:
    findings = []
    for raw in payload.get("findings", []):
        findings.append(
            FindingSummary(
                claim_text=raw.get("claim_text", ""),
                experiment_design=raw.get("experiment_design"),
                evidence_snippet=raw.get("evidence_snippet"),
                metrics=parse_metrics(raw.get("metrics", [])),
            )
        )
    return LLMAnalysis(
        problem=payload.get("problem", ""),
        solution=payload.get("solution", ""),
        effect=payload.get("effect", ""),
        keywords=[kw.lower() for kw in payload.get("keywords", [])],
        breakthrough_score=float(payload.get("breakthrough_score", 0.0)),
        breakthrough_label=bool(payload.get("breakthrough_label", False)),
        breakthrough_reason=payload.get("breakthrough_reason", ""),
        findings=findings,
    )


def heuristic_analysis(paper: ArxivPaper) -> LLMAnalysis:
    abstract = paper.abstract or ""
    first_section = paper.sections[0].content if paper.sections else paper.raw_text or ""
    problem = abstract.split(".")[0].strip() if abstract else first_section[:200]
    solution = abstract.split(".")[1].strip() if abstract and "." in abstract else "Review full paper for solution"
    effect = "Refer to experiments in the paper; automatic extraction unavailable"
    keywords = [cat.lower() for cat in paper.categories][:6]
    return LLMAnalysis(
        problem=problem,
        solution=solution,
        effect=effect,
        keywords=keywords,
        breakthrough_score=0.3,
        breakthrough_label=False,
        breakthrough_reason="Automated fallback: verify manually",
        findings=[],
    )


def analyze_paper_with_llm(paper: ArxivPaper, context_sections: Optional[List[str]] = None) -> LLMAnalysis:
    prompt = build_prompt(paper, context_sections)
    logger.info(
        "Invoking DeepSeek for arXiv %s with model %s (prompt length=%d chars)",
        paper.arxiv_id,
        settings.deepseek_model,
        len(prompt),
    )
    payload = call_deepseek(prompt)
    if payload:
        try:
            logger.debug(
                "DeepSeek payload for %s: %s",
                paper.arxiv_id,
                json.dumps(payload, ensure_ascii=False)[:2000],
            )
            return parse_llm_analysis(payload)
        except (ValueError, TypeError):
            logger.exception("Parsing DeepSeek payload failed; falling back to heuristic for %s", paper.arxiv_id)
            return heuristic_analysis(paper)
    logger.warning("DeepSeek call yielded no payload for %s; using heuristic analysis", paper.arxiv_id)
    return heuristic_analysis(paper)