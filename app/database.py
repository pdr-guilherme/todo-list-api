from datetime import datetime

from sqlalchemy import DateTime, create_engine, event, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

SQLITE_URL = "sqlite:///task_.db"
CONNECT_ARGS = {"check_same_thread": False}
engine = create_engine(SQLITE_URL, connect_args=CONNECT_ARGS)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


Session = sessionmaker(engine)


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
