from typing import Dict, Optional

from eth_account import Account
from eth_utils import keccak, to_checksum_address
from web3 import Web3

try:
    from app.config import settings
except ImportError:
    from config import settings


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

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
    {
        "inputs": [
            {"internalType": "bytes32", "name": "node", "type": "bytes32"},
            {"internalType": "bytes32", "name": "label", "type": "bytes32"},
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "resolver", "type": "address"},
            {"internalType": "uint64", "name": "ttl", "type": "uint64"},
        ],
        "name": "setSubnodeRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
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

REVERSE_REGISTRAR_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "addr", "type": "address"},
            {"internalType": "string", "name": "name", "type": "string"},
        ],
        "name": "setNameForAddr",
        "outputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "string", "name": "name", "type": "string"}],
        "name": "setName",
        "outputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
        "stateMutability": "nonpayable",
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

        # ens_private_key is not present in the provided config.py, so use a safe fallback.
        ens_private_key = getattr(settings, "ens_private_key", "") or getattr(
            settings, "backend_private_key", ""
        )
        self.account = Account.from_key(ens_private_key) if ens_private_key else None

        self.registry = self.w3.eth.contract(
            address=to_checksum_address(settings.ens_registry_address),
            abi=ENS_REGISTRY_ABI,
        )
        self.reverse_registrar = None
        if settings.ens_reverse_registrar_address:
            self.reverse_registrar = self.w3.eth.contract(
                address=to_checksum_address(settings.ens_reverse_registrar_address),
                abi=REVERSE_REGISTRAR_ABI,
            )

    def _require_signer(self) -> None:
        if not self.account:
            raise ValueError(
                "ens_private_key or backend_private_key is required for ENS write operations"
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

        return {
            "gasPrice": int(self.w3.eth.gas_price),
        }

    def _send_tx(self, tx: dict) -> str:
        self._require_signer()
        tx.setdefault("from", self.account.address)
        tx["nonce"] = self.w3.eth.get_transaction_count(self.account.address, "pending")
        tx["chainId"] = settings.chain_id
        tx.update(self._fee_params())
        if "gas" not in tx:
            tx["gas"] = 350000

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.to_hex(tx_hash)

    def resolve_full_name(self, label: Optional[str], parent_name: Optional[str] = None) -> str:
        parent = (parent_name or settings.ens_parent_name).strip(".")
        lbl = (label or "").strip(".")
        return f"{lbl}.{parent}" if lbl else parent

    def get_name_owner(self, name: str) -> str:
        return self.registry.functions.owner(namehash(name)).call()

    def get_resolver(self, name: str) -> str:
        return self.registry.functions.resolver(namehash(name)).call()

    def build_create_subname_tx(
        self,
        parent_name: str,
        label: str,
        owner_address: str,
        resolver_address: str,
        ttl: int = 0,
    ) -> dict:
        parent_node = namehash(parent_name)
        data = self.registry.encode_abi(
            "setSubnodeRecord",
            args=[
                parent_node,
                labelhash(label),
                to_checksum_address(owner_address),
                to_checksum_address(resolver_address),
                ttl,
            ],
        )
        full_name = self.resolve_full_name(label, parent_name)
        return {
            "to": self.registry.address,
            "data": data,
            "value": "0",
            "name": full_name,
            "node": self.w3.to_hex(namehash(full_name)),
            "parentNode": self.w3.to_hex(parent_node),
            "label": label,
        }

    def create_subname(
        self,
        parent_name: str,
        label: str,
        owner_address: str,
        resolver_address: str,
        ttl: int = 0,
    ) -> dict:
        self._require_signer()
        tx = self.registry.functions.setSubnodeRecord(
            namehash(parent_name),
            labelhash(label),
            to_checksum_address(owner_address),
            to_checksum_address(resolver_address),
            ttl,
        ).build_transaction({
            "from": self.account.address,
            "gas": 350000,
            **self._fee_params(),
        })
        tx_hash = self._send_tx(tx)

        full_name = self.resolve_full_name(label, parent_name)
        return {
            "tx_hash": tx_hash,
            "name": full_name,
            "node": self.w3.to_hex(namehash(full_name)),
            "owner": to_checksum_address(owner_address),
            "resolver": to_checksum_address(resolver_address),
        }

    def build_set_reverse_name_tx(self, target_address: str, name: str) -> dict:
        if not self.reverse_registrar:
            raise ValueError("ENS_REVERSE_REGISTRAR_ADDRESS is required for reverse ENS operations")

        data = self.reverse_registrar.encode_abi(
            "setNameForAddr",
            args=[to_checksum_address(target_address), name],
        )
        return {
            "to": self.reverse_registrar.address,
            "data": data,
            "value": "0",
            "address": to_checksum_address(target_address),
            "name": name,
        }

    def set_reverse_name(self, target_address: str, name: str) -> dict:
        self._require_signer()
        if not self.reverse_registrar:
            raise ValueError("ENS_REVERSE_REGISTRAR_ADDRESS is required for reverse ENS operations")

        tx = self.reverse_registrar.functions.setNameForAddr(
            to_checksum_address(target_address),
            name,
        ).build_transaction({
            "from": self.account.address,
            "gas": 350000,
            **self._fee_params(),
        })
        tx_hash = self._send_tx(tx)
        return {
            "tx_hash": tx_hash,
            "address": to_checksum_address(target_address),
            "name": name,
        }

    def build_set_addr_tx(self, name: str, address: str, resolver_address: Optional[str] = None) -> dict:
        node = namehash(name)
        resolver = resolver_address or self.get_resolver(name)
        if not resolver or resolver == ZERO_ADDRESS:
            raise ValueError(f"No resolver configured for {name}")
        resolver_contract = self.w3.eth.contract(
            address=to_checksum_address(resolver),
            abi=PUBLIC_RESOLVER_ABI,
        )
        data = resolver_contract.encode_abi("setAddr", args=[node, to_checksum_address(address)])
        return {
            "to": to_checksum_address(resolver),
            "data": data,
            "value": "0",
            "name": name,
            "address": to_checksum_address(address),
            "resolver": to_checksum_address(resolver),
            "node": self.w3.to_hex(node),
        }

    def set_addr(self, name: str, address: str, resolver_address: Optional[str] = None) -> dict:
        self._require_signer()
        tx_data = self.build_set_addr_tx(name=name, address=address, resolver_address=resolver_address)
        tx_hash = self._send_tx({
            "from": self.account.address,
            "to": tx_data["to"],
            "data": tx_data["data"],
            "value": 0,
        })
        return {"tx_hash": tx_hash, "name": name, "address": to_checksum_address(address)}

    def build_set_text_tx(
        self,
        name: str,
        key: str,
        value: str,
        resolver_address: Optional[str] = None,
    ) -> dict:
        node = namehash(name)
        resolver = resolver_address or self.get_resolver(name)
        if not resolver or resolver == ZERO_ADDRESS:
            raise ValueError(f"No resolver configured for {name}")
        resolver_contract = self.w3.eth.contract(
            address=to_checksum_address(resolver),
            abi=PUBLIC_RESOLVER_ABI,
        )
        data = resolver_contract.encode_abi("setText", args=[node, key, value])
        return {
            "to": to_checksum_address(resolver),
            "data": data,
            "value": "0",
            "name": name,
            "key": key,
            "textValue": value,
            "resolver": to_checksum_address(resolver),
            "node": self.w3.to_hex(node),
        }

    def set_text_records(self, name: str, texts: Dict[str, str], resolver_address: Optional[str] = None) -> dict:
        self._require_signer()
        tx_hashes = []
        for key, value in texts.items():
            tx_data = self.build_set_text_tx(name=name, key=key, value=value, resolver_address=resolver_address)
            tx_hashes.append(self._send_tx({
                "from": self.account.address,
                "to": tx_data["to"],
                "data": tx_data["data"],
                "value": 0,
            }))

        return {"name": name, "tx_hashes": tx_hashes, "texts": texts}

    def get_profile(self, name: str, text_keys: Optional[list[str]] = None) -> dict:
        node = namehash(name)
        owner = self.get_name_owner(name)
        resolver = self.get_resolver(name)

        addr = ZERO_ADDRESS
        texts = {}
        if resolver and resolver != ZERO_ADDRESS:
            resolver_contract = self.w3.eth.contract(
                address=to_checksum_address(resolver),
                abi=PUBLIC_RESOLVER_ABI,
            )
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
