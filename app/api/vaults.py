from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class VaultAmountRequest(BaseModel):
    vault_id: int
    amount: str
    receiver: str


class VaultSharesRequest(BaseModel):
    vault_id: int
    shares: str
    receiver: str


class CreateVaultRequest(BaseModel):
    owner_fee_bps: int


class ImportVaultRequest(BaseModel):
    vault_address: str
    chain_id: int


class AgentSwapRequest(BaseModel):
    vault_id: int
    target: str
    data: str
    min_asset_delta: str = "0"
    value: str = "0"


def build_router(vault_service) -> APIRouter:
    router = APIRouter(prefix="/v1/vaults", tags=["vaults"])

    @router.get("")
    def list_vaults():
        try:
            return vault_service.list_vaults()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{vault_id}")
    def get_vault_details(vault_id: int):
        try:
            return vault_service.get_vault_details(vault_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/import")
    def import_vault(req: ImportVaultRequest):
        try:
            return vault_service.import_vault(req.vault_address, chain_id=req.chain_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/balances")
    def get_vault_balances():
        try:
            return vault_service.get_all_balances()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/balance/{token_address}")
    def get_token_balance(token_address: str):
        try:
            balance = vault_service.get_token_balance(token_address)
            decimals = vault_service.get_token_decimals(token_address)
            symbol = vault_service.get_token_symbol(token_address)
            return {
                "token": token_address,
                "symbol": symbol,
                "balance_raw": balance,
                "balance_human": balance / (10 ** decimals),
                "decimals": decimals,
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/create/build")
    def build_create_vault(req: CreateVaultRequest):
        try:
            return vault_service.build_create_vault_tx(req.owner_fee_bps)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/deposit/build")
    def build_deposit(req: VaultAmountRequest):
        try:
            return vault_service.build_deposit_tx(
                vault_id=req.vault_id,
                amount=int(req.amount),
                receiver=req.receiver,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/withdraw/build")
    def build_withdraw(req: VaultSharesRequest):
        try:
            return vault_service.build_withdraw_tx(
                vault_id=req.vault_id,
                shares=int(req.shares),
                receiver=req.receiver,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/agent-swap/build")
    def build_agent_swap(req: AgentSwapRequest):
        try:
            return vault_service.build_agent_swap_tx(
                vault_id=req.vault_id,
                target=req.target,
                data=req.data,
                min_asset_delta=int(req.min_asset_delta),
                value=int(req.value),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/agent-swap/execute")
    def execute_agent_swap(req: AgentSwapRequest):
        try:
            return vault_service.execute_agent_swap(
                vault_id=req.vault_id,
                target=req.target,
                data=req.data,
                min_asset_delta=int(req.min_asset_delta),
                value=int(req.value),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{vault_id}/positions/{user_address}")
    def get_user_position(vault_id: int, user_address: str):
        try:
            return vault_service.get_user_position(vault_id, user_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
