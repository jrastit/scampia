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
        required_columns = {
            "vault_address": "ALTER TABLE users ADD COLUMN vault_address VARCHAR",
            "network": "ALTER TABLE users ADD COLUMN network VARCHAR NOT NULL DEFAULT 'ethereum-sepolia'",
            "chain_id": "ALTER TABLE users ADD COLUMN chain_id INTEGER NOT NULL DEFAULT 11155111",
            "is_active": "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1",
            "agent_active_transactions": "ALTER TABLE users ADD COLUMN agent_active_transactions INTEGER DEFAULT 0",
            "api_key": "ALTER TABLE users ADD COLUMN api_key VARCHAR",
        }

        for column_name, alter_sql in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(text(alter_sql))