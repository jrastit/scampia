import json
from typing import Dict, List, Optional
from app.config import settings
from pydantic import BaseModel, Field


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
    max_open_positions: Optional[int] = None
    min_eth_balance: Optional[float] = None
    max_slippage_tolerance_pct: Optional[float] = None
    max_gas_price_gwei: Optional[float] = None
    authorized_tokens: Optional[List[str]] = None

    def to_text_records(self) -> Dict[str, str]:
        records: Dict[str, str] = {}
        if self.stop_loss_pct is not None:
            records["stop_loss_pct"] = self._format_number(self.stop_loss_pct)
        if self.take_profit_pct is not None:
            records["take_profit_pct"] = self._format_number(self.take_profit_pct)
        if self.max_open_positions is not None:
            records["max_open_positions"] = str(self.max_open_positions)
        if self.min_eth_balance is not None:
            records["min_eth_balance"] = self._format_number(self.min_eth_balance)
        if self.max_slippage_tolerance_pct is not None:
            records["max_slippage_tolerance_pct"] = self._format_number(
                self.max_slippage_tolerance_pct
            )
        if self.max_gas_price_gwei is not None:
            records["max_gas_price_gwei"] = self._format_number(self.max_gas_price_gwei)
        if self.authorized_tokens is not None:
            records["authorized_tokens"] = json.dumps(self.authorized_tokens, separators=(",", ":"))
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
