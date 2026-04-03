from typing import Any, Dict, Optional

import requests
from eth_account import Account
from web3 import Web3

try:
    from app.config import settings
except ImportError:
    from config import settings


ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

SAFE_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "operation", "type": "uint8"},
            {"name": "safeTxGas", "type": "uint256"},
            {"name": "baseGas", "type": "uint256"},
            {"name": "gasPrice", "type": "uint256"},
            {"name": "gasToken", "type": "address"},
            {"name": "refundReceiver", "type": "address"},
            {"name": "signatures", "type": "bytes"},
        ],
        "name": "execTransaction",
        "outputs": [{"name": "success", "type": "bool"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "operation", "type": "uint8"},
            {"name": "safeTxGas", "type": "uint256"},
            {"name": "baseGas", "type": "uint256"},
            {"name": "gasPrice", "type": "uint256"},
            {"name": "gasToken", "type": "address"},
            {"name": "refundReceiver", "type": "address"},
            {"name": "_nonce", "type": "uint256"},
        ],
        "name": "getTransactionHash",
        "outputs": [{"name": "", "type": "bytes32"}],
        "type": "function",
    },
    {
        "inputs": [],
        "name": "nonce",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]


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

    def _checksum(self, address: str) -> str:
        return Web3.to_checksum_address(address)

    def _parse_data(self, data: str) -> bytes:
        if not data or data == "0x":
            return b""
        return bytes.fromhex(data[2:]) if data.startswith("0x") else bytes.fromhex(data)

    # Balance

    def get_eth_balance(self, safe_address: str) -> int:
        return self.w3.eth.get_balance(self._checksum(safe_address))

    def get_token_balance(self, safe_address: str, token_address: str) -> int:
        contract = self.w3.eth.contract(
            address=self._checksum(token_address), abi=ERC20_ABI,
        )
        return contract.functions.balanceOf(self._checksum(safe_address)).call()

    def get_token_decimals(self, token_address: str) -> int:
        contract = self.w3.eth.contract(
            address=self._checksum(token_address), abi=ERC20_ABI,
        )
        return contract.functions.decimals().call()

    def get_token_symbol(self, token_address: str) -> str:
        contract = self.w3.eth.contract(
            address=self._checksum(token_address), abi=ERC20_ABI,
        )
        return contract.functions.symbol().call()

    def get_token_allowance(self, safe_address: str, token_address: str, spender: str) -> int:
        contract = self.w3.eth.contract(
            address=self._checksum(token_address), abi=ERC20_ABI,
        )
        return contract.functions.allowance(
            self._checksum(safe_address), self._checksum(spender),
        ).call()

    def get_all_balances(self, safe_address: str) -> Dict[str, Any]:
        addr = self._checksum(safe_address)
        try:
            url = f"{self.base_url}/api/v1/safes/{addr}/balances/"
            resp = requests.get(url, headers=self._headers(), timeout=15)
            resp.raise_for_status()
            raw = resp.json()

            balances: Dict[str, Any] = {}
            for item in raw:
                token = item.get("token")
                if token is None:
                    balances["ETH"] = {
                        "balance": int(item["balance"]),
                        "decimals": 18,
                        "symbol": "ETH",
                        "token_address": None,
                    }
                else:
                    symbol = token.get("symbol", "???")
                    balances[symbol] = {
                        "balance": int(item["balance"]),
                        "decimals": token.get("decimals", 18),
                        "symbol": symbol,
                        "token_address": token.get("address"),
                    }
            return balances
        except Exception:
            return {
                "ETH": {
                    "balance": self.get_eth_balance(addr),
                    "decimals": 18,
                    "symbol": "ETH",
                    "token_address": None,
                }
            }

    def has_sufficient_balance(self, safe_address: str, token_address: str, amount: int) -> bool:
        return self.get_token_balance(safe_address, token_address) >= amount

    # Safe info

    def import_safe(self, safe_address: str, chain_id: int) -> Dict[str, Any]:
        return {
            "safeAddress": self._checksum(safe_address),
            "chainId": chain_id,
            "configuredChainId": settings.chain_id,
            "network": settings.network,
            "status": "imported",
        }

    def get_safe_info(self, safe_address: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/safes/{self._checksum(safe_address)}/"
        resp = requests.get(url, headers=self._headers(), timeout=20)
        resp.raise_for_status()
        info = resp.json()
        try:
            info["balances"] = self.get_all_balances(safe_address)
        except Exception:
            info["balances"] = {}
        return info

    # Transaction building

    def _get_safe_nonce(self, safe_address: str) -> int:
        try:
            url = f"{self.base_url}/api/v1/safes/{self._checksum(safe_address)}/"
            resp = requests.get(url, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            return resp.json().get("nonce", 0)
        except Exception:
            return 0

    def get_safe_nonce_onchain(self, safe_address: str) -> int:
        contract = self.w3.eth.contract(
            address=self._checksum(safe_address), abi=SAFE_ABI,
        )
        return contract.functions.nonce().call()

    def build_safe_tx(
        self,
        safe_address: str,
        to: str,
        data: str,
        value: str = "0",
        operation: int = 0,
    ) -> Dict[str, Any]:
        return {
            "safeAddress": self._checksum(safe_address),
            "chainId": settings.chain_id,
            "network": settings.network,
            "to": self._checksum(to),
            "value": str(value),
            "data": data or "0x",
            "operation": operation,
            "nonce": self._get_safe_nonce(safe_address),
            "safeTxGas": 0,
            "baseGas": 0,
            "gasPrice": "0",
            "gasToken": "0x0000000000000000000000000000000000000000",
            "refundReceiver": "0x0000000000000000000000000000000000000000",
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
        if not sender_address and not self.backend_account:
            raise ValueError("sender_address or BACKEND_PRIVATE_KEY required")

        url = f"{self.base_url}/api/v1/safes/{self._checksum(safe_address)}/multisig-transactions/"
        payload = {
            "safe": self._checksum(safe_address),
            "to": self._checksum(to),
            "value": str(value),
            "data": data,
            "operation": operation,
            "safeTxHash": safe_tx_hash,
            "senderAddress": sender_address or self.backend_account.address,
            "signature": sender_signature or "0x",
            "origin": "scampia-safe-layer",
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        resp.raise_for_status()
        return resp.json()

    # Execution

    def execute_safe_tx(
        self,
        safe_address: str,
        to: str,
        data: str,
        value: int = 0,
        operation: int = 0,
    ) -> Dict[str, Any]:
        if not self.backend_account:
            raise ValueError("BACKEND_PRIVATE_KEY required")

        addr = self._checksum(safe_address)
        safe_contract = self.w3.eth.contract(address=addr, abi=SAFE_ABI)
        zero = "0x0000000000000000000000000000000000000000"
        tx_bytes = self._parse_data(data)

        nonce = safe_contract.functions.nonce().call()

        safe_tx_hash = safe_contract.functions.getTransactionHash(
            self._checksum(to), value, tx_bytes, operation,
            0, 0, 0,
            self._checksum(zero), self._checksum(zero),
            nonce,
        ).call()

        signature = self.backend_account.signHash(safe_tx_hash)
        sig_bytes = (
            signature.r.to_bytes(32, "big")
            + signature.s.to_bytes(32, "big")
            + signature.v.to_bytes(1, "big")
        )

        tx = safe_contract.functions.execTransaction(
            self._checksum(to), value, tx_bytes, operation,
            0, 0, 0,
            self._checksum(zero), self._checksum(zero),
            sig_bytes,
        ).build_transaction({
            "chainId": settings.chain_id,
            "from": self.backend_account.address,
            "nonce": self.w3.eth.get_transaction_count(self.backend_account.address),
            "gas": 500_000,
            "gasPrice": self.w3.eth.gas_price,
        })

        signed = self.backend_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

        return {
            "txHash": self.w3.to_hex(tx_hash),
            "safeTxHash": self.w3.to_hex(safe_tx_hash),
            "safeAddress": addr,
            "to": self._checksum(to),
            "value": str(value),
            "nonce": nonce,
            "executor": self.backend_account.address,
        }

    def execute_direct_eoa_tx(self, to: str, data: str, value: int = 0) -> Dict[str, Any]:
        if not self.backend_account:
            raise ValueError("BACKEND_PRIVATE_KEY required")

        nonce = self.w3.eth.get_transaction_count(self.backend_account.address)
        tx = {
            "chainId": settings.chain_id,
            "nonce": nonce,
            "to": self._checksum(to),
            "data": data,
            "value": value,
            "gas": 600_000,
            "gasPrice": self.w3.eth.gas_price,
        }
        signed = self.backend_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return {"txHash": self.w3.to_hex(tx_hash)}