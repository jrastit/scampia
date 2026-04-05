"""
Configuration.

Shared config  → settings.yaml (committed in the repo)
Secrets        → .env          (never committed)
Network select → NETWORK env var (default: ethereum-sepolia)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

load_dotenv()

# ── Multi-network support ──
NETWORKS: Dict[str, Dict[str, str | int]] = {
    "ethereum-mainnet": {
        "rpc_url": "https://ethereum-rpc.publicnode.com",
        "chain_id": 1,
        "safe_tx_service_base": "https://safe-transaction-mainnet.safe.global",
        "ens_reverse_registrar_address": "0xA58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb",
        "ens_public_resolver_address": "0xF29100983E058B709F3D539b0c765937B804AC15",
    },
    "ethereum-sepolia": {
        "rpc_url": "https://ethereum-sepolia-rpc.publicnode.com",
        "chain_id": 11155111,
        "safe_tx_service_base": "https://safe-transaction-sepolia.safe.global",
        "ens_reverse_registrar_address": "0xA0a1AbcDAe1a2a4A2EF8e9113Ff0e02DD81DC0C6",
        "ens_public_resolver_address": "0xE99638b40E4Fff0129D56f03b55b6bbC4BBE49b5",
    },
}


def _selected_network() -> str:
    network = os.getenv("NETWORK", "ethereum-sepolia").lower()
    if network in NETWORKS:
        return network

    # Some environments inject unrelated NETWORK values.
    # Fall back to Sepolia unless the app explicitly overrides it with a supported value.
    return "ethereum-sepolia"


NETWORK = _selected_network()


# ── Load settings.yaml (optional) ──
_yaml_candidates = [
    Path(__file__).resolve().with_name("settings.yaml"),
    Path(__file__).resolve().parent / "settings.yaml",
    Path(__file__).resolve().parent.parent / "settings.yaml",
    Path.cwd() / "settings.yaml",
]
_cfg: dict[str, Any] = {}
for _yaml_path in _yaml_candidates:
    if _yaml_path.exists():
        with open(_yaml_path) as f:
            _cfg = yaml.safe_load(f) or {}
        break


def _get(yaml_keys: list[str], env_key: str = "", default: Any = "") -> Any:
    """Read from env when provided, then YAML, then default."""
    if env_key:
        env_val = os.getenv(env_key)
        if env_val is not None:
            return env_val
    val: Any = _cfg
    for k in yaml_keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            val = None
            break
    if val is not None:
        return val
    return default


@dataclass
class Settings:
    # ── App ──
    app_name: str = str(_get(["app", "name"], "APP_NAME", "Scampia API"))
    app_version: str = str(_get(["app", "version"], "APP_VERSION", "0.2.0"))
    app_host: str = str(os.getenv("APP_HOST", "0.0.0.0"))
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    app_reload: bool = str(os.getenv("APP_RELOAD", "false")).lower() in {"1", "true", "yes", "on"}
    app_root_path: str = str(os.getenv("APP_ROOT_PATH", "/api"))
    network: str = NETWORK

    # ── Chain ──
    rpc_url: str = str(_get(["chain", "rpc_url"], "RPC_URL", str(NETWORKS[NETWORK]["rpc_url"])))
    chain_id: int = int(_get(["chain", "id"], "CHAIN_ID", str(NETWORKS[NETWORK]["chain_id"])))

    # ── Safe ──
    safe_address: str = str(_get(["safe", "address"], "SAFE_ADDRESS", ""))
    safe_tx_service_base: str = str(
        _get(["safe", "tx_service"], "SAFE_TX_SERVICE_BASE", str(NETWORKS[NETWORK]["safe_tx_service_base"]))
    )
    safe_api_key: str = os.getenv("SAFE_API_KEY", "")

    # ── Vault ──
    vault_address: str = str(_get(["vault", "address"], "VAULT_ADDRESS", ""))
    vault_manager_address: str = str(
        _get(["vault", "manager_address"], "VAULT_MANAGER_ADDRESS", str(_get(["vault", "address"], "VAULT_ADDRESS", "")))
    )
    vault_asset_token: str = str(
        _get(["vault", "asset_token"], "VAULT_ASSET_TOKEN", _get(["tokens", "usdc"], "USDC_ADDRESS", ""))
    )
    vault_manager_fee_bps: int = int(_get(["vault", "manager_fee_bps"], "VAULT_MANAGER_FEE_BPS", 0))

    # ── Tokens ──
    usdc_address: str = str(
        _get(["tokens", "usdc"], "USDC_ADDRESS", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    )
    weth_address: str = str(
        _get(["tokens", "weth"], "WETH_ADDRESS", "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14")
    )

    # ── Uniswap ──
    uniswap_api_key: str = os.getenv("UNISWAP_API_KEY", "")
    uniswap_api_base: str = str(
        _get(["uniswap", "api_base"], "UNISWAP_API_BASE", "https://trade-api.gateway.uniswap.org")
    )
    uniswap_swap_router: str = str(
        _get(["uniswap", "swap_router"], "UNISWAP_SWAP_ROUTER", "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E")
    )
    uniswap_factory: str = str(
        _get(["uniswap", "factory"], "UNISWAP_FACTORY", "0x0227628f3F023bb0B980b67D528571c95c6DaC1c")
    )
    uniswap_quoter: str = str(
        _get(["uniswap", "quoter"], "UNISWAP_QUOTER", "0xEd1f6473345F45b75F8179591dd5bA1888cf2FB3")
    )

    # ── ENS ──
    ens_registry_address: str = str(
        _get(["ens", "registry_address"], "ENS_REGISTRY_ADDRESS", "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e")
    )
    ens_reverse_registrar_address: str = str(
        _get(
            ["ens", "reverse_registrar_address"],
            "ENS_REVERSE_REGISTRAR_ADDRESS",
            NETWORKS[NETWORK]["ens_reverse_registrar_address"],
        )
    )
    ens_public_resolver_address: str = str(
        _get(
            ["ens", "public_resolver_address"],
            "ENS_PUBLIC_RESOLVER_ADDRESS",
            NETWORKS[NETWORK]["ens_public_resolver_address"],
        )
    )
    ens_parent_name: str = str(_get(["ens", "parent_name"], "ENS_PARENT_NAME", "scampia.eth"))
    ens_manager_address: str = str(_get(["ens", "manager_address"], "ENS_MANAGER_ADDRESS", ""))

    # ── Secret (from .env ONLY) ──
    backend_private_key: str = os.getenv("BACKEND_PRIVATE_KEY", "")
    ens_private_key: str = os.getenv("ENS_PRIVATE_KEY", "")

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

    # Backward-compatible aliases used elsewhere in the codebase
    @property
    def trade_allowed_tokens_in(self) -> list[str]:
        return self.default_allowed_tokens_in

    @property
    def trade_allowed_tokens_out(self) -> list[str]:
        return self.default_allowed_tokens_out

    @property
    def trade_allowed_contracts(self) -> list[str]:
        return self.default_allowed_contracts

    @property
    def trade_max_input_per_tx(self) -> int:
        return self.default_max_input_per_tx
    
    @property
    def stop_loss_pct(self) -> int:
        return _get(["policy", "stop_loss_pct"], default=0)

    @property
    def take_profit_pct(self) -> int:
        return _get(["policy", "take_profit_pct"], default=0)

    @property
    def max_open_positions(self) -> int:
        return _get(["policy", "max_open_positions"], default=0)

    @property
    def min_eth_balance(self) -> float:
        return _get(["policy", "min_eth_balance"], default=0.0)

    @property
    def max_slippage_tolerance_pct(self) -> int:
        return _get(["policy", "max_slippage_tolerance_pct"], default=0)

    @property
    def max_gas_price_gwei(self) -> int:
        return _get(["policy", "max_gas_price_gwei"], default=0)

    @property
    def authorized_tokens(self) -> list[str]:
        return _get(["policy", "authorized_tokens"], default=[])
    
    @property
    def open_claw_config(self) -> str:
        return _get(["config_file", "open_claw_config"], default="")


settings = Settings()
