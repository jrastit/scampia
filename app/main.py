from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from app.api.ens import build_router as build_ens_router
    from app.api.health import build_router as build_health_router
    from app.api.vaults import build_router as build_vaults_router
    from app.api.trades import build_router as build_trades_router
    from app.api.users import build_router as build_users_router
    from app.config import settings
    from app.data import get_db, init_db
    from app.services.ens_service import ENSService
    from app.services.policy_service import PolicyService
    from app.services.simulation_service import SimulationService
    from app.services.trade_service import TradeService
    from app.services.uniswap_service import UniswapService
    from app.services.user_service import UserService
    from app.services.vault_service import VaultService
except ImportError:
    from api.ens import build_router as build_ens_router
    from api.health import build_router as build_health_router
    from api.vaults import build_router as build_vaults_router
    from api.trades import build_router as build_trades_router
    from api.users import build_router as build_users_router
    from config import settings
    from data import get_db, init_db
    from ens_service import ENSService
    from policy_service import PolicyService
    from simulation_service import SimulationService
    from trade_service import TradeService
    from uniswap_service import UniswapService
    from user_service import UserService
    from vault_service import VaultService


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    root_path=settings.app_root_path,
    openapi_url="/v1/openapi.json",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
)

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ens_service = ENSService()
vault_service = VaultService()
uniswap_service = UniswapService()
policy_service = PolicyService()
simulation_service = SimulationService()
trade_service = TradeService(
    uniswap_service=uniswap_service,
    policy_service=policy_service,
    simulation_service=simulation_service,
    vault_service=vault_service,
)
user_service = UserService(vault_service=vault_service)

app.include_router(build_health_router(settings))
app.include_router(build_users_router(user_service, get_db))
app.include_router(build_vaults_router(vault_service))
app.include_router(build_ens_router(ens_service, vault_service, settings))
app.include_router(build_trades_router(trade_service, settings))
