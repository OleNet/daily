"""
Unit tests for entities.py models.
"""
# test_models.py
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, create_engine, select

from app.models.entities import Paper, Finding, KeywordStat, Subscriber


@pytest.fixture(scope="session")
def engine(tmp_path_factory):
    # 使用基于文件的 SQLite，避免内存库在多个会话上下文中丢数据
    db_file = tmp_path_factory.mktemp("db") / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", echo=False)
    return engine


@pytest.fixture(autouse=True, scope="function")
def create_and_drop_tables(engine):
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def test_create_tables_and_crud(session: Session):
    # 插入一条 Paper
    paper = Paper(
        arxiv_id="1234.56789",
        title="A Test Paper for SQLModel",
        authors=["Alice", "Bob"],
        institutions=["MIT", "Stanford"],
        abstract="This is a test abstract.",
        keywords=["AI", "NLP"],
        breakthrough_score=0.95,
        breakthrough_label=True,
    )

    # 通过关系插入 Finding（反向设置 paper）
    finding = Finding(
        claim_text="This model achieves state-of-the-art results.",
        metrics=["accuracy", "f1-score"],
        paper=paper,
    )

    # 其他表
    keyword_stat = KeywordStat(keyword="AI", paper_count=1)
    subscriber = Subscriber(email="test@example.com", verified=True)

    session.add(paper)
    session.add(finding)
    session.add(keyword_stat)
    session.add(subscriber)
    session.commit()

    # 基本查询
    papers = session.exec(select(Paper)).all()
    assert len(papers) == 1
    p = papers[0]
    assert p.title == "A Test Paper for SQLModel"
    assert p.authors == ["Alice", "Bob"]       # JSON 列校验
    assert p.keywords == ["AI", "NLP"]
    assert isinstance(p.created_at, datetime)  # 时间戳默认值校验

    # 关系校验（Paper -> Findings）
    assert len(p.findings) == 1
    assert p.findings[0].claim_text.startswith("This model")

    # 关系校验（Finding -> Paper）
    f = session.exec(select(Finding)).first()
    assert f is not None and f.paper is not None
    assert f.paper.id == p.id

    # 其他表数据校验
    ks = session.exec(select(KeywordStat)).first()
    assert ks.keyword == "AI" and ks.paper_count == 1

    sub = session.exec(select(Subscriber)).first()
    assert sub.email == "test@example.com"
    assert sub.verified is True


def test_arxiv_id_unique_constraint(session: Session):
    p1 = Paper(
        arxiv_id="unique-0001",
        title="First",
        authors=[],
        institutions=[],
        keywords=[],
    )
    session.add(p1)
    session.commit()

    p2 = Paper(
        arxiv_id="unique-0001",  # 重复的 arxiv_id
        title="Second",
        authors=[],
        institutions=[],
        keywords=[],
    )
    session.add(p2)

    with pytest.raises(IntegrityError):
        session.commit()

    # 回滚后数据库仍只有第一条
    session.rollback()
    count = session.exec(select(Paper)).all()
    assert len(count) == 1