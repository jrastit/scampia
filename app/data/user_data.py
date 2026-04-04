from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_wallet(db: Session, wallet_address: str) -> Optional[User]:
    return db.query(User).filter(User.wallet_address == wallet_address.lower()).first()


def get_user_by_safe(db: Session, safe_address: str) -> Optional[User]:
    return db.query(User).filter(User.safe_address == safe_address.lower()).first()


def get_user_by_vault(db: Session, vault_address: str) -> Optional[User]:
    return db.query(User).filter(User.vault_address == vault_address.lower()).first()


def get_all_users(db: Session) -> list[User]:
    return db.query(User).all()


def create_user(
    db: Session,
    wallet_address: str,
    vault_address: str,
    network: str = "ethereum-sepolia",
    chain_id: int = 11155111,
) -> User:
    user = User(
        wallet_address=wallet_address.lower(),
        safe_address=vault_address.lower(),
        vault_address=vault_address.lower(),
        network=network,
        chain_id=chain_id,
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