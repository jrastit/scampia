from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Boolean

from app.data.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_address = Column(String, unique=True, nullable=False, index=True)
    safe_address = Column(String, unique=True, nullable=True)
    network = Column(String, nullable=False, default="ethereum-sepolia")
    chain_id = Column(Integer, nullable=False, default=11155111)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    agent_active_transactions = Column(Integer, default=0)
    api_key = Column(String)