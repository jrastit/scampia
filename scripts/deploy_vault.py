import json
import os
from pathlib import Path

from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parent.parent
ABI_FILE = ROOT / "contracts" / "artifacts" / "ScampiaVault.abi.json"
BYTECODE_FILE = ROOT / "contracts" / "artifacts" / "ScampiaVault.bytecode.txt"


def load_artifact() -> tuple[list[dict], str]:
    if not ABI_FILE.exists() or not BYTECODE_FILE.exists():
        raise FileNotFoundError(
            "Missing ABI/bytecode artifacts. Run: python3 scripts/export_abi.py"
        )

    abi = json.loads(ABI_FILE.read_text(encoding="utf-8"))
    bytecode = BYTECODE_FILE.read_text(encoding="utf-8").strip()
    return abi, bytecode


def main() -> None:
    rpc_url = os.getenv("RPC_URL", "").strip()
    private_key = os.getenv("BACKEND_PRIVATE_KEY", "").strip()
    asset_token = os.getenv("VAULT_ASSET_TOKEN", "").strip()
    manager_recipient = os.getenv("VAULT_MANAGER_RECIPIENT", "").strip()
    manager_fee_bps = int(os.getenv("VAULT_MANAGER_FEE_BPS", "0"))

    if not rpc_url:
        raise ValueError("RPC_URL is required")
    if not private_key:
        raise ValueError("BACKEND_PRIVATE_KEY is required")
    if not asset_token:
        raise ValueError("VAULT_ASSET_TOKEN is required")
    if not manager_recipient:
        raise ValueError("VAULT_MANAGER_RECIPIENT is required")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise RuntimeError("Unable to connect to RPC")

    account = Account.from_key(private_key)
    chain_id = w3.eth.chain_id

    abi, bytecode = load_artifact()
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx = contract.constructor(
        Web3.to_checksum_address(asset_token),
        account.address,
        Web3.to_checksum_address(manager_recipient),
        manager_fee_bps,
    ).build_transaction(
        {
            "chainId": chain_id,
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "gas": 3_500_000,
            "gasPrice": w3.eth.gas_price,
        }
    )

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)

    if receipt.status != 1:
        raise RuntimeError(f"Deployment reverted: {w3.to_hex(tx_hash)}")

    print("Deployment successful")
    print(f"Contract address: {receipt.contractAddress}")
    print(f"Tx hash: {w3.to_hex(tx_hash)}")
    print(f"Chain ID: {chain_id}")


if __name__ == "__main__":
    main()
