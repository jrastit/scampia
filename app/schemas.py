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


class CreateEnsSubnameRequest(BaseModel):
    parent_name: str = settings.ens_parent_name
    label: str
    safe_address: str
    owner_address: Optional[str] = None
    resolver_address: Optional[str] = None


class UpdateEnsRecordsRequest(BaseModel):
    name: str
    address: Optional[str] = None
    texts: Dict[str, str] = Field(default_factory=dict)


class UniswapQuoteRequest(BaseModel):
    chain_id: int
    safe_address: str
    token_in: str
    token_out: str
    amount_in: str
    slippage_bps: int = 50


class BuildTradeRequest(BaseModel):
    chain_id: int
    safe_address: str
    token_in: str
    token_out: str
    amount_in: str
    slippage_bps: int = 50
    recipient: Optional[str] = None


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
