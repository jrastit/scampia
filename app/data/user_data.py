from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
import secrets

def generate_api_key():
    return secrets.token_hex(32)

def get_user_by_wallet(db: Session, wallet_address: str) -> Optional[User]:
    return db.query(User).filter(User.wallet_address == wallet_address.lower()).first()

def get_user_by_api_key(db: Session, api_key: str) -> Optional[User]:
    return db.query(User).filter(User.api_key == api_key).first()

def get_user_by_safe(db: Session, safe_address: str) -> Optional[User]:
    return db.query(User).filter(User.safe_address == safe_address.lower()).first()

def get_all_users(db: Session) -> list[User]:
    return db.query(User).all()

def decrement_active_transactions(db: Session, user_id: id):
    user = db.query(User).filter(User.id == user_id).first()
    user.agent_active_transactions -= 1

def increment_active_transactions(db: Session, user_id: id):
    user = db.query(User).filter(User.id == user_id).first()
    user.agent_active_transactions += 1

def create_user(
    db: Session,
    wallet_address: str,
    safe_address: str,
    network: str = "ethereum-sepolia",
    chain_id: int = 11155111,
) -> User:
    user = User(
        wallet_address=wallet_address.lower(),
        safe_address=safe_address.lower(),
        network=network,
        chain_id=chain_id,
        api_key=generate_api_key(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, wallet_address: str) -> Optional[User]:
    user = get_user_by_wallet(db, wallet_address)
    if user:
        user.is_active = False
        db.commit()
        db.refresh(user)
    return user