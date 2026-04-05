"""
Setup script for Scampia Vault.
Creates vault, whitelists targets, approves Permit2, deposits USDC.

Usage:
    python scripts/setup_vault.py
"""

import os
import sys

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("BACKEND_PRIVATE_KEY")
VAULT_MANAGER = os.getenv("VAULT_MANAGER_ADDRESS")
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))

USDC = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
WETH = "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"
PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
UNI_ROUTER = "0x3A9D48AB9751398BbFa63ad67599Bb04e4BdF98b"
MAX_UINT = 2**256 - 1

VAULT_ABI = [
    {"inputs": [{"name": "ownerFeeBps", "type": "uint16"}], "name": "createVault", "outputs": [{"name": "vaultId", "type": "uint256"}], "type": "function"},
    {"inputs": [], "name": "vaultCount", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"inputs": [], "name": "admin", "outputs": [{"name": "", "type": "address"}], "type": "function"},
    {"inputs": [{"name": "t", "type": "address"}, {"name": "b", "type": "bool"}], "name": "setAllowedTarget", "outputs": [], "type": "function"},
    {"inputs": [{"name": "t", "type": "address"}], "name": "allowedTargets", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"inputs": [{"name": "vaultId", "type": "uint256"}, {"name": "assets", "type": "uint256"}, {"name": "receiver", "type": "address"}], "name": "deposit", "outputs": [{"name": "mintedShares", "type": "uint256"}], "type": "function"},
    {"inputs": [{"name": "vaultId", "type": "uint256"}, {"name": "target", "type": "address"}, {"name": "value", "type": "uint256"}, {"name": "data", "type": "bytes"}, {"name": "minAssetDelta", "type": "int256"}], "name": "executeTrade", "outputs": [{"name": "assetDelta", "type": "int256"}], "type": "function"},
]

ERC20_ABI = [
    {"inputs": [{"name": "a", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"inputs": [{"name": "s", "type": "address"}, {"name": "a", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"inputs": [{"name": "a", "type": "address"}, {"name": "b", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]


def send_tx(w3, account, tx):
    tx["nonce"] = w3.eth.get_transaction_count(account.address, "pending")
    tx["chainId"] = CHAIN_ID
    if "gasPrice" not in tx and "maxFeePerGas" not in tx:
        base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
        tx["maxFeePerGas"] = base_fee * 3
        tx["maxPriorityFeePerGas"] = w3.to_wei(1, "gwei")
    if "gas" not in tx:
        tx["gas"] = 300_000
    signed = account.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
    return w3.to_hex(h), r.status


def main():
    if not all([RPC_URL, PRIVATE_KEY, VAULT_MANAGER]):
        print("❌ Set RPC_URL, BACKEND_PRIVATE_KEY, VAULT_MANAGER_ADDRESS")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = Account.from_key(PRIVATE_KEY)
    vault_addr = Web3.to_checksum_address(VAULT_MANAGER)

    vc = w3.eth.contract(address=vault_addr, abi=VAULT_ABI)
    usdc_c = w3.eth.contract(address=USDC, abi=ERC20_ABI)

    print(f"\n{'='*60}")
    print(f"  Scampia Vault Setup — Sepolia")
    print(f"  Vault Manager: {vault_addr}")
    print(f"  Admin: {account.address}")
    print(f"{'='*60}\n")

    admin = vc.functions.admin().call()
    if admin.lower() != account.address.lower():
        print(f"❌ Backend ({account.address}) is NOT admin ({admin})")
        sys.exit(1)
    print(f"  ✓ Admin verified")

    # ── 1. Create vault if needed ──
    vault_count = vc.functions.vaultCount().call()
    print(f"\n[1] Vault count: {vault_count}")
    if vault_count == 0:
        print("  Creating vault...")
        tx = vc.functions.createVault(500).build_transaction({"from": account.address})
        h, s = send_tx(w3, account, tx)
        print(f"  {'✓' if s else '✗'} Create vault: {h}")
        vault_count = vc.functions.vaultCount().call()
    vault_id = vault_count
    print(f"  Using vault_id={vault_id}")

    # ── 2. Whitelist targets ──
    print(f"\n[2] Whitelisting targets...")
    targets = [("USDC", USDC), ("WETH", WETH), ("Permit2", PERMIT2), ("Uni Router", UNI_ROUTER)]
    for name, addr in targets:
        if vc.functions.allowedTargets(Web3.to_checksum_address(addr)).call():
            print(f"  ✓ {name} already whitelisted")
        else:
            tx = vc.functions.setAllowedTarget(Web3.to_checksum_address(addr), True).build_transaction({"from": account.address})
            h, s = send_tx(w3, account, tx)
            print(f"  {'✓' if s else '✗'} {name}: {h}")

    # ── 3. Approve USDC for vault manager ──
    print(f"\n[3] Approving USDC for vault manager...")
    if usdc_c.functions.allowance(account.address, vault_addr).call() > 0:
        print(f"  ✓ Already approved")
    else:
        tx = usdc_c.functions.approve(vault_addr, MAX_UINT).build_transaction({"from": account.address})
        h, s = send_tx(w3, account, tx)
        print(f"  {'✓' if s else '✗'} Approve: {h}")

    # ── 4. Deposit USDC ──
    usdc_balance = usdc_c.functions.balanceOf(account.address).call()
    vault_usdc = usdc_c.functions.balanceOf(vault_addr).call()
    print(f"\n[4] Deposit USDC...")
    print(f"  Backend USDC: {usdc_balance / 1e6}")
    print(f"  Vault USDC: {vault_usdc / 1e6}")
    if vault_usdc >= 1_000_000:
        print(f"  ✓ Vault already has {vault_usdc / 1e6} USDC")
    elif usdc_balance > 0:
        deposit_amount = min(usdc_balance, 5_000_000)
        print(f"  Depositing {deposit_amount / 1e6} USDC...")
        tx = vc.functions.deposit(vault_id, deposit_amount, account.address).build_transaction({"from": account.address})
        h, s = send_tx(w3, account, tx)
        print(f"  {'✓' if s else '✗'} Deposit: {h}")
    else:
        print(f"  ⚠ No USDC to deposit")

    # ── 5. Approve USDC for Permit2 from vault ──
    print(f"\n[5] Approving USDC for Permit2 from vault...")
    if usdc_c.functions.allowance(vault_addr, PERMIT2).call() > 0:
        print(f"  ✓ Already approved")
    else:
        approve_data = usdc_c.encode_abi("approve", args=[Web3.to_checksum_address(PERMIT2), MAX_UINT])
        tx = vc.functions.executeTrade(vault_id, USDC, 0, bytes.fromhex(approve_data[2:]), 0).build_transaction({"from": account.address})
        h, s = send_tx(w3, account, tx)
        print(f"  {'✓' if s else '✗'} Approve Permit2: {h}")

    # ── Done ──
    vault_usdc_final = usdc_c.functions.balanceOf(vault_addr).call()
    permit2_ok = usdc_c.functions.allowance(vault_addr, PERMIT2).call() > 0
    print(f"\n{'='*60}")
    print(f"  ✅ SETUP COMPLETE")
    print(f"  Vault Manager: {vault_addr}")
    print(f"  Vault ID: {vault_id}")
    print(f"  Vault USDC: {vault_usdc_final / 1e6}")
    print(f"  Permit2 approved: {'✓' if permit2_ok else '✗'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()