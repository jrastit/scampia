from typing import Any, Dict

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
]

VAULT_ABI = [
    {
        "inputs": [{"name": "ownerFeeBps", "type": "uint16"}],
        "name": "createVault",
        "outputs": [{"name": "vaultId", "type": "uint256"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "vaultId", "type": "uint256"},
            {"name": "assets", "type": "uint256"},
            {"name": "receiver", "type": "address"},
        ],
        "name": "deposit",
        "outputs": [{"name": "mintedShares", "type": "uint256"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "vaultId", "type": "uint256"},
            {"name": "burnedShares", "type": "uint256"},
            {"name": "receiver", "type": "address"},
        ],
        "name": "withdraw",
        "outputs": [{"name": "userAssets", "type": "uint256"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "vaultId", "type": "uint256"},
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "minAssetDelta", "type": "int256"},
        ],
        "name": "executeTrade",
        "outputs": [{"name": "assetDelta", "type": "int256"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "vaultId", "type": "uint256"},
            {"name": "user", "type": "address"},
        ],
        "name": "getUserPosition",
        "outputs": [
            {"name": "shares", "type": "uint256"},
            {"name": "principal", "type": "uint256"},
            {"name": "estimatedAssets", "type": "uint256"},
        ],
        "type": "function",
    },
]


