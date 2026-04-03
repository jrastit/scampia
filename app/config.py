import os
from dataclasses import dataclass
from typing import Dict


NETWORKS: Dict[str, Dict[str, str | int]] = {
    "ethereum-mainnet": {
        "rpc_url": "https://ethereum-rpc.publicnode.com",
        "chain_id": 1,
        "safe_tx_service_base": "https://safe-transaction-mainnet.safe.global",
    },
    "ethereum-sepolia": {
        "rpc_url": "https://ethereum-sepolia-rpc.publicnode.com",
        "chain_id": 11155111,
        "safe_tx_service_base": "https://safe-transaction-sepolia.safe.global",
    },
}


def _selected_network() -> str:
    network = os.getenv("NETWORK", "ethereum-sepolia").lower()
    if network not in NETWORKS:
        supported = ", ".join(sorted(NETWORKS))
        raise ValueError(f"Unsupported NETWORK '{network}'. Supported values: {supported}")
    return network


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "Scampia API")
    network: str = _selected_network()

    rpc_url: str = os.getenv("RPC_URL", str(NETWORKS[network]["rpc_url"]))
    chain_id: int = int(os.getenv("CHAIN_ID", str(NETWORKS[network]["chain_id"])))

    # Uniswap
    uniswap_api_key: str = os.getenv("UNISWAP_API_KEY", "")
    uniswap_api_base: str = os.getenv(
        "UNISWAP_API_BASE",
        "https://trade-api.gateway.uniswap.org",
    )

    # Safe Transaction Service
    safe_tx_service_base: str = os.getenv(
        "SAFE_TX_SERVICE_BASE",
        str(NETWORKS[network]["safe_tx_service_base"]),
    )
    safe_api_key: str = os.getenv("SAFE_API_KEY", "")

    # ENS
    ens_registry_address: str = os.getenv(
        "ENS_REGISTRY_ADDRESS",
        "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e",
    )
    ens_reverse_registrar_address: str = os.getenv("ENS_REVERSE_REGISTRAR_ADDRESS", "")
    ens_public_resolver_address: str = os.getenv("ENS_PUBLIC_RESOLVER_ADDRESS", "")
    ens_parent_name: str = os.getenv("ENS_PARENT_NAME", "openclaw.eth")

    # Trading policy
    trade_allowed_tokens_in_raw: str = os.getenv("TRADE_ALLOWED_TOKENS_IN", "")
    trade_allowed_tokens_out_raw: str = os.getenv("TRADE_ALLOWED_TOKENS_OUT", "")
    trade_max_input_per_tx: int = int(os.getenv("TRADE_MAX_INPUT_PER_TX", "0"))

    # Backend signer for optional direct relay / ENS writes
    backend_private_key: str = os.getenv("BACKEND_PRIVATE_KEY", "")

    @property
    def trade_allowed_tokens_in(self) -> list[str]:
        return [token.strip() for token in self.trade_allowed_tokens_in_raw.split(",") if token.strip()]

    @property
    def trade_allowed_tokens_out(self) -> list[str]:
        return [token.strip() for token in self.trade_allowed_tokens_out_raw.split(",") if token.strip()]


settings = Settings()
