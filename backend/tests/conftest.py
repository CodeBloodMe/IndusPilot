import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

