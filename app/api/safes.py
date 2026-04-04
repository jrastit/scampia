from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from app.schemas import ExecuteSafeTxRequest, ImportSafeRequest, SafeBuildTxRequest
except ImportError:
    from schemas import ExecuteSafeTxRequest, ImportSafeRequest, SafeBuildTxRequest


class DeploySafeRequest(BaseModel):
    owner_address: str
    threshold: int = 1


class WithdrawEthRequest(BaseModel):
    safe_address: str
    to: str
    amount: str


class WithdrawTokenRequest(BaseModel):
    safe_address: str
    to: str
    token_address: str
    amount: str


def build_router(safe_service) -> APIRouter:
    router = APIRouter(prefix="/v1/safes", tags=["safes"])

    @router.post("/deploy")
    def deploy_safe(req: DeploySafeRequest):
        try:
            return safe_service.deploy_safe(
                owner_address=req.owner_address,
                threshold=req.threshold,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/import")
    def import_safe(req: ImportSafeRequest):
        return safe_service.import_safe(req.safe_address, req.chain_id)

    @router.get("/{safe_address}")
    def get_safe_info(safe_address: str):
        try:
            return safe_service.get_safe_info(safe_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{safe_address}/balances")
    def get_safe_balances(safe_address: str):
        try:
            return safe_service.get_all_balances(safe_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{safe_address}/balance/{token_address}")
    def get_token_balance(safe_address: str, token_address: str):
        try:
            balance = safe_service.get_token_balance(safe_address, token_address)
            decimals = safe_service.get_token_decimals(token_address)
            symbol = safe_service.get_token_symbol(token_address)
            return {
                "token": token_address,
                "symbol": symbol,
                "balance_raw": balance,
                "balance_human": balance / (10 ** decimals),
                "decimals": decimals,
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{safe_address}/owners")
    def get_safe_owners(safe_address: str):
        try:
            return {"safeAddress": safe_address, "owners": safe_service.get_owners(safe_address)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{safe_address}/owners/{address}/check")
    def check_is_owner(safe_address: str, address: str):
        try:
            return {"address": address, "isOwner": safe_service.is_owner(safe_address, address)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/build-tx")
    def build_safe_tx(req: SafeBuildTxRequest):
        return safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=req.to,
            data=req.data,
            value=req.value,
            operation=req.operation,
        )

    @router.post("/execute-direct")
    def execute_direct(req: ExecuteSafeTxRequest):
        try:
            return safe_service.execute_safe_tx(
                safe_address=req.safe_address,
                to=req.to,
                data=req.data,
                value=int(req.value),
                operation=req.operation,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/withdraw/eth/build")
    def build_withdraw_eth(req: WithdrawEthRequest):
        try:
            return safe_service.build_withdraw_eth(
                safe_address=req.safe_address,
                to=req.to,
                amount=int(req.amount),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/withdraw/eth/execute")
    def execute_withdraw_eth(req: WithdrawEthRequest):
        try:
            return safe_service.withdraw_eth(
                safe_address=req.safe_address,
                to=req.to,
                amount=int(req.amount),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/withdraw/token/build")
    def build_withdraw_token(req: WithdrawTokenRequest):
        try:
            return safe_service.build_withdraw_token(
                safe_address=req.safe_address,
                to=req.to,
                token_address=req.token_address,
                amount=int(req.amount),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/withdraw/token/execute")
    def execute_withdraw_token(req: WithdrawTokenRequest):
        try:
            return safe_service.withdraw_token(
                safe_address=req.safe_address,
                to=req.to,
                token_address=req.token_address,
                amount=int(req.amount),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
