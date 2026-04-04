from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class VaultAmountRequest(BaseModel):
    vault_address: str
    amount: str
    receiver: str


class ImportVaultRequest(BaseModel):
    vault_address: str
    chain_id: int


class AgentSwapRequest(BaseModel):
    vault_address: str
    target: str
    data: str
    token_out: str
    min_token_out: str = "0"
    value: str = "0"


def build_router(vault_service) -> APIRouter:
    router = APIRouter(prefix="/v1/vaults", tags=["vaults"])

    @router.post("/import")
    def import_vault(req: ImportVaultRequest):
        try:
            return vault_service.import_vault(req.vault_address, chain_id=req.chain_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{vault_address}/balances")
    def get_vault_balances(vault_address: str):
        try:
            return vault_service.get_all_balances(vault_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{vault_address}/balance/{token_address}")
    def get_token_balance(vault_address: str, token_address: str):
        try:
            balance = vault_service.get_token_balance(vault_address, token_address)
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

    @router.post("/deposit/build")
    def build_deposit(req: VaultAmountRequest):
        try:
            return vault_service.build_deposit_tx(
                vault_address=req.vault_address,
                amount=int(req.amount),
                receiver=req.receiver,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/withdraw/build")
    def build_withdraw(req: VaultAmountRequest):
        try:
            return vault_service.build_withdraw_tx(
                vault_address=req.vault_address,
                amount=int(req.amount),
                receiver=req.receiver,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/agent-swap/build")
    def build_agent_swap(req: AgentSwapRequest):
        try:
            return vault_service.build_agent_swap_tx(
                vault_address=req.vault_address,
                target=req.target,
                data=req.data,
                token_out=req.token_out,
                min_token_out=int(req.min_token_out),
                value=int(req.value),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/agent-swap/execute")
    def execute_agent_swap(req: AgentSwapRequest):
        try:
            return vault_service.execute_agent_swap(
                vault_address=req.vault_address,
                target=req.target,
                data=req.data,
                token_out=req.token_out,
                min_token_out=int(req.min_token_out),
                value=int(req.value),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
