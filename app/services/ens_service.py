import json
from typing import Dict, Optional

from eth_account import Account
from eth_utils import keccak, to_checksum_address
from web3 import Web3

try:
    from app.config import settings
except ImportError:
    from config import settings


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_NODE = "0x" + ("00" * 32)

ENS_REGISTRY_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
        "name": "resolver",
        "outputs": [{"internalType": "contract Resolver", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]

PUBLIC_RESOLVER_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "node", "type": "bytes32"},
            {"internalType": "address", "name": "a", "type": "address"},
        ],
        "name": "setAddr",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "node", "type": "bytes32"},
            {"internalType": "string", "name": "key", "type": "string"},
            {"internalType": "string", "name": "value", "type": "string"},
        ],
        "name": "setText",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
        "name": "addr",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "node", "type": "bytes32"},
            {"internalType": "string", "name": "key", "type": "string"},
        ],
        "name": "text",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]

VAULT_ENS_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "registry", "type": "address"},
            {"internalType": "address", "name": "resolver", "type": "address"},
            {"internalType": "bytes32", "name": "parentNode", "type": "bytes32"},
        ],
        "name": "setEnsConfig",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "vaultId", "type": "uint256"},
            {"internalType": "string", "name": "label", "type": "string"},
        ],
        "name": "registerVaultEns",
        "outputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "vaultId", "type": "uint256"},
            {"internalType": "string[]", "name": "keys", "type": "string[]"},
            {"internalType": "string[]", "name": "values", "type": "string[]"},
        ],
        "name": "setVaultEnsTexts",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "vaultId", "type": "uint256"}],
        "name": "getVaultEnsRecord",
        "outputs": [
            {"internalType": "bytes32", "name": "node", "type": "bytes32"},
            {"internalType": "string", "name": "label", "type": "string"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def labelhash(label: str) -> bytes:
    return keccak(text=label)


def namehash(name: str) -> bytes:
    node = b"\x00" * 32
    if name:
        labels = [label for label in name.split(".") if label]
        for label in reversed(labels):
            node = keccak(node + keccak(text=label))
    return node


class ENSService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        admin_private_key = getattr(settings, "backend_private_key", "") or getattr(
            settings, "ens_private_key", ""
        )
        self.account = Account.from_key(admin_private_key) if admin_private_key else None
        self.registry = self.w3.eth.contract(
            address=to_checksum_address(settings.ens_registry_address),
            abi=ENS_REGISTRY_ABI,
        )

    @staticmethod
    def _checksum(address: str) -> str:
        return to_checksum_address(address)

    def _require_signer(self) -> None:
        if not self.account:
            raise ValueError("backend_private_key or ens_private_key is required for vault ENS writes")

    def _vault_contract_address(self) -> str:
        address = settings.vault_manager_address or settings.vault_address
        if not address:
            raise ValueError("VAULT_MANAGER_ADDRESS required")
        return self._checksum(address)

    def _vault_contract(self):
        return self.w3.eth.contract(address=self._vault_contract_address(), abi=VAULT_ENS_ABI)

    def _resolver_contract(self, resolver_address: str):
        return self.w3.eth.contract(
            address=self._checksum(resolver_address),
            abi=PUBLIC_RESOLVER_ABI,
        )

    def _fee_params(self) -> dict:
        latest_block = self.w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas")

        if base_fee is not None:
            try:
                priority_fee = self.w3.eth.max_priority_fee
            except Exception:
                priority_fee = self.w3.to_wei(2, "gwei")

            max_fee = int(base_fee * 2 + priority_fee)
            return {
                "maxPriorityFeePerGas": int(priority_fee),
                "maxFeePerGas": max_fee,
            }

        return {"gasPrice": int(self.w3.eth.gas_price)}

    def _send_tx(self, tx: dict) -> str:
        self._require_signer()
        tx.setdefault("from", self.account.address)
        tx["nonce"] = self.w3.eth.get_transaction_count(self.account.address, "pending")
        tx["chainId"] = settings.chain_id
        tx.update(self._fee_params())
        if "gas" not in tx:
            tx["gas"] = 500000

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            raise ValueError(f"Vault ENS transaction reverted: {self.w3.to_hex(tx_hash)}")
        return self.w3.to_hex(tx_hash)

    def _contract_tx(self, to: str, data: str, value: str | int = "0", **extra) -> dict:
        return {
            "to": self._checksum(to),
            "data": data or "0x",
            "value": str(value),
            **extra,
        }

    def resolve_full_name(self, label: Optional[str], parent_name: Optional[str] = None) -> str:
        parent = (parent_name or settings.ens_parent_name).strip(".")
        lbl = (label or "").strip(".")
        return f"{lbl}.{parent}" if lbl else parent

    def build_set_config_tx(
        self,
        registry_address: Optional[str] = None,
        resolver_address: Optional[str] = None,
        parent_name: Optional[str] = None,
    ) -> dict:
        registry = self._checksum(registry_address or settings.ens_registry_address)
        resolver = self._checksum(resolver_address or settings.ens_public_resolver_address)
        parent = parent_name or settings.ens_parent_name
        parent_node = namehash(parent)
        vault = self._vault_contract()
        data = vault.encode_abi("setEnsConfig", args=[registry, resolver, parent_node])
        return self._contract_tx(
            to=vault.address,
            data=data,
            value="0",
            registry=registry,
            resolver=resolver,
            parentName=parent,
            parentNode=self.w3.to_hex(parent_node),
        )

    def set_config(
        self,
        registry_address: Optional[str] = None,
        resolver_address: Optional[str] = None,
        parent_name: Optional[str] = None,
    ) -> dict:
        tx_data = self.build_set_config_tx(registry_address, resolver_address, parent_name)
        tx_hash = self._send_tx(
            {
                "from": self.account.address,
                "to": tx_data["to"],
                "data": tx_data["data"],
                "value": 0,
            }
        )
        return {
            "tx_hash": tx_hash,
            "registry": tx_data["registry"],
            "resolver": tx_data["resolver"],
            "parentName": tx_data["parentName"],
            "parentNode": tx_data["parentNode"],
        }

    def build_register_vault_tx(self, vault_id: int, label: str) -> dict:
        vault = self._vault_contract()
        data = vault.encode_abi("registerVaultEns", args=[vault_id, label])
        full_name = self.resolve_full_name(label)
        return self._contract_tx(
            to=vault.address,
            data=data,
            value="0",
            vaultId=str(vault_id),
            label=label,
            name=full_name,
            node=self.w3.to_hex(keccak(namehash(settings.ens_parent_name) + labelhash(label))),
        )

    def build_set_vault_texts_tx(self, vault_id: int, texts: Dict[str, str]) -> dict:
        normalized = self._normalize_text_records(texts)
        if not normalized:
            raise ValueError("At least one ENS text record is required")

        vault = self._vault_contract()
        keys = list(normalized.keys())
        values = [normalized[key] for key in keys]
        data = vault.encode_abi("setVaultEnsTexts", args=[vault_id, keys, values])
        return self._contract_tx(
            to=vault.address,
            data=data,
            value="0",
            vaultId=str(vault_id),
            texts=normalized,
        )

    def register_vault(self, vault_id: int, label: str, texts: Optional[Dict[str, str]] = None) -> dict:
        register_tx = self.build_register_vault_tx(vault_id, label)
        tx_hashes = [
            self._send_tx(
                {
                    "from": self.account.address,
                    "to": register_tx["to"],
                    "data": register_tx["data"],
                    "value": 0,
                }
            )
        ]

        normalized = self._normalize_text_records(texts or {})
        if normalized:
            text_tx = self.build_set_vault_texts_tx(vault_id, normalized)
            tx_hashes.append(
                self._send_tx(
                    {
                        "from": self.account.address,
                        "to": text_tx["to"],
                        "data": text_tx["data"],
                        "value": 0,
                    }
                )
            )

        return {
            "vaultId": str(vault_id),
            "label": label,
            "name": self.resolve_full_name(label),
            "node": register_tx["node"],
            "tx_hashes": tx_hashes,
            "texts": normalized,
        }

    def set_vault_text_records(self, vault_id: int, texts: Dict[str, str]) -> dict:
        tx_data = self.build_set_vault_texts_tx(vault_id, texts)
        tx_hash = self._send_tx(
            {
                "from": self.account.address,
                "to": tx_data["to"],
                "data": tx_data["data"],
                "value": 0,
            }
        )
        return {
            "vaultId": str(vault_id),
            "tx_hash": tx_hash,
            "texts": tx_data["texts"],
        }

    def get_vault_ens_record(self, vault_id: int) -> dict:
        vault = self._vault_contract()
        node, label = vault.functions.getVaultEnsRecord(vault_id).call()
        name = self.resolve_full_name(label) if label else ""
        return {
            "vaultId": str(vault_id),
            "label": label,
            "name": name,
            "node": self.w3.to_hex(node),
            "configured": self.w3.to_hex(node) != ZERO_NODE and bool(label),
        }

    def get_name_owner(self, name: str) -> str:
        return self.registry.functions.owner(namehash(name)).call()

    def get_resolver(self, name: str) -> str:
        return self.registry.functions.resolver(namehash(name)).call()

    def get_profile(self, name: str, text_keys: Optional[list[str]] = None) -> dict:
        node = namehash(name)
        owner = self.get_name_owner(name)
        resolver = self.get_resolver(name)

        addr = ZERO_ADDRESS
        texts = {}
        if resolver and resolver != ZERO_ADDRESS:
            resolver_contract = self._resolver_contract(resolver)
            try:
                addr = resolver_contract.functions.addr(node).call()
            except Exception:
                addr = ZERO_ADDRESS

            for key in text_keys or []:
                try:
                    texts[key] = resolver_contract.functions.text(node, key).call()
                except Exception:
                    texts[key] = ""

        return {
            "name": name,
            "node": self.w3.to_hex(node),
            "owner": owner,
            "resolver": resolver,
            "address": addr,
            "texts": texts,
            "network": settings.network,
            "chainId": settings.chain_id,
        }

    def get_vault_profile(self, vault_id: int, text_keys: Optional[list[str]] = None) -> dict:
        record = self.get_vault_ens_record(vault_id)
        if not record["configured"]:
            return {
                **record,
                "owner": ZERO_ADDRESS,
                "resolver": ZERO_ADDRESS,
                "address": ZERO_ADDRESS,
                "texts": {},
                "network": settings.network,
                "chainId": settings.chain_id,
            }

        profile = self.get_profile(record["name"], text_keys=text_keys)
        return {**record, **profile}

    def _normalize_text_records(self, texts: Dict[str, object]) -> Dict[str, str]:
        normalized: Dict[str, str] = {}
        for key, value in (texts or {}).items():
            if value is None:
                continue
            if isinstance(value, str):
                normalized[key] = value
            elif isinstance(value, (int, float)):
                if isinstance(value, int) or float(value).is_integer():
                    normalized[key] = str(int(value))
                else:
                    normalized[key] = format(float(value), "g")
            elif isinstance(value, list):
                normalized[key] = json.dumps(value, separators=(",", ":"))
            else:
                normalized[key] = json.dumps(value, separators=(",", ":"))
        return normalized
