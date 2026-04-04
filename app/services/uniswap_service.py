import random
import time
from typing import Any, Dict, Optional

import requests

try:
    from app.config import settings
except ImportError:
    from config import settings


class UniswapService:
    def __init__(self):
        configured_base = settings.uniswap_api_base.rstrip("/")
        # Accept both .../v1 and ... forms in config without duplicating the version segment.
        if configured_base.endswith("/v1"):
            configured_base = configured_base[:-3]
        self.base_url = configured_base
        self.api_key = settings.uniswap_api_key
        self.max_retries = 3
        self.backoff_base_seconds = 0.5

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _api_url(self, path: str) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}/v1{normalized_path}"

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = self._api_url(path)
        last_response = None

        for attempt in range(self.max_retries + 1):
            response = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            last_response = response

            if response.status_code != 429:
                response.raise_for_status()
                return response.json()

            if attempt == self.max_retries:
                break

            # Exponential backoff with small jitter for bursty rate limits.
            sleep_for = self.backoff_base_seconds * (2**attempt) + random.uniform(0, 0.2)
            time.sleep(sleep_for)

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("Uniswap API request failed without a response")

    @staticmethod
    def _slippage_percent_from_bps(slippage_bps: int) -> float:
        return round(slippage_bps / 100, 2)

    def check_approval(
        self,
        chain_id: int,
        wallet_address: str,
        token: str,
        amount: str,
        token_out: Optional[str] = None,
        token_out_chain_id: Optional[int] = None,
        include_gas_info: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "walletAddress": wallet_address,
            "token": token,
            "amount": amount,
            "chainId": chain_id,
            "includeGasInfo": include_gas_info,
        }
        if token_out:
            payload["tokenOut"] = token_out
        if token_out_chain_id is not None:
            payload["tokenOutChainId"] = token_out_chain_id
        return self._post("/check_approval", payload)

    def get_quote(
        self,
        chain_id: int,
        wallet_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        payload = {
            "type": "EXACT_INPUT",
            "tokenInChainId": chain_id,
            "tokenOutChainId": chain_id,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amount": amount_in,
            "swapper": wallet_address,
            "recipient": wallet_address,
            "slippageTolerance": self._slippage_percent_from_bps(slippage_bps),
            "generatePermitAsTransaction": False,
        }

        return self._post("/quote", payload)

    def build_swap(
        self,
        quote: Dict[str, Any],
        signature: Optional[str] = None,
        permit_data: Optional[Dict[str, Any]] = None,
        simulate_transaction: bool = False,
        refresh_gas_price: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "quote": quote,
            "refreshGasPrice": refresh_gas_price,
            "simulateTransaction": simulate_transaction,
        }
        if signature:
            payload["signature"] = signature
        if permit_data is not None:
            payload["permitData"] = permit_data
        return self._post("/swap", payload)

    def build_order(
        self,
        quote: Dict[str, Any],
        routing: str,
        signature: str,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "quote": quote,
            "routing": routing,
            "signature": signature,
        }
        return self._post("/order", payload)
