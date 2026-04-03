from fastapi import FastAPI, HTTPException

from app.schemas import (
    BuildTradeRequest,
    CreateEnsSubnameRequest,
    ExecuteSafeTxRequest,
    ImportSafeRequest,
    SafeBuildTxRequest,
    UniswapQuoteRequest,
    UpdateEnsRecordsRequest,
)
from app.services.ens_service import ENSService
from app.services.policy_service import PolicyService, PolicyViolation
from app.services.safe_service import SafeService
from app.services.uniswap_service import UniswapService
from app.config import settings


app = FastAPI(title="Scampia API", version="0.1.0")

ens_service = ENSService()
safe_service = SafeService()
uniswap_service = UniswapService()
policy_service = PolicyService()


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
    return safe_service.build_safe_tx(
        safe_address=req.safe_address,
        to=req.to,
        data=req.data,
        value=req.value,
        operation=req.operation,
    )


@app.post("/v1/safes/execute-direct")
def execute_direct(req: ExecuteSafeTxRequest):
    # Example only. This is not Safe multisig execution.
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
        return ens_service.get_profile(
            name,
            text_keys=["agent:type", "agent:capabilities", "agent:api", "agent:safe"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# UNISWAP
# -----------------------------

@app.post("/v1/trades/quote")
def get_trade_quote(req: UniswapQuoteRequest):
    try:
        return uniswap_service.get_quote(
            chain_id=req.chain_id,
            wallet_address=req.safe_address,
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
        recipient = req.recipient or req.safe_address

        # Example hardcoded offchain policy
        policy_service.validate_trade(
            safe_address=req.safe_address,
            recipient=recipient,
            token_in=req.token_in,
            token_out=req.token_out,
            amount_in=int(req.amount_in),
            allowed_tokens_in=["0x833589fCD6EDB6E08f4c7C32D4f71b54bdA02913"],  # USDC on Base
            allowed_tokens_out=[
                "0x4200000000000000000000000000000000000006",  # WETH on Base
            ],
            max_input_per_tx=1_000_000_000,  # example
        )

        swap = uniswap_service.build_swap(
            chain_id=req.chain_id,
            wallet_address=req.safe_address,
            token_in=req.token_in,
            token_out=req.token_out,
            amount_in=req.amount_in,
            slippage_bps=req.slippage_bps,
        )

        # Normalize a tx object your Safe service can consume
        tx = {
            "to": swap.get("to") or swap.get("tx", {}).get("to"),
            "data": swap.get("data") or swap.get("tx", {}).get("data"),
            "value": str(swap.get("value") or swap.get("tx", {}).get("value") or "0"),
        }

        return {
            "policyCheck": {"ok": True},
            "quoteOrSwapResponse": swap,
            "tx": tx,
        }

    except PolicyViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/trades/prepare-safe-tx")
def prepare_safe_trade(req: BuildTradeRequest):
    try:
        recipient = req.recipient or req.safe_address

        policy_service.validate_trade(
            safe_address=req.safe_address,
            recipient=recipient,
            token_in=req.token_in,
            token_out=req.token_out,
            amount_in=int(req.amount_in),
            allowed_tokens_in=["0x833589fCD6EDB6E08f4c7C32D4f71b54bdA02913"],
            allowed_tokens_out=["0x4200000000000000000000000000000000000006"],
            max_input_per_tx=1_000_000_000,
        )

        swap = uniswap_service.build_swap(
            chain_id=req.chain_id,
            wallet_address=req.safe_address,
            token_in=req.token_in,
            token_out=req.token_out,
            amount_in=req.amount_in,
            slippage_bps=req.slippage_bps,
        )

        tx_to = swap.get("to") or swap.get("tx", {}).get("to")
        tx_data = swap.get("data") or swap.get("tx", {}).get("data")
        tx_value = str(swap.get("value") or swap.get("tx", {}).get("value") or "0")

        safe_tx = safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=tx_to,
            data=tx_data,
            value=tx_value,
            operation=0,
        )

        return {"safeTx": safe_tx, "rawSwap": swap}
    except PolicyViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))