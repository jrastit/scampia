import json
from typing import Dict, List, Optional
from app.config import settings
from pydantic import BaseModel, ConfigDict, Field


class CreateSafeRequest(BaseModel):
    owners: List[str]
    threshold: int = Field(..., ge=1)
    chain_id: int
    label: Optional[str] = None


class ImportSafeRequest(BaseModel):
    safe_address: str
    chain_id: int


class VaultEnsPolicyUpdateRequest(BaseModel):
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    min_eth_balance: Optional[float] = None
    max_slippage_tolerance_pct: Optional[float] = None
    max_gas_price_gwei: Optional[float] = None
    authorized_tokens: Optional[List[str]] = None

    def to_text_records(self) -> Dict[str, str]:
        records: Dict[str, str] = {}
        if self.stop_loss_pct is not None:
            records["stop_loss_pct"] = self._format_number(self.stop_loss_pct)
        else:
            records["stop_loss_pct"] = settings.stop_loss_pct
        if self.take_profit_pct is not None:
            records["take_profit_pct"] = self._format_number(self.take_profit_pct)
        else:
            records["take_profit_pct"] = settings.take_profit_pct
        # if self.max_open_positions is not None:
        #     records["max_open_positions"] = str(self.max_open_positions)
        # else:
        #     records["max_open_positions"] = settings.max_open_positions
        if self.min_eth_balance is not None:
            records["min_eth_balance"] = self._format_number(self.min_eth_balance)
        else:
            records["min_eth_balance"] = settings.min_eth_balance
        if self.max_slippage_tolerance_pct is not None:
            records["max_slippage_tolerance_pct"] = self._format_number(
                self.max_slippage_tolerance_pct
            )
        else:
            records["max_slippage_tolerance_pct"] = settings.max_slippage_tolerance_pct
        if self.max_gas_price_gwei is not None:
            records["max_gas_price_gwei"] = self._format_number(self.max_gas_price_gwei)
        else:
            records["max_gas_price_gwei"] = settings.max_gas_price_gwei
        if self.authorized_tokens is not None:
            records["authorized_tokens"] = json.dumps(self.authorized_tokens, separators=(",", ":"))
        else:
            records["authorized_tokens"] = json.dumps(settings.authorized_tokens)
        return records

    @staticmethod
    def _format_number(value: float | int) -> str:
        if isinstance(value, int) or float(value).is_integer():
            return str(int(value))
        return format(float(value), "g")


class RegisterVaultEnsRequest(VaultEnsPolicyUpdateRequest):
    vault_id: int
    label: str


class BuildVaultEnsPolicyTxRequest(VaultEnsPolicyUpdateRequest):
    vault_id: int


class SetEnsConfigRequest(BaseModel):
    registry_address: Optional[str] = None
    resolver_address: Optional[str] = None
    parent_name: Optional[str] = None


class UniswapQuoteRequest(BaseModel):
    chain_id: int
    vault_address: Optional[str] = None
    safe_address: Optional[str] = None
    token_in: str
    token_out: str
    amount_in: str
    slippage_bps: int = 50

    def resolve_wallet_address(self) -> str:
        addr = self.vault_address or self.safe_address or settings.vault_manager_address
        if not addr:
            raise ValueError("vault_manager_address is required")
        return addr


class BuildTradeRequest(BaseModel):
    chain_id: int
    vault_id: Optional[int] = None
    vault_address: Optional[str] = None
    safe_address: Optional[str] = None
    token_in: str
    token_out: str
    amount_in: str
    slippage_bps: int = 50
    permit_signature: Optional[str] = None
    recipient: Optional[str] = None

    def resolve_wallet_address(self) -> str:
        addr = self.vault_address or self.safe_address or settings.vault_manager_address
        if not addr:
            raise ValueError("vault_manager_address is required")
        return addr

    def require_vault_id(self) -> int:
        if self.vault_id is None:
            raise ValueError("vault_id is required")
        return self.vault_id


class SafeBuildTxRequest(BaseModel):
    safe_address: str
    to: str
    data: str
    value: str = "0"
    operation: int = 0


class ExecuteSafeTxRequest(BaseModel):
    safe_address: str
    to: str
    data: str
    value: str = "0"
    operation: int = 0


class HealthResponse(BaseModel):
    ok: bool
    app: str
    network: str
    chainId: int
    safeTxServiceBase: str


class UserResponse(BaseModel):
    wallet_address: str
    vault_address: Optional[str] = None
    safe_address: Optional[str] = None
    vault_id: Optional[int] = None
    pending_sync: bool = False
    retry_after_seconds: int = 0
    sync_source: str = "onchain_scan"
    network: Optional[str] = None
    chain_id: Optional[int] = None
    created_at: Optional[str] = None
    is_active: Optional[bool] = None


class ConnectWalletResponse(BaseModel):
    status: str
    wallet_address: str
    vault_address: Optional[str] = None
    safe_address: Optional[str] = None
    vault_id: Optional[int] = None
    pending_sync: bool = False
    retry_after_seconds: int = 0
    sync_source: str = "onchain_scan"
    created_at: Optional[str] = None


class UserVaultSyncResponse(BaseModel):
    wallet_address: str
    vault_id: Optional[int] = None
    pending_sync: bool
    retry_after_seconds: int
    sync_source: str = "onchain_scan"


class UserInvestmentItem(BaseModel):
    vault_id: int
    shares: str
    value: str
    profit: str


class UserInvestmentsResponse(BaseModel):
    wallet_address: str
    items: List[UserInvestmentItem]


class VaultListItem(BaseModel):
    vault_id: int
    owner: str
    owner_fee_bps: int
    asset_token: str
    total_assets: str
    total_shares: str


class VaultListResponse(BaseModel):
    items: List[VaultListItem]


class VaultDetailsResponse(BaseModel):
    vault_id: int
    owner: str
    owner_fee_bps: int
    manager_fee_bps: int
    asset_token: str
    total_assets: str
    total_shares: str
    created_at: Optional[str] = None


class VaultPositionResponse(BaseModel):
    vaultId: str
    user: str
    shares: str
    principal: str
    estimatedAssets: str


class TradeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class EnsConfigResponse(BaseModel):
    network: str
    chainId: int
    managerAddress: Optional[str] = None
    vaultContractAddress: Optional[str] = None
    parentName: str
    parentNode: str
    registryAddress: str
    publicResolverAddress: str


class EnsWriteResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class EnsProfileResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    node: Optional[str] = None
    owner: Optional[str] = None
    resolver: Optional[str] = None
    address: Optional[str] = None
    texts: Dict[str, str] = Field(default_factory=dict)
    network: Optional[str] = None
    chainId: Optional[int] = None


class VaultEnsProfileResponse(EnsProfileResponse):
    vaultId: Optional[str] = None
    label: Optional[str] = None
    configured: Optional[bool] = None
