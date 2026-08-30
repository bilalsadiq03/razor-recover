from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.settings import config

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind = engine,
    autoflush=False,
    autocommit=False
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
