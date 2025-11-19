#!/usr/bin/env python3
"""Debug script to check date formats in the database"""
import sys
sys.path.insert(0, '/Users/liujiaxiang/code/papers/backend')

from sqlmodel import Session, create_engine, select
from app.models import Paper

# Connect to database
engine = create_engine("sqlite:///backend/papers.db")

with Session(engine) as session:
    # Get some sample papers
    statement = select(Paper).limit(10)
    papers = session.exec(statement).all()
    
    print("=" * 80)
    print("Sample Paper Dates:")
    print("=" * 80)
    
    for paper in papers:
        print(f"\nPaper ID: {paper.id}")
        print(f"  Title: {paper.title[:50]}...")
        print(f"  published_at: {paper.published_at} (type: {type(paper.published_at)})")
        print(f"  hf_listing_date: {paper.hf_listing_date} (type: {type(paper.hf_listing_date)})")
        if paper.hf_listing_date:
            print(f"  hf_listing_date length: {len(str(paper.hf_listing_date))}")
    
    # Check available dates from calendar endpoint logic
    print("\n" + "=" * 80)
    print("Available Dates (calendar endpoint):")
    print("=" * 80)
    
    statement = (
        select(Paper.hf_listing_date)
        .where(Paper.hf_listing_date.is_not(None))
        .group_by(Paper.hf_listing_date)
        .order_by(Paper.hf_listing_date.desc())
    )
    results = session.exec(statement).all()
    
    for i, value in enumerate(results[:20]):
        text = value if isinstance(value, str) else str(value)
        normalized = text[:10]
        print(f"{i+1}. Raw: '{value}' -> Normalized: '{normalized}'")
