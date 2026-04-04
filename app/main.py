from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from app.config import settings
    from app.data import get_db, init_db
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
    from app.services.simulation_service import SimulationError, SimulationService
    from app.services.trade_service import TradeService
    from app.services.uniswap_service import UniswapService
    from app.services.user_service import UserService
except ImportError:
    from config import settings
    from data import get_db, init_db
    from schemas import (
        BuildTradeRequest,
        CreateEnsSubnameRequest,
        ExecuteSafeTxRequest,
        ImportSafeRequest,
        SafeBuildTxRequest,
        UniswapQuoteRequest,
        UpdateEnsRecordsRequest,
    )
    from ens_service import ENSService
    from policy_service import PolicyService, PolicyViolation
    from safe_service import SafeService
    from simulation_service import SimulationError, SimulationService
    from trade_service import TradeService
    from uniswap_service import UniswapService
    from user_service import UserService


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_url="/v1/openapi.json",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
)

init_db()

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
user_service = UserService(safe_service=safe_service)


class SetReverseEnsRequest(BaseModel):
    address: str
    name: str


class PrepareReverseEnsSafeTxRequest(BaseModel):
    safe_address: str
    address: str
    name: str
    operation: int = 0


class PrepareEnsSubnameSafeTxRequest(BaseModel):
    safe_address: str
    parent_name: str = settings.ens_parent_name
    label: str
    owner_address: str | None = None
    resolver_address: str | None = None
    ttl: int = 0
    operation: int = 0




class PrepareSetEnsAddrSafeTxRequest(BaseModel):
    safe_address: str
    name: str
    address: str
    resolver_address: str | None = None
    operation: int = 0


class PrepareSetEnsTextSafeTxRequest(BaseModel):
    safe_address: str
    name: str
    key: str
    value: str
    resolver_address: str | None = None
    operation: int = 0


class RegisterSafeEnsRequest(BaseModel):
    safe_address: str
    label: str
    parent_name: str = settings.ens_parent_name
    resolver_address: str | None = None
    ttl: int = 0
    address: str | None = None
    set_reverse: bool = True
    texts: dict[str, str] = {}


class DeploySafeRequest(BaseModel):
    owner_address: str
    threshold: int = 1


class ConnectWalletRequest(BaseModel):
    wallet_address: str


class WithdrawEthRequest(BaseModel):
    safe_address: str
    to: str
    amount: str


class WithdrawTokenRequest(BaseModel):
    safe_address: str
    to: str
    token_address: str
    amount: str


@app.get("/health")
def health():
    return {
        "ok": True,
        "app": settings.app_name,
        "network": settings.network,
        "chainId": settings.chain_id,
        "rpcUrl": settings.rpc_url,
        "safeTxServiceBase": settings.safe_tx_service_base,
    }


# Users

