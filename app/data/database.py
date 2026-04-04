from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./scampia.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import User  # noqa
    Base.metadata.create_all(bind=engine)

    # Lightweight migration for existing SQLite databases.
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        existing_columns = {row[1] for row in rows}
        if "vault_address" not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN vault_address VARCHAR"))