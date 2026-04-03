from typing import Dict, Optional

from eth_account import Account
from eth_utils import keccak, to_checksum_address
from web3 import Web3

try:
    from app.config import settings
except ImportError:
    from config import settings


ENS_REGISTRY_ABI = [
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
        labels = name.split(".")
        for label in reversed(labels):
            node = keccak(node + keccak(text=label))
    return node


class ENSService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self.account = Account.from_key(settings.backend_private_key) if settings.backend_private_key else None
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
            raise ValueError("BACKEND_PRIVATE_KEY is required for ENS write operations")

    def _send_tx(self, tx: dict) -> str:
        self._require_signer()
        tx["nonce"] = self.w3.eth.get_transaction_count(self.account.address)
        tx["chainId"] = settings.chain_id
        tx["gasPrice"] = self.w3.eth.gas_price
        if "gas" not in tx:
            tx["gas"] = 350000

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.to_hex(tx_hash)

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
        full_name = f"{label}.{parent_name}"
        return {
            "to": self.registry.address,
            "data": data,
            "value": "0",
            "name": full_name,
            "node": self.w3.to_hex(namehash(full_name)),
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
        ).build_transaction({"from": self.account.address})
        tx_hash = self._send_tx(tx)

        full_name = f"{label}.{parent_name}"
        return {
            "tx_hash": tx_hash,
            "name": full_name,
            "node": self.w3.to_hex(namehash(full_name)),
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
        ).build_transaction({"from": self.account.address})
        tx_hash = self._send_tx(tx)
        return {
            "tx_hash": tx_hash,
            "address": to_checksum_address(target_address),
            "name": name,
        }

    def get_resolver(self, name: str) -> str:
        node = namehash(name)
        return self.registry.functions.resolver(node).call()

    def set_addr(self, name: str, address: str, resolver_address: Optional[str] = None) -> dict:
        self._require_signer()
        node = namehash(name)
        resolver = resolver_address or self.get_resolver(name)
        resolver_contract = self.w3.eth.contract(
            address=to_checksum_address(resolver),
            abi=PUBLIC_RESOLVER_ABI,
        )
        tx = resolver_contract.functions.setAddr(
            node,
            to_checksum_address(address),
        ).build_transaction({"from": self.account.address})
        tx_hash = self._send_tx(tx)
        return {"tx_hash": tx_hash, "name": name, "address": to_checksum_address(address)}

    def set_text_records(self, name: str, texts: Dict[str, str], resolver_address: Optional[str] = None) -> dict:
        self._require_signer()
        node = namehash(name)
        resolver = resolver_address or self.get_resolver(name)
        resolver_contract = self.w3.eth.contract(
            address=to_checksum_address(resolver),
            abi=PUBLIC_RESOLVER_ABI,
        )

        tx_hashes = []
        for key, value in texts.items():
            tx = resolver_contract.functions.setText(node, key, value).build_transaction(
                {"from": self.account.address}
            )
            tx_hashes.append(self._send_tx(tx))

        return {"name": name, "tx_hashes": tx_hashes, "texts": texts}

    def get_profile(self, name: str, text_keys: Optional[list[str]] = None) -> dict:
        node = namehash(name)
        resolver = self.get_resolver(name)
        resolver_contract = self.w3.eth.contract(
            address=to_checksum_address(resolver),
            abi=PUBLIC_RESOLVER_ABI,
        )
        addr = resolver_contract.functions.addr(node).call()

        texts = {}
        for key in text_keys or []:
            try:
                texts[key] = resolver_contract.functions.text(node, key).call()
            except Exception:
                texts[key] = ""

        return {
            "name": name,
            "resolver": resolver,
            "address": addr,
            "texts": texts,
            "network": settings.network,
            "chainId": settings.chain_id,
        }