class VaultService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self.backend_account = (
            Account.from_key(settings.backend_private_key)
            if settings.backend_private_key
            else None
        )

    @staticmethod
    def _checksum(address: str) -> str:
        return Web3.to_checksum_address(address)

    @staticmethod
    def _parse_data(data: str) -> bytes:
        if not data or data == "0x":
            return b""
        return bytes.fromhex(data[2:]) if data.startswith("0x") else bytes.fromhex(data)

    def manager_contract_address(self) -> str:
        address = settings.vault_manager_address or settings.vault_address
        if not address:
            raise ValueError("VAULT_MANAGER_ADDRESS required")
        return self._checksum(address)

    def _vault_contract(self):
        return self.w3.eth.contract(address=self.manager_contract_address(), abi=VAULT_ABI)

    def get_eth_balance(self) -> int:
        return self.w3.eth.get_balance(self.manager_contract_address())

    def get_token_balance(self, token_address: str) -> int:
        contract = self.w3.eth.contract(address=self._checksum(token_address), abi=ERC20_ABI)
        return contract.functions.balanceOf(self.manager_contract_address()).call()

    def get_token_decimals(self, token_address: str) -> int:
        contract = self.w3.eth.contract(address=self._checksum(token_address), abi=ERC20_ABI)
        return contract.functions.decimals().call()

    def get_token_symbol(self, token_address: str) -> str:
        contract = self.w3.eth.contract(address=self._checksum(token_address), abi=ERC20_ABI)
        return contract.functions.symbol().call()

    def get_all_balances(self) -> Dict[str, Any]:
        balances: Dict[str, Any] = {
            "ETH": {
                "balance": self.get_eth_balance(),
                "decimals": 18,
                "symbol": "ETH",
                "token_address": None,
            }
        }

        tokens = set(settings.trade_allowed_tokens_in + settings.trade_allowed_tokens_out)
        for token in {t for t in tokens if t}:
            try:
                symbol = self.get_token_symbol(token)
                balances[symbol] = {
                    "balance": self.get_token_balance(token),
                    "decimals": self.get_token_decimals(token),
                    "symbol": symbol,
                    "token_address": self._checksum(token),
                }
            except Exception:
                continue

        return balances

    def build_safe_tx(
        self,
        safe_address: str,
        to: str,
        data: str,
        value: str = "0",
        operation: int = 0,
    ) -> Dict[str, Any]:
        return {
            "vaultAddress": self._checksum(safe_address),
            "to": self._checksum(to),
            "data": data or "0x",
            "value": str(value),
            "operation": operation,
            "network": settings.network,
            "chainId": settings.chain_id,
        }

    def build_create_vault_tx(self, owner_fee_bps: int) -> Dict[str, Any]:
        vault = self._vault_contract()
        calldata = vault.encode_abi("createVault", args=[owner_fee_bps])
        return {
            "managerAddress": self.manager_contract_address(),
            "to": self.manager_contract_address(),
            "data": calldata,
            "value": "0",
            "ownerFeeBps": owner_fee_bps,
        }

    def build_deposit_tx(self, vault_id: int, amount: int, receiver: str) -> Dict[str, Any]:
        vault = self._vault_contract()
        calldata = vault.encode_abi("deposit", args=[vault_id, amount, self._checksum(receiver)])
        return {
            "managerAddress": self.manager_contract_address(),
            "vaultId": vault_id,
            "to": self.manager_contract_address(),
            "data": calldata,
            "value": "0",
            "amount": str(amount),
            "receiver": self._checksum(receiver),
        }

    def build_withdraw_tx(self, vault_id: int, shares: int, receiver: str) -> Dict[str, Any]:
        vault = self._vault_contract()
        calldata = vault.encode_abi("withdraw", args=[vault_id, shares, self._checksum(receiver)])
        return {
            "managerAddress": self.manager_contract_address(),
            "vaultId": vault_id,
            "to": self.manager_contract_address(),
            "data": calldata,
            "value": "0",
            "shares": str(shares),
            "receiver": self._checksum(receiver),
        }

    def build_agent_swap_tx(
        self,
        vault_id: int,
        target: str,
        data: str,
        min_asset_delta: int = 0,
        value: int = 0,
    ) -> Dict[str, Any]:
        vault = self._vault_contract()
        calldata = vault.encode_abi(
            "executeTrade",
            args=[
                vault_id,
                self._checksum(target),
                value,
                self._parse_data(data),
                min_asset_delta,
            ],
        )
        return {
            "managerAddress": self.manager_contract_address(),
            "vaultId": vault_id,
            "to": self.manager_contract_address(),
            "data": calldata,
            "value": "0",
            "target": self._checksum(target),
            "minAssetDelta": str(min_asset_delta),
        }

    def execute_agent_swap(
        self,
        vault_id: int,
        target: str,
        data: str,
        min_asset_delta: int = 0,
        value: int = 0,
    ) -> Dict[str, Any]:
        if not self.backend_account:
            raise ValueError("BACKEND_PRIVATE_KEY required")

        vault = self._vault_contract()
        tx = vault.functions.executeTrade(
            vault_id,
            self._checksum(target),
            value,
            self._parse_data(data),
            min_asset_delta,
        ).build_transaction({
            "chainId": settings.chain_id,
            "from": self.backend_account.address,
            "nonce": self.w3.eth.get_transaction_count(self.backend_account.address, "pending"),
            "gas": 700_000,
            "gasPrice": self.w3.eth.gas_price,
            "value": 0,
        })

        signed = self.backend_account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return {
            "txHash": self.w3.to_hex(tx_hash),
            "managerAddress": self.manager_contract_address(),
            "vaultId": vault_id,
            "executor": self.backend_account.address,
            "target": self._checksum(target),
            "minAssetDelta": str(min_asset_delta),
        }

    def get_user_position(self, vault_id: int, user_address: str) -> Dict[str, str]:
        vault = self._vault_contract()
        shares, principal, estimated_assets = vault.functions.getUserPosition(
            vault_id,
            self._checksum(user_address),
        ).call()
        return {
            "vaultId": str(vault_id),
            "user": self._checksum(user_address),
            "shares": str(shares),
            "principal": str(principal),
            "estimatedAssets": str(estimated_assets),
        }

    def import_vault(self, vault_address: str, chain_id: int) -> Dict[str, Any]:
        return {
            "managerAddress": self._checksum(vault_address),
            "chainId": chain_id,
            "configuredChainId": settings.chain_id,
            "network": settings.network,
            "status": "imported",
        }
