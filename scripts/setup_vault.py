"""
Complete Scampia Vault Setup.
Run this ONCE after deploying a new vault contract.

Does everything:
  1. Verify admin access
  2. Create a vault
  3. Whitelist all targets (USDC, WETH, Permit2, UniversalRouter, SwapRouter02)
  4. Approve USDC for vault manager (for user deposits)
  5. Deposit USDC if backend has some
  6. Approve tokens for Permit2 from vault (USDC + WETH)
  7. Approve Permit2 -> UniversalRouter (USDC + WETH)
  8. Approve tokens for SwapRouter02 from vault (USDC + WETH)

Usage:
    # Reads from .env or settings.yaml automatically
    python scripts/setup_vault.py

    # Or pass the vault address explicitly
    VAULT_MANAGER_ADDRESS=0x... python scripts/setup_vault.py
"""

import os
import sys
import yaml

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

# ── Config ──

# Try settings.yaml first, then .env
def load_vault_address():
    addr = os.getenv("VAULT_MANAGER_ADDRESS")
    if addr:
        return addr
    try:
        with open("app/settings.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            return cfg.get("vault", {}).get("manager_address") or cfg.get("vault", {}).get("address")
    except:
        pass
    return None

RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("BACKEND_PRIVATE_KEY")
VAULT_MANAGER = load_vault_address()
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))

# Tokens Sepolia
USDC = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
WETH = "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"
PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
UNI_ROUTER = "0x3A9D48AB9751398BbFa63ad67599Bb04e4BdF98b"       # UniversalRouter
SWAP_ROUTER_V3 = "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E"   # SwapRouter02 (V3)
MAX_UINT256 = 2**256 - 1
MAX_UINT160 = 2**160 - 1
MAX_UINT48 = 2**48 - 1

