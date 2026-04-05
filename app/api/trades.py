from fastapi import APIRouter, HTTPException, status, Depends

from app.data import user_data

try:
    from app.schemas import BuildTradeRequest, UniswapQuoteRequest
    from app.services.policy_service import PolicyViolation
    from app.services.simulation_service import SimulationError
except ImportError:
    from schemas import BuildTradeRequest, UniswapQuoteRequest
    from policy_service import PolicyViolation
    from simulation_service import SimulationError

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def build_router(trade_service, settings) -> APIRouter:
    router = APIRouter(prefix="/v1/trades", tags=["trades"])

    @router.post("/quote")
    def get_trade_quote(req: UniswapQuoteRequest):
        try:
            wallet_address = req.resolve_wallet_address()
            return trade_service.quote_trade(
                chain_id=req.chain_id,
                wallet_address=wallet_address,
                token_in=req.token_in,
                token_out=req.token_out,
                amount_in=req.amount_in,
                slippage_bps=req.slippage_bps,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/build")
    def build_trade(req: BuildTradeRequest):
        try:
            wallet_address = req.resolve_wallet_address()
            return trade_service.build_trade(
                chain_id=req.chain_id,
                wallet_address=wallet_address,
                token_in=req.token_in,
                token_out=req.token_out,
                amount_in=req.amount_in,
                slippage_bps=req.slippage_bps,
                permit_signature=req.permit_signature,
                recipient=req.recipient,
                allowed_tokens_in=settings.trade_allowed_tokens_in,
                allowed_tokens_out=settings.trade_allowed_tokens_out,
                max_input_per_tx=settings.trade_max_input_per_tx,
            )
        except PolicyViolation as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/prepare-safe-tx")
    def prepare_vault_trade(req: BuildTradeRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
        api_key = credentials.credentials
        user = user_data.get_user_by_api_key(api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        try:
            wallet_address = req.resolve_wallet_address()
            vault_id = req.require_vault_id()
            return trade_service.prepare_vault_trade(
                chain_id=req.chain_id,
                vault_id=vault_id,
                wallet_address=wallet_address,
                token_in=req.token_in,
                token_out=req.token_out,
                amount_in=req.amount_in,
                slippage_bps=req.slippage_bps,
                permit_signature=req.permit_signature,
                recipient=req.recipient,
                allowed_tokens_in=settings.trade_allowed_tokens_in,
                allowed_tokens_out=settings.trade_allowed_tokens_out,
                max_input_per_tx=settings.trade_max_input_per_tx,
            )
        except PolicyViolation as e:
            raise HTTPException(status_code=403, detail=str(e))
        except SimulationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/prepare-safe-tx")
    def prepare_vault_trade_compat(req: BuildTradeRequest):
        return prepare_vault_trade(req)

    @router.post("/execute-vault-swap")
    def execute_vault_swap(req: BuildTradeRequest):
        try:
            vault_id = req.require_vault_id()
            return trade_service.execute_vault_swap(
                chain_id=req.chain_id,
                vault_id=vault_id,
                token_in=req.token_in,
                token_out=req.token_out,
                amount_in=req.amount_in,
                slippage_bps=req.slippage_bps,
                permit_signature=req.permit_signature,
                user_id = user.id
            )
        except PolicyViolation as e:
            raise HTTPException(status_code=403, detail=str(e))
        except SimulationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
