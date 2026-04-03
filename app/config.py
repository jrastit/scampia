"""
Configuration.

Shared config  → settings.yaml (committed in the repo)
Secrets        → .env          (never committed, only BACKEND_PRIVATE_KEY)

settings.yaml values are loaded first, then .env secrets are layered on top.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_yaml_path = Path(__file__).resolve().parent.parent / "settings.yaml"
_cfg: dict = {}
if _yaml_path.exists():
    with open(_yaml_path) as f:
        _cfg = yaml.safe_load(f) or {}


def _get(yaml_keys: list[str], env_key: str = "", default=""):
    """Read from YAML first, then env var, then default."""
    # Walk into nested YAML
    val = _cfg
    for k in yaml_keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            val = None
            break
    if val is not None:
        return val
    if env_key:
        return os.getenv(env_key, default)
    return default


@dataclass
class Settings:
    # ── App ──
    app_name: str = _get(["app", "name"], "APP_NAME", "Scampia API")

    # ── Chain ──
    chain_id: int = int(_get(["chain", "id"], "CHAIN_ID", "11155111"))
    rpc_url: str = _get(["chain", "rpc_url"], "RPC_URL", "https://rpc.sepolia.org")

    # ── Safe ──
    safe_address: str = _get(["safe", "address"], "SAFE_ADDRESS", "")
    safe_tx_service_base: str = _get(
        ["safe", "tx_service"],
        "SAFE_TX_SERVICE_BASE",
        "https://safe-transaction-sepolia.safe.global",
    )
    safe_api_key: str = os.getenv("SAFE_API_KEY", "")

    # ── Tokens ──
    usdc_address: str = _get(
        ["tokens", "usdc"], "USDC_ADDRESS",
        "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    )
    weth_address: str = _get(
        ["tokens", "weth"], "WETH_ADDRESS",
        "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14",
    )

    # ── Uniswap ──
    uniswap_api_key: str = os.getenv("UNISWAP_API_KEY", "")
    uniswap_api_base: str = _get(
        ["uniswap", "api_base"], "UNISWAP_API_BASE",
        "https://trade-api.gateway.uniswap.org",
    )
    uniswap_swap_router: str = _get(
        ["uniswap", "swap_router"], "UNISWAP_SWAP_ROUTER",
        "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E",
    )
    uniswap_factory: str = _get(
        ["uniswap", "factory"], "UNISWAP_FACTORY",
        "0x0227628f3F023bb0B980b67D528571c95c6DaC1c",
    )
    uniswap_quoter: str = _get(
        ["uniswap", "quoter"], "UNISWAP_QUOTER",
        "0xEd1f6473345F45b75F8179591dd5bA1888cf2FB3",
    )

    # ── ENS ──
    ens_registry_address: str = _get(
        ["ens", "registry"], "ENS_REGISTRY_ADDRESS",
        "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e",
    )
    ens_public_resolver_address: str = os.getenv("ENS_PUBLIC_RESOLVER_ADDRESS", "")
    ens_parent_name: str = _get(
        ["ens", "parent_name"], "ENS_PARENT_NAME", "openclaw.eth",
    )

    # ── Secret (from .env ONLY) ──
    backend_private_key: str = os.getenv("BACKEND_PRIVATE_KEY", "")

    # ── Policy defaults ──
    @property
    def default_allowed_tokens_in(self) -> list[str]:
        return _get(["policy", "allowed_tokens_in"], default=[]) or [self.usdc_address]

    @property
    def default_allowed_tokens_out(self) -> list[str]:
        return _get(["policy", "allowed_tokens_out"], default=[]) or [self.weth_address]

    @property
    def default_allowed_contracts(self) -> list[str]:
        return _get(["policy", "allowed_contracts"], default=[]) or [self.uniswap_swap_router]

    @property
    def default_max_input_per_tx(self) -> int:
        return int(_get(["policy", "max_input_per_tx"], default=1_000_000_000))


settings = Settings()