"""Ligação à base de dados. Por omissão SQLite (zero configuração);
para PostgreSQL/PostGIS defina DATABASE_URL, ex.: postgresql+psycopg://user:pass@localhost/terrawatch"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./terrawatch.db")
_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import database.models  # noqa: F401  (regista as tabelas)
    Base.metadata.create_all(engine)
