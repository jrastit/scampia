import os
from dataclasses import dataclass


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "Scampia API")
    rpc_url: str = os.getenv("RPC_URL", "https://mainnet.base.org")
    chain_id: int = int(os.getenv("CHAIN_ID", "8453"))

    # Uniswap
    uniswap_api_key: str = os.getenv("UNISWAP_API_KEY", "")
    # Replace with the real Trading API base URL you use from your Uniswap account/docs
    uniswap_api_base: str = os.getenv("UNISWAP_API_BASE", "https://trade-api.gateway.uniswap.org")

    # Safe Transaction Service
    safe_tx_service_base: str = os.getenv(
        "SAFE_TX_SERVICE_BASE",
        "https://safe-transaction-base.safe.global"
    )
    safe_api_key: str = os.getenv("SAFE_API_KEY", "")

    # ENS contracts / ownership wallet used by your backend for subname management
    ens_registry_address: str = os.getenv(
        "ENS_REGISTRY_ADDRESS",
        "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
    )
    
    ens_reverse_registrar_address: str = os.getenv(
    "ENS_REVERSE_REGISTRAR_ADDRESS",
    "0x0000000000D8e504002cC26E3Ec46D81971C1664"  # Base example, not universal
)
    ens_public_resolver_address: str = os.getenv("ENS_PUBLIC_RESOLVER_ADDRESS", "")
    ens_parent_name: str = os.getenv("ENS_PARENT_NAME", "openclaw.eth")

    # Backend signer for ENS writes / optional Safe relay
    backend_private_key: str = os.getenv("BACKEND_PRIVATE_KEY", "")


settings = Settings()