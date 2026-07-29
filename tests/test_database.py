import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine, get_db


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_get_db_yields_session():
    generator = get_db()
    db = next(generator)

    assert isinstance(db, Session)

    with pytest.raises(StopIteration):
        next(generator)
