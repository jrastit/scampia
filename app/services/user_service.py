from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.data import user_data
from app.config import settings


class UserService:

    def __init__(self, vault_service):
        self.vault_service = vault_service

    def connect_wallet(self, db: Session, wallet_address: str) -> Dict[str, Any]:
        existing = user_data.get_user_by_wallet(db, wallet_address)
        if existing:
            vault_address = existing.vault_address or existing.safe_address
            return {
                "status": "existing",
                "wallet_address": existing.wallet_address,
                "vault_address": vault_address,
                "safe_address": vault_address,
                "created_at": str(existing.created_at),
            }

        configured_vault = settings.vault_address
        if not configured_vault:
            raise ValueError("VAULT_ADDRESS required to connect wallet")

        user = user_data.create_user(
            db=db,
            wallet_address=wallet_address,
            vault_address=configured_vault,
            network=settings.network,
            chain_id=settings.chain_id,
        )

        return {
            "status": "created",
            "wallet_address": user.wallet_address,
            "vault_address": user.safe_address,
            "safe_address": user.safe_address,
            "created_at": str(user.created_at),
        }

    def get_user(self, db: Session, wallet_address: str) -> Optional[Dict[str, Any]]:
        user = user_data.get_user_by_wallet(db, wallet_address)
        if not user:
            return None
        return {
            "wallet_address": user.wallet_address,
            "vault_address": user.vault_address or user.safe_address,
            "safe_address": user.vault_address or user.safe_address,
            "network": user.network,
            "chain_id": user.chain_id,
            "created_at": str(user.created_at),
            "is_active": user.is_active,
        }

    def get_all_users(self, db: Session) -> list[Dict[str, Any]]:
        users = user_data.get_all_users(db)
        return [
            {
                "wallet_address": u.wallet_address,
                "vault_address": u.vault_address or u.safe_address,
                "safe_address": u.vault_address or u.safe_address,
                "network": u.network,
                "created_at": str(u.created_at),
                "is_active": u.is_active,
            }
            for u in users
        ]
