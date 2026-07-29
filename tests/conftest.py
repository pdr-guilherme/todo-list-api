import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from tests.factories import TokenFactory, UserFactory

SQLITE_TEST_URL = "sqlite://"
CONNECT_ARGS = {"check_same_thread": False}
engine = create_engine(SQLITE_TEST_URL, connect_args=CONNECT_ARGS, poolclass=StaticPool)

TestingSession = sessionmaker(engine)


@pytest.fixture(scope="function")
def test_db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


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


@pytest.fixture(autouse=True)
def setup_factories(test_db_session):
    UserFactory._meta.sqlalchemy_session = test_db_session
    TokenFactory._meta.sqlalchemy_session = test_db_session
