import json
import os
from pathlib import Path

from eth_account import Account
from web3 import Web3

try:
    from app.config import settings
except ImportError:
    from config import settings

ROOT = Path(__file__).resolve().parent.parent
ABI_FILE = ROOT / "contracts" / "artifacts" / "ScampiaENSManager.abi.json"
BYTECODE_FILE = ROOT / "contracts" / "artifacts" / "ScampiaENSManager.bytecode.txt"


def load_artifact() -> tuple[list[dict], str]:
    if not ABI_FILE.exists() or not BYTECODE_FILE.exists():
        raise FileNotFoundError(
            "Missing ENS manager artifacts. Run: python3 scripts/export_abi.py"
        )

    abi = json.loads(ABI_FILE.read_text(encoding="utf-8"))
    bytecode = BYTECODE_FILE.read_text(encoding="utf-8").strip()
    return abi, bytecode


def main() -> None:
    rpc_url = settings.rpc_url
    private_key = os.getenv("BACKEND_PRIVATE_KEY", "").strip()
    vault_contract = settings.vault_manager_address or settings.vault_address

    if not rpc_url:
        raise ValueError("RPC_URL is required")
    if not private_key:
        raise ValueError("BACKEND_PRIVATE_KEY is required")
    if not vault_contract:
        raise ValueError("VAULT_MANAGER_ADDRESS or VAULT_ADDRESS is required")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError("Unable to connect to RPC")

    account = Account.from_key(private_key)
    chain_id = w3.eth.chain_id

    abi, bytecode = load_artifact()
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx = contract.constructor(
        account.address,
        Web3.to_checksum_address(vault_contract),
    ).build_transaction(
        {
            "chainId": chain_id,
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "gas": 2_000_000,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)

    if receipt.status != 1:
        raise RuntimeError(f"Deployment reverted: {w3.to_hex(tx_hash)}")

    print("ENS manager deployment successful")
    print(f"Contract address: {receipt.contractAddress}")
    print(f"Tx hash: {w3.to_hex(tx_hash)}")
    print(f"Chain ID: {chain_id}")


if __name__ == "__main__":
    main()
