from fastapi import status
from sqlalchemy import func, select

from app.models.auth import Token, User
from tests import factories

VALID_SIGNUP_PAYLOAD = {
    "name": "Jane Doe",
    "email": "jane.doe@test.com",
    "password": "password123",
}


def test_register(client, test_db_session):
    response = client.post("/register", json=VALID_SIGNUP_PAYLOAD)
    assert response.status_code == status.HTTP_201_CREATED
    assert "token" in response.json()

    user_count = test_db_session.scalar(select(func.count(User.id)))
    token_count = test_db_session.scalar(select(func.count(Token.key)))

    assert user_count == 1
    assert token_count == 1


def test_register_duplicate_email(client, test_db_session):
    response = client.post("/register", json=VALID_SIGNUP_PAYLOAD)
    assert response.status_code == status.HTTP_201_CREATED

    response2 = client.post("/register", json=VALID_SIGNUP_PAYLOAD)
    assert response2.status_code == status.HTTP_409_CONFLICT

    user_count = test_db_session.scalar(select(func.count(User.id)))
    assert user_count == 1


def test_register_rate_limit(client):
    for email in ["email1@test.com", "email2@test.com", "email3@test.com"]:
        data = VALID_SIGNUP_PAYLOAD | {"email": email}
        response = client.post("/register", json=data)
        assert response.status_code == status.HTTP_201_CREATED

    response = client.post("/register", json=VALID_SIGNUP_PAYLOAD)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_login(client):
    user = factories.UserFactory()
    factories.TokenFactory(user=user)
    data = {"email": user.email, "password": "defaultpassword123"}

    response = client.post("/login", json=data)
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert "token" in response_data


def test_login_wrong_email(client):
    data = {"email": "jane.doe@email.com", "password": "defaultpassword123"}

    response = client.post("/login", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_wrong_password(client):
    user = factories.UserFactory()
    data = {"email": user.email, "password": "password123"}

    response = client.post("/login", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_rate_limit(client):
    data = {"email": "temp@test.com", "password": "password123"}
    for _ in range(5):
        response = client.post("/login", json=data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = client.post("/login", json=data)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_me(client):
    user = factories.UserFactory()
    token = factories.TokenFactory(user=user)

    response = client.get("/me", headers={"Authorization": f"Bearer {token.key}"})
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data["id"] == user.id
    assert response_data["email"] == user.email
    assert response_data["name"] == user.name
    assert "password" not in response_data


def test_me_not_authenticated(client):
    response = client.get("/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_invalid_token(client):
    response = client.get("/me", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