# ABIs
VAULT_ABI = [
    {"inputs": [{"name": "ownerFeeBps", "type": "uint16"}], "name": "createVault", "outputs": [{"name": "vaultId", "type": "uint256"}], "type": "function"},
    {"inputs": [], "name": "vaultCount", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"inputs": [], "name": "admin", "outputs": [{"name": "", "type": "address"}], "type": "function"},
    {"inputs": [], "name": "asset", "outputs": [{"name": "", "type": "address"}], "type": "function"},
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

PERMIT2_ABI = [
    {"inputs": [{"name": "token", "type": "address"}, {"name": "spender", "type": "address"}, {"name": "amount", "type": "uint160"}, {"name": "expiration", "type": "uint48"}], "name": "approve", "outputs": [], "type": "function"},
]


class VaultSetup:
    def __init__(self):
        if not all([RPC_URL, PRIVATE_KEY, VAULT_MANAGER]):
            print("❌ Missing config. Need: RPC_URL, BACKEND_PRIVATE_KEY, VAULT_MANAGER_ADDRESS")
            print(f"   RPC_URL: {'✓' if RPC_URL else '✗'}")
            print(f"   BACKEND_PRIVATE_KEY: {'✓' if PRIVATE_KEY else '✗'}")
            print(f"   VAULT_MANAGER_ADDRESS: {'✓' if VAULT_MANAGER else '✗'}")
            sys.exit(1)

        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.account = Account.from_key(PRIVATE_KEY)
        self.vault_addr = Web3.to_checksum_address(VAULT_MANAGER)
        self.vc = self.w3.eth.contract(address=self.vault_addr, abi=VAULT_ABI)
        self.vault_id = None
    

    def send(self, tx, gas=200000):
        tx["nonce"] = self.w3.eth.get_transaction_count(self.account.address, "pending")
        tx["chainId"] = CHAIN_ID
        tx.pop("maxFeePerGas", None)
        tx.pop("maxPriorityFeePerGas", None)
        tx["gasPrice"] = max(self.w3.eth.gas_price * 3, self.w3.to_wei(1, "gwei"))
        tx["gas"] = gas
        signed = self.account.sign_transaction(tx)
        h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        r = self.w3.eth.wait_for_transaction_receipt(h, timeout=120)
        return r.status, self.w3.to_hex(h)
    

    def step_verify_admin(self):
        print("[0] Verifying admin...")
        admin = self.vc.functions.admin().call()
        asset = self.vc.functions.asset().call()
        if admin.lower() != self.account.address.lower():
            print(f"   ❌ Backend ({self.account.address}) is NOT admin ({admin})")
            sys.exit(1)
        print(f"   ✓ Admin: {admin}")
        print(f"   ✓ Asset: {asset}")

    def step_create_vault(self):
        print("\n[1] Creating vault...")
        count = self.vc.functions.vaultCount().call()
        if count > 0:
            self.vault_id = count  # Use last vault
            print(f"   ✓ Vault already exists (count={count}), using vault_id={self.vault_id}")
        else:
            s, h = self.send(self.vc.functions.createVault(500).build_transaction({"from": self.account.address}))
            self.vault_id = self.vc.functions.vaultCount().call()
            print(f"   {'✓' if s else '✗'} Created vault_id={self.vault_id} ({h})")

    def step_whitelist_targets(self):
        print("\n[2] Whitelisting targets...")
        targets = [
            ("USDC", USDC),
            ("WETH", WETH),
            ("Permit2", PERMIT2),
            ("UniversalRouter", UNI_ROUTER),
            ("SwapRouter02", SWAP_ROUTER_V3),
        ]
        for name, addr in targets:
            cs = Web3.to_checksum_address(addr)
            if self.vc.functions.allowedTargets(cs).call():
                print(f"   ✓ {name} already whitelisted")
            else:
                s, h = self.send(self.vc.functions.setAllowedTarget(cs, True).build_transaction({"from": self.account.address}), 100000)
                print(f"   {'✓' if s else '✗'} {name} ({h})")

    def step_approve_usdc_for_deposits(self):
        print("\n[3] Approving USDC for vault (deposits)...")
        usdc_c = self.w3.eth.contract(address=USDC, abi=ERC20_ABI)
        allowance = usdc_c.functions.allowance(self.account.address, self.vault_addr).call()
        if allowance > 10**18:
            print("   ✓ Already approved")
        else:
            s, h = self.send(usdc_c.functions.approve(self.vault_addr, MAX_UINT256).build_transaction({"from": self.account.address}), 100000)
            print(f"   {'✓' if s else '✗'} Approved ({h})")

    def step_deposit_usdc(self):
        print("\n[4] Depositing USDC into vault...")
        usdc_c = self.w3.eth.contract(address=USDC, abi=ERC20_ABI)
        vault_balance = usdc_c.functions.balanceOf(self.vault_addr).call()
        backend_balance = usdc_c.functions.balanceOf(self.account.address).call()
        print(f"   Vault USDC: {vault_balance / 1e6}")
        print(f"   Backend USDC: {backend_balance / 1e6}")

        if vault_balance >= 1_000_000:
            print(f"   ✓ Vault already has {vault_balance / 1e6} USDC")
        elif backend_balance > 0:
            deposit = min(backend_balance, 5_000_000)
            s, h = self.send(self.vc.functions.deposit(self.vault_id, deposit, self.account.address).build_transaction({"from": self.account.address}), 300000)
            print(f"   {'✓' if s else '✗'} Deposited {deposit / 1e6} USDC ({h})")
        else:
            print("   ⚠ No USDC available. Users will deposit via the frontend.")

    def _approve_from_vault(self, name, token, spender):
        """Approve a token for a spender FROM the vault via executeTrade."""
        tc = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
        allowance = tc.functions.allowance(self.vault_addr, Web3.to_checksum_address(spender)).call()
        if allowance > 10**18:
            print(f"   ✓ {name} already approved")
            return
        approve_data = tc.encode_abi("approve", args=[Web3.to_checksum_address(spender), MAX_UINT256])
        s, h = self.send(
            self.vc.functions.executeTrade(self.vault_id, token, 0, bytes.fromhex(approve_data[2:]), 0).build_transaction({"from": self.account.address})
        )
        print(f"   {'✓' if s else '✗'} {name} ({h})")

    def step_approve_permit2(self):
        print("\n[5] Approving tokens for Permit2 from vault...")
        for name, token in [("USDC→Permit2", USDC), ("WETH→Permit2", WETH)]:
            self._approve_from_vault(name, token, PERMIT2)

    def step_approve_permit2_router(self):
        print("\n[6] Approving Permit2 → UniversalRouter...")
        p2 = self.w3.eth.contract(address=PERMIT2, abi=PERMIT2_ABI)
        for name, token in [("USDC", USDC), ("WETH", WETH)]:
            permit2_data = p2.encode_abi("approve", args=[
                Web3.to_checksum_address(token),
                Web3.to_checksum_address(UNI_ROUTER),
                MAX_UINT160,
                MAX_UINT48,
            ])
            try:
                s, h = self.send(
                    self.vc.functions.executeTrade(self.vault_id, PERMIT2, 0, bytes.fromhex(permit2_data[2:]), 0).build_transaction({"from": self.account.address})
                )
                print(f"   {'✓' if s else '✗'} {name} ({h})")
            except Exception as e:
                print(f"   ✗ {name}: {e}")

    def step_approve_swap_router_v3(self):
        print("\n[7] Approving tokens for SwapRouter02 (V3) from vault...")
        for name, token in [("USDC→SwapRouter02", USDC), ("WETH→SwapRouter02", WETH)]:
            self._approve_from_vault(name, token, SWAP_ROUTER_V3)

    def step_summary(self):
        usdc_c = self.w3.eth.contract(address=USDC, abi=ERC20_ABI)
        vault_usdc = usdc_c.functions.balanceOf(self.vault_addr).call()

        print(f"\n{'='*60}")
        print(f"  ✅ SETUP COMPLETE")
        print(f"  Vault Manager:  {self.vault_addr}")
        print(f"  Vault ID:       {self.vault_id}")
        print(f"  Vault USDC:     {vault_usdc / 1e6}")
        print(f"  Admin:          {self.account.address}")
        print(f"")
        print(f"  Test swap:")
        print(f"  curl -s -X POST http://localhost:8000/v1/trades/execute-vault-swap \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"chain_id\":{CHAIN_ID},\"token_in\":\"{USDC}\",\"token_out\":\"{WETH}\",\"amount_in\":\"500000\",\"slippage_bps\":50,\"vault_id\":{self.vault_id}}}'")
        print(f"{'='*60}\n")

    def run(self):
        print(f"\n{'='*60}")
        print(f"  Scampia Vault Setup — {'Sepolia' if CHAIN_ID == 11155111 else f'Chain {CHAIN_ID}'}")
        print(f"  Vault: {self.vault_addr}")
        print(f"  Admin: {self.account.address}")
        print(f"{'='*60}")

        self.step_verify_admin()
        self.step_create_vault()
        self.step_whitelist_targets()
        self.step_approve_usdc_for_deposits()
        self.step_deposit_usdc()
        self.step_approve_permit2()
        self.step_approve_permit2_router()
        self.step_approve_swap_router_v3()
        self.step_summary()


if __name__ == "__main__":
    VaultSetup().run()