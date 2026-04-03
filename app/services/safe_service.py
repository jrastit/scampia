from typing import Any, Dict, Optional

import requests
from eth_account import Account
from web3 import Web3

from app.config import settings


class SafeService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self.base_url = settings.safe_tx_service_base.rstrip("/")
        self.api_key = settings.safe_api_key
        self.backend_account = (
            Account.from_key(settings.backend_private_key)
            if settings.backend_private_key
            else None
        )

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _require_backend_account(self):
        if not self.backend_account:
            raise ValueError("BACKEND_PRIVATE_KEY is required for direct signing or relay actions")
        return self.backend_account

    def import_safe(self, safe_address: str, chain_id: int) -> Dict[str, Any]:
        return {
            "safeAddress": Web3.to_checksum_address(safe_address),
            "chainId": chain_id,
            "status": "imported"
        }

    def get_safe_info(self, safe_address: str) -> Dict[str, Any]:
        safe_address = Web3.to_checksum_address(safe_address)
        url = f"{self.base_url}/api/v1/safes/{safe_address}/"
        response = requests.get(url, headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response.json()

    def build_safe_tx(
        self,
        safe_address: str,
        to: str,
        data: str,
        value: str = "0",
        operation: int = 0,
    ) -> Dict[str, Any]:
        return {
            "safeAddress": Web3.to_checksum_address(safe_address),
            "to": Web3.to_checksum_address(to),
            "value": str(value),
            "data": data,
            "operation": operation,
        }

    def propose_safe_tx(
        self,
        safe_address: str,
        safe_tx_hash: str,
        to: str,
        data: str,
        value: str = "0",
        operation: int = 0,
        sender_signature: Optional[str] = None,
        sender_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        sender = sender_address
        if not sender:
            sender = self._require_backend_account().address

        url = f"{self.base_url}/api/v1/safes/{Web3.to_checksum_address(safe_address)}/multisig-transactions/"

        payload = {
            "safe": Web3.to_checksum_address(safe_address),
            "to": Web3.to_checksum_address(to),
            "value": str(value),
            "data": data,
            "operation": operation,
            "safeTxHash": safe_tx_hash,
            "senderAddress": Web3.to_checksum_address(sender),
            "signature": sender_signature or "0x",
            "origin": "openclaw-skill-api",
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response.json()

    def execute_direct_eoa_tx(self, to: str, data: str, value: int = 0) -> Dict[str, Any]:
        backend_account = self._require_backend_account()
        nonce = self.w3.eth.get_transaction_count(backend_account.address)
        tx = {
            "chainId": settings.chain_id,
            "nonce": nonce,
            "to": Web3.to_checksum_address(to),
            "data": data,
            "value": value,
            "gas": 600000,
            "gasPrice": self.w3.eth.gas_price,
        }
        signed = backend_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return {"txHash": self.w3.to_hex(tx_hash)}
