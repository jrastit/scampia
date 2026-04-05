import json
import os
import sys
import time
from pathlib import Path

from eth_account import Account
from web3 import Web3
from web3.exceptions import TimeExhausted, TransactionNotFound

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from app.config import settings
except ImportError:
    from config import settings

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


def fee_params(w3: Web3) -> dict[str, int]:
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas")
    if base_fee is None:
        return {"gasPrice": w3.eth.gas_price}

    priority_fee = w3.to_wei(2, "gwei")
    max_fee = base_fee * 2 + priority_fee
    return {
        "maxPriorityFeePerGas": priority_fee,
        "maxFeePerGas": max_fee,
    }


def wait_for_receipt(w3: Web3, tx_hash, timeout: int = 240, poll_latency: float = 2.0):
    tx_hex = w3.to_hex(tx_hash)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound:
            receipt = None
        if receipt is not None:
            return receipt
        time.sleep(poll_latency)
    raise TimeExhausted(f"Transaction {tx_hex} is not in the chain after {timeout} seconds")


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
    nonce = w3.eth.get_transaction_count(account.address, "pending")

    abi, bytecode = load_artifact()
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx = contract.constructor(
        account.address,
        Web3.to_checksum_address(vault_contract),
    ).build_transaction(
        {
            "chainId": chain_id,
            "from": account.address,
            "nonce": nonce,
            "gas": 2_000_000,
            **fee_params(w3),
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = w3.to_hex(tx_hash)

    print("Submitted ENS manager deployment")
    print(f"From: {account.address}")
    print(f"Nonce: {nonce}")
    print(f"Tx hash: {tx_hex}")
    print(f"RPC: {rpc_url}")

    try:
        receipt = wait_for_receipt(w3, tx_hash, timeout=240)
    except TimeExhausted as exc:
        raise RuntimeError(
            f"ENS manager deployment transaction not mined in time: {tx_hex}. "
            "Check the tx on your RPC/explorer and retry if it was dropped."
        ) from exc

    if receipt.status != 1:
        raise RuntimeError(f"Deployment reverted: {tx_hex}")

    print("ENS manager deployment successful")
    print(f"Contract address: {receipt.contractAddress}")
    print(f"Tx hash: {tx_hex}")
    print(f"Chain ID: {chain_id}")


if __name__ == "__main__":
    main()
