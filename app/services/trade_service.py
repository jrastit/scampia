from typing import Any, Dict, Iterable, Optional

try:
    from app.services.policy_service import PolicyService
    from app.services.safe_service import SafeService
    from app.services.simulation_service import SimulationService
    from app.services.uniswap_service import UniswapService
except ImportError:
    from policy_service import PolicyService
    from safe_service import SafeService
    from simulation_service import SimulationService
    from uniswap_service import UniswapService


class TradeService:
    def __init__(
        self,
        uniswap_service: UniswapService,
        policy_service: PolicyService,
        simulation_service: SimulationService,
        safe_service: SafeService,
    ):
        self.uniswap_service = uniswap_service
        self.policy_service = policy_service
        self.simulation_service = simulation_service
        self.safe_service = safe_service

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
        value = str(swap.get("value") or tx.get("value") or "0")

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

    def quote_trade(
        self,
        chain_id: int,
        safe_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        return self.uniswap_service.get_quote(
            chain_id=chain_id,
            wallet_address=safe_address,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            slippage_bps=slippage_bps,
        )

    def build_trade(
        self,
        chain_id: int,
        safe_address: str,
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
        recipient = recipient or safe_address
        self.policy_service.validate_trade(
            safe_address=safe_address,
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
            wallet_address=safe_address,
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
            "quoteResponse": quote_response,
            "swapResponse": swap,
            "routing": routing,
            "tx": tx,
        }

    def prepare_safe_trade(
        self,
        chain_id: int,
        safe_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
        permit_signature: Optional[str] = None,
        recipient: Optional[str] = None,
        allowed_tokens_in: Optional[Iterable[str]] = None,
        allowed_tokens_out: Optional[Iterable[str]] = None,
        max_input_per_tx: int = 0,
        operation: int = 0,
    ) -> Dict[str, Any]:
        recipient = recipient or safe_address
        self.policy_service.validate_trade(
            safe_address=safe_address,
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
            wallet_address=safe_address,
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
            raise ValueError("permit signature required for this quote")

        swap = self.uniswap_service.build_swap(
            quote=quote,
            signature=permit_signature,
            permit_data=permit_data if isinstance(permit_data, dict) else None,
        )
        tx = self._normalize_swap_tx(swap)

        simulation = self.simulation_service.simulate_call(
            from_address=safe_address,
            to=tx["to"],
            data=tx["data"],
            value=int(tx["value"]),
        )

        safe_tx = self.safe_service.build_safe_tx(
            safe_address=safe_address,
            to=tx["to"],
            data=tx["data"],
            value=tx["value"],
            operation=operation,
        )

        return {
            "policyCheck": {"ok": True},
            "quoteResponse": quote_response,
            "simulation": simulation,
            "safeTx": safe_tx,
            "swapResponse": swap,
            "routing": routing,
        }
