import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.llm import DemoLLMService


@pytest.fixture
def client() -> TestClient:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_db():
        with TestingSession() as session:
            yield session

    original_admin_token = app.state.settings.admin_token
    original_rag_enabled = app.state.settings.rag_enabled
    app.state.settings.admin_token = "test-admin-token-12345"
    app.state.settings.rag_enabled = False
    app.dependency_overrides[get_db] = override_db
    app.state.llm = DemoLLMService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.state.settings.admin_token = original_admin_token
    app.state.settings.rag_enabled = original_rag_enabled
    if hasattr(app.state, "embedding_provider"):
        del app.state.embedding_provider

