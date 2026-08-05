import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app, limiter
from tests.factories import TaskFactory, TokenFactory, UserFactory

SQLITE_TEST_URL = "sqlite://"
CONNECT_ARGS = {"check_same_thread": False}
engine = create_engine(SQLITE_TEST_URL, connect_args=CONNECT_ARGS, poolclass=StaticPool)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSession = sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="function")
def test_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def setup_factories(test_db_session):
    UserFactory._meta.sqlalchemy_session = test_db_session  # type: ignore
    TokenFactory._meta.sqlalchemy_session = test_db_session  # type: ignore
    TaskFactory._meta.sqlalchemy_session = test_db_session  # type: ignore


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture(scope="function")
def client(test_db_session):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user(test_db_session):
    user = UserFactory()
    TokenFactory(user=user)
    test_db_session.commit()
    return user


@pytest.fixture
def authenticated_client(client, authenticated_user):
    client.headers.update({"Authorization": f"Bearer {authenticated_user.token.key}"})
    return client
