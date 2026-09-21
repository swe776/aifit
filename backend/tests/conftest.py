# Shared set up for the unit and integration tests
import pytest
import shutil
import os
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# A test secret key so the tests never need the real .env file
os.environ.setdefault("SECRET_KEY", "aifit-secret-key-1939939193129391391")

from backend.app.database import Base, get_database_session
from backend.app.main import app


# The tests use an empty database in memory so the real database is never touched
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestDatabaseSession = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)

def use_test_database():
    database = TestDatabaseSession()

    try:
        yield database
    finally:
        database.close()


# Make the app use the test database during the tests
app.dependency_overrides[get_database_session] = use_test_database


# A temporary folder inside the project that is deleted after each test
@pytest.fixture
def tmp_path():
    root = Path(__file__).resolve().parents[2] / ".aifit-temp-test"
    root.mkdir(exist_ok=True)
    path = root / f"case-{uuid.uuid4().hex}"
    path.mkdir(mode=0o777)
    try:
        yield path
    finally:
        shutil.rmtree(path)
        try:
            root.rmdir()
        except OSError:
            pass


# Every test starts with an empty database
@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.close()


# A session on the test database for tests that need to change a row directly
@pytest.fixture
def database():
    session = TestDatabaseSession()

    try:
        yield session
    finally:
        session.close()


# A logged in test user who has already accepted the privacy notice
@pytest.fixture
def account_headers(client):
    register_response = client.post(
        "/api/accounts/register",
        json={
            "email": "maya@gmail.com",
            "display_name": "Maya",
            "password": "password123",
        },
    )

    token = register_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    client.post(
        "/api/accounts/privacy-notice",
        headers=headers,
    )

    return headers
