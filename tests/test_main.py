import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_signup():
    response = client.post("/signup/", json={"phone": "1234567890"})
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "1234567890"
    assert data["email"] is None

def test_signup_duplicate_phone():
    client.post("/signup/", json={"phone": "1234567890"})
    response = client.post("/signup/", json={"phone": "1234567890"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Phone number already registered"

def test_update_email():
    response = client.post("/signup/", json={"phone": "1234567890"})
    user_id = response.json()["id"]
    response = client.put(f"/users/{user_id}/email/", json={"email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

def test_update_email_duplicate():
    client.post("/signup/", json={"phone": "1111111111"})
    user2_res = client.post("/signup/", json={"phone": "2222222222"})
    user2_id = user2_res.json()["id"]

    client.put(f"/users/{user2_id}/email/", json={"email": "test@example.com"})

    user1_res = client.post("/signup/", json={"phone": "3333333333"})
    user1_id = user1_res.json()["id"]

    response = client.put(f"/users/{user1_id}/email/", json={"email": "test@example.com"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already in use by another account"

def test_update_email_for_non_existing_user():
    response = client.put("/users/999/email/", json={"email": "test@example.com"})
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
