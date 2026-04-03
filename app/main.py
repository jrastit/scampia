from fastapi import FastAPI, HTTPException

from app.schemas import (
    BuildTradeRequest,
    CreateEnsSubnameRequest,
    ExecuteSafeTxRequest,
    ImportSafeRequest,
    PrepareSetReverseEnsRequest,
    SafeBuildTxRequest,
    SetReverseEnsRequest,
    UniswapQuoteRequest,
    UpdateEnsRecordsRequest,
)
from app.services.ens_service import ENSService
from app.services.policy_service import PolicyService, PolicyViolation
from app.services.safe_service import SafeService
from app.services.simulation_service import SimulationError, SimulationService
from app.services.trade_service import TradeService
from app.services.uniswap_service import UniswapService
from app.config import settings


app = FastAPI(title="Scampia API", version="0.2.0")

ens_service = ENSService()
safe_service = SafeService()
uniswap_service = UniswapService()
policy_service = PolicyService()
simulation_service = SimulationService()
trade_service = TradeService(
    uniswap_service=uniswap_service,
    policy_service=policy_service,
    simulation_service=simulation_service,
    safe_service=safe_service,
)


DEFAULT_ALLOWED_TOKENS_IN = ["0x833589fCD6EDB6E08f4c7C32D4f71b54bdA02913"]  # USDC on Base
DEFAULT_ALLOWED_TOKENS_OUT = ["0x4200000000000000000000000000000000000006"]  # WETH on Base
DEFAULT_MAX_INPUT_PER_TX = 1_000_000_000
DEFAULT_AGENT_TEXT_KEYS = ["agent:type", "agent:capabilities", "agent:api", "agent:safe"]


@app.get("/health")
def health():
    return {"ok": True, "app": settings.app_name}


# -----------------------------
# SAFE
# -----------------------------

@app.post("/v1/safes/import")
def import_safe(req: ImportSafeRequest):
    return safe_service.import_safe(req.safe_address, req.chain_id)


@app.get("/v1/safes/{safe_address}")
def get_safe_info(safe_address: str):
    try:
        return safe_service.get_safe_info(safe_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/safes/build-tx")
def build_safe_tx(req: SafeBuildTxRequest):
    try:
        return safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=req.to,
            data=req.data,
            value=req.value,
            operation=req.operation,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/safes/execute-direct")
def execute_direct(req: ExecuteSafeTxRequest):
    try:
        return safe_service.execute_direct_eoa_tx(
            to=req.to,
            data=req.data,
            value=int(req.value),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# ENS
# -----------------------------

@app.post("/v1/ens/reverse")
def set_reverse_ens(req: SetReverseEnsRequest):
    try:
        return ens_service.set_reverse_name(
            target_address=req.address,
            name=req.name,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/ens/reverse/prepare-safe-tx")
def prepare_reverse_ens_safe_tx(req: PrepareSetReverseEnsRequest):
    try:
        tx = ens_service.build_set_reverse_name_tx(
            target_address=req.address,
            name=req.name,
        )
        safe_tx = safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=tx["to"],
            data=tx["data"],
            value=tx["value"],
            operation=req.operation,
        )
        return {"tx": tx, "safeTx": safe_tx}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/ens/subnames")
def create_subname(req: CreateEnsSubnameRequest):
    try:
        resolver = req.resolver_address or settings.ens_public_resolver_address
        if not resolver:
            raise ValueError("resolver_address is required")

        owner = req.owner_address or req.safe_address

        return ens_service.create_subname(
            parent_name=req.parent_name,
            label=req.label,
            owner_address=owner,
            resolver_address=resolver,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/ens/subnames/prepare-safe-tx")
def prepare_create_subname_safe_tx(req: CreateEnsSubnameRequest):
    try:
        resolver = req.resolver_address or settings.ens_public_resolver_address
        if not resolver:
            raise ValueError("resolver_address is required")

        owner = req.owner_address or req.safe_address
        tx = ens_service.build_create_subname_tx(
            parent_name=req.parent_name,
            label=req.label,
            owner_address=owner,
            resolver_address=resolver,
        )
        safe_tx = safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=tx["to"],
            data=tx["data"],
            value=tx["value"],
            operation=0,
        )
        return {"tx": tx, "safeTx": safe_tx}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/v1/ens/records")
def update_ens_records(req: UpdateEnsRecordsRequest):
    try:
        result = {"name": req.name}

        if req.address:
            result["addr"] = ens_service.set_addr(req.name, req.address)

        if req.texts:
            result["texts"] = ens_service.set_text_records(req.name, req.texts)

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/ens/names/{name}")
def get_ens_profile(name: str):
    try:
        return ens_service.get_profile(name, text_keys=DEFAULT_AGENT_TEXT_KEYS)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# UNISWAP / TRADES
# -----------------------------

@app.post("/v1/trades/quote")
def get_trade_quote(req: UniswapQuoteRequest):
    try:
        return trade_service.quote_trade(
            chain_id=req.chain_id,
            safe_address=req.safe_address,
            token_in=req.token_in,
            token_out=req.token_out,
            amount_in=req.amount_in,
            slippage_bps=req.slippage_bps,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/trades/build")
def build_trade(req: BuildTradeRequest):
    try:
        return trade_service.build_trade(
            chain_id=req.chain_id,
            safe_address=req.safe_address,
            token_in=req.token_in,
            token_out=req.token_out,
            amount_in=req.amount_in,
            slippage_bps=req.slippage_bps,
            recipient=req.recipient,
            allowed_tokens_in=DEFAULT_ALLOWED_TOKENS_IN,
            allowed_tokens_out=DEFAULT_ALLOWED_TOKENS_OUT,
            max_input_per_tx=DEFAULT_MAX_INPUT_PER_TX,
        )
    except PolicyViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/trades/prepare-safe-tx")
def prepare_safe_trade(req: BuildTradeRequest):
    try:
        return trade_service.prepare_safe_trade(
            chain_id=req.chain_id,
            safe_address=req.safe_address,
            token_in=req.token_in,
            token_out=req.token_out,
            amount_in=req.amount_in,
            slippage_bps=req.slippage_bps,
            recipient=req.recipient,
            allowed_tokens_in=DEFAULT_ALLOWED_TOKENS_IN,
            allowed_tokens_out=DEFAULT_ALLOWED_TOKENS_OUT,
            max_input_per_tx=DEFAULT_MAX_INPUT_PER_TX,
            operation=0,
        )
    except PolicyViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SimulationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
