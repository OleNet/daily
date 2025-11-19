# """
# Pytest configuration and shared fixtures for the entire test suite.
# """
# import sys
# from pathlib import Path

# import pytest
# from sqlalchemy import create_engine
# from sqlmodel import SQLModel
# from sqlalchemy import delete
# from sqlalchemy.orm import sessionmaker, Session


# # Add the app directory to Python path
# sys.path.insert(0, str(Path(__file__).parent.parent))


# @pytest.fixture(scope="session")
# def test_db_engine():
#     """Create a test database engine."""
#     # Use in-memory SQLite for tests
#     engine = create_engine("sqlite:///:memory:", echo=False)
#     SQLModel.metadata.create_all(engine)
#     yield engine
#     engine.dispose()


# @pytest.fixture(scope="function")
# def test_db_session(test_db_engine):
#     # 每个测试前确保表存在（如果你的 engine 是内存库也很必要）
#     SQLModel.metadata.create_all(test_db_engine)

#     TestingSessionLocal = sessionmaker(bind=test_db_engine, autoflush=False, autocommit=False, class_=Session)

#     with TestingSessionLocal() as session:
#         yield session
#         session.rollback()  # 以防未提交的事务

#     # 每个测试后清掉所有表结构（最干净）
#     SQLModel.metadata.drop_all(test_db_engine)