from typing import Any, Dict, Iterable, Optional

from app.data import user_data

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

        key = settings.backend_private_key
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
        if self.policy_service.validate_parameters():
            self.policy_service.validate_trade(
                safe_address=wallet_address,
                recipient=recipient,
                token_in=token_in,
                token_out=token_out,
                amount_in=int(amount_in),
                allowed_tokens_in=allowed_tokens_in or [],
                allowed_tokens_out=allowed_tokens_out or [],
                max_input_per_tx=max_input_per_tx,
            )

            swap = self.uniswap_service.build_swap(
                chain_id=chain_id,
                wallet_address=wallet_address,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                slippage_bps=slippage_bps,
            )
            tx = self._normalize_swap_tx(swap)
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
                "quoteOrSwapResponse": swap,
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
        user_id: int,
        slippage_bps: int = 50,
        permit_signature: Optional[str] = None,
        recipient: Optional[str] = None,
        allowed_tokens_in: Optional[Iterable[str]] = None,
        allowed_tokens_out: Optional[Iterable[str]] = None,
        max_input_per_tx: int = 0,
    ) -> Dict[str, Any]:
        recipient = recipient or wallet_address
        if self.policy_service.validate_parameters(amount_in,token_in,token_out):
            self.policy_service.validate_trade(
                safe_address=wallet_address,
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
            raise ValueError("prepare-safe-tx only supports swap routes (CLASSIC/WRAP/UNWRAP/BRIDGE)")

        if permit_data is not None and not permit_signature:
            permit_signature = self._sign_permit(permit_data)

        swap = self.uniswap_service.build_swap(
            quote=quote,
            signature=permit_signature,
            permit_data=permit_data if isinstance(permit_data, dict) else None,
        )
        tx = self._normalize_swap_tx(swap)

        simulation = self.simulation_service.simulate_call(
            from_address=wallet_address,
            to=tx["to"],
            data=tx["data"],
            value=int(tx["value"]),
        )

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
            "simulation": simulation,
            "vaultTx": vault_tx,
            "swapResponse": swap,
            "routing": routing,
        }
    

    def prepare_safe_trade(self, *args, **kwargs) -> Dict[str, Any]:
        return self.prepare_vault_trade(*args, **kwargs)

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

        # Quote
        quote_response = self.uniswap_service.get_quote(
            chain_id=chain_id,
            wallet_address=wallet_address,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            slippage_bps=slippage_bps,
        )

        quote = quote_response.get("quote")
        permit_data = quote_response.get("permitData")
        routing = str(quote_response.get("routing") or "")

        if not isinstance(quote, dict):
            raise ValueError("quote response missing quote payload")

        # Auto-sign permit
        if permit_data and not permit_signature:
            permit_signature = self._sign_permit(permit_data)

        # Build swap
        swap = self.uniswap_service.build_swap(
            quote=quote,
            signature=permit_signature,
            permit_data=permit_data if isinstance(permit_data, dict) else None,
        )
        normalized = self._normalize_swap_tx(swap)

        # Execute via Vault (skip simulation)
        execution = self.vault_service.execute_agent_swap(
            vault_id=vault_id,
            target=normalized["to"],
            data=normalized["data"],
            min_asset_delta=0,
            value=int(normalized["value"]),
        )

        return {
            "quoteResponse": quote_response,
            "routing": routing,
            "execution": execution,
        }