@app.post("/v1/users/connect")
def connect_wallet(req: ConnectWalletRequest, db: Session = Depends(get_db)):
    try:
        return user_service.connect_wallet(db, req.wallet_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/users/{wallet_address}")
def get_user(wallet_address: str, db: Session = Depends(get_db)):
    user = user_service.get_user(db, wallet_address)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/v1/users")
def list_users(db: Session = Depends(get_db)):
    return user_service.get_all_users(db)


# Safe

@app.post("/v1/safes/deploy")
def deploy_safe(req: DeploySafeRequest):
    try:
        return safe_service.deploy_safe(
            owner_address=req.owner_address,
            threshold=req.threshold,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/safes/import")
def import_safe(req: ImportSafeRequest):
    return safe_service.import_safe(req.safe_address, req.chain_id)


@app.get("/v1/safes/{safe_address}")
def get_safe_info(safe_address: str):
    try:
        return safe_service.get_safe_info(safe_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/safes/{safe_address}/balances")
def get_safe_balances(safe_address: str):
    try:
        return safe_service.get_all_balances(safe_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/safes/{safe_address}/balance/{token_address}")
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


@app.get("/v1/safes/{safe_address}/owners")
def get_safe_owners(safe_address: str):
    try:
        return {"safeAddress": safe_address, "owners": safe_service.get_owners(safe_address)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/safes/{safe_address}/owners/{address}/check")
def check_is_owner(safe_address: str, address: str):
    try:
        return {"address": address, "isOwner": safe_service.is_owner(safe_address, address)}
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


# Withdraw

@app.post("/v1/safes/withdraw/eth/build")
def build_withdraw_eth(req: WithdrawEthRequest):
    try:
        return safe_service.build_withdraw_eth(
            safe_address=req.safe_address,
            to=req.to,
            amount=int(req.amount),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/safes/withdraw/eth/execute")
def execute_withdraw_eth(req: WithdrawEthRequest):
    try:
        return safe_service.withdraw_eth(
            safe_address=req.safe_address,
            to=req.to,
            amount=int(req.amount),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/safes/withdraw/token/build")
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


@app.post("/v1/safes/withdraw/token/execute")
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


# ENS

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
def prepare_reverse_ens_safe_tx(req: PrepareReverseEnsSafeTxRequest):
    try:
        tx = ens_service.build_set_reverse_name_tx(
            target_address=req.address,
            name=req.name,
        )
        return safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=tx["to"],
            data=tx["data"],
            value=tx["value"],
            operation=req.operation,
        )
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
def prepare_subname_safe_tx(req: PrepareEnsSubnameSafeTxRequest):
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
            ttl=req.ttl,
        )
        return safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=tx["to"],
            data=tx["data"],
            value=tx["value"],
            operation=req.operation,
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


@app.get("/v1/ens/config")
def get_ens_config():
    return {
        "network": settings.network,
        "chainId": settings.chain_id,
        "parentName": settings.ens_parent_name,
        "registryAddress": settings.ens_registry_address,
        "reverseRegistrarAddress": settings.ens_reverse_registrar_address,
        "publicResolverAddress": settings.ens_public_resolver_address,
    }


@app.post("/v1/ens/register-safe")
def register_safe_ens(req: RegisterSafeEnsRequest):
    try:
        resolver = req.resolver_address or settings.ens_public_resolver_address
        if not resolver:
            raise ValueError("resolver_address is required")

        full_name = ens_service.resolve_full_name(req.label, req.parent_name)
        result = {
            "subname": ens_service.create_subname(
                parent_name=settings.parent_name,
                label=req.label,
                owner_address=req.safe_address,
                resolver_address=resolver,
                ttl=req.ttl,
            )
        }

        if req.address:
            result["addr"] = ens_service.set_addr(full_name, req.address, resolver_address=resolver)

        if req.texts:
            result["texts"] = ens_service.set_text_records(full_name, req.texts, resolver_address=resolver)

        if req.set_reverse:
            result["reverse"] = ens_service.set_reverse_name(req.safe_address, full_name)

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/ens/addr/prepare-safe-tx")
def prepare_set_ens_addr_safe_tx(req: PrepareSetEnsAddrSafeTxRequest):
    try:
        tx = ens_service.build_set_addr_tx(
            name=req.name,
            address=req.address,
            resolver_address=req.resolver_address,
        )
        return safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=tx["to"],
            data=tx["data"],
            value=tx["value"],
            operation=req.operation,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/ens/text/prepare-safe-tx")
def prepare_set_ens_text_safe_tx(req: PrepareSetEnsTextSafeTxRequest):
    try:
        tx = ens_service.build_set_text_tx(
            name=req.name,
            key=req.key,
            value=req.value,
            resolver_address=req.resolver_address,
        )
        return safe_service.build_safe_tx(
            safe_address=req.safe_address,
            to=tx["to"],
            data=tx["data"],
            value=tx["value"],
            operation=req.operation,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/ens/names/{name}")
def get_ens_profile(name: str):
    try:
        return ens_service.get_profile(
            name,
            text_keys=["stop_loss_pct", "take_profit_pct", "max_open_positions", "min_eth_balance", "max_slippage_tolerance_pct", "max_gas_price_gwei", "authorized_tokens"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Trades

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
            allowed_tokens_in=settings.trade_allowed_tokens_in,
            allowed_tokens_out=settings.trade_allowed_tokens_out,
            max_input_per_tx=settings.trade_max_input_per_tx,
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
            allowed_tokens_in=settings.trade_allowed_tokens_in,
            allowed_tokens_out=settings.trade_allowed_tokens_out,
            max_input_per_tx=settings.trade_max_input_per_tx,
            operation=0,
        )
    except PolicyViolation as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SimulationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
