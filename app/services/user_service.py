from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.data import user_data
from app.config import settings


class UserService:
    SYNC_RETRY_AFTER_SECONDS = 2

    def __init__(self, vault_service):
        self.vault_service = vault_service

    @staticmethod
    def _normalize_address(address: str) -> str:
        return address.lower()

    def _find_vault_id_by_owner(self, wallet_address: str) -> Optional[int]:
        wallet = self._normalize_address(wallet_address)
        vaults_payload = self.vault_service.list_vaults()
        matching_ids: list[int] = []

        for vault in vaults_payload.get("items", []):
            owner = str(vault.get("owner", "")).lower()
            if owner == wallet:
                matching_ids.append(int(vault["vault_id"]))

        if not matching_ids:
            return None

        # If an owner created multiple vaults, expose the latest id.
        return max(matching_ids)

    def _build_vault_sync_payload(self, wallet_address: str) -> Dict[str, Any]:
        try:
            vault_id = self._find_vault_id_by_owner(wallet_address)
        except Exception:
            return {
                "vault_id": None,
                "pending_sync": True,
                "retry_after_seconds": self.SYNC_RETRY_AFTER_SECONDS,
                "sync_source": "onchain_scan_error",
            }

        if vault_id is None:
            return {
                "vault_id": None,
                "pending_sync": True,
                "retry_after_seconds": self.SYNC_RETRY_AFTER_SECONDS,
                "sync_source": "onchain_scan",
            }

        return {
            "vault_id": vault_id,
            "pending_sync": False,
            "retry_after_seconds": 0,
            "sync_source": "onchain_scan",
        }

    def connect_wallet(self, db: Session, wallet_address: str) -> Dict[str, Any]:
        existing = user_data.get_user_by_wallet(db, wallet_address)
        if existing:
            vault_address = existing.vault_address or existing.safe_address
            payload = {
                "status": "existing",
                "wallet_address": existing.wallet_address,
                "vault_address": vault_address,
                "safe_address": vault_address,
                "created_at": str(existing.created_at),
            }
            payload.update(self._build_vault_sync_payload(existing.wallet_address))
            return payload

        configured_vault = settings.vault_manager_address or settings.vault_address
        if not configured_vault:
            raise ValueError("VAULT_MANAGER_ADDRESS required to connect wallet")

        user = user_data.create_user(
            db=db,
            wallet_address=wallet_address,
            vault_address=configured_vault,
            network=settings.network,
            chain_id=settings.chain_id,
        )

        payload = {
            "status": "created",
            "wallet_address": user.wallet_address,
            "vault_address": user.safe_address,
            "safe_address": user.safe_address,
            "created_at": str(user.created_at),
        }
        payload.update(self._build_vault_sync_payload(user.wallet_address))
        return payload

    def get_user(self, db: Session, wallet_address: str) -> Optional[Dict[str, Any]]:
        user = user_data.get_user_by_wallet(db, wallet_address)
        if not user:
            return None
        payload = {
            "wallet_address": user.wallet_address,
            "vault_address": user.vault_address or user.safe_address,
            "safe_address": user.vault_address or user.safe_address,
            "network": user.network,
            "chain_id": user.chain_id,
            "created_at": str(user.created_at),
            "is_active": user.is_active,
        }
        payload.update(self._build_vault_sync_payload(user.wallet_address))
        return payload

    def get_user_vault_sync(self, db: Session, wallet_address: str) -> Optional[Dict[str, Any]]:
        user = user_data.get_user_by_wallet(db, wallet_address)
        if not user:
            return None

        payload = {
            "wallet_address": user.wallet_address,
        }
        payload.update(self._build_vault_sync_payload(user.wallet_address))
        return payload

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

    def get_user_investments(self, wallet_address: str) -> Dict[str, Any]:
        normalized_wallet = wallet_address.lower()
        vaults_payload = self.vault_service.list_vaults()
        items: list[Dict[str, Any]] = []

        for vault in vaults_payload.get("items", []):
            vault_id = int(vault["vault_id"])
            position = self.vault_service.get_user_position(vault_id, normalized_wallet)
            shares = int(position["shares"])
            if shares <= 0:
                continue

            value = int(position["estimatedAssets"])
            principal = int(position["principal"])
            profit = value - principal

            items.append(
                {
                    "vault_id": vault_id,
                    "shares": str(shares),
                    "value": str(value),
                    "profit": str(profit),
                }
            )

        return {
            "wallet_address": normalized_wallet,
            "items": items,
        }
