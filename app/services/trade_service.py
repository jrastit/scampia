from typing import Any, Dict, Iterable, Optional

from web3 import Web3

try:
    from app.config import settings
    from app.services.policy_service import PolicyService
    from app.services.simulation_service import SimulationService
    from app.services.uniswap_service import UniswapService
    from app.services.vault_service import VaultService
except ImportError:
    from config import settings
    from policy_service import PolicyService
    from simulation_service import SimulationService
    from uniswap_service import UniswapService
    from vault_service import VaultService

# SwapRouter02 (V3) — uses simple ERC20 approve, no Permit2
SWAP_ROUTER_V3 = "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E"

SWAP_ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "recipient", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMinimum", "type": "uint256"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "type": "function",
    }
]

ERC20_APPROVE_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    }
]

ERC20_ALLOWANCE_ABI = [
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    }
]


class TradeService:
    def __init__(
        self,
        uniswap_service: UniswapService,
        policy_service: PolicyService,
        simulation_service: SimulationService,
        vault_service: VaultService,
    ):
        self.uniswap_service = uniswap_service
        self.policy_service = policy_service
        self.simulation_service = simulation_service
        self.vault_service = vault_service

    @staticmethod
    def _normalize_swap_tx(swap: Dict[str, Any]) -> Dict[str, str]:
        tx = (
            swap.get("swap", {})
            if isinstance(swap.get("swap"), dict)
            else swap.get("tx", {})
            if isinstance(swap.get("tx"), dict)
            else {}
        )
        to = swap.get("to") or tx.get("to")
        data = swap.get("data") if "data" in swap else tx.get("data")
        raw_value = swap.get("value") or tx.get("value") or "0"
        if isinstance(raw_value, str) and raw_value.startswith("0x"):
            value = str(int(raw_value, 16))
        else:
            value = str(raw_value)

        if not to:
            raise ValueError("swap response missing destination address")
        if not isinstance(data, str) or not data.strip():
            raise ValueError("swap response missing calldata")

        return {"to": to, "data": data, "value": value}

    @staticmethod
    def _route_family(routing: str) -> str:
        normalized = (routing or "").upper()
        if normalized in {"CLASSIC", "WRAP", "UNWRAP", "BRIDGE", "CHAINED"}:
            return "swap"
        if normalized in {"DUTCH_V2", "DUTCH_V3", "PRIORITY", "DUTCH_LIMIT", "LIMIT_ORDER"}:
            return "order"
        raise ValueError(f"unsupported routing from quote: {routing}")

    @staticmethod
    def _sign_permit(permit_data: dict) -> str:
        from eth_account import Account

        key = getattr(settings, "admin_private_key", None) or settings.backend_private_key
        account = Account.from_key(key)
        domain = permit_data["domain"]
        types = {k: v for k, v in permit_data["types"].items() if k != "EIP712Domain"}
        values = permit_data["values"]

        signed = account.sign_typed_data(
            domain_data=domain,
            message_types=types,
            message_data=values,
        )
        return "0x" + signed.signature.hex()

    def quote_trade(
        self,
        chain_id: int,
        wallet_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        return self.uniswap_service.get_quote(
            chain_id=chain_id,
            wallet_address=wallet_address,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            slippage_bps=slippage_bps,
        )

    def build_trade(
        self,
        chain_id: int,
        wallet_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
        permit_signature: Optional[str] = None,
        recipient: Optional[str] = None,
        allowed_tokens_in: Optional[Iterable[str]] = None,
        allowed_tokens_out: Optional[Iterable[str]] = None,
        max_input_per_tx: int = 0,
    ) -> Dict[str, Any]:
        recipient = recipient or wallet_address
        self.policy_service.validate_trade(
            vault_address=wallet_address,
            recipient=recipient,
            token_in=token_in,
            token_out=token_out,
            amount_in=int(amount_in),
            allowed_tokens_in=allowed_tokens_in or [],
            allowed_tokens_out=allowed_tokens_out or [],
            max_input_per_tx=max_input_per_tx,
        )

        quote_response = self.uniswap_service.get_quote(
            chain_id=chain_id,
            wallet_address=wallet_address,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            slippage_bps=slippage_bps,
        )
        routing = str(quote_response.get("routing") or "")
        quote = quote_response.get("quote")
        permit_data = quote_response.get("permitData")

        if not isinstance(quote, dict):
            raise ValueError("quote response missing quote payload")

        route_family = self._route_family(routing)
        if (permit_data is not None or route_family == "order") and not permit_signature:
            permit_signature = self._sign_permit(permit_data) if permit_data else None
            if route_family == "order" and not permit_signature:
                raise ValueError("permit signature required for this routing")

        if route_family == "order":
            order = self.uniswap_service.build_order(
                quote=quote,
                routing=routing,
                signature=str(permit_signature),
            )
            return {
                "policyCheck": {"ok": True},
                "quoteResponse": quote_response,
                "orderResponse": order,
                "routing": routing,
            }

        swap = self.uniswap_service.build_swap(
            quote=quote,
            signature=permit_signature,
            permit_data=permit_data if isinstance(permit_data, dict) else None,
        )
        tx = self._normalize_swap_tx(swap)

        return {
            "policyCheck": {"ok": True},
            "quoteResponse": quote_response,
            "swapResponse": swap,
            "routing": routing,
            "tx": tx,
        }

    def prepare_vault_trade(
        self,
        chain_id: int,
        vault_id: int,
        wallet_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
        permit_signature: Optional[str] = None,
        recipient: Optional[str] = None,
        allowed_tokens_in: Optional[Iterable[str]] = None,
        allowed_tokens_out: Optional[Iterable[str]] = None,
        max_input_per_tx: int = 0,
    ) -> Dict[str, Any]:
        recipient = recipient or wallet_address
        self.policy_service.validate_trade(
            vault_address=wallet_address,
            recipient=recipient,
            token_in=token_in,
            token_out=token_out,
            amount_in=int(amount_in),
            allowed_tokens_in=allowed_tokens_in or [],
            allowed_tokens_out=allowed_tokens_out or [],
            max_input_per_tx=max_input_per_tx,
        )

        quote_response = self.uniswap_service.get_quote(
            chain_id=chain_id,
            wallet_address=wallet_address,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            slippage_bps=slippage_bps,
        )
        routing = str(quote_response.get("routing") or "")
        quote = quote_response.get("quote")
        permit_data = quote_response.get("permitData")

        if not isinstance(quote, dict):
            raise ValueError("quote response missing quote payload")

        route_family = self._route_family(routing)
        if route_family != "swap":
            raise ValueError("prepare-vault-tx only supports swap routes")

        if permit_data is not None and not permit_signature:
            permit_signature = self._sign_permit(permit_data)

        swap = self.uniswap_service.build_swap(
            quote=quote,
            signature=permit_signature,
            permit_data=permit_data if isinstance(permit_data, dict) else None,
        )
        tx = self._normalize_swap_tx(swap)

        vault_tx = self.vault_service.build_agent_swap_tx(
            vault_id=vault_id,
            target=tx["to"],
            data=tx["data"],
            min_asset_delta=0,
            value=int(tx["value"]),
        )

        return {
            "policyCheck": {"ok": True},
            "quoteResponse": quote_response,
            "vaultTx": vault_tx,
            "swapResponse": swap,
            "routing": routing,
        }

    def prepare_safe_trade(self, *args, **kwargs) -> Dict[str, Any]:
        return self.prepare_vault_trade(*args, **kwargs)

    # ── Vault swap via SwapRouter02 (V3) ──

    def execute_vault_swap(
        self,
        chain_id: int,
        vault_id: int,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
        permit_signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        wallet_address = settings.vault_manager_address
        if not wallet_address:
            raise ValueError("VAULT_MANAGER_ADDRESS required")

        w3 = self.vault_service.w3
        vault_addr = Web3.to_checksum_address(wallet_address)
        token_in_cs = Web3.to_checksum_address(token_in)
        token_out_cs = Web3.to_checksum_address(token_out)
        router = Web3.to_checksum_address(SWAP_ROUTER_V3)

        # 1. Get quote from Uniswap API (for pricing + fee info)
        quote_response = self.uniswap_service.get_quote(
            chain_id=chain_id,
            wallet_address=wallet_address,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            slippage_bps=slippage_bps,
        )

        quote = quote_response.get("quote")
        routing = str(quote_response.get("routing") or "")

        if not isinstance(quote, dict):
            raise ValueError("quote response missing quote payload")

        # Extract fee and min output from quote
        fee = 3000  # default
        route = quote.get("route", [[]])
        if route and route[0]:
            pool = route[0][0]
            fee = int(pool.get("fee", 3000))

        amount_out = quote.get("output", {}).get("amount", "0")
        min_amount_out = 0  # V3 pool may give different price than V4 quote

        # 2. Auto-approve token_in for SwapRouter02 if needed
        self._ensure_vault_approval_v3(vault_id, token_in_cs, router, int(amount_in))

        # 3. Build exactInputSingle calldata for SwapRouter02
        rc = w3.eth.contract(address=router, abi=SWAP_ROUTER_ABI)
        swap_data = rc.encode_abi("exactInputSingle", args=[(
            token_in_cs,
            token_out_cs,
            fee,
            vault_addr,         # recipient = vault gets the output tokens
            int(amount_in),
            min_amount_out,
            0,                  # sqrtPriceLimitX96 = no limit
        )])

        # 4. Execute via vault's executeTrade
        execution = self.vault_service.execute_agent_swap(
            vault_id=vault_id,
            target=router,
            data=swap_data,
            min_asset_delta=-int(amount_in),
            value=0,
        )

        # Wait for confirmation
        tx_hash = execution.get("txHash")
        status = "success"
        if tx_hash:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            status = "success" if receipt.status == 1 else "failed"

        return {
            "status": status,
            "txHash": execution.get("txHash"),
            "etherscanUrl": f"https://sepolia.etherscan.io/tx/{execution.get('txHash')}",
            "quoteResponse": quote_response,
            "routing": routing,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountIn": amount_in,
            "expectedAmountOut": amount_out,
            "minAmountOut": str(min_amount_out),
            "fee": fee,
            "vaultId": vault_id,
            "execution": execution,
        }

    def _ensure_vault_approval_v3(self, vault_id: int, token: str, spender: str, amount: int):
        """Approve token for SwapRouter02 from vault if allowance insufficient."""
        w3 = self.vault_service.w3
        vault_addr = self.vault_service.manager_contract_address()

        tc = w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ALLOWANCE_ABI)
        allowance = tc.functions.allowance(vault_addr, Web3.to_checksum_address(spender)).call()

        if allowance >= amount:
            return

        approve_c = w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_APPROVE_ABI)
        approve_data = approve_c.encode_abi("approve", args=[Web3.to_checksum_address(spender), 2**256 - 1])

        result = self.vault_service.execute_agent_swap(
            vault_id=vault_id,
            target=token,
            data=approve_data,
            min_asset_delta=0,
            value=0,
        )
        # Wait for approval to confirm before swapping
        tx_hash = result.get("txHash")
        if tx_hash:
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)