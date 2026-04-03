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
        self.backend_account = Account.from_key(settings.backend_private_key)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def import_safe(self, safe_address: str, chain_id: int) -> Dict[str, Any]:
        return {
            "safeAddress": Web3.to_checksum_address(safe_address),
            "chainId": chain_id,
            "status": "imported"
        }

    def get_safe_info(self, safe_address: str) -> Dict[str, Any]:
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
        # This is an app-level normalized tx payload.
        # In production you usually also compute safeTxHash and gather signatures.
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
        url = f"{self.base_url}/api/v1/safes/{safe_address}/multisig-transactions/"

        payload = {
            "safe": safe_address,
            "to": to,
            "value": value,
            "data": data,
            "operation": operation,
            "safeTxHash": safe_tx_hash,
            "senderAddress": sender_address or self.backend_account.address,
            "signature": sender_signature or "0x",
            "origin": "openclaw-skill-api",
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response.json()

    def execute_direct_eoa_tx(self, to: str, data: str, value: int = 0) -> Dict[str, Any]:
        # This is NOT a Safe multisig execution.
        # It is only here as a basic relay helper example.
        nonce = self.w3.eth.get_transaction_count(self.backend_account.address)
        tx = {
            "chainId": settings.chain_id,
            "nonce": nonce,
            "to": Web3.to_checksum_address(to),
            "data": data,
            "value": value,
            "gas": 600000,
            "gasPrice": self.w3.eth.gas_price,
        }
        signed = self.backend_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return {"txHash": self.w3.to_hex(tx_hash)}