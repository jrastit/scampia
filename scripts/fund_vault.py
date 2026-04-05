"""
Fund the Scampia Vault.
Converts ETH → WETH → USDC via Uniswap, then deposits USDC into the vault.

Usage:
    python scripts/fund_vault.py
    python scripts/fund_vault.py 0.005   # specify ETH amount (default 0.002)
"""

import os
import sys
import yaml

import requests
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("BACKEND_PRIVATE_KEY")
UNISWAP_API_KEY = os.getenv("UNISWAP_API_KEY")
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))

WETH = "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"
USDC = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"


def load_vault_config():
    """Load vault address and vault_id from settings.yaml or env."""
    addr = os.getenv("VAULT_MANAGER_ADDRESS")
    try:
        with open("app/settings.yaml", "r") as f:
            cfg = yaml.safe_load(f)
            addr = addr or cfg.get("vault", {}).get("manager_address") or cfg.get("vault", {}).get("address")
    except:
        pass

    if not addr:
        print("❌ VAULT_MANAGER_ADDRESS not found")
        sys.exit(1)

    # Get vault_id
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    abi = [{"inputs": [], "name": "vaultCount", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
    vc = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)
    vault_id = vc.functions.vaultCount().call()

    return addr, vault_id


def main():
    eth_amount = float(sys.argv[1]) if len(sys.argv) > 1 else 0.002

    if not all([RPC_URL, PRIVATE_KEY, UNISWAP_API_KEY]):
        print("❌ Missing config in .env")
        sys.exit(1)

    vault_addr, vault_id = load_vault_config()

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = Account.from_key(PRIVATE_KEY)
    gas_price = max(w3.eth.gas_price * 3, w3.to_wei(1, "gwei"))

    print(f"\n{'='*50}")
    print(f"  Fund Vault — {eth_amount} ETH → USDC")
    print(f"  Vault: {vault_addr} (id={vault_id})")
    print(f"  Wallet: {account.address}")
    print(f"{'='*50}\n")

    def send(tx, gas=200000):
        tx["nonce"] = w3.eth.get_transaction_count(account.address, "pending")
        tx["chainId"] = CHAIN_ID
        tx.pop("maxFeePerGas", None)
        tx.pop("maxPriorityFeePerGas", None)
        tx["gasPrice"] = gas_price
        tx["gas"] = gas
        signed = account.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
        return r.status, w3.to_hex(h)

    # Check ETH balance
    eth_bal = w3.eth.get_balance(account.address)
    print(f"  ETH balance: {w3.from_wei(eth_bal, 'ether')}")
    if eth_bal < w3.to_wei(eth_amount + 0.005, "ether"):
        print(f"  ❌ Need at least {eth_amount + 0.005} ETH (amount + gas)")
        sys.exit(1)

    # 1. Wrap ETH → WETH
    print(f"\n[1] Wrapping {eth_amount} ETH → WETH...")
    weth_abi = [{"inputs": [], "name": "deposit", "outputs": [], "stateMutability": "payable", "type": "function"}]
    wc = w3.eth.contract(address=WETH, abi=weth_abi)
    s, h = send(wc.functions.deposit().build_transaction({
        "from": account.address,
        "value": w3.to_wei(eth_amount, "ether"),
    }), 100000)
    print(f"    {'✓' if s else '✗'} {h}")

    # 2. Approve WETH for Permit2
    print("\n[2] Approving WETH for Permit2...")
    approve_abi = [{"inputs": [{"name": "s", "type": "address"}, {"name": "a", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}]
    allowance_abi = [{"inputs": [{"name": "a", "type": "address"}, {"name": "b", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
    weth_c = w3.eth.contract(address=WETH, abi=approve_abi + allowance_abi)
    allowance = weth_c.functions.allowance(account.address, PERMIT2).call()
    if allowance > w3.to_wei(eth_amount, "ether"):
        print("    ✓ Already approved")
    else:
        s, h = send(weth_c.functions.approve(PERMIT2, 2**256 - 1).build_transaction({"from": account.address}), 100000)
        print(f"    {'✓' if s else '✗'} {h}")

    # 3. Swap WETH → USDC via Uniswap API
    print(f"\n[3] Swapping {eth_amount} WETH → USDC...")
    headers = {"Content-Type": "application/json", "x-api-key": UNISWAP_API_KEY}
    amount_wei = str(w3.to_wei(eth_amount, "ether"))

    quote_resp = requests.post("https://trade-api.gateway.uniswap.org/v1/quote", json={
        "type": "EXACT_INPUT", "tokenInChainId": CHAIN_ID, "tokenOutChainId": CHAIN_ID,
        "tokenIn": WETH, "tokenOut": USDC, "amount": amount_wei,
        "swapper": account.address, "recipient": account.address, "slippageTolerance": 0.5,
    }, headers=headers, timeout=30).json()

    quote = quote_resp["quote"]
    permit_data = quote_resp.get("permitData")
    expected = int(quote["output"]["amount"]) / 1e6
    print(f"    Expected: {expected} USDC")

    # Sign permit
    sig = None
    if permit_data:
        types = {k: v for k, v in permit_data["types"].items() if k != "EIP712Domain"}
        signed = account.sign_typed_data(domain_data=permit_data["domain"], message_types=types, message_data=permit_data["values"])
        sig = "0x" + signed.signature.hex()

    # Build swap
    swap_payload = {"quote": quote, "refreshGasPrice": False, "simulateTransaction": False}
    if sig:
        swap_payload["signature"] = sig
    if permit_data:
        swap_payload["permitData"] = permit_data

    swap_resp = requests.post("https://trade-api.gateway.uniswap.org/v1/swap", json=swap_payload, headers=headers, timeout=30).json()
    st = swap_resp.get("swap") or swap_resp
    to = st.get("to") or swap_resp.get("to")
    data = st.get("data") or swap_resp.get("data")
    value = st.get("value") or swap_resp.get("value") or "0"
    val = int(value, 16) if isinstance(value, str) and value.startswith("0x") else int(value)

    s, h = send({"from": account.address, "to": Web3.to_checksum_address(to), "data": data, "value": val}, 500000)
    print(f"    {'✓' if s else '✗'} Swap: {h}")

    # Check USDC balance
    usdc_abi = [{"inputs": [{"name": "a", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
    uc = w3.eth.contract(address=USDC, abi=usdc_abi)
    usdc_bal = uc.functions.balanceOf(account.address).call()
    print(f"    Got: {usdc_bal / 1e6} USDC")

    if usdc_bal == 0:
        print("    ❌ No USDC received")
        sys.exit(1)

    # 4. Approve USDC for vault
    print("\n[4] Approving USDC for vault...")
    usdc_c = w3.eth.contract(address=USDC, abi=approve_abi + allowance_abi)
    vault_cs = Web3.to_checksum_address(vault_addr)
    allowance = usdc_c.functions.allowance(account.address, vault_cs).call()
    if allowance > usdc_bal:
        print("    ✓ Already approved")
    else:
        s, h = send(usdc_c.functions.approve(vault_cs, 2**256 - 1).build_transaction({"from": account.address}), 100000)
        print(f"    {'✓' if s else '✗'} {h}")

    # 5. Deposit USDC into vault
    print(f"\n[5] Depositing {usdc_bal / 1e6} USDC into vault {vault_id}...")
    dep_abi = [{"inputs": [{"name": "v", "type": "uint256"}, {"name": "a", "type": "uint256"}, {"name": "r", "type": "address"}], "name": "deposit", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
    vc = w3.eth.contract(address=vault_cs, abi=dep_abi)
    s, h = send(vc.functions.deposit(vault_id, usdc_bal, account.address).build_transaction({"from": account.address}), 300000)
    print(f"    {'✓' if s else '✗'} {h}")

    vault_usdc = uc.functions.balanceOf(vault_cs).call()
    print(f"\n{'='*50}")
    print(f"  ✅ Vault funded: {vault_usdc / 1e6} USDC")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()