import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base
from database.models import Company, User
from api.auth import create_user
from api.main import app, get_db

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture()
def db():
    Base.metadata.create_all(test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(test_engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Test-only authenticated principal.
    company = Company(name="Test Auth Company")
    db.add(company)
    db.commit()
    db.refresh(company)

    _, api_key = create_user(
        db,
        company_id=company.id,
        email="test@example.com",
        role="admin",
        api_key="test-api-key",
    )

    with TestClient(app) as test_client:
        test_client.headers.update({"X-API-Key": api_key})

        original_post = test_client.post

        def test_post(url, *args, **kwargs):
            response = original_post(url, *args, **kwargs)

            if url == "/v1/companies" and response.status_code == 200:
                company_id = response.json()["id"]
                test_user = db.query(User).filter(
                    User.api_key_hash == __import__(
                        "api.auth", fromlist=["hash_api_key"]
                    ).hash_api_key(api_key)
                ).one()
                test_user.company_id = company_id
                db.commit()

            return response

        test_client.post = test_post
        yield test_client

    app.dependency_overrides.clear()
