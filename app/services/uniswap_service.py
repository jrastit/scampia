from typing import Any, Dict

import requests

try:
    from app.config import settings
except ImportError:
    from config import settings


class UniswapService:
    def __init__(self):
        self.base_url = settings.uniswap_api_base.rstrip("/")
        self.api_key = settings.uniswap_api_key

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def get_quote(
        self,
        chain_id: int,
        wallet_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/quote"
        payload = {
            "type": "EXACT_INPUT",
            "tokenInChainId": chain_id,
            "tokenOutChainId": chain_id,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amount": amount_in,
            "swapper": wallet_address,
            "recipient": wallet_address,
            "slippageTolerance": slippage_bps,
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def build_swap(
        self,
        chain_id: int,
        wallet_address: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/swap"
        payload = {
            "type": "EXACT_INPUT",
            "tokenInChainId": chain_id,
            "tokenOutChainId": chain_id,
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amount": amount_in,
            "swapper": wallet_address,
            "recipient": wallet_address,
            "slippageTolerance": slippage_bps,
            "generatePermitAsTransaction": False,
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()
