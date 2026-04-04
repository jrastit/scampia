from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.data import user_data


class UserService:

    def __init__(self, safe_service):
        self.safe_service = safe_service

    def connect_wallet(self, db: Session, wallet_address: str) -> Dict[str, Any]:
        existing = user_data.get_user_by_wallet(db, wallet_address)
        if existing:
            return {
                "status": "existing",
                "wallet_address": existing.wallet_address,
                "safe_address": existing.safe_address,
                "created_at": str(existing.created_at),
            }

        result = self.safe_service.deploy_safe(owner_address=wallet_address)

        user = user_data.create_user(
            db=db,
            wallet_address=wallet_address,
            safe_address=result["safeAddress"],
            network=result.get("network", "ethereum-sepolia"),
            chain_id=result.get("chainId", 11155111),
        )

        return {
            "status": "created",
            "wallet_address": user.wallet_address,
            "safe_address": user.safe_address,
            "deploy_tx": result["txHash"],
            "created_at": str(user.created_at),
        }

    def get_user(self, db: Session, wallet_address: str) -> Optional[Dict[str, Any]]:
        user = user_data.get_user_by_wallet(db, wallet_address)
        if not user:
            return None
        return {
            "wallet_address": user.wallet_address,
            "safe_address": user.safe_address,
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
                "safe_address": u.safe_address,
                "network": u.network,
                "created_at": str(u.created_at),
                "is_active": u.is_active,
            }
            for u in users
        ]
